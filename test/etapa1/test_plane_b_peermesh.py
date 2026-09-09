"""Checkpoints funcionais da Sprint S3 — Plano B (malha controller-to-controller
InterEdge, em Go no sida-core).

SDD_SIDA_Etapa1_Ciclo_V3.md, secao 5.2 e 5.4 (casos 4, 6, 7, 9) e tabela 3.3.2:

- test_registro_carrega_de_env  -> T1B.1 (ControllerRegister + PeerRepository + parsing PEERS)
- test_persistencia_controllers -> T1B.2 (tabela controllers no sida_config.db, WAL)
- test_troca_mensagem_mesh      -> T1B.3 (ROUTER/DEALER + WriteMessage/RouteMessage/ReadMessage)
- test_probe_e_liveness         -> T1B.4 (probe loop + FSM alive/suspect/down + GET /api/system/peers)
- test_wiring_e_shutdown        -> T1B.5 (wiring no main.go; :5556 intacto; shutdown limpo)

Todos [heavy]: sobem 1..3 sida-core da compose.test.yml na mesh_net dedicada.
"""
from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager

import pytest

from conftest import COMPOSE_TEST

pytestmark = pytest.mark.heavy


# --------------------------------------------------------------------------- T1B.1
def test_registro_carrega_de_env(plane_b_fleet):
    """O sida-core carrega o Controller Register das envs de identidade:
    com PEERS=2 loga 'peer register: 2 pares'; com PEERS vazio, '0 pares'.
    A unidade do parser (go test ./internal/core/domain/...) fica verde."""
    # --- unidade Go do dominio (ParsePeers / NewControllerRegisterFromEnv) ---
    got = plane_b_fleet.go_test("./internal/core/domain/...")
    assert got.returncode == 0, f"go test do dominio falhou:\n{got.stdout}\n{got.stderr}"

    # --- 2 pares: edge1-core (PEERS = edge_002@... , edge_003@...) ---
    plane_b_fleet.up(1)
    assert plane_b_fleet.wait_http(1), "edge1-core nao respondeu em /api/system/info"
    logs1 = plane_b_fleet.logs(1)
    assert "peer register: 2 pares" in logs1, (
        f"log de registro de pares ausente/errado em edge1-core:\n{logs1[-2000:]}"
    )

    # --- 0 pares: mesmo binario, PEERS vazio ---
    logs0 = plane_b_fleet.run_oneoff_core(
        "e1-b-solo",
        {"PEERS": "", "CONTROLLER_ID": "edge_solo", "EDGE_GATEWAY_ID": "sida_edge_solo"},
    )
    assert "peer register: 0 pares" in logs0, (
        f"esperava 'peer register: 0 pares' com PEERS vazio:\n{logs0[-2000:]}"
    )


