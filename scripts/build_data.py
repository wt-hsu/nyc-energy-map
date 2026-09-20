#!/usr/bin/env python3
"""Build the compact GeoJSON / JSON files the map consumes.

Inputs (data/raw/):
  ll84_cy2024.csv        NYC LL84 benchmarking, report_year 2024 (calendar year 2024)
  pluto_lots_10k.csv     PLUTO lots with bldgarea >= 10,000 ft2 (BBL -> lat/lon)
  nta2020.geojson        2020 Neighborhood Tabulation Areas
  eia_plants_nyc.geojson EIA power plants in the five boroughs
  substations_nyc.geojson HIFLD substations in the five boroughs

Outputs (data/):
  nta_energy.geojson, buildings_top.geojson, plants.geojson, substations.geojson, summary.json
"""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from shapely.geometry import shape, Point, mapping
from shapely.strtree import STRtree
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / 'data' / 'raw', ROOT / 'data'
KBTU_PER_KWH = 3.412
TOP_N_BUILDINGS = 4000

# ---------- 1. LL84 ----------
ll = pd.read_csv(RAW / 'll84_cy2024.csv', low_memory=False)
num_cols = ['property_gfa_self_reported', 'site_eui_kbtu_ft', 'weather_normalized_site_eui',
            'site_energy_use_kbtu', 'electricity_use_grid_purchase_1', 'electricity_use_generated_1',
            'natural_gas_use_therms_', 'district_steam_use_kbtu', 'fuel_oil_2_use_kbtu',
            'fuel_oil_4_use_kbtu', 'total_location_based_ghg', 'total_location_based_ghg_1',
            'energy_star_score', 'data_center_gross_floor_area']
for c in num_cols:
    ll[c] = pd.to_numeric(ll[c], errors='coerce')

def first_bbl(s):
    if not isinstance(s, str):
        return None
    tok = re.split(r'[;,]', s)[0].strip()
    m = re.match(r'^(\d)-(\d{1,5})-(\d{1,4})$', tok)
    if m:
        return int(f"{m.group(1)}{int(m.group(2)):05d}{int(m.group(3)):04d}")
    tok = re.sub(r'\D', '', tok)
    return int(tok) if len(tok) == 10 else None

ll['bbl'] = ll['nyc_borough_block_and_lot'].map(first_bbl)

# property-type grouping (<= 6 classes so the filter stays legible)
def group_type(t):
    t = str(t)
    if t == 'Multifamily Housing': return 'Multifamily'
    if t in ('Office', 'Financial Office', 'Medical Office', 'Bank Branch'): return 'Office'
    if t in ('K-12 School', 'College/University', 'Residence Hall/Dormitory', 'Pre-school/Daycare',
             'Adult Education', 'Other - Education', 'Library'): return 'Education'
    if 'Hospital' in t or t in ('Senior Living Community', 'Residential Care Facility', 'Laboratory',
                                'Urgent Care/Clinic/Other Outpatient', 'Ambulatory Surgical Center',
                                'Outpatient Rehabilitation/Physical Therapy'): return 'Healthcare'
    if t in ('Hotel', 'Retail Store', 'Strip Mall', 'Enclosed Mall', 'Supermarket/Grocery Store',
             'Wholesale Club/Supercenter', 'Restaurant', 'Food Service', 'Other - Mall',
             'Vehicle Dealership', 'Other - Lodging/Residential'): return 'Retail & Hotel'
    if t in ('Data Center',): return 'Data Center'
    return 'Other'
ll['type_group'] = ll['primary_property_type'].map(group_type)

# quality filters
n0 = len(ll)
ll = ll[(ll['site_energy_use_kbtu'] > 0) & (ll['property_gfa_self_reported'] >= 25000)].copy()
# (a) parent/child duplicates: Portfolio Manager campuses report the same totals on the parent and on each
#     child property. Rows with identical site energy are one reporting unit -> keep the largest-GFA row.
ll['_e'] = ll['site_energy_use_kbtu'].round(0)
ll = ll.sort_values('property_gfa_self_reported', ascending=False).drop_duplicates('_e', keep='first').drop(columns='_e')
n1 = len(ll)
# (b) implausible intensities are reporting errors (e.g. a nursing home at 251,650 kBtu/ft2). Hospitals and
#     labs top out around 400-500; data centers are the only legitimate class above that and are rare in LL84.
EUI_LO, EUI_HI = 5, 500
ll = ll[ll['site_eui_kbtu_ft'].between(EUI_LO, EUI_HI)].copy()
ll['eui_ok'] = True
print(f'LL84 rows: {n0} -> {n1} after dedupe -> {len(ll)} after EUI {EUI_LO}-{EUI_HI} filter')

