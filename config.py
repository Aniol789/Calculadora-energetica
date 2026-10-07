"""
Configuracio de la simulacio d'una instal.lacio fotovoltaica.
Modifica aquests valors segons el cas que vulguis avaluar.
"""

# ---------------------------------------------------------------------------
# 1. UBICACIO
# ---------------------------------------------------------------------------
LOCATION = {
    "name": "Santa maria d'Oló", 
    "lat": 41.8745,       # graus, positiu = nord
    "lon": 2.0347,        # graus, positiu = est
    "altitude_m": 542,     # nomes informatiu (PVGIS ja incorpora el seu propi model d'elevacio)
    "climate": {
        "mean_annual_air_temp_c": 15.3,      # temperatura mitjana anual de l'aire
        "winter_design_temp_c": 3.0,         # temperatura de disseny hivernal
        "summer_design_temp_c": 29.0,        # temperatura de disseny estival
        "heating_degree_days_base_18": 1300, # graus-dia de calefacció (base 18°C)
        "cooling_degree_days_base_26": 120,  # graus-dia de refrigeració (base 26°C)
    },
    "ground": {
        "mean_ground_temp_c": 14.5,           # temperatura mitjana del sòl a poca profunditat
        "thermal_conductivity_w_mk": 2.2,     # conductivitat tèrmica del sòl (W/m·K)
        "thermal_diffusivity_m2_s": 1.1e-6,   # difusivitat tèrmica (m²/s)
        "groundwater_level_m": 5.0,           # nivell freàtic aproximat
        "borehole_spacing_m": 6.0,            # separació entre pous / tubs
        "rock_type": "granit",               # tipus de terreny, finalitat descriptiva
    },
}

# ---------------------------------------------------------------------------
# 2. SISTEMA FOTOVOLTAIC
# ---------------------------------------------------------------------------
PV_SYSTEM = {
    "peak_power_kwp": 5.0,       # potencia pic instal.lada (kWp)
    "tilt_deg": 30,               # inclinacio dels panells (0=horitzontal, 90=vertical)
    "azimuth_deg": 0,             # 0=sud, -90=est, 90=oest (conveni PVGIS)
    "system_loss_pct": 14,        # perdues del sistema (cablejat, inversor, brutícia, temperatura...)
    "technology": "crystSi",      # crystSi, CIS, CdTe...
    "mounting": "building",       # "free" (estructura lliure) o "building" (integrat a coberta)
    "use_horizon": True,          # tenir en compte obstacles de l'horitzo (muntanyes, edificis)
}

# ---------------------------------------------------------------------------
# 3. BASE DE DADES METEOROLOGICA DE PVGIS
# ---------------------------------------------------------------------------
# "PVGIS-SARAH3" -> Europa, Africa, gran part d'Asia (recomanat per Espanya/Catalunya)
# "PVGIS-ERA5"   -> cobertura global, millor per latituds altes / poca cobertura SARAH
PVGIS_DATABASE = "PVGIS-SARAH3"

# ---------------------------------------------------------------------------
# 4. CONSUM
# ---------------------------------------------------------------------------
CONSUMPTION = {
    "annual_kwh": 6000,                  # consum anual objectiu (kWh). Mitjana llar ES ~ 3000-4000 kWh
    "profile": "residential_default",    # "residential_default" o "custom_csv"
    "custom_csv_path": None,             # p.ex. "el_meu_consum_horari.csv" (columna data + kWh horaris)
}

# ---------------------------------------------------------------------------
# 5. DEMANDA TERMICA I FONTS DE CALOR/FRED
# ---------------------------------------------------------------------------
THERMAL = {
    "enabled": True,
    "annual_heat_demand_kwh": 10000.0,
    "active_source": "aerotermia",
    "peak_power_kw": 8.0,
    "analysis_years": 20,
    "heating_setpoint_c": 22.0,                # temperatura de consigna a l'interior a l'hivern
    "ground_loop_target_temp_c": 8.0,         # temperatura de treball del circuit de terra
    "borehole_diameter_m": 0.12,              # diàmetre de la sonda geotèrmica
    "groundwater_level_m": 5.0,              # nivell freàtic estimat; útil per a criteris geològics
    "payback_reference": "gas_natural",
    "sources": [
        "gas_natural",
        "gasoil",
        "aerotermia",
        "geotermia",
        "biomassa",
        "electricitat_resistencia",
    ],
    "weights": {"cost": 0.34, "environment": 0.33, "energy": 0.33},
    "source_overrides": {
        # Exemple: "gas_natural": {"resource_price_eur_per_kwh": 0.09}
    },
}

# ---------------------------------------------------------------------------
# 6. BATERIA (opcional)
# ---------------------------------------------------------------------------
BATTERY = {
    "enabled": True, 
    "capacity_kwh": 3.0,
    "max_charge_kw": 3.0,
    "max_discharge_kw": 3.0,
    "round_trip_efficiency": 0.90,   # eficiencia global carrega+descarrega
    "min_soc_pct": 10,                # % minim d'estat de carrega (proteccio bateria)
    "max_soc_pct": 100,
    "initial_soc_pct": 50,
}

# ---------------------------------------------------------------------------
# 7. ECONOMIA
# ---------------------------------------------------------------------------
ECONOMY = {
    "pv_cost_per_kw": 850.0,                       # €/kWp instal.lat
    "battery_cost_per_kwh": 280.0,                # €/kWh de capacitat
    "battery_cost_per_kw": 120.0,                 # €/kW de potència de bateries
    "installation_extra_pct": 0.12,               # cost addicional (BOS, inversors, obra, permisos)
    "annual_om_pct": 0.015,                       # manteniment anual (% del CAPEX)
    "electricity_buy_price_eur_kwh": 0.22,        # preu mitja de compra de la llum
    "electricity_sell_price_eur_kwh": 0.09,       # preu mitja de venda de l'excedent
    "annual_inflation_pct": 0.02,                 # inflacio anual aplicada al valor de l'energia
    "discount_rate_pct": 0.04,                    # taxa de descompte per VAN
    "project_life_years": 25,                     # anys d'analisi
}

# ---------------------------------------------------------------------------
# 8. VIDA ÚTIL, DEGRADACIÓ I IMPACTE AMBIENTAL
# ---------------------------------------------------------------------------
LIFECYCLE = {
    "panel_degradation_pct_per_year": 0.004,          # 0.4% anual de pèrdua d'eficiència
    "panel_life_years": 25,
    "battery_life_years": 10,
    "inverter_life_years": 12,
    "inverter_cost_per_kw": 180.0,                    # €/kW de potència nominal
    "pv_embodied_co2_kg_per_kwp": 340.0,             # kg CO2eq per kWp instal·lat
    "battery_embodied_co2_kg_per_kwh": 80.0,          # kg CO2eq per kWh de capacitat
    "inverter_embodied_co2_kg_per_kw": 40.0,          # kg CO2eq per kW d'inversor
    "grid_emission_factor_kg_co2_per_kwh": 0.18,     # factor mitjà de la xarxa
}

# ---------------------------------------------------------------------------
# 9. SORTIDA
# ---------------------------------------------------------------------------
OUTPUT = {
    "save_hourly_csv": True,
    "hourly_csv_path": "resultats_horaris.csv",
    "make_plots": True,
    "make_report": True,
    "report_archive_dir": "informes_historic",
    "open_report_in_browser": True,
}
