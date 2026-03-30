/* ══════════════════════════════════════════════════════════════════════
   recording.js  –  Telestration recording engine for GameTape
   Composites video + annotation canvas, captures mic audio,
   records everything as a single WebM via MediaRecorder.
   ══════════════════════════════════════════════════════════════════════ */

/* ── State ─────────────────────────────────────────────────────────── */
let recVideoEl = null;
let recAnnCanvas = null;
let recCompCanvas = null;
let recCompCtx = null;
let recMediaRecorder = null;
let recChunks = [];
let recMicStream = null;
let recAnimFrameId = null;
let recIsRecording = false;
let recStartTime = 0;
let recTimerInterval = null;
let recClipId = null;

/* ── Init ──────────────────────────────────────────────────────────── */
function initRecording(videoEl, annotationCanvas) {
  recVideoEl = videoEl;
  recAnnCanvas = annotationCanvas;

  // Create offscreen compositing canvas
  recCompCanvas = document.createElement("canvas");
  recCompCanvas.style.display = "none";
  document.body.appendChild(recCompCanvas);
  recCompCtx = recCompCanvas.getContext("2d");
}

/* ── Feature detection ─────────────────────────────────────────────── */
function isRecordingSupported() {
  return typeof MediaRecorder !== "undefined" &&
         typeof navigator.mediaDevices !== "undefined" &&
         typeof navigator.mediaDevices.getUserMedia === "function";
}

/* ── Public API ────────────────────────────────────────────────────── */
function isRecording() {
  return recIsRecording;
}

async function startRecording(clipId) {
  if (recIsRecording) return;

  // Size compositing canvas to video's native resolution
  const vw = recVideoEl.videoWidth || recVideoEl.clientWidth;
  const vh = recVideoEl.videoHeight || recVideoEl.clientHeight;
  recCompCanvas.width = vw;
  recCompCanvas.height = vh;
  recClipId = clipId;

  // Request microphone
  try {
    recMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    // If mic denied, record without audio
    console.warn("Microphone access denied, recording without audio:", e);
    recMicStream = null;
  }

  // Start compositing render loop
  recIsRecording = true;
  renderCompositeFrame();

  // Assemble streams
  const canvasStream = recCompCanvas.captureStream(30);
  const tracks = [...canvasStream.getVideoTracks()];
  if (recMicStream) {
    tracks.push(...recMicStream.getAudioTracks());
  }
  const combinedStream = new MediaStream(tracks);

  // Pick codec
  const mimeType = pickMimeType();
  recChunks = [];

  recMediaRecorder = new MediaRecorder(combinedStream, {
    mimeType,
    videoBitsPerSecond: 2500000,
  });

  recMediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recChunks.push(e.data);
  };

  recMediaRecorder.start(1000); // chunks every 1s
  recStartTime = performance.now();

  // Timer display
  const $timer = document.getElementById("rec-timer");
  recTimerInterval = setInterval(() => {
    const elapsed = (performance.now() - recStartTime) / 1000;
    const m = Math.floor(elapsed / 60);
    const s = Math.floor(elapsed % 60);
    if ($timer) $timer.textContent = `${m}:${s.toString().padStart(2, "0")}`;
  }, 500);
}

function stopRecording() {
  return new Promise((resolve) => {
    if (!recIsRecording || !recMediaRecorder) {
      resolve(null);
      return;
    }

    recMediaRecorder.onstop = () => {
      const blob = new Blob(recChunks, { type: recMediaRecorder.mimeType || "video/webm" });
      cleanup();
      resolve(blob);
    };

    recMediaRecorder.stop();
  });
}

/* ── Compositing render loop ───────────────────────────────────────── */
function renderCompositeFrame() {
  if (!recIsRecording) return;

  // Draw current video frame
  recCompCtx.drawImage(recVideoEl, 0, 0, recCompCanvas.width, recCompCanvas.height);

  // Ensure annotations are up-to-date (handles live drawing preview)
  if (typeof renderAnnotations === "function") {
    renderAnnotations();
  }

  // Draw annotation canvas on top
  if (recAnnCanvas) {
    recCompCtx.drawImage(recAnnCanvas, 0, 0, recCompCanvas.width, recCompCanvas.height);
  }

  recAnimFrameId = requestAnimationFrame(renderCompositeFrame);
}

/* ── Helpers ───────────────────────────────────────────────────────── */
function pickMimeType() {
  const types = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

function cleanup() {
  recIsRecording = false;

  if (recAnimFrameId) {
    cancelAnimationFrame(recAnimFrameId);
    recAnimFrameId = null;
  }

  if (recMicStream) {
    recMicStream.getTracks().forEach(t => t.stop());
    recMicStream = null;
  }

  if (recTimerInterval) {
    clearInterval(recTimerInterval);
    recTimerInterval = null;
  }

  recMediaRecorder = null;
  recChunks = [];
  recClipId = null;
}

function getRecordingDuration() {
  if (!recStartTime) return 0;
  return Math.round((performance.now() - recStartTime) / 1000);
}
