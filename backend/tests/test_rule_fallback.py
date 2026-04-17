
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.simulation_engine import SimulationEngine
import pandas as pd

def test_rule_fallback():
    print("Testing Rule-Based Fallback (No AI)...")
    sim = SimulationEngine()
    
    # Force model_loaded to False
    sim.model_loaded = False
    
    # Mock Data
    sim.df = pd.DataFrame({
        "load_kW": [10.0]*10,
        "solar_kW": [5.0]*10,
        "price_per_MWh": [100.0]*10,
        "battery_soc": [50.0]*10,
        "hour": [12]*10
    })
    sim.reset()
    
    # 1. Step (Should not crash)
    try:
        res = sim.step(mode="AI") # Should fallback
        print("✅ Step successful.")
        print("DEBUG: Result Keys:", res.keys())
        
        # Verify decision is Rule-based
        if "Rule" in res.get("decision", ""):
            print(f"✅ Decision is Rule-Based: {res['decision']}")
        else:
            print(f"❌ Unexpected Decision: {res.get('decision')}")
            
    except Exception as e:
        print(f"❌ Step Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rule_fallback()
