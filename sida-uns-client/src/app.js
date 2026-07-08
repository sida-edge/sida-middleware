// app.js — application bootstrap. Wires config → login → mqtt → decoder →
// store → dashboard. Nothing is persisted; all state lives in these closures.

import { initDecoder, decode } from "./sparkplug/decoder.js";
import { MqttConnection } from "./mqtt/client.js";
import { SidaStore } from "./state/store.js";
import { Session } from "./auth/session.js";
import { LoginView } from "./ui/login.js";
import { Dashboard } from "./ui/dashboard.js";

const cfg = window.__SIDA_CONFIG__ || {};
const BROKER_WS_URL = cfg.BROKER_WS_URL || "";
const HISTORY_MAX_POINTS = cfg.HISTORY_MAX_POINTS || 300;

const loginView = document.getElementById("login-view");
const dashboardView = document.getElementById("dashboard-view");

const session = new Session();
const store = new SidaStore({ maxPoints: HISTORY_MAX_POINTS });
let dashboard = null;
let conn = null;

// Expose a tiny hook for the acceptance test to introspect discovered state
// without reaching into the DOM internals (read-only; no persistence).
window.__SIDA_DEBUG__ = {
  store,
  metricIds: () => [...store.history.keys()],
  history: (id) => store.getHistory(id),
  liveness: () => Object.fromEntries(store.nodeLiveness),
  config: cfg
};

function handleRawMessage(topic, payload) {
  let msg;
  try {
    msg = decode(topic, payload);
  } catch (err) {
    // Caso 5: corrupted / non-Protobuf payload → drop silently from UI, log only.
    console.warn("[decode] payload descartado em", topic, "-", err.message);
    return;
  }
  try {
    store.applyMessage(msg);
  } catch (err) {
    console.error("[state] erro ao aplicar mensagem", err);
  }
}

async function onLogin(username, password) {
  if (!BROKER_WS_URL) {
    throw new Error("BROKER_WS_URL não configurado no container");
  }
  session.set(username, password);
  session.status = "autenticando";

  conn = new MqttConnection({
    url: BROKER_WS_URL,
    onMessage: handleRawMessage,
    onStatus: (s) => { if (dashboard) dashboard.setBanner(s); }
  });

  await conn.connect(username, password); // rejects on auth/connection failure
  session.status = "autenticado";
  showDashboard();
}

function showDashboard() {
  loginView.hidden = true;
  dashboardView.hidden = false;
  if (!dashboard) dashboard = new Dashboard(store);
  dashboard.setBanner({ connection: "conectado" });
}

function onLogout() {
  if (conn) conn.disconnect();
  session.clear();
  dashboardView.hidden = true;
  loginView.hidden = false;
  // The in-memory history/tree are intentionally left as-is only until reload;
  // a full reset happens naturally because nothing is persisted.
}

async function main() {
  try {
    await initDecoder("./sparkplug/sparkplug_b.proto");
    console.log("[app] decoder Sparkplug B inicializado");
  } catch (err) {
    console.error("[app] falha ao inicializar decoder:", err);
  }
  new LoginView({ brokerUrl: BROKER_WS_URL, onSubmit: onLogin });
  document.getElementById("logout-btn").addEventListener("click", onLogout);
  console.log("[app] pronto. Broker configurado:", BROKER_WS_URL || "(vazio)");
}

main();
