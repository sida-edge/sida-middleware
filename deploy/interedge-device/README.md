# T2.1 — Firmware do dispositivo InterEdge (ESP32) · entregável de hardware

> **Status:** `pendente` (fora do loop automatizado — ver `progress.json`).
> Os checkpoints S5–S7 da Etapa 2 usam o simulador `test/etapa2/esp32_sim.py`
> como *stand-in*, exatamente como a Etapa 1 usou `oitc/modbus-server` no lugar
> do CLP. Este diretório recebe o firmware C/C++ real e o registro de bancada.

## Objetivo

Um **ESP32** (Classe 1, com Wi-Fi) publica um *device profile* InterEdge e
leituras periódicas no broker de ingestão do RPi (`mqtt-ingest`), atravessando o
mesmo pipeline homologado (`interedgeAdapter` → `context` ISA-95 → `delivery`
Sparkplug → UNS). Opcionalmente encadeia um sensor **Classe 0** sem rede
(ex.: TMP36 num Arduino Uno) por UART.

```
sensor Classe 0  --(UART/analógico)-->  ESP32 (Classe 1)  --Wi-Fi/MQTT-->  mqtt-ingest (RPi)
```

O `device_id` publicado no `mqtt-ingest` é o do **ESP32** (o Classe 0 é a fonte
física; o Classe 1 é o "controlador"). O manifesto mapeia o ESP32 na hierarquia
ISA-95 (`asset_context.path`), como em
[`../fleet/manifest.interedge.example.json`](../fleet/manifest.interedge.example.json).

## Contrato (idêntico ao do simulador)

`schemas/interedge_ingest.md` + `schemas/interedge_ingest.schema.json`.

| Tópico | Retenção | Payload |
|---|---|---|
| `sida/ingest/{device_id}/profile` | retido, no `connect` | identidade + `device_profile.metrics` |
| `sida/ingest/{device_id}/telemetry` | — | `{ "device_id", "ts", "readings": { … } }` |

As chaves de `readings` são os nomes lógicos das métricas — as mesmas do
`metrics_mapping` do device no manifesto (ex.: `temperature`, `running`).

## Toolchain sugerida (a definir na implementação)

- **Arduino-ESP32** ou **ESP-IDF**, C/C++.
- MQTT: `PubSubClient` (Arduino) ou `esp-mqtt` (IDF), apontando para
  `INGEST_BROKER_HOST:INGEST_BROKER_PORT` do RPi.
- Sensor: DHT11/DHT22 ou TMP36; UART para o encadeamento com o Classe 0.
- Identidade e endpoint **por configuração** (NVS / `menuconfig` / build flags),
  nunca hardcoded no código-fonte.

> Se a toolchain/hardware não *buildar* ou não rodar em bancada: **parar e
> reportar** — não trocar o alvo nem "simular" o firmware (SDD Etapa 2,
> Fronteira 9). A task fica `bloqueada` em `progress.json` com a causa.

## Registro de bancada (preencher na validação)

- [ ] `profile` retido visível em `mosquitto_sub -t 'sida/ingest/#' -v`
- [ ] `telemetry` periódica com ≥ 2 métricas (uma numérica, uma booleana)
- [ ] `DBIRTH`/`DDATA` do device no UNS isolado, tópico
      `spBv1.0/{group}/…/{node}/{Area_Line_Equipment}`, `engUnit` correto
- [ ] leitura do sensor Classe 0 chega contextualizada (caso 8 do SDD §5.5)
- [ ] fotos / logs / vídeo anexados a este diretório

Data: ____  ·  Responsável: ____  ·  Commit do firmware: ____
