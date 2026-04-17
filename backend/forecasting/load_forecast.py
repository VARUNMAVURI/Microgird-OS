import pandas as pd
import numpy as np

def forecast_load(csv_path, steps=24):
    df = pd.read_csv(csv_path)
    avg_load = np.mean(df["load_kW"].tail(24))
    return pd.Series([avg_load] * steps)
