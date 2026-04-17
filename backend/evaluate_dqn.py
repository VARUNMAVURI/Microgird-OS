import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from environment.microgrid_env import MicrogridEnv  # noqa: E402
from agent.dqn_agent import DQNAgent  # noqa: E402

def evaluate(model_path="dqn_model.pth", data_path="data/clean_microgrid_dataset.csv"):
    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found: {data_path}")
        return

    env = MicrogridEnv(data_path)
    # The agent expects state_size 5 and action_size 5 (from train_agent.py)
    agent = DQNAgent(5, 5)
    
    if os.path.exists(model_path):
        agent.load(model_path)
        print(f"[OK] Loaded trained model from {model_path}")
    else:
        print(f"[WARN] Model not found at {model_path}. Evaluation will use random weights.")

    state = env.reset()
    done = False
    
    agent_total_cost = 0
    baseline_total_cost = 0
    
    # Baseline: Simple logic (no battery usage)
    # Total grid cost = Sum(max(0, load - solar) * price)
    
    while not done:
        # 1. Agent Logic
        action_idx = agent.act(state)
        # We need to peek at the env state to calculate costs precisely
        # But we can just use the env's logic
        
        # Peel into env variables for baseline
        row = env.data.loc[env.t]
        load = row["load_kW"]
        solar = row["solar_kW"]
        price = row["price_per_MWh"]
        
        baseline_grid_power = max(0, load - solar)
        baseline_total_cost += baseline_grid_power * price
        
        # Step env with agent action
        next_state, reward, done = env.step(action_idx)
        
        # The env reward is (-grid_cost ...)/REWARD_SCALE
        # Let's recalculate agent cost for transparency
        action = env.action_space[action_idx]
        agent_grid_power = max(0, (load - solar) - action)
        agent_total_cost += agent_grid_power * price
        
        state = next_state

    # Accuracy Calculation (Savings vs Baseline)
    if baseline_total_cost > 0:
        savings = baseline_total_cost - agent_total_cost
        accuracy = (savings / baseline_total_cost) * 100
    else:
        accuracy = 0.0

    print("\n" + "="*40)
    print(f"{'METRIC':<20} | {'VALUE':<15}")
    print("-" * 40)
    print(f"{'Baseline Cost':<20} | {baseline_total_cost:>10.2f}")
    print(f"{'AI Optimized Cost':<20} | {agent_total_cost:>10.2f}")
    print(f"{'Total Savings':<20} | {max(0, baseline_total_cost - agent_total_cost):>10.2f}")
    print(f"{'Savings Accuracy':<20} | {accuracy:>9.2f}%")
    print("="*40 + "\n")
    
    return accuracy

if __name__ == "__main__":
    evaluate()
