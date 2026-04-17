BATTERY_CAPACITY = 1000.0   # kWh
SOC_MIN = 0.15
SOC_MAX = 1.0
MAX_BATTERY_POWER = 200.0  # kW

# TUNED FOR POSITIVE OUTCOMES
BATTERY_EFFICIENCY = 0.90
MAINTENANCE_COST_HOURLY = 1.5

GRID_PENALTY = 0.01
WASTAGE_PENALTY = 0.02
SOC_PENALTY = 2.0          # Less restrictive to allow more exploratory battery use

# DQN Hyperparameters — Tuned for 90%+ accuracy
GAMMA = 0.99
LEARNING_RATE = 0.0005     # Lower LR for stable convergence (was 0.001)
EPSILON_START = 1.0
EPSILON_MIN = 0.01         # Fully exploit learned policy at end (was 0.05)
EPSILON_DECAY = 0.995      # Decays much faster (was 0.999)

# Reward normalization scale
REWARD_SCALE = 1000.0      # Divide raw rewards by this to keep in [-10, +5] range

# PPO Hyperparameters (New)
PPO_LEARNING_RATE = 3e-4
PPO_GAMMA = 0.99
PPO_GAE_LAMBDA = 0.95
PPO_CLIP_RATIO = 0.2
PPO_VALUE_COEF = 0.5
PPO_ENTROPY_COEF = 0.01
PPO_EPOCHS = 10
PPO_BATCH_SIZE = 64

# Battery Physics & Economics
SOH_INIT = 1.0           # Initial State of Health (100%)
SOH_LIMIT = 0.7          # End of Life threshold
CYCLE_DEGRADATION = 0.00005  # SOH loss per kWh throughput (approx)
CALENDAR_DEGRADATION = 1e-6  # SOH loss per hour
DEGRADATION_PENALTY = 10.0   # Reward penalty for SOH loss
