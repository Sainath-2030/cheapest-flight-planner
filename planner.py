# planner.py
import random, math
from collections import defaultdict, deque
from math import radians, sin, cos, atan2, sqrt
import folium

# -----------------------
# 20 airports (id 0..19)
# -----------------------
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

# -----------------------
# haversine distance (km)
# -----------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

COST_PER_KM = 6.0

def fare_and_distance(u, v):
    a = ID_TO_AIRPORT[u]; b = ID_TO_AIRPORT[v]
    dist = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    base = dist * COST_PER_KM
    fare = round(base + base * random.uniform(-0.12, 0.12))
    return int(fare), round(dist, 1)

# -----------------------
# demo negative settings
# -----------------------
NEGATIVE_EDGE_DEMOS = {(0, 3)}  # Mumbai->Chennai
NEGATIVE_CYCLE_NODES = [0, 6, 11]  # Mumbai, Pune, Nagpur

# -----------------------
# generate <=10 edges, prefer direct
# -----------------------
def generate_graph_limited(src_id, dst_id, allow_negative_cycle_demo=False):
    total_target = random.randint(6, 10)
    edges = []

    def add(u,v,f,d):
        if u == v: return
        if not any(e for e in edges if e[0]==u and e[1]==v):
            edges.append((u,v,int(f),float(d)))

    fare_direct, dist_direct = fare_and_distance(src_id, dst_id)
    if dist_direct <= 600 or random.random() < 0.6:
        add(src_id, dst_id, fare_direct, dist_direct)

    candidates = [a["id"] for a in AIRPORTS if a["id"] not in (src_id, dst_id)]
    tries = 0
    while len(edges) < total_target and tries < 300:
        tries += 1
        u = random.choice([src_id, dst_id] + candidates)
        v = random.choice([x for x in candidates + [src_id, dst_id] if x != u])
        f,d = fare_and_distance(u,v)
        add(u,v,f,d)

    if (src_id, dst_id) in NEGATIVE_EDGE_DEMOS:
        add(src_id, dst_id, -180, dist_direct)

    if allow_negative_cycle_demo:
        a,b,c = NEGATIVE_CYCLE_NODES
        f1,d1 = fare_and_distance(a,b)
        f2,d2 = fare_and_distance(b,c)
        f3,d3 = fare_and_distance(c,a)
        add(a,b,-120,d1)
        add(b,c,-130,d2)
        add(c,a,-40,d3)

    def reachable(es):
        adj = defaultdict(list)
        for u,v,_,_ in es:
            adj[u].append(v)
        q = deque([src_id]); seen={src_id}
        while q:
            x = q.popleft()
            if x == dst_id:
                return True
            for y in adj.get(x,[]):
                if y not in seen:
                    seen.add(y); q.append(y)
        return False

    if not reachable(edges):
        mids = [m for m in candidates]
        if mids:
            mid = random.choice(mids)
            f1,d1 = fare_and_distance(src_id, mid)
            f2,d2 = fare_and_distance(mid, dst_id)
            add(src_id, mid, f1, d1)
            add(mid, dst_id, f2, d2)

    if len(edges) > total_target:
        direct = [e for e in edges if e[0]==src_id and e[1]==dst_id]
        others = [e for e in edges if not (e[0]==src_id and e[1]==dst_id)]
        random.shuffle(others)
        edges = direct + others[:max(0, total_target - len(direct))]

    return edges

# -----------------------
# Bellman-Ford
# -----------------------
INF = 10**15
def bellman_ford(nodes_ids, edges, src_id):
    dist = {n: INF for n in nodes_ids}
    parent = {n: None for n in nodes_ids}
    dist[src_id] = 0
    for _ in range(len(nodes_ids)-1):
        changed = False
        for u,v,w,_ in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                parent[v] = u
                changed = True
        if not changed:
            break
    affected = set()
    for u,v,w,_ in edges:
        if dist[u] != INF and dist[u] + w < dist[v]:
            affected.add(v)
    negcycle = len(affected) > 0
    return dist, parent, negcycle

