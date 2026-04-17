from database.db_manager import DatabaseManager
import time

def test_db():
    print("Testing DatabaseManager...")
    db = DatabaseManager()
    
    # Test Registration
    email = f"test_user_{int(time.time())}@example.com"
    password = "password123"
    
    success, msg = db.register_user(email, password)
    print(f"Registration ({email}): {success} - {msg}")
    
    # Test Duplicate Registration
    success, msg = db.register_user(email, password)
    print(f"Duplicate Reg: {success} - {msg}") # Should fail
    
    # Test Auth
    if db.authenticate_user(email, password):
        print("✅ Authentication Successful")
    else:
        print("❌ Authentication Failed")
        
    if not db.authenticate_user(email, "wrongpass"):
        print("✅ Wrong Password Rejected")
    else:
        print("❌ Wrong Password Accepted")
        
    # Test Save
    data = {"test_metric": 100, "savings_pct": 50.5}
    success, msg = db.save_simulation(email, data)
    print(f"Save Simulation: {success} - {msg}")
    
    # Test History
    history = db.get_user_history(email)
    print(f"History Length: {len(history)}")
    if len(history) > 0:
        print(f"Last Item: {history[0]['summary']}")

if __name__ == "__main__":
    test_db()
