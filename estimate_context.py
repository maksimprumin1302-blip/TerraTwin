# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Transparent low-confidence fallback assessments for *field-testing opportunities*.

These never establish geology/rock type, ground-ice presence, or planetary similarity.
A number exists only when measured/model input coverage passes annual checks.
"""
from __future__ import annotations
import calendar
import math
import pandas as pd
from nasa_power import LABELS
from open_meteo_archive import DOC_URL


def valid_annual(series_frame, column, fraction=.90):
    """Return a complete-ish annual numeric series; never treat missing as zero."""
    if series_frame is None or column not in series_frame or 'Дата' not in series_frame:
        return None
    dates=pd.to_datetime(series_frame['Дата'],errors='coerce')
    years=dates.dropna().dt.year.unique()
    if len(years)!=1:
        return None
    expected=366 if calendar.isleap(int(years[0])) else 365
    nums=pd.to_numeric(series_frame[column],errors='coerce')
    mask=nums.notna() & nums.map(lambda x: math.isfinite(x) if pd.notna(x) else False)
    # Count one daily observation once. Repeated timestamps must never inflate
    # a full-year precipitation total or a freezing-day fraction.
    unique=pd.DataFrame({'date':dates[mask].dt.normalize(), 'value':nums[mask]})
    unique=unique.drop_duplicates('date',keep='first')
    if len(unique)<math.ceil(expected*fraction):
        return None
    return unique['value'].reset_index(drop=True)


def surface_materials_proxy(daily,terrain,weather_source):
    """A dryness/terrain training proxy; it is NOT a rock/material classification."""
    precipitation=valid_annual(daily,LABELS['PRECTOTCORR'],.95)
    if precipitation is None or (precipitation<0).any():
        return None
    annual_rain=float(precipitation.sum())
    aridity=max(0,min(1,(900-annual_rain)/900))
    slope=terrain.get('slope_deg') if isinstance(terrain,dict) else None
    relief=terrain.get('relief_m') if isinstance(terrain,dict) else None
    if isinstance(slope,(int,float)) and isinstance(relief,(int,float)) and math.isfinite(slope) and math.isfinite(relief) and slope>=0 and relief>=0:
        terrain_diversity=max(0,min(1,relief/120))
        value=.70*aridity+.30*terrain_diversity
        note=f'Наближений індекс сухих/складних поверхневих умов: річні опади {annual_rain:.0f} мм, перепад висот {relief:.0f} м. Формула: 70% сухість + 30% різноманітність рельєфу. НЕ визначає тип, міцність чи мінеральний склад порід.'
        source='https://open-meteo.com/en/docs/elevation-api'
    else:
        value=aridity
        note=f'Кліматична оцінка сухості поверхні за річними опадами {annual_rain:.0f} мм. Рельєф відсутній. Це НЕ карта порід і НЕ вимірювання матеріалів.'
        source=''
    return {'score':value,'note':note,'source':weather_source,
            'evidence_type':'Estimated dry-surface proxy (not lithology)', 'confidence':'low'}


def freezing_proxy(daily,soil_daily,weather_source):
    """Estimate ground freezing *conditions*, NOT an ice occurrence or mass estimate."""
    soil=valid_annual(soil_daily,'soil_temperature_7_to_28cm_mean',.90)
    if soil is not None:
        fraction=float((soil<0).mean())
        score=min(1,1.25*fraction)
        note=(f'ERA5/Open-Meteo model soil temperature (7–28 cm): {fraction*100:.1f}% of days below 0 °C. '
              'This is a frozen-soil-condition proxy; it does NOT confirm water ice, permanent permafrost or usable ice resources.')
        return {'score':score,'note':note,'source':DOC_URL,
                'evidence_type':'Estimated soil-temperature freezing proxy (not ice)', 'confidence':'low'}
    cold=valid_annual(daily,LABELS['T2M_MIN'],.90)
    if cold is not None:
        fraction=float((cold<0).mean())
        # Downweight air-temperature-only estimates compared to actual mapped data.
        score=.6*fraction
        note=(f'Air temperature daily minimum below 0 °C on {fraction*100:.1f}% of days. '
              'Weak fallback for freezing test conditions only; no soil temperature or ground-ice evidence is available.')
        return {'score':score,'note':note,'source':weather_source,
                'evidence_type':'Estimated air-freezing proxy (not ice)', 'confidence':'very low'}
    return None
