# NYC Energy Map — Concept & Spec

**Working title:** *Where New York Uses Its Energy — and Where It Comes From*
**One-line purpose:** An interactive map that puts NYC's building energy demand (every large building that reports under Local Law 84) on the same canvas as the city's in-city power supply (power plants and transmission substations), so a viewer can see, in one glance, how concentrated demand is, what powers it, and how thin the supply margin looks on a map.

## Why this map (portfolio framing)

- Demand and supply are almost never shown together. Benchmarking maps show buildings; grid maps show plants. Putting both on one canvas is the editorial point.
- It connects to the author's professional narrative: data-center / hyperscale capacity planning is fundamentally a "where is the load, where is the power, what binds" question. NYC is the cleanest public dataset in the world for showing that at city scale.
- Every number is traceable to an official open dataset (see Sources), which matters for MBA/job-application credibility.

## Audience

MBA admissions readers, recruiters and hiring managers in energy / infrastructure / data-center roles, and general readers of wantinghsu.com. Assume 60 seconds of attention: the map must deliver one insight without any clicks, and reward 3–5 minutes of exploration.

## The three layers

| Layer | Source | Geometry | Encodes |
|---|---|---|---|
| **Neighborhood demand** | LL84 CY2024 benchmarking, aggregated to NTA 2020 | 262 polygons | Sequential blue ramp: total site energy, electricity, or median GHG intensity (metric switch) |
| **Buildings** | LL84 CY2024, geocoded via PLUTO BBL | ~3,000 largest consumers as points | Circle size = site energy; single accent hue (amber); tooltip has type, EUI, ENERGY STAR, GHG |
| **Supply** | EIA-860 power plants (via EIA Atlas) + HIFLD substations | 81 plant points, 114 substation points | Plant circle size = nameplate MW, aqua; substations as small hollow diamonds; tooltip has fuel, MW, voltage |

Color roles follow the dataviz method: one sequential hue (blue) for magnitude, and at most three categorical accents (blue / amber / aqua) which validate all-pairs for colorblind safety. Identity is never carried by color alone — legend + shape + labels.

## Interactions

1. **Layer toggles** (Demand areas · Buildings · Power plants · Substations) — one control row, top-left.
2. **Metric switch** for the choropleth: Total energy (GWh-equivalent) · Electricity (GWh) · GHG intensity (median kgCO₂e/ft²) · Site EUI (median kBtu/ft²).
3. **Building-type filter** chips: Multifamily · Office · Education · Healthcare · Retail/Hotel · Other.
4. **Hover** tooltips on every mark; **click** a neighborhood → side panel with its stats, top-5 buildings, and building-type mix; click a plant → capacity by fuel.
5. **Headline stat tiles** (city totals) that re-compute against the active filter.
6. **Table view** toggle (accessibility twin of the choropleth): sortable NTA table.
7. Responsive: works at phone width inside an iframe; panel collapses to a bottom sheet.

## Visual direction

Deep-blue, night-city aesthetic to match wantinghsu.com: dark basemap (CARTO Dark Matter, no labels except at zoom), thin glowing marks, restrained typography (Inter). No dashboard-grid look — one map, one floating panel, one legend.

## Data pipeline (reproducible, in `scripts/`)

`build_data.py` → reads `data/raw/*` → writes `data/nta_energy.geojson` (simplified polygons + aggregates), `data/buildings_top.geojson`, `data/plants.geojson`, `data/substations.geojson`, `data/summary.json`. Filters: report year 2024, site energy > 0, GFA ≥ 25,000 ft², EUI within 1st–99th percentile to drop reporting errors.

## Delivery

Static site → GitHub Pages at `https://<user>.github.io/nyc-energy-map/`. Embed in Next.js with:

```html
<iframe src="https://<user>.github.io/nyc-energy-map/" width="100%" height="720" style="border:0;border-radius:16px" loading="lazy" title="NYC Energy Map"></iframe>
```

## Sources

- NYC DOB, *NYC Building Energy and Water Data Disclosure for Local Law 84 (CY2022–present)*, dataset `5zyy-y8am`, rows updated 2025-11-25 — https://data.cityofnewyork.us/Environment/NYC-Building-Energy-and-Water-Data-Disclosure-for-/5zyy-y8am
- NYC DCP, *Primary Land Use Tax Lot Output (PLUTO)*, dataset `64uk-42ks` — https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks
- NYC DCP, *2020 Neighborhood Tabulation Areas (NTAs)*, dataset `9nt8-h7nd` — https://data.cityofnewyork.us/City-Government/2020-Neighborhood-Tabulation-Areas-NTAs-/9nt8-h7nd
- U.S. EIA, *Power Plants* (U.S. Energy Atlas, from EIA-860) — https://atlas.eia.gov/datasets/eia::power-plants
- HIFLD, *Electric Substations* (via public ArcGIS feature service mirror) — https://hifld-geoplatform.opendata.arcgis.com/
- NYISO load-zone context (Zone J = NYC) — https://www.nyiso.com/documents/20142/1397960/nyca_zonemaps.pdf
