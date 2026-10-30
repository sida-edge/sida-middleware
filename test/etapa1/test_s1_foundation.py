"""Checkpoints funcionais da Sprint S1 (SDD_SIDA_Etapa1_Ciclo_V3.md, tabela 3.3.2).

- test_baseline_v2_pipeline   -> T0.4  (harness de frota local + smoke da baseline v2.0)
- test_sparkplug_proto_valido -> T1A.1 (schemas/sparkplug_b.proto como fonte da verdade)
- test_compose_parametrizado  -> T3.1  (docker-compose.yml parametrizado por .env)

Cada teste corresponde ao checkpoint que libera o commit `[T...]` da task.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from conftest import COMPOSE_TEST, FLEET_DIR, REPO_ROOT

PROTO = REPO_ROOT / "schemas" / "sparkplug_b.proto"
COMPOSE_MAIN = REPO_ROOT / "docker-compose.yml"
EDGE1_ENV = FLEET_DIR / "edge_001.env"

# Identidades que NAO podem aparecer fixas no codigo de runtime (Fronteira 11).
HARDCODE_FORBIDDEN = re.compile(r"sida_edge_00[0-9]|EDGE_GATEWAY_ID\s*[:=]\s*[\"']?sida_edge")
HARDCODE_SCAN_DIRS = ["sida-core", "core"]
HARDCODE_SCAN_EXCLUDE = ("/.env", "/data/", "/deploy/", "/test/", "node_modules")


# --------------------------------------------------------------------------- T1A.1
def test_sparkplug_proto_valido(require_protoc, tmp_path):
    """O .proto existe, compila com um compilador protobuf e declara as
    mensagens centrais do Sparkplug B (Payload / Metric / Template)."""
    assert PROTO.is_file(), f"faltando {PROTO.relative_to(REPO_ROOT)}"

    out = tmp_path / "sparkplug_b.desc"
    proc = subprocess.run(
        [*require_protoc,
         f"--proto_path={PROTO.parent}",
         f"--descriptor_set_out={out}",
         PROTO.name],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"protoc falhou:\n{proc.stderr}"
    assert out.is_file() and out.stat().st_size > 0, "descriptor set vazio"

    text = PROTO.read_text(encoding="utf-8")
    for msg in ("message Payload", "message Metric", "message Template"):
        assert msg in text, f"'{msg}' ausente no .proto"
    # alias inteiro por metrica (base do delta S2)
    assert re.search(r"\balias\b\s*=\s*2", text), "campo 'alias' do Metric ausente"

    readme = (PROTO.parent / "README.md").read_text(encoding="utf-8")
    assert "sparkplug_b.proto" in readme, "schemas/README.md nao referencia o .proto"


# ---------------------------------------------------------------------------- T3.1
def _compose_config(compose, env_file: Path) -> dict:
    proc = subprocess.run(
        [*compose, "-f", str(COMPOSE_MAIN), "--env-file", str(env_file), "config"],
        capture_output=True, text=True, timeout=90, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"`compose config` falhou:\n{proc.stderr}"
    assert "variable is not set" not in proc.stderr.lower(), proc.stderr
    return yaml.safe_load(proc.stdout)


def _env_as_map(service: dict) -> dict:
    env = service.get("environment", {})
    if isinstance(env, list):
        out = {}
        for item in env:
            k, _, v = str(item).partition("=")
            out[k] = v
        return out
    return dict(env)


def test_compose_parametrizado(require_compose):
    """`docker compose --env-file edge_001.env config` resolve sem variavel
    solta; a identidade do no vem do .env; a porta do peer-mesh e publicada;
    nao ha identidade de no fixa no codigo de runtime."""
    assert EDGE1_ENV.is_file(), f"faltando {EDGE1_ENV.relative_to(REPO_ROOT)}"
    cfg = _compose_config(require_compose, EDGE1_ENV)

    core = cfg["services"]["sida-core"]
    core_env = _env_as_map(core)
    assert core_env.get("EDGE_GATEWAY_ID") == "sida_edge_001", core_env
    assert core_env.get("CONTROLLER_ID") == "edge_001", core_env
    for key in ("GROUP_ID", "BROKER_URL", "PEERS", "PROBE_INTERVAL_MS", "PEER_DOWN_AFTER_MISSES"):
        assert key in core_env, f"{key} nao propagado ao sida-core"

    published = {str(p.get("published")) for p in core.get("ports", []) if isinstance(p, dict)}
    targets = {str(p.get("target")) for p in core.get("ports", []) if isinstance(p, dict)}
    assert "5557" in targets or "5557" in published, f"porta do peer-mesh nao publicada: {core.get('ports')}"

    delivery_env = _env_as_map(cfg["services"]["poc-delivery"])
    assert delivery_env.get("EDGE_GATEWAY_ID") == "sida_edge_001", delivery_env

    # nenhuma identidade de no fixa em codigo de runtime
    offenders = []
    for d in HARDCODE_SCAN_DIRS:
        for path in (REPO_ROOT / d).rglob("*"):
            if not path.is_file():
                continue
            sp = str(path).replace("\\", "/")
            if any(x in sp for x in HARDCODE_SCAN_EXCLUDE):
                continue
            if path.suffix not in {".go", ".js", ".json", ".ts", ".py", ".yml", ".yaml"}:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if HARDCODE_FORBIDDEN.search(content):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"identidade de no hardcoded em: {offenders}"


@pytest.mark.heavy
def test_compose_parametrizado_sobe_um_no(require_compose):
    """Passo pesado do T3.1: a compose principal sobe UM no (sida-core) sem
    erro de arquitetura e responde em /api/system/info."""
    import requests

    env = {"COMPOSE_PROJECT_NAME": "sida_t31"}
    up = subprocess.run(
        [*require_compose, "--env-file", str(EDGE1_ENV), "up", "-d", "--build", "sida-core"],
        capture_output=True, text=True, timeout=900, cwd=REPO_ROOT,
        env={**__import__("os").environ, **env},
    )
    try:
        assert up.returncode == 0, f"up falhou:\n{up.stderr}"
        deadline = time.time() + 60
        ok = False
        while time.time() < deadline:
            try:
                r = requests.get("http://localhost:8000/api/system/info", timeout=3)
                if r.status_code == 200:
                    ok = True
                    break
            except requests.RequestException:
                time.sleep(2)
        assert ok, "sida-core nao respondeu 200 em /api/system/info"
    finally:
        subprocess.run(
            [*require_compose, "--env-file", str(EDGE1_ENV), "down", "-v"],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
            env={**__import__("os").environ, **env},
        )


# ---------------------------------------------------------------------------- T0.4
@pytest.mark.heavy
def test_baseline_v2_pipeline(require_compose, require_paho):
    """Harness de frota local: sobe UM no completo (core+ingestion+context+
    delivery) da compose.test.yml contra o Mosquitto isolado + simulador, e
    confirma que o pipeline v2.0 (Modbus -> ISA-95 -> Sparkplug B) chega ao
    broker como DDATA em spBv1.0/#. Baseline preservada (Fronteira 1)."""
    mqtt = require_paho
    services = ["mosquitto", "plc-sim", "edge1-core", "edge1-ingestion", "edge1-context", "edge1-delivery"]
    project = ["-p", "sida_e1_baseline"]

    seed = subprocess.run(
        ["python3", str(COMPOSE_TEST.parent / "seed_node_config.py"),
         "--data-dir", str(COMPOSE_TEST.parent / "_data" / "edge1"),
         "--gateway-id", "sida_edge_001",
         "--broker-host", "mosquitto", "--modbus-host", "plc-sim"],
        capture_output=True, text=True, timeout=30,
    )
    assert seed.returncode == 0, f"seed do sida_config.db falhou:\n{seed.stderr}"

    up = subprocess.run(
        [*require_compose, "-f", str(COMPOSE_TEST), *project, "up", "-d", "--build", *services],
        capture_output=True, text=True, timeout=1200, cwd=COMPOSE_TEST.parent,
    )
    received: list[str] = []
    try:
        assert up.returncode == 0, f"up da frota de teste falhou:\n{up.stderr}"

        cli = mqtt.Client()
        cli.on_message = lambda c, u, m: received.append(m.topic)
        # porta do host mapeada em compose.test.yml (mosquitto: 18831->1883)
        for attempt in range(30):
            try:
                cli.connect("localhost", 18831, keepalive=30)
                break
            except OSError:
                time.sleep(2)
        else:
            pytest.fail("nao conectou ao Mosquitto de teste em localhost:18831")

        cli.subscribe("spBv1.0/#", qos=0)
        cli.loop_start()
        deadline = time.time() + 180  # baseline: builds + boot + 1º ciclo
        got_ddata = False
        while time.time() < deadline:
            if any("/DDATA/" in t for t in received):
                got_ddata = True
                break
            time.sleep(2)
        cli.loop_stop()
        cli.disconnect()

        births = [t for t in received if "/NBIRTH/" in t or "/DBIRTH/" in t]
        assert births, f"nenhum BIRTH em spBv1.0/# — pipeline nao subiu. topicos: {sorted(set(received))}"
        assert got_ddata, f"nenhum DDATA em spBv1.0/# ate o timeout. topicos: {sorted(set(received))}"
    finally:
        subprocess.run(
            [*require_compose, "-f", str(COMPOSE_TEST), *project, "down", "-v"],
            capture_output=True, text=True, timeout=180, cwd=COMPOSE_TEST.parent,
        )
