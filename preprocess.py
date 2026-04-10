"""
preprocess.py — One-time script to convert GeoJSON → JS data files for the dashboard.
Run from the ev-charging-gap-dashboard directory:
    python3 preprocess.py
"""

import json
import math
from pathlib import Path

SRC = Path("output/shapefiles")
OUT = Path("data")
OUT.mkdir(exist_ok=True)


def round_coord(v, dp=4):
    return round(v, dp)


def rdp(points, epsilon=0.002):
    """Ramer-Douglas-Peucker line simplification."""
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dlen = math.sqrt(dx*dx + dy*dy)
    max_dist, max_idx = 0, 0
    for i in range(1, len(points) - 1):
        if dlen == 0:
            d = math.sqrt((points[i][0]-start[0])**2 + (points[i][1]-start[1])**2)
        else:
            d = abs(dy*points[i][0] - dx*points[i][1] + end[0]*start[1] - end[1]*start[0]) / dlen
        if d > max_dist:
            max_dist, max_idx = d, i
    if max_dist > epsilon:
        left = rdp(points[:max_idx+1], epsilon)
        right = rdp(points[max_idx:], epsilon)
        return left[:-1] + right
    return [start, end]


def normalize_hwy(name):
    s = str(name)
    if "10" in s:
        return "I-10"
    if "35" in s:
        return "I-35"
    if "45" in s:
        return "I-45"
    return "Other"


# ── 1. gap_analysis.js ────────────────────────────────────────────────────────
print("Processing gap_analysis.geojson...")
with open(SRC / "gap_analysis.geojson") as f:
    gj = json.load(f)

gap_points = []
for feat in gj["features"]:
    lon, lat = feat["geometry"]["coordinates"]
    p = feat["properties"]
    gap_points.append({
        "lat": round_coord(lat),
        "lon": round_coord(lon),
        "highway": p.get("highway", ""),
        "dist_along_mi": round(p.get("dist_along_mi", 0), 1),
        "dist_mi": round(p.get("dist_mi", 0), 1),
        "is_desert": int(p.get("is_desert", 0)),
    })

with open(OUT / "gap_analysis.js", "w") as f:
    f.write("const GAP_POINTS = ")
    json.dump(gap_points, f, separators=(",", ":"))
    f.write(";\n")
print(f"  → {len(gap_points)} points, {(OUT/'gap_analysis.js').stat().st_size//1024}KB")


# ── 2. chargers.js ────────────────────────────────────────────────────────────
print("Processing chargers_in_corridor.geojson...")
with open(SRC / "chargers_in_corridor.geojson") as f:
    gj = json.load(f)

chargers = []
for feat in gj["features"]:
    lon, lat = feat["geometry"]["coordinates"]
    p = feat["properties"]
    chargers.append({
        "lat": round_coord(lat),
        "lon": round_coord(lon),
        "name": p.get("Station Name", ""),
        "city": p.get("City", ""),
        "dcFast": int(p.get("EV DC Fast Count") or 0),
        "network": p.get("EV Network", ""),
    })

with open(OUT / "chargers.js", "w") as f:
    f.write("const CHARGERS = ")
    json.dump(chargers, f, separators=(",", ":"))
    f.write(";\n")
print(f"  → {len(chargers)} chargers, {(OUT/'chargers.js').stat().st_size//1024}KB")


# ── 3. truck_stops.js ─────────────────────────────────────────────────────────
print("Processing truck_stops_corridor.geojson...")
with open(SRC / "truck_stops_corridor.geojson") as f:
    gj = json.load(f)

truck_stops = []
for feat in gj["features"]:
    lon, lat = feat["geometry"]["coordinates"]
    p = feat["properties"]
    name = p.get("name") or p.get("brand") or p.get("operator") or "Truck Stop"
    brand = p.get("brand") or p.get("operator") or ""
    truck_stops.append({
        "lat": round_coord(lat),
        "lon": round_coord(lon),
        "name": name,
        "brand": brand,
    })

with open(OUT / "truck_stops.js", "w") as f:
    f.write("const TRUCK_STOPS = ")
    json.dump(truck_stops, f, separators=(",", ":"))
    f.write(";\n")
