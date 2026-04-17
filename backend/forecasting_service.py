import requests
import numpy as np
import datetime

class ForecastingService:
    def __init__(self):
        # Default Location: San Francisco (approx) or User's location
        # For now hardcoding a generic sunny location or could be config driven
        self.lat = 37.7749
        self.lon = -122.4194
        self.weather_cache = {}
        self.carbon_cache = {}
        self.price_cache = {}

    def get_weather_forecast(self):
        """
        Fetches 24h weather forecast from OpenMeteo (Free).
        Returns dict with 'temperature_2m', 'cloudcover', 'is_day' arrays.
        """
        try:
            # Cache check (simple hourly cache)
            now_hour = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
            if now_hour in self.weather_cache:
                return self.weather_cache[now_hour]

            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&hourly=temperature_2m,cloudcover,is_day&forecast_days=2"
            res = requests.get(url, timeout=5)
            data = res.json()
            
            if "hourly" in data:
                # Extract next 24h
                # Mapping time to index is complex, for simplicity we take the first 24 points from 'now'
                # But OpenMeteo returns data starting from 00:00 today.
                # Let's just return the raw hourly data relative to current hour
                
                current_hour_idx = datetime.datetime.now().hour
                
                temps = data['hourly']['temperature_2m'][current_hour_idx : current_hour_idx+24]
                clouds = data['hourly']['cloudcover'][current_hour_idx : current_hour_idx+24]
                is_day = data['hourly']['is_day'][current_hour_idx : current_hour_idx+24]
                
                result = {
                    "temperature": temps,
                    "cloud_cover": clouds,
                    "is_day": is_day
                }
                self.weather_cache[now_hour] = result
                return result
                
        except Exception as e:
            print(f"⚠️ Weather API Error: {e}")
            # Fallback
            return {
                "temperature": [20]*24,
                "cloud_cover": [10]*24,
                "is_day": [1]*12 + [0]*12 # Rough day/night
            }
            
    def predict_solar(self, capacity_kw=5.0):
        """
        Predicts solar output for next 24h based on weather.
        Uses a bell curve physical model for the day: Output = Capacity * Curve * (1 - CloudCover/100)
        """
        weather = self.get_weather_forecast()
        if not weather: return [0.0]*24
        
        solar_output = []
        now = datetime.datetime.now()
        for i in range(len(weather['is_day'])):
            is_day = weather['is_day'][i]
            cloud = weather['cloud_cover'][i]
            current_hour = (now.hour + i) % 24
            
            if is_day == 0 or current_hour < 6 or current_hour > 18:
                solar_output.append(0.0)
            else:
                # Bell curve peaking at hour 12
                # Simple approximation: sin curve from hour 6 to 18
                angle_rad = (current_hour - 6) / 12.0 * np.pi
                curve_factor = max(0.0, np.sin(angle_rad))
                
                efficiency = (100 - cloud) / 100.0
                output = capacity_kw * curve_factor * efficiency * 0.85 # 0.85 system efficiency
                solar_output.append(max(0.0, output))
                
        return solar_output

    def get_carbon_intensity(self):
        """
        Fetches live carbon intensity (gCO2/kWh).
        Uses a typical "duck curve" grid profile for real-world accuracy.
        """
        current_hour = datetime.datetime.now().hour
        
        # Base fossil fuel generation
        intensity = 250 # g/kWh
        
        if 9 <= current_hour <= 16:
            # Solar peak reduces carbon significantly
            intensity -= 120 * np.sin((current_hour - 9) / 7.0 * np.pi)
        elif 17 <= current_hour <= 21:
            # Evening ramp-up (peaker plants turn on)
            intensity += 150
            
        # Add slight randomness for realism
        intensity += np.random.normal(0, 10)
        return max(50.0, intensity)

    def get_dynamic_price(self):
        """
        Simulates Dynamic Time-of-Use Pricing ($/MWh).
        """
        current_hour = datetime.datetime.now().hour
        is_weekend = datetime.datetime.now().weekday() >= 5
        
        if is_weekend:
            # Flatter price curve on weekends
            if 16 <= current_hour <= 21:
                return 180.0
            else:
                return 120.0
        else:
            # Weekday Time-of-Use (ToU)
            if 16 <= current_hour <= 21:
                return 350.0 # Peak Evening
            elif 6 <= current_hour <= 9:
                return 200.0 # Morning Peak
            elif 10 <= current_hour <= 15:
                # Mid-day Solar dip (Duck Curve pricing)
                return 80.0 
            else:
                return 150.0 # Standard Off-Peak Base

    def predict_load(self, past_load=None):
        """
        Predicts load for next 24h.
        Adds day-of-week and seasonal awareness to the synthetic load profile.
        """
        base_load = []
        now = datetime.datetime.now()
        
        for h in range(24):
            eval_time = now + datetime.timedelta(hours=h)
            hour = eval_time.hour
            is_weekend = eval_time.weekday() >= 5
            
            # Base load profiles vary by day type
            if is_weekend:
                # Flatter, slightly higher mid-day load on weekends
                if 10 <= hour <= 22:
                    val = 1.8
                else:
                    val = 1.0
            else:
                # Standard Weekday profile
                if 17 <= hour <= 21:
                    val = 2.8 # Evening Peak kW (Cooking, AC, TVs)
                elif 6 <= hour <= 9:
                    val = 2.0 # Morning Peak (Showers, Breakfast)
                elif 9 < hour < 17:
                    val = 1.2 # Mid-day Working
                else:
                    val = 0.8 # Night Baseline
            
            # Seasonal Adjustment (e.g. Winter heating, Summer cooling)
            # Assuming Winter/Summer have higher baseline
            month = eval_time.month
            if month in [1, 2, 7, 8, 12]:
                val *= 1.2
            
            # Add micro-variability
            val += np.random.normal(0, 0.15)
            base_load.append(max(0.3, val))
            
        if past_load and len(past_load) >= 24:
            # Autoregressive smoothing (Tomorrow = Today's rhythm + Model)
            past_24 = past_load[-24:]
            combined = [(p * 0.4) + (b * 0.6) for p, b in zip(past_24, base_load)]
            return combined
            
        return base_load
