## AI disclosure update (2026-11-14)

Added bilingual AI-use notice to README, machine-readable metadata for code/data and an AI usage statement in Python modules. Existing scientific data files and computational logic are unchanged.

# TerraTwin v2.1.11 — Complete EN/UA Interface Review (2026-11-14)

- Fixed the full **Limitations** statement in Mission testing: English mode now displays a complete English paragraph, without mixed Ukrainian fragments.
- Audited the seven main pages, data source descriptions, evidence tables, climate summaries, GIS import instructions, ranking labels and warning messages for language consistency.
- Improved localization matching to replace whole terms, avoiding accidental partial words such as `Marsа`.
- Localized numeric metric cards rendered inside Streamlit columns; they previously bypassed the main text localization wrapper.
- Corrected the Scientific analog verdict to use the currently selected language, not the old Ukrainian default.
- Translated remaining labels in the NASA daily-data table and made the CSV data column headers use the selected language.
- Added bilingual NASA Earthdata / Copernicus satellite discovery guidance, notifications and Charts controls.
- Kept English as the default, Ukrainian as an option, the existing Research Data Hub CSS design, help instructions, theme and navigation state logic unchanged.
- Scores and scientific sources have not been altered. Live service availability is never guaranteed by language tests.

## v2.1.10 — Climate Language Fix

- Explicit English/Ukrainian climate-summary labels in NASA data, Charts, My location and Data sources sections.
- Localized unit text (mm, m/s, kWh/m² or мм, м/с, кВт·год/м²), incomplete-year and missing-data statuses.
- English remains the default; theme/navigation and all previous features remain untouched.

TerraTwin v2.1.9 — Theme Stability Fix

The appearance radio now uses a new stable widget key, canonical EN/UA theme labels, and a callback that only updates canonical state. Invalid legacy values are ignored rather than crashing the app. Navigation and language preferences, existing design, and Quick Start are preserved.

## v2.1.7 — Navigation Stability Hotfix
- Normalize English and Ukrainian navigation labels to stable page IDs.
- Avoid application crash if a Streamlit radio contains an unexpected/stale value.
- Keep language, theme, and selected point unchanged.
- Retain Research Data Hub design and quick-start instructions.

# v2.1.5 — Bilingual Maps & Charts (2026-11-14)

- English is the default language; Ukrainian is available via a language selector. Navigation IDs and active analyses persist across language changes.
- Shared location now has user-initiated approximate reverse geocoding (municipality/district/region/country) using OSM Nominatim with global rate limit, local caching, attribution and graceful no-coverage fallback. Coordinates are always displayed.
- Fixed **Open charts for this point**: Charts uses the user-selected coordinate + climate year, automatically retrieving climate data on navigation when absent; also offers a direct load control.
- Included English descriptions of all five curated Earth analogs, bilingual map popups, translated chart labels, scientific source summaries and other interface controls.
- New live, explicitly labeled **metadata-only** lookup of NASA Earthdata CMR collections and Copernicus Sentinel-2 L2A scenes at the active point; matches and metadata never alter field-test scores without numeric evidence extraction.
- JAXA GSMaP added as an external scientific archive, **not** automatically queried for values.
- Scientific catalog increased to 21 documented sources; privacy/data-source limitations documented.
- New Windows port **8545** to avoid conflicts with 8544 previous build.
- 130 unit/regression tests + 15 additional scenarios pass. A live browser integration test is still needed on Windows.

# Smart Estimates (2026-11-14)

- Retains original Research Data Hub design and navigation.
- NASA POWER daily data primary, Open-Meteo historical reanalysis fallback.
- Estimation of dry-surface test conditions from annual precipitation + terrain, NOT geology.
- Estimation of soil-freezing conditions from modeled soil/air temperature, NOT ground ice.
- Spatial rock and ice sources override estimates.
- 6/6 assessed explicitly separated from 6/6 directly known.
- Low-confidence fallbacks never give a definitive positive suitability recommendation.
- No offline fake records, no computed scores from missing climate records.
- New Windows launch port 8544, no pip cache.
- Tests added for partial data, source priority, soil temperatures and confidence.

# v2.1 · Research Data Hub (14.11.2026)

- Новий розділ **«Джерела та дані»** для активної точки.
- Macrostrat API: автоматичне отримання картографічних геологічних одиниць за широтою/довготою, з ID першоджерела і посиланням на точний запит.
- NASA POWER + Copernicus DEM: швидке отримання без зміни координат, спільне з іншими вкладками.
- SoilGrids: необов'язкова спроба REST з явним поясненням паузи в сервісі; WCS/WebDAV у каталозі.
- 15 реальних наукових джерел із NASA, ESA, ISRIC, Macrostrat, NSIDC та інших проєктів: джерела, доступність, обмеження, фільтри.
- Макети карт: вмикаються шари **ESA WorldCover 2021** і **Macrostrat**; основна карта лишається OpenStreetMap без ключів.
- Режим баз: додатковий геологічний результат Macrostrat + окремі планетарні джерела для сценарію.
- Режим науки: довільна активна точка може завантажити геологічну карту, але не отримує недоведеного рейтингу.
- Експорт JSON із результатами, каталогом джерел і описом обмежень; `DATA_SOURCES.csv` у комплекті.
- Оновлений стартовий порт **8521**, щоб не відкривати старий процес на 8520.
- **Не реалізовано в цьому випуску:** автоматична GIS-вибірка з планетарних DEM та SoilGrids WCS/NSIDC, точні оцінки мінерального складу для кожної земної координати.

## Precision Edition
- Same v2.1 visual theme and map layout.
- Added explicit data quality, source scale and completeness explanations.
- Macrostrat response parser tolerates nested and GeoJSON payloads.
- Unknown geology is never treated as absence.
- Added NASA solar-unit awareness and finite-data checks.
- Simplified dependency installation; pip no-cache and no pytest runtime.

## Research Refined (2.1.2)
- Scientific completeness thresholds for full-year climate and solar data.
- Missing monthly precipitation left blank; never represented as complete months.
- Duplicate-date protection for source completeness.
- In-app user journey guide and clear provenance reminders.
- Research Data Hub visual design unchanged.


### v2.1.2 Geological materials and NSIDC GIS
- More informative, source-linked geological materials grade from classifiable Macrostrat mapped lithology (never arbitrary unspecified rock names).
- NSIDC GGD318 geographic coverage status, optional normalized GeoJSON upload, strict polygon matching, unknown/no-polygon distinction.
- Both evidence paths feed the Base Mission Lab with explicit author heuristics only where verified.


## v2.1.3 Evidence & Rating
- Added optional GLiM GIS fallback, provenance/status table, score bands gated by weighted evidence coverage and required materials/ice evidence.
- Redesigned no UI: Research Data Hub theme unchanged.
- Missing external source data are reported honestly; exact errors available in details.
- No automatic ESA permafrost value extraction, no globally guaranteed lithology or ground ice.

## 2.1.8 Navigation State Fix
- Corrected Streamlit widget lifecycle: programmatic navigation no longer writes to a mounted radio widget.
- All page requests use pending canonical state, synchronized before radio creation.
- Invalid navigation values are ignored safely, without application exceptions.
- Regression tests simulate widget mutation restrictions and language switching.
