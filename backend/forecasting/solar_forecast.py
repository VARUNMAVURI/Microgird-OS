import pandas as pd
import numpy as np

def forecast_solar(csv_path, steps=24):
    df = pd.read_csv(csv_path)
    avg_solar = np.mean(df["solar_kW"].tail(24))
    return pd.Series([max(avg_solar, 0)] * steps)
