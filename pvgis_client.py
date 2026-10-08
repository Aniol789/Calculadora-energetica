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
import re
import requests
import numpy as np
import pandas as pd

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def get_hourly_pv_production(
    location, pv_system, database="PVGIS-SARAH3", target_hours=None, heating_setpoint_c=18.0
):
    """
    Retorna l'any complet més representatiu de producció FV i graus-hora de calefacció.

    location: dict amb 'lat', 'lon'
    pv_system: dict amb 'peak_power_kwp', 'tilt_deg', 'azimuth_deg',
               'system_loss_pct', 'technology', 'mounting', 'use_horizon'
    target_hours: opcional; limita la selecció a anys amb aquesta durada (p. ex. per CSV de traspàs).
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
    start = next((i for i, line in enumerate(lines) if line.strip().startswith("time,")), None)
    if start is None:
        raise ValueError("La resposta de PVGIS no conté la taula horària esperada (columna 'time')")

    data_lines = []
    for line in lines[start + 1:]:
        if re.match(r"^\d{8}:\d{4},", line.strip()):
            data_lines.append(line)
        elif data_lines:
            break
    if not data_lines:
        raise ValueError("PVGIS no ha retornat cap fila horària de producció")

    csv_block = "\n".join([lines[start], *data_lines])
    df = pd.read_csv(io.StringIO(csv_block))
    if not {"time", "P"}.issubset(df.columns):
        raise ValueError("La resposta de PVGIS no conté les columnes 'time' i 'P'")
    try:
        df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", errors="raise")
        df["P"] = pd.to_numeric(df["P"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("PVGIS ha retornat dates o valors de potència no vàlids") from exc
    if not np.isfinite(df["P"].to_numpy()).all() or (df["P"] < 0).any():
        raise ValueError("PVGIS ha retornat valors de potència negatius o no finits")
    df = df.rename(columns={"P": "ac_power_w"})
    # Resolucio horaria -> potencia mitjana (W) durant 1h equival a Wh d'energia
    df["pv_kwh"] = df["ac_power_w"] / 1000.0
    df = df.set_index("time")
    # PVGIS etiqueta les mitjanes horàries amb minuts diferents de zero (p. ex. :10).
    # El perfil de consum és horari, així que les alineem amb l'hora indicada.
    df.index = df.index.floor("h")
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        raise ValueError("Les hores retornades per PVGIS estan duplicades o desordenades")

    complete_years = []
    for year, year_data in df.groupby(df.index.year, sort=True):
        expected_index = pd.date_range(f"{year}-01-01 00:00", f"{year}-12-31 23:00", freq="h")
        if year_data.index.equals(expected_index):
            complete_years.append(year_data)
    if target_hours is not None:
        complete_years = [year_data for year_data in complete_years if len(year_data) == int(target_hours)]
    if not complete_years:
        suffix = f" amb {target_hours} hores" if target_hours is not None else ""
        raise ValueError(f"PVGIS no ha retornat cap any horari complet{suffix}")

    annual_yields = np.array([year_data["pv_kwh"].sum() for year_data in complete_years], dtype=float)
    median_yield = float(np.median(annual_yields))
    selected_index = int(np.argmin(np.abs(annual_yields - median_yield)))
    selected_columns = ["pv_kwh"]
    median_heating_degree_hours = None
    if "T2m" in df.columns:
        df["outdoor_temp_c"] = pd.to_numeric(df["T2m"], errors="coerce")
        if df["outdoor_temp_c"].isna().any() or not np.isfinite(df["outdoor_temp_c"].to_numpy()).all():
            raise ValueError("PVGIS ha retornat temperatures exteriors no vàlides")
        complete_years = [
            year_data.assign(outdoor_temp_c=df.loc[year_data.index, "outdoor_temp_c"])
            for year_data in complete_years
        ]
        heating_degree_hours = np.array([
            np.maximum(float(heating_setpoint_c) - year_data["outdoor_temp_c"], 0.0).sum()
            for year_data in complete_years
        ], dtype=float)
        median_heating_degree_hours = float(np.median(heating_degree_hours))
        pv_scale = max(float(np.median(np.abs(annual_yields - median_yield))), 1e-9)
        heating_scale = max(float(np.median(np.abs(heating_degree_hours - median_heating_degree_hours))), 1e-9)
        scores = ((annual_yields - median_yield) / pv_scale) ** 2
        scores += ((heating_degree_hours - median_heating_degree_hours) / heating_scale) ** 2
        selected_index = int(np.argmin(scores))
        selected_columns.append("outdoor_temp_c")
    selected = complete_years[selected_index][selected_columns].copy()
    selected.attrs["pvgis_reference_year"] = int(selected.index[0].year)
    selected.attrs["pvgis_complete_years"] = len(complete_years)
    selected.attrs["pvgis_median_annual_yield_kwh"] = median_yield
    selected.attrs["pvgis_median_heating_degree_hours"] = median_heating_degree_hours
    return selected
