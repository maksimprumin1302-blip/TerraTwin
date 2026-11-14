# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Readable English translations for scientific source metadata.

Identifiers, URLs and scientific provenance are never rewritten.
"""
SRC_EN={
'nasa_cmr':('Automatic metadata search','Lists public NASA collections intersecting chosen coordinates.','Catalog discovery does not sample scientific pixels; some downloads require Earthdata Login.'),
'copernicus_stac':('Automatic metadata search','Searches Sentinel-2 L2A scenes by coordinates and calendar year.','Scene availability and cloud percentages do not establish rock or ice presence.'),
'jaxa_gsmap':('Research archive; not used in scoring','Global satellite-based precipitation estimates for possible future climate cross-checking.','Pixel sampling is not currently part of TerraTwin calculations.'),
'era5_archive':('Automatic model fallback','Gridded ERA5 / ERA5-Land climate reanalysis: air and soil temperatures, precipitation, sunshine and wind.','These are modeled estimates, not local measurements or direct evidence of ground ice.'),
'power':('Automatic point query','Gridded air temperature, precipitation, wind and solar energy for a selected Earth coordinate.','Gridded estimates are not on-site sensor measurements or Moon/Mars temperatures.'),
'copernicus':('Automatic point query','Elevation samples and coarse derived slope and local relief.','The slope is derived from sparse ~90 m DEM samples and cannot certify safe rover routes or landing sites.'),
'macrostrat':('Automatic where mapped','Mapped geological units, lithology and regional geologic ages.','Geologic map polygons do not equal laboratory measurements at the exact coordinate.'),
'glim':('GIS GeoJSON import','Global mapped lithology with major bedrock categories.','Requires importing a valid source map; not a direct mineral composition measurement.'),
'esa_permafrost':('External raster archive','Modeled regional permafrost estimates and ground temperatures.','Permafrost occurrence is not a direct ground-ice content measurement; raster values are not auto-sampled.'),
'worldcover':('Map visualization','ESA 10 m land-cover classifications from Sentinel imagery.','The displayed RGB WMS layer is not a numeric classification sample in TerraTwin.'),
'soilgrids':('GIS files; REST paused','Modeled global soil properties, including texture and bulk density.','Official REST API is paused. WCS/WebDAV or GIS processing is needed.'),
'permafrost':('GIS GeoJSON import','Circum-Arctic regional mapping of permafrost and ground-ice categories.','Historical regional classes require checking polygon geometry and source provenance.'),
'emit':('Spectral data archive','NASA surface-mineral spectral observations of selected dry regions.','Coverage is limited and requires downloading and processing science products.'),
'lola':('Planetary DEM archive','LRO LOLA Moon topography, including polar terrain.','Requires correct planetary coordinates and raster processing.'),
'diviner':('Planetary thermal archive','LRO Diviner temperature and thermal emission datasets.','Lunar surface temperatures are not equivalent to Earth 2 m air temperatures.'),
'illumination':('Planetary map archive','Models of solar illumination near lunar polar sites.','A specific place and observation period must be selected for meaningful comparison.'),
'mola':('Planetary DEM archive','MOLA global topographic models of Mars.','Requires downloading rasters and using Mars coordinate conventions.'),
'swim':('Planetary map archive','Mars subsurface water-ice evidence maps.','Multi-source indicators are not direct measurements of extractable ice.'),
'crism':('Planetary spectral archive','Mineral spectral images of selected Mars regions.','Spatial coverage is uneven, requiring specialized spectral processing.'),
'themis':('Planetary thermal archive','Infrared imagery and surface thermal properties from Mars Odyssey.','Observing time and physical variable must be taken into account.'),
'gibs':('Visual map layers','NASA satellite imagery layers for Earth exploration.','Imagery visualization is not direct, calibrated numerical evidence in TerraTwin.'),
}

def display_source(item,lang='en'):
    if lang!='en' or item['id'] not in SRC_EN:
        return item
    mode,what,limits=SRC_EN[item['id']]
    return {**item,'mode':mode,'what':what,'limits':limits}
