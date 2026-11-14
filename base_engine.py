"""Auditable terrestrial test-site screening for Moon/Mars mission scenarios.

No values from other planets are fabricated. Planetary profiles contain *verified
mission context* only. Earth values come from NASA POWER and Copernicus DEM;
site evidence is manually curated and cited. The result is NOT approval for a base.
"""
from __future__ import annotations
import math
import pandas as pd

TARGETS = {
    'mons_mouton': {
        'name':'Місяць · Mons Mouton Plateau', 'planet':'Місяць',
        'status':'Район-кандидат Artemis III, оголошений NASA у 2024 році; не затверджена база',
        'context':'Південний полюс: освітлення, доступ до затінених областей, ресурси та безпечний рельєф. Географічні параметри конкретного майданчика треба оцінювати окремо.',
        'source':'https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/',
        'water_source':'https://www.nasa.gov/humans-in-space/nasas-artemis-base-camp-on-the-moon-will-need-light-water-elevation/',
        'weights':{'terrain':22,'materials':12,'thermal':20,'ice':20,'sun':14,'rover':12},
    },
    'nobile_rim_2': {
        'name':'Місяць · Nobile Rim 2', 'planet':'Місяць',
        'status':'Район-кандидат Artemis III, оголошений NASA у 2024 році; не затверджена база',
        'context':'Південнополярний район із важливими обмеженнями освітлення, ухилів та можливого доступу до льодових ресурсів.',
        'source':'https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/',
        'water_source':'https://www.nasa.gov/reference/moonbase-environment/',
        'weights':{'terrain':18,'materials':14,'thermal':20,'ice':20,'sun':16,'rover':12},
    },
    'arcadia': {
        'name':'Марс · Arcadia Planitia (регіон досліджень льоду)', 'planet':'Марс',
        'status':'Досліджуваний регіон можливого підповерхневого льоду; база/посадка людей не затверджена',
        'context':'Проєкт SWIM аналізував підповерхневий лід у частині Arcadia Planitia для підтримки майбутніх досліджень ресурсів та пілотованих місій.',
        'source':'https://swim.psi.edu/',
        'water_source':'https://swim.psi.edu/',
        'weights':{'terrain':20,'materials':16,'thermal':20,'ice':24,'sun':10,'rover':10},
    },
}
CRITERIA = {
    'terrain':('Рельєф і приблизний ухил','Copernicus DEM GLO-90; локальна оцінка за дев’ятьма точками. Не перевірка придатності посадкового майданчика.'),
    'materials':('Матеріали та породи','Тільки геологічно описані наземні ділянки; оцінка можливостей випробувань, не тотожності мінералогії.'),
    'thermal':('Температурні екстремуми','Земні мінімальні та максимальні добові температури NASA POWER. Не відтворюють вакуум та радіацію.'),
    'ice':('Вода / ґрунтовий лід','Тільки території з перевіреною інформацією про мерзлоту/лід; опади не доводять наявності водяного льоду.'),
    'sun':('Сонячне освітлення','NASA POWER: потік сонячної енергії на Землі. Не тотожний освітленню планетарної ділянки.'),
    'rover':('Умови руху роботів','Модельний індекс за тим самим DEM, що й ухил. Ці дві ознаки не незалежні, а дані не підходять для сертифікації маршруту.'),
}

# Site-specific *terrestrial testing opportunity* evidence, not claimed
# composition match to lunar polar regolith or Martian Arcadia. Scores are
# explicitly heuristic (0..1) and backed by the descriptions linked here.
SITE_EVIDENCE = {
    'khaybar': {
        'materials':(.75,'Задокументовані базальтові породи та лавові потоки; вони не є точною копією місячних полярних матеріалів.',
                     'https://science.nasa.gov/earth/earth-observatory/harrat-khaybar-volcanic-field-8650/'),
    },
    'arizaro': {
        'materials':(.65,'Солі й сухі озерні відклади корисні для геохімічних випробувань, але не доводять відповідність матеріалам Arcadia.',
                     'https://science.nasa.gov/earth/earth-observatory/salar-de-arizaro-83914/'),
    },
    'bardenas': {
        'materials':(.65,'Задокументовані осадові породи та ерозійні форми; придатність для обраного експерименту треба перевіряти.',
                     'https://www.unesco.org/en/mab/bardenas-reales'),
    },
    'svalbard': {
        'materials':(.75,'Скельні виходи та мерзлотні ландшафти використовували в аналогових дослідженнях Марса.',
                     'https://www.esa.int/Enabling_Support/Preparing_for_the_Future/Space_for_Earth/Arctic/Mars_in_the_Arctic'),
        'ice':(.95,'Шпіцберген має досліджені багаторічномерзлі ґрунти; це не вимірювання льоду в конкретній вибраній точці.',
               'https://www.gu.se/en/research/splam'),
    },
    'haughton': {
        'materials':(.85,'Ударний кратер і породи використовують для випробувань геологічних та бурових інструментів.',
                     'https://www.nasa.gov/mission/haughton-mars-project-hmp-canadian-arctic/'),
        'ice':(.9,'NASA описує мерзлоту й ґрунтовий лід як складові регіону Haughton.',
               'https://ntrs.nasa.gov/citations/20060013129'),
    },
}


