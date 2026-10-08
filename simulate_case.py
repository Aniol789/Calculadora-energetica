import json
import sys
import types
from pathlib import Path


def build_runtime_config(case_data):
    runtime_config = types.ModuleType("config")
    for key in [
        "LOCATION",
        "PV_SYSTEM",
        "PVGIS_DATABASE",
        "CONSUMPTION",
        "THERMAL",
        "BATTERY",
        "ECONOMY",
        "LIFECYCLE",
        "OUTPUT",
    ]:
        if key in case_data:
            setattr(runtime_config, key, case_data[key])
    return runtime_config


def main():
    case_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cases/default_case.json")
    case_data = json.loads(case_path.read_text(encoding="utf-8"))
    runtime_config = build_runtime_config(case_data)
    sys.modules["config"] = runtime_config

    import simulate
    simulate.run()


if __name__ == "__main__":
    main()
