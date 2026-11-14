# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Point lookup in the public Macrostrat map, with explicit missing/invalid states."""
from __future__ import annotations
from urllib.parse import urlencode
import math
import requests

ENDPOINT = 'https://macrostrat.org/api/v2/geologic_units/map'

class GeologyError(Exception):
    pass


def make_geology_url(latitude: float, longitude: float) -> str:
    latitude, longitude = float(latitude), float(longitude)
    if not all(map(math.isfinite, (latitude, longitude))) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise GeologyError('Некоректні координати для Macrostrat.')
    return ENDPOINT + '?' + urlencode({'lat': round(latitude, 5), 'lng': round(longitude, 5)})


def _extract_records(payload):
    """Recognize documented list, single-unit, nested, and GeoJSON layouts.

    An unsupported response is unavailable, not 'no geology'.
    """
    if not isinstance(payload, dict):
        return None
    records = payload.get('data')
    if records is None and payload.get('type') == 'FeatureCollection':
        records = payload.get('features', [])
    if records is None:
        return None
    for _ in range(5):
        if isinstance(records, list):
            return records
        if not isinstance(records, dict):
            return None
        if any(k in records for k in ('name', 'strat_name', 'map_id', 'lith', 'unit_id')):
            return [records]
        for key in ('results', 'features', 'units', 'records', 'data'):
            if key in records:
                records = records[key]
                break
        else:
            return None
    return None


def parse_geology(payload: dict, url: str) -> dict:
    if not isinstance(payload, dict):
        raise GeologyError('Macrostrat повернув неправильний формат даних.')
    if payload.get('error') or payload.get('errors'):
        raise GeologyError('Macrostrat повідомляє про помилку даних.')
    records = _extract_records(payload)
    if records is None:
        return {'status': 'unavailable', 'units': [], 'query_url': url,
                'source': ENDPOINT, 'note': 'Формат відповіді Macrostrat не вдалося інтерпретувати. Дані невідомі.'}
    units = []
    for r in records[:12]:
        if not isinstance(r, dict):
            continue
        if isinstance(r.get('properties'), dict):
            r = r['properties']
        units.append({
            'unit': r.get('name') or r.get('strat_name') or r.get('unit_name') or 'Без назви',
            'lithology': r.get('lith') or r.get('lithology'),
            'description': r.get('descrip') or r.get('description'),
            'age_top_ma': r.get('t_int_age'),
            'age_bottom_ma': r.get('b_int_age'),
            'age_name': r.get('t_int_name') or r.get('age'),
            'source_id': r.get('source_id'),
            'map_id': r.get('map_id'),
            'scale': r.get('scale'),
        })
    return {
        'status': 'ok' if units else 'no_coverage', 'units': units,
        'query_url': url, 'source': ENDPOINT,
        'note': ('Геологічні полігони карт; це не результати аналізу конкретного зразка.'
                 if units else 'У відповіді немає геологічних одиниць; це не доказ відсутності порід.'),
    }


def fetch_geology(latitude: float, longitude: float) -> dict:
    url = make_geology_url(latitude, longitude)
    try:
        r = requests.get(url, timeout=(8, 18), headers={'Accept': 'application/json'})
        if r.status_code != 200:
            raise GeologyError(f'Macrostrat повернув HTTP {r.status_code}.')
        return parse_geology(r.json(), url)
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise GeologyError('Не вдалося отримати геологічну карту Macrostrat. Дані не домислюємо.') from exc
