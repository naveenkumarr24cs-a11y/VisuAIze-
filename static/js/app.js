/* VisuAIze – Frontend Logic (Claude-like UI)
   Handles: provider select, chip clicks, auto-resize textarea,
            image attach, form submit, SSE progress, result, gallery
*/

// ── State ─────────────────────────────────────────────────────────────────
let activeProvider = 'groq';
let eventSource    = null;

// ── DOM ───────────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const questionInput  = $('questionInput');
const sendBtn        = $('sendBtn');
const generateForm   = $('generateForm');
const providerInput  = $('providerInput');
const recentList     = $('recentList');
const fileInput      = $('fileInput');
const attachedImgWrap= $('attachedImgWrap');
const attachedImg    = $('attachedImg');
const removeAttach   = $('removeAttach');
const newBtn         = $('newBtn');

// Views
const homeView     = $('homeView');
const progressView = $('progressView');
const resultView   = $('resultView');
const errorView    = $('errorView');

// ── Auto-resize textarea ───────────────────────────────────────────────────
questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = Math.min(questionInput.scrollHeight, 180) + 'px';
  sendBtn.disabled = !questionInput.value.trim();
});
questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) generateForm.dispatchEvent(new Event('submit'));
  }
});

// ── Provider selection (Claude Style Dropdown) ───────────────────────────────
const modelSelectorWrap = $('modelSelectorWrap');
const modelSelectorBtn  = $('modelSelectorBtn');
const modelDropdown     = $('modelDropdown');
const currentModelName  = $('currentModelName');
const modelBadge        = document.querySelector('.model-selector-btn .model-badge');

// Toggle dropdown
modelSelectorBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  modelDropdown.classList.toggle('show');
});

// Close when clicking outside
document.addEventListener('click', (e) => {
  if (!modelSelectorWrap.contains(e.target)) {
    modelDropdown.classList.remove('show');
  }
});

// Select option
modelDropdown.querySelectorAll('.model-option').forEach(item => {
  item.addEventListener('click', (e) => {
    e.stopPropagation();
    const p = item.dataset.provider;
    activeProvider = p;
    providerInput.value = p;

    // Update active class
    modelDropdown.querySelectorAll('.model-option').forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    // Update checkmarks
    modelDropdown.querySelectorAll('.model-opt-check').forEach(c => c.textContent = '');
    $(`check-${p}`).textContent = '✓';

    // Update button display
    const nameEl = item.querySelector('.model-opt-name');
    currentModelName.textContent = nameEl.childNodes[0].textContent.trim();
    
    // Copy the badge over if it exists
    const badgeEl = item.querySelector('.model-opt-badge');
    if (badgeEl) {
      modelBadge.textContent = badgeEl.textContent;
      modelBadge.className = 'model-badge ' + (badgeEl.classList.contains('pro') ? 'pro' : 
                                              badgeEl.classList.contains('local') ? 'local' : '');
    }

    modelDropdown.classList.remove('show');
  });
});


// ── Suggestion chips ───────────────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    questionInput.value = chip.dataset.text;
    questionInput.style.height = 'auto';
    questionInput.style.height = Math.min(questionInput.scrollHeight, 180) + 'px';
    sendBtn.disabled = false;
    questionInput.focus();
  });
});

// ── Image attach ───────────────────────────────────────────────────────────
fileInput.addEventListener('change', () => {
  if (!fileInput.files[0]) return;
  const reader = new FileReader();
  reader.onload = e => {
    attachedImg.src = e.target.result;
    attachedImgWrap.style.display = 'inline-block';
  };
  reader.readAsDataURL(fileInput.files[0]);
});
removeAttach.addEventListener('click', () => {
  fileInput.value = '';
  attachedImgWrap.style.display = 'none';
  attachedImg.src = '';
});

// ── New generation ─────────────────────────────────────────────────────────
function goHome() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  showView('home');
  questionInput.value = '';
  questionInput.style.height = 'auto';
  sendBtn.disabled = true;
}
newBtn.addEventListener('click', goHome);
$('anotherBtn')?.addEventListener('click', goHome);
$('retryBtn')?.addEventListener('click', goHome);

// Mobile sidebar
const menuBtn = $('menuBtn');
const sidebar = document.querySelector('.sidebar');
menuBtn?.addEventListener('click', () => sidebar.classList.toggle('open'));

