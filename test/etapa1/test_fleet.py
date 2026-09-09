"""Checkpoints funcionais da Sprint S4 — frota de 3 nós (T3.2, T3.3).

- test_frota_3_nos          -> T3.2 (deploy/fleet/*.env + 3 nós sem colisão, pares cruzados)
- test_compose_test_isolado -> T3.3 (compose.test.yml final: frota + Mosquitto isolado)
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from conftest import COMPOSE_TEST, FLEET_DIR

pytestmark = pytest.mark.heavy


def _parse_env(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


# --------------------------------------------------------------------------- T3.2
def test_frota_3_nos(plane_b_fleet):
    """deploy/fleet/edge_00X.env: 3 identidades distintas com PEERS cruzados; e
    os 3 sida-core sobem sem colisão de porta/rede e cada um lista os outros
    dois em GET /api/system/peers."""
    # --- estatico: coerencia dos .env da frota ---
    envs = {n: _parse_env(FLEET_DIR / f"edge_{n}.env") for n in ("001", "002", "003")}
    gids = {e["EDGE_GATEWAY_ID"] for e in envs.values()}
    cids = {e["CONTROLLER_ID"] for e in envs.values()}
    assert len(gids) == 3, f"EDGE_GATEWAY_ID nao sao todos distintos: {gids}"
    assert len(cids) == 3, f"CONTROLLER_ID nao sao todos distintos: {cids}"
    assert {e["GROUP_ID"] for e in envs.values()} == {"Enterprise_Site"}
    for n, e in envs.items():
        peers = {p.split("@")[0] for p in e["PEERS"].split(",") if p.strip()}
        assert peers == cids - {e["CONTROLLER_ID"]}, (
            f"edge_{n}: PEERS {peers} != outros nos {cids - {e['CONTROLLER_ID']}}"
        )

    # --- dinamico: os 3 cores sobem e se enxergam ---
    f = plane_b_fleet
    f.up(1, 2, 3)
    for n in (1, 2, 3):
        assert f.wait_http(n), f"edge{n}-core nao subiu"

    # cada nó lista os outros dois E, dentro de alguns ciclos de probe,
    # os enxerga `alive` (frota íntegra, sem colisão de porta/rede/identidade).
    deadline = time.time() + 40
    while time.time() < deadline:
        ok = True
        for n in (1, 2, 3):
            pj = f.peers_api(n)
            if pj["controller_id"] != f.CONTROLLER_ID[n]:
                ok = False
            want = {f.CONTROLLER_ID[k] for k in (1, 2, 3) if k != n}
            got_alive = {p["id"] for p in pj["peers"] if p["state"] == "alive"}
            if got_alive != want:
                ok = False
        if ok:
            break
        time.sleep(1)
    else:
        pytest.fail(f"frota nao convergiu para alive: "
                    f"{[f.peers_api(n) for n in (1, 2, 3)]}")
