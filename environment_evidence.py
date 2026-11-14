# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Source-aware interpretation of geological map and optional NSIDC GGD318 vector data.

The results are *field-test heuristics*, not mineral assays or ground-ice measurements.
Unverified/missing values must not be converted into scores.
"""
from __future__ import annotations
import json
import math

MACROSTRAT_URL = 'https://macrostrat.org/api/v2/geologic_units/map'
NSIDC_URL = 'https://nsidc.org/data/ggd318/versions/2'
NSIDC_CITATION = 'Brown et al. (2002), GGD318 v2, DOI:10.7265/skbg-kf16'

# Only unambiguous rock groups are mapped to an illustrative *testing usefulness* grade.
# Unknown mineral names or unconstrained geological descriptions are never scored.
LITHOLOGY_RULES = (
    ('basalt', ('basalt', 'basaltic'), .80, 'Basaltic rocks / volcanic navigation and sampling'),
    ('volcanic', ('volcanic', 'lava', 'andesite', 'rhyolite', 'dacite', 'tuff'), .72, 'Volcanic rocks / geology and rover testing'),
    ('sedimentary', ('sandstone', 'mudstone', 'siltstone', 'limestone', 'shale', 'conglomerate'), .66, 'Sedimentary rocks / outcrop and sampling tests'),
    ('igneous', ('granite', 'gabbro', 'diorite', 'peridotite'), .65, 'Igneous rocks / instrument testing'),
    ('metamorphic', ('gneiss', 'schist', 'quartzite', 'slate', 'marble'), .60, 'Metamorphic rocks / surface instrument testing'),
    ('evaporite', ('evaporite', 'halite', 'gypsum'), .62, 'Evaporites / mineral identification tests'),
)


def mapped_materials(geology):
    """Conservative classification based strictly on lithology fields, not the map unit title."""
    if not isinstance(geology, dict) or geology.get('status') != 'ok':
        return {'status':'unknown', 'reason':'No validated Macrostrat map-unit response.'}
    matches = []
    for unit in geology.get('units', []):
        if not isinstance(unit, dict):
            continue
        raw = unit.get('lithology')
        if not isinstance(raw, str) or not raw.strip():
            continue
        cleaned=raw.casefold()
        for code, needles, value, label in LITHOLOGY_RULES:
            if any(word in cleaned for word in needles):
                matches.append({'class':code,'grade':value,'description':label,
                                'lithology':raw,'unit':unit.get('unit'),
                                'source_id':unit.get('source_id'), 'map_id':unit.get('map_id')})
                break
    if not matches:
        return {'status':'unknown', 'reason':'Geological map returned no classifiable lithology field.'}
    # A mixed map is not just its most useful rock type; average all classified units.
    grade = sum(m['grade'] for m in matches)/len(matches)
    return {'status':'mapped_proxy', 'score':round(grade,3), 'matches':matches,
            'source_url':geology.get('query_url') or MACROSTRAT_URL,
            'note':'Illustrative Earth field-testing score from mapped lithology, not laboratory-confirmed composition or planetary similarity. Map scale and local variation apply.'}


def nsidc_coverage(latitude, longitude):
    """BBox filter only: within dataset bounds does NOT imply permafrost is present."""
    lat,lon=float(latitude),float(longitude)
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Invalid coordinates')
    if lat < 28:
        return {'status':'outside_coverage','note':'Outside the published NSIDC GGD318 northern extent (28°N–90°N). No conclusion about local ice.', 'source_url':NSIDC_URL}
    return {'status':'in_extent_unchecked', 'note':'Inside the dataset bounding area only. No permafrost or ice classification is inferred without a matching map polygon.', 'source_url':NSIDC_URL}


def _contains_ring(point, ring):
    """Ray casting in WGS84 longitude/latitude; boundary counts as inside."""
    x,y=point
    inside=False
    if not isinstance(ring,list) or len(ring)<4:
        return False
    prev=ring[-1]
    for cur in ring:
        if not isinstance(cur,(list,tuple)) or not isinstance(prev,(list,tuple)) or len(cur)<2 or len(prev)<2:
            return False
        x1,y1=prev[:2]; x2,y2=cur[:2]
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x1,y1,x2,y2)):
            return False
        dx=x2-x1;dy=y2-y1
        if abs(dx*(y-y1)-dy*(x-x1))<1e-10 and min(x1,x2)-1e-10<=x<=max(x1,x2)+1e-10 and min(y1,y2)-1e-10<=y<=max(y1,y2)+1e-10:
            return True
        if (y1>y)!=(y2>y) and x < dx*(y-y1)/(y2-y1)+x1:
            inside=not inside
        prev=cur
    return inside


def _contains_polygon(point, polygon):
    return bool(polygon and _contains_ring(point,polygon[0]) and not any(_contains_ring(point,hole) for hole in polygon[1:]))


def geometry_contains(point, geometry):
    if not isinstance(geometry,dict):
        return False
    t=geometry.get('type'); coords=geometry.get('coordinates')
    if t=='Polygon' and isinstance(coords,list):
        return _contains_polygon(point,coords)
    if t=='MultiPolygon' and isinstance(coords,list):
        return any(_contains_polygon(point,p) for p in coords)
    return False


def parse_ground_ice_geojson(file_bytes, lat, lon):
    """Query user-supplied NSIDC polygons reprojected to EPSG:4326.

    Required explicit properties: permafrost_extent and ground_ice_category.
    This prevents treating arbitrary NUM_CODE tokens as physical measurements.
    Class values are interpreted as regional estimates, not point measurements.
    """
    if len(file_bytes)>15_000_000:
        raise ValueError('GeoJSON exceeds 15 MB; please clip the source layer in QGIS.')
    try:
        payload=json.loads(file_bytes.decode('utf-8-sig'))
    except (UnicodeError, ValueError) as exc:
        raise ValueError('Invalid UTF-8 GeoJSON file.') from exc
    if not isinstance(payload,dict) or payload.get('type') != 'FeatureCollection' or not isinstance(payload.get('features'),list):
        raise ValueError('Expected a GeoJSON FeatureCollection.')
    if len(payload['features'])>20000:
        raise ValueError('Please clip the dataset to an area of interest (20,000 polygon limit).')
    # GeoJSON RFC7946 coordinates must be WGS84 lon/lat. Reject explicit non-WGS84 CRS.
    crs=payload.get('crs')
    if crs and '4326' not in json.dumps(crs) and 'CRS84' not in json.dumps(crs).upper():
        raise ValueError('Reproject the map to WGS84 (EPSG:4326) before export.')
    point=(float(lon),float(lat))
    if not all(math.isfinite(x) for x in point) or not -180<=point[0]<=180 or not -90<=point[1]<=90:
        raise ValueError('Invalid point coordinates.')
    matched=[]
    for feature in payload['features']:
        # Never interpret native projected (metre) coordinates as WGS84 degrees.
        geom=feature.get('geometry') if isinstance(feature,dict) else None
        if isinstance(geom,dict) and geom.get('type') in ('Polygon','MultiPolygon'):
            def _validate_vertices(obj, depth=0):
                if depth>8:
                    raise ValueError('GeoJSON geometry nesting is invalid.')
                if isinstance(obj, (list,tuple)) and obj and isinstance(obj[0],(int,float)):
                    if len(obj)<2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in obj[:2]) or not -180<=obj[0]<=180 or not -90<=obj[1]<=90:
                        raise ValueError('Coordinates outside WGS84 lon/lat bounds. Reproject to EPSG:4326.')
                elif isinstance(obj,list):
                    for child in obj:
                        _validate_vertices(child,depth+1)
            _validate_vertices(geom.get('coordinates'))
    for feature in payload['features']:
        if not isinstance(feature,dict) or not geometry_contains(point,feature.get('geometry')):
            continue
        props=feature.get('properties') or {}
        if not isinstance(props,dict):
            continue
        extent=str(props.get('permafrost_extent','')).strip().casefold()
        ice=str(props.get('ground_ice_category','')).strip().casefold()
        allowed_extent={'continuous','discontinuous','sporadic','isolated','none','unknown'}
        allowed_ice={'high','medium','low','none','unknown'}
        if extent not in allowed_extent or ice not in allowed_ice:
            raise ValueError('Matching polygon requires normalized permafrost_extent (continuous/discontinuous/sporadic/isolated/none/unknown) and ground_ice_category (high/medium/low/none/unknown).')
        matched.append({'permafrost_extent':extent,'ground_ice_category':ice,'properties':props})
    if not matched:
        return {'status':'no_polygon', 'note':'The imported GeoJSON has no polygon containing this point. This does not prove absence of ice.', 'source_url':NSIDC_URL}
    # Overlapping polygons are ambiguous. Do not silently choose one.
    classes={(m['permafrost_extent'],m['ground_ice_category']) for m in matched}
    if len(classes)>1:
        return {'status':'ambiguous','note':'Several overlapping polygons have conflicting categories. Review GIS data manually.', 'source_url':NSIDC_URL}
    item=matched[0]
    return {'status':'mapped_class', 'permafrost_extent':item['permafrost_extent'],
            'ground_ice_category':item['ground_ice_category'],
            'source_url':NSIDC_URL, 'citation':NSIDC_CITATION,
            'note':'Regional historical polygon classes from NSIDC GGD318. Not a point measurement of present-day ground-ice volume.'}


def ice_testing_proxy(ice_record):
    """Returns a transparent author-chosen trial-usefulness score, never ice % content."""
    if not isinstance(ice_record,dict) or ice_record.get('status') != 'mapped_class':
        return None
    cls=ice_record.get('ground_ice_category')
    # A mapped no-ice class may be useful for negative-control tests, but this
    # score specifically measures ground-ice field-test relevance.
    lookup={'high':.90,'medium':.70,'low':.45,'none':.0}
    if cls not in lookup:
        return None
    return {'score':lookup[cls], 'source_url':NSIDC_URL,
            'note':f"NSIDC GGD318 mapped class: ground ice '{cls}', permafrost '{ice_record.get('permafrost_extent')}'. Score is an author-defined field-testing relevance proxy, NOT percent ground ice nor a verified local observation."}
