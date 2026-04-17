import pulp
import pandas as pd
import os
import sys

# Add Parent Directory to Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (  # noqa: E402
    MAX_BATTERY_POWER, SOC_MIN, BATTERY_CAPACITY, SOC_MAX,
    DEGRADATION_PENALTY, CYCLE_DEGRADATION, BATTERY_EFFICIENCY
)

def solve_optimal_schedule(data_path):
    print(f"🔬 Solving Optimal Schedule (LP Benchmark) for {data_path}...")
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return None

    df = pd.read_csv(data_path)
    T = len(df)
    
    # Create Problem
    prob = pulp.LpProblem("Microgrid_Optimization", pulp.LpMinimize)
    
    # Variables
    # P_grid_import[t] >= 0
    # P_grid_export[t] >= 0
    # P_charge[t] >= 0
    # P_discharge[t] >= 0
    # E_soc[t] (State of Charge in kWh)
    # Binary variable for charging/discharging to prevent simultaneous? 
    # For LP relaxation, we often skip binary if price signals are clear, 
    # but to be strict we might need MILP. Let's stick to LP for speed if usually distinct.
    # Actually, simultaneous charge/discharge is physically impossible but mathematically allowed in LP 
    # if we don't use binaries. However, with efficiency loss, the solver naturally avoids it 
    # (waste of energy to charge and discharge at same time).
    
    P_grid_import = pulp.LpVariable.dicts("Grid_Import", range(T), lowBound=0)
    P_grid_export = pulp.LpVariable.dicts("Grid_Export", range(T), lowBound=0)
    P_charge = pulp.LpVariable.dicts("Battery_Charge", range(T), lowBound=0, upBound=MAX_BATTERY_POWER)
    P_discharge = pulp.LpVariable.dicts("Battery_Discharge", range(T), lowBound=0, upBound=MAX_BATTERY_POWER)
    E_soc = pulp.LpVariable.dicts("SOC", range(T+1), lowBound=SOC_MIN*BATTERY_CAPACITY, upBound=SOC_MAX*BATTERY_CAPACITY)
    
    # Initialize SOC
    prob += E_soc[0] == 0.5 * BATTERY_CAPACITY
    
    # Objective Function: Minimize Cost (Import Cost - Export Revenue)
    # We could include degradation cost here too to be fair to the RL agent.
    # Cost = Sum(Import*Price - Export*Price + DegradationCost)
    # Degradation ~ (Charge + Discharge) * CostPerkWhThroughput
    
    # Let's align with the RL reward function which includes degradation.
    # deg_cost_per_kwh = DEGRADATION_PENALTY * 1000 * CYCLE_DEGRADATION # Approx cost per kWh
    # Wait, DEGRADATION_PENALTY in RL was 10.0 (abstract units). 
    # In RL: Reward -= (cycle_deg + cal_deg) * 10*1000
    # cycle_deg = power * 0.00005. So cost = power * 0.00005 * 10000 = power * 0.5
    # So effectively 0.5 currency units per kW per step?
    
    # Let's prioritize pure economic profit for the benchmark, but maybe with a small penalty to avoid unnecessary churn.
    # deg_cost = 0.0 # Set to 0 for "Perfect Economic" benchmark, or >0 for "Realistic" one.
    
    total_cost = 0
    for t in range(T):
        price = df.loc[t, "price_per_MWh"] / 1000.0 # Price per kWh
        
        cost_t = (P_grid_import[t] * price) - (P_grid_export[t] * price)
        # Add degradation cost proxy
        # cost_t += (P_charge[t] + P_discharge[t]) * 0.01 
        
        total_cost += cost_t
        
    prob += total_cost
    
    for t in range(T):
        load = df.loc[t, "load_kW"]
        solar = df.loc[t, "solar_kW"]
        
        # 1. Energy Balance at Bus
        # Generation + Import + Discharge = Load + Export + Charge
        # Solar + Import + Discharge = Load + Export + Charge
        prob += (solar + P_grid_import[t] + P_discharge[t] 
                 == load + P_grid_export[t] + P_charge[t])
                 
        # 2. Battery SOC Dynamics
        # E[t+1] = E[t] + Charge*Eff - Discharge/Eff
        # Note: In RL we did Discharge/Eff for internal loss. 
        # Here: Energy Stored = Charge*Eff. Energy Released from Storage = Discharge/Eff.
        # Wait, if I discharge 10kW to grid, I lose 10/Eff from SOC. Correct.
        
        prob += E_soc[t+1] == E_soc[t] + (P_charge[t] * BATTERY_EFFICIENCY) - (P_discharge[t] / BATTERY_EFFICIENCY)
        
    # Solve
    # solver = pulp.PULP_CBC_CMD(msg=1) # Default solver
    prob.solve()
    
    status = pulp.LpStatus[prob.status]
    print(f"✅ Simulation Status: {status}")
    
    if status != "Optimal":
        return None
        
    # Extract Results
    results = []
    total_savings = 0
    benchmark_cost = 0 # Cost without battery/solar
    
    for t in range(T):
        # Calculate what cost would be without microgrid
        load = df.loc[t, "load_kW"]
        price = df.loc[t, "price_per_MWh"] / 1000.0
        benchmark_cost += load * price
        
        # Actual optimized cost
        imp = pulp.value(P_grid_import[t])
        exp = pulp.value(P_grid_export[t])
        actual_cost = (imp * price) - (exp * price)
        
        results.append({
            "t": t,
            "import": imp,
            "export": exp,
            "charge": pulp.value(P_charge[t]),
            "discharge": pulp.value(P_discharge[t]),
            "soc": pulp.value(E_soc[t]),
            "cost": actual_cost
        })
        
    total_opt_cost = pulp.value(prob.objective)
    total_savings = benchmark_cost - total_opt_cost
    
    print(f"💰 LP Benchmark Savings: ${total_savings:,.2f}")
    print(f"📉 Benchmark Cost: ${benchmark_cost:,.2f}")
    print(f"📉 Optimized Cost: ${total_opt_cost:,.2f}")
    
    return results, total_savings

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "optimized_data.csv")
    solve_optimal_schedule(path)
