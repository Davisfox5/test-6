/* ══════════════════════════════════════════════════════════════════════
   annotations.js  –  Drawing overlay engine for GameTape
   ══════════════════════════════════════════════════════════════════════ */

/* ── State ─────────────────────────────────────────────────────────── */
let annCanvas, annCtx;
let annActive = false;           // annotation mode on/off
let annClip = null;              // the clip being annotated
let annList = [];                // annotations for current clip
let annTool = "arrow";           // arrow | rect | circle | freehand | text
let annColor = "#ff0000";
let annLineWidth = 3;
let annDrawing = false;
let annStart = null;             // {x, y} normalised
let annFreehandPts = [];
let annFreezeMode = false;
let annFreezeDuration = 2.0;     // seconds the freeze holds
let annFreezeTS = null;          // timestamp of freeze frame

/* ── Helpers ───────────────────────────────────────────────────────── */
function normX(px) { return px / annCanvas.width; }
function normY(px) { return px / annCanvas.height; }
function denormX(n) { return n * annCanvas.width; }
function denormY(n) { return n * annCanvas.height; }

function canvasXY(e) {
  const r = annCanvas.getBoundingClientRect();
  return { px: e.clientX - r.left, py: e.clientY - r.top };
}

/* ── Initialisation ────────────────────────────────────────────────── */
function initAnnotations(videoEl) {
  annCanvas = document.getElementById("annotation-canvas");
  annCtx = annCanvas.getContext("2d");
  resizeCanvas(videoEl);

  // Keep canvas aligned with video on resize / metadata load
  const ro = new ResizeObserver(() => resizeCanvas(videoEl));
  ro.observe(videoEl);
  videoEl.addEventListener("loadedmetadata", () => resizeCanvas(videoEl));
}

function resizeCanvas(videoEl) {
  annCanvas.width = videoEl.clientWidth;
  annCanvas.height = videoEl.clientHeight;
  renderAnnotations();
}

/* ── Enter / Exit Annotation Mode ──────────────────────────────────── */
function enterAnnotationMode(clip) {
  annActive = true;
  annClip = clip;
  annList = (clip.annotations || []).map(a => ({...a, data: {...a.data}}));
  annCanvas.style.pointerEvents = "auto";
  annCanvas.style.cursor = "crosshair";
  document.getElementById("ann-toolbar").classList.add("visible");
  renderAnnotations();
}

function exitAnnotationMode() {
  annActive = false;
  annClip = null;
  annList = [];
  annFreezeMode = false;
  annFreezeTS = null;
  annCanvas.style.pointerEvents = "none";
  annCanvas.style.cursor = "default";
  document.getElementById("ann-toolbar").classList.remove("visible");
  clearCanvas();
}

/* ── Drawing: Mouse Events ─────────────────────────────────────────── */
function onAnnMouseDown(e) {
  if (!annActive) return;
  const { px, py } = canvasXY(e);
  annDrawing = true;
  annStart = { x: normX(px), y: normY(py) };

  if (annTool === "freehand") {
    annFreehandPts = [{ x: annStart.x, y: annStart.y }];
  }
  if (annTool === "text") {
    annDrawing = false;
    const text = prompt("Enter text:");
    if (text) {
      saveAnnotation({
        type: "text",
        data: { x: annStart.x, y: annStart.y, text },
      });
    }
  }
}

function onAnnMouseMove(e) {
  if (!annActive || !annDrawing) return;
  const { px, py } = canvasXY(e);
  const cur = { x: normX(px), y: normY(py) };

  if (annTool === "freehand") {
    annFreehandPts.push(cur);
  }

  // Live preview
  renderAnnotations();
  drawShapePreview(annStart, cur);
}

