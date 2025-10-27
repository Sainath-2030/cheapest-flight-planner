# planner.py
import random, math
from collections import deque
from pathlib import Path
import json

# ---------------------------
# AIRPORTS — 20 sample Indian airports
# Each entry: id (int), name, lat, lon
# ---------------------------
AIRPORTS = [
    {"id": 0, "name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"id": 1, "name": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"id": 2, "name": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    {"id": 3, "name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"id": 4, "name": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"id": 5, "name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"id": 6, "name": "Pune", "lat": 18.5204, "lon": 73.8567},
    {"id": 7, "name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"id": 8, "name": "Surat", "lat": 21.1702, "lon": 72.8311},
    {"id": 9, "name": "Jaipur", "lat": 26.9124, "lon": 75.7873},
    {"id": 10, "name": "Lucknow", "lat": 26.8467, "lon": 80.9462},
    {"id": 11, "name": "Nagpur", "lat": 21.1458, "lon": 79.0882},
    {"id": 12, "name": "Indore", "lat": 22.7196, "lon": 75.8577},
    {"id": 13, "name": "Bhopal", "lat": 23.2599, "lon": 77.4126},
    {"id": 14, "name": "Patna", "lat": 25.5941, "lon": 85.1376},
    {"id": 15, "name": "Vadodara", "lat": 22.3072, "lon": 73.1812},
    {"id": 16, "name": "Guwahati", "lat": 26.1445, "lon": 91.7362},
    {"id": 17, "name": "Srinagar", "lat": 34.0837, "lon": 74.7973},
    {"id": 18, "name": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366},
    {"id": 19, "name": "Coimbatore", "lat": 11.0168, "lon": 76.9558},
]

ID_TO_AIRPORT = {a["id"]: a for a in AIRPORTS}
NAMES = [a["name"] for a in AIRPORTS]

# ---------------------------
# Haversine distance
# ---------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

COST_PER_KM = 6.0

def fare_by_distance(a_id, b_id):
    a = ID_TO_AIRPORT[a_id]; b = ID_TO_AIRPORT[b_id]
    d = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    base = d * COST_PER_KM
    # small randomness and occasional discount (negative edge)
    fluct = base * random.uniform(-0.12, 0.12)
    fare = round(base + fluct)
    # chance for discount edge (negative weight)
    if random.random() < 0.08:
        disc = -round(min(abs(base)*0.4, random.uniform(20, 150)))
        fare = disc
    # ensure integer fare
    if fare == 0:
        fare = 50
    return fare, round(d, 1)


# ---------------------------
# Generate random directed edges, ensure connectivity from src to dst
# Edge format: (u_name, v_name, fare, distance_km)
# ---------------------------
def generate_edges_ensure_connectivity(src_id, dst_id, min_out=3, max_out=5):
    edges = []
    for a in AIRPORTS:
        possible = [x["id"] for x in AIRPORTS if x["id"] != a["id"]]
        out_count = random.randint(min_out, min(max_out, len(possible)))
        picks = random.sample(possible, k=out_count)
        for pid in picks:
            fare, dist = fare_by_distance(a["id"], pid)
            edges.append((a["name"], ID_TO_AIRPORT[pid]["name"], fare, dist))

    # Check reachability via BFS; if unreachable, add a guaranteed path
    def is_reachable(edges_list):
        adj = {n: [] for n in NAMES}
        for u,v,_,_ in edges_list:
            adj[u].append(v)
        src_name = ID_TO_AIRPORT[src_id]["name"]
        dst_name = ID_TO_AIRPORT[dst_id]["name"]
        q = deque([src_name]); seen = {src_name}
        while q:
            u = q.popleft()
            if u == dst_name:
                return True
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); q.append(v)
        return False

    if not is_reachable(edges):
        # build 1-3 intermediate path
        intermediates = [n for n in NAMES if n not in (ID_TO_AIRPORT[src_id]["name"], ID_TO_AIRPORT[dst_id]["name"])]
        k = random.randint(1, min(3, max(1, len(intermediates))))
        mids = random.sample(intermediates, k)
        path = [ID_TO_AIRPORT[src_id]["name"]] + mids + [ID_TO_AIRPORT[dst_id]["name"]]
        for i in range(len(path)-1):
            u = path[i]; v = path[i+1]
            u_id = next(a["id"] for a in AIRPORTS if a["name"] == u)
            v_id = next(a["id"] for a in AIRPORTS if a["name"] == v)
            fare, dist = fare_by_distance(u_id, v_id)
            edges.append((u, v, fare, dist))

    # remove duplicates
    seen = set(); unique=[]
    for u,v,f,d in edges:
        if (u,v) not in seen:
            seen.add((u,v)); unique.append((u,v,f,d))
    return unique


# ---------------------------
# Bellman-Ford: nodes (list of names), edges list (u,v,w,d)
# returns (dist dict, parent dict, negcycle flag)
# ---------------------------
def bellman_ford(nodes, edges, source_name):
    INF = float('inf')
    dist = {n: INF for n in nodes}
    parent = {n: None for n in nodes}
    dist[source_name] = 0
    for _ in range(len(nodes)-1):
        updated = False
        for u,v,w,_ in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                parent[v] = u
                updated = True
        if not updated:
            break

    # detect negative cycle (reachable)
    neg = False
    for u,v,w,_ in edges:
        if dist[u] != INF and dist[u] + w < dist[v]:
            neg = True
            break
    return (None, None, True) if neg else (dist, parent, False)


# ---------------------------
# Enumerate simple paths (DFS) limited by limit
# returns list of (path_list_of_names, cost)
# ---------------------------
def enum_simple_paths(nodes, edges, src_name, dst_name, limit=2000):
    adj = {n: [] for n in nodes}
    for u,v,w,d in edges:
        adj[u].append((v,w,d))
    all_paths=[]
    visited=set()
    path=[]
    def dfs(u):
        if len(all_paths) >= limit:
            return
        if u == dst_name:
            # compute cost for current path
            cost = 0
            for i in range(len(path)-1):
                cur = path[i]; nxt = path[i+1]
                for vv,ww,_ in adj[cur]:
                    if vv == nxt:
                        cost += ww
                        break
            all_paths.append((path.copy(), cost))
            return
        for v,_,_ in adj[u]:
            if v not in visited:
                visited.add(v); path.append(v)
                dfs(v)
                path.pop(); visited.remove(v)
    visited.add(src_name); path.append(src_name)
    dfs(src_name)
    return all_paths


# ---------------------------
# Build result HTML (Leaflet) showing all edges and highlighting cheapest path
# edges: list of (u,v,fare,dist)
# cheapest_path: list of names
# all_paths: list of (path, cost)
# negcycle: boolean
# ---------------------------
def build_result_map_html(edges, cheapest_path, all_paths, negcycle=False, cheapest_cost=None):
    center_lat = sum(a["lat"] for a in AIRPORTS) / len(AIRPORTS)
    center_lon = sum(a["lon"] for a in AIRPORTS) / len(AIRPORTS)

    # markers and polylines JS arrays
    marker_js = []
    for a in AIRPORTS:
        popup = f"{a['name']}"
        marker_js.append(f"L.marker([{a['lat']},{a['lon']}]).addTo(map).bindPopup({json.dumps(popup)});")

    poly_js = []
    for u,v,f,d in edges:
        ua = next(x for x in AIRPORTS if x["name"]==u)
        va = next(x for x in AIRPORTS if x["name"]==v)
        color = "gray" if f >= 0 else "purple"
        popup = f"{u} → {v} : ₹{f} ({d} km)"
        poly_js.append(f"L.polyline([[{ua['lat']},{ua['lon']}],[{va['lat']},{va['lon']}]], {{color:'{color}', weight:2}}).addTo(map).bindPopup({json.dumps(popup)});")

    highlight_js = []
    for i in range(len(cheapest_path)-1):
        u = cheapest_path[i]; v = cheapest_path[i+1]
        ua = next(x for x in AIRPORTS if x["name"]==u)
        va = next(x for x in AIRPORTS if x["name"]==v)
        highlight_js.append(f"L.polyline([[{ua['lat']},{ua['lon']}],[{va['lat']},{va['lon']}]], {{color:'red', weight:5, opacity:0.9}}).addTo(map);")

    # build paths table HTML
    rows_html = ""
    if all_paths:
        # sort by cost
        sorted_paths = sorted(all_paths, key=lambda x: x[1])
        for i, (p, c) in enumerate(sorted_paths, 1):
            cls = "cheapest" if (cheapest_cost is not None and abs(c - cheapest_cost) < 1e-6) else ""
            rows_html += f"<tr class='{cls}'><td>{i}</td><td>{' → '.join(p)}</td><td>₹{c}</td></tr>"
    else:
        rows_html = "<tr><td colspan='3'>No simple paths enumerated (graph too large)</td></tr>"

    neg_banner = ""
    if negcycle:
        neg_banner = "<div style='position:fixed;left:50%;transform:translateX(-50%);top:10px;padding:8px 12px;background:#ffefef;border:1px solid #ff8a8a;z-index:9999;'>⚠️ Negative cycle detected — no finite cheapest path.</div>"

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Flight Planner - Results</title>
<link rel="stylesheet" href="/static/css/styles.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<style>
  body{{font-family:Arial,Helvetica,sans-serif;margin:0}}
  #mapid{{height:60vh}}
  .panel{{padding:12px}}
  table{{width:100%;border-collapse:collapse;margin-top:8px}}
  th,td{{padding:8px;border:1px solid #ddd;text-align:left}}
  th{{background:#f4f4f4}}
  tr.cheapest{{background:#fff8e1}}
</style>
</head><body>
{neg_banner}
<header style="background:linear-gradient(90deg,#0b79d0,#4ab3f4);color:white;padding:12px 16px;">
  <h2 style="margin:0">Flight Planner — Results</h2>
</header>

<div id="mapid"></div>
<div class="panel">
  <h3>Cheapest path: {(' → '.join(cheapest_path) if cheapest_path else 'N/A')}</h3>
  <p>Total cost: {('₹' + str(cheapest_cost) if cheapest_cost is not None else 'N/A')}</p>

  <h3>All simple paths (limited)</h3>
  <table>
    <thead><tr><th>#</th><th>Path</th><th>Cost</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <p style="margin-top:12px"><a href="/">⟵ Back to selection</a></p>
</div>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
  var map = L.map('mapid').setView([{center_lat}, {center_lon}], 5);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19, attribution: '© OpenStreetMap' }}).addTo(map);

  {''.join(marker_js)}
  {''.join(poly_js)}
  {''.join(highlight_js)}
</script>
</body>
</html>
"""
    return html
