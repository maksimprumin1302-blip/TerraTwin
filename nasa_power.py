"""NASA POWER daily weather client.

Correctly assembled HTTPS parameters; no API key required.
See https://power.larc.nasa.gov/docs/services/api/temporal/daily/
"""
from __future__ import annotations
import time
from urllib.parse import urlencode
import math
import pandas as pd
import requests

POWER_ENDPOINT = 'https://power.larc.nasa.gov/api/temporal/daily/point'
PARAMETERS = ('T2M', 'PRECTOTCORR', 'WS10M', 'T2M_MIN', 'T2M_MAX', 'ALLSKY_SFC_SW_DWN')
LABELS = {'T2M':'Температура, °C', 'PRECTOTCORR':'Опади, мм/день', 'WS10M':'Вітер, м/с', 'T2M_MIN':'Температура мін., °C', 'T2M_MAX':'Температура макс., °C', 'ALLSKY_SFC_SW_DWN':'Сонячна енергія, кВт·год/м²/добу'}

class NASADataError(Exception):
    """Connection, HTTP or data validation problem, ready for user display."""


def make_power_url(latitude: float, longitude: float, year: int) -> str:
    if not (math.isfinite(float(latitude)) and math.isfinite(float(longitude)) and -89.9 <= float(latitude) <= 89.9 and -180 <= float(longitude) <= 180):
        raise NASADataError('Некоректні координати: виберіть точку на Землі.')
    if not 1981 <= int(year) <= 2025:
        raise NASADataError('Для повного річного аналізу оберіть рік від 1981 до 2025.')
    params = {
        'parameters': ','.join(PARAMETERS), 'community':'AG',
        'longitude':f'{float(longitude):.4f}', 'latitude':f'{float(latitude):.4f}',
        'start':f'{int(year)}0101', 'end':f'{int(year)}1231',
        'format':'JSON', 'time-standard':'UTC',
    }
    # Keep literal '&' delimiters and commas: don't concatenate manually with backslashes.
    return POWER_ENDPOINT + '?' + urlencode(params, safe=',')


def parse_power_response(payload: dict) -> pd.DataFrame:
    if not isinstance(payload, dict):
        raise NASADataError('NASA POWER повернув некоректні дані.')
    if payload.get('errors'):
        raise NASADataError('NASA POWER повідомляє: ' + '; '.join(map(str, payload['errors']))[:400])
    parameters = payload.get('properties', {}).get('parameter', {})
    if not isinstance(parameters, dict) or not any(k in parameters for k in PARAMETERS):
        raise NASADataError('У відповіді NASA немає потрібних показників.')
    dates = set()
    for code in PARAMETERS:
        values = parameters.get(code, {})
        if isinstance(values, dict):
            dates.update(d for d in values if len(d) == 8 and d.isdigit())
    # AG solar energy commonly arrives in MJ/m²/day. Consult response metadata
    # rather than silently assuming a unit when NASA reports it explicitly.
    solar_info = payload.get('parameters', {}).get('ALLSKY_SFC_SW_DWN', {})
    unit = str(solar_info.get('units', '') if isinstance(solar_info, dict) else '').lower()
    if unit and ('mj' in unit):
        solar_factor = 1.0 / 3.6
    elif unit and (('kw' in unit) or ('kwh' in unit)):
        solar_factor = 1.0
    else:
        # community=AG published convention; separately disclosed in methodology.
        solar_factor = 1.0 / 3.6
    rows=[]
    for day in sorted(dates):
        date=pd.to_datetime(day, format='%Y%m%d', errors='coerce')
        if pd.isna(date):
            continue
        row={'Дата':date}
        for code in PARAMETERS:
            values=parameters.get(code, {})
            try:
                value=float(values.get(day)) if isinstance(values,dict) else float('nan')
                if value <= -900:
                    value=float('nan')
                elif not math.isfinite(value):
                    value=float('nan')
                elif code == 'ALLSKY_SFC_SW_DWN':
                    # NASA POWER community=AG supplies solar energy as MJ/m²/day.
                    # TerraTwin consistently displays kWh/m²/day (1 kWh=3.6 MJ).
                    value = value * solar_factor
            except (TypeError,ValueError):
                value=float('nan')
            row[LABELS[code]]=value
        rows.append(row)
    if not rows:
        raise NASADataError('NASA POWER не повернув щоденних даних для обраного року.')
    df=pd.DataFrame(rows).sort_values('Дата').reset_index(drop=True)
    if df[[LABELS[code] for code in PARAMETERS]].isna().all().all():
        raise NASADataError('NASA POWER повернув лише пропущені значення.')
    return df


def _http_error(response) -> NASADataError:
    status=response.status_code
    if status == 429:
        msg='Забагато запитів до NASA POWER (429). Повторіть пізніше.'
    elif status in (500,502,503,504):
        msg=f'Сервіс NASA POWER тимчасово недоступний ({status}). Спробуйте пізніше.'
    elif status == 422:
        msg='NASA POWER відхилив параметри запиту (422). Перевірте координати та обраний рік.'
    elif status == 403:
        msg='NASA POWER відмовив у доступі (403). Не надсилайте забагато запитів.'
    else:
        msg=f'NASA POWER повернув HTTP {status}.'
    return NASADataError(msg)


def fetch_power(latitude: float, longitude: float, year: int) -> tuple[pd.DataFrame, str]:
    url=make_power_url(latitude,longitude,year)
    try:
        # One retry only for transient server failures; caching is handled in app.py.
        for attempt in range(2):
            response=requests.get(url, timeout=(10,50), headers={'Accept':'application/json'})
            if response.status_code in (429,500,502,503,504) and attempt == 0:
                time.sleep(0.5)
                continue
            if not 200 <= response.status_code < 300:
                raise _http_error(response)
            try:
                payload=response.json()
            except ValueError as exc:
                raise NASADataError('Сервер NASA повернув відповідь не у форматі JSON.') from exc
            return parse_power_response(payload),url
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        raise NASADataError('Не вдалося зв’язатися з NASA POWER. Перевірте з’єднання або повторіть пізніше.') from exc
    except requests.exceptions.RequestException as exc:
        raise NASADataError('Помилка мережевого запиту до NASA POWER.') from exc
    raise NASADataError('Сервіс NASA POWER недоступний.')


def monthly_summary(daily:pd.DataFrame) -> pd.DataFrame:
    df=daily.set_index('Дата').resample('MS').agg({
        LABELS['T2M']:'mean', LABELS['PRECTOTCORR']:'sum', LABELS['WS10M']:'mean',
    }).reset_index()
    monthly_precip=daily.set_index('Дата')[LABELS['PRECTOTCORR']].resample('MS').sum(min_count=1)
    monthly_counts=daily.set_index('Дата')[LABELS['PRECTOTCORR']].resample('MS').count()
    expected_days=monthly_counts.index.days_in_month
    monthly_precip=monthly_precip.where(monthly_counts.to_numpy() >= .95 * expected_days)
    df[LABELS['PRECTOTCORR']]=monthly_precip.to_numpy()
    return df.rename(columns={LABELS['PRECTOTCORR']:'Опади за місяць, мм'})
