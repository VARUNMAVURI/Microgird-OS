
import unittest
import json
import sys
import os

# Create a dummy database manager to avoid needing a real DB connection for this test if possible,
# or just rely on the existing one if it's SQLite (which it seems to be).
# For now, we will try to import the app directly.

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import app

class TestMicrogridAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True 
        # Create a test session
        with self.app.session_transaction() as sess:
            sess['user_email'] = "test@example.com"

    def test_1_start_simulation(self):
        print("\nTesting /api/simulation/start...")
        # First ensure we have data loaded. 
        # We can try to upload the default optimized_data.csv
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "optimized_data.csv")
        if os.path.exists(data_path):
            with open(data_path, 'rb') as f:
                response = self.app.post('/api/upload_data', data={'file': f}, content_type='multipart/form-data')
                print("Upload Response:", response.get_json())
                self.assertEqual(response.status_code, 200)

        response = self.app.post('/api/simulation/start', 
                                 data=json.dumps({'mode': 'AI'}),
                                 content_type='application/json')
        
        data = response.get_json()
        print("Start Response:", data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('initial_state', data)

    def test_2_step_simulation(self):
        print("\nTesting /api/simulation/step...")
        # Run a few steps
        contacted_server = False
        for i in range(5):
            response = self.app.post('/api/simulation/step', 
                                     data=json.dumps({'mode': 'AI'}),
                                     content_type='application/json')
            data = response.get_json()
            if i == 0:
                print("Step 1 Response:", data)
            
            self.assertEqual(response.status_code, 200)
            if 'error' in data:
                self.fail(f"Simulation Error: {data['error']}")
            
            contacted_server = True
            
        self.assertTrue(contacted_server)

if __name__ == '__main__':
    unittest.main()
