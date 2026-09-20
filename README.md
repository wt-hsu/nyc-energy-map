# NYC Energy Map

**Where New York City uses its energy — and where it comes from.**

An interactive map that puts the city's building energy demand (every large building reporting under Local Law 84, calendar year 2024) on the same canvas as its in-city power supply (EIA power plants and HIFLD transmission substations).

Live: `https://wt-hsu.github.io/nyc-energy-map/`

## Embed it

```html
<iframe
  src="https://wt-hsu.github.io/nyc-energy-map/"
  title="NYC Energy Map"
  width="100%" height="720"
  style="border:0;border-radius:16px;overflow:hidden"
  loading="lazy" allowfullscreen></iframe>
```

For a Next.js page, drop the same tag into a component (or use `next/dynamic` if you want it client-only). The page is fully static, so it can be embedded from any origin.

## What's in the map

| Layer | Source | What it encodes |
|---|---|---|
| Neighborhood demand | LL84 CY2024 aggregated to 2020 NTAs | Choropleth: total site energy, electricity, energy density, GHG, median EUI, median GHG intensity (switchable) |
| Buildings | LL84 CY2024, geocoded via PLUTO BBL | 4,000 largest consumers; circle size = site energy; filterable by building type |
| Power plants | EIA-860 via U.S. Energy Atlas | Circle size = nameplate MW; fuel mix in the detail panel |
| Substations | HIFLD Electric Substations | Transmission substations (imagery-derived, 2015 vintage) |

Interactions: layer toggles, metric switch, building-type filter (also re-computes the choropleth for energy metrics), hover tooltips, click-through detail panel, sortable table view, mobile bottom sheet.

## Rebuild the data

```bash
# 1. put the raw files in data/raw/  (URLs in data/raw/SOURCES.md)
# 2. python3 -m pip install pandas numpy shapely
python3 scripts/build_data.py
```

Cleaning rules (see `scripts/build_data.py`): Portfolio Manager parent/child duplicates are collapsed to one reporting unit; rows with site EUI outside 5–500 kBtu/ft² are dropped as reporting errors; buildings under 25,000 ft² are excluded. Conversions: 3.412 kBtu/kWh, 29.3 kWh/therm.

## Stack

Single static page — [MapLibre GL JS](https://maplibre.org/) (vendored in `vendor/`), OpenFreeMap vector tiles (open source, no API key) styled as a warm "glowing grid" basemap, no build step, no backend.

## Data sources

- NYC DOB — [NYC Building Energy and Water Data Disclosure for Local Law 84 (CY2022–present)](https://data.cityofnewyork.us/Environment/NYC-Building-Energy-and-Water-Data-Disclosure-for-/5zyy-y8am), dataset `5zyy-y8am`
- NYC DCP — [PLUTO](https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks), dataset `64uk-42ks`
- NYC DCP — [2020 Neighborhood Tabulation Areas](https://data.cityofnewyork.us/City-Government/2020-Neighborhood-Tabulation-Areas-NTAs-/9nt8-h7nd), dataset `9nt8-h7nd`
- U.S. EIA — [Power Plants, U.S. Energy Atlas](https://atlas.eia.gov/datasets/eia::power-plants) (EIA-860)
- HIFLD — [Electric Substations](https://hifld-geoplatform.opendata.arcgis.com/)
- Basemap tiles — [OpenFreeMap](https://openfreemap.org) (OpenMapTiles schema); map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL)

## License

Code: MIT. Data: per each source's terms (NYC Open Data — public domain; EIA — public domain; HIFLD — public).
