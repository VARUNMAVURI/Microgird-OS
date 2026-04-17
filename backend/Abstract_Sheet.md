# Microgrid OS: Abstract Sheet

## 📝 Project Overview
**Title:** Microgrid Energy Management System using Deep Reinforcement Learning (DRL)  
**Objective:** To optimize energy distribution and minimize costs in a decentralized microgrid using autonomous AI agents that balance load, solar generation, and battery storage.

---

## 🧩 Modules Step-by-Step

### 1. Frontend Layer (User Interfaces)
- **Community Admin Dashboard:** Centralized command center for managing the entire microgrid, monitoring EV fleets, and running large-scale simulations.
- **Resident Portal:** Personalized interface for house owners to track their specific energy usage, solar contribution, and savings.
- **AI Advisor (Deep Intelligence):** A dynamic insights engine that translates complex simulation telemetry into actionable optimization strategies for the user.

### 2. Backend Intelligence Layer
- **Core API Engine (Flask):** Orchestrates data flow between the UI, database, and simulation modules.
- **Simulation Engine:** The "brain" of the system that executes chronological timesteps, applying real-world physical constraints and energy balance logic.
- **PPO AI Agent:** A Deep Reinforcement Learning core using the **Proximal Policy Optimization (PPO)** algorithm to learn and execute optimal battery strategies.
- **Forecasting Service:** Provides 24-hour lookahead predictions for Load demand, Solar irradiance, and Grid Carbon Intensity.

### 3. Physical & Economic Environment
- **BMS (Battery Management System):** Simulates real battery physics, including State of Charge (SOC) tracking and State of Health (SOH) degradation.
- **Energy Market (P2P & V2G):** Simulates peer-to-peer energy trading between neighbors and Vehicle-to-Grid stabilization from EV fleets.
- **Billing System:** Automated generation of professional electricity bills based on regional regulatory standards.

### 4. Data Persistence Layer
- **NoSQL Storage:** Uses **MongoDB** for high-performance tracking of simulation history and user records.
- **Local Fallback:** Robust **JSON-based** database system to ensure continuity when cloud databases are unavailable.

---

## 🛠️ Technologies & Techniques

- **Programming Languages:** Python (Backend Logic), JavaScript (Frontend Interactivity), HTML5/CSS3 (Theming).
- **AI/RL Stack:** PyTorch (Neural Networks), Stable Baselines 3 (PPO Framework), Pandas & NumPy (Mathematical Analysis).
- **Backend Framework:** Flask with Waitress (Production-grade WSGI server).
- **Data Visualization:** Chart.js (Real-time Power Curves), FontAwesome (Iconography).
- **Security:** CSRF Protection, Password Hashing, Session Management.
- **Techniques:** Proximal Policy Optimization (PPO), Time-Series Forecasting, Dynamic Load Shifting, Responsive Grid Design.

---

## 🤖 Algorithms Used

1.  **Proximal Policy Optimization (PPO):** An advanced Reinforcement Learning algorithm that ensures stable and efficient training of the AI agent for non-linear energy management.
2.  **Slab-Based Billing Algorithm:** Implements regional electricity board logic (e.g., APSPDCL) to calculate costs based on consumption tiers.
3.  **Battery Control Logic:** A hybrid of AI decisions and safe-guard rules to prevent overcharging and maximize battery lifespan.
4.  **Weather-Dynamic Forecasting:** Correlates cloud cover and temperature data to predict future solar generation.

---

## 📐 Core Formulas

### 1. Energy Balance Equation
Determines the net interaction with the utility grid:
`Grid_Net = (Load + Battery_Charging) - (Solar + Battery_Discharging + V2G_Discharge)`

### 2. SOC (State of Charge) Update
Calculates the remaining battery capacity:
`SOC_new = SOC_old + ((Energy_Stored * Efficiency) / Capacity) * 100`

### 3. SOH (State of Health) Degradation
Models long-term battery aging:
`SOH_loss = (Throughput_kWh * Cycle_Deg) + Calendar_Deg`

### 4. Economic Savings Formula
Calculates the ROI of the AI system:
`Total_Savings = Baseline_Grid_Cost - Actual_Net_Cost`
*Where `Actual_Net_Cost = (Grid_Import * Price) - (Grid_Export * Tariff) + Maintenance`*

### 5. Slab-Based Billing (APSPDCL Standard)
Used for professional bill generation:
- **0–50 Units:** ₹1.45 / unit
- **51–100 Units:** ₹2.60 / unit
- **101–200 Units:** ₹3.60 / unit
- **>200 Units:** ₹6.90 / unit

---

## 🚀 Significance
Microgrid OS bridge the gap between complex AI research and practical home automation. By utilizing high-fidelity simulation and professional billing standards, it provides a transparent, cost-effective, and sustainable energy future.