def _clamp(value):
    return max(0.,min(1.,float(value)))


def _series(daily, label, min_count=220):
    """Require near-complete annual coverage before calculating annual proxies."""
    if daily is None or label not in daily:
        return None
    values = pd.to_numeric(daily[label], errors='coerce')
    if 'Дата' in daily:
        dates = pd.to_datetime(daily['Дата'], errors='coerce')
        years = dates.dropna().dt.year.unique()
        if len(years) != 1:
            return None
        year = int(years[0])
        expected = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
        valid_days = dates[values.notna()].dt.normalize().nunique()
        if valid_days < max(min_count, .9 * expected):
            return None
    elif values.notna().sum() < max(min_count, 329):
        return None
    return values.dropna()


def derive_observations(daily,terrain,site_id=None,geology=None,ground_ice=None,glim=None,*,
                        soil_daily=None,allow_proxies=False,weather_source=None):
    """Build observed terrestrial fields, returning None for unmeasured axes."""
    scores={}; notes={}; metrics={}; sources={}; evidence_types={}
    terrain_url='https://open-meteo.com/en/docs/elevation-api'
    nasa_url=weather_source or 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/'
    climate_provider='Open-Meteo historical reanalysis' if 'open-meteo.com' in nasa_url else 'NASA POWER'
    if terrain and isinstance(terrain.get('slope_deg'),(float,int)):
        slope=float(terrain['slope_deg'])
        relief=float(terrain.get('relief_m',0))
        # Simulation training proxy, not a planetary landing safety metric.
        scores['terrain']=_clamp((18-slope)/18)
        notes['terrain']=f'Ухил ≈ {slope:.1f}°, перепад на сітці ≈ {relief:.0f} м. Оцінка лише для земних навчальних випробувань.'
        sources['terrain']=terrain_url
        evidence_types['terrain']='Modeled DEM proxy'
        scores['rover']=_clamp(1-abs(slope-7)/17) * _clamp((55-relief)/55)
        notes['rover']='Оцінка різноманітності й прохідності навчального маршруту на основі тієї самої DEM; не незалежне вимірювання.'
        sources['rover']=terrain_url
        evidence_types['rover']='Derived from the same DEM'
        metrics['Ухил (грубо)']=round(slope,2)
        metrics['Висота над рівнем моря, м']=terrain.get('elevation_m')
        metrics['Перепад на сітці, м']=terrain.get('relief_m')
    cold=_series(daily,'Температура мін., °C')
    warm=_series(daily,'Температура макс., °C')
    if cold is not None and warm is not None:
        minimum=float(cold.quantile(0.10)); maximum=float(warm.quantile(.90))
        daily_amp=(warm-cold).dropna()
        if len(daily_amp)>=220:
            mean_range=float(daily_amp.mean())
            cold_sub=_clamp((5-minimum)/35)
            cycle_sub=_clamp(mean_range/25)
            scores['thermal']=.6*cold_sub+.4*cycle_sub
            notes['thermal']=f'10-й процентиль добових мінімумів {minimum:.1f} °C; середній добовий розмах {mean_range:.1f} °C. Еталонні пороги — авторські.'
            sources['thermal']=nasa_url
            evidence_types['thermal']=climate_provider+' gridded climate proxy'
            metrics['Холодний період (P10), °C']=round(minimum,1)
            metrics['Спекотний період (P90), °C']=round(maximum,1)
            metrics['Середній добовий розмах, °C']=round(mean_range,1)
    # Ground freezing context: observational *air* temperature, never used to
    # claim the presence or amount of ground ice. Only report on complete years.
    if cold is not None:
        freezing_fraction=100*float((cold<0).mean())
        metrics['Дні з мінімальною T нижче 0 °C, % (не доказ льоду)']=round(freezing_fraction,1)
    solar=_series(daily,'Сонячна енергія, кВт·год/м²/добу')
    if solar is not None:
        mean_solar=float(solar.mean())
        scores['sun']=_clamp(mean_solar/6.0)
        notes['sun']=f'Середня сонячна енергія на Землі: {mean_solar:.2f} кВт·год/м²/день. Не порівнюється прямо з освітленням Місяця чи Марса.'
        sources['sun']=nasa_url
        evidence_types['sun']=climate_provider+' gridded solar proxy'
        metrics['Сонячна енергія, кВт·год/м²/добу']=round(mean_solar,2)
    curated=SITE_EVIDENCE.get(site_id, {})
    for feature in ('materials','ice'):
        if feature in curated:
            if feature=='ice' and isinstance(ground_ice,dict) and ground_ice.get('status')=='mapped_class' \
                    and ground_ice.get('ground_ice_category') in ('high','medium','low','none'):
                # A matching regional map class supersedes a generalized
                # literature proxy; a mapped 'none' must not be overridden.
                continue
            scores[feature],notes[feature],sources[feature]=curated[feature]
            evidence_types[feature]='Curated regional literature (not point verified)'
    # For arbitrary coordinates, use actual mapped lithology when it is classifiable.
    # Curated records take priority: their narrative sources provide site context
    # beyond the map's coarse generalization. Never infer rock type from site names.
    if 'materials' not in scores and geology is not None:
        from environment_evidence import mapped_materials
        interpreted=mapped_materials(geology)
        if interpreted['status']=='mapped_proxy':
            scores['materials']=interpreted['score']
            names=', '.join(sorted(set(m['lithology'] for m in interpreted['matches'])))[:300]
            notes['materials']=f'Картографічна літологія Macrostrat: {names}. {interpreted["note"]}'
            sources['materials']=interpreted['source_url']
            evidence_types['materials']='Mapped lithology proxy (Macrostrat)'
    # A permafrost polygon is used only after explicit GIS import with fields
    # validated by environment_evidence. Map class is not a point ice assay.
    if 'ice' not in scores and ground_ice is not None:
        from environment_evidence import ice_testing_proxy
        interpreted=ice_testing_proxy(ground_ice)
        if interpreted is not None:
            scores['ice']=interpreted['score']
            notes['ice']=interpreted['note']
            sources['ice']=interpreted['source_url']
            evidence_types['ice']='Imported regional ground-ice map (NSIDC)'
            metrics['NSIDC: категорія ґрунтового льоду']=ground_ice['ground_ice_category']
            metrics['NSIDC: поширення мерзлоти']=ground_ice['permafrost_extent']
    # Optional global GLiM map subset is a fallback *only* if both a more
    # detailed mapped lithology and regional literature were unavailable.
    if 'materials' not in scores and isinstance(glim,dict) and glim.get('status')=='mapped_proxy':
        scores['materials']=glim['score']
        notes['materials']=glim['note']
        sources['materials']=glim['source_url']
        evidence_types['materials']='Imported regional lithology map (GLiM)'
    # Optional low-confidence fallbacks make the *field-test screening* more complete.
    # They are NOT substituted measurements of rocks or ground ice. In particular,
    # weather cannot establish lithology and freezing soil is not proof of water ice.
    if allow_proxies:
        from estimate_context import surface_materials_proxy, freezing_proxy
        for key, proxy in (
            ('materials', surface_materials_proxy(daily,terrain,nasa_url)),
            ('ice', freezing_proxy(daily,soil_daily,nasa_url)),
        ):
            if key not in scores and proxy is not None:
                scores[key]=proxy['score']
                notes[key]=proxy['note']
                sources[key]=proxy['source']
                evidence_types[key]=proxy['evidence_type']
    return {'scores':scores,'notes':notes,'sources':sources,'metrics':metrics,
            'evidence_types':evidence_types}



