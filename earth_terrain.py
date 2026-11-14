"""Coarse local topographic proxy using Copernicus DEM GLO-90 via Open-Meteo.

Nine point samples at about 300 m from centre, not a landing-zone
survey and NOT equivalent to a slope map derived from full-resolution DEM.
"""
from __future__ import annotations
import math
import requests

ELEVATION_ENDPOINT = 'https://api.open-meteo.com/v1/elevation'
DOCS_URL = 'https://open-meteo.com/en/docs/elevation-api'


class TerrainError(Exception):
    pass


def sampling_grid(lat: float, lon: float, step_m: float = 300) -> list[tuple[float, float]]:
    lat = float(lat); lon = float(lon)
    if not (-89.5 <= lat <= 89.5 and -180 <= lon <= 180):
        raise TerrainError('Розрахунок локального ухилу не підтримується так близько до полюсів.')
    lat_step = step_m / 111_132
    lon_step = step_m / (111_320 * math.cos(math.radians(lat)))
    return [(lat + y * lat_step, ((lon + x * lon_step + 180) % 360) - 180)
            for y in (-1, 0, 1) for x in (-1, 0, 1)]


def describe_terrain(elevations: list[float], spacing_m: float = 300) -> dict:
    if len(elevations) != 9:
        raise TerrainError('Потрібні висоти дев’яти точок навколо центру.')
    try:
        z = [float(v) for v in elevations]
    except (ValueError, TypeError) as exc:
        raise TerrainError('Модель висот повернула порожні або некоректні значення.') from exc
    if any(not math.isfinite(v) or v < -12000 or v > 9000 for v in z):
        raise TerrainError('Модель висот повернула некоректні значення.')
    dzdx = (z[5] - z[3]) / (2.0 * spacing_m)
    dzdy = (z[7] - z[1]) / (2.0 * spacing_m)
    slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
    return {'elevation_m': round(z[4], 1), 'slope_deg': round(slope, 2),
            'relief_m': round(max(z) - min(z), 1), 'spacing_m': spacing_m,
            'data_source': DOCS_URL}


def fetch_terrain(lat: float, lon: float) -> dict:
    grid = sampling_grid(lat, lon)
    params = {
        'latitude': ','.join(f'{p[0]:.6f}' for p in grid),
        'longitude': ','.join(f'{p[1]:.6f}' for p in grid),
    }
    try:
        response = requests.get(ELEVATION_ENDPOINT, params=params, timeout=(8, 25))
        if response.status_code != 200:
            raise TerrainError(f'Модель висот повернула HTTP {response.status_code}.')
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('elevation'), list):
            raise TerrainError('Немає висот у відповіді сервісу.')
        return describe_terrain(payload['elevation'])
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise TerrainError('Не вдалося завантажити висоти Copernicus DEM. Спробуйте пізніше.') from exc
