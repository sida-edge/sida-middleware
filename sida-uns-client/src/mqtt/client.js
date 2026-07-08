// mqtt/client.js
// WebSocket MQTT connection lifecycle: connect with user/pass, subscribe to
// spBv1.0/#, deliver raw (topic, bytes) upstream, and reconnect with backoff.
// It does NOT decode Protobuf and knows nothing about the UI (SDD 6.2).
// mqtt.js is loaded globally as `mqtt` from the vendored browser bundle.

const TOPIC = "spBv1.0/#";

export class MqttConnection {
  constructor({ url, onMessage, onStatus }) {
    this.url = url;
    this.onMessage = onMessage || (() => {});
    this.onStatus = onStatus || (() => {});
    this.client = null;
    this._authSettled = false;
    this._everConnected = false;
  }

  // Returns a promise that resolves on first successful CONNACK and rejects on
  // an authentication/connection failure that happens before we ever connect.
  connect(username, password) {
    if (typeof mqtt === "undefined") {
      return Promise.reject(new Error("mqtt.js (vendor/mqtt.min.js) não foi carregado"));
    }
    this.onStatus({ connection: "conectando" });

    return new Promise((resolve, reject) => {
      let settled = false;
      const client = mqtt.connect(this.url, {
        username,
        password,
        protocolVersion: 4,
        clean: true,
        // We drive reconnection ourselves so we can surface a clear banner and
        // reuse the in-memory credentials without persisting them anywhere.
        reconnectPeriod: 0,
        connectTimeout: 8000,
        keepalive: 30
      });
      this.client = client;

      client.on("connect", () => {
        this._everConnected = true;
        this._backoff = 1000;
        this.onStatus({ connection: "conectado", auth: "autenticado" });
        client.subscribe(TOPIC, { qos: 0 }, (err) => {
          if (err) console.error("[mqtt] falha ao subscrever", TOPIC, err);
          else console.log(`[mqtt] conectado e subscrito em ${TOPIC}`);
        });
        if (!settled) { settled = true; resolve(); }
      });

      client.on("message", (topic, payload) => {
        // payload is a Buffer/Uint8Array of the raw Sparkplug B bytes.
        this.onMessage(topic, payload);
      });

      client.on("error", (err) => {
        console.error("[mqtt] erro", err && err.message);
        const authFail = isAuthError(err);
        if (!settled) {
          settled = true;
          this.onStatus({ connection: "erro", auth: authFail ? "credenciais_invalidas" : "nao_autenticado" });
          try { client.end(true); } catch (_) {}
          reject(err);
        } else {
          this.onStatus({ connection: "erro" });
        }
      });

      client.on("close", () => {
        if (this._everConnected && !this._manualClose) {
          this.onStatus({ connection: "erro", reconnecting: true });
          this._scheduleReconnect(username, password);
        }
      });
    });
  }

  _scheduleReconnect(username, password) {
    this._backoff = Math.min((this._backoff || 1000) * 2, 30000);
    const delay = this._backoff;
    console.warn(`[mqtt] conexão perdida — reconectando em ${Math.round(delay / 1000)}s`);
    this.onStatus({ connection: "erro", reconnecting: true, retryInMs: delay });
    clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      if (this._manualClose) return;
      // Reuse the same in-memory credentials; re-subscribe happens on connect.
      this.connect(username, password).catch(() => {
        // keep retrying with backoff via the close handler
      });
    }, delay);
  }

  disconnect() {
    this._manualClose = true;
    clearTimeout(this._reconnectTimer);
    if (this.client) { try { this.client.end(true); } catch (_) {} }
    this.onStatus({ connection: "desconectado" });
  }
}

function isAuthError(err) {
  if (!err) return false;
  const code = err.code;
  // MQTT 3.1.1 CONNACK return codes 4 (bad user/pass) and 5 (not authorized).
  if (code === 4 || code === 5) return true;
  const msg = String(err.message || "").toLowerCase();
  return msg.includes("not authorized") || msg.includes("bad user") ||
         msg.includes("credentials") || msg.includes("password");
}
