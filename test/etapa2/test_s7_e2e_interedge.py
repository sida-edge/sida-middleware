"""Checkpoints da Sprint S7 — contextualizacao ISA-95 + E2E + relatorio.

- test_isa95_mapeia_dispositivo_sem_clp -> T2.5  (device interedge no topico ISA-95, engUnit)
- test_pipeline_interedge_ponta_a_ponta -> T2.6  (passos 1-7 de 3.1; nao-regressao Modbus)
- test_report_e_aceite                  -> T2.RPT (passo 8: test/etapa2/report.json + aceite)

Todos [heavy]: fixture `etapa2_node` (no completo + os dois brokers + plc-sim +
esp32-sim). `esp32_a` e publicado pelo esp32-sim; `esp32_b` e semeado sem
simulador e serve de SONDA — o teste publica a sua telemetry com valores
conhecidos para medir latencia sensor->UNS e perda.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.heavy

GROUP = "Enterprise_Site"
NODE = "sida_edge_e2"
DEV_ESP = "Area_1_Line_1_ESP32_A"
DEV_ESP_B = "Area_1_Line_1_ESP32_B"
DEV_PUMP = "Area_1_Line_1_Pump_01"
REPORT = Path(__file__).parent / "report.json"


# --------------------------------------------------------------------------- sniffer
class UnsSniffer:
    """Assina spBv1.0/# no UNS isolado e decodifica cada payload Sparkplug."""

    def __init__(self, mqtt_mod, pb2, port):
        self._pb2 = pb2
        self.ev: list[dict] = []
        self._lock = threading.Lock()
        self._c = mqtt_mod.Client(mqtt_mod.CallbackAPIVersion.VERSION2, client_id="e2-s7-sniffer")
        self._c.on_connect = lambda c, u, f, rc, p=None: c.subscribe("spBv1.0/#", qos=1)
        self._c.on_message = self._on
        for _ in range(30):
            try:
                self._c.connect("localhost", port, keepalive=15)
                break
            except OSError:
                time.sleep(2)
        else:
            raise AssertionError(f"nao conectou ao Mosquitto do UNS em localhost:{port}")
        self._c.loop_start()

    def _on(self, _c, _u, m):
        parts = m.topic.split("/")
        if len(parts) < 4:
            return
        pb = self._pb2.Payload()
        try:
            pb.ParseFromString(m.payload)
        except Exception:
            return
        with self._lock:
            self.ev.append({
                "kind": parts[2], "node": parts[3],
                "device": parts[4] if len(parts) > 4 else None,
                "seq": pb.seq, "pb": pb, "ts": time.time(),
            })

    def snap(self, kind=None, device=None, after=0.0):
        with self._lock:
            evs = list(self.ev)
        return [e for e in evs
                if (kind is None or e["kind"] == kind)
                and (device is None or e["device"] == device)
                and e["ts"] >= after]

    def wait(self, kind, device, after=0.0, timeout=120, pred=None):
        dl = time.time() + timeout
        while time.time() < dl:
            for e in self.snap(kind, device, after):
                if pred is None or pred(e):
                    return e
            time.sleep(1)
        raise AssertionError(f"timeout esperando {kind} de {device} (after={after:.0f})")

    def stop(self):
        try:
            self._c.loop_stop()
            self._c.disconnect()
        except Exception:
            pass


def _mval(m):
    for f in ("int_value", "long_value", "float_value", "double_value",
              "boolean_value", "string_value"):
        if m.HasField(f):
            return getattr(m, f)
    return None


def _eng_unit(metric):
    ps = metric.properties
    for k, v in zip(ps.keys, ps.values):
        if k == "engUnit":
            return v.string_value
    return None


def _numeric_reading(pb):
    """O valor numerico (nao-booleano) do DDATA da sonda — a leitura de temperatura."""
    for m in pb.metrics:
        v = _mval(m)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def _rebirth(f, sniff, timeout=180):
    """Reinicia o delivery -> nova sessao Sparkplug (NBIRTH + DBIRTH de todo
    device ativo) ja com o sniffer ligado. Devolve o instante do restart."""
    t = time.time()
    f.restart("edge-delivery")
    sniff.wait("NBIRTH", None, after=t, timeout=timeout,
               pred=lambda e: e["node"] == NODE and e["device"] is None)
    return t


