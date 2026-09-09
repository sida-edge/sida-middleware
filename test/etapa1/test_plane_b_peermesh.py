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

import time

import pytest

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
