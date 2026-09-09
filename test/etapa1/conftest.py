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
SIDA_CORE = REPO_ROOT / "sida-core"
GOMOD_VOLUME = "sida_e1_gomod"   # cache de modulos Go entre execucoes


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


def reset_fleet_data(*nodes: int):
    """Apaga test/etapa1/_data/edgeN antes de re-semear. Os containers rodam
    como root e deixam o sida_config.db root:root no bind mount -> o seed do
    host (usuario comum) falharia com 'readonly database'. Um container
    descartavel apaga como root."""
    data = COMPOSE_TEST.parent / "_data"
    targets = " ".join(f"/d/edge{n}" for n in (nodes or (1, 2, 3)))
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{data}:/d", "alpine",
         "sh", "-c", f"rm -rf {targets}"],
        capture_output=True, text=True, timeout=60,
    )


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
        reset_fleet_data(1)
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


# --------------------------------------------------------------------------- plano B
class PlaneBFleet:
    """Sobe 1..3 `sida-core` (edge1..3) da compose.test.yml, ligados pela
    mesh_net dedicada, para os testes do plano B (peer-mesh ZeroMQ InterEdge).
    Os `*-core` publicam :8000 em 1800X e :5557 (peer-mesh) em 1557X no host."""

    CORE = {1: "edge1-core", 2: "edge2-core", 3: "edge3-core"}
    HTTP_PORT = {1: 18001, 2: 18002, 3: 18003}
    PEER_PORT_HOST = {1: 15571, 2: 15572, 3: 15573}
    PUB_PORT_HOST = {1: 15561}   # :5556 (manifesto) exposto só no edge1 (T1B.5)
    CONTROLLER_ID = {1: "edge_001", 2: "edge_002", 3: "edge_003"}

    def __init__(self, compose: list[str], project: str):
        self._compose = compose
        self._project = ["-p", project]

    def _dc(self, *args, timeout=1200, check=True):
        proc = subprocess.run(
            [*self._compose, "-f", str(COMPOSE_TEST), *self._project, *args],
            capture_output=True, text=True, timeout=timeout, cwd=COMPOSE_TEST.parent,
        )
        if check:
            assert proc.returncode == 0, (
                f"`compose {' '.join(args)}` falhou:\n{proc.stderr}\n{proc.stdout}"
            )
        return proc

    def down(self):
        self._dc("down", "-v", timeout=200, check=False)

    def up(self, *nodes, timeout=1800):
        self._dc("up", "-d", "--build", *[self.CORE[n] for n in nodes], timeout=timeout)

    def restart(self, node, timeout=120):
        self._dc("restart", "-t", "10", self.CORE[node], timeout=timeout)

    def stop(self, node, timeout=60):
        self._dc("stop", "-t", "10", self.CORE[node], timeout=timeout)

    def start(self, node, timeout=120):
        self._dc("start", self.CORE[node], timeout=timeout)

    def logs(self, node) -> str:
        p = self._dc("logs", "--no-color", self.CORE[node], timeout=30, check=False)
        return p.stdout + p.stderr

    def db_path(self, node) -> Path:
        return COMPOSE_TEST.parent / "_data" / f"edge{node}" / "sida_config.db"

    def db_query(self, node, sql: str, params=()):
        import sqlite3
        con = sqlite3.connect(f"file:{self.db_path(node)}?mode=ro", uri=True, timeout=5)
        try:
            return con.execute(sql, params).fetchall()
        finally:
            con.close()

    def wait_http(self, node, path="/api/system/info", timeout=120) -> bool:
        import requests
        url = f"http://localhost:{self.HTTP_PORT[node]}{path}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get(url, timeout=3).status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False

    def _url(self, node, path):
        return f"http://localhost:{self.HTTP_PORT[node]}{path}"

    def api_get(self, node, path, timeout=5):
        import requests
        r = requests.get(self._url(node, path), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def api_post(self, node, path, payload, timeout=5):
        import requests
        return requests.post(self._url(node, path), json=payload, timeout=timeout)

    def peers_api(self, node, timeout=5) -> dict:
        return self.api_get(node, "/api/system/peers", timeout=timeout)

    def run_oneoff_core(self, name: str, env: dict, settle_s: float = 6.0) -> str:
        """Sobe um sida-core efemero (sem deps) com env custom, colhe o log e o remove."""
        args = ["run", "-d", "--name", name, "--no-deps"]
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        args.append("edge1-core")
        self._dc(*args, timeout=400)
        try:
            time.sleep(settle_s)
            p = subprocess.run(["docker", "logs", name],
                               capture_output=True, text=True, timeout=30)
            return p.stdout + p.stderr
        finally:
            subprocess.run(["docker", "rm", "-f", name],
                           capture_output=True, text=True, timeout=30)

    @staticmethod
    def go_test(pkg: str = "./internal/core/domain/...", timeout: int = 600):
        return subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{SIDA_CORE}:/app", "-w", "/app",
             "-v", f"{GOMOD_VOLUME}:/go/pkg/mod",
             "-e", "CGO_ENABLED=0",
             "golang:alpine", "go", "test", pkg],
            capture_output=True, text=True, timeout=timeout,
        )


