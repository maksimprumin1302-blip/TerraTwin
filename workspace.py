# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""One shared user-selected location, reused by all TerraTwin sections.

Pure functions are separated from Streamlit so state transitions can be tested
without a browser or connection to NASA.
"""
from __future__ import annotations
from site_agent import normalize_earth_point

DEFAULT_LOCATION = {'lat':25.5, 'lon':40.0, 'label':'Харрат-Хайбар (початковий приклад)', 'known_site':True, 'name_en':'Harrat Khaybar', 'name_uk':'Харрат-Хайбар'}


def ensure_location(state):
    if 'tt_active_point' not in state:
        state['tt_active_point'] = dict(DEFAULT_LOCATION)
    if 'tt_location_revision' not in state:
        state['tt_location_revision'] = 0
    return state['tt_active_point']


def set_location(state, lat, lon, label='Обрана точка'):
    latitude, longitude = normalize_earth_point(lat, lon)
    current = ensure_location(state)
    different = (current['lat'], current['lon']) != (latitude, longitude)
    if different:
        state['tt_active_point'] = {'lat': latitude, 'lon': longitude, 'label': str(label)[:100]}
    else:
        current['label'] = str(label)[:100]
    if different:
        state['tt_location_revision'] += 1
        # The previous analysis must not be displayed under newly selected coordinates.
        state.pop('tt_active_analysis', None)
    return different


def dataset_key(lat, lon, year):
    latitude, longitude = normalize_earth_point(lat, lon)
    return (latitude, longitude, int(year))


def analysis_for_active(state):
    point = ensure_location(state)
    analysis = state.get('tt_active_analysis')
    if analysis and analysis.get('key') == dataset_key(point['lat'], point['lon'], analysis.get('year')):
        return analysis
    return None
