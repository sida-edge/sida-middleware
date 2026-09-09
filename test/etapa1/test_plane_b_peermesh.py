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
