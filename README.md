# AeroPath — Cheapest Flight Planner (AOA project)

Local Flask app demonstrating:
- Graph-based flight route generation
- Bellman-Ford for shortest/cheapest path with negative-edge handling
- Negative-fare & negative-cycle demo cases
- Interactive selection via dropdown or clickable map
- Result opens in a new tab showing table + map (cheapest highlighted)

Run:
1. pip install -r requirements.txt
2. python app.py
3. Open http://127.0.0.1:5000/

Demo suggestions:
- Mumbai → Chennai (negative-fare demo)
- Tick "Negative-cycle demo" to show negative cycle among Mumbai↔Pune↔Nagpur