function onAnnMouseUp(e) {
  if (!annActive || !annDrawing) return;
  annDrawing = false;
  const { px, py } = canvasXY(e);
  const end = { x: normX(px), y: normY(py) };

  if (annTool === "arrow") {
    saveAnnotation({ type: "arrow", data: { x1: annStart.x, y1: annStart.y, x2: end.x, y2: end.y } });
  } else if (annTool === "rect") {
    saveAnnotation({ type: "rect", data: { x1: annStart.x, y1: annStart.y, x2: end.x, y2: end.y } });
  } else if (annTool === "circle") {
    const cx = (annStart.x + end.x) / 2;
    const cy = (annStart.y + end.y) / 2;
    const rx = Math.abs(end.x - annStart.x) / 2;
    const ry = Math.abs(end.y - annStart.y) / 2;
    saveAnnotation({ type: "circle", data: { cx, cy, rx, ry } });
  } else if (annTool === "freehand") {
    saveAnnotation({ type: "freehand", data: { points: annFreehandPts } });
    annFreehandPts = [];
  }
}

/* ── Preview while dragging ────────────────────────────────────────── */
function drawShapePreview(start, cur) {
  annCtx.save();
  annCtx.strokeStyle = annColor;
  annCtx.lineWidth = annLineWidth;
  annCtx.setLineDash([6, 4]);

  if (annTool === "arrow") {
    drawArrow(annCtx, denormX(start.x), denormY(start.y), denormX(cur.x), denormY(cur.y));
  } else if (annTool === "rect") {
    const x = denormX(Math.min(start.x, cur.x));
    const y = denormY(Math.min(start.y, cur.y));
    const w = denormX(Math.abs(cur.x - start.x));
    const h = denormY(Math.abs(cur.y - start.y));
    annCtx.strokeRect(x, y, w, h);
  } else if (annTool === "circle") {
    const cx = denormX((start.x + cur.x) / 2);
    const cy = denormY((start.y + cur.y) / 2);
    const rx = denormX(Math.abs(cur.x - start.x) / 2);
    const ry = denormY(Math.abs(cur.y - start.y) / 2);
    annCtx.beginPath();
    annCtx.ellipse(cx, cy, Math.max(rx, 1), Math.max(ry, 1), 0, 0, Math.PI * 2);
    annCtx.stroke();
  } else if (annTool === "freehand") {
    annCtx.beginPath();
    annFreehandPts.forEach((p, i) => {
      const fx = denormX(p.x), fy = denormY(p.y);
      i === 0 ? annCtx.moveTo(fx, fy) : annCtx.lineTo(fx, fy);
    });
    annCtx.stroke();
  }

  annCtx.restore();
}

