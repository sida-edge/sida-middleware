"""Checkpoints da Sprint S5 — contrato `interedge` + transporte + simulador.

- test_manifesto_interedge_aceito          -> T2.4
- test_broker_ingestao_isolado             -> T2.2a
- test_simulador_publica_perfil_e_leituras -> T2.SIM
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.heavy

COMPOSE = Path(__file__).parent / "compose.test.yml"


def _line_devices(devices: dict) -> dict:
    return {"plant": {"enterprise": "Enterprise", "site": "Site",
                      "areas": {"Area_1": {"lines": {"Line_1": {"devices": devices}}}}},
            "receivers": {"uns": {"protocol": "mqtt", "host": "mosquitto-uns", "port": 1883,
                                  "endpoint": "", "username": "", "password": ""}}}


_ISA95 = {"standard": "ISA-95", "path": [
    {"type": "area", "id": "Area_1"}, {"type": "line", "id": "Line_1"},
    {"type": "equipment", "id": "ESP32_A"}]}
_MM = {"temperature": {"name": "Temperature", "scale_factor": 1.0, "unit": "°C", "data_type": "float"}}


# --------------------------------------------------------------------------- T2.4
def test_manifesto_interedge_aceito(etapa2_core):
    """`interedge` no enum Connection.Protocol; device interedge sem
    host/port/scan_rate e aceito; sem asset_context e rejeitado; um device
    modbus_tcp sem host segue rejeitado (nao-regressao)."""
    f = etapa2_core

    got = f.go_test("./internal/core/domain/...")
    assert got.returncode == 0, f"go test do dominio falhou:\n{got.stdout}\n{got.stderr}"

    assert f.wait_http(), "edge-core nao subiu"

    # (a) device interedge valido -> 200
    ok = f.post_manifest(_line_devices({
        "esp32_a": {"enabled": True, "connection": {"protocol": "interedge"},
                    "asset_context": _ISA95, "metrics_mapping": _MM},
    }))
    assert ok.status_code == 200, f"manifesto interedge valido rejeitado: {ok.status_code} {ok.text}"

    # (b) device interedge SEM asset_context -> 400
    bad = f.post_manifest(_line_devices({
        "esp32_x": {"enabled": True, "connection": {"protocol": "interedge"},
                    "metrics_mapping": _MM},
    }))
    assert bad.status_code == 400, f"interedge sem asset_context devia ser 400, veio {bad.status_code}"

    # (c) device modbus_tcp SEM host -> 400 (regressao da validacao)
    modbad = f.post_manifest(_line_devices({
        "pump_x": {"enabled": True,
                   "connection": {"protocol": "modbus_tcp", "port": 502, "scan_rate_ms": 1000},
                   "asset_context": _ISA95,
                   "metrics_mapping": {"40001": {"register_type": "holding", "name": "T",
                                                 "scale_factor": 1.0, "unit": "", "data_type": "int16"}}},
    }))
    assert modbad.status_code == 400, f"modbus_tcp sem host devia ser 400, veio {modbad.status_code}"


# --------------------------------------------------------------------------- T2.2a
def test_broker_ingestao_isolado(etapa2_core, require_paho):
    """O broker de ingestao dedicado sobe, entrega pub/sub, e e distinto do
    broker do UNS (portas host diferentes; UNS nao recebe nada dele)."""
    mqtt = require_paho
    f = etapa2_core

    got = {"n": 0}
    sub = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-ingest-probe")
    sub.on_message = lambda c, u, m: got.update(n=got["n"] + 1)
    sub.subscribe("sida/ingest/#", qos=0)
    sub.loop_start()
    time.sleep(0.5)

    pub = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-ingest-pubprobe")
    for _ in range(5):
        pub.publish("sida/ingest/probe/telemetry", '{"device_id":"probe","readings":{"x":1}}', qos=0)
        time.sleep(0.3)
    time.sleep(1)
    sub.loop_stop(); sub.disconnect(); pub.disconnect()
    assert got["n"] >= 3, f"broker de ingestao nao entregou pub/sub (n={got['n']})"

    # portas host distintas na compose
    txt = COMPOSE.read_text(encoding="utf-8")
    assert f'"{f.INGEST_PORT}:1883"' in txt and f'"{f.UNS_PORT}:1883"' in txt
    assert f.INGEST_PORT != f.UNS_PORT

    # o UNS nao recebe nada do broker de ingestao
    f.wait_port(f.UNS_PORT, timeout=30)
    uns = f.mqtt_connect(mqtt, f.UNS_PORT, "e2-uns-probe")
    uns_msgs = []
    uns.on_message = lambda c, u, m: uns_msgs.append(m.topic)
    uns.subscribe("#", qos=0)
    uns.loop_start()
    pub2 = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-ingest-pub2")
    for _ in range(5):
        pub2.publish("sida/ingest/probe/telemetry", "x", qos=0)
        time.sleep(0.2)
    time.sleep(1)
    uns.loop_stop(); uns.disconnect(); pub2.disconnect()
    assert not [t for t in uns_msgs if t.startswith("sida/ingest")], \
        f"vazamento: o UNS recebeu topicos de ingestao: {uns_msgs}"


# --------------------------------------------------------------------------- T2.SIM
def test_simulador_publica_perfil_e_leituras(etapa2_core, require_compose, require_paho):
    """O mock de ESP32 publica um `profile` retido e `telemetry` periodica no
    broker de ingestao, cada leitura com uma metrica numerica e uma booleana."""
    mqtt = require_paho
    f = etapa2_core
    f._dc("up", "-d", "esp32-sim", timeout=400)
    try:
        seen = {"profile": None, "telemetry": []}

        def on_msg(c, u, m):
            payload = json.loads(m.payload.decode())
            if m.topic.endswith("/profile"):
                seen["profile"] = payload
            elif m.topic.endswith("/telemetry"):
                seen["telemetry"].append(payload)

        cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="e2-sim-probe")
        cli.on_message = on_msg
        cli.connect("localhost", f.INGEST_PORT, keepalive=15)
        cli.subscribe("sida/ingest/#", qos=1)
        cli.loop_start()

        dl = time.time() + 30
        while time.time() < dl and (seen["profile"] is None or len(seen["telemetry"]) < 3):
            time.sleep(1)
        cli.loop_stop(); cli.disconnect()

        assert seen["profile"] is not None, "profile retido nao recebido do simulador"
        assert seen["profile"]["device_id"] == "esp32_a"
        assert "temperature" in seen["profile"]["device_profile"]["metrics"]
        assert len(seen["telemetry"]) >= 3, f"poucas leituras: {len(seen['telemetry'])}"
        r0 = seen["telemetry"][0]["readings"]
        assert isinstance(r0.get("temperature"), (int, float))
        assert isinstance(r0.get("running"), bool)
    finally:
        f._dc("stop", "esp32-sim", timeout=60, check=False)
