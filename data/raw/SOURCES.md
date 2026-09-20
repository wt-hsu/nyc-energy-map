# Raw inputs (not committed — download to this folder, then run scripts/build_data.py)

| file | URL |
|---|---|
| ll84_cy2024.csv | https://data.cityofnewyork.us/resource/5zyy-y8am.csv?$select=property_id,property_name,nyc_borough_block_and_lot,nyc_building_identification,address_1,postal_code,primary_property_type,largest_property_use_type,year_built,occupancy,number_of_buildings,property_gfa_self_reported,site_eui_kbtu_ft,weather_normalized_site_eui,site_energy_use_kbtu,electricity_use_grid_purchase_1,electricity_use_generated_1,natural_gas_use_therms_,district_steam_use_kbtu,fuel_oil_2_use_kbtu,fuel_oil_4_use_kbtu,total_location_based_ghg,total_location_based_ghg_1,energy_star_score,data_center_gross_floor_area&$where=report_year='2024'&$limit=100000 |
| pluto_lots_10k.csv | https://data.cityofnewyork.us/resource/64uk-42ks.csv?$select=bbl,latitude,longitude,borough,zipcode,cd,council,numfloors,bldgarea,landuse,yearbuilt,ownertype,address&$where=bldgarea>=10000&$limit=200000 |
| nta2020.geojson | https://data.cityofnewyork.us/api/geospatial/9nt8-h7nd?method=export&format=GeoJSON |
| eia_plants_nyc.geojson | https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/Power_Plants_in_the_US/FeatureServer/0/query?where=State%3D%27New%20York%27%20AND%20County%20IN%20(%27New%20York%27%2C%27Kings%27%2C%27Queens%27%2C%27Bronx%27%2C%27Richmond%27)&outFields=*&f=geojson |
| substations_nyc.geojson | https://services5.arcgis.com/HDRa0B57OVrv2E1q/ArcGIS/rest/services/Electric_Substations/FeatureServer/0/query?where=STATE%3D%27NY%27%20AND%20COUNTY%20IN%20(%27NEW%20YORK%27%2C%27KINGS%27%2C%27QUEENS%27%2C%27BRONX%27%2C%27RICHMOND%27)&outFields=*&f=geojson&resultRecordCount=5000 |

Downloaded 2026-09-20. LL84 dataset rows last updated 2025-11-25.
