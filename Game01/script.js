const COLS = 10;
const ROWS = 20;
const SHAPES = [
  { color: '#55d9dc', shape: [[1, 1, 1, 1]] },
  { color: '#d2f34c', shape: [[1, 1], [1, 1]] },
  { color: '#ff668d', shape: [[0, 1, 0], [1, 1, 1]] },
  { color: '#ffb84d', shape: [[1, 0, 0], [1, 1, 1]] },
  { color: '#8e9cff', shape: [[0, 0, 1], [1, 1, 1]] },
  { color: '#bc7cff', shape: [[0, 1, 1], [1, 1, 0]] },
  { color: '#53e08c', shape: [[1, 1, 0], [0, 1, 1]] }
];
const ITEMS = {
  bomb: { symbol: 'B', label: '폭탄 아이템: 주변 한 줄을 추가로 제거합니다.' },
  bonus: { symbol: '+', label: '라인 아이템: 보너스 점수 500점을 얻습니다.' },
  slow: { symbol: 'S', label: '슬로우 아이템: 8초 동안 블록이 천천히 내려옵니다.' }
};

const boardElement = document.querySelector('#game-board');
const nextElement = document.querySelector('#next-piece');
const overlay = document.querySelector('#overlay');
const overlayTitle = document.querySelector('#overlay-title');
const startButton = document.querySelector('#start-button');
const pauseButton = document.querySelector('#pause-button');
const restartButton = document.querySelector('#restart-button');
const scoreElement = document.querySelector('#score');
const highScoreElement = document.querySelector('#high-score');
const levelElement = document.querySelector('#level');
const linesElement = document.querySelector('#lines');
const itemStatusElement = document.querySelector('#item-status');
let board = createBoard();
let currentPiece;
let nextPiece;
let score = 0;
let lines = 0;
let highScore = Number(localStorage.getItem('neon-tetris-high-score')) || 0;
let gameTimer;
let isPlaying = false;
let isPaused = false;
let slowUntil = 0;

