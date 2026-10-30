#!/usr/bin/env python3
"""Simulador de dispositivo Classe 1 (mock ESP32) para os testes da Etapa 2.

Stand-in do firmware real (T2.1) nos checkpoints automatizados — assim como o
`oitc/modbus-server` fez o papel do CLP na Etapa 1. Publica, no broker de
INGESTAO (nao no UNS):

  sida/ingest/{DEVICE_ID}/profile    (retido, 1x no boot)   -> device profile InterEdge minimo
  sida/ingest/{DEVICE_ID}/telemetry  (a cada INTERVAL_MS)   -> { device_id, ts, readings }

Parametrizado por env:
  DEVICE_ID          (default esp32_a)
  INGEST_BROKER_HOST (default mqtt-ingest)   INGEST_BROKER_PORT (default 1883)
  INGEST_TOPIC_ROOT  (default sida/ingest)
  INTERVAL_MS        (default 1000)
  TEMP_BASE / TEMP_AMP (default 23.0 / 3.0)  -> temperatura ~ base + amp*sin(t)
"""
from __future__ import annotations

import json
import math
import os
import time

import paho.mqtt.client as mqtt

DEVICE_ID = os.getenv("DEVICE_ID", "esp32_a")
HOST = os.getenv("INGEST_BROKER_HOST", "mqtt-ingest")
PORT = int(os.getenv("INGEST_BROKER_PORT", "1883"))
ROOT = os.getenv("INGEST_TOPIC_ROOT", "sida/ingest").rstrip("/")
INTERVAL = int(os.getenv("INTERVAL_MS", "1000")) / 1000.0
TEMP_BASE = float(os.getenv("TEMP_BASE", "23.0"))
TEMP_AMP = float(os.getenv("TEMP_AMP", "3.0"))

PROFILE = {
    "device_id": DEVICE_ID,
    "class": 1,
    "vendor": "espressif",
    "network_profile": {"transport": "mqtt", "interval_ms": int(INTERVAL * 1000)},
    "device_profile": {
        "metrics": {
            "temperature": {"type": "float", "unit": "°C"},
            "running": {"type": "bool"},
        }
    },
}


def main() -> None:
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"esp32-sim-{DEVICE_ID}")
    cli.on_connect = lambda c, u, f, rc, p=None: c.publish(
        f"{ROOT}/{DEVICE_ID}/profile", json.dumps(PROFILE), qos=1, retain=True
    )
    for _ in range(60):
        try:
            cli.connect(HOST, PORT, keepalive=30)
            break
        except OSError as e:
            print(f"[esp32-sim] aguardando {HOST}:{PORT} ({e})", flush=True)
            time.sleep(2)
    else:
        raise SystemExit(f"[esp32-sim] nao conectou a {HOST}:{PORT}")

    cli.loop_start()
    print(f"[esp32-sim] {DEVICE_ID} publicando em {ROOT}/{DEVICE_ID}/telemetry @ {INTERVAL}s", flush=True)
    t0 = time.time()
    while True:
        t = time.time() - t0
        reading = {
            "device_id": DEVICE_ID,
            "ts": int(time.time() * 1000),
            "readings": {
                "temperature": round(TEMP_BASE + TEMP_AMP * math.sin(t / 5.0), 2),
                "running": (int(t) % 20) < 15,
            },
        }
        cli.publish(f"{ROOT}/{DEVICE_ID}/telemetry", json.dumps(reading), qos=0, retain=False)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