@pytest.fixture(scope="session")
def plane_b_fleet(require_compose):
    """Frota do plano B; cada teste sobe os nós de que precisa (`fleet.up(1,2)`)."""
    fleet = PlaneBFleet(require_compose, project="sida_e1_planeb")
    fleet.down()
    try:
        yield fleet
    finally:
        fleet.down()


# --------------------------------------------------------------------------- frota completa (S4)
_FLEET_SERVICES_OF = {
    n: [f"edge{n}-core", f"edge{n}-ingestion", f"edge{n}-context", f"edge{n}-delivery"]
    for n in (1, 2, 3)
}
_FLEET_ALL_SERVICES = ["mosquitto", "plc-sim"] + [
    s for lst in _FLEET_SERVICES_OF.values() for s in lst
]


class FullFleet:
    """Frota COMPLETA de 3 nós da compose.test.yml (cada nó = core + ingestion +
    context + delivery) + Mosquitto isolado + simulador Modbus. Base dos testes
    de frota (T3.2/T3.3) e da injeção de falha / teste de aceite (T4.3-T4.6)."""

    MQTT_HOST, MQTT_PORT = "localhost", 18831
    HTTP_PORT = {1: 18001, 2: 18002, 3: 18003}
    CONTROLLER_ID = {1: "edge_001", 2: "edge_002", 3: "edge_003"}
    GATEWAY_ID = {1: "sida_edge_001", 2: "sida_edge_002", 3: "sida_edge_003"}
    DEVICE_ID = "Area_1_Line_1_Pump_01"
    SITE = "Enterprise_Site"
    SCAN_RATE_MS = 500
    SERVICES_OF = _FLEET_SERVICES_OF
    ALL_SERVICES = _FLEET_ALL_SERVICES

    def __init__(self, compose: list[str], project: str):
        self._compose = compose
        self._project = ["-p", project]

    def _dc(self, *args, timeout=1800, check=True):
        proc = subprocess.run(
            [*self._compose, "-f", str(COMPOSE_TEST), *self._project, *args],
            capture_output=True, text=True, timeout=timeout, cwd=COMPOSE_TEST.parent,
        )
        if check:
            assert proc.returncode == 0, (
                f"`compose {' '.join(args)}` falhou:\n{proc.stderr}\n{proc.stdout[-2000:]}"
            )
        return proc

    def seed_all(self):
        reset_fleet_data(1, 2, 3)
        for n in (1, 2, 3):
            p = subprocess.run(
                ["python3", str(SEED_SCRIPT),
                 "--data-dir", str(COMPOSE_TEST.parent / "_data" / f"edge{n}"),
                 "--gateway-id", self.GATEWAY_ID[n],
                 "--broker-host", "mosquitto", "--modbus-host", "plc-sim",
                 "--scan-rate-ms", str(self.SCAN_RATE_MS)],
                capture_output=True, text=True, timeout=30,
            )
            assert p.returncode == 0, f"seed edge{n} falhou:\n{p.stderr}"

    def down(self):
        self._dc("down", "-v", "--remove-orphans", timeout=240, check=False)

    def up(self, timeout=2400):
        self.seed_all()
        self._dc("up", "-d", "--build", *self.ALL_SERVICES, timeout=timeout)

    def stop_node(self, n, timeout=90):
        self._dc("stop", "-t", "10", *self.SERVICES_OF[n], timeout=timeout)

    def start_node(self, n, timeout=180):
        self._dc("start", *self.SERVICES_OF[n], timeout=timeout)

    def logs(self, service, tail="all") -> str:
        p = self._dc("logs", "--no-color", "--tail", str(tail), service, timeout=40, check=False)
        return p.stdout + p.stderr

    def wait_http(self, node, path="/api/system/info", timeout=180) -> bool:
        import requests
        url = f"http://localhost:{self.HTTP_PORT[node]}{path}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get(url, timeout=3).status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False

    def peers_api(self, node, timeout=5) -> dict:
        import requests
        r = requests.get(
            f"http://localhost:{self.HTTP_PORT[node]}/api/system/peers", timeout=timeout
        )
        r.raise_for_status()
        return r.json()

    def _container_ids(self) -> list[str]:
        p = self._dc("ps", "-q", timeout=30, check=False)
        return [x for x in p.stdout.split() if x]

    def docker_stats(self) -> dict:
        """Amostra única de docker stats (cpu %, mem) dos containers DESTA frota."""
        ids = self._container_ids()
        if not ids:
            return {}
        p = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             "{{.Name}};{{.CPUPerc}};{{.MemUsage}}", *ids],
            capture_output=True, text=True, timeout=60,
        )
        out = {}
        for line in p.stdout.splitlines():
            parts = line.split(";")
            if len(parts) != 3:
                continue
            name, cpu, mem = parts
            try:
                cpu_v = float(cpu.strip().rstrip("%"))
            except ValueError:
                cpu_v = None
            out[name] = {"cpu_pct": cpu_v, "mem": mem.split("/")[0].strip()}
        return out


@pytest.fixture(scope="session")
def full_fleet(require_compose):
    """Sobe a frota completa de 3 nós uma vez por sessão; derruba no fim."""
    fleet = FullFleet(require_compose, project="sida_e1_fleet")
    fleet.down()
    fleet.up()
    time.sleep(3)
    try:
        yield fleet
    finally:
        fleet.down()
