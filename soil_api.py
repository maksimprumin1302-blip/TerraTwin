# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Optional SoilGrids lookup. REST officially paused; any HTTP failure is reported.

SoilGrids values are model predictions, not point samples. This function isn't
called in the 'load all' path so an unavailable beta REST API does not hang it.
"""
from __future__ import annotations
import requests

ENDPOINT = 'https://rest.isric.org/soilgrids/v2.0/properties/query'
SOURCE = 'https://docs.isric.org/globaldata/soilgrids/index.html'

class SoilError(Exception):
    pass

# SoilGrids standard query for 0-5cm means; units require own metadata.
def fetch_soil(latitude:float, longitude:float):
    params=[('lat',float(latitude)),('lon',float(longitude)),
            ('property','sand'),('property','clay'),('property','bdod'),
            ('depth','0-5cm'),('value','mean')]
    try:
        r=requests.get(ENDPOINT,params=params,timeout=(5,11))
        if r.status_code != 200:
            raise SoilError(f'SoilGrids REST недоступний (HTTP {r.status_code}); скористайтеся WCS або WebDAV.')
        p=r.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise SoilError('SoilGrids REST недоступний. Використайте джерело WCS/WebDAV, посилання в каталозі.') from exc
    if not isinstance(p,dict) or not isinstance(p.get('properties'),dict):
        raise SoilError('SoilGrids повернув відповідь без очікуваних полів.')
    layers=p['properties'].get('layers')
    if not isinstance(layers,list):
        raise SoilError('SoilGrids не повернув шарів для цих координат.')
    results=[]
    for l in layers:
        if not isinstance(l,dict): continue
        for d in l.get('depths',[]):
            if not isinstance(d,dict):continue
            v=d.get('values')
            value=v.get('mean') if isinstance(v,dict) else None
            if value is not None:
                results.append({'property':l.get('name'),'depth':d.get('label'),
                                'raw_value':value,'unit_measure':l.get('unit_measure'),
                                'd_factor':l.get('d_factor')})
    return {'items':results,'source':SOURCE,'request_url':r.url}
