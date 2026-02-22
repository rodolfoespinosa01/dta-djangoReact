import copy
import json
from functools import lru_cache
from pathlib import Path


_CONFIG_DIR = Path(__file__).parent
_GLOBAL_FILE = _CONFIG_DIR / "admin_parameter_defaults_v1_global.json"
_STANDARD_FILE = _CONFIG_DIR / "admin_parameter_defaults_v1_standard.json"
_KETO_FILE = _CONFIG_DIR / "admin_parameter_defaults_v1_keto.json"
_CARB_CYCLING_FILE = _CONFIG_DIR / "admin_parameter_defaults_v1_carb_cycling.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_defaults_v1():
    global_payload = _load_json(_GLOBAL_FILE)
    standard_payload = _load_json(_STANDARD_FILE)
    keto_payload = _load_json(_KETO_FILE)
    carb_cycling_payload = _load_json(_CARB_CYCLING_FILE)

    defaults = global_payload["AdminParametersDefaults"]
    defaults["meal_plans"] = {}
    defaults["meal_plans"]["standard"] = standard_payload["meal_plans"]["standard"]
    defaults["meal_plans"]["keto"] = keto_payload["meal_plans"]["keto"]
    defaults["meal_plans"]["carb_cycling"] = carb_cycling_payload["meal_plans"]["carb_cycling"]
    return defaults


def get_admin_parameter_defaults_v1():
    # Return a deep copy so callers can mutate safely without touching the template in memory.
    return copy.deepcopy(_load_defaults_v1())
