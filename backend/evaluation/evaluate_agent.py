import sys
import os
import matplotlib.pyplot as plt

# Add Project Root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.microgrid_env import MicrogridEnv
from agent.dqn_agent import DQNAgent

# Initialize
env = MicrogridEnv("data/clean_microgrid_dataset.csv")
agent = DQNAgent(5, 5) # State size 5, Action size 5

# Load Model
model_path = "dqn_model.pth"
if os.path.exists(model_path):
    agent.load(model_path)
    print(f"✅ Loaded model from {model_path}")
else:
    print(f"⚠️ Model not found at {model_path}. Running with random weights.")

state = env.reset()
rewards = []
total_reward = 0

print("Starting Evaluation...")

while True:
    action = agent.act(state)
    next_state, reward, done = env.step(action)
    rewards.append(reward)
    total_reward += reward
    state = next_state
    if done:
        break

print(f"Evaluation Complete. Total Reward: {total_reward:.2f}")

plt.plot(rewards)
plt.title("Reward per Time Step")
plt.xlabel("Time")
plt.ylabel("Reward")
plt.show()
