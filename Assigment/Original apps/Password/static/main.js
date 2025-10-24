// main.js - client logic for validation, async checks, and state steering

document.addEventListener('DOMContentLoaded', () => {
  // page-specific initialization
  if (document.getElementById('display_name')) {
    const dn = document.getElementById('display_name')
    const status = document.getElementById('display_name_status')
    let pending = false
    dn.addEventListener('input', () => {
      pending = true
      status.textContent = 'checking...'
      fetch(`/check_display_name?display_name=${encodeURIComponent(dn.value)}`)
        .then(r => r.json())
        .then(j => { pending = false; status.textContent = j.taken ? 'taken' : 'available' })
        .catch(_ => { pending = false; status.textContent = 'error' })
    })

    document.getElementById('toCreds').addEventListener('click', () => {
      // gather and persist to sessionStorage
      const data = {name: document.getElementById('name').value, email: document.getElementById('email').value, display_name: dn.value, display_name_check_pending: pending ? '1' : '0', middle_initial: document.getElementById('middle_initial').value }
      sessionStorage.setItem('step1', JSON.stringify(data))
      window.location = '/credentials'
    })
  }

  if (document.getElementById('toReview')) {
    // populate recovery selects
    const wordList = ['apple','bridge','cat','delta','echo','flame','garden','hotel','igloo','jazz','kite','lemon','mount','north','ocean','pine','quarry','river','stone','tango','unity','viper','willow','xray','yonder','zeal']
    for (let i=1;i<=3;i++){
      const sel = document.getElementById('r'+i)
      wordList.slice(0,15).forEach(w=>{ const o=document.createElement('option'); o.value=w; o.text=w; sel.add(o) })
    }

    const captchaDiv = document.getElementById('simple_captcha');
    if (captchaDiv) {
      captchaDiv.innerHTML = '';
      const slider = document.createElement('input');
      slider.type = 'range';
      slider.min = '0';
      slider.max = '100';
      slider.value = '0';
      slider.id = 'captcha_slider';
      slider.style.width = '200px';
      captchaDiv.appendChild(slider);

      const label = document.createElement('span');
      label.textContent = ' Slide to pass';
      captchaDiv.appendChild(label);

      slider.addEventListener('input', () => {
        if (slider.value === slider.max) {
          sessionStorage.setItem('captcha','passed');
          label.textContent = ' Passed!';
          label.style.color = 'green';
        } else {
          sessionStorage.removeItem('captcha');
          label.textContent = ' Slide to pass';
          label.style.color = '';
        }
      });
    }

    document.getElementById('toReview').addEventListener('click', ()=>{
      const data = JSON.parse(sessionStorage.getItem('step1')||'{}')
      data.password = document.getElementById('password').value
      data.confirm_password = document.getElementById('confirm_password').value
      data.recovery_phrase = [document.getElementById('r1').value, document.getElementById('r2').value, document.getElementById('r3').value]
      data.captcha = sessionStorage.getItem('captcha') || ''
      sessionStorage.setItem('step2', JSON.stringify(data))
      window.location = '/review'
    })
  }

  if (document.getElementById('submitBtn')){
    document.getElementById('submitBtn').addEventListener('click', ()=>{
      const data = JSON.parse(sessionStorage.getItem('step2')||'{}')
      fetch('/submit', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)})
        .then(r => r.json().then(j => ({code: r.status, body: j}))).then(({code, body}) => {
          if (code === 200 && body.success) window.location = '/success'
          else { window.location = '/failed'; sessionStorage.setItem('last_errors', JSON.stringify(body)) }
        })
    })
  }
})
