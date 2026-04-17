import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add Parent Directory to Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from environment.microgrid_env_v2 import MicrogridEnvV2  # noqa: E402
from agent.ppo_agent import PPOAgent  # noqa: E402
from utils.config import PPO_BATCH_SIZE  # noqa: E402

def train():
    # Load Environment
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/clean_microgrid_dataset.csv")
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return

    env = MicrogridEnvV2(data_path)
    
    state_dim = env.state_size
    action_dim = 1 # Continuous 1D action
    
    agent = PPOAgent(state_dim, action_dim)
    
    episodes = 50 # Set to 50 for faster demonstration
    scores = []
    
    print(f"🚀 Starting PPO Training on {len(env.data)} data points for {episodes} episodes...")
    
    for e in range(episodes):
        state = env.reset()
        score = 0
        done = False
        
        while not done:
            action, log_prob, val = agent.get_action(state)
            next_state, reward, done = env.step(action)
            
            agent.store_transition((state, action, reward, next_state, val, log_prob, done))
            
            # Learn every N steps or at end of episode? 
            # PPO usually collects a batch (trajectory) then updates.
            # Our batch size is in config.
            if len(agent.experience_buffer) >= PPO_BATCH_SIZE:
                agent.learn()
                
            state = next_state
            score += reward
            
        # Learn from remaining experience at end of episode
        if len(agent.experience_buffer) > 0:
            agent.learn()
            
        scores.append(score)
        avg_score = np.mean(scores[-100:])
        
        print(f"Episode {e+1}/{episodes} | Score: {float(score):.1f} | Avg Score: {float(avg_score):.1f} | SOH: {float(env.soh):.3f}")
        
        # Save best model
        if e % 50 == 0:
            agent.save(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ppo_model.pth"))
            
    # Final Save
    agent.save(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ppo_model.pth"))
    print("✅ Training Complete. Model saved as ppo_model.pth")
    
    # Plot Learning Curve
    plt.plot(scores)
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.title('PPO Training Progress')
    plt.savefig('training_curve_ppo.png')
    print("📊 Training curve saved as training_curve_ppo.png")

if __name__ == "__main__":
    train()
