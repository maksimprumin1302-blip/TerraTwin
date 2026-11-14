# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Reproducible climate-proxy screening agent for arbitrary Earth coordinates.

This is intentionally NOT a physical Mars/Moon similarity model. NASA POWER
only supplies Earth meteorology. It can't establish minerals, actual regolith,
volcanism, dust composition, water ice, slopes, vacuum or radiation.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from nasa_power import LABELS


def clamp(x: float) -> float:
    return max(0.0,min(1.0,x))


def normalize_earth_point(lat: float, lon: float) -> tuple[float,float]:
    lat = float(lat); lon = float(lon)
    if not math.isfinite(lat) or not math.isfinite(lon) or not -89.9 <= lat <= 89.9:
        raise ValueError('Широта має бути між −89,9° та 89,9°.')
    lon = ((lon + 180.0) % 360.0) - 180.0
    return round(lat, 4), round(lon, 4)


def nearby_site(lat: float, lon: float, sites: list[dict], radius_km: float = 30) -> dict | None:
    """Only match a curated geological site within a small radius, never globally infer geology."""
    latr=math.radians(lat)
    for site in sites:
        lat2=math.radians(site['latitude'])
        lon_delta=math.radians(((lon-site['longitude']+180)%360)-180)
        a=math.sin((lat2-latr)/2)**2+math.cos(latr)*math.cos(lat2)*math.sin(lon_delta/2)**2
        dist=6371*2*math.asin(min(1,math.sqrt(a)))
        if dist<=radius_km:
            return site
    return None


def _coverage_window(daily: pd.DataFrame) -> tuple[int, int]:
    """Calendar-day denominator for annual NASA POWER summaries.

    If a synthetic dataset has no dates, treat it as one non-leap year.
    Duplicates must never increase completeness.
    """
    if 'Дата' not in daily:
        return len(daily), 365
    dates = pd.to_datetime(daily['Дата'], errors='coerce')
    years = dates.dropna().dt.year.unique()
    if len(years) != 1:
        return 0, 365
    year = int(years[0])
    expected = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
    return int(dates.dropna().dt.normalize().nunique()), expected


def valid_mean(df: pd.DataFrame, column: str, completeness: float = .90) -> float | None:
    if column not in df or len(df) == 0:
        return None
    observed_days, expected = _coverage_window(df)
    s = pd.to_numeric(df[column], errors='coerce').replace([float('inf'), float('-inf')], float('nan'))
    if 'Дата' in df:
        dates = pd.to_datetime(df['Дата'], errors='coerce')
        valid_days = int(dates[s.notna()].dt.normalize().nunique())
    else:
        valid_days = min(int(s.notna().sum()), observed_days)
    if valid_days < expected * completeness:
        return None
    return float(s.dropna().mean()) if s.notna().any() else None


def weather_features(daily: pd.DataFrame) -> dict:
    """Use calendar completeness, not simply percentage of returned rows.

    A truncated year cannot give an annual rainfall total or an annual
    climate score. Missing measurements are never treated as zero.
    """
    tempcol = LABELS['T2M']
    raincol = LABELS['PRECTOTCORR']
    windcol = LABELS['WS10M']
    t = valid_mean(daily, tempcol)
    w = valid_mean(daily, windcol)
    rain = None
    if raincol in daily and len(daily) > 0:
        vals = pd.to_numeric(daily[raincol], errors='coerce').replace([float('inf'), float('-inf')], float('nan'))
        if 'Дата' in daily:
            dates = pd.to_datetime(daily['Дата'], errors='coerce')
            years = dates.dropna().dt.year.unique()
            valid_days = int(dates[vals.notna()].dt.normalize().nunique()) if len(years) == 1 else 0
        else:
            valid_days = int(vals.notna().sum())
        _, expected = _coverage_window(daily)
        if valid_days >= expected * .95:
            rain = float(vals.sum())
    spread = None
    if t is not None:
        vals = pd.to_numeric(daily[tempcol], errors='coerce').dropna()
        spread = float(vals.quantile(.90) - vals.quantile(.10))
    observed, expected = _coverage_window(daily)
    return {'temperature': t, 'rain': rain, 'wind': w, 'temp_range': spread,
            'days': observed, 'expected_days': expected,
            'calendar_coverage': round(100 * observed / expected, 1)}


def _score(components: list[tuple[str,float,float | None]]) -> dict:
    """Returns score only when >=60% of weighted evidence is available."""
    full_weight = sum(weight for _,weight,_ in components)
    present = [(name,weight,value) for name,weight,value in components if value is not None]
    covered = sum(w for _,w,_ in present)
    coverage = int(round(covered/full_weight*100)) if full_weight else 0
    score = (int(round(100*sum(weight*value for _,weight,value in present)/covered))
             if covered and coverage >= 60 else None)
    return {'score':score,'coverage':coverage,
            'parts':[{'name':name,'weight':weight,'value':None if value is None else round(value*100)}
                     for name,weight,value in components]}


def analyze_climate(daily: pd.DataFrame) -> dict:
    """Screen Earth field-test conditions by explicit, illustrative proxy weights.

    Not validated planetary similarity. Denominators use available metrics only
    when at least 60% of total weight is available, with coverage surfaced.
    """
    f = weather_features(daily)
    dry = clamp((800-f['rain'])/800) if f['rain'] is not None else None
    cold = clamp((10-f['temperature'])/30) if f['temperature'] is not None else None
    windy = clamp(f['wind']/8) if f['wind'] is not None else None
    range_ = clamp(f['temp_range']/30) if f['temp_range'] is not None else None
    mars = _score([('Посушливість',.45,dry),('Холодні умови',.35,cold),('Вітер',.20,windy)])
    moon = _score([('Посушливість',.60,dry),('Річна мінливість температури',.40,range_)])
    conclusions = []
    if f['rain'] is not None:
        if f['rain'] < 250:
            conclusions.append('Мала кількість опадів може бути корисною для випробувань техніки у сухому середовищі.')
        else:
            conclusions.append('Опади суттєві: місцевість не є виражено посушливим наземним аналогом.')
    if f['temperature'] is not None:
        if f['temperature'] < 0:
            conclusions.append('Холодний клімат дає можливість випробовувати роботу обладнання за низьких температур.')
        elif f['temperature'] > 20:
            conclusions.append('Клімат відносно теплий, тому середні температури не є марсіанським температурним аналогом.')
    if f['wind'] is not None and f['wind'] >= 5:
        conclusions.append('Підвищені земні вітри корисні для випробування пилозахисту; силу марсіанського вітру напряму не відтворюють.')
    conclusions.append('Геологія, схили, льодові ресурси, радіація та склад ґрунту тут НЕ оцінені: потрібні окремі дані.')
    return {'features':f,'moon':moon,'mars':mars,'conclusions':conclusions,
            'method':{'dryness':'max(0,min(1,(800 − річні опади)/800))',
                      'cold':'max(0,min(1,(10 − середня температура)/30))',
                      'wind':'max(0,min(1, середній вітер/8))',
                      'range':'max(0,min(1, (P90 температури − P10 температури)/30))'}}
