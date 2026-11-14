# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Reusable scientific dashboard charts for TerraTwin.

Charts are based exclusively on the evidence/score inputs passed to them.
Unknown evidence is rendered as unknown, not as a negative measurement.
"""

from __future__ import annotations

import csv
import io

import plotly.graph_objects as go

from analog_scoring import FEATURES, STATUS_SCORE

RED = '#d61f26'
CYAN = '#1f6daf'
YELLOW = '#ffc46b'
TEXT = '#182237'
MUTED = '#526477'
GRID = 'rgba(70,90,115,0.17)'
PAPER = 'rgba(0,0,0,0)'


def _layout(fig: go.Figure, height: int = 350, dark: bool = False) -> go.Figure:
    ink = '#eaf2ff' if dark else TEXT
    fig.update_layout(
        template='plotly_dark' if dark else 'plotly_white',
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family='Arial, sans-serif', color=ink, size=12),
        margin=dict(l=14, r=12, t=25, b=20),
        height=height,
        hoverlabel=dict(bgcolor='#18263d' if dark else '#f7f8fa', font=dict(color='#f4f8ff' if dark else '#182237')),
        showlegend=False,
    )
    return fig


def ranking_chart(ranking: list[dict], dark: bool = False, lang: str = 'en') -> go.Figure:
    """Horizontal bar chart recalculated from the same ranking results as score labels."""
    ordered = list(reversed(ranking))
    names = [entry['site'].get('name_en',entry['site']['name']) if lang=='en' else entry['site']['name'] for entry in ordered]
    values = [entry['score'] for entry in ordered]
    colors = [RED if idx == len(ordered) - 1 else CYAN for idx in range(len(ordered))]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        text=[f'{score}/100' for score in values],
        textposition='inside',
        insidetextanchor='end',
        textfont=dict(size=13, color='#ffffff'),
        hovertemplate='%{y}<br>Earth analog index: %{x}/100<extra></extra>' if lang=='en' else '%{y}<br>Індекс релевантності: %{x}/100<extra></extra>',
    ))
    fig.update_xaxes(range=[0, 100], dtick=20, ticksuffix='',
                     gridcolor=GRID, zeroline=False, title=None)
    fig.update_yaxes(showgrid=False, title=None, automargin=True)
    return _layout(fig, 310, dark)


def evidence_heatmap(sites: list[dict], evidence: dict, weights: dict[str, int], dark: bool = False, lang: str = 'en') -> go.Figure:
    """0 = no verified source (neutral); 0.5 partial; 1 confirmed."""
    keys = [key for key, weight in weights.items() if weight > 0]
    from localization import translate
    names = [translate(FEATURES[key],lang) for key in keys]
    rows, labels, hovers = [], [], []
    for site in sites:
        values, texts, tips = [], [], []
        for key in keys:
            entry = evidence.get(site['id'], {}).get(key, {})
            status = entry.get('status', 'unknown')
            values.append(STATUS_SCORE[status])
            text = {'yes': '✓', 'partial': '½', 'unknown': '—'}[status]
            texts.append(text)
            tips.append({
                'yes': 'Підтверджено',
                'partial': 'Частково підтверджено',
                'unknown': 'Немає перевіреного джерела',
            }[status])
        rows.append(values)
        labels.append(texts)
        hovers.append([translate(x,lang) for x in tips])
    fig = go.Figure(go.Heatmap(
        x=names, y=[site.get('name_en',site['name']) if lang=='en' else site['name'] for site in sites], z=rows, text=labels,
        customdata=hovers,
        texttemplate='%{text}', textfont=dict(color='#ffffff', size=19),
        zmin=0, zmax=1,
        colorscale=[
            [0.0, '#273344'], [0.499, '#273344'],
            [0.5, '#c18b45'], [0.999, '#c18b45'],
            [1.0, '#167fab'],
        ],
        xgap=5, ygap=5, showscale=False,
        hovertemplate='%{y}<br>%{x}<br>%{customdata}<extra></extra>',
    ))
    fig.update_xaxes(side='top', tickfont=dict(size=11), showgrid=False,
                     tickangle=0, automargin=True)
    fig.update_yaxes(autorange='reversed', showgrid=False, automargin=True)
    return _layout(fig, 310, dark)


def weather_temperature_chart(monthly, temperature_column: str, dark: bool = False, lang: str = 'en') -> go.Figure:
    labels = monthly['Дата']
    values = monthly[temperature_column]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values, name='Temperature' if lang=='en' else 'Температура', mode='lines+markers',
        line=dict(color=RED, width=3, shape='spline'),
        marker=dict(color='#ffb0a8', size=7, line=dict(color=RED, width=2)),
        fill='tozeroy', fillcolor='rgba(246,65,55,.09)',
        hovertemplate='%{x|%b %Y}<br>%{y:.1f} °C<extra></extra>',
    ))
    fig.update_yaxes(title='°C', gridcolor=GRID, zerolinecolor=GRID)
    fig.update_xaxes(gridcolor='rgba(0,0,0,0)', dtick='M1', tickformat='%b')
    return _layout(fig, 325, dark)


def weather_precip_chart(monthly, dark: bool = False, lang: str = 'en') -> go.Figure:
    fig = go.Figure(go.Bar(
        x=monthly['Дата'], y=monthly['Опади за місяць, мм'],
        marker_color=CYAN, width=24 * 3600 * 1000,
        hovertemplate='%{x|%b %Y}<br>%{y:.1f} mm<extra></extra>' if lang=='en' else '%{x|%b %Y}<br>%{y:.1f} мм<extra></extra>',
    ))
    fig.update_yaxes(title='mm' if lang=='en' else 'мм', gridcolor=GRID, rangemode='tozero')
    fig.update_xaxes(dtick='M1', tickformat='%b', showgrid=False)
    return _layout(fig, 325, dark)


def ranking_csv(ranking: list[dict], target_name: str, weights: dict[str, int]) -> bytes:
    """Export derived values (and their weights) with a clear scientific disclaimer."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['Ціль', 'Локація Землі', 'Індекс 0–100', 'Ознака', 'Вага', 'Статус'])
    for item in ranking:
        for criterion in item['calculation']['criteria']:
            writer.writerow([
                target_name, item['site']['name'], item['score'],
                FEATURES[criterion['feature']], criterion['weight'], criterion['status'],
            ])
    writer.writerow([])
    writer.writerow(['ПРИМІТКА', 'Це зважений індекс наявності доказів, НЕ фізичний відсоток схожості.'])
    return out.getvalue().encode('utf-8-sig')
