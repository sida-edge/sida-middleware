#!/usr/bin/env python3
"""Semeia o sida_config.db de um nó da frota de teste (Etapa 1 do Ciclo V3.0).

Roda no HOST (stdlib apenas), ANTES do `docker compose ... up`, gravando o
manifesto que o sida-core serve em /api/config/manifest. Sem ele, a baseline
v2.0 não sobe (ingestion/context/delivery dependem do manifesto: plant,
device Modbus e receiver mqtt).

    python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge1 \
        --gateway-id sida_edge_001 --broker-host mosquitto --modbus-host plc-sim

O schema de `edge_manifests` espelha sida-core/internal/adapters/repository/
sqlite_repository.go (CREATE TABLE IF NOT EXISTS). O mapa de registradores
Modbus casa com test/etapa1/modbus.test.json (imagem oitc/modbus-server):
  - 40001 (holding, int16) -> endereço de fio 0 -> chave "1" do JSON = 235
                              -> scale 0.1 -> 23.5 °C
  - 40002 (holding, bool)  -> endereço de fio 1 -> chave "2" do JSON = 1
                              -> Running = true
O flow de ingestão converte 4xxxx em (addr-40001), lê 1 registrador por
métrica não-float e a imagem serve a chave N no endereço N-1 (pymodbus
zero_mode=False). Valores estáticos bastam: o DeliveryProcessor emite DDATA
a cada ciclo de leitura, sem report-by-exception.
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


def build_config(broker_host: str, broker_port: int, modbus_host: str, modbus_port: int) -> dict:
    return {
        "plant": {
            "enterprise": "Enterprise",
            "site": "Site",
            "areas": {
                "Area_1": {
                    "lines": {
                        "Line_1": {
                            "devices": {
                                "pump_01": {
                                    "enabled": True,
                                    "connection": {
                                        "protocol": "modbus_tcp",
                                        "scan_rate_ms": 1000,
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
                                        "40001": {
                                            "register_type": "holding",
                                            "name": "Temperature",
                                            "scale_factor": 0.1,
                                            "unit": "°C",
                                            "data_type": "int16",
                                        },
                                        "40002": {
                                            "register_type": "holding",
                                            "name": "Running",
                                            "scale_factor": 1.0,
                                            "unit": "",
                                            "data_type": "bool",
                                        },
                                    },
                                }
                            }
                        }
                    }
                }
            },
        },
        "receivers": {
            "uns": {
                "protocol": "mqtt",
                "host": broker_host,
                "port": broker_port,
                "endpoint": "",
                "username": "",
                "password": "",
            }
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
    ap.add_argument("--broker-host", default="mosquitto")
    ap.add_argument("--broker-port", default=1883, type=int)
    ap.add_argument("--modbus-host", default="plc-sim")
    ap.add_argument("--modbus-port", default=5020, type=int)
    args = ap.parse_args()

    cfg = build_config(args.broker_host, args.broker_port, args.modbus_host, args.modbus_port)
    db = seed(args.data_dir, args.gateway_id, cfg)
    print(f"seeded {db} :: gateway_id={args.gateway_id} broker={args.broker_host}:{args.broker_port}")


if __name__ == "__main__":
    main()
