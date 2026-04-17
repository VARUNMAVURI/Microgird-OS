# Data Acquisition and Curation: Microgrid OS

6.2 Data Acquisition and Curation
A robust deep reinforcement learning model requires high-quality, diverse data. The methodology incorporates two primary dataset sources to train the specialist agents:

6.2.1 Solar Photovoltaic (PV) Generation Dataset
The solar forecasting and distribution model utilizes a multi-class dataset derived from regional irradiance telemetry (e.g., PVGIS or NREL), categorized by atmospheric conditions and generation yield:
1. High Yield (Sunny): Optimal brain-like "clear" scans of the energy environment showing peak generation.
2. Medium Yield (Cloudy): Intermittent generation patterns indicating the earliest signs of intermittent atmospheric decline.
3. Low Yield (Rainy/Overcast): Scans with noticeable power atrophy, particularly during heavy overcast periods.
4. Zero Yield (Nocturnal): Periods exhibiting severe solar shrinkage and no photovoltaic activity.

6.2.2 Residential Energy Load Dataset
The energy management and battery control model is trained on a binary and multi-class dataset of household electricity consumption:
1. Peak Demand: Scans of the load environment containing high-intensity consumption lesion patterns requiring immediate battery intervention.
2. Baseline Demand: Healthy resident scans with no signs of abnormal vascular electricity blockage or bleeding-edge spikes.
