const map = L.map('map').setView([36.5, 127.8], 7);
const summaryCard     = document.getElementById('summary-card');
const refreshButton   = document.getElementById('refresh-button');
const codeSelect      = document.getElementById('code-select');
const statusBar       = document.getElementById('status-bar');
const timeSlider      = document.getElementById('time-slider');
const sliderLabel     = document.getElementById('slider-label');
const sliderMinLabel  = document.getElementById('slider-min-label');
const sliderMaxLabel  = document.getElementById('slider-max-label');
const thresholdInput  = document.getElementById('threshold-input');
const thresholdUnit   = document.getElementById('threshold-unit');
const warningBadge    = document.getElementById('warning-badge');
const warningCountEl  = document.getElementById('warning-count');
const legendTitle     = document.getElementById('legend-title');
const legendList      = document.getElementById('legend-list');

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markersLayer = L.layerGroup().addTo(map);
let currentItems = [];
let selectedItem  = null;
let currentHour   = 1;
let threshold     = 35;

// ── 지수별 설정 ──────────────────────────────────────────────────────────────
const INDEX_CONFIG = {
  // 체감온도 (A41~A49)
  SENSATION: {
    sliderMin: 1, sliderMax: 78, sliderStep: 1,
    defaultThreshold: 35, unit: '°C',
    legendTitle: '체감온도 범례 (°C)',
    legend: [
      { cls: 'blue',   label: '쾌적  (< 25)' },
      { cls: 'green',  label: '보통  (25 ~ 30)' },
      { cls: 'orange', label: '더움  (30 ~ 35)' },
      { cls: 'red',    label: '매우 더움  (≥ 35)' },
      { cls: 'gray',   label: '데이터 없음' },
    ],
    getColor(v) {
      if (v === null || v === undefined) return '#9ca3af';
      if (v < 25) return '#3b82f6';
      if (v < 30) return '#16a34a';
      if (v < 35) return '#f59e0b';
      return '#dc2626';
    },
  },
  UV: {
    sliderMin: 0, sliderMax: 75, sliderStep: 3, defaultHour: 9,
    defaultThreshold: 8, unit: '',
    legendTitle: '자외선지수 범례',
    legend: [
      { cls: 'blue',   label: '낮음  (0 ~ 2)' },
      { cls: 'green',  label: '보통  (3 ~ 5)' },
      { cls: 'orange', label: '높음  (6 ~ 7)' },
      { cls: 'red',    label: '매우 높음  (8 ~ 10)' },
      { cls: 'purple', label: '위험  (≥ 11)' },
      { cls: 'gray',   label: '데이터 없음' },
    ],
    getColor(v) {
      if (v === null || v === undefined) return '#9ca3af';
      if (v < 3)  return '#3b82f6';
      if (v < 6)  return '#16a34a';
      if (v < 8)  return '#f59e0b';
      if (v < 11) return '#dc2626';
      return '#7c3aed';
    },
  },
  AIR: {
    sliderMin: 3, sliderMax: 78, sliderStep: 3,
    defaultThreshold: 75, unit: '',
    legendTitle: '대기정체지수 범례',
    legend: [
      { cls: 'blue',   label: '좋음  (25)' },
      { cls: 'green',  label: '보통  (50)' },
      { cls: 'orange', label: '나쁨  (75)' },
      { cls: 'red',    label: '매우 나쁨  (100)' },
      { cls: 'gray',   label: '데이터 없음' },
    ],
    getColor(v) {
      if (v === null || v === undefined) return '#9ca3af';
      if (v <= 25) return '#3b82f6';
      if (v <= 50) return '#16a34a';
      if (v <= 75) return '#f59e0b';
      return '#dc2626';
    },
  },
};

function getConfig(code) {
  if (code === 'UV')  return INDEX_CONFIG.UV;
  if (code === 'AIR') return INDEX_CONFIG.AIR;
  return INDEX_CONFIG.SENSATION;
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

/** forecast 객체에서 hour에 가장 가까운 값을 반환 (step이 3인 경우 대응). */
function getHourValue(item, hour) {
  if (!item.forecast) return item.index_value ?? null;
  const exact = item.forecast[`h${hour}`];
  if (exact !== undefined) return exact;

  // 가장 가까운 키 탐색
  const keys = Object.keys(item.forecast).map(k => parseInt(k.slice(1), 10));
  if (!keys.length) return item.index_value ?? null;
  const nearest = keys.reduce((a, b) => Math.abs(b - hour) < Math.abs(a - hour) ? b : a);
  return item.forecast[`h${nearest}`] ?? null;
}

/** publishedAt(YYYYMMDDHHmm) + N시간 → 'YYYY-MM-DD HH:mm' (KST) */
function addHours(publishedAt, hours) {
  if (!publishedAt || publishedAt.length < 12) return '-';
  const iso = `${publishedAt.slice(0,4)}-${publishedAt.slice(4,6)}-${publishedAt.slice(6,8)}` +
              `T${publishedAt.slice(8,10)}:00:00+09:00`;
  const d = new Date(new Date(iso).getTime() + hours * 3600_000);
  return d.toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
    timeZone: 'Asia/Seoul',
  });
}

function formatSynced(str) {
  return str ? str.slice(0, 19).replace('T', ' ') : '-';
}

function formatValue(value, code) {
  if (value === null || value === undefined) return '데이터 없음';
  const cfg = getConfig(code);
  return value.toFixed(1) + (cfg.unit ? ` ${cfg.unit}` : '');
}

