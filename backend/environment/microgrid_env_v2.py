# pyre-ignore-all-errors
# type: ignore
import pandas as pd
import numpy as np
import sys
import os

# Ensure the root directory is in the path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    SOH_INIT, MAX_BATTERY_POWER, BATTERY_CAPACITY, BATTERY_EFFICIENCY,
    CYCLE_DEGRADATION, SOC_MIN, SOC_MAX, CALENDAR_DEGRADATION,
    DEGRADATION_PENALTY, WASTAGE_PENALTY, GRID_PENALTY
)

class MicrogridEnvV2:
    def __init__(self, data_path, lookahead=24):
        self.data = pd.read_csv(data_path)
        self.lookahead = lookahead
        self.t = 0
        self.soc = 0.0
        self.soh = 1.0
        
        # State: 
        # 0: Current Load
        # 1: Current Solar
        # 2: Current Price
        # 3: Battery SOC
        # 4: Battery SOH
        # 5-(5+lookahead): Future Load
        # (5+lookahead)-(5+2*lookahead): Future Solar
        # (5+2*lookahead)-(5+3*lookahead): Future Price
        self.state_size = 5 + 3 * self.lookahead
        
        # Action: Continuous [-1.0, 1.0] (Charge/Discharge Power Ratio)
        self.action_space_low = -1.0
        self.action_space_high = 1.0
        
        self.reset()

    def reset(self):
        self.t = 0
        
        # Initialize Battery Physics
        if "battery_soc" in self.data.columns:
            self.soc = self.data.iloc[0]["battery_soc"]
        else:
            self.soc = 50.0  # Default 50%
            
        self.soh = SOH_INIT # 1.0 (100%)
        
        return self._get_state()

    def _get_state(self):
        # Current data
        row = self.data.iloc[self.t]
        
        # Forecast data (padding with 0 if end of data)
        remaining_steps = len(self.data) - 1 - self.t
        if remaining_steps >= self.lookahead:
            future_data = self.data.iloc[self.t+1 : self.t+1+self.lookahead]
            f_load = future_data["load_kW"].values
            f_solar = future_data["solar_kW"].values
            f_price = future_data["price_per_MWh"].values
        else:
            # Pad with last known value or zeros
            future_data = self.data.iloc[self.t+1 :]
            padding = self.lookahead - len(future_data)
            
            f_load = np.concatenate([future_data["load_kW"].values, np.zeros(padding)])
            f_solar = np.concatenate([future_data["solar_kW"].values, np.zeros(padding)])
            f_price = np.concatenate([future_data["price_per_MWh"].values, np.zeros(padding)])
            
        # Debugging Types
        # print(f"DEBUG State Types: Load={type(row['load_kW'])}, Solar={type(row['solar_kW'])}, SOC={type(self.soc)}")
        
        # Normalize simple inputs to help NN (optional but good practice)
        try:
            state_features = np.array([
                float(row["load_kW"]),
                float(row["solar_kW"]),
                float(row["price_per_MWh"]),
                float(self.soc),
                float(self.soh)
            ], dtype=np.float32)
        except Exception as e:
            print(f"Error constructing state_features: {e}")
            print(f"Row: {row}")
            print(f"SOC: {self.soc}, SOH: {self.soh}")
            raise e
        
        state = np.concatenate([state_features, f_load, f_solar, f_price]).astype(np.float32)
        return state

    def step(self, action):
        # Action is continuous [-1, 1]
        # map to Power [-MAX_POWER, MAX_POWER] * SOH (Old batteries have less power?) 
        # Actually SOH mostly affects Capacity, mostly separate Power limits. 
        # But let's say Internal Resistance increases -> Power Limit decreases slightly.
        # For simplicity: Power Limit is constant, Capacity fades.
        
        action = np.clip(action, -1.0, 1.0)
        action_power = action * MAX_BATTERY_POWER 
        
        row = self.data.iloc[self.t]
        load = row["load_kW"]
        solar = row["solar_kW"]
        price = row["price_per_MWh"]
        
        net_load = load - solar
        
        # Battery Physics logic (Capacity fades with SOH)
        current_capacity = BATTERY_CAPACITY * self.soh
        
        # --- EXECUTE ACTION ---
        if action_power > 0: # Charge
            # Can we charge this much?
            # Space remaining in battery
            # SOC is Percentage of NOMINAL or CURRENT capacity? 
            # Usually users see % of Current Capacity.
            
            energy_to_full = (100.0 - self.soc) / 100.0 * current_capacity
            max_input = energy_to_full / BATTERY_EFFICIENCY
            
            real_power = min(action_power, max_input)
            
            # Physics: Throughput Degradation
            cycle_deg = abs(real_power) * CYCLE_DEGRADATION
            
            # Energy Flow
            stored_energy = real_power * BATTERY_EFFICIENCY
            self.soc += (stored_energy / current_capacity) * 100
            
            grid_power = max(0, net_load + real_power) # noqa: F841 If solar covers load, we manipulate this logic in SimulationEngine, 
                                                       # but here for TRAINING reward calculation we simplify:
                                                       # We just look at Net Grid Exchange.
            # Simplified Grid Interaction for Reward:
            # If (Load - Solar) + Battery_Charge > 0: Import
            # If (Load - Solar) + Battery_Charge < 0: Export
            
            grid_exchange = net_load + real_power
            
        else: # Discharge
            # Energy available
            energy_avail = (self.soc - (SOC_MIN*100)) / 100.0 * current_capacity
            max_output = energy_avail * BATTERY_EFFICIENCY
            
            real_power = max(action_power, -max_output) # action_power is negative
            
            # Physics
            cycle_deg = abs(real_power) * CYCLE_DEGRADATION
            
            discharged_energy = abs(real_power) # This is output
            internal_loss = (discharged_energy / BATTERY_EFFICIENCY) - discharged_energy
            self.soc -= ((discharged_energy + internal_loss) / current_capacity) * 100
            
            grid_exchange = net_load + real_power
            
        # --- PHYSICS UPDATE ---
        self.soh -= cycle_deg
        self.soh -= CALENDAR_DEGRADATION
        self.soh = max(0.1, self.soh) # Clamp to 10%
        
        # Safety Clamp SOC
        self.soc = np.clip(self.soc, SOC_MIN*100, SOC_MAX*100)
        
        # --- REWARD CALCULATION ---
        # 1. Cost of Energy
        if grid_exchange > 0: # Import
            grid_cost = grid_exchange * price
        else: # Export
            grid_cost = grid_exchange * price # Negative cost = Revenue
            
        # 2. Battery Degradation Cost (The "Hidden" Cost)
        # We value the battery life. Losing 1% SOH is expensive.
        # Cost = SOH_loss * VALUE_OF_BATTERY
        # Let's use the constant from config.
        deg_penalty = (cycle_deg + CALENDAR_DEGRADATION) * DEGRADATION_PENALTY * 1000 # Scaling factor
        
        # 3. Penalties (Aligned with Abstract)
        # "The system penalizes energy wastage, excessive grid usage, and power shortages."
        
        # Wastage: Energy lost due to efficiency (charge/discharge) or dumped
        # In this simplified model, 'wasted_energy' can be approximated by efficiency losses 
        # or if we had a logic for dumping excess solar (which we don't explicitly have here, but can infer).
        # For now, let's penalize efficiency loss as "wastage".
        # (internal_loss defined above for discharge, charge loss is similar)
        
        # Calculate usage penalties
        wastage_penalty = 0
        if action_power > 0: # Charge
             stored = real_power * BATTERY_EFFICIENCY
             loss = real_power - stored
             wastage_penalty += loss * WASTAGE_PENALTY
        else: # Discharge
             loss = internal_loss
             wastage_penalty += loss * WASTAGE_PENALTY
             
        # Grid Usage Penalty (Encourage local self-sufficiency)
        # Penalize any grid interaction, but maybe more for peaks?
        # Abstract says "excessive grid usage". Let's penalize all usage slightly.
        grid_penalty = abs(grid_exchange) * GRID_PENALTY
        
        obs_reward = -grid_cost - deg_penalty - wastage_penalty - grid_penalty
        
        self.t += 1
        done = self.t >= len(self.data) - 1 - self.lookahead # End when we run out of forecast
        
        return self._get_state(), obs_reward, done

    def render(self):
        pass
