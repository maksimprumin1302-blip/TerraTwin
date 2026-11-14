# TerraTwin v2.1.11 — Complete English / Ukrainian UI

## AI Usage Disclosure / Розкриття використання ШІ

**English:** Parts of TerraTwin's Python code, debugging, English/Ukrainian interface text, documentation and presentation design were developed with assistance from **OpenAI ChatGPT**. AI-assisted presentation visuals are visibly labeled. Scientific data from NASA, Copernicus and other cited providers are **not** AI-generated measurements; site descriptions, feature annotations and source catalogs were curated with AI assistance. TerraTwin's 0–100 scores are project-defined calculations, not validated planetary similarity measurements. See [AI_USAGE.md](AI_USAGE.md) and [ai_provenance.json](ai_provenance.json) for a detailed disclosure and machine-readable metadata.

**Українською:** Під час розробки частини Python-коду, налагодження, перекладів, документації та презентацій використовувався **OpenAI ChatGPT**. Ілюстрації з допомогою ШІ позначено на слайдах. Наукові дані NASA та інших джерел **не є згенерованими ШІ вимірюваннями**. Описові довідники й пояснення частково підготовлені з допомогою ШІ, а бали придатності є авторськими розрахунковими показниками. Детальніше: [AI_USAGE.md](AI_USAGE.md).

---


This build improves the English translation throughout TerraTwin, including Mission testing limitations, source explanations, climate and geological tables, and chart controls. **English is the default language.** Switch to Українська at the top of the app at any time. Navigation, location and Dark/Light theme continue to use stable internal IDs. The cosmic Research Data Hub visual design and built-in Quick Start are preserved.

**Setup:** Unzip into a new, empty directory (do not overwrite an older TerraTwin folder), run `START_TERRATWIN.bat`, and visit `http://localhost:8546` if the browser does not open automatically. Live API responses depend on internet access and external service coverage; no local full-browser validation is claimed.

# TerraTwin — Earth Analog Explorer

**Independent educational research project. Not affiliated with NASA.**

## Quick start (Windows)

1. Install **Python 3.11 or newer** if it is not already installed.
2. Unzip the archive into a new folder.
3. Double-click **START_TERRATWIN.bat**. The launcher creates a local Python environment and downloads missing packages when needed.
4. TerraTwin opens automatically in your browser. If it does not, visit **http://localhost:8546**.

No separate Streamlit installation is required. Internet connectivity is needed to set up the application and to obtain live scientific data. If setup fails, check disk space, Python installation and connectivity.

## Using TerraTwin

The initial language is **English**. At the top of the page you can choose **English / Українська** and the **Dark / Light** theme. Switching language should preserve the currently selected theme, page and Earth location.

- **My location** — choose a spot on the map, enter coordinates or use one of the documented sites. Where available, TerraTwin adds an approximate area and country name.
- **NASA data / Charts** — load satellite/model climate time series; charts follow the active point. NASA POWER is the primary provider with Open-Meteo as fallback.
- **Scientific analog** — compare documented geological evidence for terrestrial analog sites with a Moon/Mars research target.
- **Mission testing** — evaluate terrestrial field-testing usefulness with six scored criteria, evidence completeness and qualifications.
- **Data sources** — inspect providers, limitations and science source links. NASA Earthdata and Copernicus satellite searches show **catalog metadata**, not directly sampled pixels.

The built-in **How to use TerraTwin · Quick start** guide remains accessible at the top of the application.

**Scientific limitations.** Scores 0–100 are project-defined indicators of suitability for Earth testing; they are not precise Moon/Mars similarity percentages, and do not certify landing safety. Estimates are identified separately from mapped/observed data. Some datasets may be unavailable for a location or when their services are offline. TerraTwin does not manufacture observations to fill missing coverage.

**Data privacy.** Selecting a custom location may send coordinates to OpenStreetMap Nominatim for approximate place names and to requested data services. Do not submit sensitive locations if you do not want to share their coordinates with these external services.

---

# TerraTwin — Українська інструкція

**Незалежний освітній науковий проєкт, не пов’язаний із NASA.**

## Як запустити на Windows

1. Установіть **Python 3.11 або новішу версію**, якщо його ще немає.
2. Розпакуйте ZIP у нову папку.
3. Запустіть **START_TERRATWIN.bat**. Скрипт сам створить середовище Python та встановить потрібні бібліотеки за наявності інтернету.
4. Сайт відкриється в браузері. Якщо ні, перейдіть на **http://localhost:8546**.

Початкова мова — **англійська**. Угорі можна перемикатися між українською та англійською, а також між темною та світлою темами. Налаштування теми, розділ і вибрана точка зберігаються під час перемикання мови.

- **Моя точка** — виберіть місце на карті, введіть координати або скористайтеся прикладом. Для довільної точки може з'явитися приблизна назва місцевості.
- **Дані NASA / Графіки** — отримайте кліматичні показники та графіки саме для активної точки.
- **Науковий аналог** — порівняйте задокументовані геологічні ознаки.
- **Підготовка бази** — перегляньте оцінку придатності для земних випробувань за шістьма критеріями.
- **Джерела та дані** — перегляньте походження значень, наукові посилання та обмеження.

На головній сторінці залишено вбудовану інструкцію **«Як користуватися TerraTwin · Швидкий початок»**.

**Обмеження.** Оцінка 0–100 — авторський індекс для наземних досліджень, не точний відсоток подібності до Місяця чи Марса. Модельні значення позначаються як приблизні. Деякі показники можуть бути відсутні, якщо немає наукового покриття або зовнішній сервіс недоступний. Власні координати можуть надсилатися зовнішнім картографічним і науковим сервісам.


### Navigation stability fix (v2.1.7)

Fixed a crash when the navigation radio supplied an old English/translated label instead of the internal page ID. Unknown navigation values no longer cause a ValueError: the current page is retained. The active language, theme and chosen Earth location are preserved.

To install, extract this ZIP into **a new empty folder** and run `START_TERRATWIN.bat`. Do not mix files from different versions.

### v2.1.8: Navigation repair
Navigation state is now updated before the Streamlit navigation radio is instantiated. Unzip in a **new directory**, not over an old TerraTwin installation.