print(f"  → {len(truck_stops)} truck stops, {(OUT/'truck_stops.js').stat().st_size//1024}KB")


# ── 4. corridor.js ────────────────────────────────────────────────────────────
print("Processing corridor_buffer.geojson...")
with open(SRC / "corridor_buffer.geojson") as f:
    gj = json.load(f)

def simplify_ring(ring, epsilon=0.005):
    """Apply RDP to a polygon ring (list of [lon, lat] coords)."""
    simplified = rdp(ring, epsilon=epsilon)
    # Ensure ring is closed
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return [[round(c[0], 3), round(c[1], 3)] for c in simplified]

def simplify_polygon_geom(geom, epsilon=0.005):
    """Simplify all rings in a Polygon or MultiPolygon geometry."""
    if geom["type"] == "Polygon":
        geom["coordinates"] = [simplify_ring(ring, epsilon) for ring in geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        geom["coordinates"] = [
            [simplify_ring(ring, epsilon) for ring in polygon]
            for polygon in geom["coordinates"]
        ]
    return geom

corridor_geom = gj["features"][0]["geometry"]
corridor_geom = simplify_polygon_geom(corridor_geom, epsilon=0.005)

def round_geom_coords(obj, dp=3):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(obj[0], dp), round(obj[1], dp)]
        return [round_geom_coords(item, dp) for item in obj]
    return obj

with open(OUT / "corridor.js", "w") as f:
    f.write("const CORRIDOR = ")
    json.dump(corridor_geom, f, separators=(",", ":"))
    f.write(";\n")
print(f"  → corridor simplified, {(OUT/'corridor.js').stat().st_size//1024}KB")


# ── 5. highways.js ────────────────────────────────────────────────────────────
print("Processing triangle_hwys.geojson...")
with open(SRC / "triangle_hwys.geojson") as f:
    gj = json.load(f)

hwy_features = []
for feat in gj["features"]:
    label = normalize_hwy(feat["properties"].get("FULLNAME", ""))
    if label == "Other":
        continue
    geom = feat["geometry"]
    coords = geom["coordinates"]
    # Simplify coordinates
    simplified = rdp(coords, epsilon=0.002)
    rounded = [[round(c[0], 3), round(c[1], 3)] for c in simplified]
    hwy_features.append({
        "type": "Feature",
        "properties": {"highway": label},
        "geometry": {"type": "LineString", "coordinates": rounded}
    })
print(f"  → {len(hwy_features)} highway features (RDP simplified)")

highways_fc = {"type": "FeatureCollection", "features": hwy_features}
with open(OUT / "highways.js", "w") as f:
    f.write("const HIGHWAYS = ")
    json.dump(highways_fc, f, separators=(",", ":"))
    f.write(";\n")
print(f"  → {(OUT/'highways.js').stat().st_size//1024}KB")


# ── 6. meta.js ────────────────────────────────────────────────────────────────
print("Computing META stats...")

# Re-read gap points for stats
all_pts = gap_points
total = len(all_pts)
deserts = [p for p in all_pts if p["is_desert"] == 1]
desert_count = len(deserts)
desert_pct = round(desert_count / total * 100, 1)

