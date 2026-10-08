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
    annual_kwh = float(annual_kwh)
    if not np.isfinite(annual_kwh) or annual_kwh < 0:
        raise ValueError("El consum anual ha de ser un valor finit no negatiu")
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
    try:
        df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"No s'ha pogut llegir el CSV de consum '{csv_path}': {exc}") from exc

    if len(df.columns) != 1:
        raise ValueError("El CSV de consum ha de tenir exactament dues columnes: data/hora i kWh")
    if not isinstance(df.index, pd.DatetimeIndex) or df.index.hasnans:
        raise ValueError("La primera columna del CSV ha de contenir dates i hores vàlides")

    try:
        values = pd.to_numeric(df.iloc[:, 0], errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("La columna de consum del CSV només pot contenir valors numèrics") from exc
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("El CSV de consum conté valors buits o no finits")
    if (values < 0).any():
        raise ValueError("El consum horari no pot ser negatiu")

    if df.index.tz is not None:
        raise ValueError("El CSV ha d'utilitzar hores locals sense zona horària ni canvis d'horari d'estiu")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("Les dates del CSV han d'estar ordenades i no poden repetir-se")
    expected_index = pd.date_range(
        f"{df.index[0].year}-01-01 00:00",
        f"{df.index[0].year}-12-31 23:00",
        freq="h",
    ) if len(df.index) else pd.DatetimeIndex([])
    if not df.index.equals(expected_index):
        raise ValueError(
            "El CSV ha de contenir totes les hores d'un any complet, des de l'1 de gener a les 00:00, "
            "en ordre i sense salts ni duplicats (8760 o 8784 files)"
        )

    return pd.DataFrame({"load_kwh": values.to_numpy()}, index=df.index)
