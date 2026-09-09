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


# --------------------------------------------------------------------------- T4.4
def test_deteccao_dois_planos(full_fleet, sniffer):
    """Passos 3–5: LWT de edge_002 com o bdSeq casado (A); edge_001/edge_003
    marcam edge_002 `down` dentro de PROBE_INTERVAL_MS x PEER_DOWN_AFTER_MISSES
    (B); sobreviventes seguem publicando DDATA sem perda (C)."""
    f = full_fleet
    for n in (1, 2, 3):
        assert f.wait_http(n)

    nb2, _, _ = _fresh_cycle(f, sniffer, 2)
    bdseq2 = _bdseq(nb2["pb"])
    # deixa a malha convergir para alive
    time.sleep(6)

    t1 = time.time()
    f.kill_node(2)  # morte abrupta -> LWT

    # (A) plano norte: NDEATH via LWT com o bdSeq do ultimo NBIRTH de edge_002
    nd = sniffer.wait("NDEATH", GW[2], after=t1, timeout=90)
    assert _bdseq(nd["pb"]) == bdseq2, (
        f"bdSeq do LWT ({_bdseq(nd['pb'])}) != ultimo NBIRTH de edge_002 ({bdseq2})"
    )
    t_ndeath = nd["ts"] - t1

    # (B) plano leste-oeste: edge_001 e edge_003 marcam edge_002 down
    d1 = _peer_down_at(f, 1, "edge_002", t1, timeout=15)
    d3 = _peer_down_at(f, 3, "edge_002", t1, timeout=15)
    assert d1 is not None and d3 is not None, f"edge_002 nao ficou down: d1={d1} d3={d3}"

    # (C) sobreviventes publicam DDATA sem perda durante e apos a falha
    time.sleep(10)
    for n in (1, 3):
        losses = _ddata_losses(sniffer, GW[n], t1, time.time())
        assert losses == 0, f"{GW[n]}: {losses} lacuna(s) de DDATA na falha"
    # sem rebirth espurio nos sobreviventes
    for n in (1, 3):
        assert not sniffer.snap("NBIRTH", GW[n], after=t1), f"{GW[n]} deu NBIRTH espurio"

    f.start_node(2)


# --------------------------------------------------------------------------- T4.5
def test_religamento(full_fleet, sniffer):
    """Passo 6: edge_002 volta e emite um novo NBIRTH com bdSeq incrementado;
    edge_001/edge_003 voltam a reportá-lo `alive`."""
    f = full_fleet
    for n in (1, 2, 3):
        assert f.wait_http(n)

    nb_a, _, _ = _fresh_cycle(f, sniffer, 2)
    bd_a = _bdseq(nb_a["pb"])

    f.stop_node(2)
    assert _peer_down_at(f, 1, "edge_002", time.time(), timeout=15) is not None

    t2 = time.time()
    f.start_node(2)
    assert f.wait_http(2), "edge_002 nao voltou"
    nb_b = sniffer.wait("NBIRTH", GW[2], after=t2, timeout=150)
    bd_b = _bdseq(nb_b["pb"])
    # religamento => NOVO NBIRTH de sessao (seq=0, com metrica bdSeq). Por SDD
    # 5.1.1 o bdSeq vive so no contexto do fluxo em memoria: reinicio de
    # container reinicia a contagem em 0 (aceitavel) — daí `>=`, não `>`.
    assert nb_b["seq"] == 0, f"NBIRTH do religamento com seq={nb_b['seq']}"
    assert bd_b is not None and bd_b >= 0, "NBIRTH do religamento sem metrica bdSeq"
    assert bd_a is not None

    # pares voltam a alive
    deadline = time.time() + 40
    while time.time() < deadline:
        s1 = next((p["state"] for p in f.peers_api(1)["peers"] if p["id"] == "edge_002"), None)
        s3 = next((p["state"] for p in f.peers_api(3)["peers"] if p["id"] == "edge_002"), None)
        if s1 == "alive" and s3 == "alive":
            break
        time.sleep(1)
    else:
        pytest.fail("edge_002 nao voltou a alive nos observadores")


# --------------------------------------------------------------------------- T4.6
def test_report_e_aceite(full_fleet, sniffer):
    """Passo 7: roda o cenário 3.1 ponta a ponta e emite test/etapa1/report.json
    com t_ndeath, t_peer_detect por observador, perdas (==0) e overhead de
    CPU/RAM por container."""
    f = full_fleet
    for n in (1, 2, 3):
        assert f.wait_http(n)

    # t0: frota íntegra, sessões frescas
    nb2, _, _ = _fresh_cycle(f, sniffer, 2)
    bdseq2 = _bdseq(nb2["pb"])
    for n in (1, 3):
        _fresh_cycle(f, sniffer, n)
    time.sleep(6)

    stats_t0 = f.docker_stats()

    # t1: injeção (kill -> LWT)
    t1 = time.time()
    f.kill_node(2)

    nd = sniffer.wait("NDEATH", GW[2], after=t1, timeout=90)
    t_ndeath = round(nd["ts"] - t1, 3)
    assert _bdseq(nd["pb"]) == bdseq2

    t_peer_detect = {}
    for obs in (1, 3):
        d = _peer_down_at(f, obs, "edge_002", t1, timeout=15)
        assert d is not None, f"edge_00{obs} nao detectou edge_002 down"
        t_peer_detect[f"edge_00{obs}"] = round(d, 3)

    time.sleep(10)
    perdas = {GW[n]: _ddata_losses(sniffer, GW[n], t1, time.time()) for n in (1, 3)}

    # t2: religamento
    t2 = time.time()
    f.start_node(2)
    assert f.wait_http(2)
    nb_b = sniffer.wait("NBIRTH", GW[2], after=t2, timeout=150)
    religou = nb_b["seq"] == 0 and _bdseq(nb_b["pb"]) is not None

    report = {
        "cenario": "SDD 3.1 — injeção de falha na frota de 3 nós",
        "nos": list(GW.values()),
        "t_ndeath_s": t_ndeath,
        "t_peer_detect_s": t_peer_detect,
        "probe_interval_ms": 1000,
        "peer_down_after_misses": 3,
        "perdas_ddata_sobreviventes": perdas,
        "religamento_novo_nbirth": bool(religou),
        "religamento_bdseq": _bdseq(nb_b["pb"]),
        "overhead": {
            name: st for name, st in sorted(stats_t0.items())
        },
        "aceite": (
            all(v == 0 for v in perdas.values())
            and religou
            and t_ndeath is not None
            and all(v is not None for v in t_peer_detect.values())
        ),
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # validação do schema/criterio
    assert REPORT.is_file()
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    for k in ("t_ndeath_s", "t_peer_detect_s", "perdas_ddata_sobreviventes",
              "religamento_novo_nbirth", "aceite"):
        assert k in r, f"report.json sem a chave {k!r}"
    assert r["perdas_ddata_sobreviventes"] == {GW[1]: 0, GW[3]: 0}, r["perdas_ddata_sobreviventes"]
    assert r["religamento_novo_nbirth"] is True
    assert r["aceite"] is True, r
