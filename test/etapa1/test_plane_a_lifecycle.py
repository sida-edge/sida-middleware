"""Checkpoints funcionais da Sprint S2 — Plano A (ciclo de vida Sparkplug B).

SDD_SIDA_Etapa1_Ciclo_V3.md, secoes 5.1 e 5.4 (casos 1-3, 8) e tabela 3.3.2:

- test_bdseq_sessao_no_lwt   -> T1A.2 (bdSeq de sessao no LWT/NDEATH)
- test_nbirth_bdseq_e_reset  -> T1A.3 (bdSeq no NBIRTH + reset de estado)
- test_dbirth_define_aliases -> T1A.4 (DBIRTH declara definicoes com alias)
- test_ddata_por_alias       -> T1A.5 (DDATA referencia so por alias)
- test_ndeath_gracioso       -> T1A.6 (NDEATH explicito no SIGTERM)
- test_contabilidade_seq     -> T1A.7 (seq continuo mod 256, bdSeq constante)

Todos [heavy]: sobem a frota do plano A (fixture `plane_a_node`) contra o
Mosquitto isolado. O payload Sparkplug B e decodificado com o modulo gerado
de schemas/sparkplug_b.proto (fixture `spb_pb2`).
"""
from __future__ import annotations

import threading
import time

import pytest

pytestmark = pytest.mark.heavy


# --------------------------------------------------------------------------- helpers
class SpbBus:
    """Assina spBv1.0/# no Mosquitto de teste e decodifica cada payload.

    Guarda os eventos como dicts {kind, topic, device, payload(pb), ts_recv}.
    kind e um de NBIRTH/DBIRTH/DDATA/NDEATH/DCMD/... (3o segmento do topico).
    """

    def __init__(self, mqtt_mod, pb2, host: str, port: int):
        self._pb2 = pb2
        self.events: list[dict] = []
        self._lock = threading.Lock()
        self._cli = mqtt_mod.Client(
            mqtt_mod.CallbackAPIVersion.VERSION2, client_id="s2-spbbus"
        )
        self._cli.reconnect_delay_set(min_delay=1, max_delay=5)
        self._cli.on_message = self._on_message
        # re-assina a cada (re)conexao — o broker e bounçado nos testes
        self._cli.on_connect = lambda c, u, flags, rc, props=None: c.subscribe("spBv1.0/#", qos=1)
        for _ in range(30):
            try:
                self._cli.connect(host, port, keepalive=15)
                break
            except OSError:
                time.sleep(2)
        else:
            raise AssertionError(f"nao conectou ao Mosquitto de teste em {host}:{port}")
        self._cli.loop_start()

    def _on_message(self, _c, _u, m):
        parts = m.topic.split("/")
        kind = parts[2] if len(parts) > 2 else "?"
        pb = self._pb2.Payload()
        try:
            pb.ParseFromString(m.payload)
        except Exception:
            return
        ev = {
            "kind": kind,
            "topic": m.topic,
            "device": parts[4] if len(parts) > 4 else None,
            "payload": pb,
            "ts_recv": time.time(),
        }
        with self._lock:
            self.events.append(ev)

    def snapshot(self, kind: str | None = None) -> list[dict]:
        with self._lock:
            evs = list(self.events)
        return [e for e in evs if kind is None or e["kind"] == kind]

    def clear(self):
        with self._lock:
            self.events.clear()

    def wait_for(self, kind: str, *, after_ts: float = 0.0, timeout: float = 60.0,
                 predicate=None) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for e in self.snapshot(kind):
                if e["ts_recv"] < after_ts:
                    continue
                if predicate is None or predicate(e):
                    return e
            time.sleep(1)
        got = sorted({e["kind"] for e in self.snapshot()})
        raise AssertionError(
            f"timeout esperando {kind} (after_ts={after_ts:.0f}); tipos vistos: {got}"
        )

    def stop(self):
        try:
            self._cli.loop_stop()
            self._cli.disconnect()
        except Exception:
            pass


def metric_map(pb_payload) -> dict:
    """name -> Metric (para NBIRTH/DBIRTH, que trazem name)."""
    return {m.name: m for m in pb_payload.metrics}


def metric_value(m):
    """Extrai o valor escalar setado num Metric decodificado."""
    for f in ("int_value", "long_value", "float_value", "double_value",
              "boolean_value", "string_value"):
        if m.HasField(f):
            return getattr(m, f)
    return None


