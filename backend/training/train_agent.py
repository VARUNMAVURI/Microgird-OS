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
# Force UTF-8 output on Windows to avoid UnicodeEncodeError
import io  # noqa: E402
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from environment.microgrid_env import MicrogridEnv  # noqa: E402
from agent.dqn_agent import DQNAgent  # noqa: E402
from database.mongo_logger import log_episode  # noqa: E402

# Configuration
EPISODES       = 1000      # Increased from 100 for better learning
BATCH_SIZE     = 256       # Increased batch size to learn from more past experiences
WARMUP_STEPS   = 500      # Faster warmup
REPLAY_FREQ    = 4        # Train every 4 env steps
SOFT_UPDATE_FREQ = 5      # Soft target update every 5 episodes
SAVE_PATH      = "dqn_model.pth"

env   = MicrogridEnv("data/clean_microgrid_dataset.csv")
agent = DQNAgent(5, 5)

print(f"Starting warm-up phase ({WARMUP_STEPS} random steps to fill replay buffer)...")
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

print(f"[OK] Warm-up complete ({len(agent.memory)} transitions in buffer).\n")
print("=" * 55)
print(f"{'Episode':>8} | {'Reward':>14} | {'Epsilon':>8} | {'Best':>10}")
print("=" * 55)
sys.stdout.flush()

best_reward = float("-inf")

for ep in range(EPISODES):
    state = env.reset()
    total_reward = 0.0
    t = 0

    while True:
        action = agent.act(state)
        next_state, reward, done = env.step(action)
        agent.remember(state, action, reward, next_state, done)
        state = next_state
        total_reward += reward
        t += 1

        # Replay every REPLAY_FREQ steps
        if t % REPLAY_FREQ == 0:
            agent.replay(batch=BATCH_SIZE)

        if done:
            break

    # Soft target update every SOFT_UPDATE_FREQ episodes
    if (ep + 1) % SOFT_UPDATE_FREQ == 0:
        agent.update_target_network(soft=True, tau=0.05)

    # Hard target update less frequently
    if (ep + 1) % 50 == 0:
        agent.update_target_network(soft=False)

    # Auto-save best model
    is_best = ""
    if total_reward > best_reward:
        best_reward = total_reward
        agent.save(SAVE_PATH)
        is_best = "[SAVED]"

    log_episode(ep, total_reward)
    print(f"  Ep {ep+1:>4} | {total_reward:>14.2f} | e={agent.epsilon:.4f} | {is_best}")
    sys.stdout.flush()

print("=" * 55)
print(f"\n[OK] Training complete! Best model saved as '{SAVE_PATH}'")
print(f"   Best episode reward: {best_reward:.2f}")

# Run evaluation automatically
print("\n" + "=" * 55)
print("Running post-training evaluation...")
print("=" * 55)
import evaluate_dqn  # noqa: E402
evaluate_dqn.evaluate()
