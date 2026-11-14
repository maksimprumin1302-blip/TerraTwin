# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Live Earth-observation discovery; returns METADATA, never scientific pixel values.

NASA CMR and Copernicus CDSE STAC are open research catalogues. Searching
products does not imply the products are processed in TerraTwin's scores.
"""
from __future__ import annotations
import math
import requests

CMR='https://cmr.earthdata.nasa.gov/search/collections.json'
STAC='https://stac.dataspace.copernicus.eu/v1/search'

class CatalogUnavailable(Exception):
    pass


def _valid(lat,lon):
    lat=float(lat);lon=float(lon)
    if not(math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):
        raise ValueError('Invalid coordinates')
    return lat,lon


def nasa_collections(lat,lon, requester=requests.get):
    lat,lon=_valid(lat,lon)
    params={'point':f'{lon:.4f},{lat:.4f}', 'page_size':8}
    try:
        response=requester(CMR,params=params,timeout=13,
                           headers={'User-Agent':'TerraTwin-Research-Explorer/2.1'})
        response.raise_for_status()
        items=response.json().get('feed',{}).get('entry',[])
        if not isinstance(items,list):raise ValueError('Invalid NASA CMR response')
        results=[]
        for item in items:
            title=item.get('title') or item.get('dataset_id')
            cid=item.get('id')
            if title and cid:
                results.append({'name':str(title)[:180], 'id':str(cid),
                                'url':f'https://search.earthdata.nasa.gov/search?q={cid}'})
        return results
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        raise CatalogUnavailable('NASA Earthdata CMR did not respond with usable metadata.') from exc


def sentinel_scenes(lat,lon,year=2025,requester=requests.post):
    lat,lon=_valid(lat,lon)
    if not 2015<=int(year)<=2100:raise ValueError('Invalid year')
    delta=0.016  # bbox ~1–4km, metadata query only
    bbox=[max(-180,lon-delta), max(-90,lat-delta),min(180,lon+delta),min(90,lat+delta)]
    payload={'collections':['sentinel-2-l2a'],
             'bbox':bbox,'datetime':f'{int(year)}-01-01T00:00:00Z/{int(year)}-12-31T23:59:59Z',
             'limit':6,'sortby':[{'field':'properties.datetime','direction':'desc'}]}
    try:
        response=requester(STAC,json=payload,timeout=15,
                           headers={'User-Agent':'TerraTwin-Research-Explorer/2.1', 'Accept':'application/geo+json'})
        response.raise_for_status()
        body=response.json()
        scenes=body.get('features')
        if not isinstance(scenes,list):raise ValueError('Invalid STAC response')
        result=[]
        for scene in scenes:
            props=scene.get('properties') or {}
            links=scene.get('links') or []
            landing=next((link.get('href') for link in links if link.get('rel')=='self'),None)
            result.append({'name':str(scene.get('id','Sentinel-2'))[:120],
                           'datetime':props.get('datetime',''),
                           'cloud_cover':props.get('eo:cloud_cover'),
                           'url':landing or 'https://dataspace.copernicus.eu/'})
        return result
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        raise CatalogUnavailable('Copernicus STAC did not return usable scene metadata.') from exc
