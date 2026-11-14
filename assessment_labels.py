"""Interpretable heuristic ratings that never confuse test usefulness with planetary fidelity.

Thresholds are project-defined presentation bands, NOT validated NASA thresholds.
Coverage always qualifies scores; missing critical evidence prevents an endorsement.
"""
from __future__ import annotations

BANDS = ((40, 'poor'), (60, 'limited'), (75, 'conditional'), (90, 'good'), (101, 'strong'))

LABELS = {
    'uk': {
        'insufficient': ('Недостатньо даних', 'Недостатньо перевірених показників для висновку. Це не означає, що територія непридатна.'),
        'preliminary': ('Попередня оцінка — потрібно більше даних', 'Частина критеріїв відсутня або є критичні прогалини. Поки не можна рекомендувати територію.'),
        'poor': ('Не рекомендується для цих випробувань', 'Низька відповідність обраним умовам земних випробувань.'),
        'limited': ('Низька придатність', 'Територія має окремі корисні властивості, але загальний результат слабкий.'),
        'conditional': ('Може підійти для окремих випробувань', 'Є перспективні характеристики; перед практичним використанням потрібна перевірка на місці.'),
        'good': ('Добрий земний аналог для обраних випробувань', 'Висока відповідність авторським критеріям за умови підтвердження на місці.'),
        'strong': ('Дуже перспективний земний аналог', 'Дуже високий індекс корисності за заданими критеріями; це не фізична схожість із планетою.'),
    },
    'en': {
        'insufficient': ('Insufficient evidence', 'Not enough verified criteria for a conclusion. This does not mean the site is unsuitable.'),
        'preliminary': ('Preliminary — more evidence required', 'Data coverage or key evidence is incomplete; the site should not yet be recommended.'),
        'poor': ('Not recommended for these tests', 'Low alignment with the selected Earth field-testing criteria.'),
        'limited': ('Low suitability', 'Some conditions may be useful, but the overall field-test index is weak.'),
        'conditional': ('Conditionally useful for selected tests', 'Promising conditions, but local ground verification is required.'),
        'good': ('Good Earth analog for selected tests', 'High alignment with the defined testing criteria, pending field validation.'),
        'strong': ('Very promising Earth analog', 'High Earth-testing usefulness under the chosen weights; not physical planetary similarity.'),
    },
}


def _band(score: int) -> str:
    if not 0 <= score <= 100:
        raise ValueError('Score must be between 0 and 100.')
    return next(name for upper, name in BANDS if score < upper)


def classify_base(score: int | None, coverage: int, criteria: list[dict], lang='uk') -> dict:
    """Classify an Earth field-testing *screen*, not a Moon/Mars base site.

    Critical unknowns in materials or ice require a preliminary label whenever
    the target assigns either criterion a positive weight. This is deliberately
    conservative even if the normalized score from other criteria is high.
    """
    if lang not in LABELS:
        raise ValueError('Unknown language')
    if not 0 <= coverage <= 100:
        raise ValueError('Invalid coverage')
    missing = [r['key'] for r in criteria if r.get('weight',0)>0 and r.get('score') is None]
    critical = [key for key in ('materials','ice') if key in missing]
    low_confidence = [r['key'] for r in criteria if r.get('weight',0)>0 and r.get('score') is not None
                      and 'Estimated ' in r.get('evidence_type','')]

    if score is None or coverage < 60:
        category = 'insufficient'
    elif coverage < 85 or critical or low_confidence:
        category = 'preliminary'
    else:
        category = _band(int(score))
    title, detail = LABELS[lang][category]
    return {'category':category, 'title':title, 'description':detail,
            'critical_missing':critical, 'low_confidence':low_confidence, 'potential_band':_band(int(score)) if score is not None else None,
            'missing':missing, 'coverage':coverage, 'score':score,
            'qualified':category not in ('insufficient','preliminary')}


def classify_analog(score: int | None, coverage: int, lang='uk') -> dict:
    """Geological feature-evidence band; never claim physical planetary match."""
    if lang not in LABELS:
        raise ValueError('Unknown language')
    if score is None or coverage < 60:
        category='insufficient'
    elif coverage < 85:
        category='preliminary'
    else:
        category=_band(int(score))
    title, detail=LABELS[lang][category]
    return {'category':category,'title':title,'description':detail,'coverage':coverage,
            'disclaimer':('Висновок стосується лише наявності підтверджених геологічних ознак, не фізичної подібності планет.' if lang=='uk'
                          else 'This rating concerns geological feature evidence only, not physical planetary similarity.')}
