import sys
import os

# Mocking the environment for the test
os.environ['TWILIO_ACCOUNT_SID'] = 'mock_sid'
os.environ['TWILIO_AUTH_TOKEN'] = 'mock_token'
os.environ['TWILIO_PHONE_NUMBER'] = '+1234567890'

# Add project root to path
sys.path.append(os.getcwd())

from utils.sms_service import sms_service

def test_formatting():
    test_cases = [
        ("9381418345", "+919381418345"),
        ("919381418345", "+919381418345"),
        ("+919381418345", "+919381418345"),
        (" 93814 18345 ", "+919381418345"),
        ("+91 93814 18345", "+919381418345"),
        ("12345", "+9112345"), # Less than 10 digits
        ("1234567890123", "+1234567890123"), # More than 12 digits
    ]
    
    print("Running SMS Formatting Tests...")
    all_passed = True
    for input_val, expected in test_cases:
        result = sms_service.format_number(input_val)
        if result == expected:
            print(f"PASS: '{input_val}' -> '{result}'")
        else:
            print(f"FAIL: '{input_val}' -> Expected '{expected}', got '{result}'")
            all_passed = False
            
    if all_passed:
        print("\nAll tests passed! 🚀")
    else:
        print("\nSome tests failed. ⚠️")

if __name__ == "__main__":
    test_formatting()
