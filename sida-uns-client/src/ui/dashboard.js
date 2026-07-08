// ui/dashboard.js
// Wires the store to the tree view and the detail panel (chart for numeric
// metrics, LED indicator for booleans). Reacts to connection/liveness changes.

import { DeviceTreeView } from "./tree.js";
import { TimeSeriesChart } from "./chart.js";

export class Dashboard {
  constructor(store) {
    this.store = store;
    this.treeEl = document.getElementById("device-tree");
    this.emptyEl = document.getElementById("detail-empty");
    this.contentEl = document.getElementById("detail-content");
    this.bannerEl = document.getElementById("conn-banner");
    this.selected = null;
    this.chart = null;

    this.tree = new DeviceTreeView(this.treeEl, store, {
      onSelect: (meta) => this.select(meta)
    });

    // Re-render on every state change; refresh the open detail if affected.
    store.subscribe(() => {
      this.tree.render();
      if (this.selected) this._refreshDetail();
    });
    this.tree.render();
  }

  setBanner(state) {
    const el = this.bannerEl;
    if (!el) return;
    if (state.connection === "conectado") {
      el.textContent = "● conectado";
      el.className = "conn-banner ok";
    } else if (state.reconnecting) {
      el.textContent = "⟳ reconectando ao broker…";
      el.className = "conn-banner warn";
    } else if (state.connection === "erro") {
      el.textContent = "⚠ conexão perdida";
      el.className = "conn-banner err";
    } else if (state.connection === "conectando") {
      el.textContent = "… conectando";
      el.className = "conn-banner warn";
    } else {
      el.textContent = "desconectado";
      el.className = "conn-banner";
    }
  }

  select(meta) {
    this.selected = meta;
    this.emptyEl.hidden = true;
    this.contentEl.hidden = false;
    this.chart = null;
    this._renderDetailShell();
    this._refreshDetail();
  }

  _renderDetailShell() {
    const meta = this.selected;
    const unit = meta.engUnit ? ` <span class="munit">${escapeHtml(meta.engUnit)}</span>` : "";
    this.contentEl.innerHTML = `
      <div class="metric-header">
        <span class="mname">${escapeHtml(meta.name)}</span>${unit}
        <span id="detail-offline" class="offline-tag" hidden>offline</span>
      </div>
      <div class="metric-meta">
        ${escapeHtml(pathOf(meta))} · tipo: ${meta.kind}
      </div>
      <div id="detail-body"></div>
    `;
  }

  _refreshDetail() {
    const meta = this._currentMeta();
    if (!meta) return;
    const body = document.getElementById("detail-body");
    const offlineTag = document.getElementById("detail-offline");
    if (offlineTag) offlineTag.hidden = !this._isOffline(meta);

    if (meta.kind === "boolean") {
      const on = meta.lastValue === true;
      body.innerHTML = `
        <div class="bool-indicator ${on ? "on" : "off"}">
          <span class="led"></span>
          <span>${on ? "TRUE" : "FALSE"}</span>
        </div>
        <div class="metric-meta">último: ${fmtTs(meta.lastTs)}</div>`;
      return;
    }

    // numeric (or fallback) → chart
    if (!body.querySelector("canvas")) {
      body.innerHTML = `<div class="chart-wrap"><canvas height="260"></canvas></div>
                        <div class="metric-meta" id="chart-caption"></div>`;
      this.chart = new TimeSeriesChart(body.querySelector("canvas"), { unit: meta.engUnit });
    }
    this.chart.setUnit(meta.engUnit);
    const pts = this.store.getHistory(meta.id);
    this.chart.setPoints(pts);
    const cap = document.getElementById("chart-caption");
    if (cap) {
      const last = pts[pts.length - 1];
      cap.textContent = `${pts.length} ponto(s)` +
        (last ? ` · último ${fmtNum(last.v)} ${meta.engUnit || ""} @ ${fmtTs(last.t)}` : "");
    }
  }

  // Resolve the freshest meta object for the current selection from the store.
  _currentMeta() {
    if (!this.selected) return null;
    const s = this.selected;
    const g = this.store.tree.get(s.groupId);
    const node = g && g.nodes.get(s.nodeId);
    if (!node) return s;
    if (s.deviceId == null) return node.metrics.get(s.name) || s;
    const dev = node.devices.get(s.deviceId);
    return (dev && dev.metrics.get(s.name)) || s;
  }

  _isOffline(meta) {
    if (this.store.isNodeOffline(meta.groupId, meta.nodeId)) return true;
    const g = this.store.tree.get(meta.groupId);
    const node = g && g.nodes.get(meta.nodeId);
    if (!node) return false;
    if (meta.deviceId == null) return !!node.offline;
    const dev = node.devices.get(meta.deviceId);
    return !!(dev && dev.offline);
  }
}

function pathOf(m) {
  return [m.groupId, m.nodeId, m.deviceId].filter(Boolean).join(" › ");
}
function fmtTs(ms) { return ms ? new Date(ms).toLocaleTimeString("pt-BR", { hour12: false }) : "—"; }
function fmtNum(v) { return typeof v === "number" ? (Math.round(v * 1000) / 1000) : v; }
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}
