/* ══════════════════════════════════════════════════════════════════════════════
   VisuAIze – Claude.ai & Google Spark Conversational Frontend
   ══════════════════════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────────────────────
let activeProvider = 'groq';
let activeJobId    = null;
let eventSource    = null;
let currentStepData= [];

// ── DOM Elements ──────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const promptTextarea       = $('promptTextarea');
const sendActionBtn        = $('sendActionBtn');
const chatForm             = $('chatForm');
const providerInput        = $('providerInput');
const imageFileInput       = $('imageFileInput');
const attachedPreviewWrap  = $('attachedPreviewWrap');
const attachedThumb        = $('attachedThumb');
const attachedName         = $('attachedName');
const removeAttachBtn      = $('removeAttachBtn');
const newChatBtn           = $('newChatBtn');
const welcomeHero          = $('welcomeHero');
const messagesContainer    = $('messagesContainer');
const chatScrollArea       = $('chatScrollArea');
const recentList           = $('recentList');
const topModelName         = $('topModelName');
const chatTitle            = $('chatTitle');

// Model Dropdown
const modelDropdownContainer = $('modelDropdownContainer');
const modelSelectBtn         = $('modelSelectBtn');
const modelPopover           = $('modelPopover');
const selectedModelLabel     = $('selectedModelLabel');
const selectedModelTag       = $('selectedModelTag');

// Mobile Sidebar
const mobileMenuBtn          = $('mobileMenuBtn');
const closeSidebarBtn        = $('closeSidebarBtn');
const sidebar                = $('sidebar');


// ── 1. Auto-resize Textarea & Send Button State ───────────────────────────────
promptTextarea.addEventListener('input', () => {
  promptTextarea.style.height = 'auto';
  promptTextarea.style.height = Math.min(promptTextarea.scrollHeight, 200) + 'px';
  sendActionBtn.disabled = !promptTextarea.value.trim();
});

promptTextarea.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendActionBtn.disabled) {
      chatForm.dispatchEvent(new Event('submit'));
    }
  }
});


// ── 2. Claude Style Model Selector Dropdown ──────────────────────────────────
modelSelectBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  modelDropdownContainer.classList.toggle('open');
});

document.addEventListener('click', (e) => {
  if (!modelDropdownContainer.contains(e.target)) {
    modelDropdownContainer.classList.remove('open');
  }
});

const MODEL_INFO = {
  groq:        { label: 'Groq',        tag: 'Fast',    cls: 'fast',  full: 'Groq Llama 3.3' },
  gemini:      { label: 'Gemini',      tag: 'Pro',     cls: 'pro',   full: 'Google Gemini 2.0 Flash' },
  huggingface: { label: 'HuggingFace', tag: 'Free',    cls: 'free',  full: 'Hugging Face Open Source' },
  ollama:      { label: 'Ollama',      tag: 'Offline', cls: 'local', full: 'Ollama 100% Offline' },
};

modelPopover.querySelectorAll('.model-option-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.stopPropagation();
    const p = item.dataset.provider;
    activeProvider = p;
    providerInput.value = p;

    // Active state in popover
    modelPopover.querySelectorAll('.model-option-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    // Update Checkmarks
    modelPopover.querySelectorAll('.check-icon').forEach(c => c.textContent = '');
    $(`check-${p}`).textContent = '✓';

    // Update Button Display
    const info = MODEL_INFO[p] || MODEL_INFO.groq;
    selectedModelLabel.textContent = info.label;
    selectedModelTag.textContent   = info.tag;
    selectedModelTag.className     = `model-badge-tag ${info.cls}`;
    topModelName.textContent       = info.full;

    modelDropdownContainer.classList.remove('open');
  });
});


// ── 3. Image Attachment ───────────────────────────────────────────────────────
imageFileInput.addEventListener('change', () => {
  if (!imageFileInput.files[0]) return;
  const file = imageFileInput.files[0];
  const reader = new FileReader();
  reader.onload = e => {
    attachedThumb.src = e.target.result;
    attachedName.textContent = file.name;
    attachedPreviewWrap.style.display = 'block';
  };
  reader.readAsDataURL(file);
});

removeAttachBtn.addEventListener('click', () => {
  imageFileInput.value = '';
  attachedPreviewWrap.style.display = 'none';
  attachedThumb.src = '';
});


// ── 4. Suggestion Chips ───────────────────────────────────────────────────────
document.querySelectorAll('.prompt-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    promptTextarea.value = chip.dataset.prompt;
    promptTextarea.style.height = 'auto';
    promptTextarea.style.height = Math.min(promptTextarea.scrollHeight, 200) + 'px';
    sendActionBtn.disabled = false;
    promptTextarea.focus();
  });
});


// ── 5. Mobile Sidebar Toggle ──────────────────────────────────────────────────
mobileMenuBtn?.addEventListener('click', () => sidebar.classList.add('open'));
closeSidebarBtn?.addEventListener('click', () => sidebar.classList.remove('open'));


// ── 6. New Video / New Chat ───────────────────────────────────────────────────
function resetToNewChat() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  welcomeHero.style.display = 'block';
  messagesContainer.innerHTML = '';
  promptTextarea.value = '';
  promptTextarea.style.height = 'auto';
  sendActionBtn.disabled = true;
  chatTitle.textContent = 'New Video Generation';
  imageFileInput.value = '';
  attachedPreviewWrap.style.display = 'none';
  promptTextarea.focus();
}

newChatBtn.addEventListener('click', resetToNewChat);
$('navChats')?.addEventListener('click', (e) => { e.preventDefault(); resetToNewChat(); });


// ── 7. Append User Bubble ─────────────────────────────────────────────────────
function appendUserMessage(text, imgDataUrl) {
  welcomeHero.style.display = 'none';

  const row = document.createElement('div');
  row.className = 'user-msg-row';

  let imgHtml = '';
  if (imgDataUrl) {
    imgHtml = `<img src="${imgDataUrl}" class="user-attached-thumb" alt="attached"/>`;
  }

  row.innerHTML = `
    <div class="user-bubble">
      ${imgHtml}
      <div>${escapeHtml(text)}</div>
    </div>
  `;

  messagesContainer.appendChild(row);
  scrollToBottom();
}


// ── 8. Append Assistant Response Card with Thinking Accordion ─────────────────
function appendAssistantCard(jobId) {
  const row = document.createElement('div');
  row.className = 'assistant-msg-row';
  row.id = `assistant-row-${jobId}`;

  row.innerHTML = `
    <div class="assistant-avatar">✦</div>
    <div class="assistant-body" id="body-${jobId}">

      <!-- Claude Style Collapsible Thinking Box -->
      <div class="thinking-accordion active" id="thinking-${jobId}">
        <div class="thinking-header" onclick="toggleThinking('${jobId}')">
          <div class="thinking-header-left">
            <div class="thinking-spinner" id="spinner-${jobId}"></div>
            <span class="thinking-check" id="checkDone-${jobId}" style="display:none">✓</span>
            <span class="thinking-title" id="thinkTitle-${jobId}">Running video creation pipeline...</span>
          </div>
          <div class="thinking-header-right">
            <span class="thinking-pct" id="thinkPct-${jobId}">0%</span>
            <svg class="thinking-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
          </div>
        </div>

        <div class="thinking-content">
          <!-- Timeline Steps -->
          <div class="timeline-step active" id="step-1-${jobId}">
            <div class="timeline-icon">🧠</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 1: AI Scripting</span>
              <span class="timeline-step-detail" id="detail-1-${jobId}">Deconstructing question into 6 structured steps...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-2-${jobId}">
            <div class="timeline-icon">🎨</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 2: Realistic Visuals</span>
              <span class="timeline-step-detail" id="detail-2-${jobId}">Generating 1080p Flux presentation slides via Pollinations...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-3-${jobId}">
            <div class="timeline-icon">🎙️</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 3: Voiceover Synthesis</span>
              <span class="timeline-step-detail" id="detail-3-${jobId}">Recording studio audio narrations for each step...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-4-${jobId}">
            <div class="timeline-icon">🎬</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 4: Video Engine & Assembly</span>
              <span class="timeline-step-detail" id="detail-4-${jobId}">Compositing Ken Burns zoom, subtitles & rendering MP4...</span>
            </div>
          </div>

          <!-- Progress Track -->
          <div class="thinking-progress-track">
            <div class="thinking-progress-fill" id="fill-${jobId}"></div>
          </div>
        </div>
      </div>

      <!-- Container where final Video Artifact will be inserted -->
      <div id="artifact-container-${jobId}"></div>

    </div>
  `;

  messagesContainer.appendChild(row);
  scrollToBottom();
}

window.toggleThinking = function(jobId) {
  const acc = $(`thinking-${jobId}`);
  if (acc) acc.classList.toggle('collapsed');
};


// ── 9. Embed Final Video Player Artifact ──────────────────────────────────────
function embedVideoArtifact(jobId, data) {
  const container = $(`artifact-container-${jobId}`);
  if (!container) return;

  // Mark thinking as finished
  const spinner   = $(`spinner-${jobId}`);
  const checkDone = $(`checkDone-${jobId}`);
  const thinkTitle= $(`thinkTitle-${jobId}`);
  const thinkPct  = $(`thinkPct-${jobId}`);
  const fill      = $(`fill-${jobId}`);

  if (spinner)   spinner.style.display   = 'none';
  if (checkDone) checkDone.style.display = 'inline';
  if (thinkTitle)thinkTitle.textContent  = 'Ran 4 pipeline passes · Finished in ~45s';
  if (thinkPct)  thinkPct.textContent   = '100%';
  if (fill)      fill.style.width        = '100%';

  for (let i = 1; i <= 4; i++) {
    const el = $(`step-${i}-${jobId}`);
    if (el) {
      el.classList.remove('active');
      el.classList.add('done');
    }
  }

  // Collapse thinking after a moment
  setTimeout(() => {
    const acc = $(`thinking-${jobId}`);
    if (acc) acc.classList.add('collapsed');
  }, 1200);

  // Video URL
  const videoUrl  = `/video/${data.filename}`;
  const cleanTitle = data.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');

  chatTitle.textContent = cleanTitle;

  const card = document.createElement('div');
  card.className = 'video-artifact-card';
  card.innerHTML = `
    <div class="artifact-header">
      <div class="artifact-title-wrap">
        <span class="artifact-badge">Ready · 1080p HD</span>
        <span class="artifact-name">${escapeHtml(cleanTitle)}</span>
      </div>
      <div class="artifact-meta-stats">${data.steps} Steps · ${data.size_mb} MB</div>
    </div>

    <!-- 16:9 Video Player -->
    <div class="player-screen">
      <video controls autoplay playsinline preload="metadata">
        <source src="${videoUrl}" type="video/mp4"/>
        Your browser does not support the video tag.
      </video>
    </div>

    <!-- Actions Toolbar below Video -->
    <div class="artifact-actions">
      <div class="action-btns-left">
        <a href="${videoUrl}" download="${data.filename}" class="btn-download-primary">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Download MP4</span>
        </a>
        <button class="btn-secondary" onclick="copyVideoLink('${videoUrl}')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Copy Link</span>
        </button>
        <button class="btn-secondary" onclick="resetToNewChat()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span>New Video</span>
        </button>
      </div>
    </div>
  `;

  container.appendChild(card);
  scrollToBottom();
  loadRecentVideos();
}

window.copyVideoLink = function(url) {
  const fullUrl = window.location.origin + url;
  navigator.clipboard.writeText(fullUrl).then(() => {
    alert('Video link copied to clipboard!');
  }).catch(() => {});
};


// ── 10. SSE Progress Listener ─────────────────────────────────────────────────
function startProgressListener(jobId) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`/api/progress/${jobId}`);

  eventSource.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.type === 'ping') return;

    if (d.type === 'progress') {
      const fill      = $(`fill-${jobId}`);
      const thinkPct  = $(`thinkPct-${jobId}`);
      const thinkTitle= $(`thinkTitle-${jobId}`);

      if (fill) fill.style.width = d.pct + '%';
      if (thinkPct) thinkPct.textContent = d.pct + '%';
      if (thinkTitle) thinkTitle.textContent = d.message || 'Processing...';

      // Update Phase statuses
      for (let p = 1; p < d.phase; p++) {
        const el = $(`step-${p}-${jobId}`);
        if (el) {
          el.classList.remove('active');
          el.classList.add('done');
        }
      }
      const curr = $(`step-${d.phase}-${jobId}`);
      if (curr) {
        curr.classList.add('active');
        const det = $(`detail-${d.phase}-${jobId}`);
        if (det && d.detail) det.textContent = d.detail;
      }
    }

    if (d.type === 'done') {
      eventSource.close();
      embedVideoArtifact(jobId, d);
    }

    if (d.type === 'error') {
      eventSource.close();
      const container = $(`artifact-container-${jobId}`);
      if (container) {
        container.innerHTML = `
          <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:14px 18px;color:#fca5a5;font-size:0.88rem;">
            <b>⚠️ Generation Error:</b> ${escapeHtml(d.error || 'Pipeline encountered an issue.')}
          </div>
        `;
      }
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };
}


// ── 11. Form Submit (Handle Prompt Submission) ────────────────────────────────
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = promptTextarea.value.trim();
  if (!q) return;

  let imgPreviewData = null;
  if (imageFileInput.files[0]) {
    imgPreviewData = attachedThumb.src;
  }

  // 1. Append user prompt bubble
  appendUserMessage(q, imgPreviewData);

  // Clear inputs
  promptTextarea.value = '';
  promptTextarea.style.height = 'auto';
  sendActionBtn.disabled = true;
  attachedPreviewWrap.style.display = 'none';

  // 2. Prepare FormData
  const fd = new FormData(chatForm);
  fd.set('provider', activeProvider);
  fd.set('question', q);

  try {
    const res  = await fetch('/api/generate', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || 'Server error');

    activeJobId = json.job_id;

    // 3. Append assistant response card with live thinking timeline
    appendAssistantCard(activeJobId);

    // 4. Start listening to SSE stream
    startProgressListener(activeJobId);

  } catch (err) {
    const errRow = document.createElement('div');
    errRow.className = 'assistant-msg-row';
    errRow.innerHTML = `
      <div class="assistant-avatar">✦</div>
      <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:14px 18px;color:#fca5a5;font-size:0.88rem;">
        <b>⚠️ Failed to start:</b> ${escapeHtml(err.message)}
      </div>
    `;
    messagesContainer.appendChild(errRow);
    scrollToBottom();
  }
});


// ── 12. Recent Videos Sidebar ─────────────────────────────────────────────────
async function loadRecentVideos() {
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
      const item  = document.createElement('a');
      item.className = 'recent-item';
      item.href   = `/video/${v.filename}`;
      item.target = '_blank';
      item.innerHTML = `
        <span class="recent-item-icon">▶</span>
        <span class="recent-item-name" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
      `;
      recentList.appendChild(item);
    });
  } catch (e) {
    console.error('Failed to load recent videos', e);
  }
}

$('refreshRecentBtn')?.addEventListener('click', loadRecentVideos);


// ── 13. Helpers ───────────────────────────────────────────────────────────────
function scrollToBottom() {
  setTimeout(() => {
    chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
  }, 50);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}


// ── Init ──────────────────────────────────────────────────────────────────────
loadRecentVideos();
