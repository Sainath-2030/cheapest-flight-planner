async function fetchAirports() {
  const res = await fetch('/api/airports');
  return await res.json();
}

let airportsGlobal = [];
let map = null;
let sourceSelect, destSelect;

async function init() {
  const airports = await fetchAirports();
  airportsGlobal = airports;
  sourceSelect = document.getElementById('source');
  destSelect = document.getElementById('destination');

  airports.forEach(a => {
    const opt1 = document.createElement('option');
    opt1.value = a.id;
    opt1.text = a.name;
    const opt2 = document.createElement('option');
    opt2.value = a.id;
    opt2.text = a.name;
    sourceSelect.appendChild(opt1);
    destSelect.appendChild(opt2);
  });

  initMap();
  attachHandlers();
}

function initMap() {
  map = L.map('map').setView([21.0, 78.0], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  airportsGlobal.forEach(a => {
    const marker = L.marker([a.lat, a.lon]).addTo(map).bindPopup(a.name);
    marker.on('click', () => {
      const pick = confirm(`Set ${a.name} as SOURCE? (Cancel = DESTINATION)`);
      if (pick) sourceSelect.value = a.id;
      else destSelect.value = a.id;
    });
  });
}

function attachHandlers() {
  document.getElementById('computeBtn').addEventListener('click', async () => {
    const src = Number(sourceSelect.value);
    const dst = Number(destSelect.value);
    const demoCheckbox = document.getElementById('demo_cycle');
    const demo = demoCheckbox ? demoCheckbox.checked : false;


    if (isNaN(src) || isNaN(dst) || src === dst) {
      alert('Please select different Source and Destination.');
      return;
    }

    const payload = { source: src, destination: dst, demo_negcycle: demo };
    const res = await fetch('/api/compute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const txt = await res.text();
      console.error('Server error:', txt);
      alert('Server error — check console.');
      return;
    }

    const html = await res.text();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);

    const neg = res.headers.get('X-Negative-Cycle');
    if (neg === '1') {
      setTimeout(() => alert('Demo note: Generated graph contains a negative-weight cycle.'), 400);
    }
  });
}

window.addEventListener('load', init);
