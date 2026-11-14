# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Optional local GLiM lithology fallback for an Earth point.

Only accepts a spatially matching, user-supplied, WGS84 GeoJSON excerpt from
Hartmann & Moosdorf's GLiM lithological map. Never extrapolates unsupported
rock types from climate, imagery colours or general location labels.
"""
from __future__ import annotations

import json
import math
from environment_evidence import geometry_contains

GLIM_URL = 'https://doi.org/10.1029/2012GC004370'
GLIM_CLASSES = {
    'su': ('Unconsolidated sediments', .58),
    'ss': ('Siliciclastic sedimentary rocks', .66),
    'sm': ('Mixed sedimentary rocks', .63),
    'sc': ('Carbonate sedimentary rocks', .65),
    'ev': ('Evaporites', .62),
    'py': ('Pyroclastic deposits', .72),
    'va': ('Acid volcanic rocks', .72),
    'vi': ('Intermediate volcanic rocks', .72),
    'vb': ('Basic volcanic rocks', .80),
    'pa': ('Acid plutonic rocks', .65),
    'pi': ('Intermediate plutonic rocks', .65),
    'pb': ('Basic plutonic rocks', .65),
    'mt': ('Metamorphic rocks', .60),
    # wb=water, ig=ice/glaciers, nd=no data are NOT lithology proxies.
}
VALID_CODES = set(GLIM_CLASSES) | {'wb', 'ig', 'nd'}


def parse_glim_geojson(file_bytes: bytes, lat: float, lon: float) -> dict:
    """Interpret first-level GLiM polygon classes; never assume GeoJSON means GLiM.

    User must explicitly import a prepared GLiM map; its provenance must still
    be confirmed by the user. Original data may be large: clip in GIS first.
    """
    if len(file_bytes) > 15_000_000:
        raise ValueError('GeoJSON exceeds 15 MB; clip the GLiM layer to the study area.')
    try:
        payload=json.loads(file_bytes.decode('utf-8-sig'))
    except (UnicodeError,ValueError) as exc:
        raise ValueError('Invalid UTF-8 GeoJSON.') from exc
    if not isinstance(payload,dict) or payload.get('type')!='FeatureCollection' or not isinstance(payload.get('features'),list):
        raise ValueError('Expected a GeoJSON FeatureCollection.')
    if len(payload['features']) > 20_000:
        raise ValueError('Too many polygons; clip the source dataset first.')
    crs=payload.get('crs')
    if crs and '4326' not in json.dumps(crs) and 'CRS84' not in json.dumps(crs).upper():
        raise ValueError('Reproject to WGS84 longitude/latitude first (EPSG:4326).')
    if not all(math.isfinite(float(v)) for v in (lat,lon)) or not -90<=float(lat)<=90 or not -180<=float(lon)<=180:
        raise ValueError('Invalid coordinate.')
    matched=[]
    for feature in payload['features']:
        if not isinstance(feature,dict):
            continue
        geom=feature.get('geometry')
        if not isinstance(geom,dict):
            continue
        # Reject obvious projected coordinates regardless of polygon match.
        def validate_vertices(obj, depth=0):
            if depth>8:
                raise ValueError('Geometry nesting is invalid.')
            if isinstance(obj,list) and obj and isinstance(obj[0],(int,float)):
                if len(obj)<2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in obj[:2]) or not (-180<=obj[0]<=180 and -90<=obj[1]<=90):
                    raise ValueError('Geometry must be in WGS84 degrees (EPSG:4326).')
            elif isinstance(obj,list):
                for child in obj:
                    validate_vertices(child,depth+1)
        validate_vertices(geom.get('coordinates'))
        if not geometry_contains((float(lon),float(lat)),geom):
            continue
        props=feature.get('properties') or {}
        if not isinstance(props,dict):
            continue
        # GLiM first-level class (xx). Avoid treating arbitrary labels as proof.
        val=props.get('xx') or props.get('XX') or props.get('glim_lithology') or props.get('glim_code')
        if val is None:
            continue
        code=str(val).strip().lower().split('_')[0][:2]
        if code not in VALID_CODES:
            continue
        matched.append(code)
    unique=set(matched)
    if not unique:
        return {'status':'no_coverage','source_url':GLIM_URL,
                'note':'No valid GLiM class polygon covers these coordinates.'}
    if len(unique)>1:
        return {'status':'ambiguous','source_url':GLIM_URL,
                'note':'Conflicting GLiM classes overlap this point; manual map review required.'}
    code=next(iter(unique))
    if code not in GLIM_CLASSES:
        return {'status':'no_rock_class','class_code':code,'source_url':GLIM_URL,
                'note':'This GLiM class is water, surface ice/glacier, or no data; it does not establish ground ice or a rock type.'}
    name,grade=GLIM_CLASSES[code]
    return {'status':'mapped_proxy','class_code':code,'rock_type':name,'score':grade,
            'source_url':GLIM_URL, 'source_name':'GLiM (Hartmann & Moosdorf 2012), uploaded GIS subset',
            'note':f'User-provided GLiM regional rock class: {name}. Illustrative field-test proxy; not an assay or lunar/Mars equivalence. Verify the uploaded map provenance.'}
