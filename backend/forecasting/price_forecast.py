import pandas as pd
import numpy as np

def forecast_price(csv_path, steps=24):
    df = pd.read_csv(csv_path)
    avg_price = np.mean(df["price_per_MWh"].tail(24))
    return pd.Series([avg_price] * steps)
