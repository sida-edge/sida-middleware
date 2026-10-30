# Contrato de ingestão InterEdge — dispositivos Classe 0/1 sem CLP (Etapa 2)

O dispositivo (ou o mock `test/etapa2/esp32_sim.py`) publica no **broker de
ingestão** (`mqtt-ingest`, tópico-raiz `sida/ingest`, **distinto do broker do
UNS**). Duas mensagens:

| Tópico | Retido | Cadência | Conteúdo |
|---|---|---|---|
| `sida/ingest/{device_id}/profile` | sim | 1× no boot | *device profile* InterEdge mínimo (identidade, métricas, transporte) |
| `sida/ingest/{device_id}/telemetry` | não (`qos 0`) | periódica | leitura corrente (`readings`) |

## `profile`

```json
{
  "device_id": "esp32_a",
  "class": 1,
  "vendor": "espressif",
  "network_profile": { "transport": "mqtt", "interval_ms": 1000 },
  "device_profile": {
    "metrics": {
      "temperature": { "type": "float", "unit": "°C" },
      "running":     { "type": "bool" }
    }
  }
}
```

O `profile` é **informativo** (diagnóstico/observabilidade). A **verdade da
contextualização** é o **manifesto do SIDA** (`asset_context` + `metrics_mapping`
do device, resolvidos pelo `context` via `device_id`). Se `profile` divergir do
manifesto, **o manifesto vence** e o adaptador loga um aviso.

## `telemetry`

```json
{
  "device_id": "esp32_a",
  "ts": 1731000000000,
  "readings": { "temperature": 23.7, "running": true }
}
```

- `device_id` (string, obrigatório) — deve existir no manifesto do nó, senão a
  leitura é **descartada** (`[interedge] descartado: device_id 'X' ausente no
  manifesto`).
- `ts` (epoch ms, opcional) — usado como `timestamp` do payload interno se
  plausível; senão `Date.now()` do RPi.
- `readings` (objeto, obrigatório) — chave = **nome lógico** da métrica (ex.:
  `"temperature"`), que deve constar do `metrics_mapping` do device no manifesto.
  Chave não mapeada é ignorada com aviso.

## O que o adaptador produz (payload interno do SIDA)

Mesmo shape que o ramo Modbus já emite:

```json
{
  "timestamp": 1731000000000,
  "gateway_id": "sida_edge_e2",
  "source": { "device_id": "esp32_a", "source_protocol": "interedge" },
  "data": { "temperature": 23.7, "running": true }
}
```

injetado no `zeromq out` `ipc:///tmp/.ipc/ingestion.ipc` — o `context` aplica
ISA-95 exatamente como faz para um device Modbus.

## Manifesto (device `interedge`)

`connection.protocol == "interedge"` — **sem** `host`/`port`/`scan_rate_ms`/
`register_type` (o dispositivo empurra, não é sondado). `asset_context`
**continua obrigatório**.

```json
"esp32_a": {
  "enabled": true,
  "connection": { "protocol": "interedge" },
  "asset_context": { "standard": "ISA-95", "path": [
    { "type": "area", "id": "Area_1" },
    { "type": "line", "id": "Line_1" },
    { "type": "equipment", "id": "ESP32_A" } ] },
  "metrics_mapping": {
    "temperature": { "name": "Temperature", "scale_factor": 1.0, "unit": "°C", "data_type": "float" },
    "running":     { "name": "Running",     "scale_factor": 1.0, "unit": "",   "data_type": "bool"  }
  }
}
```

O JSON Schema da mensagem de `telemetry` está em
[`interedge_ingest.schema.json`](interedge_ingest.schema.json).