# ---------- 2. PLUTO join ----------
pl = pd.read_csv(RAW / 'pluto_lots_10k.csv', low_memory=False)
pl['bbl'] = pd.to_numeric(pl['bbl'], errors='coerce').round().astype('Int64')
pl = pl.dropna(subset=['bbl', 'latitude', 'longitude']).drop_duplicates('bbl')
ll = ll.merge(pl[['bbl', 'latitude', 'longitude', 'cd', 'council']], on='bbl', how='left')
matched = ll['latitude'].notna()
print(f'geocoded via PLUTO: {matched.sum()} / {len(ll)} ({matched.mean():.1%})')
ll = ll[matched].copy()
ll['boro'] = (ll['bbl'] // 1_000_000_000).map({1: 'Manhattan', 2: 'Bronx', 3: 'Brooklyn', 4: 'Queens', 5: 'Staten Island'})

# derived metrics
ll['energy_gwh'] = ll['site_energy_use_kbtu'] / KBTU_PER_KWH / 1e6
ll['elec_gwh'] = ll['electricity_use_grid_purchase_1'].fillna(0) / 1e6
ll['gas_gwh'] = ll['natural_gas_use_therms_'].fillna(0) * 29.3001 / 1e6   # therm = 29.3 kWh
ll['steam_gwh'] = ll['district_steam_use_kbtu'].fillna(0) / KBTU_PER_KWH / 1e6
ll['oil_gwh'] = (ll['fuel_oil_2_use_kbtu'].fillna(0) + ll['fuel_oil_4_use_kbtu'].fillna(0)) / KBTU_PER_KWH / 1e6
ll['ghg_t'] = ll['total_location_based_ghg']

# ---------- 3. NTA assignment ----------
nta_fc = json.load(open(RAW / 'nta2020.geojson'))
nta_feats = [f for f in nta_fc['features'] if f['properties'].get('ntatype') == '0']   # residential/mixed NTAs; drop parks/airports/cemeteries
polys = [shape(f['geometry']) for f in nta_feats]
tree = STRtree(polys)
pts = [Point(x, y) for x, y in zip(ll['longitude'], ll['latitude'])]
idx = np.full(len(pts), -1)
for i, p in enumerate(pts):
    cands = tree.query(p, predicate='within')
    if len(cands):
        idx[i] = cands[0]
    else:  # fall back to nearest polygon within ~150 m (buildings on NTA edges / park-type NTAs)
        near = tree.nearest(p)
        if polys[near].distance(p) < 0.0015:
            idx[i] = near
ll['nta_i'] = idx
print(f'assigned to NTA: {(idx >= 0).sum()} / {len(idx)}')
ll = ll[ll['nta_i'] >= 0].copy()

# ---------- 4. Aggregate ----------
agg_rows = []
for i, f in enumerate(nta_feats):
    g = ll[ll['nta_i'] == i]
    p = f['properties']
    area_km2 = float(p['shape_area']) * 0.09290304 / 1e6
    ok = g[g['eui_ok']]
    mix = g.groupby('type_group')['energy_gwh'].sum().sort_values(ascending=False)
    top = g.nlargest(5, 'energy_gwh')[['property_name', 'address_1', 'type_group', 'energy_gwh', 'site_eui_kbtu_ft']]
    agg_rows.append({
        'nta': p['nta2020'], 'name': p['ntaname'], 'boro': p['boroname'], 'area_km2': round(area_km2, 3),
        'n': int(len(g)), 'gfa_msf': round(g['property_gfa_self_reported'].sum() / 1e6, 2),
        'energy_gwh': round(g['energy_gwh'].sum(), 2), 'elec_gwh': round(g['elec_gwh'].sum(), 2),
        'gas_gwh': round(g['gas_gwh'].sum(), 2), 'steam_gwh': round(g['steam_gwh'].sum(), 2),
        'oil_gwh': round(g['oil_gwh'].sum(), 2), 'ghg_kt': round(g['ghg_t'].sum() / 1e3, 2),
        'density': round(g['energy_gwh'].sum() / area_km2, 2) if area_km2 > 0 else None,
        'eui_med': round(float(ok['site_eui_kbtu_ft'].median()), 1) if len(ok) else None,
        'ghgi_med': round(float(ok['total_location_based_ghg_1'].median()), 2) if len(ok) else None,
        'elec_share': round(float(g['elec_gwh'].sum() / g['energy_gwh'].sum()), 3) if g['energy_gwh'].sum() > 0 else None,
        'mix': {k: round(v, 2) for k, v in mix.items()},
        'top': [{'name': (r.property_name if isinstance(r.property_name, str) else r.address_1),
                 'addr': r.address_1, 'type': r.type_group, 'gwh': round(r.energy_gwh, 2),
                 'eui': None if pd.isna(r.site_eui_kbtu_ft) else round(r.site_eui_kbtu_ft, 1)} for r in top.itertuples()],
    })

def rnd(geom, tol=0.00025):
    g = geom.simplify(tol, preserve_topology=True)
    return json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), 5))

