const API = 'https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo=';
const $ = (selector) => document.querySelector(selector);
const numberChart = $('#number-chart');
const recommendations = $('#recommendations');
const loadStatus = $('#load-status');
const windowSize = $('#window-size');
const cacheKey = 'lotto-stats-cache-v1';

function getLatestDraw() {
  const firstDraw = Date.UTC(2002, 11, 7);
  const today = new Date();
  const weeks = Math.floor((Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) - firstDraw) / 604800000);
  return Math.max(1, weeks + 1);
}

async function fetchDraw(drawNumber) {
  const response = await fetch(`${API}${drawNumber}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const result = await response.json();
  if (result.returnValue !== 'success') return null;
  return { draw: drawNumber, numbers: [1, 2, 3, 4, 5, 6].map((index) => result[`drwtNo${index}`]), bonus: result.bnusNo };
}

async function fetchHistory(start, end) {
  if (window.location.protocol !== 'file:') {
    const response = await fetch(`/api/history?start=${start}&end=${end}`);
    if (!response.ok) throw new Error(`로컬 데이터 서버 HTTP ${response.status}`);
    return response.json();
  }
  const draws = [];
  const chunkSize = 20;
  for (let cursor = start; cursor <= end; cursor += chunkSize) {
    const batchEnd = Math.min(cursor + chunkSize - 1, end);
    const batch = await Promise.all(Array.from({ length: batchEnd - cursor + 1 }, (_, offset) => fetchDraw(cursor + offset)));
    draws.push(...batch.filter(Boolean));
    loadStatus.textContent = `${draws.length} / ${end - start + 1}회 데이터를 읽는 중...`;
  }
  return draws;
}

function countNumbers(draws) {
  const main = Array(46).fill(0);
  const bonus = Array(46).fill(0);
  draws.forEach(({ numbers, bonus: bonusNumber }) => { numbers.forEach((number) => { main[number] += 1; }); bonus[bonusNumber] += 1; });
  return { main, bonus };
}

function selectAnalysisDraws(draws) {
  if (windowSize.value === 'all') return draws;
  return draws.slice(-Number(windowSize.value));
}

function getShapeStats(draws) {
  const sums = draws.map(({ numbers }) => numbers.reduce((total, number) => total + number, 0));
  const oddEven = draws.map(({ numbers }) => numbers.filter((number) => number % 2).length);
  const highLow = draws.map(({ numbers }) => numbers.filter((number) => number >= 23).length);
  const consecutive = draws.map(({ numbers }) => {
    const sorted = [...numbers].sort((a, b) => a - b);
    return sorted.filter((number, index) => index > 0 && number === sorted[index - 1] + 1).length;
  });
  return {
    averageSum: Math.round(sums.reduce((total, sum) => total + sum, 0) / Math.max(sums.length, 1)),
    commonOdd: [...new Set(oddEven)].sort((a, b) => oddEven.filter((value) => value === b).length - oddEven.filter((value) => value === a).length)[0],
    commonHigh: [...new Set(highLow)].sort((a, b) => highLow.filter((value) => value === b).length - highLow.filter((value) => value === a).length)[0],
    consecutiveRounds: consecutive.filter((value) => value > 0).length,
  };
}

function getPairCounts(draws) {
  const pairs = new Map();
  draws.forEach(({ numbers }) => numbers.forEach((first, index) => numbers.slice(index + 1).forEach((second) => {
    const key = `${first}-${second}`;
    pairs.set(key, (pairs.get(key) || 0) + 1);
  })));
  return pairs;
}

function getAcValue(numbers) {
  const differences = new Set();
  numbers.forEach((first, index) => numbers.slice(index + 1).forEach((second) => differences.add(Math.abs(first - second))));
  return differences.size - 5;
}

function getNumberProfile(number, draws, counts, fullDraws) {
  const recentMax = Math.max(...counts.main.slice(1));
  const lastIndex = fullDraws.reduce((latest, draw, index) => draw.numbers.includes(number) ? index : latest, -1);
  return {
    recent: counts.main[number],
    gap: lastIndex < 0 ? fullDraws.length : fullDraws.length - 1 - lastIndex,
    hot: counts.main[number] >= Math.max(2, recentMax - 1),
    rollover: fullDraws.at(-1)?.numbers.includes(number) || false,
  };
}

function isBalancedCombination(numbers, previousNumbers) {
  const odd = numbers.filter((number) => number % 2).length;
  const high = numbers.filter((number) => number >= 23).length;
  const sum = numbers.reduce((total, number) => total + number, 0);
  const consecutive = numbers.filter((number, index) => index > 0 && number === numbers[index - 1] + 1).length;
  const sections = numbers.map((number) => Math.floor((number - 1) / 9));
  const ends = numbers.map((number) => number % 10);
  const rollover = numbers.filter((number) => previousNumbers.includes(number)).length;
  return odd >= 2 && odd <= 4 && high >= 2 && high <= 4 && sum >= 110 && sum <= 170
    && consecutive <= 1 && Math.max(...sections.map((section) => sections.filter((value) => value === section).length)) <= 2
    && Math.max(...ends.map((end) => ends.filter((value) => value === end).length)) <= 2
    && rollover <= 2 && getAcValue(numbers) >= 7 && getAcValue(numbers) <= 10;
}

function explainCombination(numbers, draws, counts, fullDraws) {
  const odd = numbers.filter((number) => number % 2).length;
  const high = numbers.filter((number) => number >= 23).length;
  const sum = numbers.reduce((total, number) => total + number, 0);
  const consecutive = numbers.filter((number, index) => index > 0 && number === numbers[index - 1] + 1).length;
  const sections = new Set(numbers.map((number) => Math.floor((number - 1) / 9))).size;
  const profiles = numbers.map((number) => getNumberProfile(number, draws, counts, fullDraws));
  const hot = numbers.filter((number, index) => profiles[index].hot).join(', ') || '없음';
  const cold = numbers.filter((number, index) => profiles[index].gap >= 5).join(', ') || '없음';
  const rollover = numbers.filter((number, index) => profiles[index].rollover).join(', ') || '없음';
  const endCounts = numbers.reduce((map, number) => { const end = number % 10; map[end] = (map[end] || 0) + 1; return map; }, {});
  const repeatedEnds = Object.entries(endCounts).filter(([, count]) => count > 1).map(([end, count]) => `${end}끝 ${count}개`).join(', ') || '중복 적음';
  return `핫수 ${hot} · 미출현 5회+ ${cold} · 이월 ${rollover} | 홀짝 ${odd}:${6 - odd}, 고저 ${6 - high}:${high}, 합계 ${sum}, AC ${getAcValue(numbers)}, 구간 ${sections}개, ${consecutive ? `연속 ${consecutive}쌍` : '연속 없음'}, ${repeatedEnds}`;
}

function pickRecommendations(draws, counts, fullDraws = draws) {
  const recentCounts = counts.main;
  const fullCounts = countNumbers(fullDraws).main;
  const pairCounts = getPairCounts(fullDraws);
  const previousNumbers = fullDraws.at(-1)?.numbers || [];
  const lastSeen = Array(46).fill(0);
  fullDraws.forEach(({ numbers }, index) => numbers.forEach((number) => { lastSeen[number] = index + 1; }));
  const scores = Array.from({ length: 45 }, (_, index) => ({
    number: index + 1,
    score: recentCounts[index + 1] / Math.max(draws.length, 1) * 0.55
      + fullCounts[index + 1] / Math.max(fullDraws.length, 1) * 0.25
      + (fullDraws.length - lastSeen[index + 1]) / Math.max(fullDraws.length, 1) * 0.08,
  }));
  const result = [];
  let retries = 0;
  for (let row = 0; row < 5; row += 1) {
    const selected = []; const pool = scores.map((item) => ({ ...item }));
    while (selected.length < 6) {
      const candidates = pool.filter(({ number }) => {
        if (selected.includes(number) || (selected.length >= 3 && Math.abs(number - selected[selected.length - 1]) <= 1)) return false;
        const oddCount = selected.filter((value) => value % 2).length + (number % 2);
        const highCount = selected.filter((value) => value >= 23).length + (number >= 23);
        const section = Math.floor((number - 1) / 9);
        const sectionCount = selected.filter((value) => Math.floor((value - 1) / 9) === section).length;
        const nextSum = selected.reduce((sum, value) => sum + value, 0) + number;
        const endCount = selected.filter((value) => value % 10 === number % 10).length;
        const rolloverCount = selected.filter((value) => previousNumbers.includes(value)).length + (previousNumbers.includes(number) ? 1 : 0);
        const sumOkay = selected.length < 5 || (nextSum >= 110 && nextSum <= 170);
        return oddCount <= 4 && oddCount + (6 - selected.length - 1) >= 2 && highCount <= 4 && highCount + (6 - selected.length - 1) >= 2 && sectionCount < 2 && endCount < 2 && (selected.length < 5 || rolloverCount <= 2) && sumOkay;
      });
      const source = candidates.length ? candidates : pool.filter(({ number }) => !selected.includes(number));
      const weighted = source.map((item) => ({ ...item, score: item.score + selected.reduce((sum, number) => sum + (pairCounts.get(`${Math.min(number, item.number)}-${Math.max(number, item.number)}`) || 0) / Math.max(fullDraws.length, 1) * 0.04, 0) }));
      weighted.forEach((item) => {
        if (previousNumbers.includes(item.number) && selected.filter((number) => previousNumbers.includes(number)).length < 2) item.score += 0.025;
        if (item.number % 10 === 0 || item.number % 10 === 5) item.score += 0.004;
      });
      const total = weighted.reduce((sum, item) => sum + item.score + 0.0001, 0);
      let target = Math.random() * total;
      const chosen = weighted.find((item) => { target -= item.score + 0.0001; return target <= 0; }) || weighted[0];
      selected.push(chosen.number); pool.splice(pool.findIndex((item) => item.number === chosen.number), 1);
    }
    const sorted = selected.sort((a, b) => a - b);
    if (!isBalancedCombination(sorted, previousNumbers)) {
      retries += 1;
      if (retries < 1000) { row -= 1; continue; }
    }
    result.push(sorted);
  }
  return result;
}

function render(draws, fullDraws = draws) {
  const counts = countNumbers(draws); const max = Math.max(...counts.main.slice(1)); const min = Math.min(...counts.main.slice(1));
  numberChart.innerHTML = counts.main.slice(1).map((count, index) => `<div class="number-bar ${count === max ? 'hot' : count === min ? 'cool' : ''}"><b>${index + 1}</b><span>${count}회</span></div>`).join('');
  const picks = pickRecommendations(draws, counts, fullDraws);
  recommendations.innerHTML = picks.map((row, rowIndex) => `<div class="recommendation" style="animation-delay:${rowIndex * 70}ms"><div class="recommendation-top"><span>0${rowIndex + 1}</span>${row.map((number) => `<b class="ball">${number}</b>`).join('')}</div><p class="recommendation-reason">${explainCombination(row, draws, counts, fullDraws)}</p></div>`).join('');
  const top = [...counts.main.keys()].slice(1).sort((a, b) => counts.main[b] - counts.main[a]).slice(0, 3);
  const bonusTop = [...counts.bonus.keys()].slice(1).sort((a, b) => counts.bonus[b] - counts.bonus[a])[0];
  const shapeStats = getShapeStats(draws);
  $('#draw-count').textContent = `${draws.length}회 분석`; $('#insights').innerHTML = `<div><dt>데이터</dt><dd>정상 ${draws.length}회</dd></div><div><dt>최다 출현</dt><dd>${top.join(', ')}번</dd></div><div><dt>보너스 최다</dt><dd>${bonusTop}번 (${counts.bonus[bonusTop]}회)</dd></div><div><dt>분석 범위</dt><dd>${draws[0].draw}회 ~ ${draws.at(-1).draw}회</dd></div><div><dt>평균 합계</dt><dd>${shapeStats.averageSum}</dd></div><div><dt>최빈 홀수 개수</dt><dd>${shapeStats.commonOdd}개</dd></div><div><dt>최빈 고번호 개수</dt><dd>${shapeStats.commonHigh}개</dd></div><div><dt>연속수 포함 회차</dt><dd>${shapeStats.consecutiveRounds}회</dd></div>`;
}

async function load() {
  const start = 1; const end = getLatestDraw();
  $('#refresh-button').disabled = true; loadStatus.textContent = '최신 회차 확인 완료. 데이터 요청 준비 중...';
  try { const draws = await fetchHistory(start, end); if (!draws.length) throw new Error('회차 데이터 없음'); render(selectAnalysisDraws(draws), draws); localStorage.setItem(cacheKey, JSON.stringify({ savedAt: Date.now(), draws })); loadStatus.textContent = `${draws.at(-1).draw}회까지 · ${windowSize.options[windowSize.selectedIndex].text} 분석 완료`; } catch (error) { loadStatus.textContent = '데이터를 불러오지 못했습니다. 네트워크 연결을 확인하세요.'; console.error(error); } finally { $('#refresh-button').disabled = false; }
}

$('#refresh-button').addEventListener('click', load);
windowSize.addEventListener('change', () => {
  const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
  if (cached?.draws?.length) render(selectAnalysisDraws(cached.draws), cached.draws);
});
const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
if (cached?.draws?.length) { render(selectAnalysisDraws(cached.draws), cached.draws); loadStatus.textContent = `저장된 최신 회차 통계 · ${windowSize.options[windowSize.selectedIndex].text}`; } else load();