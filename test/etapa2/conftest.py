"""Fixtures da suite da Etapa 2 do Ciclo V3.0 (ingestao Classe 0/1 sem CLP).

Reaproveita o padrao da Etapa 1: `--run-heavy` para os testes que sobem
containers; skip acionavel quando falta ferramenta.
"""
from __future__ import annotations

import hashlib
import importlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

ETAPA2_DIR = Path(__file__).resolve().parent
REPO_ROOT = ETAPA2_DIR.parents[1]
COMPOSE = ETAPA2_DIR / "compose.test.yml"
SEED = ETAPA2_DIR / "seed_node_config.py"
SIDA_CORE = REPO_ROOT / "sida-core"
PROTO = REPO_ROOT / "schemas" / "sparkplug_b.proto"
GOMOD_VOLUME = "sida_e1_gomod"

PIN = "000000"
BEARER = "Bearer session_" + hashlib.sha256(PIN.encode()).hexdigest()

UNS_PORT = 18832
INGEST_PORT = 18841
CORE_PORT = 18011


def pytest_addoption(parser):
    parser.addoption("--run-heavy", action="store_true", default=False,
                     help="Executa os passos que sobem containers. Lento.")


def pytest_configure(config):
    config.addinivalue_line("markers", "heavy: sobe containers; exige --run-heavy")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-heavy"):
        return
    skip = pytest.mark.skip(reason="passo pesado; rode com --run-heavy")
    for item in items:
        if "heavy" in item.keywords:
            item.add_marker(skip)


def _which(cmd):
    import shutil
    return shutil.which(cmd)


@pytest.fixture(scope="session")
def require_compose():
    if not _which("docker"):
        pytest.skip("instale docker + docker compose v2")
    try:
        subprocess.run(["docker", "compose", "version"], check=True,
                       capture_output=True, timeout=15)
    except Exception:
        pytest.skip("docker compose v2 indisponivel")
    return ["docker", "compose"]


@pytest.fixture(scope="session")
def require_paho():
    try:
        import paho.mqtt.client as mqtt  # noqa: F401
    except Exception:
        pytest.skip("instale paho-mqtt")
    import paho.mqtt.client as mqtt
    return mqtt