nta_out = {'type': 'FeatureCollection', 'features': []}
for i, f in enumerate(nta_feats):
    if agg_rows[i]['n'] == 0:
        continue
    nta_out['features'].append({'type': 'Feature', 'id': i, 'properties': agg_rows[i], 'geometry': rnd(polys[i])})
json.dump(nta_out, open(OUT / 'nta_energy.geojson', 'w'), separators=(',', ':'))

# borough outlines (dissolve)
boros = {}
for f, poly in zip(nta_feats, polys):
    boros.setdefault(f['properties']['boroname'], []).append(poly)
for f in nta_fc['features']:  # include park/airport NTAs for a complete outline
    if f['properties'].get('ntatype') != '0':
        boros.setdefault(f['properties']['boroname'], []).append(shape(f['geometry']))
boro_out = {'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'properties': {'boro': b}, 'geometry': rnd(unary_union(ps).buffer(0.0002).buffer(-0.0002), 0.0004)}
    for b, ps in boros.items()]}
json.dump(boro_out, open(OUT / 'boroughs.geojson', 'w'), separators=(',', ':'))

# ---------- 5. Buildings (top N by site energy) ----------
top = ll.nlargest(TOP_N_BUILDINGS, 'energy_gwh')
b_out = {'type': 'FeatureCollection', 'features': []}
for r in top.itertuples():
    b_out['features'].append({'type': 'Feature', 'properties': {
        'name': r.property_name if isinstance(r.property_name, str) else r.address_1,
        'addr': r.address_1, 'type': r.type_group, 'ptype': r.primary_property_type, 'boro': r.boro,
        'nta': nta_feats[r.nta_i]['properties']['ntaname'], 'built': int(r.year_built) if r.year_built > 0 else None,
        'gfa': int(r.property_gfa_self_reported), 'gwh': round(r.energy_gwh, 2), 'elec': round(r.elec_gwh, 2),
        'gas': round(r.gas_gwh, 2), 'steam': round(r.steam_gwh, 2),
        'eui': None if pd.isna(r.site_eui_kbtu_ft) else round(r.site_eui_kbtu_ft, 1),
        'ghgi': None if pd.isna(r.total_location_based_ghg_1) else round(r.total_location_based_ghg_1, 2),
        'star': None if pd.isna(r.energy_star_score) else int(r.energy_star_score),
    }, 'geometry': {'type': 'Point', 'coordinates': [round(r.longitude, 5), round(r.latitude, 5)]}})
json.dump(b_out, open(OUT / 'buildings_top.geojson', 'w'), separators=(',', ':'))

# ---------- 6. Supply ----------
pf = json.load(open(RAW / 'eia_plants_nyc.geojson'))
fuel_keys = {'NG_MW': 'Natural gas', 'Solar_MW': 'Solar', 'Bat_MW': 'Battery', 'Crude_MW': 'Petroleum',
             'Bio_MW': 'Biomass', 'Hydro_MW': 'Hydro', 'Other_MW': 'Other', 'Coal_MW': 'Coal', 'Nuclear_MW': 'Nuclear',
             'Wind_MW': 'Wind', 'Geo_MW': 'Geothermal', 'HydroPS_MW': 'Pumped storage'}
