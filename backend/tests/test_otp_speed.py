import sys
import os
import time
import json
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import app

class TestOTPSpeed(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()

    def test_otp_request_speed(self):
        print("\nTesting /api/request_otp speed...")
        
        start_time = time.time()
        
        # Test with a dummy mobile number
        response = self.app.post('/api/request_otp', 
                                 data=json.dumps({'mobile': '1234567890'}),
                                 content_type='application/json')
        
        end_time = time.time()
        duration = end_time - start_time
        
        data = response.get_json()
        print(f"Response Time: {duration:.4f} seconds")
        print("Response Data:", data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        # The response should be very fast (usually < 0.1s) since it's async
        self.assertLess(duration, 0.5, f"OTP request took too long: {duration:.4f}s")
        self.assertIn("may take a few seconds", data['message'])

if __name__ == '__main__':
    unittest.main()
