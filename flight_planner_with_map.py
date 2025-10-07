

"""
Flight Planner with Map Visualization (console + map file)

- Writes 'airports_map.html' (Leaflet map) with 20 airport markers (id shown)
- Opens the map in default browser for visual selection
- Console asks only for source and destination (no list printed)
- Computes all simple paths when feasible and prints cheapest path

Author: ChatGPT (adapted for Sainath)
"""

import webbrowser
import math
import heapq
from collections import deque, defaultdict
from pathlib import Path
import json
import time
import os
import sys

# -------------------------------
# Predefined airports with lat/lon
# 20 example cities in India (approximate coords)
# id will be integer index from 0..19
AIRPORTS = [
    {"id": 0, "name": "Mumbai", "lat": 19.0896, "lon": 72.8656},
    {"id": 1, "name": "Delhi", "lat": 28.5562, "lon": 77.1000},
    {"id": 2, "name": "Bengaluru", "lat": 12.9530, "lon": 77.6683},
    {"id": 3, "name": "Chennai", "lat": 12.9941, "lon": 80.1709},
    {"id": 4, "name": "Kolkata", "lat": 22.6540, "lon": 88.4467},
    {"id": 5, "name": "Hyderabad", "lat": 17.2403, "lon": 78.4294},
    {"id": 6, "name": "Pune", "lat": 18.5793, "lon": 73.9143},
    {"id": 7, "name": "Ahmedabad", "lat": 23.0772, "lon": 72.6347},
    {"id": 8, "name": "Surat", "lat": 21.1161, "lon": 72.7411},
    {"id": 9, "name": "Jaipur", "lat": 26.8248, "lon": 75.8058},
    {"id": 10, "name": "Lucknow", "lat": 26.7606, "lon": 80.8893},
    {"id": 11, "name": "Nagpur", "lat": 21.0890, "lon": 79.0488},
    {"id": 12, "name": "Indore", "lat": 22.7236, "lon": 75.8256},
    {"id": 13, "name": "Bhopal", "lat": 23.2870, "lon": 77.3375},
    {"id": 14, "name": "Patna", "lat": 25.6100, "lon": 85.1414},
    {"id": 15, "name": "Vadodara", "lat": 22.3072, "lon": 73.1812},
    {"id": 16, "name": "Guwahati", "lat": 26.1063, "lon": 91.5850},
    {"id": 17, "name": "Srinagar", "lat": 33.9871, "lon": 74.7748},
    {"id": 18, "name": "Thiruvananthapuram", "lat": 8.4824, "lon": 76.9204},
    {"id": 19, "name": "Coimbatore", "lat": 11.0296, "lon": 77.0434},
]

# -------------------------------
# Predefined directed edges (u_name, v_name, fare)
# Edit fares as required. Negative fares represent discounts/promotions.
# Use names from AIRPORTS list above.
EDGES = [
    ("Mumbai", "Pune", 120),
    ("Mumbai", "Bengaluru", 2500),
    ("Mumbai", "Ahmedabad", 2000),
    ("Pune", "Mumbai", 110),
    ("Pune", "Hyderabad", 700),
    ("Pune", "Mumbai", 100),
    ("Pune", "Bengaluru", 900),
    ("Bengaluru", "Chennai", 1000),
    ("Bengaluru", "Coimbatore", 600),
    ("Chennai", "Thiruvananthapuram", 1500),
    ("Hyderabad", "Nagpur", 800),
    ("Nagpur", "Mumbai", 900),
    ("Ahmedabad", "Surat", 400),
    ("Surat", "Vadodara", 300),
    ("Vadodara", "Ahmedabad", 280),
    ("Jaipur", "Delhi", 600),
    ("Delhi", "Lucknow", 1200),
    ("Lucknow", "Patna", 1000),
    ("Patna", "Guwahati", 1800),
    ("Guwahati", "Kolkata", 1600),
    ("Kolkata", "Patna", 1400),
    ("Indore", "Bhopal", 400),
    ("Bhopal", "Indore", 380),
    ("Bhopal", "Nagpur", 700),
    ("Nagpur", "Pune", -150),   # discount edge - shows negative fare
    ("Pune", "Mumbai", -50),    # another negative discount (parallel edge)
    ("Coimbatore", "Thiruvananthapuram", 900),
    ("Thiruvananthapuram", "Coimbatore", 850),
]

# -------------------------------
# Utilities to build graph indices
def build_index_maps(airports, edges):
    name2idx = {}
    idx2name = {}
    for a in airports:
        name2idx[a["name"]] = a["id"]
        idx2name[a["id"]] = a["name"]
    # edges may contain names not in airports; add them if necessary
    next_idx = max(idx2name.keys()) + 1
    for u, v, _ in edges:
        if u not in name2idx:
            name2idx[u] = next_idx
            idx2name[next_idx] = u
            next_idx += 1
        if v not in name2idx:
            name2idx[v] = next_idx
            idx2name[next_idx] = v
            next_idx += 1
    edges_idx = [(name2idx[u], name2idx[v], w) for (u, v, w) in edges]
    nodes = [idx2name[i] for i in range(len(idx2name))]
    return nodes, edges_idx, name2idx, idx2name

