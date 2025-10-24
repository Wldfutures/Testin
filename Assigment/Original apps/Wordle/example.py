import gymnasium as gym
from wordle_env import WordleEnv

env = WordleEnv(word_size=5)
obs, info = env.reset()

done = False
total_reward = 0

while not done:
    action = env.action_space.sample()  # random guess
    obs, reward, done, truncated, info = env.step(action)
    total_reward += reward
    env.render()
    print(f"Guess: {info['guess']} | Reward: {reward}")

print("Episode finished. Target word was:", info["target"])