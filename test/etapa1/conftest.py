"""Fixtures e deteccao de ferramentas para a suite da Etapa 1 do Ciclo V3.0.

Os testes marcados como "funcionais" (checkpoint por task, SDD secao 3.3.1)
precisam de: docker + docker compose, um compilador protobuf (protoc ou
grpc_tools.protoc) e paho-mqtt. Quando a ferramenta nao esta disponivel o
teste e PULADO com uma mensagem acionavel — nunca falha por ambiente.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ETAPA1_DIR = Path(__file__).resolve().parent
COMPOSE_TEST = ETAPA1_DIR / "compose.test.yml"
FLEET_DIR = REPO_ROOT / "deploy" / "fleet"


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
