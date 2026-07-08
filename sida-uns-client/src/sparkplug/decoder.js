// sparkplug/decoder.js
// Decodes binary Sparkplug B (Protobuf) payloads using protob.js (protobufjs,
// loaded globally as `protobuf` from the vendored browser bundle). It also
// parses the spBv1.0 topic and normalizes metric values / properties.
//
// Responsibility boundary (SDD 6.2): decode + classify + resolve value shape.
// It does NOT touch the DOM and keeps NO long-lived state beyond the loaded
// schema. Alias RESOLUTION against a node's alias table happens in state/.

const SPB_NAMESPACE = "spBv1.0";

// Sparkplug B DataType enum (subset we care about) — from the Eclipse spec.
export const DataType = {
  Int8: 1, Int16: 2, Int32: 3, Int64: 4,
  UInt8: 5, UInt16: 6, UInt32: 7, UInt64: 8,
  Float: 9, Double: 10, Boolean: 11, String: 12,
  DateTime: 13, Text: 14, UUID: 15, DataSet: 16,
  Bytes: 17, File: 18, Template: 19
};

const NUMERIC_DATATYPES = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13]);

let PayloadType = null;

// Load and compile the schema once. Returns a promise.
export async function initDecoder(protoUrl = "./sparkplug/sparkplug_b.proto") {
  if (PayloadType) return;
  if (typeof protobuf === "undefined") {
    throw new Error("protobufjs (vendor/protobuf.min.js) não foi carregado");
  }
  const root = await protobuf.load(protoUrl);
  PayloadType = root.lookupType("org.eclipse.tahu.protobuf.Payload");
}

// Parse "spBv1.0/{group}/{type}/{node}[/{device}]".
// Returns null for anything that is not a Sparkplug B message topic.
export function parseTopic(topic) {
  const parts = String(topic || "").split("/");
  if (parts.length < 4 || parts[0] !== SPB_NAMESPACE) return null;
  const [, groupId, messageType, nodeId, ...rest] = parts;
  const deviceId = rest.length ? rest.join("/") : null;
  return { groupId, messageType, nodeId, deviceId };
}

// Extract the concrete JS value + a coarse kind for a decoded Metric.
// Datatype hint wins when present; otherwise we fall back to whichever oneof
// value field protobufjs populated.
export function metricValue(metric) {
  if (metric.isNull) return { value: null, kind: "null" };
  const dt = metric.datatype;

  if (dt === DataType.Boolean && metric.booleanValue != null) {
    return { value: !!metric.booleanValue, kind: "boolean" };
  }
  if (dt === DataType.String || dt === DataType.Text || dt === DataType.UUID) {
    if (metric.stringValue != null) return { value: metric.stringValue, kind: "string" };
  }

  if (metric.doubleValue != null) return { value: metric.doubleValue, kind: "number" };
  if (metric.floatValue != null) return { value: metric.floatValue, kind: "number" };
  if (metric.intValue != null) return { value: toNum(metric.intValue), kind: "number" };
  if (metric.longValue != null) return { value: toNum(metric.longValue), kind: "number" };
  if (metric.booleanValue != null) return { value: !!metric.booleanValue, kind: "boolean" };
  if (metric.stringValue != null) return { value: metric.stringValue, kind: "string" };
  if (metric.bytesValue != null) return { value: metric.bytesValue, kind: "bytes" };
  return { value: null, kind: "unknown" };
}

// protobufjs represents 64-bit ints as Long objects unless configured; coerce.
function toNum(v) {
  if (v == null) return null;
  if (typeof v === "number") return v;
  if (typeof v === "object" && typeof v.toNumber === "function") return v.toNumber();
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

export function isNumericDataType(dt) {
  return NUMERIC_DATATYPES.has(dt);
}

// Read engineering unit and other scalar props from a metric PropertySet.
export function readProperties(metric) {
  const out = {};
  const ps = metric.properties;
  if (!ps || !Array.isArray(ps.keys)) return out;
  for (let i = 0; i < ps.keys.length; i++) {
    const key = ps.keys[i];
    const pv = ps.values && ps.values[i];
    if (!pv || pv.isNull) { out[key] = null; continue; }
    out[key] = propScalar(pv);
  }
  return out;
}

function propScalar(pv) {
  if (pv.stringValue != null) return pv.stringValue;
  if (pv.doubleValue != null) return pv.doubleValue;
  if (pv.floatValue != null) return pv.floatValue;
  if (pv.intValue != null) return toNum(pv.intValue);
  if (pv.longValue != null) return toNum(pv.longValue);
  if (pv.booleanValue != null) return !!pv.booleanValue;
  return null;
}

// Decode a raw binary payload (Uint8Array) into a normalized message.
// Throws if the schema is not initialized or the bytes are not a valid payload.
export function decode(topic, payloadBytes) {
  const parsed = parseTopic(topic);
  if (!parsed) {
    throw new Error(`Tópico fora do namespace Sparkplug B: ${topic}`);
  }
  if (!PayloadType) {
    throw new Error("Decoder não inicializado — chame initDecoder() primeiro");
  }
  const bytes = payloadBytes instanceof Uint8Array
    ? payloadBytes
    : new Uint8Array(payloadBytes);

  // protobufjs throws on malformed/invalid wire data — surfaced to caller so
  // corrupted payloads are dropped (SDD caso 5).
  const message = PayloadType.decode(bytes);
  const obj = PayloadType.toObject(message, {
    longs: Number,
    enums: Number,
    bytes: Array,
    defaults: false,
    arrays: true,
    objects: true
  });

  const metrics = (obj.metrics || []).map((m) => {
    const { value, kind } = metricValue(m);
    const props = readProperties(m);
    return {
      name: m.name ?? null,
      alias: m.alias != null ? toNum(m.alias) : null,
      datatype: m.datatype ?? null,
      timestamp: m.timestamp != null ? toNum(m.timestamp) : null,
      isNull: !!m.isNull,
      value,
      kind,
      numeric: kind === "number" || (m.datatype != null && isNumericDataType(m.datatype)),
      properties: props,
      engUnit: props.engUnit ?? props.EngUnit ?? props.eng_unit ?? null
    };
  });

  return {
    groupId: parsed.groupId,
    nodeId: parsed.nodeId,
    deviceId: parsed.deviceId,
    messageType: parsed.messageType, // NBIRTH | DBIRTH | DDATA | NDEATH | DDEATH | NCMD | DCMD | STATE
    timestamp: obj.timestamp != null ? toNum(obj.timestamp) : Date.now(),
    seq: obj.seq != null ? toNum(obj.seq) : null,
    metrics
  };
}
