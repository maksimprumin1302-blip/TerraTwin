"""Source-aware gridded ERA5 fallback. No source data are fabricated.

Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
ERA5/ERA5-Land are reanalysis (model-informed gridded estimates), NOT in situ
measurements. Soil temperatures are NOT ground-ice observations.
"""
from __future__ import annotations
from urllib.parse import urlencode
import math
import pandas as pd
import requests
from nasa_power import LABELS

ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
DOC_URL = 'https://open-meteo.com/en/docs/historical-weather-api'
SOIL_KEYS = ('soil_temperature_0_to_7cm_mean', 'soil_temperature_7_to_28cm_mean',
             'soil_temperature_28_to_100cm_mean', 'soil_moisture_0_to_7cm_mean')
DAILY_KEYS = ('temperature_2m_mean', 'temperature_2m_min', 'temperature_2m_max',
              'precipitation_sum', 'wind_speed_10m_mean', 'shortwave_radiation_sum') + SOIL_KEYS

class ArchiveError(Exception):
    pass


def make_archive_url(lat:float, lon:float, year:int) -> str:
    lat,lon = float(lat),float(lon)
    if not all(math.isfinite(x) for x in (lat,lon)) or not (-89.9 <= lat <= 89.9 and -180 <= lon <= 180):
        raise ArchiveError('Invalid Earth coordinates.')
    if not 1981 <= int(year) <= 2025:
        raise ArchiveError('Select a complete year from 1981 to 2025.')
    return ARCHIVE_URL+'?'+urlencode({
        'latitude':f'{lat:.4f}', 'longitude':f'{lon:.4f}',
        'start_date':f'{year}-01-01','end_date':f'{year}-12-31',
        'daily':','.join(DAILY_KEYS), 'timezone':'GMT',
        'wind_speed_unit':'ms', 'temperature_unit':'celsius',
        'precipitation_unit':'mm',
    },safe=',')


def parse_archive(payload:dict) -> pd.DataFrame:
    if not isinstance(payload,dict) or not isinstance(payload.get('daily'),dict):
        raise ArchiveError('Open-Meteo returned no daily data.')
    daily = payload['daily']; dates=daily.get('time')
    if not isinstance(dates,list) or not dates:
        raise ArchiveError('Open-Meteo did not return a date series.')
    df=pd.DataFrame({'Дата':pd.to_datetime(dates, errors='coerce')})
    rename={
        'temperature_2m_mean': LABELS['T2M'],
        'temperature_2m_min': LABELS['T2M_MIN'],
        'temperature_2m_max': LABELS['T2M_MAX'],
        'precipitation_sum':LABELS['PRECTOTCORR'],
        'wind_speed_10m_mean':LABELS['WS10M'],
        'shortwave_radiation_sum':LABELS['ALLSKY_SFC_SW_DWN'],
    }
    for key in DAILY_KEYS:
        values=daily.get(key)
        if values is None:
            df[rename.get(key,key)]=float('nan');continue
        if not isinstance(values,list) or len(values)!=len(dates):
            raise ArchiveError('Inconsistent daily response length from Open-Meteo.')
        numeric=pd.to_numeric(pd.Series(values),errors='coerce')
        numeric=numeric.where(numeric.between(-1e5,1e5))
        if key == 'shortwave_radiation_sum':
            # API supplies MJ/m²/day; TerraTwin solar units are kWh/m²/day.
            numeric=numeric/3.6
        df[rename.get(key,key)]=numeric
    df=df[df['Дата'].notna()].sort_values('Дата').drop_duplicates('Дата').reset_index(drop=True)
    if len(df)<300:
        raise ArchiveError('Historical dataset has insufficient calendar coverage.')
    # All core fields may be absent even if the API provides dates.
    if df[[LABELS['T2M'],LABELS['T2M_MIN'],LABELS['T2M_MAX']]].notna().sum().max()<300:
        raise ArchiveError('Open-Meteo temperature series is incomplete.')
    return df


def fetch_archive(lat:float, lon:float, year:int) -> tuple[pd.DataFrame,str]:
    url=make_archive_url(lat,lon,year)
    try:
        r=requests.get(url, timeout=(8,35), headers={'Accept':'application/json'})
        if not 200<=r.status_code<300:
            raise ArchiveError(f'Open-Meteo archive returned HTTP {r.status_code}.')
        return parse_archive(r.json()),url
    except (requests.exceptions.RequestException,ValueError) as exc:
        raise ArchiveError('Open-Meteo historical model is temporarily unavailable.') from exc
