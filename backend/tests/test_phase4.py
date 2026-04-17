import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.simulation_engine import SimulationEngine

def test_phase4():
    print("Testing Phase 4 Features...")
    sim = SimulationEngine()
    
    # Mock Data
    if sim.df is None:
        print("Mocking Data...")
        import pandas as pd
        sim.df = pd.DataFrame({
            "load_kW": [10]*100,
            "solar_kW": [5]*100,
            "price_per_MWh": [100]*100,
            "battery_soc": [50]*100,
            "hour": [i%24 for i in range(100)]
        })
        sim.reset()
        
    # 1. Check Initial State
    assert sim.grid_online == True
    print("✅ Grid Online Initially")
    
    # 2. Toggle Grid
    new_state = sim.toggle_grid()
    assert new_state == False
    assert sim.grid_online == False
    print("✅ Grid Toggled Offline (Island Mode)")
    
    # 3. Step in Island Mode
    res = sim.step()
    if res.get('error'):
        print(f"❌ SIMULATION ERROR: {res['error']}")
        sys.exit(1)
        
    print("DEBUG: Step Result:", res)
    grid_used = res['grid_used']
    grid_export = res['grid_export']
    
    assert grid_used == 0.0
    assert grid_export == 0.0
    print(f"✅ Island Mode Verified: Grid Used={grid_used}, Export={grid_export}")
    
    # 4. Check New Fields
    assert "eco_score" in res
    assert "decision_reason" in res
    print(f"✅ New Fields Present: Eco-Score={res['eco_score']}, Reason={res['decision_reason']}")
    
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_phase4()
