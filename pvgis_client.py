"""
Client per obtenir series horaries de produccio fotovoltaica des de PVGIS
(Photovoltaic Geographical Information System - Comissio Europea, JRC).

Documentacio oficial de l'API "non-interactive":
https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en

Nota: aquesta funcio fa una crida HTTP real. Necessites connexio a internet
per executar-la. Si l'API canvia algun nom de parametre en el futur, revisa
la documentacio oficial (l'estructura general no sol variar gaire).
"""
import io
import requests
import pandas as pd

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def get_hourly_pv_production(location, pv_system, database="PVGIS-SARAH3"):
    """
    Retorna un DataFrame amb la produccio fotovoltaica horaria (kWh) per un any.

    location: dict amb 'lat', 'lon'
    pv_system: dict amb 'peak_power_kwp', 'tilt_deg', 'azimuth_deg',
               'system_loss_pct', 'technology', 'mounting', 'use_horizon'
    """
    params = {
        "lat": location["lat"],
        "lon": location["lon"],
        "raddatabase": database,
        "outputformat": "csv",
        "browser": 0,
        "pvcalculation": 1,
        "peakpower": pv_system["peak_power_kwp"],
        "loss": pv_system["system_loss_pct"],
        "angle": pv_system["tilt_deg"],
        "aspect": pv_system["azimuth_deg"],
        "pvtechchoice": pv_system.get("technology", "crystSi"),
        "mountingplace": pv_system.get("mounting", "building"),
        "usehorizon": 1 if pv_system.get("use_horizon", True) else 0,
    }

    r = requests.get(PVGIS_URL, params=params, timeout=60)
    r.raise_for_status()

    # El CSV de PVGIS porta metadades abans i despres de la taula de dades;
    # localitzem la linia de capçalera real ("time,P,...") i la linia buida
    # que marca el final del bloc de dades.
    lines = r.text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("time,"))
    end = next(i for i, l in enumerate(lines[start:], start) if l.strip() == "")
    csv_block = "\n".join(lines[start:end])

    df = pd.read_csv(io.StringIO(csv_block))
    df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
    df = df.rename(columns={"P": "ac_power_w"})
    # Resolucio horaria -> potencia mitjana (W) durant 1h equival a Wh d'energia
    df["pv_kwh"] = df["ac_power_w"] / 1000.0
    df = df.set_index("time")
    return df[["pv_kwh"]]