# --------------------------------------------------------------------------- T1B.2
def test_persistencia_controllers(plane_b_fleet):
    """A tabela `controllers` existe no sida_config.db (WAL) e guarda o
    Controller Register deste no; `docker restart` preserva o registro."""
    import json as _json

    f = plane_b_fleet
    f.up(1)
    assert f.wait_http(1), "edge1-core nao subiu"
    time.sleep(1)

    tables = {r[0] for r in f.db_query(1, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "controllers" in tables, f"tabela `controllers` ausente: {sorted(tables)}"

    jmode = f.db_query(1, "PRAGMA journal_mode")[0][0]
    assert str(jmode).lower() == "wal", f"journal_mode={jmode!r} (esperado wal)"

    row = f.db_query(
        1, "SELECT connected_controllers, probe_interval_ms FROM controllers WHERE controller_id=?",
        ("edge_001",),
    )
    assert row, "registro de edge_001 nao persistido"
    assert len(_json.loads(row[0][0])) == 2, f"esperava 2 pares persistidos: {row[0][0]}"

    # docker restart preserva o registro
    f.restart(1)
    assert f.wait_http(1), "edge1-core nao voltou apos restart"
    time.sleep(1)
    row2 = f.db_query(
        1, "SELECT connected_controllers FROM controllers WHERE controller_id=?", ("edge_001",),
    )
    assert row2 and len(_json.loads(row2[0][0])) == 2, "registro de pares perdido apos restart"


# --------------------------------------------------------------------------- T1B.3
def test_troca_mensagem_mesh(plane_b_fleet):
    """edge_001.WriteMessage(edge_002, payload) e edge_002 recebe o payload
    integro via ReadMessage(); a troca usa :5557 e o :5556 segue intacto."""
    f = plane_b_fleet
    f.up(1, 2)
    assert f.wait_http(1) and f.wait_http(2), "cores nao subiram"

    # :5557 e :5556 coexistem
    l1 = f.logs(1)
    assert "peer-mesh: ROUTER em tcp://0.0.0.0:5557" in l1, f"peer-mesh nao logou o bind :5557\n{l1[-1500:]}"
    assert "tcp://0.0.0.0:5556" in l1, "ZMQ Publisher de manifesto (:5556) sumiu"

    nonce = f"ola-mesh-{int(time.time())}"
    # da tempo para os DEALER conectarem
    deadline = time.time() + 40
    delivered = False
    while time.time() < deadline:
        r = f.api_post(1, "/api/system/peers/test/send", {"peer": "edge_002", "payload": nonce})
        assert r.status_code in (202, 502), f"send inesperado: {r.status_code} {r.text}"
        time.sleep(2)
        inbox = f.api_get(2, "/api/system/peers/test/inbox").get("messages", [])
        if nonce in inbox:
            delivered = True
            break
    assert delivered, f"edge_002 nao recebeu {nonce!r} via a malha"

    # e a volta: edge_002 -> edge_001
    nonce2 = f"volta-{int(time.time())}"
    got_back = False
    deadline = time.time() + 30
    while time.time() < deadline:
        f.api_post(2, "/api/system/peers/test/send", {"peer": "edge_001", "payload": nonce2})
        time.sleep(2)
        if nonce2 in f.api_get(1, "/api/system/peers/test/inbox").get("messages", []):
            got_back = True
            break
    assert got_back, f"edge_001 nao recebeu {nonce2!r} de volta"


# --------------------------------------------------------------------------- T1B.4
def _peer_state(fleet, node, peer_id):
    for p in fleet.peers_api(node)["peers"]:
        if p["id"] == peer_id:
            return p
    return None


def test_probe_e_liveness(plane_b_fleet):
    """Frota de 3 nos (probe 1000ms / down apos 3): t0 todos alive; ao derrubar
    edge_002, edge_001 e edge_003 o reportam `down` (via suspect) em ~3s, com
    missed/last_ack_ms coerentes; a queda e LOCAL (edge_001<->edge_003 seguem)."""
    f = plane_b_fleet
    f.up(1, 2, 3)
    for n in (1, 2, 3):
        assert f.wait_http(n), f"edge{n}-core nao subiu"

    # convergencia inicial para alive
    deadline = time.time() + 30
    while time.time() < deadline:
        if (_peer_state(f, 1, "edge_002")["state"] == "alive"
                and _peer_state(f, 1, "edge_003")["state"] == "alive"
                and _peer_state(f, 3, "edge_002")["state"] == "alive"):
            break
        time.sleep(1)
    else:
        pytest.fail(f"pares nao convergiram para alive: e1={f.peers_api(1)}")

    # derruba edge_002
    f.stop(2)
    t_ref = time.time()

    down_at = {}
    deadline = time.time() + 12
    while time.time() < deadline and len(down_at) < 2:
        for node in (1, 3):
            if node not in down_at and _peer_state(f, node, "edge_002")["state"] == "down":
                down_at[node] = time.time() - t_ref
        time.sleep(0.5)

    assert 1 in down_at and 3 in down_at, (
        f"edge_002 nao ficou down em edge_001/edge_003: e1={f.peers_api(1)} e3={f.peers_api(3)}"
    )
    assert max(down_at.values()) <= 6.0, f"deteccao lenta demais: {down_at}"

    p2 = _peer_state(f, 1, "edge_002")
    assert p2["missed"] >= 3, f"missed incoerente: {p2}"
    assert p2["last_ack_ms"] >= 2500, f"last_ack_ms incoerente: {p2}"

    # a queda e local: edge_001 <-> edge_003 seguem alive entre si
    assert _peer_state(f, 1, "edge_003")["state"] == "alive"
    assert _peer_state(f, 3, "edge_001")["state"] == "alive"

    f.start(2)  # restaura para o resto da suite


# --------------------------------------------------------------------------- T1B.5
def test_wiring_e_shutdown(plane_b_fleet):
    """O peer_service sobe no boot (log :5557) sem tocar no PUB de manifesto
    (:5556, que segue entregando a um assinante) nem nas rotas; /api/system/info
    segue 200; `docker stop` encerra a malha limpo e rapido."""
    import hashlib

    import requests
    import zmq

    f = plane_b_fleet
    f.up(1)
    assert f.wait_http(1), "edge1-core nao subiu"

    l1 = f.logs(1)
    assert "peer-mesh: ROUTER em tcp://0.0.0.0:5557" in l1, l1[-1500:]
    assert "ZMQ Publisher rodando em tcp://0.0.0.0:5556" in l1, "PUB de manifesto (:5556) sumiu"

    pj = f.peers_api(1)
    assert pj["controller_id"] == "edge_001" and len(pj["peers"]) == 2, pj
    assert f.api_get(1, "/api/system/info"), "/api/system/info nao respondeu 200"

    # :5556 (papel do ontology-builder) ainda entrega manifesto a um assinante
    sub = zmq.Context.instance().socket(zmq.SUB)
    sub.setsockopt(zmq.SUBSCRIBE, b"sida/manifest")
    sub.setsockopt(zmq.RCVTIMEO, 1500)
    sub.connect(f"tcp://localhost:{f.PUB_PORT_HOST[1]}")
    time.sleep(1.0)  # slow joiner do ZeroMQ

    bearer = "Bearer session_" + hashlib.sha256(b"000000").hexdigest()
    manifest = {"gateway_id": "sida_edge_001", "config": {"plant": {"enterprise": "E", "site": "S"}}}
    got_pub = False
    try:
        for _ in range(8):
            r = requests.post(f._url(1, "/api/config/manifest"), json=manifest,
                              headers={"Authorization": bearer}, timeout=5)
            assert r.status_code == 200, f"upload manifest: {r.status_code} {r.text}"
            try:
                topic, _body = sub.recv_multipart()
                if topic.startswith(b"sida/manifest"):
                    got_pub = True
                    break
            except zmq.Again:
                time.sleep(0.5)
    finally:
        sub.close()
    assert got_pub, ":5556 nao entregou o manifesto ao assinante apos o wiring do plano B"

    # shutdown limpo e rapido (sem chegar ao SIGKILL do -t 10)
    t0 = time.time()
    f.stop(1)
    dt = time.time() - t0
    lg = f.logs(1)
    assert "peer-mesh encerrada" in lg, f"peer-mesh nao encerrou no shutdown\n{lg[-1500:]}"
    assert "SIDA-Core encerrado" in lg, f"shutdown nao chegou ao fim\n{lg[-1500:]}"
    assert dt <= 10.0, f"shutdown lento demais ({dt:.1f}s) — possivel goroutine presa"


# ---------------------------------------------------------------- T4.2: casos 6, 7, 9
def _wait_states(fleet, want: dict, timeout: float):
    """want = {(node, peer_id): estado_esperado}. Espera todos baterem."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = {}
        ok = True
        for (node, pid), exp in want.items():
            st = _peer_state(fleet, node, pid)
            last[(node, pid)] = st["state"] if st else None
            if last[(node, pid)] != exp:
                ok = False
        if ok:
            return
        time.sleep(1)
    raise AssertionError(f"liveness nao convergiu: quer={want} tem={last}")


def test_flap_religamento(plane_b_fleet):
    """Caso 6: edge_002 cai e volta em poucos segundos. edge_001/edge_003 o
    marcam `down` (via suspect) e, ao voltar, `alive` de novo — a histerese
    evita oscilacao e a malha entre os sobreviventes nao se corrompe."""
    f = plane_b_fleet
    f.up(1, 2, 3)
    for n in (1, 2, 3):
        assert f.wait_http(n), f"edge{n}-core nao subiu"
    _wait_states(f, {(1, "edge_002"): "alive", (1, "edge_003"): "alive",
                     (3, "edge_002"): "alive", (3, "edge_001"): "alive"}, 40)

    f.stop(2)
    _wait_states(f, {(1, "edge_002"): "down", (3, "edge_002"): "down"}, 15)
    assert _peer_state(f, 1, "edge_003")["state"] == "alive", "flap contaminou edge_001<->edge_003"
    assert _peer_state(f, 3, "edge_001")["state"] == "alive"

    f.start(2)
    assert f.wait_http(2), "edge2-core nao voltou"
    _wait_states(f, {(1, "edge_002"): "alive", (3, "edge_002"): "alive",
                     (2, "edge_001"): "alive", (2, "edge_003"): "alive",
                     (1, "edge_003"): "alive", (3, "edge_001"): "alive"}, 40)


def _container(node: int) -> str:
    # compose.test.yml fixa container_name = e1-edge{N}-core
    return f"e1-edge{node}-core"


def _mesh_ip(fleet, node: int) -> str:
    net = f"{fleet._project[1]}_mesh_net"
    p = subprocess.run(
        ["docker", "inspect", "-f",
         '{{(index .NetworkSettings.Networks "' + net + '").IPAddress}}', _container(node)],
        capture_output=True, text=True, timeout=20,
    )
    ip = p.stdout.strip()
    assert ip, f"sem IP de {_container(node)} em {net}: {p.stderr}"
    return ip


@contextmanager
def _partition(fleet, a: int, b: int):
    """Bloqueia (iptables no netns de cada container) o trafego a<->b, mantendo
    o resto da malha. Remove no fim; a teardown da fixture (`down -v`) tambem
    limpa se algo escapar."""
    ip_a, ip_b = _mesh_ip(fleet, a), _mesh_ip(fleet, b)

    def _rule(op: str, node: int, other_ip: str):
        subprocess.run(
            ["docker", "run", "--rm", "--network", f"container:{_container(node)}",
             "--cap-add", "NET_ADMIN", "alpine", "sh", "-c",
             f"apk add -q iptables 2>/dev/null; "
             f"iptables -{op} INPUT -s {other_ip} -j DROP; "
             f"iptables -{op} OUTPUT -d {other_ip} -j DROP"],
            capture_output=True, text=True, timeout=90,
        )

    _rule("A", a, ip_b)
    _rule("A", b, ip_a)
    try:
        yield
    finally:
        _rule("D", a, ip_b)
        _rule("D", b, ip_a)


def test_particao_parcial(plane_b_fleet):
    """Caso 7: regra de rede permite edge_001<->edge_002 e edge_002<->edge_003,
    mas bloqueia edge_001<->edge_003. Cada no reporta sua visao LOCAL: edge_001
    ve edge_003 down e edge_002 alive; edge_003 o simetrico; edge_002 ve os
    dois alive. Sem eleicao/quorum — o plano B nao reconcilia."""
    f = plane_b_fleet
    f.up(1, 2, 3)
    for n in (1, 2, 3):
        assert f.wait_http(n), f"edge{n}-core nao subiu"
    _wait_states(f, {(1, "edge_002"): "alive", (1, "edge_003"): "alive",
                     (2, "edge_001"): "alive", (2, "edge_003"): "alive",
                     (3, "edge_001"): "alive", (3, "edge_002"): "alive"}, 40)

    with _partition(f, 1, 3):
        _wait_states(f, {(1, "edge_003"): "down", (3, "edge_001"): "down"}, 20)
        # visao local, sem consenso:
        assert _peer_state(f, 1, "edge_002")["state"] == "alive", "edge_001 perdeu edge_002 (nao devia)"
        assert _peer_state(f, 3, "edge_002")["state"] == "alive", "edge_003 perdeu edge_002 (nao devia)"
        assert _peer_state(f, 2, "edge_001")["state"] == "alive", "edge_002 nao devia perder edge_001"
        assert _peer_state(f, 2, "edge_003")["state"] == "alive", "edge_002 nao devia perder edge_003"

    # ao remover a particao, edge_001<->edge_003 voltam a alive
    _wait_states(f, {(1, "edge_003"): "alive", (3, "edge_001"): "alive"}, 40)


def test_colisao_identidade(plane_b_fleet, tmp_path):
    """Caso 9: dois nos com o MESMO CONTROLLER_ID. O peer_service detecta a
    colisao no trafego da malha (assinado com o proprio id) e recusa o par
    com log claro — condicao visivel, nao um flap silencioso."""
    f = plane_b_fleet
    dup = tmp_path / "compose.dup.yml"
    dup.write_text(
        "services:\n  edge2-core:\n    environment:\n      CONTROLLER_ID: edge_001\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [*f._compose, "-f", str(COMPOSE_TEST), "-f", str(dup), *f._project,
         "up", "-d", "--build", "edge1-core", "edge2-core"],
        capture_output=True, text=True, timeout=600, cwd=COMPOSE_TEST.parent,
    )
    assert r.returncode == 0, f"up com CONTROLLER_ID colidido falhou:\n{r.stderr}"
    assert f.wait_http(1) and f.wait_http(2), "cores nao subiram"

    time.sleep(10)  # deixa alguns ciclos de probe cruzarem
    l1, l2 = f.logs(1), f.logs(2)
    assert ("CONTROLLER_ID duplicado" in l1) or ("CONTROLLER_ID duplicado" in l2), (
        f"colisao de CONTROLLER_ID nao registrada em log:\n--edge1--\n{l1[-1500:]}\n--edge2--\n{l2[-1500:]}"
    )
