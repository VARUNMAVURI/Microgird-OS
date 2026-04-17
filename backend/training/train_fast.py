# pyre-ignore-all-errors
# type: ignore
import sys
import os
import numpy as np
import torch

# Fix for Windows freezing during PyTorch training
torch.set_num_threads(1)

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.microgrid_env import MicrogridEnv  # noqa: E402
from agent.dqn_agent import DQNAgent  # noqa: E402

# Configuration - FAST
EPISODES       = 250
BATCH_SIZE     = 256
WARMUP_STEPS   = 500
REPLAY_FREQ    = 4
SOFT_UPDATE_FREQ = 1
SAVE_PATH      = "dqn_model.pth"

env   = MicrogridEnv("data/clean_microgrid_dataset.csv")
agent = DQNAgent(5, 5)

print(f"Starting fast training ({EPISODES} episodes)...")
state = env.reset()
warmup_count = 0
while warmup_count < WARMUP_STEPS:
    action = np.random.randint(0, 5)
    next_state, reward, done = env.step(action)
    agent.remember(state, action, reward, next_state, done)
    state = next_state
    warmup_count += 1
    if done:
        state = env.reset()

print("Warm-up complete. Training...")

best_reward = float("-inf")

for ep in range(EPISODES):
    state = env.reset()
    total_reward = 0
    t = 0
    while True:
        action = agent.act(state)
        next_state, reward, done = env.step(action)
        agent.remember(state, action, reward, next_state, done)
        state = next_state
        total_reward += reward
        t += 1
        if t % REPLAY_FREQ == 0:
            agent.replay(batch=BATCH_SIZE)
        if done: break
    # Calculate "Accuracy" as a ratio of reward to a baseline (simplified)
    # Here we just print the reward
    print(f"Episode {ep+1}/{EPISODES} | Reward: {total_reward:.2f}")
    sys.stdout.flush()

print("Fast training complete.")
