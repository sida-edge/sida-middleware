#!/usr/bin/env python3
"""Semeia o sida_config.db do no da frota de teste da Etapa 2 do Ciclo V3.0.

Manifesto com DOIS devices na mesma linha ISA-95:
  - pump_01 (protocol modbus_tcp) -> caminho v2.0, garante a nao-regressao;
  - esp32_a (protocol interedge)  -> dispositivo Classe 1 sem CLP (empurra
    leituras pelo broker de ingestao). Sem host/port/scan_rate/register_type;
    as chaves do metrics_mapping sao os nomes logicos do `readings` do device.

    python3 test/etapa2/seed_node_config.py --data-dir test/etapa2/_data/edge \
        --gateway-id sida_edge_e2 --broker-host mosquitto-uns --modbus-host plc-sim

Espelha sida-core/internal/adapters/repository/sqlite_repository.go.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS edge_manifests (
    gateway_id TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def modbus_device(modbus_host: str, modbus_port: int, scan_rate_ms: int) -> dict:
    return {
        "enabled": True,
        "connection": {
            "protocol": "modbus_tcp",
            "scan_rate_ms": scan_rate_ms,
            "host": modbus_host,
            "port": modbus_port,
            "unit_id": 1,
            "byte_order": "ABCD",
        },
        "asset_context": {
            "standard": "ISA-95",
            "path": [
                {"type": "area", "id": "Area_1"},
                {"type": "line", "id": "Line_1"},
                {"type": "equipment", "id": "Pump_01"},
            ],
        },
        "metrics_mapping": {
            "40001": {"register_type": "holding", "name": "Temperature",
                      "scale_factor": 0.1, "unit": "°C", "data_type": "int16"},
            "40002": {"register_type": "holding", "name": "Running",
                      "scale_factor": 1.0, "unit": "", "data_type": "bool"},
        },
    }


def interedge_device(device_id: str = "esp32_a", equipment_id: str = "ESP32_A") -> dict:
    """Dispositivo Classe 1 sem CLP. `connection.protocol == "interedge"` — sem
    host/port/scan_rate_ms/register_type. As chaves do metrics_mapping sao os
    nomes do `readings` que o dispositivo publica (`temperature`, `running`)."""
    return {
        "enabled": True,
        "connection": {"protocol": "interedge"},
        "asset_context": {
            "standard": "ISA-95",
            "path": [
                {"type": "area", "id": "Area_1"},
                {"type": "line", "id": "Line_1"},
                {"type": "equipment", "id": equipment_id},
            ],
        },
        "metrics_mapping": {
            "temperature": {"name": "Temperature", "scale_factor": 1.0,
                            "unit": "°C", "data_type": "float"},
            "running": {"name": "Running", "scale_factor": 1.0,
                        "unit": "", "data_type": "bool"},
        },
    }


def build_config(broker_host: str, broker_port: int, modbus_host: str, modbus_port: int,
                 scan_rate_ms: int = 1000, with_interedge: bool = True,
                 extra_interedge: list[str] | None = None) -> dict:
    devices = {"pump_01": modbus_device(modbus_host, modbus_port, scan_rate_ms)}
    if with_interedge:
        devices["esp32_a"] = interedge_device("esp32_a", "ESP32_A")
    for dev_id in (extra_interedge or []):
        devices[dev_id] = interedge_device(dev_id, dev_id.replace("esp32_", "ESP32_").upper())
    return {
        "plant": {
            "enterprise": "Enterprise",
            "site": "Site",
            "areas": {"Area_1": {"lines": {"Line_1": {"devices": devices}}}},
        },
        "receivers": {
            "uns": {"protocol": "mqtt", "host": broker_host, "port": broker_port,
                    "endpoint": "", "username": "", "password": ""},
        },
    }


def seed(data_dir: Path, gateway_id: str, config: dict) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "sida_config.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DDL)
        conn.execute(
            "INSERT INTO edge_manifests (gateway_id, config_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(gateway_id) DO UPDATE SET config_json=excluded.config_json, "
            "updated_at=excluded.updated_at",
            (gateway_id, json.dumps(config), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, type=Path)
    ap.add_argument("--gateway-id", required=True)
    ap.add_argument("--broker-host", default="mosquitto-uns")
    ap.add_argument("--broker-port", default=1883, type=int)
    ap.add_argument("--modbus-host", default="plc-sim")
    ap.add_argument("--modbus-port", default=5020, type=int)
    ap.add_argument("--scan-rate-ms", default=1000, type=int)
    ap.add_argument("--no-interedge", action="store_true",
                    help="semeia so o device Modbus (baseline)")
    ap.add_argument("--extra-interedge", nargs="*", default=[],
                    help="ids extras de dispositivos interedge (ex.: esp32_b)")
    args = ap.parse_args()

    cfg = build_config(args.broker_host, args.broker_port, args.modbus_host, args.modbus_port,
                       scan_rate_ms=args.scan_rate_ms, with_interedge=not args.no_interedge,
                       extra_interedge=args.extra_interedge)
    db = seed(args.data_dir, args.gateway_id, cfg)
    n_dev = len(cfg["plant"]["areas"]["Area_1"]["lines"]["Line_1"]["devices"])
    print(f"seeded {db} :: gateway_id={args.gateway_id} devices={n_dev}")


if __name__ == "__main__":
    main()