all_dists = [p["dist_mi"] for p in all_pts]
avg_dist = round(sum(all_dists) / len(all_dists), 1)
sorted_dists = sorted(all_dists)
median_dist = round(sorted_dists[len(sorted_dists) // 2], 1)
longest_gap = round(max(all_dists), 1)
longest_gap_hwy = max(all_pts, key=lambda p: p["dist_mi"])["highway"]

# Per-highway stats
by_highway = {}
for hw in ["I-10", "I-35", "I-45"]:
    pts = [p for p in all_pts if p["highway"] == hw]
    dists = [p["dist_mi"] for p in pts]
    d_pts = [p for p in pts if p["is_desert"] == 1]
    s_dists = sorted(dists)
    by_highway[hw] = {
        "points": len(pts),
        "deserts": len(d_pts),
        "maxGap": round(max(dists), 1) if dists else 0,
        "avgDist": round(sum(dists) / len(dists), 1) if dists else 0,
        "medianDist": round(s_dists[len(s_dists) // 2], 1) if s_dists else 0,
    }

# Histogram bins
bins = [
    {"label": "0–5", "min": 0, "max": 5},
    {"label": "5–10", "min": 5, "max": 10},
    {"label": "10–15", "min": 10, "max": 15},
    {"label": "15–25", "min": 15, "max": 25},
    {"label": "25–50", "min": 25, "max": 50},
    {"label": "50–100", "min": 50, "max": 100},
    {"label": "100+", "min": 100, "max": 9999},
]
for b in bins:
    for hw in ["I-10", "I-35", "I-45"]:
        b[hw] = len([p for p in all_pts if p["highway"] == hw and b["min"] <= p["dist_mi"] < b["max"]])
    b["total"] = sum(b[hw] for hw in ["I-10", "I-35", "I-45"])

# Network counts (top 6 + Other)
networks = {}
with open(SRC / "chargers_in_corridor.geojson") as f:
    gj_c = json.load(f)
for feat in gj_c["features"]:
    net = feat["properties"].get("EV Network") or "Unknown"
    networks[net] = networks.get(net, 0) + 1

top6_keys = ["Tesla", "ChargePoint Network", "eVgo Network", "Electrify America", "SHELL_RECHARGE", "Blink Network"]
network_counts = {}
other = 0
for k, v in networks.items():
    if k in top6_keys:
        network_counts[k] = v
    else:
        other += v
network_counts["Other"] = other

meta = {
    "totalChargers": len(chargers),
    "totalDeserts": desert_count,
    "desertPct": desert_pct,
    "longestGap": longest_gap,
    "longestGapHwy": longest_gap_hwy,
    "avgDist": avg_dist,
    "medianDist": median_dist,
    "totalTruckStops": len(truck_stops),
    "byHighway": by_highway,
    "histBins": bins,
    "networkCounts": network_counts,
}

with open(OUT / "meta.js", "w") as f:
    f.write("const META = ")
    json.dump(meta, f, indent=2)
    f.write(";\n")
print(f"  → meta.js written")

# ── 7. penske.js ─────────────────────────────────────────────────────────────
penske_src = Path("output/shapefiles/penske_texas_facilities_classified.geojson")
if penske_src.exists():
    print("Processing penske_texas_facilities_classified.geojson...")
    with open(penske_src) as f:
        gj = json.load(f)

    penske_facilities = []
    for feat in gj["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        p = feat["properties"]
        penske_facilities.append({
            "lat": round_coord(lat),
            "lon": round_coord(lon),
            "name": p.get("name", ""),
            "city": p.get("city", ""),
            "address": p.get("address", ""),
            "facilityType": p.get("facility_type", ""),
            "riskTier": p.get("risk_tier", ""),
            "nearestHighway": p.get("nearest_highway", ""),
            "distChargerMi": round(p.get("dist_to_nearest_charger_mi", 0), 1),
            "nearestGapMi": round(p.get("nearest_gap_mi", 0), 1),
        })

    with open(OUT / "penske.js", "w") as f:
        f.write("const PENSKE = ")
        json.dump(penske_facilities, f, separators=(",", ":"))
        f.write(";\n")
    print(f"  → {len(penske_facilities)} facilities, {(OUT/'penske.js').stat().st_size//1024}KB")
else:
    print("SKIP: penske_texas_facilities_classified.geojson not found (run classify_penske.py first)")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n✓ All data files written to data/")
all_files = ["gap_analysis.js","chargers.js","truck_stops.js","corridor.js","highways.js","meta.js"]
if (OUT / "penske.js").exists():
    all_files.append("penske.js")
total_kb = sum((OUT / fn).stat().st_size for fn in all_files) // 1024
print(f"  Total payload: ~{total_kb}KB")
print(f"\nKey stats:")
print(f"  DC Fast chargers in corridor: {len(chargers)}")
print(f"  Charging deserts: {desert_count} ({desert_pct}%)")
print(f"  Longest gap: {longest_gap} mi on {longest_gap_hwy}")
print(f"  Avg/median dist: {avg_dist} / {median_dist} mi")