# -----------------------
# enum simple paths up to limit
# -----------------------
def enum_simple_paths(nodes_ids, edges, src_id, dst_id, limit=10):
    adj = defaultdict(list)
    for u,v,w,d in edges:
        adj[u].append((v,w,d))
    all_paths = []
    visited = set()
    path = []

    def dfs(u):
        if len(all_paths) >= limit:
            return
        if u == dst_id:
            total_fare = 0; total_dist = 0.0
            for i in range(len(path)-1):
                a = path[i]; b = path[i+1]
                for vv,ww,dd in adj[a]:
                    if vv == b:
                        total_fare += ww; total_dist += dd; break
            all_paths.append((path.copy(), int(total_fare), round(total_dist,1)))
            return
        for v,w,d in adj[u]:
            if v not in visited:
                visited.add(v); path.append(v)
                dfs(v)
                path.pop(); visited.remove(v)

    visited.add(src_id); path.append(src_id)
    dfs(src_id)
    return all_paths

# -----------------------
# Build result HTML (folium map + table)
# -----------------------
def build_result_map_html(edges, paths, cheapest_path_ids=None, negcycle=False):
    m = folium.Map(location=[21.0,78.0], zoom_start=5, control_scale=True)

    for a in AIRPORTS:
        folium.Marker(location=[a["lat"], a["lon"]],
                      popup=f"{a['id']}: {a['name']}",
                      tooltip=a["name"]).add_to(m)

    for u,v,fare,dist in edges:
        a = ID_TO_AIRPORT[u]; b = ID_TO_AIRPORT[v]
        color = "purple" if fare < 0 else "#666666"
        folium.PolyLine(locations=[(a["lat"], a["lon"]), (b["lat"], b["lon"])],
                        color=color, weight=2, opacity=0.6,
                        tooltip=f"{a['name']}→{b['name']} : ₹{fare} ({dist} km)").add_to(m)

    if cheapest_path_ids:
        for i in range(len(cheapest_path_ids)-1):
            u = cheapest_path_ids[i]; v = cheapest_path_ids[i+1]
            a = ID_TO_AIRPORT[u]; b = ID_TO_AIRPORT[v]
            folium.PolyLine(locations=[(a["lat"], a["lon"]), (b["lat"], b["lon"])],
                            color="red", weight=5, opacity=0.9).add_to(m)

    rows_html = ""
    if paths:
        for idx, (p, fare, dist) in enumerate(paths, start=1):
            highlight = "background:#fff7e6;" if (idx == 1) else ""
            names = " → ".join(ID_TO_AIRPORT[i]["name"] for i in p)
            rows_html += f"<tr style='{highlight}'><td>{idx}</td><td>{names}</td><td>₹{fare}</td><td>{dist} km</td></tr>"
    else:
        rows_html = "<tr><td colspan='4'>No paths found</td></tr>"

    table_html = f"""
    <div style="font-family:Arial, Helvetica, sans-serif; padding:12px; max-width:1100px; margin:12px auto;">
      <h2 style="margin-top:8px">Available routes (top {len(paths)})</h2>
      <table style="width:100%; border-collapse: collapse; border:1px solid #ddd;">
        <thead style="background:#f6f8fb;">
          <tr><th style="padding:8px;border:1px solid #e8eef7">#</th><th style="padding:8px;border:1px solid #e8eef7">Path</th><th style="padding:8px;border:1px solid #e8eef7">Fare</th><th style="padding:8px;border:1px solid #e8eef7">Distance</th></tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
      <p style="margin-top:8px;color:#555;">Cheapest highlighted in table and on map (red). Purple edges indicate negative fares/discounts.</p>
    </div>
    """

    neg_banner = ""
    if negcycle:
        neg_banner = "<div style='padding:10px;background:#fff1f0;border:1px solid #ffd4d6;color:#9b1c1c;text-align:center;'>⚠️ Negative-weight cycle detected — no finite cheapest path exists.</div>"

    full = m.get_root().render()
    full = full.replace("</body>", f"{neg_banner}{table_html}</body>")
    return full
