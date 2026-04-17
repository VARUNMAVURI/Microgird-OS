
import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.simulation_engine import SimulationEngine

def test_sorting_fix():
    print("Testing SimulationEngine.load_data sorting behavior...")
    
    # Create a dummy dataset with 4 days of data (96 hours) to bypass min_rows=72 check
    # Day 1: Load = 10
    # Day 2: Load = 20
    # Day 3: Load = 30
    # Day 4: Load = 40
    csv_path = "temp_test_sorting.csv"
    with open(csv_path, "w") as f:
        f.write("hour,load_kW,solar_kW,price_per_MWh\n")
        hours_per_day = 24
        
        # Day 1
        for h in range(hours_per_day):
            f.write(f"{h},10,0,10\n")
        # Day 2
        for h in range(hours_per_day):
            f.write(f"{h},20,0,20\n")
        # Day 3
        for h in range(hours_per_day):
            f.write(f"{h},30,0,30\n")
        # Day 4
        for h in range(hours_per_day):
            f.write(f"{h},40,0,40\n")
            
    try:
        sim = SimulationEngine()
        success = sim.load_data(csv_path)
        
        if not success:
            print("❌ Failed to load data")
            return

        loaded_load = sim.df["load_kW"].tolist()
        
        # Expected: 24 of 10s, then 24 of 20s, etc.
        expected_load = ([10.0]*24) + ([20.0]*24) + ([30.0]*24) + ([40.0]*24)
        
        # Checking just the first few transitions is enough to verify order
        # But let's check full equality since we control the input
        
        loaded_load_int = [int(x) for x in loaded_load]
        expected_load_int = [int(x) for x in expected_load]

        # Verify just the transitions to confirm blocks are intact
        # Index 23 should be 10, Index 24 should be 20
        # Index 47 should be 20, Index 48 should be 30
        
        print(f"Index 23 (End Day 1): {loaded_load_int[23]} (Expected 10)")
        print(f"Index 24 (Start Day 2): {loaded_load_int[24]} (Expected 20)")
        
        if loaded_load_int == expected_load_int:
            print("✅ SUCCESS: Data order preserved! Sorting bug is fixed.")
        else:
            print("❌ FAILURE: Data order was changed.")
            # Print simplified error
            print(f"First 5: {loaded_load_int[:5]}")
            print(f"Index 23-28: {loaded_load_int[23:28]}")
            
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)

if __name__ == "__main__":
    test_sorting_fix()