function createBoard() { return Array.from({ length: ROWS }, () => Array(COLS).fill(null)); }
function createCells() { boardElement.innerHTML = ''; for (let i = 0; i < ROWS * COLS; i += 1) boardElement.appendChild(document.createElement('div')); }
function randomPiece() { const source = SHAPES[Math.floor(Math.random() * SHAPES.length)]; const shape = source.shape.map(row => [...row]); let item; if (Math.random() < 0.2) { const filled = []; shape.forEach((row, y) => row.forEach((value, x) => { if (value) filled.push({ x, y }); })); const target = filled[Math.floor(Math.random() * filled.length)]; item = { ...ITEMS[Object.keys(ITEMS)[Math.floor(Math.random() * Object.keys(ITEMS).length)]], type: Object.keys(ITEMS)[Math.floor(Math.random() * Object.keys(ITEMS).length)] }; const itemType = Object.keys(ITEMS).find(type => ITEMS[type].symbol === item.symbol); item.type = itemType; item.position = target; } return { color: source.color, shape, item, x: Math.floor((COLS - source.shape[0].length) / 2), y: 0 }; }
function rotate(shape) { return shape[0].map((_, column) => shape.map(row => row[column]).reverse()); }
function canMove(piece, dx = 0, dy = 0, shape = piece.shape) { return shape.every((row, y) => row.every((value, x) => !value || (piece.y + y + dy >= 0 && piece.y + y + dy < ROWS && piece.x + x + dx >= 0 && piece.x + x + dx < COLS && !board[piece.y + y + dy][piece.x + x + dx]))); }
function draw() {
  const cells = boardElement.children;
  Array.from(cells).forEach(cell => { cell.className = 'cell'; cell.style.removeProperty('--piece-color'); });
  board.forEach((row, y) => row.forEach((cell, x) => { if (cell) paint(cells[y * COLS + x], cell.color, cell.item); }));
  if (currentPiece) currentPiece.shape.forEach((row, y) => row.forEach((value, x) => { if (value && currentPiece.y + y >= 0) { const item = currentPiece.item?.position.x === x && currentPiece.item?.position.y === y ? currentPiece.item : null; paint(cells[(currentPiece.y + y) * COLS + currentPiece.x + x], currentPiece.color, item); } }));
}
function paint(cell, color, item) { cell.className = `cell filled${item ? ' item-cell' : ''}`; cell.style.setProperty('--piece-color', color); cell.textContent = item?.symbol || ''; }
function drawNext() { nextElement.innerHTML = ''; const preview = nextPiece.shape; for (let y = 0; y < 4; y += 1) for (let x = 0; x < 4; x += 1) { const cell = document.createElement('div'); cell.className = 'next-cell'; if (preview[y]?.[x]) { cell.classList.add('filled'); cell.style.setProperty('--piece-color', nextPiece.color); } nextElement.appendChild(cell); } }
function spawn() { currentPiece = nextPiece || randomPiece(); nextPiece = randomPiece(); drawNext(); if (!canMove(currentPiece)) endGame(); }
function lockPiece() { currentPiece.shape.forEach((row, y) => row.forEach((value, x) => { if (value) { const item = currentPiece.item?.position.x === x && currentPiece.item?.position.y === y ? currentPiece.item : null; board[currentPiece.y + y][currentPiece.x + x] = { color: currentPiece.color, item }; } })); clearLines(); spawn(); }
function clearLines() { const completed = board.filter(row => row.every(Boolean)); const itemTypes = completed.flatMap(row => row.map(cell => cell.item?.type).filter(Boolean)); const remaining = board.filter(row => row.some(cell => !cell)); const cleared = ROWS - remaining.length; while (remaining.length < ROWS) remaining.unshift(Array(COLS).fill(null)); board = remaining; if (cleared) { lines += cleared; score += [0, 100, 300, 500, 800][cleared] * getLevel(); applyItems(itemTypes); updateStats(); } }
function applyItems(itemTypes) { if (itemTypes.includes('bonus')) score += 500; if (itemTypes.includes('bomb')) { const rowIndex = board.findIndex(row => row.some(Boolean)); if (rowIndex >= 0) board.splice(rowIndex, 1); board.unshift(Array(COLS).fill(null)); } if (itemTypes.includes('slow')) { slowUntil = Date.now() + 8000; itemStatusElement.textContent = ITEMS.slow.label; setTimer(); } if (!itemTypes.length) itemStatusElement.textContent = '아이템 없음'; else if (!itemTypes.includes('slow')) itemStatusElement.textContent = itemTypes.map(type => ITEMS[type].label).join(' '); }
function getLevel() { return Math.floor(lines / 10) + 1; }
function updateStats() { scoreElement.textContent = String(score).padStart(6, '0'); linesElement.textContent = String(lines).padStart(3, '0'); levelElement.textContent = String(getLevel()).padStart(2, '0'); highScoreElement.textContent = String(highScore).padStart(6, '0'); }
function setTimer() { clearInterval(gameTimer); const speed = Math.max(90, 700 - (getLevel() - 1) * 55); gameTimer = setInterval(() => moveDown(), Date.now() < slowUntil ? speed * 2 : speed); }
function moveDown() { if (!isPlaying || isPaused) return; if (canMove(currentPiece, 0, 1)) currentPiece.y += 1; else lockPiece(); draw(); }
function moveSide(direction) { if (isPlaying && !isPaused && canMove(currentPiece, direction)) { currentPiece.x += direction; draw(); } }
function rotatePiece() { if (!isPlaying || isPaused) return; const rotated = rotate(currentPiece.shape); for (const offset of [0, -1, 1, -2, 2]) if (canMove(currentPiece, offset, 0, rotated)) { currentPiece.x += offset; currentPiece.shape = rotated; draw(); break; } }
function hardDrop() { if (!isPlaying || isPaused) return; let distance = 0; while (canMove(currentPiece, 0, 1)) { currentPiece.y += 1; distance += 1; } score += distance * 2; lockPiece(); updateStats(); draw(); }
function showOverlay(title, buttonText) { overlayTitle.textContent = title; startButton.textContent = buttonText; overlay.classList.remove('hidden'); }
function startGame() { board = createBoard(); score = 0; lines = 0; slowUntil = 0; itemStatusElement.textContent = '아이템 없음'; isPlaying = true; isPaused = false; pauseButton.disabled = false; pauseButton.textContent = '일시정지'; overlay.classList.add('hidden'); nextPiece = randomPiece(); spawn(); updateStats(); setTimer(); draw(); }
function togglePause() { if (!isPlaying) return; isPaused = !isPaused; pauseButton.textContent = isPaused ? '계속하기' : '일시정지'; if (isPaused) showOverlay('잠시 멈췄습니다', '계속하기'); else overlay.classList.add('hidden'); }
function endGame() { isPlaying = false; isPaused = false; clearInterval(gameTimer); highScore = Math.max(highScore, score); localStorage.setItem('neon-tetris-high-score', highScore); updateStats(); pauseButton.disabled = true; showOverlay('GAME OVER', '다시 시작'); }
function handleAction(action) { ({ left: () => moveSide(-1), right: () => moveSide(1), down: moveDown, rotate: rotatePiece, drop: hardDrop }[action])(); }

createCells(); highScoreElement.textContent = String(highScore).padStart(6, '0'); nextPiece = randomPiece(); drawNext();
startButton.addEventListener('click', () => isPaused ? togglePause() : startGame());
pauseButton.addEventListener('click', togglePause);
restartButton.addEventListener('click', startGame);
document.addEventListener('keydown', event => { const actions = { ArrowLeft: 'left', ArrowRight: 'right', ArrowDown: 'down', ArrowUp: 'rotate', ' ': 'drop' }; if (event.key === 'p' || event.key === 'P') togglePause(); else if (actions[event.key]) { event.preventDefault(); handleAction(actions[event.key]); } });
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => handleAction(button.dataset.action)));
