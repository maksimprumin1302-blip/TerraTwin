# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Verifiable research catalogue: data access isn't equivalent to point-level availability.

Each source explicitly states whether TerraTwin can request numeric values directly,
only display a visual layer, or must defer a source raster/GIS workflow.
"""

SOURCES = [
    {
        'id':'nasa_cmr', 'topic':'Супутникові знімки', 'world':'Земля',
        'name':'NASA Earthdata CMR Search API', 'provider':'NASA Earthdata',
        'mode':'Автоматичний пошук метаданих', 'url':'https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html',
        'what':'Пошук відкритих колекцій NASA за координатами. TerraTwin показує назви й посилання на набори.',
        'limits':'Лише метадані, не значення пікселів. Доступ до окремих файлів може вимагати NASA Earthdata Login.',
    },
    {
        'id':'copernicus_stac', 'topic':'Супутникові знімки', 'world':'Земля',
        'name':'Copernicus Data Space STAC Sentinel-2 L2A', 'provider':'ESA / Copernicus',
        'mode':'Автоматичний пошук метаданих', 'url':'https://documentation.dataspace.copernicus.eu/APIs/STAC.html',
        'what':'Пошук знімків Sentinel-2 L2A для координат і року; дата та хмарність з метаданих.',
        'limits':'Наявний знімок не доводить склад порід чи наявність льоду, і не включений автоматично до індексу.',
    },
    {
        'id':'jaxa_gsmap', 'topic':'Клімат / освітлення', 'world':'Земля',
        'name':'JAXA GSMaP Global Satellite Mapping of Precipitation', 'provider':'JAXA',
        'mode':'Науковий архів (не інтегровано в розрахунки)', 'url':'https://sharaku.eorc.jaxa.jp/GSMaP/',
        'what':'Глобальні супутникові оцінки опадів; перспективне джерело перехресної перевірки.',
        'limits':'Точкове автоматичне вибирання пікселів GSMaP в поточній версії ще не реалізоване.',
    },
    {
        'id':'era5_archive','topic':'Клімат / освітлення','world':'Земля',
        'name':'Open-Meteo Historical ERA5 / ERA5-Land Reanalysis', 'provider':'Open-Meteo / ECMWF',
        'mode':'Автоматичний резерв (модельні дані)', 'url':'https://open-meteo.com/en/docs/historical-weather-api',
        'what':'Модельні температури повітря та ґрунту, опади, сонячна радіація і вітер за повний рік.',
        'limits':'Це реаналіз, а НЕ локальні сенсори або підтверджений ґрунтовий лід чи мінералогія. Для критеріїв льоду та матеріалів використовуються тільки позначені низькодостовірні проксі.',
    },
    {
        'id': 'power', 'topic': 'Клімат / освітлення', 'world': 'Земля',
        'name': 'NASA POWER Daily API', 'provider': 'NASA',
        'mode': 'Автоматично', 'url': 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/',
        'what': 'T2M, T2M_MIN, T2M_MAX, PRECTOTCORR, WS10M, ALLSKY_SFC_SW_DWN; щоденні модельні/супутникові дані за координатами.',
        'limits': 'Сіткові продукти; не датчик на вибраній точці й не температура інших планет.',
    },
    {
        'id': 'copernicus', 'topic': 'Висота / рельєф', 'world': 'Земля',
        'name': 'Copernicus DEM GLO-90 / Open-Meteo Elevation', 'provider': 'Copernicus / Open-Meteo',
        'mode': 'Автоматично', 'url': 'https://open-meteo.com/en/docs/elevation-api',
        'what': 'Висоти дев’яти точок і груба похідна оцінка ухилу/перепаду.',
        'limits': 'Похідний ухил із 9 вимірювань ~300 м; недостатньо для вибору безпечного посадкового майданчика.',
    },
    {
        'id': 'macrostrat', 'topic': 'Геологія / породи', 'world': 'Земля',
        'name': 'Macrostrat Geological Map API v2', 'provider': 'Macrostrat',
        'mode': 'Автоматично (за наявності покриття)', 'url': 'https://macrostrat.org/api/v2/geologic_units/map',
        'what': 'Картографічні геологічні одиниці, літологія, геологічний вік, опис, карта-першоджерело.',
        'limits': 'Це узагальнені полігони карт; не лабораторний аналіз мінералів чи ґрунту саме в точці.',
    },
    {
        'id': 'glim', 'topic': 'Геологія / породи', 'world': 'Земля',
        'name': 'GLiM Global Lithological Map (2012)', 'provider': 'Hartmann & Moosdorf / GFZ / AWI',
        'mode': 'GIS / імпорт GeoJSON', 'url': 'https://doi.org/10.1029/2012GC004370',
        'what': 'Регіональні карти типів поверхневих порід, 16 класів літології, глобальне картографічне покриття.',
        'limits': 'Потрібно завантажити фрагмент GIS-карти та перевірити код класу; це не лабораторний аналіз у точці.',
    },
    {
        'id': 'esa_permafrost', 'topic': 'Вода / лід', 'world': 'Земля',
        'name': 'ESA CCI Permafrost v5', 'provider': 'ESA Climate Change Initiative',
        'mode': 'GIS / архів растрових даних', 'url': 'https://climate.esa.int/en/projects/permafrost/data/',
        'what': 'Модельна частка територій із мерзлотою та температури ґрунту у Північній півкулі, ~1 км.',
        'limits': 'Поширення мерзлоти — не вимірювання ґрунтового льоду; растрові файли не зчитуються автоматично в цьому застосунку.',
    },
    {
        'id': 'worldcover', 'topic': 'Покрив поверхні', 'world': 'Земля',
        'name': 'ESA WorldCover 2021 v200 (10 m)', 'provider': 'ESA / Terrascope',
        'mode': 'Картографічний шар (без числової оцінки)', 'url': 'https://esa-worldcover.org/en/data-access',
        'what': 'Класи земного покриву за Sentinel-1/2 у картографічному шарі.',
        'limits': 'WMS надає стилізовані RGB-пікселі, не класи, придатні для кількісного аналізу.',
    },
    {
        'id': 'soilgrids', 'topic': 'Властивості ґрунтів', 'world': 'Земля',
        'name': 'ISRIC SoilGrids 250 m', 'provider': 'ISRIC',
        'mode': 'Набір для GIS; REST призупинений', 'url': 'https://docs.isric.org/globaldata/soilgrids/index.html',
        'what': 'Частка піску/глини/мулу, щільність, pH та інші змодельовані характеристики ґрунту.',
        'limits': 'Потрібен WCS/WebDAV або GIS. REST API офіційно повідомляє про призупинення; немає автоматичних чисел.',
    },
    {
        'id': 'permafrost', 'topic': 'Вода / лід', 'world': 'Земля',
        'name': 'Circum-Arctic permafrost and ground ice, v2', 'provider': 'NASA NSIDC',
        'mode': 'GIS / імпорт GeoJSON', 'url': 'https://nsidc.org/data/ggd318/versions/2',
        'what': 'Поширення багаторічної мерзлоти та відносна кількість підземного льоду в Арктиці.',
        'limits': 'GGD318 v2 — історична регіональна карта масштабом близько 1:10 млн. Потрібен імпорт GIS і перевірка полігона; класи не є точковим вимірюванням.',
    },
    {
        'id': 'emit', 'topic': 'Мінерали / спектри', 'world': 'Земля',
        'name': 'NASA EMIT', 'provider': 'NASA/JPL',
        'mode': 'Спектральні файли, часткове покриття', 'url': 'https://earth.jpl.nasa.gov/emit/data/data-portal/coverage-and-forecasts/',
        'what': 'Спектральні вимірювання у вибраних аридних зонах Землі, мінералогічні ознаки.',
        'limits': 'Не глобальне точкове API; потрібне визначення покриття, завантаження файлу та спектральний аналіз.',
    },
    {
        'id': 'lola', 'topic': 'Висота / рельєф', 'world': 'Місяць',
        'name': 'LRO LOLA DEM', 'provider': 'NASA / PDS',
        'mode': 'Планетарні DEM-файли', 'url': 'https://imbrium.mit.edu/',
        'what': 'Рельєф Місяця, включно з новими детальними DEM південного полюса.',
        'limits': 'Файли потребують перетворення координат та обробки растрів; значення не завантажуються кнопкою для Землі.',
    },
    {
        'id': 'diviner', 'topic': 'Температура', 'world': 'Місяць',
        'name': 'LRO Diviner thermal products', 'provider': 'NASA / PDS / UCLA',
        'mode': 'Планетарні карти / архів', 'url': 'https://pds-geosciences.wustl.edu/missions/lro/diviner.htm',
        'what': 'Дані теплового випромінювання та температур місячної поверхні.',
        'limits': 'Температура поверхні та її часове усереднення не тотожні земній T2M.',
    },
    {
        'id': 'illumination', 'topic': 'Сонячне освітлення', 'world': 'Місяць',
        'name': 'Lunar Polar Illumination (PGDA)', 'provider': 'NASA / GSFC',
        'mode': 'Планетарні карти / архів', 'url': 'https://pgda.gsfc.nasa.gov/products/69',
        'what': 'Моделі освітлення місячних полярних регіонів.',
        'limits': 'Потрібні дані для конкретного району та часовий інтервал; не тотожні земному сонячному потоку.',
    },
    {
        'id': 'mola', 'topic': 'Висота / рельєф', 'world': 'Марс',
        'name': 'Mars Global Surveyor MOLA', 'provider': 'NASA / PDS',
        'mode': 'Планетарні DEM-файли', 'url': 'https://pds-geosciences.wustl.edu/missions/mgs/mola.html',
        'what': 'Глобальна висота та рельєф Марса (MEGDR).',
        'limits': 'Потрібне завантаження та коректна марсіанська система координат.',
    },
    {
        'id': 'swim', 'topic': 'Вода / лід', 'world': 'Марс',
        'name': 'SWIM — Subsurface Water Ice Mapping', 'provider': 'PSI / NASA',
        'mode': 'Геопросторові карти льоду', 'url': 'https://swim.psi.edu/SWIM4MIMProducts.php',
        'what': 'Кілька непрямих ознак можливого підповерхневого льоду; GeoTIFF продукти.',
        'limits': 'Це об’єднана оцінка узгодженості ознак, а не вимірювання доступних запасів льоду.',
    },
    {
        'id': 'crism', 'topic': 'Мінерали / спектри', 'world': 'Марс',
        'name': 'MRO CRISM', 'provider': 'NASA / PDS',
        'mode': 'Спектральні архівні файли', 'url': 'https://pds-geosciences.wustl.edu/missions/mro/crism.htm',
        'what': 'Мінералогічні спектральні зображення вибраних територій Марса.',
        'limits': 'Покриття нерівномірне; потрібна обробка спектрів та реєстрація локацій.',
    },
    {
        'id': 'themis', 'topic': 'Температура / поверхня', 'world': 'Марс',
        'name': 'Mars Odyssey THEMIS', 'provider': 'NASA / ASU',
        'mode': 'Теплові карти / архів', 'url': 'https://www.mars.asu.edu/data/',
        'what': 'Інфрачервоні знімки, теплові властивості та поверхневі структури.',
        'limits': 'Час спостереження й фізична величина повинні відповідати цілі дослідження.',
    },
    {
        'id': 'gibs', 'topic': 'Супутникові знімки', 'world': 'Земля',
        'name': 'NASA GIBS', 'provider': 'NASA Earthdata',
        'mode': 'Супутникові картографічні шари', 'url': 'https://nasa-gibs.github.io/gibs-api-docs/access-basics/',
        'what': 'Картографічні зображення Землі через стандарти WMS/WMTS.',
        'limits': 'Візуальні дані — не безпосереднє числове вимірювання стану ґрунту чи порід.',
    },
]

BY_ID = {x['id']: x for x in SOURCES}

# Planetary target specific: a catalogue of documented sources, not invented
# values at exact lat/lon. Numeric planetary rasters still require GIS extraction.
PLANET_SOURCES = {
    'mons_mouton': ('lola', 'diviner', 'illumination'),
    'nobile_rim_2': ('lola', 'diviner', 'illumination'),
    'arcadia': ('mola', 'swim', 'themis', 'crism'),
    'mare_crisium': ('lola', 'diviner'),
    'jezero': ('mola', 'crism', 'themis'),
}
