const map = L.map('map').setView([36.5, 127.8], 7);
const summaryCard = document.getElementById('summary-card');
const refreshButton = document.getElementById('refresh-button');
const codeSelect = document.getElementById('code-select');
const statusBar = document.getElementById('status-bar');
const timeSlider = document.getElementById('time-slider');
const sliderLabel = document.getElementById('slider-label');
const thresholdInput = document.getElementById('threshold-input');
const warningBadge = document.getElementById('warning-badge');
const warningCountEl = document.getElementById('warning-count');

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markersLayer = L.layerGroup().addTo(map);
let currentItems = [];   // 전체 데이터 (forecast 포함)
let selectedItem = null; // 사이드바에 표시 중인 지점
let currentHour = 1;
let threshold = 35;

// ── 유틸 ────────────────────────────────────────────────────────────────────

function getHourValue(item, hour) {
  return item.forecast?.[`h${hour}`] ?? item.index_value ?? null;
}

function getMarkerColor(value) {
  if (value === null || value === undefined) return '#9ca3af';
  if (value < 25) return '#3b82f6';
  if (value < 30) return '#16a34a';
  if (value < 35) return '#f59e0b';
  return '#dc2626';
}

function createMarkerIcon(color, value, isWarning) {
  const label = value !== null && value !== undefined ? value.toFixed(1) : '-';
  const warnClass = isWarning ? ' warning' : '';
  return L.divIcon({
    className: '',
    html: `<div class="custom-marker${warnClass}" style="background:${color}"><span>${label}</span></div>`,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  });
}

/** published_at(YYYYMMDDHHmm) + N시간 → 'YYYY-MM-DD HH:mm' */
function addHoursToPublished(publishedAt, hours) {
  if (!publishedAt || publishedAt.length < 12) return '-';
  const y  = publishedAt.slice(0, 4);
  const mo = publishedAt.slice(4, 6);
  const d  = publishedAt.slice(6, 8);
  const h  = publishedAt.slice(8, 10);
  const base = new Date(`${y}-${mo}-${d}T${h}:00:00+09:00`);
  base.setTime(base.getTime() + hours * 3600 * 1000);
  return base.toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
    timeZone: 'Asia/Seoul',
  });
}

function formatSynced(str) {
  return str ? str.slice(0, 19).replace('T', ' ') : '-';
}

// ── 마커 렌더링 ──────────────────────────────────────────────────────────────

function displayMarkers(items, hour, thresh) {
  markersLayer.clearLayers();
  if (!items.length) return 0;

  let warningCount = 0;

  items.forEach((item) => {
    if (!item.lat || !item.lng) return;

    const value = getHourValue(item, hour);
    const isWarning = value !== null && value >= thresh;
    if (isWarning) warningCount++;

    const color = getMarkerColor(value);
    const marker = L.marker([item.lat, item.lng], {
      icon: createMarkerIcon(color, value, isWarning),
      zIndexOffset: isWarning ? 1000 : 0,
    });

    marker.bindPopup(
      `<strong>${item.area_name}</strong><br>` +
      `체감온도: ${value !== null ? value.toFixed(1) + ' °C' : '-'}<br>` +
      `${addHoursToPublished(item.published_at, hour)}`
    );
    marker.on('click', () => {
      selectedItem = item;
      renderSummary(item, hour);
    });
    marker.addTo(markersLayer);
  });

  return warningCount;
}

// ── 사이드바 요약 ────────────────────────────────────────────────────────────