# -------------------------------
# Write an HTML file using Leaflet with markers for each airport
def write_map_html(filename: str, airports):
    center_lat = sum(a["lat"] for a in airports) / len(airports)
    center_lon = sum(a["lon"] for a in airports) / len(airports)
    markers_js = []
    for a in airports:
        # marker popup shows "id: name"
        popup = f"{a['id']}: {a['name']}"
        markers_js.append(
            f"L.marker([{a['lat']}, {a['lon']}]).addTo(map).bindPopup('{popup}');"
        )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Airports Map</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
  <style>
    #mapid {{ height: 90vh; width: 100%; }}
    body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
    .topbar {{ padding: 8px; background: #f8f9fa; border-bottom: 1px solid #ddd; }}
  </style>
</head>
<body>
  <div class="topbar">
    <strong>Airports Map</strong> — Click a marker to see its <em>id: name</em>.
    <span style="margin-left:20px">Use the <code>id</code> or exact name in the console to choose source/destination.</span>
  </div>
  <div id="mapid"></div>

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <script>
    var map = L.map('mapid').setView([{center_lat}, {center_lon}], 5);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18,
        attribution: '© OpenStreetMap contributors'
    }}).addTo(map);

    {"".join(markers_js)}

    // Add small legend showing number of airports
    var info = L.control({{position: 'topright'}});
    info.onAdd = function (map) {{
        var div = L.DomUtil.create('div', 'info');
        div.innerHTML = '<b>{len(airports)} airports</b><br>IDs shown in popups';
        div.style.background = 'white';
        div.style.padding = '6px';
        div.style.border = '1px solid #ccc';
        return div;
    }};
    info.addTo(map);
  </script>
