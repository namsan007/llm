const CONFIG = {
  // 서울 열린데이터광장 인증키를 넣으면 데모 대신 실시간 데이터를 사용합니다.
  serviceKey: '',
  apiUrl: 'http://ws.bus.go.kr/api/rest/buspos/getBusPosByRtid'
};

const DEMO_BUSES = [
  { id: 'demo-10-a', route: '10', label: '구로10 · 01', lat: 37.4977, lng: 126.8593, stop: '구로역' },
  { id: 'demo-10-b', route: '10', label: '구로10 · 02', lat: 37.5054, lng: 126.8842, stop: '가리봉시장' },
  { id: 'demo-11-a', route: '11', label: '구로11 · 01', lat: 37.4935, lng: 126.8326, stop: '개봉역' },
  { id: 'demo-11-b', route: '11', label: '구로11 · 02', lat: 37.5104, lng: 126.8758, stop: '남구로역' }
];

const map = L.map('map', { zoomControl: false }).setView([37.498, 126.864], 13);
L.control.zoom({ position: 'bottomright' }).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
const markers = new Map();
let buses = [];
let selectedRoute = 'all';
let refreshTimer;

const $ = (selector) => document.querySelector(selector);

function markerIcon(route) {
  return L.divIcon({ className: '', html: `<span class="map-marker route-${route}-marker">${route}</span>`, iconSize: [38, 38], iconAnchor: [19, 19] });
}

function visibleBuses() {
  return buses.filter((bus) => selectedRoute === 'all' || bus.route === selectedRoute);
}

function render() {
  const visible = visibleBuses();
  markers.forEach((marker, id) => { if (!visible.some((bus) => bus.id === id)) marker.remove(); });
  visible.forEach((bus) => {
    const popup = `<strong>${bus.label}</strong><br><span>${bus.stop || '운행 중'}</span>`;
    if (!markers.has(bus.id)) markers.set(bus.id, L.marker([bus.lat, bus.lng], { icon: markerIcon(bus.route) }).addTo(map).bindPopup(popup));
    else markers.get(bus.id).setLatLng([bus.lat, bus.lng]).setPopupContent(popup).addTo(map);
  });
  $('#bus-count').textContent = `${visible.length}대`;
  $('#bus-cards').innerHTML = visible.length ? visible.map((bus) => `<article class="bus-card"><span class="bus-badge route-${bus.route}-badge">${bus.route}</span><div><strong>${bus.label}</strong><small>${bus.stop || '운행 중'}</small></div><span class="moving">운행 중</span></article>`).join('') : '<p class="empty">선택한 노선의 버스가 없습니다.</p>';
}

function parseApiBus(item, index) {
  return { id: item.vehId || `bus-${index}`, route: String(item.rtNm || item.busRouteNm || '').replace(/[^0-9]/g, ''), label: item.rtNm || item.busRouteNm || '마을버스', lat: Number(item.gpsY), lng: Number(item.gpsX), stop: item.stationNm || item.stNm || '운행 중' };
}

async function loadBuses() {
  $('#refresh-button').disabled = true;
  $('#status').textContent = CONFIG.serviceKey ? '실시간 위치를 가져오는 중...' : '데모 위치를 표시하는 중...';
  try {
    if (!CONFIG.serviceKey) throw new Error('demo');
    const response = await fetch(`${CONFIG.apiUrl}?serviceKey=${encodeURIComponent(CONFIG.serviceKey)}&format=json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const items = payload?.ServiceResult?.msgBody?.itemList || [];
    buses = items.map(parseApiBus).filter((bus) => ['10', '11'].includes(bus.route) && Number.isFinite(bus.lat) && Number.isFinite(bus.lng));
    if (!buses.length) throw new Error('no buses');
    $('#status').textContent = '실시간 데이터 연결됨';
  } catch (error) {
    buses = DEMO_BUSES.map((bus) => ({ ...bus, lat: bus.lat + (Math.random() - 0.5) * 0.0015, lng: bus.lng + (Math.random() - 0.5) * 0.0015 }));
    $('#status').textContent = '데모 위치 · API 키를 입력하면 실시간 전환';
    console.info('실시간 API 미연결:', error.message);
  } finally {
    render();
    $('#updated-at').textContent = `마지막 갱신: ${new Intl.DateTimeFormat('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date())}`;
    $('#refresh-button').disabled = false;
  }
}

function setRefreshTimer() {
  clearInterval(refreshTimer);
  const seconds = Number($('#refresh-interval').value);
  if (seconds) refreshTimer = setInterval(loadBuses, seconds * 1000);
}

document.querySelectorAll('.route-button').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('.route-button').forEach((item) => item.classList.remove('active'));
  button.classList.add('active'); selectedRoute = button.dataset.route; render();
}));
$('#refresh-button').addEventListener('click', loadBuses);
$('#refresh-interval').addEventListener('change', setRefreshTimer);
loadBuses(); setRefreshTimer();