import time
import random
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, abort
from flask import make_response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = 'dev-secret-key'
app.wsgi_app = ProxyFix(app.wsgi_app)

# Configure static files
app.static_folder = 'static'
app.static_url_path = '/static'

# In-memory simple DB/state (for demo only)
DB = {
    'display_names': set(['alice', 'bob', 'charlie']),
    'rate_limits': {},  # ip -> [timestamps]
}

# Configurable flakiness and timeouts
CONFIG = {
    'display_name_timeout_prob': 0.05,   # prob of timeout during async check
    'email_reject_rate': 0.03,           # chance email is rejected server-side
    'session_timeout_seconds': 30,       # short for testing
    'rate_limit_window_s': 10,
    'rate_limit_max': 10,
    'honeypot_enabled': True,
    'accessibility_mode': False,
}

# Utility helpers
def client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)

def too_many_requests(ip):
    now = time.time()
    window = CONFIG['rate_limit_window_s']
    arr = DB['rate_limits'].get(ip, [])
    # remove old
    arr = [t for t in arr if t > now - window]
    DB['rate_limits'][ip] = arr
    return len(arr) >= CONFIG['rate_limit_max']

def record_request(ip):
    DB['rate_limits'].setdefault(ip, []).append(time.time())

@app.before_request
def enforce_session_timeout():
    # simple idle timeout using session
    if 'last_ts' in session:
        idle = time.time() - session['last_ts']
        if idle > CONFIG['session_timeout_seconds']:
            session.clear()
            return redirect(url_for('session_expired'))
    session['last_ts'] = time.time()

@app.route('/')
def index():
    invite = request.args.get('invite')
    return render_template('index.html', invite=invite)

@app.route('/check_display_name')
def check_display_name():
    # Simulate async check with occasional timeouts/500
    name = request.args.get('display_name', '')
    # probabilistic delay/timeout
    if random.random() < CONFIG['display_name_timeout_prob']:
        time.sleep(2)
        return make_response(jsonify({'error': 'timeout'}), 500)
    is_taken = name.lower() in DB['display_names']
    return jsonify({'taken': is_taken})

@app.route('/submit', methods=['POST'])
def submit():
    ip = client_ip()
    if too_many_requests(ip):
        return make_response(jsonify({'error': 'rate_limited'}), 429)
    record_request(ip)

    data = request.json or request.form
    # Honeypot
    if CONFIG['honeypot_enabled'] and data.get('middle_initial'):
        return make_response(jsonify({'error': 'honeypot_triggered'}), 403)

    # Captcha check
    if data.get('captcha') != 'passed':
        return make_response(jsonify({'success': False, 'errors': [{'field': 'captcha', 'msg': 'Captcha not passed'}]}), 400)

    name = data.get('name', '')
    email = data.get('email', '')
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')
    recovery = data.get('recovery_phrase')

    errors = []
    if not (4 <= len(name) <= 20):
        errors.append({'field': 'name', 'msg': 'Name must be 4-20 chars'})
    if '@' not in email:
        errors.append({'field': 'email', 'msg': 'Email must contain @'})
    if password == name or password == email:
        errors.append({'field': 'password', 'msg': 'Password must differ from name/email'})
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        errors.append({'field': 'password', 'msg': 'Password must contain letters and numbers'})
    if password != confirm:
        errors.append({'field': 'confirm_password', 'msg': 'Passwords do not match'})
    if not recovery:
        errors.append({'field': 'recovery', 'msg': 'Recovery phrase required'})

    # Simulate intermittent server-side email rejection
    if random.random() < CONFIG['email_reject_rate']:
        errors.append({'field': 'email', 'msg': 'Email domain blacklisted (intermittent)'} )

    # Simulate race condition: if display_name_check_pending flag present, reject
    if data.get('display_name_check_pending') == '1':
        return make_response(jsonify({'error': 'state_inconsistent'}), 409)

    if errors:
        return make_response(jsonify({'success': False, 'errors': errors}), 400)

    # create account - deterministic id
    account_id = f"acct_{int(time.time()*1000)}"
    DB['display_names'].add(data.get('display_name', '').lower())
    return jsonify({'success': True, 'account_id': account_id})

@app.route('/session_expired')
def session_expired():
    return render_template('session_expired.html')

@app.route('/static-config')
def static_config():
    return jsonify(CONFIG)

@app.route('/user_info')
def user_info():
    return render_template('user_info.html')

@app.route('/credentials')
def credentials():
    return render_template('credentials.html')

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/failed')
def failed():
    return render_template('failed.html')

if __name__ == '__main__':
    app.run(port=8000, debug=True)