def assess_base(observations, target_id, weights=None):
    if target_id not in TARGETS:
        raise ValueError('Невідома планетарна ціль')
    weights=dict(TARGETS[target_id]['weights'] if weights is None else weights)
    if set(weights) != set(CRITERIA) or any(not isinstance(w,int) or w<0 or w>50 for w in weights.values()):
        raise ValueError('Некоректні ваги')
    total=sum(weights.values())
    if total<=0:
        raise ValueError('Потрібно обрати ненульову вагу')
    observed=observations.get('scores', {})
    rows=[]; earned=0.; covered=0; low_conf_weight=0; low_conf_count=0
    for key,weight in weights.items():
        available=(key in observed and observed[key] is not None and math.isfinite(float(observed[key])))
        value=_clamp(observed[key]) if available else None
        if available and weight:
            covered+=weight;earned+=weight*value
            if 'Estimated ' in observations.get('evidence_types',{}).get(key,''):
                low_conf_weight+=weight
                low_conf_count+=1
        rows.append({'key':key,'criterion':CRITERIA[key][0], 'weight':weight,
                     'score':None if value is None else round(value*100),
                     'note':observations.get('notes',{}).get(key,'Немає перевірених даних для цієї території.'),
                     'source':observations.get('sources',{}).get(key,''),
                     'evidence_type':observations.get('evidence_types',{}).get(key,'Not verified')} )
    coverage=round(100*covered/total)
    # Only a partial, Earth-testing suitability score; not the actual site or
    # planetary base suitability. Unknown axes are never scored as zero.
    score=round(100*earned/covered) if covered and coverage>=60 else None
    return {'target':TARGETS[target_id],'score':score,'coverage':coverage,
            'estimated_count':low_conf_count,
            'estimated_weight':low_conf_weight,
            'mapped_or_modeled_count':sum(r['score'] is not None and 'Estimated ' not in r['evidence_type'] for r in rows),
            'status':'попередня оцінка' if score is not None else 'замало даних',
            'criteria':rows,'used_weight':covered,'total_weight':total,
            'metrics':observations.get('metrics',{})}
