# pyre-ignore-all-errors
# type: ignore
import pandas as pd
import numpy as np
import sys
import os

# Ensure the root directory is in the path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    BATTERY_CAPACITY, SOC_MIN, SOC_MAX, SOC_PENALTY,
    GRID_PENALTY, WASTAGE_PENALTY, REWARD_SCALE
)

class MicrogridEnv:
    def __init__(self, data_path):
        self.data = pd.read_csv(data_path)
        self.action_space = np.array([-50, -25, 0, 25, 50])
        self.t = 0
        self.soc = 0.0
        self.reset()

    def reset(self):
        self.t = 0
        self.soc = self.data.loc[0, "battery_soc"]
        return self._get_state()

    def _get_state(self):
        row = self.data.loc[self.t]
        hour_of_day = (self.t % 24) / 24.0
        # Normalize each state feature to reduce scale differences
        return np.array([
            row["load_kW"] / 1000.0,        # Normalize to ~[0, 1]
            row["solar_kW"] / 1000.0,       # Normalize to ~[0, 1]
            row["price_per_MWh"] / 300.0,   # Normalize price (typical range ~0-300)
            self.soc,                        # Already in [0, 1]
            hour_of_day                      # Already in [0, 1]
        ], dtype=np.float32)

    def step(self, action_idx):
        action = self.action_space[action_idx]
        row = self.data.loc[self.t]

        load = row["load_kW"]
        solar = row["solar_kW"]
        price = row["price_per_MWh"]

        net_load = load - solar
        soc_next = self.soc + (action / BATTERY_CAPACITY)

        # SOC violation penalty — proportional to how far out of bounds
        penalty = 0
        if soc_next < SOC_MIN:
            penalty = SOC_PENALTY * (SOC_MIN - soc_next)
            soc_next = SOC_MIN
        elif soc_next > SOC_MAX:
            penalty = SOC_PENALTY * (soc_next - SOC_MAX)
            soc_next = SOC_MAX

        self.soc = soc_next

        grid_power = net_load - action

        # Core cost: only pay for grid imports (positive grid_power)
        grid_cost = max(grid_power, 0) * price

        # Wastage: solar energy that can't be used or stored
        wastage = max(solar - load, 0)

        # Solar self-consumption bonus: reward when solar covers load
        solar_bonus = min(solar, load) * 0.05  # small positive reward

        # Build normalized reward — dividing by REWARD_SCALE keeps values in [-10, +5]
        reward = (-grid_cost
                  - GRID_PENALTY * abs(grid_power)
                  - WASTAGE_PENALTY * wastage
                  - penalty
                  + solar_bonus) / REWARD_SCALE

        self.t += 1
        done = self.t >= len(self.data) - 1

        return self._get_state(), reward, done
