// state/store.js
// In-memory system state (SDD section 4) and the reducer that applies the
// business rules of section 5.2. No network I/O, no DOM. Everything here lives
// only in the JS heap of the current tab and is lost on reload — nothing is
// persisted to disk, localStorage or sessionStorage.

const DEFAULT_MAX_POINTS = 300;

export function nodeKey(groupId, nodeId) {
  return `${groupId}/${nodeId}`;
}
export function metricId(groupId, nodeId, deviceId, metricName) {
  return `${groupId}/${nodeId}/${deviceId ?? "_node_"}/${metricName}`;
}

export class SidaStore {
  constructor(opts = {}) {
    this.maxPoints = opts.maxPoints || DEFAULT_MAX_POINTS;
    // device_tree: Map<groupId, {nodes: Map<nodeId, node>}>
    //   node   = { devices: Map<deviceId, device>, metrics: Map<name, metric>, offline }
    //   device = { metrics: Map<name, metric>, offline }
    //   metric = { id, name, kind, datatype, engUnit, lastValue, lastTs }
    this.tree = new Map();
    this.nodeLiveness = new Map();        // "group/node" -> 'online' | 'offline'
    this.aliasTable = new Map();          // "group/node" -> Map<alias:number, name>
    this.history = new Map();             // metricId -> Array<{t, v}> (circular)
    this.listeners = new Set();
  }

