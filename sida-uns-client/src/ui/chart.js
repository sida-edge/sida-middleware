// ui/chart.js
// Minimal dependency-free time-series chart on a <canvas>. Reads a points array
// [{t, v}] and draws axes + line. Kept intentionally simple (no chart library).

export class TimeSeriesChart {
  constructor(canvas, { unit } = {}) {
    this.canvas = canvas;
    this.unit = unit || "";
    this.points = [];
  }

  setUnit(u) { this.unit = u || ""; }
  setPoints(points) { this.points = points || []; this.draw(); }

  draw() {
    const c = this.canvas;
    const ratio = window.devicePixelRatio || 1;
    const cssW = c.clientWidth || 600;
    const cssH = c.clientHeight || 260;
    c.width = Math.floor(cssW * ratio);
    c.height = Math.floor(cssH * ratio);
    const ctx = c.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const padL = 56, padR = 14, padT = 14, padB = 26;
    const w = cssW - padL - padR;
    const h = cssH - padT - padB;

    const style = getComputedStyle(document.documentElement);
    const grid = "#2a3b4d";
    const axis = style.getPropertyValue("--muted").trim() || "#8aa0b5";
    const line = style.getPropertyValue("--accent").trim() || "#37b6ff";

    const pts = this.points.filter(p => typeof p.v === "number" && isFinite(p.v));
    // Axis frame
    ctx.strokeStyle = grid; ctx.lineWidth = 1;
    ctx.strokeRect(padL, padT, w, h);

    if (pts.length === 0) {
      ctx.fillStyle = axis; ctx.font = "13px system-ui";
      ctx.fillText("sem dados numéricos", padL + 10, padT + 20);
      return;
    }

    let vMin = Math.min(...pts.map(p => p.v));
    let vMax = Math.max(...pts.map(p => p.v));
    if (vMin === vMax) { vMin -= 1; vMax += 1; }
    const tMin = pts[0].t, tMax = pts[pts.length - 1].t;
    const tSpan = (tMax - tMin) || 1;

    const x = (t) => padL + ((t - tMin) / tSpan) * w;
    const y = (v) => padT + h - ((v - vMin) / (vMax - vMin)) * h;

    // Y gridlines + labels
    ctx.fillStyle = axis; ctx.font = "11px system-ui"; ctx.textBaseline = "middle";
    const ticks = 4;
    for (let i = 0; i <= ticks; i++) {
      const v = vMin + (i / ticks) * (vMax - vMin);
      const yy = y(v);
      ctx.strokeStyle = grid; ctx.globalAlpha = 0.5;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + w, yy); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillText(fmt(v), 6, yy);
    }

    // X labels (first / last timestamp)
    ctx.textBaseline = "alphabetic";
    ctx.fillText(hhmmss(tMin), padL, cssH - 8);
    const lastLbl = hhmmss(tMax);
    ctx.fillText(lastLbl, padL + w - ctx.measureText(lastLbl).width, cssH - 8);

    // Line
    ctx.strokeStyle = line; ctx.lineWidth = 2; ctx.beginPath();
    pts.forEach((p, i) => { const xx = x(p.t), yy = y(p.v); i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); });
    ctx.stroke();

    // Points
    ctx.fillStyle = line;
    for (const p of pts) { ctx.beginPath(); ctx.arc(x(p.t), y(p.v), 2.5, 0, Math.PI * 2); ctx.fill(); }

    // Last value label
    const last = pts[pts.length - 1];
    ctx.fillStyle = line; ctx.font = "12px system-ui";
    const txt = `${fmt(last.v)} ${this.unit}`.trim();
    ctx.fillText(txt, x(last.t) - ctx.measureText(txt).width - 4, y(last.v) - 8);
  }
}

function fmt(v) {
  if (Math.abs(v) >= 1000 || (v !== 0 && Math.abs(v) < 0.01)) return v.toPrecision(4);
  return (Math.round(v * 100) / 100).toString();
}
function hhmmss(ms) {
  const d = new Date(ms);
  return d.toLocaleTimeString("pt-BR", { hour12: false });
}
