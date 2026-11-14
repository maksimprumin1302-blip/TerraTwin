# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Stable user preferences independent of Streamlit widget identity.

A Streamlit widget may be reconstructed when a label or formatted options
change. We keep the selected page and theme in canonical, non-widget fields
and update those fields only from deliberate user callbacks.
"""
from __future__ import annotations

# Page IDs are deliberately stable and independent of the display language.
PAGE_IDS = ('Моя точка', 'Карта аналогів', 'Науковий аналог',
            'Підготовка бази', 'Дані NASA', 'Графіки', 'Джерела та дані')
THEME_IDS = ('dark', 'light')
THEME_WIDGET_KEY = 'tt_theme_choice_v2'

# Compatibility with values left by older Streamlit widgets.  A translated
# display string MUST NOT be passed directly to the renderer as a page ID.
_PAGE_LABELS = {
    'My location': PAGE_IDS[0], 'Analog atlas': PAGE_IDS[1],
    'Scientific analog': PAGE_IDS[2], 'Mission testing': PAGE_IDS[3],
    'NASA data': PAGE_IDS[4], 'Charts': PAGE_IDS[5],
    'Data sources': PAGE_IDS[6], 'Джерела й дані': PAGE_IDS[6],
    'Data and scientific sources': PAGE_IDS[6],
}


def canonical_page(value):
    """Return the stable internal page ID, or None for unknown widget state."""
    if isinstance(value, str):
        value = value.strip()
        if value in PAGE_IDS:
            return value
        if value in _PAGE_LABELS:
            return _PAGE_LABELS[value]
        lowered = value.casefold()
        for label, target in _PAGE_LABELS.items():
            if label.casefold() == lowered:
                return target
    return None


def ensure_preferences(state):
    """Migrate old saved names without ever mutating a rendered widget."""
    if state.get('tt_lang') not in ('en', 'uk'):
        state['tt_lang'] = 'en'
    raw_theme = state.get('tt_theme', 'dark')
    state['tt_theme'] = canonical_theme(raw_theme) or canonical_theme(state.get('tt_theme_control')) or 'dark'
    state['tt_page'] = (canonical_page(state.get('tt_page'))
                        or canonical_page(state.get('tt_navigation_control'))
                        or PAGE_IDS[0])
    return state['tt_page'], state['tt_theme'], state['tt_lang']


def set_page(state, page):
    """Request a page without writing to a potentially mounted Streamlit widget.

    Streamlit forbids modifying a widget's session-state key after it has
    been instantiated in a run. All programmatic navigation must use this
    independent pending field, consumed before navigation radio is rendered.
    """
    canonical = canonical_page(page)
    if canonical is None:
        return False
    state['tt_page'] = canonical
    state['tt_navigation_pending'] = canonical
    return True


def select_navigation(state, widget_value):
    """Radio callback: user selection replaces any old programmatic request."""
    selected = canonical_page(widget_value)
    if selected is None:
        return False
    state['tt_page'] = selected
    state.pop('tt_navigation_pending', None)
    return True


def sync_navigation_before_widget(state):
    """Run before st.radio. This is the ONLY location writing its widget key."""
    desired = (canonical_page(state.pop('tt_navigation_pending', None))
               or canonical_page(state.get('tt_page')) or PAGE_IDS[0])
    state['tt_page'] = desired
    if state.get('tt_navigation_control') != desired:
        state['tt_navigation_control'] = desired
    return desired

def canonical_theme(value):
    """Accept historic EN/UA labels and canonical tokens; never guess a theme."""
    if not isinstance(value, str):
        return None
    value = value.strip().casefold()
    return {'dark': 'dark', 'темна': 'dark', 'light': 'light',
            'світла': 'light'}.get(value)


def set_theme(state, mode):
    """Safely update only canonical state, not a mounted Streamlit widget.

    Invalid/stale values are ignored. Streamlit may retain translated widget
    values from previous builds; they must never crash the whole application.
    """
    canonical = canonical_theme(mode)
    if canonical is None:
        return False
    state['tt_theme'] = canonical
    return True


def select_theme(state, widget_value):
    return set_theme(state, widget_value)


def sync_theme_before_widget(state):
    """Migrate stale values before the radio exists, not in its callback."""
    selected = (canonical_theme(state.get('tt_theme'))
                or canonical_theme(state.get(THEME_WIDGET_KEY))
                or canonical_theme(state.get('tt_theme_control'))
                or 'dark')
    state['tt_theme'] = selected
    if state.get(THEME_WIDGET_KEY) != selected:
        state[THEME_WIDGET_KEY] = selected
    return selected


def theme_name(mode, lang):
    canonical = canonical_theme(mode) or 'dark'
    return {'en': {'dark': 'Dark', 'light': 'Light'},
            'uk': {'dark': 'Темна', 'light': 'Світла'}}.get(
                lang, {'dark': 'Dark', 'light': 'Light'})[canonical]