function renderSummary(item, hour) {
  const value = getHourValue(item, hour);
  const color = getMarkerColor(value);
  const isWarning = value !== null && value >= threshold;

  summaryCard.innerHTML = `
    <h3>
      ${item.area_name}
      ${isWarning ? '<span class="warning-tag">⚠ 경고</span>' : ''}
    </h3>
    <dl>
      <dt>지점코드</dt>
      <dd>${item.area_no}</dd>
      <dt>체감온도 지수 (h${hour})</dt>
      <dd style="color:${color}; font-size:1.5rem; font-weight:800;">
        ${value !== null ? value.toFixed(1) + ' °C' : '데이터 없음'}
      </dd>
      <dt>예보 시각</dt>
      <dd>${addHoursToPublished(item.published_at, hour)}</dd>
      <dt>발표시각 (기준)</dt>
      <dd>${item.published_at ? item.published_at.replace(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1-$2-$3 $4:$5') : '-'}</dd>
      <dt>동기화</dt>
      <dd>${formatSynced(item.synced_at)}</dd>
    </dl>
  `;
}

// ── 슬라이더 라벨 업데이트 ────────────────────────────────────────────────────

function updateSliderLabel(hour) {
  const days = Math.floor((hour - 1) / 24);
  const hrs  = (hour - 1) % 24 + 1;
  let label = `+${hour}시간 후`;
  if (days > 0) label += ` (${days}일 ${hrs}h)`;

  // 대표 published_at으로 실제 시각 표시
  const first = currentItems[0];
  if (first?.published_at) {
    label += ` · ${addHoursToPublished(first.published_at, hour)}`;
  }
  sliderLabel.textContent = label;
}

// ── 경고 배지 업데이트 ────────────────────────────────────────────────────────

function updateWarningBadge(count) {
  if (count > 0) {
    warningCountEl.textContent = count;
    warningBadge.classList.remove('hidden');
  } else {
    warningBadge.classList.add('hidden');
  }
}

// ── 전체 재렌더 (슬라이더·임계값 변경 시 공통 호출) ─────────────────────────

function rerender() {
  const count = displayMarkers(currentItems, currentHour, threshold);
  updateWarningBadge(count);
  updateSliderLabel(currentHour);
  if (selectedItem) renderSummary(selectedItem, currentHour);
}

// ── 데이터 로드 ──────────────────────────────────────────────────────────────

async function loadData() {
  const code = codeSelect.value;
  statusBar.textContent = '데이터 불러오는 중...';
  refreshButton.disabled = true;

  try {
    const resp = await fetch(`/api/v1/weather-index?requestCode=${code}`);
    const data = await resp.json();
    currentItems = data.items || [];
    selectedItem = null;
    summaryCard.innerHTML = '<p>지도에서 지점을 선택해 주세요.</p>';

    rerender();
    statusBar.textContent =
      `[${data.label}] ${data.count}개 지점 · 마지막 동기화: ${formatSynced(data.last_synced_at)}`;
  } catch (e) {
    statusBar.textContent = '데이터 로드 실패: ' + e.message;
  } finally {
    refreshButton.disabled = false;
  }
}

async function syncAndLoad() {
  const code = codeSelect.value;
  statusBar.textContent = 'API 동기화 중...';
  refreshButton.disabled = true;

  try {
    const resp = await fetch(`/api/v1/sync?requestCode=${code}`);
    const data = await resp.json();
    currentItems = data.items || [];
    selectedItem = null;
    summaryCard.innerHTML = '<p>지도에서 지점을 선택해 주세요.</p>';

    rerender();
    statusBar.textContent =
      `[${data.label}] ${data.count}개 지점 동기화 완료`;
  } catch (e) {
    statusBar.textContent = '동기화 실패: ' + e.message;
  } finally {
    refreshButton.disabled = false;
  }
}

// ── 이벤트 ───────────────────────────────────────────────────────────────────

timeSlider.addEventListener('input', () => {
  currentHour = parseInt(timeSlider.value, 10);
  rerender();
});

thresholdInput.addEventListener('input', () => {
  const val = parseFloat(thresholdInput.value);
  if (!isNaN(val)) {
    threshold = val;
    rerender();
  }
});

codeSelect.addEventListener('change', () => {
  timeSlider.value = 1;
  currentHour = 1;
  loadData();
});

refreshButton.addEventListener('click', syncAndLoad);

// ── 초기 로드 ────────────────────────────────────────────────────────────────
loadData();
