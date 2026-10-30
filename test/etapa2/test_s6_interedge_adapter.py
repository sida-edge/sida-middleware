"""Checkpoints da Sprint S6 — adaptador de ingestao InterEdge.

- test_mqtt_in_recebe_do_simulador -> T2.2b (mqtt in do transporte de ingestao)
- test_adapter_normaliza_e_injeta   -> T2.3  (interedgeAdapter -> payload interno no IPC do ramo Modbus)
"""
from __future__ import annotations

import json
import time

import pytest

pytestmark = pytest.mark.heavy


# --------------------------------------------------------------------------- T2.2b
def test_mqtt_in_recebe_do_simulador(etapa2_node):
    """O `mqtt in` novo conecta ao broker de INGESTAO (via ${INGEST_BROKER_HOST})
    e assina o topico de telemetry — visivel no log do ingestion. O ramo Modbus
    (setupClient/modbusPolling) segue no ar em paralelo."""
    f = etapa2_node
    assert f.wait_http(), "edge-core nao subiu"

    deadline = time.time() + 120
    connected = False
    logs = ""
    while time.time() < deadline:
        logs = f.logs("edge-ingestion")
        if "Connected to broker" in logs and "mqtt-ingest" in logs:
            connected = True
            break
        time.sleep(3)
    assert connected, (
        "o mqtt in de ingestao nao conectou ao broker mqtt-ingest "
        f"(a substituicao de ${{INGEST_BROKER_HOST}} pode ter falhado):\n{logs[-2500:]}"
    )

    # o ramo Modbus nao foi afetado: o setupClient roda e loga a conexao Modbus
    assert "MODBUS" in logs or "Modbus" in logs or "modbus" in logs, (
        f"o ramo Modbus do ingestion nao aparece no log (adaptador nao pode te-lo quebrado):\n{logs[-2000:]}"
    )


# --------------------------------------------------------------------------- T2.3
def test_adapter_normaliza_e_injeta(etapa2_node, require_paho, spb_pb2):
    """O interedgeAdapter normaliza a leitura do simulador para o payload
    interno (source_protocol=='interedge', data com as chaves do metrics_mapping)
    e a injeta no mesmo caminho do Modbus — o context/delivery a leva ao UNS.
    Uma leitura malformada e descartada sem quebrar o fluxo."""
    f = etapa2_node
    for _ in range(3):
        if f.wait_http():
            break
    assert f.wait_http(), "edge-core nao subiu"

    mqtt = require_paho
    pb2 = spb_pb2

    # assina o UNS isolado
    events = []

    def on_msg(c, u, m):
        parts = m.topic.split("/")
        if len(parts) < 4:
            return
        pb = pb2.Payload()
        try:
            pb.ParseFromString(m.payload)
        except Exception:
            return
        events.append({"kind": parts[2], "device": parts[4] if len(parts) > 4 else None,
                       "pb": pb, "ts": time.time()})

    sub = f.mqtt_connect(mqtt, f.UNS_PORT, "e2-s6-uns")
    sub.on_message = on_msg
    sub.subscribe("spBv1.0/#", qos=1)
    sub.loop_start()

    # O NBIRTH/DBIRTH de cada device sai uma unica vez por sessao Sparkplug, no
    # arranque do delivery — antes deste subscriber existir. Reinicia o delivery
    # para abrir uma sessao nova (NBIRTH + DBIRTH de todo device ativo) ja com o
    # subscriber ligado. O esp32-sim segue publicando esp32_a o tempo todo.
    f.restart("edge-delivery")

    # (a) o esp32-sim ja publica esp32_a: espera DBIRTH+DDATA do device interedge no UNS
    dl = time.time() + 180
    ddata = None
    dbirth = None
    while time.time() < dl:
        for e in events:
            if e["device"] == f.DEVICE_ESP and e["kind"] == "DBIRTH":
                dbirth = e
            if e["device"] == f.DEVICE_ESP and e["kind"] == "DDATA":
                ddata = e
        if dbirth and ddata:
            break
        time.sleep(2)
    assert dbirth is not None, f"sem DBIRTH de {f.DEVICE_ESP} no UNS. vistos: {sorted({(x['kind'], x['device']) for x in events})}"
    assert ddata is not None, f"sem DDATA de {f.DEVICE_ESP} no UNS"

    # o context/delivery trataram como device interedge (metricas Temperature/Running com alias)
    names = {m.name for m in dbirth["pb"].metrics}
    assert {"Temperature", "Running"} <= names, f"DBIRTH de {f.DEVICE_ESP} sem as metricas do device: {names}"
    for m in ddata["pb"].metrics:
        assert m.HasField("alias"), "DDATA do device interedge sem alias"
        assert not m.HasField("name"), "DDATA do device interedge com name"

    # (b) leitura malformada: publica lixo no broker de ingestao e confirma que
    #     nao gera DBIRTH/DDATA de um device fantasma nem interrompe o esp32_a
    pub = f.mqtt_connect(mqtt, f.INGEST_PORT, "e2-s6-ingpub")
    n_before = len([e for e in events if e["device"] == f.DEVICE_ESP and e["kind"] == "DDATA"])
    for bad in ["nao-e-json", json.dumps({"readings": {"x": 1}}),  # sem device_id
                json.dumps({"device_id": "esp32_ghost", "readings": {"t": 1}})]:  # fora do manifesto
        pub.publish("sida/ingest/esp32_ghost/telemetry", bad, qos=0)
        time.sleep(0.5)
    time.sleep(12)

    ghost = [e for e in events if e["device"] and "GHOST" in (e["device"] or "").upper()]
    assert not ghost, f"leitura malformada gerou trafego no UNS: {ghost}"
    n_after = len([e for e in events if e["device"] == f.DEVICE_ESP and e["kind"] == "DDATA"])
    assert n_after > n_before, "o esp32_a parou de publicar depois da mensagem malformada (fluxo quebrou)"

    sub.loop_stop(); sub.disconnect(); pub.disconnect()

    # log do adaptador: descartes com motivo claro
    ing_logs = f.logs("edge-ingestion")
    assert "[interedge] descartado" in ing_logs, f"o adaptador nao logou o descarte:\n{ing_logs[-2000:]}"
