/* ══════════════════════════════════════════════════════════════════════════════
   VisuAIze – Complete Functional Conversational Engine
   Features:
     • Sidebar Collapse & Toggle (⌘B / Ctrl+B)
     • Full Chat Session Restoration (Claude/ChatGPT/Gemini Style)
     • Voice input with Web Speech API
     • 5 Model Selector: Groq, Gemini, Llama 3.1, Mistral, Ollama
     • Interactive Video Player with 0.75x - 2.0x Speed Buttons & Duration
     • Working Share Modal & Social Links
     • 100% Smooth Auto-Scroll & Manual Scrolling
   ══════════════════════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────────────────────
let activeProvider   = 'groq';
let activeJobId      = null;
let eventSource      = null;
let speechRecognizer = null;
let isRecording      = false;
let currentVideoData = null;

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
const micBtn               = $('micBtn');
const shareBtn             = $('shareBtn');

// Share Modal
const shareModalBackdrop   = $('shareModalBackdrop');
const closeShareModalBtn   = $('closeShareModalBtn');
const shareLinkInput       = $('shareLinkInput');
const copyShareLinkBtn     = $('copyShareLinkBtn');
const shareWhatsapp        = $('shareWhatsapp');
const shareTwitter         = $('shareTwitter');
const shareTelegram        = $('shareTelegram');

// Model Dropdown
const modelDropdownContainer = $('modelDropdownContainer');
const modelSelectBtn         = $('modelSelectBtn');
const modelPopover           = $('modelPopover');
const selectedModelLabel     = $('selectedModelLabel');
const selectedModelTag       = $('selectedModelTag');

// Sidebar Toggle
const sidebarToggleBtn       = $('sidebarToggleBtn');
const collapseSidebarBtn     = $('collapseSidebarBtn');
const sidebar                = $('sidebar');
const appContainer           = $('appContainer');


// Theme Switcher Elements
const themeToggleBtn = $('themeToggleBtn');
const themeIconSun   = $('themeIconSun');
const themeIconMoon  = $('themeIconMoon');
const themeLabel     = $('themeLabel');

function applyTheme(theme) {
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    if (themeIconSun)  themeIconSun.style.display  = 'none';
    if (themeIconMoon) themeIconMoon.style.display = 'inline-block';
    if (themeLabel)    themeLabel.textContent      = 'Dark';
    localStorage.setItem('visuaize-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (themeIconSun)  themeIconSun.style.display  = 'inline-block';
    if (themeIconMoon) themeIconMoon.style.display = 'none';
    if (themeLabel)    themeLabel.textContent      = 'Light';
    localStorage.setItem('visuaize-theme', 'dark');
  }
}

// Check saved theme or system preference
const savedTheme = localStorage.getItem('visuaize-theme') || 'dark';
applyTheme(savedTheme);

themeToggleBtn?.addEventListener('click', () => {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  applyTheme(isLight ? 'dark' : 'light');
});


// ── 1. Toggle Sidebar (Claude/ChatGPT Style) ──────────────────────────────────
function toggleSidebar() {
  sidebar.classList.toggle('collapsed');
}

sidebarToggleBtn?.addEventListener('click', toggleSidebar);
collapseSidebarBtn?.addEventListener('click', toggleSidebar);

document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    toggleSidebar();
  }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    resetToNewChat();
  }
});


// ── 2. Auto-resize Textarea & Send Button State ───────────────────────────────
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


// ── 3. Working Voice Input (Web Speech Recognition) ───────────────────────────
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Speech recognition not supported in this browser.');
    return null;
  }

  const rec = new SpeechRecognition();
  rec.continuous     = false;
  rec.interimResults = true;
  rec.lang           = 'en-US';

  rec.onstart = () => {
    isRecording = true;
    micBtn.classList.add('listening');
    promptTextarea.placeholder = 'Listening... Speak your tutorial question now...';
  };

  rec.onresult = (e) => {
    let transcript = '';
    for (let i = e.resultIndex; i < e.results.length; ++i) {
      transcript += e.results[i][0].transcript;
    }
    if (transcript) {
      promptTextarea.value = transcript;
      promptTextarea.style.height = 'auto';
      promptTextarea.style.height = Math.min(promptTextarea.scrollHeight, 200) + 'px';
      sendActionBtn.disabled = false;
    }
  };

  rec.onerror = (err) => {
    console.error('Speech recognition error:', err);
    stopRecording();
  };

  rec.onend = () => {
    stopRecording();
  };

  return rec;
}

function stopRecording() {
  isRecording = false;
  micBtn.classList.remove('listening');
  promptTextarea.placeholder = 'Reply to VisuAIze or describe a new video tutorial...';
}

micBtn?.addEventListener('click', () => {
  if (!speechRecognizer) {
    speechRecognizer = initSpeechRecognition();
  }

  if (!speechRecognizer) {
    alert('Voice input is supported in Google Chrome, Microsoft Edge, and Safari. Please type your prompt.');
    return;
  }

  if (isRecording) {
    speechRecognizer.stop();
  } else {
    try {
      speechRecognizer.start();
    } catch (e) {
      speechRecognizer.stop();
    }
  }
});


// ── 4. Working Share Modal & Social Links ─────────────────────────────────────
function openShareModal(videoUrl, title) {
  const fullUrl = window.location.origin + (videoUrl || '');
  shareLinkInput.value = fullUrl;

  const encodedTitle = encodeURIComponent(`Check out this step-by-step AI video: "${title || 'VisuAIze Video'}"`);
  const encodedUrl   = encodeURIComponent(fullUrl);

  shareWhatsapp.href = `https://api.whatsapp.com/send?text=${encodedTitle}%20${encodedUrl}`;
  shareTwitter.href  = `https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`;
  shareTelegram.href = `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`;

  shareModalBackdrop.style.display = 'flex';
}

shareBtn?.addEventListener('click', () => {
  if (currentVideoData) {
    openShareModal(`/video/${currentVideoData.filename}`, currentVideoData.title);
  } else {
    openShareModal('', 'VisuAIze – AI Video Generator');
  }
});

closeShareModalBtn?.addEventListener('click', () => {
  shareModalBackdrop.style.display = 'none';
});

shareModalBackdrop?.addEventListener('click', (e) => {
  if (e.target === shareModalBackdrop) {
    shareModalBackdrop.style.display = 'none';
  }
});

copyShareLinkBtn?.addEventListener('click', () => {
  shareLinkInput.select();
  navigator.clipboard.writeText(shareLinkInput.value).then(() => {
    copyShareLinkBtn.textContent = '✓ Copied!';
    setTimeout(() => { copyShareLinkBtn.textContent = 'Copy'; }, 2000);
  });
});


// ── 5. 5-Model Selector Dropdown ──────────────────────────────────────────────
modelSelectBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  modelDropdownContainer.classList.toggle('open');
});

document.addEventListener('click', (e) => {
  if (!modelDropdownContainer?.contains(e.target)) {
    modelDropdownContainer?.classList.remove('open');
  }
});

const MODEL_MAP = {
  groq:        { label: 'Groq',        tag: 'Fast',    cls: 'fast',  full: 'Groq (Llama 3.3)' },
  gemini:      { label: 'Gemini',      tag: 'Pro',     cls: 'pro',   full: 'Google Gemini' },
  llama31:     { label: 'Llama 3.1',   tag: 'Open',    cls: 'open',  full: 'Llama 3.1' },
  mistral:     { label: 'Mistral',     tag: 'Smart',   cls: 'fast',  full: 'Mistral' },
  ollama:      { label: 'Ollama',      tag: 'Offline', cls: 'local', full: 'Ollama Local' },
};

modelPopover?.querySelectorAll('.model-option-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.stopPropagation();
    const p = item.dataset.provider;
    activeProvider = p;
    providerInput.value = p;

    modelPopover.querySelectorAll('.model-option-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    modelPopover.querySelectorAll('.check-icon').forEach(c => c.textContent = '');
    const checkEl = $(`check-${p}`);
    if (checkEl) checkEl.textContent = '✓';

    const info = MODEL_MAP[p] || MODEL_MAP.groq;
    selectedModelLabel.textContent = info.label;
    selectedModelTag.textContent   = info.tag;
    selectedModelTag.className     = `model-badge-tag ${info.cls}`;
    topModelName.textContent       = info.full;

    modelDropdownContainer.classList.remove('open');
  });
});


// ── 6. Image Attachment ───────────────────────────────────────────────────────
imageFileInput?.addEventListener('change', () => {
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

removeAttachBtn?.addEventListener('click', () => {
  imageFileInput.value = '';
  attachedPreviewWrap.style.display = 'none';
  attachedThumb.src = '';
});


// ── 7. Suggestion Chips ───────────────────────────────────────────────────────
document.querySelectorAll('.prompt-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    promptTextarea.value = chip.dataset.prompt;
    promptTextarea.style.height = 'auto';
    promptTextarea.style.height = Math.min(promptTextarea.scrollHeight, 200) + 'px';
    sendActionBtn.disabled = false;
    promptTextarea.focus();
  });
});


// ── 8. New Video Reset ────────────────────────────────────────────────────────
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
  document.querySelectorAll('.recent-item').forEach(i => i.classList.remove('active'));
  promptTextarea.focus();
}

newChatBtn?.addEventListener('click', resetToNewChat);
$('navChats')?.addEventListener('click', (e) => { e.preventDefault(); resetToNewChat(); });


// ── 9. Append User Message ────────────────────────────────────────────────────
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


// ── 10. Append Assistant Thinking Card ────────────────────────────────────────
function appendAssistantCard(jobId) {
  const row = document.createElement('div');
  row.className = 'assistant-msg-row';
  row.id = `assistant-row-${jobId}`;

  row.innerHTML = `
    <div class="assistant-avatar">
      <img src="/static/img/workflow_logo.png" class="workflow-avatar-img" alt="Workflow Logo"/>
    </div>
    <div class="assistant-body" id="body-${jobId}">

      <!-- Claude Style Collapsible Thinking Box -->
      <div class="thinking-accordion active" id="thinking-${jobId}">
        <div class="thinking-header" onclick="toggleThinking('${jobId}')">
          <div class="thinking-header-left">
            <div class="thinking-spinner" id="spinner-${jobId}"></div>
            <span class="thinking-check" id="checkDone-${jobId}" style="display:none">✓</span>
            <span class="thinking-title" id="thinkTitle-${jobId}">Running ultra-fast Google Flow pipeline...</span>
          </div>
          <div class="thinking-header-right">
            <span class="thinking-pct" id="thinkPct-${jobId}">0%</span>
            <svg class="thinking-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
          </div>
        </div>

        <div class="thinking-content">
          <div class="timeline-step active" id="step-1-${jobId}">
            <div class="timeline-icon">🧠</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 1: AI Scripting</span>
              <span class="timeline-step-detail" id="detail-1-${jobId}">Deconstructing question into structured steps...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-2-${jobId}">
            <div class="timeline-icon">🎨</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 2: Realistic Google Flow Visuals (Parallel)</span>
              <span class="timeline-step-detail" id="detail-2-${jobId}">Generating 1080p Flux visual slides via Pollinations & Flow engine...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-3-${jobId}">
            <div class="timeline-icon">🎙️</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 3: Studio Voiceover (Synchronized)</span>
              <span class="timeline-step-detail" id="detail-3-${jobId}">Recording human audio narrations for each step...</span>
            </div>
          </div>

          <div class="timeline-step" id="step-4-${jobId}">
            <div class="timeline-icon">🎬</div>
            <div class="timeline-text-wrap">
              <span class="timeline-step-name">Pass 4: Fast Video Assembly</span>
              <span class="timeline-step-detail" id="detail-4-${jobId}">Compositing Ken Burns animations & rendering 1080p MP4...</span>
            </div>
          </div>

          <div class="thinking-progress-track">
            <div class="thinking-progress-fill" id="fill-${jobId}"></div>
          </div>
        </div>
      </div>

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


// ── 11. Embed Final Video Player Artifact with Speed Controls & Details ────────
function embedVideoArtifact(jobId, data) {
  const container = $(`artifact-container-${jobId}`);
  if (!container) return;

  const spinner    = $(`spinner-${jobId}`);
  const checkDone  = $(`checkDone-${jobId}`);
  const thinkTitle = $(`thinkTitle-${jobId}`);
  const thinkPct   = $(`thinkPct-${jobId}`);
  const fill       = $(`fill-${jobId}`);

  if (spinner)   spinner.style.display   = 'none';
  if (checkDone) checkDone.style.display = 'inline';
  if (thinkTitle)thinkTitle.textContent  = 'Ran 4 pipeline passes · Finished in seconds';
  if (thinkPct)  thinkPct.textContent   = '100%';
  if (fill)      fill.style.width        = '100%';

  for (let i = 1; i <= 4; i++) {
    const el = $(`step-${i}-${jobId}`);
    if (el) {
      el.classList.remove('active');
      el.classList.add('done');
    }
  }

  setTimeout(() => {
    const acc = $(`thinking-${jobId}`);
    if (acc) acc.classList.add('collapsed');
  }, 1000);

  const videoUrl   = `/video/${data.filename}`;
  const cleanTitle = data.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');

  chatTitle.textContent = cleanTitle;
  currentVideoData = { filename: data.filename, title: cleanTitle };

  const estDuration = Math.round((data.steps || 6) * 5.5);

  const card = document.createElement('div');
  card.className = 'video-artifact-card';
  card.innerHTML = `
    <!-- Header with Badges -->
    <div class="artifact-header">
      <div class="artifact-title-wrap">
        <span class="artifact-badge">Ready · 1080p HD</span>
        <span class="artifact-name">${escapeHtml(cleanTitle)}</span>
      </div>
      <div class="artifact-meta-badges">
        <span class="meta-pill">⏱ ${estDuration}s Duration</span>
        <span class="meta-pill">${data.steps || 6} Steps</span>
        <span class="meta-pill">${data.size_mb || 3.5} MB</span>
      </div>
    </div>

    <!-- 16:9 Video Player -->
    <div class="player-screen">
      <video id="video-player-${jobId}" controls autoplay playsinline preload="metadata">
        <source src="${videoUrl}" type="video/mp4"/>
        Your browser does not support the video tag.
      </video>
    </div>

    <!-- Video Control Strip with Speed Buttons -->
    <div class="video-control-strip">
      <div class="speed-control-group">
        <span class="speed-label">Playback Speed:</span>
        <button class="speed-btn" onclick="setPlayerSpeed('${jobId}', 0.75, this)">0.75x</button>
        <button class="speed-btn active" onclick="setPlayerSpeed('${jobId}', 1.0, this)">1.0x</button>
        <button class="speed-btn" onclick="setPlayerSpeed('${jobId}', 1.25, this)">1.25x</button>
        <button class="speed-btn" onclick="setPlayerSpeed('${jobId}', 1.5, this)">1.5x</button>
        <button class="speed-btn" onclick="setPlayerSpeed('${jobId}', 2.0, this)">2.0x</button>
      </div>
      <div class="artifact-meta-stats">
        High-Def 1080p · AAC Stereo
      </div>
    </div>

    <!-- Actions Toolbar below Video -->
    <div class="artifact-actions">
      <div class="action-btns-left">
        <a href="${videoUrl}" download="${data.filename}" class="btn-download-primary">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Download MP4</span>
        </a>
        <button class="btn-secondary" onclick="openShareModal('${videoUrl}', '${escapeHtml(cleanTitle)}')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
          <span>Share Video</span>
        </button>
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

window.setPlayerSpeed = function(jobId, rate, btn) {
  const vid = $(`video-player-${jobId}`);
  if (vid) {
    vid.playbackRate = rate;
    const parent = btn.parentElement;
    parent.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
};

window.copyVideoLink = function(url) {
  const fullUrl = window.location.origin + url;
  navigator.clipboard.writeText(fullUrl).then(() => {
    alert('Video link copied to clipboard!');
  }).catch(() => {});
};


// ── 12. Full Chat Session Restoration (Claude/ChatGPT/Gemini Style) ───────────
async function openChatSession(sessionId) {
  try {
    const res = await fetch(`/api/session/${sessionId}`);
    if (!res.ok) throw new Error('Session not found');
    const session = await res.json();

    welcomeHero.style.display = 'none';
    messagesContainer.innerHTML = '';

    const cleanTitle = session.question || session.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');
    chatTitle.textContent = cleanTitle;

    // 1. Render User Question Bubble
    appendUserMessage(cleanTitle, null);

    // 2. Render Completed Assistant Thinking Box
    const mockJobId = `hist_${Date.now()}`;
    const row = document.createElement('div');
    row.className = 'assistant-msg-row';
    row.id = `assistant-row-${mockJobId}`;
    row.innerHTML = `
      <div class="assistant-avatar">
      <img src="/static/img/workflow_logo.png" class="workflow-avatar-img" alt="Workflow Logo"/>
    </div>
      <div class="assistant-body" id="body-${mockJobId}">
        <div class="thinking-accordion collapsed" id="thinking-${mockJobId}">
          <div class="thinking-header" onclick="toggleThinking('${mockJobId}')">
            <div class="thinking-header-left">
              <span class="thinking-check" style="display:inline">✓</span>
              <span class="thinking-title">Ran 4 pipeline passes · Completed Google Flow Tutorial</span>
            </div>
            <div class="thinking-header-right">
              <span class="thinking-pct">100%</span>
              <svg class="thinking-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
            </div>
          </div>
        </div>
        <div id="artifact-container-${mockJobId}"></div>
      </div>
    `;
    messagesContainer.appendChild(row);

    // 3. Embed the Video Artifact Card
    embedVideoArtifact(mockJobId, {
      filename: session.filename,
      steps: session.steps?.length || 7,
      size_mb: session.size_mb || 3.8
    });

    // Mark as active in recent list
    document.querySelectorAll('.recent-item').forEach(i => {
      if (i.dataset.id === sessionId || i.dataset.filename === session.filename) {
        i.classList.add('active');
      } else {
        i.classList.remove('active');
      }
    });

    scrollToBottom();

  } catch (e) {
    console.error('Failed to load chat session', e);
  }
}


// ── 13. SSE Progress Listener ─────────────────────────────────────────────────
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
      scrollToBottom();
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
      scrollToBottom();
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };
}


// ── 14. Form Submit ───────────────────────────────────────────────────────────
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = promptTextarea.value.trim();
  if (!q) return;

  let imgPreviewData = null;
  if (imageFileInput.files[0]) {
    imgPreviewData = attachedThumb.src;
  }

  appendUserMessage(q, imgPreviewData);

  promptTextarea.value = '';
  promptTextarea.style.height = 'auto';
  sendActionBtn.disabled = true;
  attachedPreviewWrap.style.display = 'none';

  const fd = new FormData(chatForm);
  fd.set('provider', activeProvider);
  fd.set('question', q);

  try {
    const res  = await fetch('/api/generate', { method: 'POST', body: fd });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || 'Server error');

    activeJobId = json.job_id;
    appendAssistantCard(activeJobId);
    startProgressListener(activeJobId);

  } catch (err) {
    const errRow = document.createElement('div');
    errRow.className = 'assistant-msg-row';
    errRow.innerHTML = `
      <div class="assistant-avatar">🐨</div>
      <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:14px 18px;color:#fca5a5;font-size:0.88rem;">
        <b>⚠️ Failed to start:</b> ${escapeHtml(err.message)}
      </div>
    `;
    messagesContainer.appendChild(errRow);
    scrollToBottom();
  }
});


// ── 15. Recent Videos & Chats Sidebar ─────────────────────────────────────────
async function loadRecentVideos() {
  try {
    const res  = await fetch('/api/history');
    const list = await res.json();

    if (!list.length) {
      recentList.innerHTML = '<div class="recent-empty">No videos yet</div>';
      return;
    }

    recentList.innerHTML = '';
    list.forEach(v => {
      const label = v.question || v.filename.replace(/^\d{8}_\d{6}_/, '').replace(/_/g, ' ').replace('.mp4', '');
      const item  = document.createElement('div');
      item.className = 'recent-item';
      item.dataset.id = v.id || v.filename;
      item.dataset.filename = v.filename;
      item.innerHTML = `
        <span class="recent-item-icon">▶</span>
        <span class="recent-item-name" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
      `;

      // When clicked, open the full Claude/ChatGPT/Gemini chat interface directly!
      item.addEventListener('click', (e) => {
        e.preventDefault();
        openChatSession(v.id || v.filename);
      });

      recentList.appendChild(item);
    });
  } catch (e) {
    console.error('Failed to load recent videos', e);
  }
}

$('refreshRecentBtn')?.addEventListener('click', loadRecentVideos);


// ── 16. Smooth Auto-Scroll Helper ─────────────────────────────────────────────
function scrollToBottom() {
  setTimeout(() => {
    if (chatScrollArea) {
      chatScrollArea.scrollTop = chatScrollArea.scrollHeight + 1000;
    }
  }, 60);
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
