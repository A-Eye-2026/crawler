const map = L.map('map').setView([36.4, 127.8], 7);
const summaryCard = document.getElementById('summary-card');
const refreshButton = document.getElementById('refresh-button');
const searchInput = document.getElementById('search-input');

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markersLayer = L.layerGroup().addTo(map);
let allRestAreas = [];

function getMarkerColor(item) {
  if (!item.total_parking_spaces) return '#6b7280';
  const availabilityRatio = item.available_parking_spaces / item.total_parking_spaces;
  if (availabilityRatio <= 0.15) return '#dc2626';
  if (availabilityRatio <= 0.4) return '#f59e0b';
  return '#16a34a';
}

function createMarkerIcon(color) {
  return L.divIcon({
    className: '',
    html: `<div class="custom-marker" style="background:${color}"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });
}

function renderSummary(item) {
  summaryCard.innerHTML = `
    <h3>${item.name}</h3>
    <dl>
      <dt>노선명</dt>
      <dd>${item.route_name || '-'}</dd>
      <dt>현재 여유 / 총 공간</dt>
      <dd>${item.available_parking_spaces} / ${item.total_parking_spaces}</dd>
      <dt>현재 주차 대수</dt>
      <dd>${item.occupied_parking_spaces}</dd>
      <dt>전기차 충전기</dt>
      <dd>${item.ev_charger_count ?? 0}</dd>
      <dt>최근 업데이트</dt>
      <dd>${item.last_synced_at || '-'}</dd>
    </dl>
  `;
}

function displayMarkers(items) {
  markersLayer.clearLayers();
  
  if (items.length === 0) return;

  const bounds = L.latLngBounds();

  items.forEach((item) => {
    // 위경도가 0,0이거나 잘못된 경우 건너뜀
    if (item.lat === 0 || item.lng === 0) return;

    const color = getMarkerColor(item);
    const marker = L.marker([item.lat, item.lng], {
      icon: createMarkerIcon(color)
    });

    marker.bindPopup(`
      <strong>${item.name}</strong><br>
      ${item.route_name}<br>
      여유 ${item.available_parking_spaces} / 총 ${item.total_parking_spaces}
    `);

    marker.on('click', () => renderSummary(item));
    marker.addTo(markersLayer);
    bounds.extend([item.lat, item.lng]);
  });

  // 모든 마커가 보이도록 지도 범위 조정 (전국 보기)
  if (!bounds.isValid()) {
    map.setView([36.4, 127.8], 7);
  } else if (items.length === 1) {
    map.setView([items[0].lat, items[0].lng], 13);
    renderSummary(items[0]);
  } else {
    map.fitBounds(bounds, { padding: [50, 50] });
  }
}

async function loadParkingStatus() {
  console.log('API 호출 시도...');
  const response = await fetch('/api/v1/parking-status');
  const data = await response.json();
  console.log(`서버로부터 ${data.items.length}개의 데이터를 받았습니다.`);
  allRestAreas = data.items;
  displayMarkers(allRestAreas);
}

function handleSearch(e) {
  const query = e.target.value.toLowerCase().trim();
  if (!query) {
    displayMarkers(allRestAreas);
    return;
  }

  const filtered = allRestAreas.filter(item => 
    item.name.toLowerCase().includes(query) || 
    item.route_name.toLowerCase().includes(query)
  );
  
  displayMarkers(filtered);
}

searchInput.addEventListener('input', handleSearch);
refreshButton.addEventListener('click', loadParkingStatus);
loadParkingStatus();
