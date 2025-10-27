# app.py
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, Response, jsonify
from planner import (
    AIRPORTS, ID_TO_AIRPORT,
    generate_graph_limited, bellman_ford, enum_simple_paths, build_result_map_html
)

app = Flask(__name__, static_folder="static", template_folder="templates")


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


@app.route("/")
def index():
    return render_template("index.html", airports=AIRPORTS)


@app.route("/api/airports")
def api_airports():
    return jsonify(AIRPORTS)


@app.route("/api/compute", methods=["POST"])
def api_compute():
    data = request.get_json(force=True)
    try:
        src = int(data["source"])
        dst = int(data["destination"])
    except Exception:
        return jsonify({"error": "invalid input"}), 400
    demo_cycle = bool(data.get("demo_negcycle", False))

    edges = generate_graph_limited(src, dst, allow_negative_cycle_demo=demo_cycle)
    node_ids = [a["id"] for a in AIRPORTS]
    dist_map, parent_map, negcycle = bellman_ford(node_ids, edges, src)

    all_paths = enum_simple_paths(node_ids, edges, src, dst, limit=10)
    all_paths_sorted = sorted(all_paths, key=lambda x: x[1])

    cheapest_ids = all_paths_sorted[0][0] if all_paths_sorted else None

    html = build_result_map_html(edges, all_paths_sorted, cheapest_ids, negcycle=negcycle)

    headers = {}
    headers["X-Negative-Cycle"] = "1" if negcycle else "0"
    return Response(html, headers=headers, mimetype="text/html")


if __name__ == "__main__":
    print("Starting AeroPath local server... opening browser: http://127.0.0.1:5000/")
    Timer(1, _open_browser).start()
    app.run(port=5000, debug=False)
