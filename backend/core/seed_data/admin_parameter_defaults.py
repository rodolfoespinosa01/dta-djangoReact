import copy
import json
from functools import lru_cache
from pathlib import Path


_SEED_DIR = Path(__file__).parent
_GLOBAL_FILE = _SEED_DIR / "admin_parameter_defaults_v1_global.json"
_STANDARD_FILE = _SEED_DIR / "admin_parameter_defaults_v1_standard.json"
_KETO_FILE = _SEED_DIR / "admin_parameter_defaults_v1_keto.json"
_CARB_CYCLING_FILE = _SEED_DIR / "admin_parameter_defaults_v1_carb_cycling.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_defaults_v1():
    global_payload = _load_json(_GLOBAL_FILE)
    standard_payload = _load_json(_STANDARD_FILE)
    keto_payload = _load_json(_KETO_FILE)
    carb_cycling_payload = _load_json(_CARB_CYCLING_FILE)

    defaults = global_payload["AdminParametersDefaults"]
    defaults["meal_plans"] = {
        "standard": standard_payload["meal_plans"]["standard"],
        "keto": keto_payload["meal_plans"]["keto"],
        "carb_cycling": carb_cycling_payload["meal_plans"]["carb_cycling"],
    }
    return defaults


def get_admin_parameter_defaults_v1():
    return copy.deepcopy(_load_defaults_v1())