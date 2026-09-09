"""Teste de aceite final da Etapa 1 (SDD 3.1) — injeção de falha na frota.

Sprint S4, tasks T4.3–T4.6:
- test_frota_integra_e_injecao  -> T4.3 (passos 1–2: t0 nos dois planos + derrubada em t1)
- test_deteccao_dois_planos     -> T4.4 (passos 3–5: NDEATH/LWT casado, pares `down`, sobreviventes sem perda)
- test_religamento              -> T4.5 (passo 6: edge_002 volta, novo NBIRTH com bdSeq maior)
- test_report_e_aceite          -> T4.6 (passo 7: cenário completo + test/etapa1/report.json)

Todos [heavy]: usam a fixture `full_fleet` (3 nós completos + Mosquitto isolado).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.heavy

GROUP = "Enterprise_Site"
DEVICE = "Area_1_Line_1_Pump_01"
GW = {1: "sida_edge_001", 2: "sida_edge_002", 3: "sida_edge_003"}
REPORT = Path(__file__).parent / "report.json"


# --------------------------------------------------------------------------- sniffer
class Sniffer:
    """Assina spBv1.0/# e decodifica cada payload; guarda eventos com ts_recv."""

    def __init__(self, mqtt_mod, pb2, host, port):
        self._pb2 = pb2
        self.ev: list[dict] = []
        self._lock = threading.Lock()
        self._c = mqtt_mod.Client(mqtt_mod.CallbackAPIVersion.VERSION2, client_id="s4-sniffer")
        self._c.on_connect = lambda c, u, f, rc, p=None: c.subscribe("spBv1.0/#", qos=1)
        self._c.on_message = self._on
        for _ in range(30):
            try:
                self._c.connect(host, port, keepalive=15)
                break
            except OSError:
                time.sleep(2)
        else:
            raise AssertionError(f"nao conectou ao Mosquitto em {host}:{port}")
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
                "kind": parts[2], "edge": parts[3],
                "device": parts[4] if len(parts) > 4 else None,
                "seq": pb.seq, "pb": pb, "ts": time.time(),
            })

    def snap(self, kind=None, edge=None, after=0.0):
        with self._lock:
            evs = list(self.ev)
        return [e for e in evs
                if (kind is None or e["kind"] == kind)
                and (edge is None or e["edge"] == edge)
                and e["ts"] >= after]

    def wait(self, kind, edge, after=0.0, timeout=90, pred=None):
        dl = time.time() + timeout
        while time.time() < dl:
            for e in self.snap(kind, edge, after):
                if pred is None or pred(e):
                    return e
            time.sleep(1)
        raise AssertionError(f"timeout esperando {kind} de {edge} (after={after:.0f})")

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


def _bdseq(pb):
    for m in pb.metrics:
        if m.name == "bdSeq":
            return _mval(m)
    return None


@pytest.fixture(scope="session")
def sniffer(require_paho, spb_pb2, full_fleet):
    s = Sniffer(require_paho, spb_pb2, full_fleet.MQTT_HOST, full_fleet.MQTT_PORT)
    try:
        yield s
    finally:
        s.stop()


# --------------------------------------------------------------------------- helpers
def _fresh_cycle(fleet, sniffer, node):
    """Reinicia o delivery de `node` e devolve (nbirth, dbirth, primeiro ddata)."""
    t = time.time()
    fleet.restart_service(f"edge{node}-delivery")
    nb = sniffer.wait("NBIRTH", GW[node], after=t, timeout=150)
    db = sniffer.wait("DBIRTH", GW[node], after=t, timeout=120,
                      pred=lambda e: e["device"] == DEVICE)
    dd = sniffer.wait("DDATA", GW[node], after=db["ts"], timeout=60,
                      pred=lambda e: e["device"] == DEVICE)
    return nb, db, dd


def _peer_down_at(fleet, observer, target_cid, t1, timeout=15):
    """Segundos entre t1 e o instante em que `observer` reporta `target` down."""
    dl = time.time() + timeout
    while time.time() < dl:
        for p in fleet.peers_api(observer)["peers"]:
            if p["id"] == target_cid and p["state"] == "down":
                return time.time() - t1
        time.sleep(0.5)
    return None


def _ddata_losses(sniffer, edge, t_from, t_to, scan_ms=500):
    """Conta 'perdas' = lacunas de publicacao > 3x o scan_rate entre t_from e t_to."""
    ds = sorted((e["ts"] for e in sniffer.snap("DDATA", edge)
                 if t_from <= e["ts"] <= t_to))
    gap = 3 * scan_ms / 1000.0
    return sum(1 for a, b in zip(ds, ds[1:]) if (b - a) > gap)


# --------------------------------------------------------------------------- T4.3
def test_frota_integra_e_injecao(full_fleet, sniffer):
    """Passo 1: em t0 os 3 nós mostram NBIRTH(seq=0, bdSeq) -> DBIRTH(alias) ->
    DDATA(por alias); GET /api/system/peers vê os outros dois `alive`.
    Passo 2: derruba edge_002 e cronometra t1."""
    f = full_fleet
    for n in (1, 2, 3):
        assert f.wait_http(n), f"edge{n}-core nao subiu"

    for n in (1, 2, 3):
        nb, db, dd = _fresh_cycle(f, sniffer, n)
        assert nb["seq"] == 0, f"NBIRTH de {GW[n]} com seq={nb['seq']}"
        assert _bdseq(nb["pb"]) is not None, f"NBIRTH de {GW[n]} sem bdSeq"
        b_aliases = {m.alias for m in db["pb"].metrics if m.HasField("alias")}
        assert len(b_aliases) >= 2, f"DBIRTH de {GW[n]} sem aliases: {b_aliases}"
        for m in dd["pb"].metrics:
            assert m.HasField("alias") and m.alias in b_aliases, f"DDATA de {GW[n]} fora do alias_map"
            assert not m.HasField("name"), f"DDATA de {GW[n]} com name"

    # plano B: cada nó vê os outros dois alive
    deadline = time.time() + 40
    while time.time() < deadline:
        if all(
            {p["id"] for p in f.peers_api(n)["peers"] if p["state"] == "alive"}
            == {f.CONTROLLER_ID[k] for k in (1, 2, 3) if k != n}
            for n in (1, 2, 3)
        ):
            break
        time.sleep(1)
    else:
        pytest.fail(f"pares nao alive: {[f.peers_api(n) for n in (1, 2, 3)]}")

    # passo 2: injeção
    t1 = time.time()
    f.stop_node(2)
    assert time.time() - t1 < 30, "docker stop de edge_002 demorou demais"
    # confirma que edge_002 saiu
    import requests
    with pytest.raises(requests.RequestException):
        requests.get(f"http://localhost:{f.HTTP_PORT[2]}/api/system/info", timeout=3)

    f.start_node(2)  # restaura para os testes seguintes
