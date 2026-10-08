"""
Simulacio horaria d'una bateria domestica (model simplificat de balanç
energetic, sense modelar la dinamica electroquimica en detall).

A cada pas, a mes del balanç d'energia, es marca si l'excedent/deficit
no s'ha pogut absorbir del tot per CAPACITAT (bateria plena/buida) o per
POTENCIA (el carregador/inversor no dona per mes, encara que hi hagi
marge de capacitat). Aquesta distincio es clau per saber si cal ampliar
kWh (capacitat) o kW (potencia) de la bateria.
"""
import math

import pandas as pd


class BatterySimulator:
    def __init__(self, capacity_kwh, max_charge_kw, max_discharge_kw,
                 round_trip_efficiency=0.9, min_soc_pct=10, max_soc_pct=100,
                 initial_soc_pct=50):
        values = {
            "capacity_kwh": capacity_kwh,
            "max_charge_kw": max_charge_kw,
            "max_discharge_kw": max_discharge_kw,
            "round_trip_efficiency": round_trip_efficiency,
            "min_soc_pct": min_soc_pct,
            "max_soc_pct": max_soc_pct,
            "initial_soc_pct": initial_soc_pct,
        }
        for name, value in values.items():
            try:
                values[name] = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} ha de ser un nombre finit") from exc
            if not math.isfinite(values[name]):
                raise ValueError(f"{name} ha de ser un nombre finit")

        if values["capacity_kwh"] < 0:
            raise ValueError("La capacitat de la bateria no pot ser negativa")
        if values["max_charge_kw"] < 0 or values["max_discharge_kw"] < 0:
            raise ValueError("Les potències de càrrega i descàrrega no poden ser negatives")
        if not 0 < values["round_trip_efficiency"] <= 1:
            raise ValueError("L'eficiència round trip ha de ser superior a 0 i com a màxim 1")
        for name in ("min_soc_pct", "max_soc_pct", "initial_soc_pct"):
            if not 0 <= values[name] <= 100:
                raise ValueError(f"{name} ha d'estar entre 0 i 100")
        if values["min_soc_pct"] > values["max_soc_pct"]:
            raise ValueError("El SOC mínim no pot superar el SOC màxim")
        if not values["min_soc_pct"] <= values["initial_soc_pct"] <= values["max_soc_pct"]:
            raise ValueError("El SOC inicial ha d'estar entre els límits mínim i màxim")

        self.capacity = values["capacity_kwh"]
        self.max_charge = values["max_charge_kw"]
        self.max_discharge = values["max_discharge_kw"]
        # arrel quadrada de l'eficiencia global aplicada a cada sentit (carrega i descarrega)
        self.eff = values["round_trip_efficiency"] ** 0.5
        self.min_soc = values["min_soc_pct"] / 100 * self.capacity
        self.max_soc = values["max_soc_pct"] / 100 * self.capacity
        self.soc = values["initial_soc_pct"] / 100 * self.capacity

    def step(self, surplus_kwh):
        try:
            surplus_kwh = float(surplus_kwh)
        except (TypeError, ValueError) as exc:
            raise ValueError("L'energia excedentària ha de ser un nombre finit") from exc
        if not math.isfinite(surplus_kwh):
            raise ValueError("L'energia excedentària ha de ser un nombre finit")

        grid_export = 0.0
        grid_import = 0.0
        battery_full = False
        battery_empty = False
        power_limited_charge = False
        power_limited_discharge = False

        if surplus_kwh >= 0:
            headroom = max(self.max_soc - self.soc, 0.0)
            # El límit de capacitat és energia que queda dins la bateria;
            # l'energia de càrrega necessària és headroom / eficiència.
            charge_possible = max(min(surplus_kwh, self.max_charge, headroom / self.eff), 0.0)
            self.soc += charge_possible * self.eff
            grid_export = surplus_kwh - charge_possible
            if grid_export > 1e-9:
                if headroom / self.eff <= self.max_charge:
                    battery_full = True
                else:
                    power_limited_charge = True
        else:
            deficit = -surplus_kwh
            available = max(self.soc - self.min_soc, 0.0)
            # La capacitat disponible limita l'energia lliurada després de les pèrdues.
            discharge_possible = max(min(deficit, self.max_discharge, available * self.eff), 0.0)
            self.soc -= discharge_possible / self.eff
            grid_import = deficit - discharge_possible
            if grid_import > 1e-9:
                if available * self.eff <= self.max_discharge:
                    battery_empty = True
                else:
                    power_limited_discharge = True

        self.soc = min(max(self.soc, self.min_soc), self.max_soc)

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
