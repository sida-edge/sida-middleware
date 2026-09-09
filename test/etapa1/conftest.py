"""Fixtures e deteccao de ferramentas para a suite da Etapa 1 do Ciclo V3.0.

Os testes marcados como "funcionais" (checkpoint por task, SDD secao 3.3.1)
precisam de: docker + docker compose, um compilador protobuf (protoc ou
grpc_tools.protoc) e paho-mqtt. Quando a ferramenta nao esta disponivel o
teste e PULADO com uma mensagem acionavel — nunca falha por ambiente.
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ETAPA1_DIR = Path(__file__).resolve().parent
COMPOSE_TEST = ETAPA1_DIR / "compose.test.yml"
FLEET_DIR = REPO_ROOT / "deploy" / "fleet"
SEED_SCRIPT = ETAPA1_DIR / "seed_node_config.py"
PROTO = REPO_ROOT / "schemas" / "sparkplug_b.proto"


def pytest_addoption(parser):
    parser.addoption(
        "--run-heavy",
        action="store_true",
        default=False,
        help="Executa os passos que sobem containers (build + up). Lento.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "heavy: sobe containers (build/up); exige --run-heavy")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-heavy"):
        return
    skip = pytest.mark.skip(reason="passo pesado; rode com --run-heavy")
    for item in items:
        if "heavy" in item.keywords:
            item.add_marker(skip)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def compose_cmd() -> list[str] | None:
    """Retorna o comando 'docker compose' (v2) ou 'docker-compose' (v1), ou None."""
    if which("docker"):
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                check=True, capture_output=True, timeout=15,
            )
            return ["docker", "compose"]
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            pass
    if which("docker-compose"):
        return ["docker-compose"]
    return None


def protoc_cmd() -> list[str] | None:
    if which("protoc"):
        return ["protoc"]
    try:
        import grpc_tools.protoc  # noqa: F401
        return ["python3", "-m", "grpc_tools.protoc"]
    except Exception:
        return None


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def require_compose() -> list[str]:
    cmd = compose_cmd()
    if cmd is None:
        pytest.skip("instale docker + docker compose v2 (pacote docker.io / docker-compose-plugin)")
    return cmd


@pytest.fixture(scope="session")
def require_protoc() -> list[str]:
    cmd = protoc_cmd()
    if cmd is None:
        pytest.skip("instale protobuf-compiler (protoc) OU 'pip install grpcio-tools'")
    return cmd


@pytest.fixture(scope="session")
def require_paho():
    try:
        import paho.mqtt.client as mqtt  # noqa: F401
    except Exception:
        pytest.skip("instale paho-mqtt ('pip install paho-mqtt' ou pacote python3-paho-mqtt)")
    import paho.mqtt.client as mqtt
    return mqtt


# --------------------------------------------------------------------------- plano A
@pytest.fixture(scope="session")
def spb_pb2(require_protoc, tmp_path_factory):
    """Compila schemas/sparkplug_b.proto para um modulo Python e o importa.

    Serve para os testes do plano A decodificarem os payloads Sparkplug B que
    o delivery publica no broker de teste. Precisa do runtime `protobuf` (skip
    acionavel se ausente)."""
    try:
        import google.protobuf  # noqa: F401
    except Exception:
        pytest.skip("instale o runtime protobuf ('pip install protobuf')")
    out = tmp_path_factory.mktemp("spb_pb2")
    proc = subprocess.run(
        [*require_protoc, f"--proto_path={PROTO.parent}", f"--python_out={out}", PROTO.name],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"protoc --python_out falhou:\n{proc.stderr}"
    sys.path.insert(0, str(out))
    mod = importlib.import_module("sparkplug_b_pb2")
    return mod


class PlaneANode:
    """Controla UM no completo (core+ingestion+context+delivery) + Mosquitto
    isolado + simulador Modbus, da compose.test.yml, para os testes do plano A."""

    MQTT_HOST = "localhost"
    MQTT_PORT = 18831            # mapeada no compose.test.yml (mosquitto 18831->1883)
    GATEWAY_ID = "sida_edge_001"
    SITE = "Enterprise_Site"
    DEVICE_ID = "Area_1_Line_1_Pump_01"
    SERVICES = ["mosquitto", "plc-sim", "edge1-core",
                "edge1-ingestion", "edge1-context", "edge1-delivery"]
    DELIVERY = "edge1-delivery"

    def __init__(self, compose: list[str], project: str):
        self._compose = compose
        self._project = ["-p", project]
        self.data_dir = COMPOSE_TEST.parent / "_data" / "edge1"

    def _dc(self, *args, timeout=1200, check=True):
        proc = subprocess.run(
            [*self._compose, "-f", str(COMPOSE_TEST), *self._project, *args],
            capture_output=True, text=True, timeout=timeout, cwd=COMPOSE_TEST.parent,
        )
        if check:
            assert proc.returncode == 0, f"`compose {' '.join(args)}` falhou:\n{proc.stderr}"
        return proc

    SCAN_RATE_MS = 300   # rapido: junta >256 mensagens (T1A.7) em ~80s

    def seed(self):
        proc = subprocess.run(
            ["python3", str(SEED_SCRIPT), "--data-dir", str(self.data_dir),
             "--gateway-id", self.GATEWAY_ID,
             "--broker-host", "mosquitto", "--modbus-host", "plc-sim",
             "--scan-rate-ms", str(self.SCAN_RATE_MS)],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, f"seed do sida_config.db falhou:\n{proc.stderr}"

    def up(self):
        self._dc("up", "-d", "--build", *self.SERVICES, timeout=1800)

    def down(self):
        self._dc("down", "-v", timeout=180, check=False)

    def restart_delivery(self, timeout=60):
        """Reinicia o container do delivery (novo processo Node-RED)."""
        self._dc("restart", "-t", "10", self.DELIVERY, timeout=timeout)

    def restart_broker(self, timeout=60):
        """Bounce do Mosquitto: forca uma reconexao MQTT do delivery SEM
        matar o processo (o contexto do fluxo, e o bdSeq, sobrevivem)."""
        self._dc("restart", "-t", "5", "mosquitto", timeout=timeout)

    def stop_delivery(self, timeout=45):
        """SIGTERM no delivery (encerramento limpo -> NDEATH gracioso)."""
        self._dc("stop", "-t", "20", self.DELIVERY, timeout=timeout)

    def kill_delivery(self, timeout=30):
        """SIGKILL no delivery (morte abrupta -> LWT pelo broker)."""
        self._dc("kill", "-s", "SIGKILL", self.DELIVERY, timeout=timeout, check=False)

    def start_delivery(self, timeout=60):
        self._dc("start", self.DELIVERY, timeout=timeout)


@pytest.fixture(scope="session")
def plane_a_node(require_compose):
    """Sobe a frota do plano A uma vez por sessao de teste; derruba no fim."""
    node = PlaneANode(require_compose, project="sida_e1_planea")
    node.down()          # limpa resto de execucao anterior
    node.seed()
    node.up()
    time.sleep(3)
    try:
        yield node
    finally:
        node.down()