@pytest.fixture(scope="session")
def spb_pb2(tmp_path_factory):
    try:
        import google.protobuf  # noqa: F401
    except Exception:
        pytest.skip("instale o runtime protobuf ('pip install protobuf')")
    protoc = _which("protoc")
    if not protoc:
        pytest.skip("instale protobuf-compiler (protoc)")
    out = tmp_path_factory.mktemp("spb_pb2_e2")
    p = subprocess.run([protoc, f"--proto_path={PROTO.parent}", f"--python_out={out}", PROTO.name],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    sys.path.insert(0, str(out))
    return importlib.import_module("sparkplug_b_pb2")


# --------------------------------------------------------------------------- frota
class Etapa2Fleet:
    UNS_PORT, INGEST_PORT, CORE_PORT = UNS_PORT, INGEST_PORT, CORE_PORT
    GATEWAY_ID = "sida_edge_e2"
    SITE = "Enterprise_Site"
    DEVICE_ESP = "Area_1_Line_1_ESP32_A"
    DEVICE_PUMP = "Area_1_Line_1_Pump_01"
    FULL = ["mosquitto-uns", "mqtt-ingest", "plc-sim", "esp32-sim",
            "edge-core", "edge-ingestion", "edge-context", "edge-delivery"]

    def __init__(self, compose, project):
        self._c = compose
        self._p = ["-p", project]
        self.data_dir = ETAPA2_DIR / "_data" / "edge"

    def _dc(self, *args, timeout=1800, check=True):
        p = subprocess.run([*self._c, "-f", str(COMPOSE), *self._p, *args],
                           capture_output=True, text=True, timeout=timeout, cwd=ETAPA2_DIR)
        if check:
            assert p.returncode == 0, f"`compose {' '.join(args)}` falhou:\n{p.stderr}\n{p.stdout[-2000:]}"
        return p

    def reset_data(self):
        # `_data/edge` e bind-mount do /app/data do core: os containers rodam
        # como root e o deixam root:root, entao o seed do host (usuario comum)
        # falharia. Um container descartavel apaga e devolve a posse ao host.
        data = ETAPA2_DIR / "_data"
        data.mkdir(exist_ok=True)
        import os as _os
        uid, gid = _os.getuid(), _os.getgid()
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{data}:/d", "alpine",
             "sh", "-c", f"rm -rf /d/edge && chown -R {uid}:{gid} /d"],
            capture_output=True, text=True, timeout=60,
        )

    def seed(self, *extra_interedge, no_interedge=False):
        self.reset_data()
        args = ["python3", str(SEED), "--data-dir", str(self.data_dir),
                "--gateway-id", self.GATEWAY_ID, "--broker-host", "mosquitto-uns",
                "--modbus-host", "plc-sim"]
        if no_interedge:
            args.append("--no-interedge")
        if extra_interedge:
            args += ["--extra-interedge", *extra_interedge]
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, f"seed falhou:\n{p.stderr}"

    def down(self):
        self._dc("down", "-v", "--remove-orphans", timeout=200, check=False)

    def up(self, *services, timeout=2400):
        self._dc("up", "-d", "--build", *(services or self.FULL), timeout=timeout)

    def restart(self, service, timeout=90):
        self._dc("restart", "-t", "10", service, timeout=timeout)

    def logs(self, service, tail="all"):
        p = self._dc("logs", "--no-color", "--tail", str(tail), service, timeout=40, check=False)
        return p.stdout + p.stderr

    def core_url(self, path=""):
        return f"http://localhost:{self.CORE_PORT}{path}"

    def wait_http(self, path="/api/system/info", timeout=120):
        import requests
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                if requests.get(self.core_url(path), timeout=3).status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False

    def wait_port(self, port, timeout=60):
        import socket as _s
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                with _s.create_connection(("localhost", port), timeout=2):
                    return True
            except OSError:
                time.sleep(1)
        return False

    def mqtt_connect(self, mqtt_mod, port, client_id, timeout=45):
        """Conecta um cliente paho com retry (broker pode demorar a expor a porta)."""
        cli = mqtt_mod.Client(mqtt_mod.CallbackAPIVersion.VERSION2, client_id=client_id)
        dl = time.time() + timeout
        while time.time() < dl:
            try:
                cli.connect("localhost", port, keepalive=15)
                return cli
            except OSError:
                time.sleep(2)
        raise AssertionError(f"nao conectou a localhost:{port}")

    def get_manifest(self):
        import requests
        r = requests.get(self.core_url("/api/config/manifest"),
                         params={"gateway_id": self.GATEWAY_ID}, timeout=5)
        return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)

    def post_manifest(self, config: dict, gateway_id: str | None = None):
        import requests
        body = {"gateway_id": gateway_id or self.GATEWAY_ID, "config": config}
        return requests.post(self.core_url("/api/config/manifest"), json=body,
                             headers={"Authorization": BEARER}, timeout=8)

    def docker_stats(self):
        ids = [x for x in self._dc("ps", "-q", timeout=30, check=False).stdout.split() if x]
        if not ids:
            return {}
        p = subprocess.run(["docker", "stats", "--no-stream", "--format",
                            "{{.Name}};{{.CPUPerc}};{{.MemUsage}}", *ids],
                           capture_output=True, text=True, timeout=60)
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

    @staticmethod
    def go_test(pkg="./internal/core/domain/...", timeout=600):
        return subprocess.run(
            ["docker", "run", "--rm", "-v", f"{SIDA_CORE}:/app", "-w", "/app",
             "-v", f"{GOMOD_VOLUME}:/go/pkg/mod", "-e", "CGO_ENABLED=0",
             "golang:alpine", "go", "test", pkg],
            capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="session")
def etapa2_core(require_compose):
    """So o sida-core + o broker de ingestao — para os testes de contrato (S5)."""
    f = Etapa2Fleet(require_compose, project="sida_e2")
    f.down()
    f.seed()
    f.up("edge-core", "mqtt-ingest", "mosquitto-uns", timeout=1200)
    f.wait_port(f.INGEST_PORT, timeout=60)
    f.wait_port(f.UNS_PORT, timeout=30)
    time.sleep(2)
    try:
        yield f
    finally:
        f.down()


@pytest.fixture(scope="session")
def etapa2_node(require_compose):
    """No completo: core + ingestion + context + delivery + os dois brokers +
    plc-sim + esp32-sim. Para S6/S7."""
    f = Etapa2Fleet(require_compose, project="sida_e2")
    f.down()
    f.seed()
    f.up(timeout=2400)
    time.sleep(3)
    try:
        yield f
    finally:
        f.down()
