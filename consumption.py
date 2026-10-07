"""
Perfils de consum electric residencial.

Si no proporciones un CSV personalitzat, es genera un perfil horari sintetic
per tot l'any basat en corbes de carrega tipiques d'una llar espanyola
(doble punta mati/vespre, variacio setmana/cap de setmana, variacio
estacional per calefaccio/refrigeracio).

IMPORTANT: aquestes corbes son una aproximacio raonable, NO dades oficials
mesurades. Si vols precisio real, substitueix-les pel teu propi consum
horari (comptador intel.ligent, distribuidora, o "curvas de carga tipo"
publicades per REE) fent servir 'custom_csv' a config.py.
"""
import numpy as np
import pandas as pd

# Coeficient horari relatiu (forma tipica d'un dia laborable, 24 valors)
WEEKDAY_SHAPE = np.array([
    0.5, 0.4, 0.35, 0.3, 0.3, 0.35, 0.55, 0.8, 0.9, 0.8, 0.7, 0.65,
    0.7, 0.75, 0.7, 0.65, 0.7, 0.85, 1.1, 1.4, 1.6, 1.4, 1.0, 0.65,
])
WEEKEND_SHAPE = np.array([
    0.55, 0.45, 0.4, 0.35, 0.35, 0.4, 0.5, 0.65, 0.85, 0.95, 0.95, 0.9,
    0.95, 0.95, 0.85, 0.8, 0.8, 0.9, 1.1, 1.3, 1.45, 1.3, 1.0, 0.7,
])

# Factor estacional mensual (1 = mitjana anual; hivern amb calefaccio electrica > estiu)
MONTHLY_FACTOR = {
    1: 1.25, 2: 1.15, 3: 1.05, 4: 0.90, 5: 0.85, 6: 0.90,
    7: 1.00, 8: 0.95, 9: 0.85, 10: 0.90, 11: 1.05, 12: 1.20,
}


def default_hourly_consumption(annual_kwh, year=2023):
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    values = []
    for ts in idx:
        shape = WEEKDAY_SHAPE if ts.dayofweek < 5 else WEEKEND_SHAPE
        base = shape[ts.hour] * MONTHLY_FACTOR[ts.month]
        values.append(base)
    values = np.array(values)
    # normalitzem perque la suma total doni exactament l'objectiu anual
    values = values / values.sum() * annual_kwh
    return pd.DataFrame({"load_kwh": values}, index=idx)


def load_custom_consumption(csv_path):
    """
    Espera un CSV amb dues columnes: data/hora i consum en kWh, amb 8760
    (o 8784 en any de traspas) files horaries.
    """
    df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)
    df.columns = ["load_kwh"]
    return df