p_out = {'type': 'FeatureCollection', 'features': []}
for f in pf['features']:
    q = f['properties']
    fuels = {v: round(q[k], 1) for k, v in fuel_keys.items() if q.get(k) and q[k] > 0}
    p_out['features'].append({'type': 'Feature', 'properties': {
        'name': q['Plant_Name'], 'mw': round(q['Total_MW'], 1), 'src': q['PrimSource'], 'tech': q['tech_desc'],
        'sector': q['sector_nam'], 'utility': q['Utility_Na'], 'city': q['City'], 'county': q['County'],
        'fuels': fuels, 'period': q.get('Period')},
        'geometry': {'type': 'Point', 'coordinates': [round(q['Longitude'], 5), round(q['Latitude'], 5)]}})
json.dump(p_out, open(OUT / 'plants.geojson', 'w'), separators=(',', ':'))

sf = json.load(open(RAW / 'substations_nyc.geojson'))
s_out = {'type': 'FeatureCollection', 'features': []}
for f in sf['features']:
    q = f['properties']
    name = q['NAME'] if not str(q['NAME']).startswith('UNKNOWN') else 'Unnamed substation'
    s_out['features'].append({'type': 'Feature', 'properties': {
        'name': name.title(), 'kv': q['MAX_VOLT'] if q['MAX_VOLT'] and q['MAX_VOLT'] > 0 else None,
        'lines': q['LINES'] if q['LINES'] and q['LINES'] > 0 else None, 'status': str(q['STATUS']).title(),
        'county': str(q['COUNTY']).title()},
        'geometry': {'type': 'Point', 'coordinates': [round(q['LONGITUDE'], 5), round(q['LATITUDE'], 5)]}})
json.dump(s_out, open(OUT / 'substations.geojson', 'w'), separators=(',', ':'))

# ---------- 7. Summary ----------
by_boro = ll.groupby('boro').agg(n=('bbl', 'size'), energy_gwh=('energy_gwh', 'sum'), elec_gwh=('elec_gwh', 'sum'),
                                 ghg_kt=('ghg_t', lambda s: s.sum() / 1e3), gfa_msf=('property_gfa_self_reported', lambda s: s.sum() / 1e6))
by_type = ll.groupby('type_group').agg(n=('bbl', 'size'), energy_gwh=('energy_gwh', 'sum'), elec_gwh=('elec_gwh', 'sum'))
plant_mw = {}
for f in p_out['features']:
    for k, v in f['properties']['fuels'].items():
        plant_mw[k] = round(plant_mw.get(k, 0) + v, 1)
plant_boro = {}
for f in p_out['features']:
    c = f['properties']['county']
    plant_boro[c] = round(plant_boro.get(c, 0) + f['properties']['mw'], 1)
summary = {
    'year': 2024, 'buildings': int(len(ll)), 'gfa_msf': round(ll['property_gfa_self_reported'].sum() / 1e6, 1),
    'energy_gwh': round(ll['energy_gwh'].sum(), 1), 'elec_gwh': round(ll['elec_gwh'].sum(), 1),
    'gas_gwh': round(ll['gas_gwh'].sum(), 1), 'steam_gwh': round(ll['steam_gwh'].sum(), 1), 'oil_gwh': round(ll['oil_gwh'].sum(), 1),
    'ghg_kt': round(ll['ghg_t'].sum() / 1e3, 1),
    'by_boro': {k: {c: round(float(v), 2) for c, v in r.items()} for k, r in by_boro.to_dict('index').items()},
    'by_type': {k: {c: round(float(v), 2) for c, v in r.items()} for k, r in by_type.to_dict('index').items()},
    'plants': len(p_out['features']), 'plant_mw': round(sum(f['properties']['mw'] for f in p_out['features']), 1),
    'plant_mw_by_fuel': dict(sorted(plant_mw.items(), key=lambda kv: -kv[1])),
    'plant_mw_by_county': plant_boro, 'substations': len(s_out['features']),
    'top_nta': sorted([{k: r[k] for k in ('nta', 'name', 'boro', 'energy_gwh', 'density')} for r in agg_rows], key=lambda r: -r['energy_gwh'])[:10],
    'metric_ranges': {m: [float(np.nanpercentile([r[m] for r in agg_rows if r[m] is not None and r['n'] > 0], q)) for q in (5, 95)]
                      for m in ('energy_gwh', 'elec_gwh', 'density', 'eui_med', 'ghgi_med', 'ghg_kt')},
}
json.dump(summary, open(OUT / 'summary.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ('top_nta', 'by_type', 'by_boro')}, indent=1))
print('sizes:', {p.name: f'{p.stat().st_size/1024:.0f} KB' for p in OUT.glob('*.*json')})
