// ui/tree.js
// Renders the discovered Group > Node > Device > Metric hierarchy from the
// store, and reports metric selection back to the dashboard. Read-only view of
// state — it never decodes payloads or manages the MQTT connection.

export class DeviceTreeView {
  constructor(container, store, { onSelect } = {}) {
    this.el = container;
    this.store = store;
    this.onSelect = onSelect || (() => {});
    this.selectedId = null;
    this.expanded = new Set(); // collapsed-by-default is annoying for a small tree; expand all
  }

  render() {
    const rootUl = document.createElement("ul");
    const groups = [...this.store.tree.keys()].sort();
    if (groups.length === 0) {
      this.el.innerHTML = `<div class="empty-hint">Aguardando dados do broker…</div>`;
      return;
    }
    for (const groupId of groups) {
      rootUl.appendChild(this._groupNode(groupId, this.store.tree.get(groupId)));
    }
    this.el.replaceChildren(rootUl);
  }

  _labelRow({ text, offline = false, dotClass = "", badge = "", caret = "" }) {
    const row = document.createElement("div");
    row.className = "tree-label" + (offline ? " offline" : "");
    row.innerHTML =
      `<span class="caret">${caret}</span>` +
      (dotClass !== null ? `<span class="dot ${dotClass}"></span>` : "") +
      `<span class="name">${escapeHtml(text)}</span>` +
      (badge ? `<span class="badge">${escapeHtml(badge)}</span>` : "");
    return row;
  }

  _groupNode(groupId, group) {
    const li = document.createElement("li");
    li.className = "tree-node";
    li.appendChild(this._labelRow({ text: groupId, dotClass: null, badge: "grupo", caret: "▾" }));
    const ul = document.createElement("ul");
    for (const nodeId of [...group.nodes.keys()].sort()) {
      ul.appendChild(this._nodeNode(groupId, nodeId, group.nodes.get(nodeId)));
    }
    li.appendChild(ul);
    return li;
  }

  _nodeNode(groupId, nodeId, node) {
    const li = document.createElement("li");
    li.className = "tree-node";
    const offline = this.store.isNodeOffline(groupId, nodeId) || node.offline;
    li.appendChild(this._labelRow({
      text: nodeId, offline, badge: offline ? "offline" : "online", caret: "▾"
    }));
    const ul = document.createElement("ul");
    // node-level metrics
    for (const name of [...node.metrics.keys()].sort()) {
      ul.appendChild(this._metricLeaf(node.metrics.get(name), offline));
    }
    for (const deviceId of [...node.devices.keys()].sort()) {
      ul.appendChild(this._deviceNode(groupId, nodeId, deviceId, node.devices.get(deviceId), offline));
    }
    li.appendChild(ul);
    return li;
  }

  _deviceNode(groupId, nodeId, deviceId, device, nodeOffline) {
    const li = document.createElement("li");
    li.className = "tree-node";
    const offline = nodeOffline || device.offline;
    li.appendChild(this._labelRow({
      text: deviceId, offline, badge: "dispositivo", caret: "▾"
    }));
    const ul = document.createElement("ul");
    for (const name of [...device.metrics.keys()].sort()) {
      ul.appendChild(this._metricLeaf(device.metrics.get(name), offline));
    }
    li.appendChild(ul);
    return li;
  }

  _metricLeaf(meta, offline) {
    const li = document.createElement("li");
    li.className = "tree-node";
    const isBool = meta.kind === "boolean";
    const row = this._labelRow({
      text: meta.name,
      offline,
      dotClass: "",
      badge: meta.engUnit || (isBool ? "bool" : "")
    });
    row.classList.add("metric-leaf");
    if (isBool) row.classList.add("bool");
    if (meta.id === this.selectedId) row.classList.add("selected");
    row.addEventListener("click", () => {
      this.selectedId = meta.id;
      this.render();
      this.onSelect(meta);
    });
    li.appendChild(row);
    return li;
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}