def _pub_telemetry(cli, device_id, temperature, running=True):
    body = json.dumps({
        "device_id": device_id,
        "ts": int(time.time() * 1000),
        "readings": {"temperature": round(float(temperature), 4), "running": bool(running)},
    })
    cli.publish(f"sida/ingest/{device_id}/telemetry", body, qos=0)
    return time.time()


# --------------------------------------------------------------------------- T2.5
def test_isa95_mapeia_dispositivo_sem_clp(etapa2_node, require_paho, spb_pb2):
    """O device `interedge` sem CLP e mapeado na hierarquia ISA-95 pelo
    manifesto: o `DBIRTH`/`DDATA` de `esp32_a` sai no topico
    spBv1.0/{group}/.../{node}/Area_1_Line_1_ESP32_A e a metrica Temperature
    carrega engUnit='C' — exatamente como um device com CLP."""
    f = etapa2_node
    assert f.wait_http(), "edge-core nao subiu"

    st, mani = f.get_manifest()
    assert st == 200, f"GET manifest {st}: {mani}"
    devs = mani["config"]["plant"]["areas"]["Area_1"]["lines"]["Line_1"]["devices"]
    assert devs.get("esp32_a", {}).get("connection", {}).get("protocol") == "interedge", devs
    assert "pump_01" in devs, "o device Modbus de nao-regressao sumiu do manifesto"

    sniff = UnsSniffer(require_paho, spb_pb2, f.UNS_PORT)
    try:
        t = _rebirth(f, sniff)
        db = sniff.wait("DBIRTH", DEV_ESP, after=t, timeout=150)
        dd = sniff.wait("DDATA", DEV_ESP, after=db["ts"], timeout=60)

        # topico ISA-95: group + node + device derivado do asset_context.path
        assert db["node"] == NODE, f"DBIRTH de {DEV_ESP} no node errado: {db['node']}"

        by_name = {m.name: m for m in db["pb"].metrics}
        assert {"Temperature", "Running"} <= set(by_name), f"DBIRTH sem as metricas: {set(by_name)}"
        assert _eng_unit(by_name["Temperature"]) == "°C", "Temperature sem engUnit='°C' no DBIRTH"

        b_aliases = {m.alias for m in db["pb"].metrics if m.HasField("alias")}
        assert len(b_aliases) >= 2, f"DBIRTH sem aliases: {b_aliases}"
        for m in dd["pb"].metrics:
            assert m.HasField("alias") and m.alias in b_aliases, "DDATA fora do alias_map do DBIRTH"
            assert not m.HasField("name"), "DDATA do device interedge com name (devia ser so alias)"
    finally:
        sniff.stop()


