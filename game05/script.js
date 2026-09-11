const codeSamples = {
  html: { label: 'HTML을 편집해보세요', hint: 'h1의 글자를 바꿔보세요.', value: '<h1>나의 첫 웹페이지</h1>\n<p>코드를 바꾸고 실행해보세요.</p>\n<button>인사하기</button>' },
  css: { label: 'CSS를 편집해보세요', hint: '버튼의 색을 바꿔보세요.', value: 'h1 { color: #6d8df7; }\np { color: #687485; }\nbutton {\n  background: #ef806f;\n  color: white;\n  padding: 10px 16px;\n  border: 0;\n}' },
  js: { label: 'JavaScript를 편집해보세요', hint: '버튼을 눌렀을 때의 문장을 바꿔보세요.', value: "const button = document.querySelector('button');\nbutton.onclick = () => {\n  document.querySelector('h1').textContent = '반가워요!';\n};" }
};
let activeTab = 'html';
const editor = document.querySelector('#code-editor');
const preview = document.querySelector('#preview');
const editorLabel = document.querySelector('#editor-label');
const editorHint = document.querySelector('#editor-hint');
const progressValue = document.querySelector('#progress-value');
const progressBar = document.querySelector('#progress-bar');

function renderPreview() {
  const html = activeTab === 'html' ? editor.value : codeSamples.html.value;
  const css = activeTab === 'css' ? editor.value : codeSamples.css.value;
  const js = activeTab === 'js' ? editor.value : codeSamples.js.value;
  preview.innerHTML = `<div class="preview-stage"><style>${css}</style>${html}</div>`;
  if (activeTab === 'js') {
    try { new Function('document', js)({ querySelector: (selector) => preview.querySelector(selector) }); } catch (error) { return; }
  }
  const button = preview.querySelector('button');
  if (button && activeTab !== 'js') button.addEventListener('click', () => { preview.querySelector('h1').textContent = '반가워요!'; });
}

function selectTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.editor-tab').forEach((button) => button.classList.toggle('active', button.dataset.tab === tab));
  editorLabel.textContent = codeSamples[tab].label;
  editorHint.textContent = codeSamples[tab].hint;
  editor.value = codeSamples[tab].value;
  renderPreview();
}

document.querySelectorAll('.editor-tab').forEach((button) => button.addEventListener('click', () => selectTab(button.dataset.tab)));
document.querySelector('#run-code').addEventListener('click', () => { renderPreview(); progressValue.textContent = '50%'; progressBar.style.width = '50%'; });
editor.addEventListener('input', () => { if (activeTab === 'html') renderPreview(); });

document.querySelectorAll('.quiz-options button').forEach((button) => button.addEventListener('click', () => {
  const feedback = document.querySelector('#quiz-feedback');
  document.querySelectorAll('.quiz-options button').forEach((option) => option.classList.remove('selected'));
  button.classList.add('selected');
  if (button.dataset.answer === 'js') {
    feedback.textContent = '정답이에요! JavaScript가 사용자 동작에 반응을 더합니다.';
    feedback.style.color = '#63c6af';
    progressValue.textContent = '100%'; progressBar.style.width = '100%';
  } else {
    feedback.textContent = '거의 다 왔어요. 화면의 동작은 JavaScript가 담당해요.';
    feedback.style.color = '#f4c948';
  }
}));

selectTab('html');