// ── 범례 업데이트 ────────────────────────────────────────────────────────────

function updateLegend(code) {
  const cfg = getConfig(code);
  legendTitle.textContent = cfg.legendTitle;
  legendList.innerHTML = cfg.legend
    .map(({ cls, label }) => `<li><span class="dot ${cls}"></span>${label}</li>`)
    .join('');
}

// ── 슬라이더 설정 ────────────────────────────────────────────────────────────

function applySliderConfig(code) {
  const cfg = getConfig(code);
  timeSlider.min   = cfg.sliderMin;
  timeSlider.max   = cfg.sliderMax;
  timeSlider.step  = cfg.sliderStep;
  const initHour   = cfg.defaultHour ?? cfg.sliderMin;
  timeSlider.value = initHour;
  currentHour      = initHour;
  sliderMinLabel.textContent = `+${cfg.sliderMin}h`;
  sliderMaxLabel.textContent = `+${cfg.sliderMax}h`;

  threshold = cfg.defaultThreshold;
  thresholdInput.value = threshold;
  thresholdUnit.textContent = cfg.unit ? cfg.unit : '(지수)';
}

function updateSliderLabel(hour, code) {
  const days = Math.floor(hour / 24);
  const hrs  = hour % 24;
  let label  = `+${hour}시간 후`;
  if (days > 0) label += ` (${days}일 ${hrs}h)`;
  const first = currentItems[0];
  if (first?.published_at) label += ` · ${addHours(first.published_at, hour)}`;
  sliderLabel.textContent = label;
}

// ── 마커 렌더링 ──────────────────────────────────────────────────────────────

function displayMarkers(items, hour, thresh, code) {
  markersLayer.clearLayers();
  if (!items.length) return 0;

  const cfg = getConfig(code);
  let warningCount = 0;

  items.forEach((item) => {
    if (!item.lat || !item.lng) return;

    const value     = getHourValue(item, hour);
    const isWarning = value !== null && value >= thresh;
    if (isWarning) warningCount++;

    const color  = cfg.getColor(value);
    const label  = value !== null ? value.toFixed(1) : '-';
    const warnCls = isWarning ? ' warning' : '';

    const marker = L.marker([item.lat, item.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="custom-marker${warnCls}" style="background:${color}"><span>${label}</span></div>`,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      }),
      zIndexOffset: isWarning ? 1000 : 0,
    });

    marker.bindPopup(
      `<strong>${item.area_name}</strong><br>` +
      `${cfg.legendTitle.split(' 범례')[0]}: ${formatValue(value, code)}<br>` +
      addHours(item.published_at, hour)
    );
    marker.on('click', () => {
      selectedItem = item;
      renderSummary(item, hour, code);
    });
    marker.addTo(markersLayer);
  });

  return warningCount;
}

// ── 사이드바 ─────────────────────────────────────────────────────────────────

function renderSummary(item, hour, code) {
  const cfg       = getConfig(code);
  const value     = getHourValue(item, hour);
  const color     = cfg.getColor(value);
  const isWarning = value !== null && value >= threshold;

  summaryCard.innerHTML = `
    <h3>
      ${item.area_name}
      ${isWarning ? '<span class="warning-tag">⚠ 경고</span>' : ''}
    </h3>
    <dl>
      <dt>지점코드</dt>
      <dd>${item.area_no}</dd>
      <dt>${cfg.legendTitle.split(' 범례')[0]} (h${hour})</dt>
      <dd style="color:${color}; font-size:1.5rem; font-weight:800;">
        ${formatValue(value, code)}
      </dd>
      <dt>예보 시각</dt>
      <dd>${addHours(item.published_at, hour)}</dd>
      <dt>발표 기준</dt>
      <dd>${item.published_at
            ? item.published_at.replace(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1-$2-$3 $4:$5')
            : '-'}</dd>
      <dt>동기화</dt>
      <dd>${formatSynced(item.synced_at)}</dd>
    </dl>
  `;
}

// ── 전체 재렌더 ──────────────────────────────────────────────────────────────

function rerender() {
  const code  = codeSelect.value;
  const count = displayMarkers(currentItems, currentHour, threshold, code);
  warningCountEl.textContent = count;
  warningBadge.classList.toggle('hidden', count === 0);
  updateSliderLabel(currentHour, code);
  if (selectedItem) renderSummary(selectedItem, currentHour, code);
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
    statusBar.textContent = `[${data.label}] ${data.count}개 지점 동기화 완료`;
  } catch (e) {
    statusBar.textContent = '동기화 실패: ' + e.message;
  } finally {
    refreshButton.disabled = false;
  }
}

// ── 이벤트 ───────────────────────────────────────────────────────────────────

codeSelect.addEventListener('change', () => {
  const code = codeSelect.value;
  applySliderConfig(code);
  updateLegend(code);
  loadData();
});

timeSlider.addEventListener('input', () => {
  currentHour = parseInt(timeSlider.value, 10);
  rerender();
});

thresholdInput.addEventListener('input', () => {
  const v = parseFloat(thresholdInput.value);
  if (!isNaN(v)) { threshold = v; rerender(); }
});

refreshButton.addEventListener('click', syncAndLoad);

// ── 초기 실행 ────────────────────────────────────────────────────────────────
updateLegend(codeSelect.value);
applySliderConfig(codeSelect.value);
loadData();
