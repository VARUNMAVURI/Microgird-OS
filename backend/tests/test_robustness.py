import os
import sys

# Add the current directory to sys.path to ensure local imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

def test_robustness():
    print("Starting Robustness Tests...")
    db = DatabaseManager()
    
    # Test 1: Empty inputs for registration
    res, msg = db.register_user("", "")
    print(f"Test 1 (Empty Reg): Result={res}, Msg='{msg}'")
    assert res is False
    
    # Test 2: None inputs for registration
    res, msg = db.register_user(None, None)
    print(f"Test 2 (None Reg): Result={res}, Msg='{msg}'")
    assert res is False
    
    # Test 3: Empty inputs for authentication
    auth = db.authenticate_user("", "")
    print(f"Test 3 (Empty Auth): Result={auth}")
    assert auth is False
    
    # Test 4: None inputs for authentication
    auth = db.authenticate_user(None, None)
    print(f"Test 4 (None Auth): Result={auth}")
    assert auth is False
    
    # Test 5: Invalid MongoDB ID
    sim = db.get_simulation("invalid_id_123")
    print(f"Test 5 (Invalid ID): Result={sim}")
    assert sim is None
    
    # Test 6: Normal flow still works
    email = "robust@test.com"
    pwd = "password123"
    # Clear if exists
    if db.use_mongo:
        db.users.delete_one({"email": email})
    
    res, msg = db.register_user(email, pwd)
    print(f"Test 6 (Normal Reg): Result={res}, Msg='{msg}'")
    assert res is True
    
    auth = db.authenticate_user(email, pwd)
    print(f"Test 7 (Normal Auth): Result={auth}")
    assert auth is True
    
    print("\nAll Robustness Tests Passed!")

if __name__ == "__main__":
    try:
        test_robustness()
    except Exception as e:
        print(f"Robustness Test Failed: {e}")
        import traceback
        traceback.print_exc()
