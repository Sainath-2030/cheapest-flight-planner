// static/js/main.js
// This script receives `airports` variable injected into index.html by Flask.

(function () {
  // ensure airports is defined
  if (typeof airports === "undefined" || !Array.isArray(airports)) {
    console.error("airports data not found on page.");
    alert("Airports data not loaded. Reload page.");
    return;
  }

  const map = L.map('mapid').setView([20.5937, 78.9629], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
  }).addTo(map);

  let selection = { source: null, dest: null };

  // add markers and popup with Select button
  airports.forEach(a => {
    const marker = L.marker([a.lat, a.lon]).addTo(map);
    const popupHtml = `<div style="font-size:14px"><b>${a.name}</b><br/><em>${a.id}</em><br/><button onclick="selectAirport(${a.id})">Select</button></div>`;
    marker.bindPopup(popupHtml);
  });

  // expose selectAirport globally (popup button calls it)
  window.selectAirport = function(id) {
    const a = airports.find(x => x.id === id);
    if (!a) {
      alert("Airport not found");
      return;
    }
    if (!selection.source) {
      selection.source = a;
      alert(`Source set: ${a.name}\nNow select destination`);
    } else if (!selection.dest) {
      if (selection.source.id === a.id) {
        alert("Source and destination must be different");
        return;
      }
      selection.dest = a;
      alert(`Destination set: ${a.name}\nGenerating routes...`);
      // send to backend to compute dynamic graph, BF, etc.
      fetch('/api/compute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: selection.source.id, dest: selection.dest.id })
      }).then(r => r.json()).then(resp => {
        if (!resp) { alert("No response from server"); return; }
        if (resp.status === 'ok' || resp.status === 'negcycle') {
          // go to result page that loads the generated HTML map (saved under static_maps)
          window.location.href = '/result?map=' + encodeURIComponent(resp.map_file);
        } else {
          alert("Error: " + (resp.message || "unknown"));
        }
      }).catch(err => {
        console.error(err);
        alert("Network/server error. See console.");
      });
    } else {
      alert("Both source and destination already chosen. Reload page to restart.");
    }
  };

})();
