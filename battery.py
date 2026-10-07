"""
Simulacio horaria d'una bateria domestica (model simplificat de balanç
energetic, sense modelar la dinamica electroquimica en detall).

A cada pas, a mes del balanç d'energia, es marca si l'excedent/deficit
no s'ha pogut absorbir del tot per CAPACITAT (bateria plena/buida) o per
POTENCIA (el carregador/inversor no dona per mes, encara que hi hagi
marge de capacitat). Aquesta distincio es clau per saber si cal ampliar
kWh (capacitat) o kW (potencia) de la bateria.
"""
import pandas as pd


class BatterySimulator:
    def __init__(self, capacity_kwh, max_charge_kw, max_discharge_kw,
                 round_trip_efficiency=0.9, min_soc_pct=10, max_soc_pct=100,
                 initial_soc_pct=50):
        self.capacity = capacity_kwh
        self.max_charge = max_charge_kw
        self.max_discharge = max_discharge_kw
        # arrel quadrada de l'eficiencia global aplicada a cada sentit (carrega i descarrega)
        self.eff = round_trip_efficiency ** 0.5
        self.min_soc = min_soc_pct / 100 * capacity_kwh
        self.max_soc = max_soc_pct / 100 * capacity_kwh
        self.soc = initial_soc_pct / 100 * capacity_kwh

    def step(self, surplus_kwh):
        grid_export = 0.0
        grid_import = 0.0
        battery_full = False
        battery_empty = False
        power_limited_charge = False
        power_limited_discharge = False

        if surplus_kwh >= 0:
            headroom = max(self.max_soc - self.soc, 0.0)
            charge_possible = max(min(surplus_kwh, self.max_charge, headroom), 0.0)
            self.soc += charge_possible * self.eff
            grid_export = surplus_kwh - charge_possible
            if grid_export > 1e-9:
                # si el marge de capacitat era mes petit que la potencia, el que limita es la capacitat
                if headroom <= self.max_charge:
                    battery_full = True
                else:
                    power_limited_charge = True
        else:
            deficit = -surplus_kwh
            available = max(self.soc - self.min_soc, 0.0)
            discharge_possible = max(min(deficit, self.max_discharge, available), 0.0)
            self.soc -= discharge_possible / self.eff
            grid_import = deficit - discharge_possible
            if grid_import > 1e-9:
                if available <= self.max_discharge:
                    battery_empty = True
                else:
                    power_limited_discharge = True

        soc_pct = (self.soc / self.capacity * 100) if self.capacity else 0.0

        return {
            "grid_export_kwh": grid_export,
            "grid_import_kwh": grid_import,
            "battery_soc_kwh": self.soc,
            "battery_soc_pct": soc_pct,
            "battery_full": battery_full,
            "battery_empty": battery_empty,
            "limited_by_power_charge": power_limited_charge,
            "limited_by_power_discharge": power_limited_discharge,
        }


def simulate_battery_series(surplus_series, battery_config):
    bat = BatterySimulator(
        capacity_kwh=battery_config["capacity_kwh"],
        max_charge_kw=battery_config["max_charge_kw"],
        max_discharge_kw=battery_config["max_discharge_kw"],
        round_trip_efficiency=battery_config["round_trip_efficiency"],
        min_soc_pct=battery_config["min_soc_pct"],
        max_soc_pct=battery_config["max_soc_pct"],
        initial_soc_pct=battery_config["initial_soc_pct"],
    )
    rows = [bat.step(v) for v in surplus_series]
    return pd.DataFrame(rows, index=surplus_series.index)
