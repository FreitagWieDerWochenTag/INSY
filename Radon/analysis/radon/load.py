"""Load the raw CSV and give every column a short English name.

The export has one row per sensor message (irregular, ~10 min per radon sensor, 1 h for the weather);
columns that a message did not report are empty.
"""
import pandas as pd

from .paths import DATA

TZ = "Europe/Vienna"

# room key -> (English label, German name in the CSV)
ROOMS = {
    "office": ("Office", "Buero"),
    "kitchen": ("Kitchen", "Kueche"),
    "kitchen_floor": ("Kitchen (floor level)", "Kueche - Sockel"),
    "bedroom": ("Bedroom", "Schlafzimmer"),
    "utility": ("Utility room", "Technikraum"),
    "workshop": ("Workshop", "Werkstatt"),
    "living": ("Living room", "Wohnzimmer"),
}

# CSV column -> short name; radon and uptime columns are generated from ROOMS
CLIMATE = {
    "Kueche (Luft) – Luftdruck innen (hPa)": "kitchen_pressure",
    "Kueche (Luft) – Temperatur innen (°C)": "kitchen_temp",
    "Kueche (Luft) – CO₂ (ppm)": "kitchen_co2",
    "Kueche (Luft) – rel. Luftfeuchte (%)": "kitchen_humidity",
    "Schlafzimmer – Luftdruck innen (hPa)": "bedroom_pressure",
    "Schlafzimmer – Temperatur innen (°C)": "bedroom_temp",
    "Schlafzimmer – CO₂ (ppm)": "bedroom_co2",
    "Schlafzimmer – rel. Luftfeuchte (%)": "bedroom_humidity",
    "Wetter – Temperatur 2 m (°C)": "out_temp",
    "Wetter – Luftdruck (hPa)": "out_pressure",
    "Wetter – Wind 10 m (km/h)": "wind",
    "Wetter – Bodentemperatur 0 cm (°C)": "soil_temp_0",
    "Wetter – Bodentemperatur 6 cm (°C)": "soil_temp_6",
    "Wetter – Bodentemperatur 54 cm (°C)": "soil_temp_54",
}


def column_names() -> dict[str, str]:
    names = dict(CLIMATE)
    for key, (_, german) in ROOMS.items():
        names[f"{german} – Radon (Bq/m³)"] = f"{key}_radon"
        names[f"{german} – Betriebszeit (min)"] = f"{key}_uptime"
    return names


def load_raw(path=DATA) -> pd.DataFrame:
    """Raw readings, indexed by local time (Europe/Vienna), columns renamed. Unknown columns are dropped."""
    df = pd.read_csv(path, encoding="utf-8")
    time = pd.to_datetime(df["Zeit (UTC)"], format="ISO8601", utc=True).dt.tz_convert(TZ)
    names = column_names()
    df = df[[c for c in df.columns if c in names]].rename(columns=names)
    df.index = pd.DatetimeIndex(time, name="time")
    return df.sort_index()