# --------------------------------------------------------------------------- T2.6
def test_pipeline_interedge_ponta_a_ponta(etapa2_node, require_paho, spb_pb2):
    """Passos 1-7 de 3.1: a leitura do sensor simulado atravessa
    interedge -> adapter -> context (ISA-95) -> delivery (Sparkplug) -> UNS,
    EM PARALELO ao Modbus (pump_01), sem regressao; leitura malformada e
    descartada; o `mqtt-ingest` cai e volta e o adaptador reconecta sozinho."""
    mqtt = require_paho
    f = etapa2_node
    assert f.wait_http(), "edge-core nao subiu"

    sniff = UnsSniffer(mqtt, spb_pb2, f.UNS_PORT)
    ing = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-s7-ingpub")
    ing.loop_start()
    try:
        t = _rebirth(f, sniff)
        sniff.wait("DBIRTH", DEV_ESP, after=t, timeout=150)
        sniff.wait("DBIRTH", DEV_PUMP, after=t, timeout=120)

        # (passo 5/6) os dois devices publicam DDATA em paralelo e continuamente
        t_win = time.time()
        time.sleep(18)
        esp = sniff.snap("DDATA", DEV_ESP, after=t_win)
        pump = sniff.snap("DDATA", DEV_PUMP, after=t_win)
        assert len(esp) >= 8, f"poucos DDATA de {DEV_ESP} em 18s: {len(esp)}"
        assert len(pump) >= 8, f"poucos DDATA de {DEV_PUMP} em 18s (regressao Modbus): {len(pump)}"
        # sem lacuna > 3x o periodo (~1s) em nenhum dos dois
        for tag, evs in ((DEV_ESP, esp), (DEV_PUMP, pump)):
            ts = sorted(e["ts"] for e in evs)
            gaps = [b - a for a, b in zip(ts, ts[1:]) if (b - a) > 3.0]
            assert not gaps, f"{tag}: lacuna(s) de DDATA {gaps}"

        # (passo 5) valores de esp32_a batem com o publicado no mqtt-ingest (escala 1.0)
        pub_temps = []
        probe = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-s7-valcheck")
        probe.on_message = lambda c, u, m: pub_temps.append(json.loads(m.payload)["readings"]["temperature"])
        probe.subscribe("sida/ingest/esp32_a/telemetry", qos=0)
        probe.loop_start()
        v0 = time.time()
        time.sleep(8)
        probe.loop_stop(); probe.disconnect()
        assert pub_temps, "nao capturou telemetry de esp32_a no mqtt-ingest"
        lo, hi = min(pub_temps) - 0.5, max(pub_temps) + 0.5
        dd_temps = [_numeric_reading(e["pb"]) for e in sniff.snap("DDATA", DEV_ESP, after=v0)]
        dd_temps = [x for x in dd_temps if x is not None]
        assert any(lo <= x <= hi for x in dd_temps), (
            f"nenhum DDATA de {DEV_ESP} na faixa publicada [{lo:.2f},{hi:.2f}]: {dd_temps[:8]}"
        )

        # (passo 7a) leitura malformada -> descartada, sem device fantasma, sem quebrar o fluxo
        n_before = len(sniff.snap("DDATA", DEV_ESP))
        for bad in ["nao-e-json",
                    json.dumps({"readings": {"x": 1}}),
                    json.dumps({"device_id": "esp32_ghost", "readings": {"t": 1}})]:
            ing.publish("sida/ingest/esp32_ghost/telemetry", bad, qos=0)
            time.sleep(0.4)
        time.sleep(10)
        ghost = [e for e in sniff.ev if e["device"] and "GHOST" in e["device"].upper()]
        assert not ghost, f"leitura malformada gerou trafego no UNS: {ghost}"
        assert len(sniff.snap("DDATA", DEV_ESP)) > n_before, "esp32_a parou apos a msg malformada"
        assert "[interedge] descartado" in f.logs("edge-ingestion"), "adaptador nao logou o descarte"

        # (passo 7b) mqtt-ingest cai e volta -> o adaptador reconecta sozinho
        t_bounce = time.time()
        f.restart("mqtt-ingest")
        dd_after = sniff.wait("DDATA", DEV_ESP, after=t_bounce + 3, timeout=90)
        assert dd_after["ts"] > t_bounce, "sem DDATA de esp32_a apos o bounce do mqtt-ingest"
    finally:
        ing.loop_stop(); ing.disconnect()
        sniff.stop()


