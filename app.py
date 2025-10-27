# app.py
import os
import time
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from planner import AIRPORTS, ID_TO_AIRPORT, generate_edges_ensure_connectivity, bellman_ford, enum_simple_paths, build_result_map_html

app = Flask(__name__, static_folder="static")

STATIC_MAP_DIR = Path("static_maps")
STATIC_MAP_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    # pass airports to template so JS can use them
    return render_template("index.html", airports=AIRPORTS)


@app.route("/api/compute", methods=["POST"])
def api_compute():
    """
    Expects JSON: { "source": <id>, "dest": <id> }
    Returns JSON with map_file (path), cheapest_path, cheapest_cost, all_paths, negcycle flag
    """
    data = request.get_json(force=True)
    src = data.get("source")
    dst = data.get("dest")
    if src is None or dst is None:
        return jsonify({"status": "error", "message": "source and dest required"}), 400
    if src == dst:
        return jsonify({"status": "error", "message": "source and dest must differ"}), 400

    # generate dynamic edges ensuring connectivity
    edges = generate_edges_ensure_connectivity(src, dst, min_out=3, max_out=5)

    nodes = [a["name"] for a in AIRPORTS]

    # run Bellman-Ford (detect negative cycles)
    dist, parent, negcycle = bellman_ford(nodes, edges, ID_TO_AIRPORT[src]["name"])
    if negcycle:
        # still build result map to visualize generated graph and indicate negative cycle
        cheapest_path = []
        all_paths = enum_simple_paths(nodes, edges, ID_TO_AIRPORT[src]["name"], ID_TO_AIRPORT[dst]["name"], limit=2000)
        # save result HTML
        fname = f"result_map_{int(time.time())}.html"
        fpath = STATIC_MAP_DIR / fname
        html = build_result_map_html(edges, cheapest_path, all_paths, negcycle=True)
        fpath.write_text(html, encoding="utf-8")
        return jsonify({
            "status": "negcycle",
            "message": "Negative cycle detected in generated graph (demo).",
            "map_file": f"/{fpath.as_posix()}",
            "all_paths": [{"path": p, "cost": c} for p, c in all_paths]
        }), 200

    dest_name = ID_TO_AIRPORT[dst]["name"]
    if dist[dest_name] == float("inf"):
        # unexpected because generator ensures connectivity, but handle gracefully
        return jsonify({"status": "error", "message": "destination unreachable (unexpected)"}), 500

    # reconstruct cheapest path
    path = []
    cur = dest_name
    while cur is not None:
        path.insert(0, cur)
        cur = parent[cur]

    # enumerate all simple paths (limited)
    all_paths = enum_simple_paths(nodes, edges, ID_TO_AIRPORT[src]["name"], dest_name, limit=2000)

    # build and save result map html
    fname = f"result_map_{int(time.time())}.html"
    fpath = STATIC_MAP_DIR / fname
    html = build_result_map_html(edges, path, all_paths, negcycle=False, cheapest_cost=dist[dest_name])
    fpath.write_text(html, encoding="utf-8")

    return jsonify({
        "status": "ok",
        "map_file": f"/{fpath.as_posix()}",
        "cheapest_path": path,
        "cheapest_cost": dist[dest_name],
        "all_paths": [{"path": p, "cost": c} for p, c in all_paths]
    }), 200


@app.route("/result")
def result_page():
    mp = request.args.get("map")
    if not mp:
        return "No map provided", 400
    realpath = mp.lstrip("/")
    if not Path(realpath).exists():
        return "Map not found", 404
    # return raw HTML so Flask/Jinja don't try to reprocess it
    return Response(Path(realpath).read_text(encoding="utf-8"), mimetype="text/html")


if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    print("Starting local server... opening browser:", url)
    webbrowser.open(url)
    app.run(port=5000, debug=False)