</body>
</html>
"""
    Path(filename).write_text(html, encoding="utf-8")
    print(f"Map written to {filename}")


# -------------------------------
# Graph algorithms (same as earlier, well-indented)
INF = 10**18


def adjacency_list(n, edges_idx):
    adj = [[] for _ in range(n)]
    for u, v, w in edges_idx:
        adj[u].append((v, w))
    return adj


def bellman_ford(n, edges_idx, src):
    dist = [INF] * n
    parent = [-1] * n
    dist[src] = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges_idx:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                parent[v] = u
                changed = True
        if not changed:
            break

    # detect negative-cycle reachable from src
    affected = set()
    for u, v, w in edges_idx:
        if dist[u] != INF and dist[u] + w < dist[v]:
            affected.add(v)

    if not affected:
        return dist, parent, None

    # reconstruct a cycle (best-effort)
    start = next(iter(affected))
    y = start
    for _ in range(n):
        if parent[y] == -1:
            break
        y = parent[y]
    cycle = []
    visited = set()
    cur = y
    while True:
        if cur in visited:
            try:
                idx = cycle.index(cur)
                cycle = cycle[idx:]
            except ValueError:
                pass
            break
        visited.add(cur)
        cycle.append(cur)
        cur = parent[cur]
        if cur == -1 or len(cycle) > n + 5:
            break
    return dist, parent, {"affected": affected, "cycle": cycle}


def dijkstra(n, adj, src):
    dist = [math.inf] * n
    parent = [-1] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            if w < 0:
                raise ValueError("Dijkstra cannot run with negative edge weights.")
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, parent


def reconstruct_path(parent, src, dst):
    if parent is None:
        return []
    path = []
    cur = dst
    while cur != -1 and cur != src:
        path.append(cur)
        cur = parent[cur]
    if cur == -1 and (not path or path[-1] != src):
        return []
    path.append(src)
    path.reverse()
    return path


def enum_simple_paths(n, adj, src, dst, limit_paths=200000):
    all_paths = []
    visited = [False] * n
    path = []

    def dfs(u, cost):
        if len(all_paths) >= limit_paths:
            return
        if u == dst:
            all_paths.append((path.copy(), cost))
            return
        for v, w in adj[u]:
            if not visited[v]:
                visited[v] = True
                path.append(v)
                dfs(v, cost + w)
                path.pop()
                visited[v] = False

    visited[src] = True
    path.append(src)
    dfs(src, 0)
    path.pop()
    visited[src] = False
    return all_paths


def reachable_from_set(start_nodes, target, edges_idx):
    if isinstance(start_nodes, int):
        start_nodes = [start_nodes]
    n = max((max(u, v) for u, v, _ in edges_idx), default=-1) + 1
    adj = [[] for _ in range(n)]
    for u, v, _ in edges_idx:
        adj[u].append(v)
    seen = [False] * n
    q = deque()
    for s in start_nodes:
        if 0 <= s < n:
            q.append(s)
            seen[s] = True
    while q:
        u = q.popleft()
        if u == target:
            return True
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                q.append(v)
    return False


# -------------------------------
# Console flow (no printing of airport list)
def main():
    nodes, edges_idx, name2idx, idx2name = build_index_maps(AIRPORTS, EDGES)
    n = len(nodes)
    adj = adjacency_list(n, edges_idx)

    # Write HTML map and open in browser
    out_file = "airports_map.html"
    write_map_html(out_file, AIRPORTS)
    # try to open in default browser
    web_path = Path(out_file).absolute().as_uri()
    try:
        print("\nOpening map in your default web browser... (file: airports_map.html)")
        webbrowser.open(web_path)
    except Exception:
        print("Please open 'airports_map.html' manually in a browser to view airport IDs and names.")

    # pause briefly so user can see the map
    time.sleep(1)

    print("\n( Airport list is shown on the map. Please use the airport 'id' or exact name from the map )")
    src_input = input("Enter SOURCE (id or exact name): ").strip()
    dst_input = input("Enter DESTINATION (id or exact name): ").strip()

    # parse inputs
    def parse_node(s):
        if s.isdigit():
            idx = int(s)
            if 0 <= idx < n:
                return idx
            raise ValueError("Index out of range.")
        # exact name match
        if s in name2idx:
            return name2idx[s]
        # case-insensitive match
        for name in name2idx:
            if name.lower() == s.lower():
                return name2idx[name]
        raise ValueError("Unknown airport name or id. Use id or exact name from map.")

    try:
        src = parse_node(src_input)
        dst = parse_node(dst_input)
    except ValueError as e:
        print("Input error:", e)
        return

    has_negative = any(w < 0 for (_, _, w) in edges_idx)
    # If negative, detect negative cycles reachable from source and whether they affect destination
    if has_negative:
        dist_bf, parent_bf, neg_info = bellman_ford(n, edges_idx, src)
        if neg_info:
            affected = neg_info["affected"]
            cycle = neg_info.get("cycle", [])
            affects_dst = reachable_from_set(affected, dst, edges_idx)
            print("\n⚠️ Negative cycle reachable from source detected on the graph.")
            if cycle:
                print(" Example cycle (ids):", cycle)
                print(" Example cycle (names):", " -> ".join(idx2name[i] for i in cycle))
            if affects_dst:
                print("\nBecause the negative cycle can reach the destination, there is NO finite cheapest path.")
                return
            else:
                print("The negative cycle does NOT affect the selected destination; proceeding.\n")
        else:
            # no negative cycle reachable: continue
            pass

    # enumerate all simple paths only when graph is reasonably small
    MAX_ENUM_NODES = 12
    all_paths = []
    if n <= MAX_ENUM_NODES:
        print("Enumerating all simple paths from source to destination (may be many)...")
        all_paths = enum_simple_paths(n, adj, src, dst)
        if all_paths:
            print(f"Found {len(all_paths)} simple paths. (sorted by cost):")
            all_paths_sorted = sorted(all_paths, key=lambda x: x[1])
            for i, (p, cost) in enumerate(all_paths_sorted, 1):
                names = " -> ".join(idx2name[x] for x in p)
                print(f"{i:3}. Cost = {cost} | Path: {names}")
        else:
            print("No simple paths found between the selected nodes.")
    else:
        print(f"Graph has {n} nodes (> {MAX_ENUM_NODES}); skipping full enumeration of simple paths.")

    # find cheapest via algorithm
    print("\nComputing cheapest path using algorithm...")
    if has_negative:
        dist, parent, neginfo2 = bellman_ford(n, edges_idx, src)
    else:
        dist, parent = dijkstra(n, adj, src)

    if dist[dst] == INF or dist[dst] == math.inf:
        print("\nDestination unreachable from source.")
    else:
        path = reconstruct_path(parent, src, dst)
        print("\n--- Cheapest path (algorithm result) ---")
        print("Path:", " -> ".join(idx2name[i] for i in path))
        print("Total cheapest fare:", dist[dst])

        # verify against enumerated simple paths if available
        if all_paths:
            min_cost = min(c for _, c in all_paths)
            print("\nVerification against enumerated simple paths:")
            print("Min cost among enumerated simple paths =", min_cost)
            if abs(min_cost - dist[dst]) < 1e-9:
                print("Verified: algorithm's cheapest path matches enumerated simple-path minimum.")
            else:
                print("Note: algorithm's cheapest path differs from enumerated simple-path min.")
                print("This can happen if cycles reduce cost (but negative-cycle case was handled), or if the cheapest path revisits nodes.")

    print("\nDone. You may edit the EDGES list in the script to change fares or add/remove flights.")


if __name__ == "__main__":
    main()