# --------------------------------------------------------------------------- T2.RPT
def test_report_e_aceite(etapa2_node, require_paho, spb_pb2):
    """Passo 8: roda o cenario ponta a ponta com a SONDA `esp32_b` (telemetry
    publicada pelo teste com valores unicos) e emite test/etapa2/report.json:
    latencia sensor->UNS (p50/p95), perda interedge, ISA-95 ok, source_protocol
    observado, overhead CPU/RAM do mqtt-ingest e do ingestion."""
    mqtt = require_paho
    f = etapa2_node
    assert f.wait_http(), "edge-core nao subiu"

    sniff = UnsSniffer(mqtt, spb_pb2, f.UNS_PORT)
    ing = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-s7-rpt-pub")
    ing.loop_start()
    try:
        t = _rebirth(f, sniff)
        sniff.wait("DBIRTH", DEV_ESP, after=t, timeout=150)
        sniff.wait("DBIRTH", DEV_PUMP, after=t, timeout=120)

        stats = f.docker_stats()

        # --- sonda de latencia: N leituras de esp32_b com temperatura unica ---
        N = 24
        pub_at: dict[float, float] = {}
        for i in range(N):
            temp = 900.0 + i * 0.25          # exatamente representavel em float32
            pub_at[round(temp, 4)] = _pub_telemetry(ing, "esp32_b", temp)
            time.sleep(1.0)
        time.sleep(8)  # deixa as ultimas atravessarem

        # casa cada DDATA de esp32_b com a leitura publicada (escala 1.0)
        latencies: list[float] = []
        matched: set[float] = set()
        for e in sniff.snap("DDATA", DEV_ESP_B):
            v = _numeric_reading(e["pb"])
            if v is None:
                continue
            key = min(pub_at, key=lambda k: abs(k - v))
            if abs(key - v) <= 0.05 and key not in matched:
                matched.add(key)
                latencies.append(e["ts"] - pub_at[key])
        latencies.sort()

        assert latencies, "nenhum DDATA de esp32_b casou com as leituras publicadas"
        perda = N - len(matched)

        def _pct(p):
            if not latencies:
                return None
            k = min(len(latencies) - 1, int(round((p / 100.0) * (len(latencies) - 1))))
            return round(latencies[k], 4)

        # --- ISA-95: o DBIRTH da sonda resolve o path ate ESP32_B com engUnit ---
        db_b = sniff.wait("DBIRTH", DEV_ESP_B, after=t, timeout=30)
        by_name = {m.name: m for m in db_b["pb"].metrics}
        isa95_ok = ({"Temperature", "Running"} <= set(by_name)
                    and _eng_unit(by_name.get("Temperature")) == "°C"
                    and db_b["node"] == NODE)

        # --- source_protocol observado por device que chegou ao UNS ---
        _, mani = f.get_manifest()
        devs = mani["config"]["plant"]["areas"]["Area_1"]["lines"]["Line_1"]["devices"]
        observed = {}
        for dev_key, dev_topic in (("esp32_b", DEV_ESP_B), ("pump_01", DEV_PUMP)):
            if sniff.snap("DDATA", dev_topic):
                observed[dev_topic] = devs[dev_key]["connection"]["protocol"]

        stats_names = {k: v for k, v in stats.items()
                       if k.endswith("mqtt-ingest") or k.endswith("edge-ingestion")}

        report = {
            "cenario": "SDD Etapa 2 §3.1 — ingestao InterEdge ponta a ponta (sonda esp32_b)",
            "node": NODE,
            "devices": {"interedge": DEV_ESP_B, "modbus": DEV_PUMP},
            "amostras_latencia": len(latencies),
            "latencia_sensor_uns_s": {"p50": _pct(50), "p95": _pct(95),
                                      "min": round(latencies[0], 4), "max": round(latencies[-1], 4)},
            "interedge_publicadas": N,
            "interedge_entregues": len(matched),
            "perda": perda,
            "isa95_ok": bool(isa95_ok),
            "source_protocol_observado": observed,
            "overhead": {name: st for name, st in sorted(stats_names.items())},
            "nao_regressao_modbus": bool(sniff.snap("DDATA", DEV_PUMP)),
            "aceite": bool(perda == 0 and isa95_ok and latencies
                           and sniff.snap("DDATA", DEV_PUMP)),
        }
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        # --- validacao do schema/criterio ---
        r = json.loads(REPORT.read_text(encoding="utf-8"))
        for k in ("latencia_sensor_uns_s", "perda", "isa95_ok",
                  "source_protocol_observado", "overhead", "aceite"):
            assert k in r, f"report.json sem a chave {k!r}"
        assert r["perda"] == 0, f"perda != 0 no regime estavel: {r['perda']}"
        assert r["isa95_ok"] is True, "mapeamento ISA-95 da sonda falhou"
        assert r["source_protocol_observado"].get(DEV_ESP_B) == "interedge"
        assert r["source_protocol_observado"].get(DEV_PUMP) == "modbus_tcp"
        assert r["nao_regressao_modbus"] is True, "pump_01 (Modbus) nao publicou DDATA no cenario"
        assert r["aceite"] is True, r
    finally:
        ing.loop_stop(); ing.disconnect()
        sniff.stop()
