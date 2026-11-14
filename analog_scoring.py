"""Transparent educational ranking of Earth locations by published features.

Scores are *feature evidence coverage* for a defined target, NOT measured
physical similarity to the Moon or Mars. Missing evidence counts as 0 and
must be presented as UNKNOWN, never as proof of absence.
"""

import json
from pathlib import Path

FEATURES = {
    "basalt": "Базальтові породи",
    "lava_flows": "Сліди лавових потоків",
    "ancient_water": "Свідчення давньої води / озера",
    "sediments": "Осадові відклади",
    "erosion": "Ерозійні форми рельєфу",
    "rugged": "Складний або нерівний рельєф",
}

TARGETS = {
    "mare_crisium": {
        "name": "Місяць · Море Криз (Mare Crisium)",
        "planet": "Місяць",
        "description": (
            "Базальтова місячна рівнина, заповнена давніми потоками лави. "
            "Критерії стосуються геології та окремих форм рельєфу, "
            "а не вакууму, температури чи гравітації."
        ),
        "source_url": "https://science.nasa.gov/resource/wrinkle-ridge-in-mare-crisium/",
        "weights": {"basalt": 5, "lava_flows": 4, "rugged": 1},
    },
    "jezero": {
        "name": "Марс · кратер Єзеро (Jezero), дельта",
        "planet": "Марс",
        "description": (
            "Давні озерні та річкові осади, сформовані водою, "
            "зі складними формами рельєфу. Це геологічна аналогія, "
            "а не порівняння сучасної атмосфери."
        ),
        "source_url": "https://science.nasa.gov/mission/mars-2020-perseverance/science-highlights/",
        "weights": {"ancient_water": 4, "sediments": 4, "erosion": 1, "rugged": 1},
    },
}

STATUS_SCORE = {"yes": 1.0, "partial": 0.5, "unknown": 0.0}


def load_evidence(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("База ознак має бути словником локацій")
    for location, features in data.items():
        if not isinstance(features, dict):
            raise ValueError(f"Некоректні ознаки {location}")
        for name, evidence in features.items():
            if name not in FEATURES:
                raise ValueError(f"Невідома ознака {name}")
            if evidence.get("status") not in STATUS_SCORE:
                raise ValueError(f"Некоректний статус {location}/{name}")
    return data


def score_analog(evidence: dict, weights: dict[str, int]) -> dict:
    """Compute a 0–100 coverage index and an auditable breakdown.

    `unknown` is lack of verified supporting evidence, NOT negative evidence.
    The denominator includes all positive weights (conservative comparison).
    """
    if any(key not in FEATURES for key in weights):
        raise ValueError("Невідома ознака в наборі критеріїв")
    if any(not isinstance(w, int) or not 0 <= w <= 5 for w in weights.values()):
        raise ValueError("Вага кожної ознаки має бути цілим числом 0–5")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Потрібна хоча б одна ознака з ненульовою вагою")

    raw = 0.0
    known_weight = 0
    unknown_count = 0
    criteria = []
    for feature, weight in weights.items():
        if weight == 0:
            continue
        item = evidence.get(feature, {})
        status = item.get("status", "unknown")
        if status not in STATUS_SCORE:
            raise ValueError(f"Невідомий статус доказів: {status}")
        contribution = weight * STATUS_SCORE[status]
        if status == "unknown":
            unknown_count += 1
        else:
            known_weight += weight
        raw += contribution
        criteria.append({
            "feature": feature,
            "weight": weight,
            "status": status,
            "note": item.get("note", "Для цієї ознаки у поточній базі немає перевіреного джерела."),
            "source_url": item.get("source_url", ""),
            "contribution": contribution,
        })
    return {
        "score": int(100 * raw / total + 0.5),  # conventional .5 rounds upward
        "raw": raw,
        "total": total,
        "known_weight": known_weight,
        "coverage": int(100 * known_weight / total + 0.5),
        "unknown_count": unknown_count,
        "criteria": criteria,
    }


def rank_analogs(sites: list[dict], evidence: dict, target_id: str,
                 weights: dict[str, int] | None = None) -> list[dict]:
    if target_id not in TARGETS:
        raise ValueError("Невідома планетарна ціль")
    weight_map = TARGETS[target_id]["weights"] if weights is None else weights
    results = []
    for site in sites:
        calculation = score_analog(evidence.get(site["id"], {}), weight_map)
        results.append({"site": site, "score": calculation["score"], "calculation": calculation})
    return sorted(results, key=lambda x: (-x["score"], x["site"]["name"]))