// ── View switcher ──────────────────────────────────────────────────────────
function showView(name) {
  homeView.style.display     = name === 'home'     ? 'flex' : 'none';
  progressView.style.display = name === 'progress' ? 'flex' : 'none';
  resultView.style.display   = name === 'result'   ? 'flex' : 'none';
  errorView.style.display    = name === 'error'    ? 'flex' : 'none';
}

// ── Phase helpers ──────────────────────────────────────────────────────────
function setPhaseBox(n, state, label) {
  const box  = $(`pb${n}`);
  const stat = $(`pbs${n}`);
  box.classList.remove('active', 'done');
  if (state === 'active') { box.classList.add('active'); stat.textContent = 'Running...'; }
  else if (state === 'done') { box.classList.add('done'); stat.textContent = '✓ Done'; }
  else { stat.textContent = label || 'Pending'; }
}
function resetPhases() {
  for (let i = 1; i <= 4; i++) setPhaseBox(i, 'pending', 'Pending');
}

// ── SSE progress ───────────────────────────────────────────────────────────
function listenProgress(jobId) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`/api/progress/${jobId}`);

  eventSource.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.type === 'ping') return;

    if (d.type === 'progress') {
      $('progressMsg').textContent = d.message  || 'Processing...';
      $('progressSub').textContent = d.detail   || '';
      $('progressFill').style.width = d.pct + '%';
      $('progressPct').textContent  = d.pct + '%';
      for (let i = 1; i < d.phase; i++) setPhaseBox(i, 'done');
      setPhaseBox(d.phase, 'active');
    }

    if (d.type === 'done') {
      eventSource.close();
      $('progressFill').style.width = '100%';
      $('progressPct').textContent  = '100%';
      for (let i = 1; i <= 4; i++) setPhaseBox(i, 'done');
      setTimeout(() => showResult(d), 500);
    }

    if (d.type === 'error') {
      eventSource.close();
      $('errorBody').textContent = d.error || 'Unknown error occurred.';
      showView('error');
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    $('errorBody').textContent = 'Connection lost. The server may have stopped. Please refresh and try again.';
    showView('error');
  };
}

// ── Show result ────────────────────────────────────────────────────────────
function showResult(data) {
  const src = `/video/${data.filename}`;
  const video = $('resultVideo');
  video.src = src;
  $('dlBtn').href     = src;
  $('dlBtn').download = data.filename;

  const label = data.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');
  $('resultTitle').textContent = label;
  $('resultInfo').textContent  = `${data.steps} steps · ${data.size_mb} MB · Ready to play & download`;
  showView('result');
  video.play().catch(() => {});
  loadRecent();
}

// ── Form submit ────────────────────────────────────────────────────────────
generateForm.addEventListener('submit', async e => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if (!q) return;

  resetPhases();
  $('progressTopic').textContent = `"${q}"`;
  $('progressMsg').textContent   = 'Starting pipeline...';
  $('progressSub').textContent   = 'Please wait, this takes 2-3 minutes';
  $('progressFill').style.width  = '0%';
  $('progressPct').textContent   = '0%';
  showView('progress');

  const fd = new FormData(generateForm);
  fd.set('provider', activeProvider);

  try {
    const res  = await fetch('/api/generate', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || 'Server error');
    listenProgress(json.job_id);
  } catch (err) {
    $('errorBody').textContent = err.message;
    showView('error');
  }
});

// ── Recent videos (sidebar) ────────────────────────────────────────────────
async function loadRecent() {
  try {
    const res  = await fetch('/api/videos');
    const list = await res.json();

    if (!list.length) {
      recentList.innerHTML = '<div class="recent-empty">No videos yet</div>';
      return;
    }
    recentList.innerHTML = '';
    list.forEach(v => {
      const label = v.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');
      const item = document.createElement('a');
      item.className = 'recent-item';
      item.href   = `/video/${v.filename}`;
      item.target = '_blank';
      item.innerHTML = `<span class="recent-item-icon">▶</span><span class="recent-item-name">${label}</span>`;
      recentList.appendChild(item);
    });
  } catch { /* silent */ }
}

// ── Init ───────────────────────────────────────────────────────────────────
showView('home');
loadRecent();
