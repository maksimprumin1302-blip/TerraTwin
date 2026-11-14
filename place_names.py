# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""One-click locality lookup for a point picked by the user.

Public OpenStreetMap Nominatim is used ONLY for an explicit point selection,
not map panning or systematic queries. Strict global 1 req/s, descriptive UA,
30-day persistent Streamlit cache at callsite, configurable endpoint for migration.
No reverse service can promise an address for every coordinate (e.g. oceans).
"""
from __future__ import annotations
import os
import threading
import time
from typing import Any
import requests

_ENDPOINT = os.environ.get('TERRATWIN_REVERSE_URL', 'https://nominatim.openstreetmap.org/reverse')
_GUARD = threading.Lock()
_LAST_CALL = 0.0
_USER_AGENT = 'TerraTwin-Research-Explorer/2.1 (educational Earth analog Streamlit desktop application)'  # descriptive app UA


def format_place(address: dict[str, Any], language: str='en') -> str | None:
    if not isinstance(address, dict):
        return None
    locality = next((str(address[k]) for k in (
        'city','town','village','municipality','hamlet','county','state_district')
        if address.get(k)), None)
    region = next((str(address[k]) for k in ('state','province','region') if address.get(k)), None)
    country = str(address.get('country') or '').strip()
    parts=[]
    for val in (locality, region, country):
        if val and val.lower() not in [v.lower() for v in parts]:
            parts.append(val)
    return ', '.join(parts[:3]) or None


def resolve_point_name(lat:float, lon:float, language='en', requester=requests.get) -> str | None:
    """Return nearby municipality/district/region, or None on no coverage/error.

    Never invent an administrative name; reverse search is an APPROXIMATE nearby
    feature, not a statement that a precise point falls inside its boundaries.
    """
    global _LAST_CALL
    if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        raise ValueError('Invalid Earth coordinates')
    if language not in ('en','uk'):
        raise ValueError('Language must be en or uk')
    # Enforces the public Nominatim usage limit even if two threads request at once.
    try:
        with _GUARD:
            delay = max(0, 1.05-(time.monotonic()-_LAST_CALL)) if _LAST_CALL else 0
            if delay:
                time.sleep(delay)
            _LAST_CALL=time.monotonic()
            resp=requester(_ENDPOINT, params={
                'lat':f'{lat:.4f}', 'lon':f'{lon:.4f}',
                'format':'jsonv2', 'addressdetails':1, 'zoom':10,
                'accept-language':language,
            }, headers={'User-Agent': _USER_AGENT,'Accept-Language':language},timeout=8)
        resp.raise_for_status()
        payload=resp.json()
        if not isinstance(payload, dict) or payload.get('error'):
            return None
        return format_place(payload.get('address') or {}, language)
    except (requests.RequestException, ValueError, TypeError):
        return None


def display_point(point: dict, lang='en') -> str:
    """Prefer selected site's bilingual name or reverse-geocoded locality."""
    if point.get('known_site'):
        return point.get('name_en' if lang=='en' else 'name_uk') or point['label']
    return point.get('place_'+lang) or point.get('place_en') or point.get('place_uk') or point['label']
