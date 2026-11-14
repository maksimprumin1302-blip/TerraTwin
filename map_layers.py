"""Folium map powered by OpenStreetMap standard tiles: NO API key required.

World wraps horizontally. Site dots are duplicated in nearby worlds; user-selected
locations are duplicated too. Clicks in any world copy are mapped back to [-180,180].
"""
from __future__ import annotations
from html import escape
import folium
from branca.element import Element

COPY_INDICES = (-2, -1, 0, 1, 2)
OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'


def normalize_longitude(longitude: float) -> float:
    """A click in repeated world tiles represents the same lon in the main world."""
    return ((float(longitude) + 180) % 360) - 180


def is_valid_point(lat: float, lon: float) -> bool:
    return -89.9 <= lat <= 89.9 and -180 <= lon <= 180


def build_world_map(sites: list[dict], selected_id: str | None = None,
                    dark: bool = False, picked: tuple[float, float] | None = None,
                    center: tuple[float, float] | None = None,
                    zoom: int | None = None, fit_sites: bool = True, lang: str = 'en') -> folium.Map:
    # OSM is free to browse subject to its usage policy, not an API-key basemap.
    init_center = list(center) if center is not None else [20, 10]
    world = folium.Map(location=init_center, zoom_start=zoom if zoom is not None else 2,
                       min_zoom=2, max_zoom=17, tiles=None,
                       control_scale=True, world_copy_jump=True, prefer_canvas=True)
    folium.TileLayer(tiles=OSM_TILES, attr=OSM_ATTR,
                     name=('OpenStreetMap basemap' if lang=='en' else 'Карта OpenStreetMap'), overlay=False,
                     control=False, max_zoom=19).add_to(world)
    if dark:
        # The filter intentionally affects map tiles, not text/markers.
        world.get_root().header.add_child(Element('<style>.leaflet-tile-pane {filter:invert(1) hue-rotate(180deg) brightness(.73) contrast(1.08)}</style>'))
    # Research overlays load only if the visitor enables them in Leaflet layer control.
    # Do not confuse visual WMS and PNG tiles with numeric pixel observations.
    folium.TileLayer(
        tiles='https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png',
        name=('Macrostrat geology (visual)' if lang=='en' else 'Геологія · Macrostrat (візуально)'),
        attr='Macrostrat · CC BY 4.0',
        overlay=True, control=True, show=False,
    ).add_to(world)
    folium.raster_layers.WmsTileLayer(
        url='https://services.terrascope.be/wms/v2',
        layers='WORLDCOVER_2021_MAP',
        name=('ESA WorldCover 2021 (visual)' if lang=='en' else 'ESA WorldCover 2021 (візуально)'),
        fmt='image/png', transparent=True,
        attr='ESA WorldCover 2021 · © ESA / Copernicus Sentinel',
        overlay=True, control=True, show=False,
    ).add_to(world)
    folium.LayerControl(collapsed=True).add_to(world)
    for site in sites:
        moon = site['planet'] == 'Місяць'
        color = '#41a8e9' if moon else '#e74750'
        chosen = site['id'] == selected_id
        name=site.get('name_en',site['name']) if lang=='en' else site['name']
        country=site.get('country_en',site['country']) if lang=='en' else site['country']
        terrain=site.get('terrain_en',site['terrain']) if lang=='en' else site['terrain']
        planet=('Moon' if site['planet']=='Місяць' else 'Mars') if lang=='en' else site['planet']
        popup = (f'<div style="font-family:Arial;min-width:180px;color:#132139">'
                 f'<strong>{escape(name)}</strong><br>'
                 f'{escape(country)}<br>'
                 f'{escape(terrain)}<br>'
                 f'{"Analog" if lang=="en" else "Аналог"}: {escape(planet)}' '</div>')
        for offset in COPY_INDICES:
            folium.CircleMarker(
                location=[site['latitude'], site['longitude'] + 360*offset],
                radius=9 if chosen else 7, color='#fff' if chosen else color,
                fill=True, fill_color=color, fill_opacity=.97,
                weight=3 if chosen else 1.5,
                tooltip=name, popup=folium.Popup(popup,max_width=270),
            ).add_to(world)
    if picked is not None:
        lat, lon = picked
        for offset in COPY_INDICES:
            folium.CircleMarker(
                location=[lat, lon + 360*offset],
                radius=11, color='#ffffff', weight=3,
                fill=True, fill_color='#f6b731', fill_opacity=1,
                tooltip=f'{"Selected point" if lang=="en" else "Обрана точка"}: {lat:.3f}, {lon:.3f}',
            ).add_to(world)
    if fit_sites and len(sites) > 1 and center is None:
        world.fit_bounds([[s['latitude'], s['longitude']] for s in sites],padding=(35,35))
    elif fit_sites and len(sites) == 1 and center is None:
        world.location=[sites[0]['latitude'],sites[0]['longitude']]
        world.options['zoom']=5
    return world
