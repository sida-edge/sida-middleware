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


SCALAR_VALUE_FIELDS = ("int_value", "long_value", "float_value",
                       "double_value", "boolean_value", "string_value")


def has_scalar_value(m) -> bool:
    return any(m.HasField(f) for f in SCALAR_VALUE_FIELDS)


def prop_str(m, key: str):
    ps = m.properties
    for k, v in zip(ps.keys, ps.values):
        if k == key:
            return v.string_value
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


# --------------------------------------------------------------------------- T1A.4
def test_dbirth_define_aliases(plane_a_node, spb_bus):
    """O DBIRTH de Line_1/Pump_01 traz Temperature e Running como DEFINICOES:
    name + datatype Sparkplug + alias inteiro distinto + engUnit; sem valores."""
    dev = plane_a_node.DEVICE_ID
    t = time.time()
    plane_a_node.restart_delivery()
    spb_bus.wait_for("NBIRTH", after_ts=t, timeout=180)
    dbirth = spb_bus.wait_for("DBIRTH", after_ts=t, timeout=120,
                              predicate=lambda e: e["device"] == dev)
    mm = metric_map(dbirth["payload"])
    assert {"Temperature", "Running"} <= set(mm), f"DBIRTH sem as metricas esperadas: {list(mm)}"

    for name in ("Temperature", "Running"):
        m = mm[name]
        assert m.HasField("alias") and m.alias >= 1, f"{name}: alias inteiro ausente no DBIRTH"
        assert m.datatype != 0, f"{name}: datatype Sparkplug ausente"
        assert not has_scalar_value(m), f"{name}: DBIRTH traz valor (deveria ser so definicao)"

    assert mm["Temperature"].alias != mm["Running"].alias, "aliases nao sao distintos"
    assert prop_str(mm["Temperature"], "engUnit") == "°C", "engUnit de Temperature perdido no DBIRTH"


# --------------------------------------------------------------------------- T1A.5
def test_ddata_por_alias(plane_a_node, spb_bus):
    """Todo DDATA referencia metricas SO por alias (sem name); os aliases batem
    com os do DBIRTH; nenhum DDATA antes do DBIRTH da sessao."""
    dev = plane_a_node.DEVICE_ID
    t = time.time()
    plane_a_node.restart_delivery()
    nbirth = spb_bus.wait_for("NBIRTH", after_ts=t, timeout=180)
    dbirth = spb_bus.wait_for("DBIRTH", after_ts=nbirth["ts_recv"], timeout=120,
                              predicate=lambda e: e["device"] == dev)
    birth_aliases = {m.alias for m in dbirth["payload"].metrics if m.HasField("alias")}
    assert len(birth_aliases) >= 2, f"DBIRTH declarou poucos aliases: {birth_aliases}"

    # nenhum DDATA ENTRE o NBIRTH e o DBIRTH desta sessao (janela da sessao —
    # DDATA de sessao anterior, antes do NBIRTH novo, e trafego residual)
    early = [e for e in spb_bus.snapshot("DDATA")
             if e["device"] == dev and nbirth["ts_recv"] <= e["ts_recv"] < dbirth["ts_recv"]]
    assert not early, f"{len(early)} DDATA entre o NBIRTH e o DBIRTH da sessao"

    time.sleep(6)   # deixa alguns ciclos de DDATA acontecerem
    ddatas = [e for e in spb_bus.snapshot("DDATA")
              if e["device"] == dev and e["ts_recv"] >= dbirth["ts_recv"]]
    assert len(ddatas) >= 2, f"poucos DDATA capturados ({len(ddatas)})"
    for e in ddatas:
        assert e["payload"].metrics, "DDATA sem metricas"
        for m in e["payload"].metrics:
            assert m.HasField("alias"), "metrica de DDATA sem alias"
            assert m.alias in birth_aliases, f"alias {m.alias} do DDATA nao esta no DBIRTH"
            assert not m.HasField("name") and not m.name, f"DDATA traz name='{m.name}' (so alias)"
            assert has_scalar_value(m), "DDATA sem valor"


# --------------------------------------------------------------------------- T1A.6
def test_ndeath_gracioso(plane_a_node, spb_bus):
    """docker stop (SIGTERM) gera UM NDEATH explicito com o bdSeq da sessao,
    antes do close limpo; o Will nao dispara em duplicidade."""
    t = time.time()
    plane_a_node.restart_delivery()
    nbirth = spb_bus.wait_for("NBIRTH", after_ts=t, timeout=180)
    bdseq = bdseq_of(nbirth["payload"])
    assert bdseq is not None

    t_stop = time.time()
    plane_a_node.stop_delivery()
    ndeath = spb_bus.wait_for("NDEATH", after_ts=t_stop, timeout=90)
    assert bdseq_of(ndeath["payload"]) == bdseq, "NDEATH gracioso com bdSeq da sessao errado"

    time.sleep(10)   # janela para um eventual LWT atrasado
    deaths = [e for e in spb_bus.snapshot("NDEATH") if e["ts_recv"] >= t_stop]
    assert len(deaths) == 1, (
        f"esperava 1 NDEATH (explicito); vieram {len(deaths)} (Will em duplicidade?)"
    )

    plane_a_node.start_delivery()   # restaura o no para o resto da suite


# --------------------------------------------------------------------------- T1A.7
def test_contabilidade_seq(plane_a_node, spb_bus):
    """seq da sessao e continuo mod 256 (NBIRTH=0 -> +1 por mensagem publicada,
    rolagem 255->0 sem salto nem reuso); nao ha rebirth no meio."""
    t = time.time()
    plane_a_node.restart_delivery()
    nbirth = spb_bus.wait_for("NBIRTH", after_ts=t, timeout=180)
    t_nb = nbirth["ts_recv"]

    # junta > 256 mensagens Sparkplug desta sessao, na ordem de chegada
    deadline = time.time() + 300
    seq_events: list[dict] = []
    while time.time() < deadline:
        seq_events = [e for e in spb_bus.snapshot()
                      if e["ts_recv"] >= t_nb and e["kind"] in ("NBIRTH", "DBIRTH", "DDATA")]
        if len(seq_events) > 260:
            break
        time.sleep(3)
    assert len(seq_events) > 256, f"coletou so {len(seq_events)} mensagens da sessao"

    seqs = [e["payload"].seq for e in seq_events]
    assert seqs[0] == 0, f"1a mensagem da sessao (NBIRTH) deveria ter seq=0, veio {seqs[0]}"
    for i in range(1, len(seqs)):
        assert seqs[i] == (seqs[i - 1] + 1) % 256, (
            f"quebra de seq no indice {i}: ...{seqs[max(0, i - 2):i + 1]}"
        )
    assert any(seqs[i - 1] == 255 and seqs[i] == 0 for i in range(1, len(seqs))), (
        "seq nao rolou 255->0 na janela coletada"
    )
    assert sum(1 for e in seq_events if e["kind"] == "NBIRTH") == 1, (
        "houve um rebirth no meio da sessao (seq/bdSeq nao estaveis)"
    )
