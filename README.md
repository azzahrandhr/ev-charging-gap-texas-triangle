# EV Charging Gap — Texas Triangle

**Two questions this project answers:**
1. Can an electric semi-truck run the Texas Triangle freight corridor (I-10 / I-35 / I-45) today?
2. How vulnerable is the corridor to disasters that could cause charging outages?

Read the full analysis: [nadhira.me/posts/202604_texas-triangle-ev-gap](https://nadhira.me/posts/202604_texas-triangle-ev-gap/)  
Explore the interactive dashboard: [azzahrandhr.github.io/ev-charging-gap-dashboard](https://azzahrandhr.github.io/ev-charging-gap-dashboard/)

---

## Key findings

| Metric | Value |
|---|---|
| DC Fast chargers in corridor | 629 |
| Charging deserts (gap > 50 mi) | **0** |
| Longest single gap | 47.5 mi (I-10) |
| Median distance to charger | 1.8 mi |

The Texas Triangle is fully covered — no point along I-10, I-35, or I-45 is more than 50 miles from a DC Fast charger. I-10 has the thinnest coverage (avg 10.9 mi gap); I-45 is the most saturated (avg 2.0 mi).

---

## Project structure

```
code/
  01_get_data.ipynb        # Download chargers (NREL AFDC), roads (Census), truck stops (OSM)
  02_analysis.ipynb        # Spatial gap analysis — sample points every 10 mi, nearest charger distance
  03_maps_and_export.ipynb # Static maps + export trimmed GeoJSON to output/shapefiles/
output/                    # Generated — gitignored
  shapefiles/              # GeoJSON exports consumed by preprocess.py
data/
  *.js                     # Compiled JS data files (output of preprocess.py)
index.html                 # Interactive Leaflet dashboard (single-file, no build step)
preprocess.py              # Converts output/shapefiles/*.geojson → data/*.js
```

---

## How to run

**1. Reproduce the analysis**

```bash
# Run notebooks in order inside code/
jupyter notebook code/01_get_data.ipynb
jupyter notebook code/02_analysis.ipynb
jupyter notebook code/03_maps_and_export.ipynb
```

Notebook 01 requires a free NREL AFDC API key — set it as `NREL_API_KEY` in the notebook.

**2. Rebuild dashboard data**

```bash
python preprocess.py
```

Reads from `output/shapefiles/`, writes compiled JS to `data/`.

**3. View the dashboard**

Open `index.html` in a browser — no server needed.

---

## Data sources

| Dataset | Source |
|---|---|
| DC Fast charger locations | [NREL Alternative Fuels Data Center](https://afdc.energy.gov/) |
| Highway geometries | US Census TIGER/Line (via `pygris`) |
| Truck stops | OpenStreetMap Overpass API |
| Texas boundary | TIGER/Line |

---

## Dependencies

```
geopandas
pygris
contextily
matplotlib
shapely
requests
pandas
numpy
```