  subscribe(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  _emit(evt) { for (const fn of this.listeners) { try { fn(evt); } catch (e) { console.error(e); } } }

  getHistory(id) { return this.history.get(id) || []; }

  // ---- internal helpers -------------------------------------------------
  _group(groupId) {
    let g = this.tree.get(groupId);
    if (!g) { g = { nodes: new Map() }; this.tree.set(groupId, g); }
    return g;
  }
  _node(groupId, nodeId) {
    const g = this._group(groupId);
    let n = g.nodes.get(nodeId);
    if (!n) { n = { devices: new Map(), metrics: new Map(), offline: false }; g.nodes.set(nodeId, n); }
    return n;
  }
  _device(groupId, nodeId, deviceId) {
    const n = this._node(groupId, nodeId);
    let d = n.devices.get(deviceId);
    if (!d) { d = { metrics: new Map(), offline: false }; n.devices.set(deviceId, d); }
    return d;
  }

  _pushPoint(id, t, v) {
    let arr = this.history.get(id);
    if (!arr) { arr = []; this.history.set(id, arr); }
    arr.push({ t, v });
    if (arr.length > this.maxPoints) arr.splice(0, arr.length - this.maxPoints); // circular
  }

  // Register/update a metric leaf under a container (node or device).
  _upsertMetric(container, groupId, nodeId, deviceId, m) {
    const id = metricId(groupId, nodeId, deviceId, m.name);
    let meta = container.metrics.get(m.name);
    if (!meta) {
      meta = { id, name: m.name, groupId, nodeId, deviceId };
      container.metrics.set(m.name, meta);
    }
    meta.kind = m.kind;
    meta.datatype = m.datatype;
    if (m.engUnit != null) meta.engUnit = m.engUnit;
    meta.lastValue = m.value;
    meta.lastTs = m.timestamp ?? Date.now();
    return meta;
  }

  // Rebuild a node's alias table from a birth payload's metric list, and merge
  // in any additional (device) aliases. NBIRTH resets; DBIRTH merges.
  _rebuildAliases(key, metrics, { reset }) {
    let table = this.aliasTable.get(key);
    if (reset || !table) { table = new Map(); this.aliasTable.set(key, table); }
    for (const m of metrics) {
      if (m.alias != null && m.name) table.set(m.alias, m.name);
    }
  }

  _resolveName(key, m) {
    if (m.name) return m.name;
    if (m.alias != null) {
      const table = this.aliasTable.get(key);
      if (table && table.has(m.alias)) return table.get(m.alias);
    }
    return null; // unresolved
  }

  // ---- reducer (SDD 5.2) ------------------------------------------------
  applyMessage(msg) {
    if (!msg || !msg.messageType) {console.error("Erro de tipo")} return;
    const { groupId, nodeId, deviceId, messageType } = msg;
    const key = nodeKey(groupId, nodeId);

    switch (messageType) {
      case "NBIRTH":   this._onNBirth(key, groupId, nodeId, msg); break;
      case "DBIRTH":   this._onDBirth(key, groupId, nodeId, deviceId, msg); break;
      case "NDATA":    this._onNData(key, groupId, nodeId, msg); break;
      case "DDATA":    this._onDData(key, groupId, nodeId, deviceId, msg); break;
      case "NDEATH":   this._onNDeath(key, groupId, nodeId); break;
      case "DDEATH":   this._onDDeath(groupId, nodeId, deviceId); break;
      default:
        // STATE/NCMD/DCMD and unknown types are ignored by this passive reader.
        return;
    }
    this._emit({ type: messageType, groupId, nodeId, deviceId });
  }

  _onNBirth(key, groupId, nodeId, msg) {
    this._rebuildAliases(key, msg.metrics, { reset: true });
    this.nodeLiveness.set(key, "online");
    const node = this._node(groupId, nodeId);
    node.offline = false;
    // Node-level metrics (excluding bdSeq/Node Control/*) are kept for context.
    for (const m of msg.metrics) {
      if (!m.name) continue;
      if (m.name.startsWith("bdSeq") || m.name.startsWith("Node Control/")) continue;
      const meta = this._upsertMetric(node, groupId, nodeId, null, m);
      this._pushPoint(meta.id, m.timestamp ?? msg.timestamp, m.value);
    }
  }

  _onDBirth(key, groupId, nodeId, deviceId, msg) {
    // DBIRTH may define additional device aliases — merge, don't reset.
    this._rebuildAliases(key, msg.metrics, { reset: false });
    const device = this._device(groupId, nodeId, deviceId);
    device.offline = false;
    if (!this.nodeLiveness.has(key)) this.nodeLiveness.set(key, "online");
    for (const m of msg.metrics) {
      const name = this._resolveName(key, m);
      if (!name) continue;
      const meta = this._upsertMetric(device, groupId, nodeId, deviceId, { ...m, name });
      this._pushPoint(meta.id, m.timestamp ?? msg.timestamp, m.value); // first point
    }
  }

  _onNData(key, groupId, nodeId, msg) {
    // Node data behaves like device data but for node-level metrics.
    if (!this.aliasTable.has(key) && !this.nodeLiveness.has(key)) {
      console.warn(`[state] NDATA de nó não nascido (${key}) descartado`);
      return;
    }
    const node = this._node(groupId, nodeId);
    for (const m of msg.metrics) {
      const name = this._resolveName(key, m);
      if (!name) { console.warn(`[state] métrica sem nome/alias resolvível em NDATA (${key})`); continue; }
      const meta = this._upsertMetric(node, groupId, nodeId, null, { ...m, name });
      this._pushPoint(meta.id, m.timestamp ?? msg.timestamp, m.value);
    }
  }

  _onDData(key, groupId, nodeId, deviceId, msg) {
    // Caso 3: DDATA referencing a node that was never born → drop the message.
    if (!this.aliasTable.has(key) && !this.nodeLiveness.has(key)) {
      console.warn(`[state] DDATA descartado: nó ${key} sem NBIRTH prévio (alias não resolvível)`);
      return;
    }
    const device = this._device(groupId, nodeId, deviceId); // auto-discover device
    for (const m of msg.metrics) {
      const name = this._resolveName(key, m);
      if (!name) {
        console.warn(`[state] DDATA: métrica com alias ${m.alias} não resolvível em ${key} — descartada`);
        continue; // drop just this metric, keep rendering the rest (caso 3 / 7.2)
      }
      const meta = this._upsertMetric(device, groupId, nodeId, deviceId, { ...m, name });
      this._pushPoint(meta.id, m.timestamp ?? msg.timestamp, m.value); // incremental point
    }
  }

  _onNDeath(key, groupId, nodeId) {
    // Caso 7.7: NDEATH for a node we never saw born → ignore silently.
    if (!this.nodeLiveness.has(key)) {
      console.warn(`[state] NDEATH ignorado: nó ${key} desconhecido`);
      return;
    }
    this.nodeLiveness.set(key, "offline");
    const g = this.tree.get(groupId);
    const node = g && g.nodes.get(nodeId);
    if (node) {
      node.offline = true;
      for (const d of node.devices.values()) d.offline = true; // history preserved
    }
  }

  _onDDeath(groupId, nodeId, deviceId) {
    const g = this.tree.get(groupId);
    const node = g && g.nodes.get(nodeId);
    const device = node && node.devices.get(deviceId);
    if (device) device.offline = true; // history preserved, no new points
  }

  isNodeOffline(groupId, nodeId) {
    return this.nodeLiveness.get(nodeKey(groupId, nodeId)) === "offline";
  }
}