/* ── Save annotation to server ─────────────────────────────────────── */
async function saveAnnotation(shape) {
  const video = document.getElementById("game-video");
  const startTime = annFreezeMode && annFreezeTS !== null ? annFreezeTS : video.currentTime;
  const endTime = annFreezeMode ? startTime + annFreezeDuration : annClip.end;

  const body = {
    type: shape.type,
    color: annColor,
    lineWidth: annLineWidth,
    startTime: Math.max(startTime, annClip.start),
    endTime: Math.min(endTime, annClip.end),
    data: shape.data,
  };

  const res = await fetch(`/api/projects/${currentProject.id}/clips/${annClip.id}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const ann = await res.json();
  if (!ann.error) {
    annList.push(ann);
    // Also update local clip data
    if (!annClip.annotations) annClip.annotations = [];
    annClip.annotations.push(ann);
  }
  renderAnnotations();
}

/* ── Delete single annotation ──────────────────────────────────────── */
async function deleteAnnotation(annId) {
  await fetch(`/api/projects/${currentProject.id}/clips/${annClip.id}/annotations/${annId}`, {
    method: "DELETE",
  });
  annList = annList.filter(a => a.id !== annId);
  if (annClip.annotations) {
    annClip.annotations = annClip.annotations.filter(a => a.id !== annId);
  }
  renderAnnotations();
  renderAnnList();
}

/* ── Clear all annotations ─────────────────────────────────────────── */
async function clearAllAnnotations() {
  await fetch(`/api/projects/${currentProject.id}/clips/${annClip.id}/annotations`, {
    method: "DELETE",
  });
  annList = [];
  if (annClip) annClip.annotations = [];
  renderAnnotations();
  renderAnnList();
}

/* ── Render all visible annotations ────────────────────────────────── */
function renderAnnotations() {
  clearCanvas();
  if (!annClip) return;

  const video = document.getElementById("game-video");
  const t = video.currentTime;

  annList.forEach(a => {
    if (t >= a.startTime && t <= a.endTime) {
      drawAnnotation(a);
    }
  });
}

function clearCanvas() {
  if (annCtx) annCtx.clearRect(0, 0, annCanvas.width, annCanvas.height);
}

/* ── Draw a single annotation ──────────────────────────────────────── */
function drawAnnotation(a) {
  annCtx.save();
  annCtx.strokeStyle = a.color;
  annCtx.fillStyle = a.color;
  annCtx.lineWidth = a.lineWidth;
  annCtx.setLineDash([]);

  const d = a.data;
  switch (a.type) {
    case "arrow":
      drawArrow(annCtx, denormX(d.x1), denormY(d.y1), denormX(d.x2), denormY(d.y2));
      break;
    case "rect":
      annCtx.strokeRect(
        denormX(Math.min(d.x1, d.x2)),
        denormY(Math.min(d.y1, d.y2)),
        denormX(Math.abs(d.x2 - d.x1)),
        denormY(Math.abs(d.y2 - d.y1))
      );
      break;
    case "circle":
      annCtx.beginPath();
      annCtx.ellipse(
        denormX(d.cx), denormY(d.cy),
        Math.max(denormX(d.rx), 1), Math.max(denormY(d.ry), 1),
        0, 0, Math.PI * 2
      );
      annCtx.stroke();
      break;
    case "freehand":
      if (d.points && d.points.length > 1) {
        annCtx.beginPath();
        d.points.forEach((p, i) => {
          const fx = denormX(p.x), fy = denormY(p.y);
          i === 0 ? annCtx.moveTo(fx, fy) : annCtx.lineTo(fx, fy);
        });
        annCtx.stroke();
      }
      break;
    case "text":
      const fontSize = Math.max(a.lineWidth * 6, 14);
      annCtx.font = `bold ${fontSize}px sans-serif`;
      annCtx.fillStyle = a.color;
      annCtx.shadowColor = "rgba(0,0,0,0.7)";
      annCtx.shadowBlur = 4;
      annCtx.fillText(d.text, denormX(d.x), denormY(d.y));
      break;
  }
  annCtx.restore();
}

/* ── Arrow drawing helper ──────────────────────────────────────────── */
function drawArrow(ctx, x1, y1, x2, y2) {
  const headLen = Math.max(ctx.lineWidth * 4, 12);
  const angle = Math.atan2(y2 - y1, x2 - x1);

  // Shaft
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();

  // Arrowhead
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6));
  ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6));
  ctx.closePath();
  ctx.fill();
}

/* ── Freeze Frame ──────────────────────────────────────────────────── */
function toggleFreezeFrame() {
  const video = document.getElementById("game-video");
  annFreezeMode = !annFreezeMode;
  const btn = document.getElementById("btn-ann-freeze");
  if (annFreezeMode) {
    video.pause();
    annFreezeTS = video.currentTime;
    btn.classList.add("active");
  } else {
    annFreezeTS = null;
    btn.classList.remove("active");
  }
}

/* ── Annotation list panel (inside toolbar) ────────────────────────── */
function renderAnnList() {
  const container = document.getElementById("ann-list");
  if (!container) return;
  container.innerHTML = "";
  if (annList.length === 0) {
    container.innerHTML = '<span class="ann-empty">No annotations yet</span>';
    return;
  }
  annList.forEach(a => {
    const row = document.createElement("div");
    row.className = "ann-list-item";
    const tRange = `${fmtAnn(a.startTime)}-${fmtAnn(a.endTime)}`;
    row.innerHTML = `
      <span class="ann-swatch" style="background:${a.color}"></span>
      <span class="ann-type">${a.type}</span>
      <span class="ann-time">${tRange}</span>
      <button class="ann-del" data-id="${a.id}">&times;</button>
    `;
    row.querySelector(".ann-del").addEventListener("click", () => deleteAnnotation(a.id));
    container.appendChild(row);
  });
}

function fmtAnn(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

/* ── Playback: render annotations on each frame ────────────────────── */
function tickAnnotations() {
  if (annClip) renderAnnotations();
}