def bdseq_of(pb_payload):
    for m in pb_payload.metrics:
        if m.name == "bdSeq":
            return metric_value(m)
    return None


@pytest.fixture(scope="session")
def spb_bus(require_paho, spb_pb2, plane_a_node):
    bus = SpbBus(require_paho, spb_pb2, plane_a_node.MQTT_HOST, plane_a_node.MQTT_PORT)
    try:
        yield bus
    finally:
        bus.stop()


# --------------------------------------------------------------------------- T1A.2
def test_bdseq_sessao_no_lwt(plane_a_node, spb_bus):
    """O LWT (NDEATH que o broker publica numa morte abrupta) carrega o bdSeq
    da sessao, igual ao do NBIRTH daquela sessao, e incrementa a cada sessao.

    NBIRTH nao e retido -> para observa-lo desde o inicio da sessao forcamos
    uma reconexao/religamento do delivery em vez de contar com o startup da
    fixture."""
    # --- sessao A: religa o delivery so para capturar o NBIRTH desde o comeco ---
    t_a = time.time()
    plane_a_node.restart_delivery()
    nbirth_a = spb_bus.wait_for("NBIRTH", after_ts=t_a, timeout=180)
    bdseq_a = bdseq_of(nbirth_a["payload"])
    assert bdseq_a is not None, "NBIRTH sem metrica bdSeq"

    # --- reconexao MQTT forcada SEM matar o processo: bounce do Mosquitto.
    #     O delivery renova a sessao (novo bdSeq + novo will) ao reconectar. ---
    t_r = time.time()
    plane_a_node.restart_broker()
    time.sleep(2)
    nbirth_b = spb_bus.wait_for(
        "NBIRTH", after_ts=t_r, timeout=180,
        predicate=lambda e: bdseq_of(e["payload"]) is not None and bdseq_of(e["payload"]) > bdseq_a,
    )
    bdseq_b = bdseq_of(nbirth_b["payload"])
    assert bdseq_b >= bdseq_a + 1, f"bdSeq nao incrementou na reconexao: {bdseq_a} -> {bdseq_b}"

    # --- morte abrupta (SIGKILL): o broker publica o LWT da sessao B ---
    t_k = time.time()
    plane_a_node.kill_delivery()
    ndeath_b = spb_bus.wait_for("NDEATH", after_ts=t_k, timeout=120)
    assert bdseq_of(ndeath_b["payload"]) == bdseq_b, (
        f"bdSeq do LWT ({bdseq_of(ndeath_b['payload'])}) != NBIRTH da sessao B ({bdseq_b})"
    )
    plane_a_node.start_delivery()   # restaura o no para os testes seguintes


# --------------------------------------------------------------------------- T1A.3
def test_nbirth_bdseq_e_reset(plane_a_node, spb_bus):
    """A cada NBIRTH o estado de sessao e zerado: apos uma reconexao MQTT o
    DBIRTH do device ativo e reemitido (born_devices/alias_map limpos) e o
    NBIRTH sai com seq=0 e a metrica bdSeq da sessao."""
    dev = plane_a_node.DEVICE_ID

    # sessao A
    t_a = time.time()
    plane_a_node.restart_delivery()
    nbirth_a = spb_bus.wait_for("NBIRTH", after_ts=t_a, timeout=180)
    spb_bus.wait_for("DBIRTH", after_ts=t_a, timeout=120,
                     predicate=lambda e: e["device"] == dev)
    bdseq_a = bdseq_of(nbirth_a["payload"])
    assert bdseq_a is not None, "NBIRTH sem metrica bdSeq"
    assert nbirth_a["payload"].seq == 0, "NBIRTH nao saiu com seq=0"

    # reconexao MQTT (bounce do broker): nova sessao, mesmos devices
    t_b = time.time()
    plane_a_node.restart_broker()
    time.sleep(2)
    nbirth_b = spb_bus.wait_for(
        "NBIRTH", after_ts=t_b, timeout=180,
        predicate=lambda e: bdseq_of(e["payload"]) is not None and bdseq_of(e["payload"]) > bdseq_a,
    )
    dbirth_b = spb_bus.wait_for("DBIRTH", after_ts=t_b, timeout=120,
                                predicate=lambda e: e["device"] == dev)

    assert dbirth_b["ts_recv"] >= t_b, "DBIRTH nao foi reemitido apos a reconexao (mapas nao limpos)"
    assert nbirth_b["payload"].seq == 0
    assert bdseq_of(nbirth_b["payload"]) >= bdseq_a + 1
