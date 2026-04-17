import numpy as np
import random

class NeighborMicrogrid:
    def __init__(self, name="Neighbor A"):
        self.name = name
        # Neighbor has their own profile, usually slightly different from ours
        # We simulate this stochastically
        self.base_load = 1.0 # kW
        self.solar_capacity = 4.0 # kW

    def get_status(self, hour, weather_solar=0.0):
        """
        Returns neighbor's status: 'BUYING', 'SELLING', or 'IDLE'
        and the amount of energy they want to trade.
        """
        # Simulate neighbor load/solar
        # Load peak evening
        is_evening = 18 <= hour <= 21
        load = self.base_load * (2.0 if is_evening else 1.0) + random.uniform(-0.2, 0.2)
        
        # Solar is proportional to our weather but with some variance
        solar = weather_solar * (self.solar_capacity / 5.0) * random.uniform(0.8, 1.2) # normalized to 5kW base
        
        net = solar - load
        
        if net > 0.5:
            return "SELLING", net, 0.12 # Selling excess at cheaper rate than grid (e.g. $0.12)
        elif net < -0.5:
            return "BUYING", -net, 0.18 # Buying at premium (e.g. $0.18)
        else:
            return "IDLE", 0, 0

class EVFleet:
    def __init__(self, capacity_kwh=50.0):
        self.capacity = capacity_kwh
        self.soc = 50.0 # %
        self.connected = False
        self.target_soc = 90.0
        self.departure_hour = 8 # 8 AM
        self.arrival_hour = 18 # 6 PM

    def update(self, hour):
        # Simulate connection
        # Simple Logic: Connects at 6 PM, Leaves at 8 AM
        if self.arrival_hour <= hour <= 23 or 0 <= hour < self.departure_hour:
            self.connected = True
        else:
            self.connected = False
            # When away, use energy
            if hour == self.departure_hour:
             self.soc -= random.uniform(30, 40) # Drive drain
             self.soc = max(10.0, self.soc)

    def get_constraint(self, hour):
        """
        Returns (min_charge_needed, can_discharge)
        """
        if not self.connected:
            return 0.0, False
            
        # If near departure, must charge
        hours_left = (self.departure_hour - hour) % 24
        if hours_left == 0: hours_left = 24
        
        current_kwh = (self.soc / 100.0) * self.capacity
        target_kwh = (self.target_soc / 100.0) * self.capacity
        
        needed = max(0, target_kwh - current_kwh)
        
        # Panic charge if time is tight
        # Assuming max 7kW charger
        max_charge_rate = 7.0
        kw_needed_per_hour = needed / hours_left
        
        must_charge = kw_needed_per_hour
        
        # V2G Allowed if we have excess and plenty of time
        can_v2g = (self.soc > 60.0) and (hours_left > 4)
        
        return must_charge, can_v2g

    def charge(self, kw):
        if not self.connected: return 0.0
        # Limit by capacity
        current_kwh = (self.soc / 100.0) * self.capacity
        max_input = self.capacity - current_kwh
        energy = min(kw, max_input)
        
        new_kwh = current_kwh + energy
        self.soc = min(100.0, (new_kwh / self.capacity) * 100.0)
        return energy


    def discharge(self, kw):
        if not self.connected: return 0
        energy = kw
        
        current_kwh = (self.soc / 100.0) * self.capacity
        new_kwh = max(0, current_kwh - energy)
        self.soc = (new_kwh / self.capacity) * 100.0
        return energy
