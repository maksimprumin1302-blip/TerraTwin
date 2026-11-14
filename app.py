"""TerraTwin v2.1 — scientific analogs and base mission scenarios.

Run from project folder: python -m streamlit run app.py --server.port 8521
Independent educational project, NOT affiliated with NASA.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as _st
from localization import LocalizedStreamlit, translate
st=LocalizedStreamlit(_st)
from streamlit_folium import st_folium

from analog_scoring import FEATURES, TARGETS as SCIENCE_TARGETS, load_evidence, rank_analogs
from dashboard_visuals import (
    evidence_heatmap, ranking_chart, ranking_csv,
    weather_temperature_chart, weather_precip_chart,
)
from map_layers import build_world_map
from earth_terrain import fetch_terrain, TerrainError
from geology_api import fetch_geology, GeologyError
from open_meteo_archive import fetch_archive, ArchiveError, DOC_URL as ARCHIVE_DOC
from soil_api import fetch_soil, SoilError
from environment_evidence import mapped_materials, nsidc_coverage, parse_ground_ice_geojson, NSIDC_URL
from fallback_geology import parse_glim_geojson, GLIM_URL
from assessment_labels import classify_base, classify_analog
from source_catalog import SOURCES, BY_ID, PLANET_SOURCES
from base_engine import TARGETS as BASE_TARGETS, CRITERIA as BASE_CRITERIA, derive_observations, assess_base
from nasa_power import LABELS, NASADataError, fetch_power, make_power_url, monthly_summary
from site_agent import analyze_climate, nearby_site
from ui_skin import brand, hero, theme_css
from workspace import ensure_location, set_location, dataset_key, analysis_for_active
from place_names import resolve_point_name, display_point
from satellite_catalogs import nasa_collections, sentinel_scenes, CatalogUnavailable
from source_locale import display_source
from ui_preferences import ensure_preferences, set_page, set_theme, PAGE_IDS, THEME_IDS, theme_name, canonical_page, select_navigation, sync_navigation_before_widget, select_theme, sync_theme_before_widget, THEME_WIDGET_KEY

ROOT = Path(__file__).resolve().parent
BUILD = '2.1.11 — Complete EN/UA UI'
NASA_DOCS = 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/'

st.set_page_config(page_title='TerraTwin | Earth Analog Explorer',
                   page_icon='🌍', layout='wide', initial_sidebar_state='collapsed')

@st.cache_data(show_spinner=False)
def load_sites():
    return json.loads((ROOT / 'data' / 'sites.json').read_text(encoding='utf-8'))

@st.cache_data(show_spinner=False)
def load_evidence_db():
    return load_evidence(ROOT / 'data' / 'feature_evidence.json')

@st.cache_data(ttl=86400, show_spinner=False)
def load_nasa(lat:float, lon:float, year:int):
    return fetch_power(lat,lon,year)

@st.cache_data(ttl=604800,show_spinner=False)
def load_elevation(lat:float,lon:float):
    return fetch_terrain(lat,lon)

@st.cache_data(ttl=604800,show_spinner=False)
def load_geology(lat:float,lon:float):
    return fetch_geology(lat,lon)

@st.cache_data(ttl=604800,show_spinner=False)
def load_soil(lat:float,lon:float):
    return fetch_soil(lat,lon)

@st.cache_data(ttl=30*86400, max_entries=800, show_spinner=False)
def reverse_place(lat: float, lon: float, lang: str):
    # One user-triggered request per chosen point/language, cached for 30 days.
    return resolve_point_name(lat,lon,lang)

@st.cache_data(ttl=86400, max_entries=200, show_spinner=False)
def load_nasa_collections(lat: float, lon: float):
    return nasa_collections(lat,lon)

@st.cache_data(ttl=86400, max_entries=200, show_spinner=False)
def load_sentinel_scenes(lat: float, lon: float, year: int):
    return sentinel_scenes(lat,lon,year)


def localized_point():
    point=ensure_location(st.session_state)
    language=st.session_state.get('tt_lang','en')
    if not point.get('known_site') and not point.get('place_'+language) and not point.get('lookup_attempt_'+language):
        # Resolve only after a user-selected location; never bulk lookup sites.
        if point.get('user_selected'):
            point['lookup_attempt_'+language]=True
            place=reverse_place(point['lat'],point['lon'],language)
            if place:point['place_'+language]=place
    return display_point(point,language)


def select_custom_point(lat:float,lon:float,label='Selected on map'):
    changed=set_location(st.session_state,lat,lon,label)
    point=ensure_location(st.session_state)
    if changed:
        point['user_selected']=True
        lang=st.session_state.get('tt_lang','en')
        point['lookup_attempt_'+lang]=True
        place=reverse_place(point['lat'],point['lon'],lang)
        if place:point['place_'+lang]=place
    return changed


def open_active_charts():
    point=ensure_location(st.session_state)
    set_page(st.session_state,'Графіки')
    st.session_state['tt_chart_year']=int(st.session_state.get('tt_pick_year',2025))
    st.session_state['tt_chart_requested']=dataset_key(point['lat'],point['lon'],st.session_state['tt_chart_year'])


@st.cache_data(ttl=604800,show_spinner=False)
def load_archive(lat:float,lon:float,year:int):
    return fetch_archive(lat,lon,year)



def source_link(source_id: str, label: str | None = None):
    source = BY_ID[source_id]
    st.link_button(label or (source['provider'] + ' · ' + source['name']), source['url'])


def ui_text(en: str, uk: str) -> str:
    """A clear two-language string, independent of the text translation shim."""
    return en if st.session_state.get('tt_lang','en') == 'en' else uk


def localized_metric(container, label, value, **kwargs):
    """Translate metrics even when rendered on a Streamlit column object."""
    lang = st.session_state.get('tt_lang', 'en')
    return container.metric(translate(label, lang),
                            translate(value, lang) if isinstance(value, str) else value,
                            **kwargs)


def quality_note(kind: str):
    messages = {
        'weather': 'NASA POWER: грідовані супутниково-модельні дані. Середні показники не є локальними вимірюваннями на місці; рік і кількість доступних днів мають значення.',
        'terrain': 'Copernicus GLO-90: висота з DEM ~90 м; місцевий ухил в TerraTwin обчислений із 9 точок на відстані ~300 м, тому не підходить для оцінки конкретного посадкового майданчика.',
        'geology': 'Macrostrat: геологічні полігони з карт різного масштабу. Літологія не означає, що мінеральний склад породи лабораторно виміряно саме в обраній координаті.',
        'planet': 'Планетарна ціль задає контекст місії. Числові пікселі LOLA, MOLA, Diviner та SWIM поки не зчитуються автоматично; це не пряме числове зіставлення двох планет.',
    }
    st.caption('Достовірність і масштаб: ' + messages[kind])


def dataset_completeness(daily):
    """Coverage relative to the full calendar year, not just returned rows."""
    indicators = [LABELS[x] for x in ('T2M', 'PRECTOTCORR', 'WS10M', 'T2M_MIN', 'T2M_MAX', 'ALLSKY_SFC_SW_DWN')]
    if daily is None or len(daily) == 0:
        return {field: 0 for field in indicators}
    dates = pd.to_datetime(daily['Дата'], errors='coerce')
    years = dates.dropna().dt.year.unique()
    if len(years) != 1:
        return {field: 0 for field in indicators}
    year = int(years[0])
    expected = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
    result = {}
    for field in indicators:
        if field not in daily:
            result[field] = 0
        else:
            mask=(dates.dt.year == year) & pd.to_numeric(daily[field], errors='coerce').notna()
            valid_days=dates[mask].dt.normalize().nunique()
            result[field] = int(round(100 * min(int(valid_days), expected) / expected))
    return result


def point_lookups(lat: float, lon: float, *, include_weather: bool = False, year: int = 2025):
    """Retrieve every safe point-query dataset. Failed lookups are explicitly unavailable.

    SoilGrids REST is paused, planetary rasters need GIS; we never silently
    substitute default or manually invented figures for those missing values.
    """
    key = (round(float(lat), 4), round(float(lon), 4))
    existing = st.session_state.get('tt_point_sources')
    if not isinstance(existing, dict) or existing.get('key') != key:
        existing = {'key': key, 'terrain': None, 'geology': None,
                    'errors': {}, 'retrieved': []}
    for source_id, getter in (('copernicus', load_elevation), ('macrostrat', load_geology)):
        try:
            result = getter(*key)
            existing['terrain' if source_id == 'copernicus' else 'geology'] = result
            existing['errors'].pop(source_id, None)
            if source_id not in existing['retrieved']:
                existing['retrieved'].append(source_id)
        except (TerrainError, GeologyError) as exc:
            existing['errors'][source_id] = str(exc)
    if include_weather:
        try:
            get_weather(*key, year, set_as_active=True)
            existing['errors'].pop('power', None)
        except NASADataError as exc:
            existing['errors']['power'] = str(exc)
        try:
            existing['soil_climate'],_ = load_archive(*key,year)
            existing['soil_year']=year
        except ArchiveError:
            existing['soil_climate']=None
            existing['soil_year']=year
    st.session_state['tt_point_sources'] = existing
    return existing


def geology_block(geo):
    if not geo:
        st.info('Геологічну карту для цієї точки ще не завантажено.')
        return
    if geo['status'] != 'ok':
        if geo['status'] == 'no_coverage':
            st.info('Macrostrat: у відповіді немає картографічних одиниць для цієї точки. Це не доказ відсутності геологічних порід.')
        else:
            st.info('Геологічна карта для цієї точки недоступна у Macrostrat. Перевірте резервні дані GLiM або описи наукових аналогів.')
        if geo.get('query_url'):
            st.link_button('Перевірити відповідь Macrostrat', geo['query_url'])
        return
    rows=[]
    for unit in geo['units']:
        rows.append({'Геологічна одиниця':unit['unit'],
                     'Літологія':unit['lithology'] or 'Немає даних',
                     'Вік':unit['age_name'] or 'Немає даних',
                     'ID першоджерела':unit['source_id'] if unit['source_id'] is not None else 'Немає даних',
                     'Масштаб':unit['scale'] or 'Немає даних'})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander('Опис геологічних одиниць'):
        for unit in geo['units']:
            if unit['description']:
                st.write('**'+str(unit['unit'])+'** — '+str(unit['description']))
    quality_note('geology')
    st.link_button('Відкрити точний запит Macrostrat',geo['query_url'])


def render_planetary_sources(target_id: str):
    keys=PLANET_SOURCES.get(target_id, ())
    if not keys:
        return
    with st.expander('Планетарні вимірювання та карти для цього району'):
        st.write('Наведені реальні наукові архіви. Для кількісного порівняння з координатою на Землі '
                 'потрібно відібрати пікселі відповідних планетарних карт у GIS; TerraTwin не вигадує їхні числа.')
        for key in keys:
            source=BY_ID[key]
            st.markdown('**'+source['name']+'** · '+source['provider'])
            st.caption(source['what']+' Обмеження: '+source['limits'])
            source_link(key,'Відкрити архів · '+source['name'])


def imported_ground_ice(lat: float, lon: float) -> dict:
    """Import-only NSIDC raster/vector assessment; always source/coverage-aware."""
    local=nsidc_coverage(lat, lon)
    data=st.session_state.get('tt_nsidc_geojson')
    if data is None or local['status']=='outside_coverage':
        return local
    try:
        return parse_ground_ice_geojson(data, lat, lon)
    except ValueError as exc:
        return {'status':'invalid_import','note':str(exc),'source_url':NSIDC_URL}


@st.cache_data(show_spinner=False)
def parse_glim_cached(file_bytes: bytes, lat: float, lon: float):
    return parse_glim_geojson(file_bytes, lat, lon)


def imported_glim(lat: float, lon: float) -> dict:
    raw=st.session_state.get('tt_glim_geojson')
    if raw is None:
        return {'status':'not_loaded', 'source_url':GLIM_URL}
    try:
        return parse_glim_cached(raw,lat,lon)
    except ValueError as exc:
        return {'status':'invalid_import', 'note':str(exc), 'source_url':GLIM_URL}


def glim_upload_panel(point):
    with st.expander('🪨 Резервне джерело порід: глобальна карта GLiM', expanded=False):
        st.write('Якщо Macrostrat не надає тип порід, можна використати офіційну '
                 'глобальну літологічну карту GLiM (Hartmann & Moosdorf, 2012). '
                 'Це **резервний варіант**, а не гарантія даних у кожній точці.')
        st.caption('Завантажте справжній GIS-шар GLiM, обріжте його для потрібного району '
                   'та експортуйте GeoJSON у WGS84 (EPSG:4326). Програма читає '
                   'перший рівень GLiM із поля `xx`, `glim_code` або `glim_lithology`. '
                   'Класи water / ice-glaciers / no-data не перетворюються на тип порід.')
        st.link_button('Публікація та легенда GLiM',GLIM_URL)
        uploaded=st.file_uploader('Завантажити підготовлений GLiM GeoJSON (до 15 МБ)',
                                  type=['geojson','json'],key='tt_glim_upload_control')
        if uploaded is not None:
            if uploaded.size>15_000_000:
                st.warning('Файл завеликий. Обріжте GIS-карту до району дослідження.')
            else:
                st.session_state['tt_glim_geojson']=uploaded.getvalue()
        if st.session_state.get('tt_glim_geojson') is not None:
            if st.button('Видалити імпорт GLiM',key='tt_glim_clear'):
                st.session_state.pop('tt_glim_geojson',None)
                st.rerun()
        result=imported_glim(point['lat'],point['lon'])
        if result['status']=='mapped_proxy':
            st.success('Знайдено літологічний клас GLiM для цієї точки: '+result['rock_type'])
            st.caption('Регіональна карта, а не лабораторний аналіз. Походження завантаженого файлу має бути перевірене користувачем.')
        elif result['status']=='not_loaded':
            st.info('Карту GLiM ще не завантажено. Для відомих аналогів можуть використовуватися вже процитовані польові дослідження.')
        elif result['status']=='invalid_import':
            st.warning('Не вдалося використати цей GIS-файл: '+result['note'])
        else:
            st.info(result.get('note','Для цієї точки немає підтвердженого літологічного полігона GLiM.'))
    return result


def evidence_status_panel(observations):
    """Compact provenance table: map values, site-specific literature and unknowns."""
    titles={'terrain':'Рельєф / ухил','materials':'Матеріали / породи',
            'thermal':'Температурні екстремуми','ice':'Вода / ґрунтовий лід',
            'sun':'Сонячна енергія','rover':'Умови руху роботів'}
    evidence_names={
        'Modeled DEM proxy':'DEM-модель · похідна оцінка',
        'Derived from the same DEM':'DEM-модель · залежна оцінка',
        'NASA POWER gridded climate proxy':'NASA POWER · сіткова модель',
        'NASA POWER gridded solar proxy':'NASA POWER · сіткова модель',
        'Curated regional literature (not point verified)':'Наукова публікація · рівень регіону',
        'Mapped lithology proxy (Macrostrat)':'Macrostrat · картографічна літологія',
        'Imported regional lithology map (GLiM)':'GLiM · імпортована геологічна карта',
        'Imported regional ground-ice map (NSIDC)':'NSIDC · імпортована карта льоду',
        'Estimated dry-surface proxy (not lithology)':'Низька впевненість · опади та рельєф (НЕ породи)',
        'Estimated soil-temperature freezing proxy (not ice)':'Низька впевненість · температура ґрунту (НЕ лід)',
        'Estimated air-freezing proxy (not ice)':'Дуже низька впевненість · температура повітря (НЕ лід)',
    }
    rows=[]
    for key,title in titles.items():
        value=observations.get('scores',{}).get(key)
        kind=observations.get('evidence_types',{}).get(key,'')
        rows.append({'Критерій':title,
                     'Статус':('Наближено' if 'Estimated ' in kind else 'Оцінено') if value is not None else 'Не підтверджено',
                     'Тип доказів':evidence_names.get(kind,'Відсутні перевірені дані'),
                     'Джерело':observations.get('sources',{}).get(key,'—')})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.caption('Оцінка 0–100 — корисність для наземних випробувань, а не виміряний відсоток схожості з іншою планетою.')


def nsidc_upload_panel(point):
    with st.expander('🧊 NASA NSIDC — карта мерзлоти та ґрунтового льоду', expanded=False):
        st.write('**GGD318 v2:** карта Північної півкулі, регіональна класифікація багаторічної мерзлоти та льоду. '
                 'Тут не використовується температура повітря для вигадування факту наявності льоду.')
        st.caption('Автоматичного точкового API для GGD318 немає. Завантажте офіційний GIS-набір, '
                   'за потреби обріжте в QGIS, переведіть геометрію в EPSG:4326 і експортуйте GeoJSON. '
                   'Нормалізуйте поля `permafrost_extent` (continuous/discontinuous/sporadic/isolated/none/unknown) '
                   'та `ground_ice_category` (high/medium/low/none/unknown) за легендою оригінальної карти.')
        st.link_button('Офіційний набір NASA NSIDC GGD318',NSIDC_URL)
        upload=st.file_uploader('Завантажити підготовлений GeoJSON GGD318 (макс. 15 МБ)',type=['geojson','json'],key='tt_nsidc_upload_control')
        if upload is not None:
            if upload.size>15_000_000:
                st.warning('Файл занадто великий. Обріжте шар до досліджуваного району.')
            else:
                st.session_state['tt_nsidc_geojson']=upload.getvalue()
        if st.session_state.get('tt_nsidc_geojson') is not None:
            if st.button('Очистити імпортований GIS-шар',key='tt_nsidc_clear'):
                st.session_state.pop('tt_nsidc_geojson',None)
                st.rerun()
        record=imported_ground_ice(point['lat'],point['lon'])
        status=record['status']
        if status=='mapped_class':
            st.success('Знайдено картографічний полігон NSIDC для активної точки.')
            st.write(f"**Мерзлота:** {record['permafrost_extent']} · **Ґрунтовий лід:** {record['ground_ice_category']}")
            st.caption('Регіональна класифікація за історичною картою, а не виміряна концентрація льоду в точці.')
        elif status=='outside_coverage':
            st.info('Поза межами просторового охоплення набору GGD318; місцевий лід залишається невідомим.')
        elif status=='in_extent_unchecked':
            st.info('Координата в географічних межах набору, але GIS-шар не імпортовано. Лід — невідомо.')
        elif status=='invalid_import':
            st.error('Некоректний GIS-файл: '+record['note'])
        else:
            st.warning(record['note'])
        return record


def geology_materials_panel(geo):
    st.markdown('**🪨 Матеріали та породи: наукове походження оцінки**')
    result=mapped_materials(geo)
    if result['status']=='mapped_proxy':
        a,b=st.columns(2)
        localized_metric(a,'Орієнтовна придатність геології для земних випробувань',f"{round(result['score']*100)} / 100")
        localized_metric(b,'Класифіковано одиниць на карті',str(len(result['matches'])))
        st.dataframe(pd.DataFrame([{'Картографічна одиниця':r['unit'],'Літологія':r['lithology'],
                                   'Випробувальний тип':r['description'],'ID карти':r['map_id']}
                                  for r in result['matches']]),hide_index=True,use_container_width=True)
        st.caption('Це авторська шкала користі для геологічних випробувань, НЕ лабораторний аналіз та НЕ відсоток схожості з планетою.')
        st.link_button('Запит Macrostrat, з якого взято літологію',result['source_url'])
    else:
        point=ensure_location(st.session_state)
        match=nearby_site(point['lat'],point['lon'],load_sites(),radius_km=8)
        glim=imported_glim(point['lat'],point['lon'])
        evidence=derive_observations(None,None,site_id=match['id'] if match else None,
                                     geology=geo,glim=glim)
        material=evidence['scores'].get('materials')
        if material is None:
            st.info('У наявних джерелах поки немає перевіреного типу порід. Це не доказ відсутності порід. Для додаткових даних скористайтеся GLiM або картою регіону.')
        else:
            st.metric('Орієнтовна придатність матеріалів для земних випробувань',f'{round(material*100)} / 100')
            st.write(evidence['notes']['materials'])
            st.caption('Тип доказів: '+evidence['evidence_types']['materials'])
            st.link_button('Відкрити наукове джерело',evidence['sources']['materials'])


def render_sources(sites):
    section('07 / SCIENTIFIC DATA HUB', 'Дані й наукові джерела',
            'Знайди вимірювання для вибраної точки та перевір, звідки отримано кожну характеристику.')
    point=ensure_location(st.session_state)
    show_active_point()
    st.info('Джерела для автоматичних запитів: NASA POWER, Open-Meteo (резерв), Copernicus DEM та Macrostrat. '
            'SoilGrids, NSIDC, EMIT, LOLA, Diviner, SWIM, MOLA та CRISM містять наукові набори, '
            'але не всі надають доступні без реєстрації числові відповіді за одним кліком.')
    col1,col2=st.columns([1.4,1],gap='large')
    with col1:
        year=st.selectbox('Рік кліматичних даних (NASA / ERA5)', [2025,2024,2023,2022,2021], key='tt_data_hub_year')
    with col2:
        st.write('**Поточна точка:** '+localized_point())
        st.caption(f"{point['lat']:.4f}°; {point['lon']:.4f}°")
    if st.button('🛰️ Отримати всі доступні числові дані',type='primary',use_container_width=True):
        with st.spinner('NASA POWER, Copernicus DEM і Macrostrat…'):
            point_lookups(point['lat'],point['lon'],include_weather=True,year=year)
    record=st.session_state.get('tt_point_sources',{})
    key=(round(point['lat'],4),round(point['lon'],4))
    active_record = record if record.get('key')==key else {}
    if active_record.get('errors'):
        st.info('Деякі наукові джерела тимчасово недоступні. Уже отримані дані залишаються чинними; резервні джерела наведені нижче.')
        with st.expander('Деталі стану зовнішніх сервісів'):
            for source_id, err in active_record['errors'].items():
                st.caption(BY_ID[source_id]['name']+': '+err)
    weather=weather_result_for_current(year)
    terrain=active_record.get('terrain')
    geology=active_record.get('geology')
    st.subheader('Показники вибраної точки')
    st.caption('Доступність джерела ≠ наявність усіх показників. Невідомі дані ніколи не замінюються вигаданими значеннями.')
    a,b,c=st.columns(3)
    localized_metric(a,'Клімат (NASA / Open-Meteo)', 'Отримано' if weather else 'Не завантажено')
    localized_metric(b,'Copernicus DEM', 'Отримано' if terrain else 'Не завантажено')
    localized_metric(c,'Macrostrat', 'Є геологія' if geology and geology['status']=='ok' else ('Немає покриття' if geology else 'Не завантажено'))
    if weather:
        st.markdown('**Метеорологічні та сонячні дані**')
        summary_metrics(weather['data'])
        quality_note('weather')
        st.caption(f"Отримано {len(weather['data'])} рядків щоденних даних; повнота відносно повного календарного року:")
        st.dataframe(pd.DataFrame([{'Показник':k,'Повнота':str(v)+'%'} for k,v in dataset_completeness(weather['data']).items()]),hide_index=True,use_container_width=True)
        st.caption('Використаний кліматичний сервіс: '+weather.get('provider','NASA POWER'))
        st.link_button('Оригінальний запит до даних',weather['url'])
    if terrain:
        st.markdown('**Рельєф і висота**')
        t1,t2,t3=st.columns(3)
        localized_metric(t1,'Висота',f"{terrain['elevation_m']:.0f} м")
        localized_metric(t2,'Приблизний ухил',f"{terrain['slope_deg']:.2f}°")
        localized_metric(t3,'Локальний перепад',f"{terrain['relief_m']:.0f} м")
        source_link('copernicus')
        quality_note('terrain')
    st.subheader('Геологія та гірські породи · Macrostrat')
    geology_block(geology)
    geology_materials_panel(geology)
    if weather and mapped_materials(geology).get('status') != 'mapped_proxy':
        from estimate_context import surface_materials_proxy, freezing_proxy
        mp=surface_materials_proxy(weather['data'],terrain,weather['url'])
        soil_daily=active_record.get('soil_climate') if active_record.get('soil_year')==year else None
        ip=freezing_proxy(weather['data'],soil_daily,weather['url'])
        with st.expander('Непрямі оцінки, якщо карт немає · не вимірювання порід чи льоду',expanded=False):
            if mp:
                st.write('**Поверхневі умови (не літологія):** '+str(round(mp['score']*100))+'/100')
                st.caption(mp['note'])
            if ip:
                st.write('**Умови промерзання (не наявність льоду):** '+str(round(ip['score']*100))+'/100')
                st.caption(ip['note'])
            if not mp and not ip:
                st.info('Немає достатньо даних навіть для коректної приблизної оцінки.')
            st.link_button('Метод даних ґрунту та клімату · Open-Meteo',ARCHIVE_DOC)
    st.caption('Якщо Macrostrat не повернув карту, перевірте опис підтвердженого аналога або завантажте фрагмент GLiM нижче.')
    glim_upload_panel(point)
    st.caption('Резервні літологічні дані GLiM не означають автоматичного підтвердження мінерального складу в конкретній точці.')
    nsidc_upload_panel(point)
    with st.expander('Ґрунт: SoilGrids (спроба резервного REST API)',expanded=False):
        st.warning('Офіційна документація ISRIC повідомляє про призупинення REST API. '
                   'Для гарантованої роботи потрібні WCS, WebDAV або завантажені GIS-файли. '
                   'Ми не підставляємо жодних фіктивних цифр.')
        source_link('soilgrids','Документація SoilGrids та варіанти WCS/WebDAV')
        if st.button('Спробувати REST (може не працювати)',key='tt_soil_request'):
            try:
                with st.spinner('Звертаємося до ISRIC…'):
                    st.session_state['tt_soil']={'key':key,'data':load_soil(*key)}
            except SoilError as exc:
                st.warning(str(exc))
        soil=st.session_state.get('tt_soil',{})
        if soil.get('key')==key:
            items=soil.get('data',{}).get('items',[])
            if items:
                st.dataframe(pd.DataFrame(items),hide_index=True,use_container_width=True)
                st.caption('Raw значення моделі + масштабний коефіцієнт. Перевіряйте одиниці й d_factor за метаданими ISRIC.')
            else:
                st.info('ISRIC не повернула вимірювань для точки.')
    st.divider()
    with st.expander('Як читати ці результати й обмеження точності'):
        for key in ('weather','terrain','geology','planet'):
            quality_note(key)
        st.write('Значення «немає даних», «немає покриття» та «сервіс недоступний» означають різні речі. Жодне не дорівнює нулю.')
    st.subheader(ui_text('🛰️ Satellite image discovery · NASA & Copernicus', '🛰️ Пошук супутникових знімків · NASA та Copernicus'))
    st.caption(ui_text('These are live catalog searches for available datasets and scenes around the selected coordinates. Metadata is NOT a measured value and does not automatically increase scientific scores.', 'Це пошук доступних наборів даних і знімків за вибраними координатами. Метадані НЕ є вимірюванням і не підвищують автоматично наукову оцінку.'))
    if st.button(ui_text('Search NASA Earthdata and Copernicus for this location', 'Знайти дані NASA Earthdata та Copernicus для цієї точки'),key='tt_search_satellites'):
        with st.spinner(ui_text('Searching public NASA CMR and Copernicus STAC catalogs…', 'Шукаємо дані у відкритих каталогах NASA CMR і Copernicus STAC…')):
            results={'point':key,'year':year}
            try:results['nasa']=load_nasa_collections(*key)
            except CatalogUnavailable as exc:results['nasa_error']=str(exc)
            try:results['copernicus']=load_sentinel_scenes(*key,year)
            except CatalogUnavailable as exc:results['copernicus_error']=str(exc)
            st.session_state['tt_satellite_discovery']=results
    discovery=st.session_state.get('tt_satellite_discovery',{})
    if discovery.get('point')==key and discovery.get('year')==year:
        left,right=st.columns(2)
        with left:
            st.markdown('**NASA Earthdata · CMR**')
            if discovery.get('nasa_error'):st.warning(discovery['nasa_error'])
            if not discovery.get('nasa'):st.info(ui_text('No NASA collections returned for this query.', 'За цим запитом колекцій NASA не знайдено.'))
            for i,source in enumerate(discovery.get('nasa',[])):
                st.link_button(source['name'][:70],source['url'])
        with right:
            st.markdown('**ESA Copernicus · Sentinel-2 L2A**')
            if discovery.get('copernicus_error'):st.warning(discovery['copernicus_error'])
            if not discovery.get('copernicus'):st.info(ui_text('No Sentinel-2 scenes returned for this year and location.', 'Для вибраного року й території знімків Sentinel-2 не знайдено.'))
            for i,scene in enumerate(discovery.get('copernicus',[])):
                cloud=scene.get('cloud_cover')
                name=(scene.get('datetime') or scene['name'])[:20]
                st.link_button(name+((' · cloud ' if st.session_state.get('tt_lang','en')=='en' else ' · хмарність ')+str(cloud)+'%' if cloud is not None else ''),scene['url'])
    st.caption(ui_text('Catalog sources: NASA Earthdata CMR Search API and Copernicus Data Space STAC API. Some downloads may require authentication.', 'Джерела каталогів: NASA Earthdata CMR Search API та Copernicus Data Space STAC API. Для деяких завантажень потрібен обліковий запис.'))
    st.subheader('Каталог наукових джерел')
    world=st.selectbox('Територія даних',['Усі','Земля','Місяць','Марс'],key='tt_data_world')
    topics=sorted({x['topic'] for x in SOURCES})
    topic=st.selectbox('Тематика',['Усі']+topics,key='tt_data_topic')
    filtered=[s for s in SOURCES if (world=='Усі' or s['world']==world) and (topic=='Усі' or s['topic']==topic)]
    st.caption(f'Показано {len(filtered)} із {len(SOURCES)} перевірених наборів даних')
    for src0 in filtered:
        src=display_source(src0,st.session_state.get('tt_lang','en'))
        with st.expander(f"{src['world']} · {src['name']} — {src['mode']}"):
            st.write('**Що містить:** '+src['what'])
            st.write('**Обмеження:** '+src['limits'])
            st.caption('Організація: '+src['provider']+' · Режим: '+src['mode'])
            st.markdown(f"[Відкрити наукове джерело]({src['url']})")
    st.divider()
    st.subheader('Планетарні райони для порівняння')
    for tid,target in BASE_TARGETS.items():
        with st.expander(target['name']):
            st.write(target['context'])
            st.caption(target['status'])
            st.link_button('Джерело району',target['source'])
            render_planetary_sources(tid)
    payload={
        'project':'TerraTwin', 'version':BUILD,'point':point,'year':year,
        'weather_url':weather['url'] if weather else None,
        'terrain':terrain,'geology':geology,
        'ground_ice':imported_ground_ice(point['lat'],point['lon']),
        'materials_interpretation':mapped_materials(geology),
        'catalog':SOURCES,
        'notice':'Unavailable planetary GIS layers are catalogued, not automatically converted to point measurements.'
    }
    st.download_button('⬇ Завантажити дані, обмеження й джерела (JSON)',
                       json.dumps(payload,ensure_ascii=False,indent=2,default=str).encode('utf-8'),
                       file_name='TerraTwin_sources_and_point.json',mime='application/json')


def section(tag:str, title:str, subtitle:str):
    # Native Streamlit text blocks: do not replace/reactively mutate DOM children.
    st.caption(tag)
    st.header(title)
    st.write(subtitle)


def go_to(page:str):
    # Widget callback runs before new page's navigation radio is instantiated.
    set_page(st.session_state, page)


def make_active(lat,lon,label):
    set_location(st.session_state,lat,lon,label)
    p=ensure_location(st.session_state)
    for site in load_sites():
        if abs(site['latitude']-p['lat'])<0.0001 and abs(site['longitude']-p['lon'])<0.0001:
            p.update({'known_site':True,'name_en':site.get('name_en',site['name']),
                      'name_uk':site['name'],'user_selected':True})
            break



def show_active_point(compact=False):
    loc=ensure_location(st.session_state)
    if loc.get('user_selected') and not loc.get('known_site'):
        st.caption(ui_text('Approximate place label © OpenStreetMap contributors (Nominatim); coordinates are shown separately. Location lookup is sent to an external mapping service.', 'Приблизна назва місця © учасники OpenStreetMap (Nominatim); координати показано окремо. Запит назви надсилається зовнішньому картографічному сервісу.'))
    if compact:
        st.caption(f"📍 Вибрано: {localized_point()} · {loc['lat']:.4f}°, {loc['lon']:.4f}°")
    else:
        st.info(f"📍 **Активна точка:** {localized_point()} · {loc['lat']:.4f}°, {loc['lon']:.4f}°. "
                'Вона доступна в «Науковому аналозі», «Даних NASA» та «Графіках».')


def weather_result_for_current(year:int):
    active=ensure_location(st.session_state)
    return st.session_state.get('tt_weather_cache',{}).get(dataset_key(active['lat'],active['lon'],year))


def get_weather(lat,lon,year, set_as_active=False):
    """One consistent cache shared by site analyzer, NASA section and plots."""
    key=dataset_key(lat,lon,year)
    cache=st.session_state.setdefault('tt_weather_cache',{})
    if key in cache:
        result=cache[key]
    else:
        primary_error=None
        try:
            daily,url=load_nasa(*key)
            provider='NASA POWER'
            # A partial primary year must not be used as a full yearly profile.
            completeness=dataset_completeness(daily)
            needed=(LABELS['T2M'],LABELS['T2M_MIN'],LABELS['T2M_MAX'],LABELS['ALLSKY_SFC_SW_DWN'])
            if min(completeness[x] for x in needed) < 90 or completeness[LABELS['PRECTOTCORR']] < 95:
                primary_error='Partial NASA POWER year; used reanalysis when available.'
                try:
                    daily,url=load_archive(*key)
                    provider='Open-Meteo historical reanalysis'
                except ArchiveError:
                    # Keep partial observations. Annual checks still prevent ungrounded scores.
                    provider='NASA POWER (partial year)'
        except NASADataError as exc:
            primary_error=str(exc)
            try:
                daily,url=load_archive(*key)
            except ArchiveError as fallback_exc:
                raise NASADataError('NASA POWER і резервний Open-Meteo наразі недоступні. Перевірте інтернет або повторіть запит.') from fallback_exc
            provider='Open-Meteo historical reanalysis'
        result={'key':key,'year':year,'data':daily,'url':url,'provider':provider,
                'fallback_note':primary_error,'report':analyze_climate(daily)}
        cache[key]=result
    active=ensure_location(st.session_state)
    if set_as_active and (active['lat'],active['lon']) == key[:2]:
        st.session_state['tt_active_analysis']=result
    return result


def nasa_failure(exc:Exception,lat,lon,year):
    st.error(f'Не вдалося отримати дані NASA POWER: {exc}')
    st.caption('Це не означає, що територія непридатна для досліджень. Без перевірених даних оцінку не створюємо.')
    with st.expander('Перевірити запит і документацію NASA'):
        st.write('Адреса нижче містить звичайні роздільники `&` (без зворотних скісних рисок).')
        st.code(make_power_url(lat,lon,year),language=None)
        st.link_button('Документація NASA POWER',NASA_DOCS)


def climate_metric_labels(lang: str) -> dict[str, str]:
    """Localized climate-summary labels, status strings, and units.

    Do not rely on the general Streamlit text wrapper for these values: this
    also keeps units consistently in the selected language across all pages.
    """
    if lang == 'uk':
        return {
            'temperature': 'Середня температура',
            'precipitation': 'Опади за рік',
            'wind': 'Середній вітер',
            'solar': 'Сонячна енергія / день',
            'insufficient': 'Недостатньо даних',
            'incomplete': 'Неповний рік',
            'precip_unit': 'мм',
            'wind_unit': 'м/с',
            'solar_unit': 'кВт·год/м²',
        }
    return {
        'temperature': 'Mean temperature',
        'precipitation': 'Annual precipitation',
        'wind': 'Mean wind speed',
        'solar': 'Daily solar energy',
        'insufficient': 'Insufficient data',
        'incomplete': 'Incomplete year',
        'precip_unit': 'mm',
        'wind_unit': 'm/s',
        'solar_unit': 'kWh/m²',
    }


def summary_metrics(daily):
    text = climate_metric_labels(st.session_state.get('tt_lang', 'en'))
    a,b,c,d=st.columns(4)
    t=daily[LABELS['T2M']].mean()
    p=daily[LABELS['PRECTOTCORR']].sum(min_count=1)
    w=daily[LABELS['WS10M']].mean()
    solar=daily[LABELS['ALLSKY_SFC_SW_DWN']].mean() if LABELS['ALLSKY_SFC_SW_DWN'] in daily else float('nan')
    completeness = dataset_completeness(daily)
    localized_metric(a,text['temperature'], f'{t:.1f} °C' if pd.notna(t) and completeness[LABELS['T2M']] >= 90 else text['insufficient'])
    localized_metric(b,text['precipitation'], f"{p:.1f} {text['precip_unit']}" if pd.notna(p) and completeness[LABELS['PRECTOTCORR']] >= 95 else text['incomplete'])
    localized_metric(c,text['wind'], f"{w:.1f} {text['wind_unit']}" if pd.notna(w) and completeness[LABELS['WS10M']] >= 90 else text['insufficient'])
    localized_metric(d,text['solar'], f"{solar:.2f} {text['solar_unit']}" if pd.notna(solar) and completeness[LABELS['ALLSKY_SFC_SW_DWN']] >= 90 else text['insufficient'])


def chart_weather(daily,dark):
    monthly=monthly_summary(daily)
    c1,c2=st.columns(2)
    with c1:
        st.plotly_chart(weather_temperature_chart(monthly,LABELS['T2M'],dark=dark,lang=st.session_state.get('tt_lang','en')),use_container_width=True)
    with c2:
        st.plotly_chart(weather_precip_chart(monthly,dark=dark,lang=st.session_state.get('tt_lang','en')),use_container_width=True)


def climate_report(result):
    report=result['report']
    col_moon,col_mars=st.columns(2)
    for col,name,key in [(col_moon,'Місяць','moon'),(col_mars,'Марс','mars')]:
        with col:
            with st.container(border=True):
                st.subheader(('🌕 ' if key=='moon' else '🔴 ')+name)
                score=report[key]['score']
                if score is None:
                    st.warning('Недостатньо кліматичних даних')
                else:
                    st.metric('Індекс умов для наземних випробувань',f'{score} / 100')
                    st.progress(max(0.0,min(1.0,score/100.0)))
                st.caption(f"Повнота кліматичних показників: {report[key]['coverage']}%")
                for part in report[key]['parts']:
                    value='Немає даних' if part['value'] is None else f"{part['value']}/100"
                    st.write(f"{part['name']} — {value}; вага {int(part['weight']*100)}%")
    st.caption('Кліматичне джерело: '+result.get('provider','NASA POWER')+' · Модельні дані, не покази локального датчика.')
    st.caption('**Важливо:** оцінка описує лише зручність певних земних кліматичних випробувань. '
               'Це не відсоток фізичної схожості з планетою та не оцінка безпечності побудови бази.')
    st.subheader('Наукове пояснення')
    for message in report['conclusions']:
        st.write('• '+message)
    with st.expander('Методика обчислення'):
        for name,formula in report['method'].items():
            st.code(f'{name}: {formula}',language=None)
        st.caption('Порогові значення та ваги обрані авторами TerraTwin, не NASA.')
    with st.expander('Джерело щоденних даних'):
        st.code(result['url'],language=None)
        st.link_button('Відкрити оригінальний запит до даних',result['url'])
        st.link_button('Документація API',ARCHIVE_DOC if result.get('provider','').startswith('Open-Meteo') else NASA_DOCS)


def render_pick_map(sites,dark):
    active=ensure_location(st.session_state)
    m=build_world_map(sites,dark=dark,picked=(active['lat'],active['lon']),
                      fit_sites=False,center=(active['lat'],active['lon']),zoom=3,lang=st.session_state.get('tt_lang','en'))
    response=st_folium(m,height=475,use_container_width=True,
                       returned_objects=['last_clicked'],
                       key=f"tt_choose_{'dark' if dark else 'light'}_{st.session_state['tt_location_revision']}")
    click=response.get('last_clicked') if isinstance(response,dict) else None
    if isinstance(click,dict) and 'lat' in click and 'lng' in click:
        try:
            changed=select_custom_point(click['lat'],click['lng'],'Selected on map')
        except (ValueError,TypeError):
            changed=False
        if changed:
            st.rerun()
    st.caption('© OpenStreetMap · Шари (угорі праворуч): Macrostrat та ESA WorldCover. Клацніть для вибору точки. Шари — візуальні, не вимірювання.')


def render_pick(sites,dark):
    section('01 / LOCATION WORKSPACE','Обери місце на Землі',
            'Натисни на карту, введи координати або вибери вже досліджену територію.')
    show_active_point()
    st.caption('Як користуватися: ① оберіть місце → ② відкрийте «Підготовка бази» або «Науковий аналог» → ③ перевірте повноту даних і джерела → ④ експортуйте висновок.')
    mode_a,mode_b=st.columns(2,gap='medium')
    with mode_a:
        with st.container(border=True):
            st.subheader('🔬 Науковий аналог')
            st.write('Геологія та форми рельєфу Землі проти конкретного району Місяця або Марса.')
            st.button('Відкрити науковий аналіз',on_click=go_to,args=('Науковий аналог',),
                      use_container_width=True,key='tt_home_science')
    with mode_b:
        with st.container(border=True):
            st.subheader('🚀 Підготовка космічної бази')
            st.write('Шість критеріїв для випробувань, прив’язаних до планетарного району-кандидата.')
            st.button('Перейти до сценаріїв баз',on_click=go_to,args=('Підготовка бази',),
                      use_container_width=True,key='tt_home_base')
    left,right=st.columns([1.6,1],gap='large')
    with left:
        render_pick_map(sites,dark)
    with right:
        st.subheader('Вибір місця')
        loc=ensure_location(st.session_state)
        with st.form(key=f"tt_coord_form_{st.session_state['tt_location_revision']}"):
            lat=st.number_input('Широта (°)',min_value=-89.9,max_value=89.9,
                                value=float(loc['lat']),format='%.4f')
            lon=st.number_input('Довгота (°)',min_value=-180.0,max_value=180.0,
                                value=float(loc['lon']),format='%.4f')
            submitted=st.form_submit_button('Вибрати ці координати',use_container_width=True)
        if submitted:
            select_custom_point(lat,lon,'Entered coordinates')
            st.rerun()
        st.markdown('**Готові локації**')
        for s in sites:
            st.button(s.get('name_en',s['name']) if st.session_state.get('tt_lang')=='en' else s['name'],key=f"tt_pick_site_{s['id']}",use_container_width=True,
                      on_click=make_active,args=(s['latitude'],s['longitude'],s['name']))
    st.divider()
    st.subheader('Що зробити з обраною точкою?')
    b1,b2,b3,b4=st.columns(4)
    with b1:
        st.button('🔬 Науковий аналог',use_container_width=True,type='primary',
                  on_click=go_to,args=('Науковий аналог',))
    with b2:
        st.button('🚀 Підготовка бази',use_container_width=True,
                  on_click=go_to,args=('Підготовка бази',))
    with b3:
        st.button('🛰️ Дані NASA',use_container_width=True,
                  on_click=go_to,args=('Дані NASA',))
    with b4:
        st.button('📚 Джерела й дані',use_container_width=True,
                  on_click=go_to,args=('Джерела та дані',))
    st.divider()
    st.subheader('Швидкий кліматичний аналіз')
    year=st.selectbox('Рік NASA POWER',[2025,2024,2023,2022,2021],key='tt_pick_year')
    loc=ensure_location(st.session_state)
    if st.button('Проаналізувати точку за даними NASA',type='primary',key='tt_go_analyze'):
        try:
            with st.spinner('Отримуємо щоденні вимірювання…'):
                get_weather(loc['lat'],loc['lon'],year,set_as_active=True)
        except NASADataError as exc:
            nasa_failure(exc,loc['lat'],loc['lon'],year)
    result=analysis_for_active(st.session_state)
    if result:
        st.caption(f"Дані за {result['year']} рік · {localized_point()}")
        summary_metrics(result['data'])
        climate_report(result)
        st.button('Відкрити графіки для цієї точки',on_click=open_active_charts)
    else:
        st.info('Завантажені дані та аналіз для активної точки з’являться тут і в інших розділах.')


def render_atlas(sites,dark):
    section('02 / EARTH ATLAS','Карта відомих земних аналогів',
            'П’ять задокументованих аналогових територій. Будь-яку можна додати до власного аналізу.')
    show_active_point(compact=True)
    planet=st.radio('Показати аналоги',['Усі','Місяць','Марс'],horizontal=True,key='tt_atlas_filter')
    subset=[s for s in sites if planet=='Усі' or s['planet']==planet]
    labels={s['id']:(s.get('name_en',s['name']) if st.session_state.get('tt_lang')=='en' else s['name']) for s in subset}
    sid=st.selectbox('Територія',list(labels),format_func=lambda key:labels[key],key='tt_atlas_site_'+planet)
    selected=next(s for s in subset if s['id']==sid)
    left,right=st.columns([1.6,1],gap='large')
    with left:
        m=build_world_map(subset,selected_id=sid,dark=dark,
                          picked=(ensure_location(st.session_state)['lat'],ensure_location(st.session_state)['lon']),lang=st.session_state.get('tt_lang','en'))
        st_folium(m,height=465,use_container_width=True,returned_objects=[],key=f'tt_atlas_map_{planet}_{dark}')
    with right:
        en=st.session_state.get('tt_lang')=='en'
        st.subheader(selected.get('name_en',selected['name']) if en else selected['name'])
        st.caption(f"{selected.get('country_en',selected['country']) if en else selected['country']} · {selected.get('terrain_en',selected['terrain']) if en else selected['terrain']}")
        st.write(selected.get('description_en',selected['description']) if en else selected['description'])
        st.write(('**Why it is useful:** ' + selected.get('similar_en',selected['similar'])) if en else '**Чим схоже:** '+selected['similar'])
        st.write(('**Key differences:** ' + selected.get('different_en',selected['different'])) if en else '**Важлива відмінність:** '+selected['different'])
        st.write(('**Possible tests:** ' + selected.get('use_case_en',selected['use_case'])) if en else '**Можливі випробування:** '+selected['use_case'])
        st.link_button('Наукове джерело',selected['source_url'])
        st.button('📍 Використати цю точку в усіх розділах',type='primary',
                  on_click=make_active,args=(selected['latitude'],selected['longitude'],selected['name']),
                  use_container_width=True)


def saved_weights(target):
    defaults=SCIENCE_TARGETS[target]['weights']
    existing=st.session_state.setdefault('tt_saved_weights',{}).get(target,defaults)
    return {feature:int(existing.get(feature,default)) for feature,default in defaults.items()}


def update_weight(target,feature):
    key=f'tt_w_{target}_{feature}'
    st.session_state.setdefault('tt_saved_weights',{}).setdefault(target,{})[feature]=int(st.session_state[key])


def reset_weights(target):
    st.session_state.setdefault('tt_saved_weights',{})[target]=dict(SCIENCE_TARGETS[target]['weights'])
    for feature,value in SCIENCE_TARGETS[target]['weights'].items():
        st.session_state[f'tt_w_{target}_{feature}']=value


def render_compare(sites,evidence,dark):
    section('02 / SCIENTIFIC ANALOG','Науковий аналог',
            'Порівнюй задокументовані ознаки земної ділянки з конкретним планетарним районом.')
    show_active_point()
    target=st.selectbox('Планетарний об’єкт',list(SCIENCE_TARGETS),
                        format_func=lambda k:SCIENCE_TARGETS[k]['name'],key='tt_target')
    st.session_state['tt_last_target']=target
    st.caption(translate(SCIENCE_TARGETS[target]['description'],st.session_state.get('tt_lang','en')))
    col_w,col_r=st.columns([1,1.55],gap='large')
    with col_w:
        st.subheader('Важливість ознак')
        weights={}
        for feature,default in saved_weights(target).items():
            key=f'tt_w_{target}_{feature}'
            st.session_state.setdefault(key,default)
            weights[feature]=st.slider(FEATURES[feature],0,5,key=key,on_change=update_weight,args=(target,feature))
        st.button('Повернути стандартні ваги',on_click=reset_weights,args=(target,))
        st.caption('0 — не враховувати, 5 — найважливіше. Значення оновлюють рейтинг.')
    if not sum(weights.values()):
        st.warning('Оберіть хоча б одну ознаку з ненульовою важливістю.')
        return
    ranking=rank_analogs(sites,evidence,target,weights)
    with col_r:
        st.subheader('Рейтинг досліджених локацій')
        for i,item in enumerate(ranking,1):
            with st.container(border=True):
                s=item['site'];score=item['score']; coverage=item['calculation']['coverage']
                c1,c2=st.columns([3,1])
                c1.markdown(f"**{i}. {s.get('name_en', s['name']) if st.session_state.get('tt_lang','en')=='en' else s['name']}**")
                if coverage == 0:
                    c2.markdown('**Unknown**' if st.session_state.get('tt_lang','en')=='en' else '**Невідомо**')
                    st.progress(0)
                else:
                    c2.markdown(f'**{score} / 100**')
                    st.progress(score/100)
                st.caption(f"Наукове покриття: {coverage}% · {translate(s['country'], st.session_state.get('tt_lang','en'))}")
                verdict=classify_analog(score,coverage,lang=st.session_state.get('tt_lang','en'))
                st.caption('Оцінка доказовості: '+verdict['title'])
        st.caption('Індекс доказовості за обраними геологічними ознаками; це НЕ фізичний відсоток подібності. Невідомі ознаки зменшують покриття доказами.')
    st.subheader('Пояснення оцінок')
    byid={item['site']['id']:item for item in ranking}
    selected_id=st.selectbox('Детальний розрахунок',list(byid),
                             format_func=lambda k:byid[k]['site'].get('name_en',byid[k]['site']['name']) if st.session_state.get('tt_lang','en')=='en' else byid[k]['site']['name'],key=f'tt_evidence_{target}')
    chosen=byid[selected_id]
    calc=chosen['calculation']
    st.write(f"**Формула:** 100 × {calc['raw']:g} / {calc['total']} ≈ **{calc['score']} / 100**")
    analog_verdict=classify_analog(calc['score'],calc['coverage'],lang=st.session_state.get('tt_lang','en'))
    st.info('**'+analog_verdict['title']+'** — '+analog_verdict['description'])
    st.caption(analog_verdict['disclaimer'])
    rows=[]
    for cr in calc['criteria']:
        rows.append({'Критерій':FEATURES[cr['feature']], 'Вага':cr['weight'],
                     'Докази':{'yes':'Підтверджено','partial':'Частково','unknown':'Немає даних'}[cr['status']],
                     'Внесок':cr['contribution']})
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    with st.expander('Наукові джерела'):
        for cr in calc['criteria']:
            st.write('**'+FEATURES[cr['feature']]+'** — '+cr['note'])
            if cr.get('source_url'):
                st.link_button('Джерело: '+FEATURES[cr['feature']],cr['source_url'])
    st.download_button('Завантажити геологічний рейтинг (CSV)',
                       ranking_csv(ranking,SCIENCE_TARGETS[target]['name'],weights),
                       file_name='TerraTwin_geology_ranking.csv',mime='text/csv')
    st.divider()
    st.subheader('📍 Що з моєю точкою?')
    loc=ensure_location(st.session_state)
    known=nearby_site(loc['lat'],loc['lon'],sites)
    if known:
        st.success(ui_text(f"The selected point is near documented site “{known.get('name_en',known['name'])}”. Published geology descriptions are available.", f"Вибрана точка розташована поблизу дослідженої території «{known['name']}». Для неї доступні перевірені геологічні описи."))
    else:
        st.info('Це довільна точка: рейтинг задокументованих локацій не присвоюється їй автоматично. '
                'Однак тепер можна запитати геологічні карти Macrostrat для її координат.')
    point_record=st.session_state.get('tt_point_sources',{})
    if point_record.get('key')==(round(loc['lat'],4),round(loc['lon'],4)) and point_record.get('geology'):
        geology_block(point_record['geology'])
    elif st.button('🌍 Отримати геологічну карту моєї точки',key='tt_geo_compare'):
        try:
            geodata=load_geology(loc['lat'],loc['lon'])
            st.session_state['tt_point_sources']={
                'key':(round(loc['lat'],4),round(loc['lon'],4)),
                'geology':geodata,'terrain':None,'retrieved':['macrostrat'],'errors':{},
            }
            geology_block(geodata)
        except GeologyError as exc:
            st.warning(str(exc))
    render_planetary_sources(target)
    active=analysis_for_active(st.session_state)
    if active:
        st.write(ui_text(f"**Climate assessment for {active['year']}:**", f"**Кліматична оцінка точки за {active['year']} рік:**"))
        climate_report(active)
    else:
        st.button('Перейти до NASA POWER для моєї точки',type='primary',
                  on_click=go_to,args=('Дані NASA',))


def render_nasa(sites,dark):
    section('04 / NASA POWER','Метеорологічні дані NASA',
            'Завантаження даних для активної точки або дослідженої території.')
    show_active_point(compact=True)
    options=['Активна точка']+[s['name'] for s in sites]
    choice=st.selectbox('Для якого місця завантажити дані?',options,key='tt_nasa_choice')
    if choice=='Активна точка':
        loc=ensure_location(st.session_state)
        lat,lon,name=loc['lat'],loc['lon'],localized_point()
    else:
        s=next(x for x in sites if x['name']==choice)
        lat,lon,name=s['latitude'],s['longitude'],s.get('name_en',s['name']) if st.session_state.get('tt_lang','en')=='en' else s['name']
    year=st.selectbox('Рік',[2025,2024,2023,2022,2021],key='tt_nasa_year')
    st.write(f"**Координати:** {lat:.4f}°, {lon:.4f}° · {localized_point() if choice=='Активна точка' else name}")
    st.caption('Кліматичні дані — NASA POWER або резервний Open-Meteo; обидва джерела містять сіткові модельні оцінки, а не локальні датчики.')
    if st.button('🛰️ Завантажити кліматичні дані',type='primary'):
        try:
            with st.spinner('Отримуємо щоденні кліматичні дані…'):
                get_weather(lat,lon,year,set_as_active=(choice=='Активна точка'))
        except NASADataError as exc:
            nasa_failure(exc,lat,lon,year)
    key=dataset_key(lat,lon,year)
    result=st.session_state.setdefault('tt_weather_cache',{}).get(key)
    if result is None:
        st.info('Виберіть точку та натисніть «Завантажити». Після цього дані будуть доступні і в «Графіках».')
        with st.expander('Показати правильно сформований запит до NASA'):
            st.code(make_power_url(lat,lon,year),language=None)
            st.link_button('Документація NASA POWER',NASA_DOCS)
        return
    st.success('Дані отримані та збережені для роботи у поточній сесії.')
    st.caption('Постачальник фактичного набору: '+result.get('provider','NASA POWER'))
    summary_metrics(result['data'])
    quality_note('weather')
    with st.expander('Повнота щоденних даних фактичного джерела'):
        st.dataframe(pd.DataFrame([{'Показник':k, 'Повнота':f'{v}%'} for k,v in dataset_completeness(result['data']).items()]),hide_index=True,use_container_width=True)
    chart_weather(result['data'],dark)
    with st.expander('Щоденні дані'):
        st.dataframe(result['data'],hide_index=True,use_container_width=True)
    st.download_button('Завантажити дані CSV',result['data'].rename(columns=lambda name:translate(name,st.session_state.get('tt_lang','en'))).to_csv(index=False).encode('utf-8-sig'),
                       file_name=f'TerraTwin_NASA_{year}.csv',mime='text/csv')
    with st.expander('Прямий запит до використаного джерела'):
        st.code(result['url'],language=None)
        st.link_button('Відкрити оригінальні дані',result['url'])
    if choice=='Активна точка':
        st.button('Відкрити науковий аналог',
                  on_click=go_to,args=('Науковий аналог',))


def render_charts(sites,evidence,dark):
    section('05 / VISUAL INSIGHTS','Графіки й дослідження',
            'Дані активної точки та порівняння підтверджених геологічних ознак.')
    show_active_point(compact=True)
    point=ensure_location(st.session_state)
    year_options=[2025,2024,2023,2022,2021]
    if 'tt_chart_year' not in st.session_state:
        st.session_state['tt_chart_year']=int(st.session_state.get('tt_pick_year',2025))
    year=st.selectbox(ui_text('Climate year', 'Рік кліматичних даних'),year_options,key='tt_chart_year')
    current=weather_result_for_current(year)
    request=st.session_state.pop('tt_chart_requested',None)
    if current is None and request==dataset_key(point['lat'],point['lon'],year):
        try:
            with st.spinner(ui_text('Loading climate charts for your selected point…', 'Завантажуємо кліматичні графіки для вибраної точки…')):
                current=get_weather(point['lat'],point['lon'],year,set_as_active=True)
        except NASADataError as exc:
            st.warning(ui_text('Climate services are currently unavailable for this location. ', 'Кліматичні сервіси наразі недоступні для цієї точки. ')+translate(str(exc),st.session_state.get('tt_lang','en')))
    st.caption(f"📍 {localized_point()} · {point['lat']:.4f}°, {point['lon']:.4f}°")
    if current:
        st.subheader(f"📍 Кліматичні графіки вибраної точки · {current['year']}")
        st.caption(ui_text('Source: ', 'Джерело: ')+current.get('provider','NASA POWER'))
        summary_metrics(current['data'])
        chart_weather(current['data'],dark)
        st.divider()
    else:
        st.info('Для вибраної точки ще немає кліматичних графіків. Отримайте її дані NASA POWER.')
        if st.button(ui_text('Load climate charts for this location', 'Завантажити кліматичні графіки для цієї точки'),type='primary'):
            try:
                with st.spinner(ui_text('Loading climate data for your selected point…', 'Завантажуємо кліматичні дані для вибраної точки…')):
                    get_weather(point['lat'],point['lon'],year,set_as_active=True)
                st.rerun()
            except NASADataError as exc:
                st.warning(str(exc))
    target=st.session_state.get('tt_last_target','mare_crisium')
    weights=saved_weights(target)
    if not sum(weights.values()):
        st.warning('У геологічному рейтингу всі ваги дорівнюють нулю.')
        return
    ranking=rank_analogs(sites,evidence,target,weights)
    st.subheader('Геологічні аналоги · '+SCIENCE_TARGETS[target]['name'])
    c1,c2=st.columns(2)
    with c1:
        st.plotly_chart(ranking_chart(ranking,dark=dark,lang=st.session_state.get('tt_lang','en')),use_container_width=True)
    with c2:
        st.plotly_chart(evidence_heatmap(sites,evidence,weights,dark=dark,lang=st.session_state.get('tt_lang','en')),use_container_width=True)
    st.caption('Довільну вибрану точку не включено до геологічного рейтингу без джерел про породи.')
    st.download_button('Завантажити рейтинг (CSV)',
                       ranking_csv(ranking,SCIENCE_TARGETS[target]['name'],weights),
                       file_name='TerraTwin_geology.csv',mime='text/csv')




def render_base(sites,dark):
    section('03 / BASE MISSION LAB','Підготовка до космічної бази',
            'Оціни можливості земної території як полігону для випробувань перед конкретною місячною чи марсіанською місією.')
    show_active_point()
    quality_note('planet')
    st.info('Ми оцінюємо **корисність земної ділянки для підготовки випробувань**, а не можливість побудувати базу на Землі чи Марсі. Пороги й ваги є авторськими та не затверджені NASA.')
    lcol,rcol=st.columns([1.05,1],gap='large')
    with lcol:
        st.subheader('1. Обери планетарну ціль')
        target_id=st.selectbox('Район дослідження',list(BASE_TARGETS),
                               format_func=lambda k:BASE_TARGETS[k]['name'],key='tt_base_target')
        target=BASE_TARGETS[target_id]
        st.caption(target['status'])
        st.write(target['context'])
        st.link_button('Джерело про цей район',target['source'])
    with rcol:
        st.subheader('2. Досліджувана точка Землі')
        point=ensure_location(st.session_state)
        st.write('**'+localized_point()+'**')
        a,b=st.columns(2)
        localized_metric(a,'Широта',f"{point['lat']:.4f}°")
        localized_metric(b,'Довгота',f"{point['lon']:.4f}°")
        st.button('📍 Обрати іншу точку',use_container_width=True,
                  on_click=go_to,args=('Моя точка',))
        year=st.selectbox('Рік земних даних NASA POWER',[2025,2024,2023,2022,2021],key='tt_base_year')
    st.divider()
    st.subheader('3. Критерії аналізу')
    st.caption('Наукові дані позначені джерелами; оцінки умов для технічних випробувань обчислюються за поясненими правилами.')
    criteria_cols=st.columns(3)
    names=list(BASE_CRITERIA)
    for i,key in enumerate(names):
        with criteria_cols[i%3]:
            with st.container(border=True):
                st.markdown('**'+BASE_CRITERIA[key][0]+'**')
                st.caption(BASE_CRITERIA[key][1])
                st.caption(f"Важливість у сценарії: {target['weights'][key]} зі 100")
    with st.expander('Налаштувати важливість критеріїв (необов’язково)'):
        customized=st.toggle('Власні ваги',key='tt_base_custom')
        if customized:
            st.caption('Числа від 0 до 5 — від не враховувати до найважливішого. Шкала нормалізується автоматично.')
            custom_weights={}
            sliders=st.columns(3)
            for i,key in enumerate(names):
                with sliders[i%3]:
                    custom_weights[key]=st.slider(BASE_CRITERIA[key][0],0,5,
                                value=max(1,round(target['weights'][key]/5)),
                                key=f'tt_base_w_{target_id}_{key}')
            if not sum(custom_weights.values()):
                st.warning('Для оцінки потрібна хоча б одна ознака з вагою більше 0.')
            weights=custom_weights
        else:
            weights=target['weights']
    st.divider()
    st.subheader('4. Оцінка ділянки')
    point=ensure_location(st.session_state)
    key=dataset_key(point['lat'],point['lon'],year)
    if st.button('🛰️ Отримати дані та виконати аналіз',type='primary',use_container_width=True):
        daily=None; terrain=None; errors=[]; weather_provider=None; soil_daily=None
        try:
            with st.spinner('Завантажуємо NASA POWER…'):
                result=get_weather(point['lat'],point['lon'],year,set_as_active=True)
                daily=result['data']
                weather_provider=result['provider']
        except NASADataError as exc:
            errors.append('Кліматичні сервіси: '+str(exc))
        try:
            with st.spinner('Отримуємо приблизні температури ґрунту з Open-Meteo ERA5…'):
                soil_daily,soil_url=load_archive(point['lat'],point['lon'],year)
        except ArchiveError:
            # Soil temperature is optional. A weaker air-freezing proxy can be used.
            soil_daily=None
        try:
            with st.spinner('Перевіряємо рельєф Copernicus DEM…'):
                terrain=load_elevation(point['lat'],point['lon'])
        except TerrainError as exc:
            errors.append('Copernicus DEM: '+str(exc))
        geo=None
        try:
            with st.spinner('Перевіряємо геологічну карту Macrostrat…'):
                geo=load_geology(point['lat'],point['lon'])
        except GeologyError as exc:
            errors.append('Macrostrat: '+str(exc))
        site=nearby_site(point['lat'],point['lon'],sites,radius_km=8)
        st.session_state['tt_point_sources']={
             'key':(round(point['lat'],4),round(point['lon'],4)),
             'terrain':terrain,'geology':geo,'errors':{},'retrieved':[],
        }
        st.session_state['tt_base_data']={
             'key':key,'site_id':None if site is None else site['id'],
             'terrain':terrain,'geology':geo,'errors':errors,
             'soil_daily':soil_daily,'weather_provider':weather_provider,
        }
    record=st.session_state.get('tt_base_data',{})
    if record.get('key') != key:
        st.info('Обери планетарну ціль і натисни «Отримати дані та виконати аналіз». Дані з’являться нижче.')
        return
    if record.get('errors'):
        st.info('Не всі зовнішні джерела відповіли. Показуємо підтверджені наявні дані; резервні GIS-карти можна підключити нижче.')
        with st.expander('Деталі технічних запитів',expanded=False):
            for err in record['errors']:
                st.caption(err)
    daily=st.session_state.get('tt_weather_cache',{}).get(key,{}).get('data')
    nsidc_upload_panel(point)
    glim_upload_panel(point)
    ground_ice=imported_ground_ice(point['lat'],point['lon'])
    glim=imported_glim(point['lat'],point['lon'])
    weather_result=st.session_state.get('tt_weather_cache',{}).get(key,{})
    weather_source=weather_result.get('url') or NASA_DOCS
    observations=derive_observations(daily,record.get('terrain'),record.get('site_id'),
                                     geology=record.get('geology'),ground_ice=ground_ice,glim=glim,
                                     allow_proxies=True,soil_daily=record.get('soil_daily'),
                                     weather_source=weather_source)
    if not sum(weights.values()):
        st.warning('Усі ваги дорівнюють нулю. Увімкни хоча б один критерій.')
        return
    report=assess_base(observations,target_id,weights)
    a,b,c=st.columns([1,1,1])
    if report['score'] is not None:
        localized_metric(a,'Попередній індекс випробувань',f"{report['score']} / 100")
        st.progress(report['score']/100)
    else:
        localized_metric(a,'Індекс випробувань','Замало даних')
    localized_metric(b,'Охоплення оцінкою',f"{report['coverage']}%")
    if daily is not None:
        completeness=dataset_completeness(daily)
        rain_pct=completeness.get(LABELS['PRECTOTCORR'], 0)
        st.caption(f'Повнота річних даних NASA POWER (опади): {rain_pct}%. '
                   'Неповний рік не можна інтерпретувати як достовірну річну суму.')
    localized_metric(c,'Оцінено критеріїв',f"{sum(r['score'] is not None for r in report['criteria'])} / {len(report['criteria'])}")
    st.caption(f"Без додаткових наближених критеріїв: {report['mapped_or_modeled_count']}/6 · "
               f"Наближені критерії: {report['estimated_count']}/6. "
               '6/6 оцінено НЕ означає 6/6 підтверджених порід і льоду.')
    if record.get('weather_provider'):
        st.caption('Кліматичне джерело: '+record['weather_provider']+'.')
    verdict=classify_base(report['score'],report['coverage'],report['criteria'],lang=st.session_state.get('tt_lang','en'))
    st.subheader('Підсумок: наскільки хороший цей земний аналог?')
    st.markdown('### '+verdict['title'])
    if verdict['category']=='insufficient':
        st.warning(verdict['description'])
    elif verdict['category']=='preliminary':
        st.info(verdict['description'])
    elif verdict['category'] in ('poor','limited'):
        st.warning(verdict['description'])
    else:
        st.success(verdict['description'])
    if verdict.get('low_confidence'):
        st.info('Попередня оцінка за балами: '+str(report['score'])+'/100 · '+
                {'poor':'не рекомендується','limited':'низька придатність',
                 'conditional':'умовно підходить','good':'добрий аналог',
                 'strong':'дуже перспективний'}.get(verdict.get('potential_band'),'недостатньо даних')+
                '. **Остаточна рекомендація обмежена**: породи або ґрунтовий лід оцінено за непрямими ознаками.')
    if verdict['critical_missing']:
        st.caption('Важливо: бракує ключових даних — '+', '.join(BASE_CRITERIA[k][0] for k in verdict['critical_missing'])+'.')
    st.caption('Авторські межі оцінки: 0–39 · не рекомендується; 40–59 · низька придатність; '
               '60–74 · умовна; 75–89 · добра; 90–100 · дуже перспективна. '
               'Позитивна оцінка можлива лише за достатньої повноти доказів, включно з геологією та льодом.')
    st.caption('Число не є відсотком подібності до планети. 100% охоплення оцінкою — не 100% достовірність. Для кожного рядка перевіряйте спосіб отримання та джерело.')
    if report['coverage'] < 80:
        st.warning('Частина важливих критеріїв невідома. Особливо обережно трактуй оцінку геології, льоду та ресурси.')
    st.subheader('Що саме відомо про місцевість')
    with st.expander('Перевірка наукової достовірності кожної ознаки',expanded=False):
        evidence_status_panel(observations)
    if daily is not None:
        quality_note('weather')
    if record.get('terrain'):
        quality_note('terrain')
    if observations['metrics']:
        cols=st.columns(3)
        for i,(name,value) in enumerate(observations['metrics'].items()):
            with cols[i%3]:
                st.metric(name,f'{value}')
    else:
        st.info('Зовнішні сервіси не повернули вимірювань. Доступні тільки описи підтверджених аналогів.')
    rows=[]
    for row in report['criteria']:
        rows.append({'Критерій':row['criterion'],
                    'Оцінка':f"{row['score']}/100" if row['score'] is not None else 'Немає даних',
                    'Вага':row['weight'],
                    'Докази / обмеження':row['note'],
                    'Тип джерела':row.get('evidence_type','Not verified'),
                    'Надійність':('Наближено (низька)' if 'Estimated ' in row.get('evidence_type','') else ('Дані/картографічна модель' if row['score'] is not None else 'Невідомо')),
                    'Посилання':row['source'] or '—'})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    if report['estimated_count']:
        st.warning('Позначені як Estimated значення є авторськими приблизними індексами з температури, опадів та/або рельєфу. '
                   'Вони не підтверджують наявність водяного льоду чи конкретний тип порід. '
                   'Для практичних експедицій потрібні лабораторні та польові дослідження.')
    st.subheader('Геологічна карта за координатами')
    geology_block(record.get('geology'))
    geology_materials_panel(record.get('geology'))
    st.caption('Знайдена літологія — додаткова підтверджена інформація. Вона не створює автоматично числову відповідність реголіту іншої планети.')
    render_planetary_sources(target_id)
    st.subheader('Поради дослідницького агента')
    if report['coverage'] < 60:
        st.warning('Наразі неможливо зробити обґрунтований комплексний висновок: джерел недостатньо.')
    else:
        st.write('**Можливе застосування:** наземні випробування пересування роботів, вимірювальних приладів, живлення та термостійкості — лише за тими характеристиками, для яких є дані.')
    if any(r['score'] is None for r in report['criteria']):
        language = st.session_state.get('tt_lang', 'en')
        unknown=', '.join(translate(r['criterion'], language).lower() for r in report['criteria'] if r['score'] is None)
        st.write('**Що треба дослідити додатково:** '+unknown+'.')
    st.write('**Обмеження:** земна атмосфера, сила тяжіння та радіація відрізняються від планетарних умов. '
             'Наявність земного льоду не доводить існування доступного льоду в заданих координатах Місяця або Марса.')
    with st.expander('Наукові джерела кожної ознаки'):
        for row in report['criteria']:
            st.markdown('**'+row['criterion']+'**')
            st.write(row['note'])
            if row['source']:
                st.link_button('Відкрити джерело · '+row['criterion'],row['source'])
        st.link_button('Наукове підґрунтя планетарної цілі',target['source'])
        st.link_button('Контекст пошуку льоду',target['water_source'])
    export={'project':'TerraTwin','version':BUILD,'mode':'Підготовка бази',
            'terrestrial_location':point,'year':year,'planetary_target':target['name'],
            'evaluation':'Earth field-test screening, not planetary physical similarity',
            'score':report['score'],'coverage':report['coverage'],
            'interpretation':verdict,
            'criteria':report['criteria'],'observed_earth':report['metrics'],
            'geology_map':record.get('geology'),
            'glim_map_interpretation':glim,'ground_ice_interpretation':ground_ice,
            'evidence_types':observations['evidence_types'],
            'estimated_count':report['estimated_count'],
            'climate_provider':record.get('weather_provider'),
            'scientific_data_sources':[BY_ID[k] for k in PLANET_SOURCES.get(target_id, ())],
            'earth_source_catalog':[BY_ID[k] for k in ('power','copernicus','macrostrat','soilgrids','worldcover','permafrost','emit')]}
    st.download_button('⬇ Експортувати науковий профіль JSON',
                       json.dumps(export,ensure_ascii=False,indent=2).encode('utf-8'),
                       file_name='TerraTwin_mission_profile.json',mime='application/json')


def on_navigation_change():
    """Radio callback runs before the next rerender (never set its own key)."""
    select_navigation(st.session_state, st.session_state.get('tt_navigation_control'))


def on_theme_change():
    """Do not allow localization rerenders to overwrite the user theme."""
    select_theme(st.session_state, st.session_state.get(THEME_WIDGET_KEY))


sites=load_sites()
evidence=load_evidence_db()
ensure_location(st.session_state)
ensure_preferences(st.session_state)
# Synchronize programmatic navigation BEFORE the radio widget is created.
sync_navigation_before_widget(st.session_state)
sync_theme_before_widget(st.session_state)
dark=st.session_state['tt_theme']=='dark'
lang=st.session_state['tt_lang']

# The stylesheet is always derived from the CANONICAL theme, never from a
# transient language-dependent widget label or a radio's formatted text.
st.markdown(f'<style>{theme_css("dark" if dark else "light")}</style>',unsafe_allow_html=True)
st.markdown(brand(),unsafe_allow_html=True)
st.markdown(hero(lang),unsafe_allow_html=True)
nav,theme,language=st.columns([4.2,1.05,1.05])
with nav:
    # Use native Streamlit here rather than the localization wrapper. The label
    # is identity-stable; user-visible option names are translated separately.
    _st.radio('Navigation',PAGE_IDS,index=PAGE_IDS.index(st.session_state['tt_page']),
              format_func=lambda p:translate(p,_st.session_state.get('tt_lang','en')),
              horizontal=True,key='tt_navigation_control',
              on_change=on_navigation_change,label_visibility='collapsed')
with theme:
    _st.radio('Appearance',THEME_IDS,index=THEME_IDS.index(st.session_state['tt_theme']),
              format_func=lambda mode:theme_name(mode,_st.session_state.get('tt_lang','en')),
              horizontal=True,key=THEME_WIDGET_KEY,
              on_change=on_theme_change,label_visibility='collapsed')
with language:
    _st.radio('Language',['en','uk'],
              format_func=lambda value:'English' if value=='en' else 'Українська',
              horizontal=True,key='tt_lang',label_visibility='collapsed')

if lang=='en':
    st.caption('TerraTwin · Research Data Hub · Independent educational project — not affiliated with NASA')
    with _st.expander('🧭 How to use TerraTwin · Quick start',expanded=False):
        _st.markdown('**1. Choose a location.** Click the map, enter coordinates, or select a documented Earth site.  '
                     '**2. Explore data.** Open NASA data for climate charts, or Data sources for terrain, geology and archives.  '
                     '**3. Evaluate an analog.** Use Scientific analog or Mission testing; both share your selected point.  '
                     '**4. Check evidence.** Read the source and confidence next to each result, then export a report.')
        _st.caption('Scores from 0 to 100 are project-defined Earth testing indicators, not measured percentages of Moon/Mars similarity. Approximate results are identified as estimates.')
else:
    st.caption('TerraTwin · Наукові дані · Незалежний освітній проєкт — не пов’язаний з NASA')
    with _st.expander('🧭 Як користуватися TerraTwin · Швидкий початок',expanded=False):
        _st.markdown('**1. Обери місце.** Натисни на карту, введи координати або вибери досліджену територію.  '
                     '**2. Переглянь дані.** У розділі «Дані NASA» відкрий кліматичні графіки; у «Джерелах та даних» — рельєф, геологію та архіви.  '
                     '**3. Оціни аналог.** Розділи «Науковий аналог» і «Підготовка бази» використовують ту саму точку.  '
                     '**4. Перевір докази.** Прочитай джерело й надійність результатів, після чого експортуй звіт.')
        _st.caption('Оцінки від 0 до 100 — авторські індикатори для земних випробувань, а не відсотки фізичної схожості з Місяцем чи Марсом. Приблизні результати позначено окремо.')
page=st.session_state['tt_page']
if page=='Моя точка':
    render_pick(sites,dark)
elif page=='Карта аналогів':
    render_atlas(sites,dark)
elif page=='Науковий аналог':
    render_compare(sites,evidence,dark)
elif page=='Підготовка бази':
    render_base(sites,dark)
elif page=='Дані NASA':
    render_nasa(sites,dark)
elif page=='Графіки':
    render_charts(sites,evidence,dark)
else:
    render_sources(sites)
st.caption(('TerraTwin · NASA POWER / PDS · Copernicus · Macrostrat · ESA · ISRIC · NSIDC · Independent project © 2026' if lang=='en' else 'TerraTwin · NASA POWER / PDS · Copernicus · Macrostrat · ESA · ISRIC · NSIDC · Незалежний проєкт © 2026'))
