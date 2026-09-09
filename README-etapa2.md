# SIDA — Etapa 2 do Ciclo V3.0: ingestão de dispositivos Classe 0/1 sem CLP

Guia operacional para subir um nó com ingestão InterEdge e rodar os testes. O
plano completo está em `SDD_SIDA_Etapa2_Ciclo_V3.md`; o avanço por task em
[`progress.json`](progress.json). A Etapa 1 (frota A+B) tem README e SDD
próprios e já está concluída.

## O que a Etapa 2 entrega

- **Dispositivo como "mais uma fonte de protocolo"** — o modelo `Connection`
  em `sida-core` aceita `protocol: "interedge"`; um device que **empurra**
  leituras não exige `host`/`port`/`scan_rate_ms`/`register_type` (validação
  condicional ao protocolo em `manifest_validation.go`). `asset_context`
  continua **obrigatório**: sem contexto ISA-95 não há ingestão.
- **Transporte de ingestão dedicado** — broker `mqtt-ingest` (Mosquitto local,
  anônimo), **distinto** do broker do UNS de saída. O dispositivo publica em
  `sida/ingest/{device_id}/{profile,telemetry}`.
- **Adaptador InterEdge** — sub-fluxo novo em `core/ingestion/flows.json`
  (grupo *InterEdge Ingest*, aba *Messaging*): `mqtt in` →
  `interedgeAdapter` → o **mesmo** `ZQM Output` do ramo Modbus
  (`ipc:///tmp/.ipc/ingestion.ipc`). O ramo `modbusPolling`/`opcuaPolling`/
  `setupClient` fica **intacto**. O adaptador valida `device_id` contra o
  manifesto, normaliza `readings → data` (valor **cru**; o `context` aplica
  escala/tipo) e descarta o malformado com `node.warn("[interedge] descartado: …")`.
- **Nível organizacional do InterEdge** — o device sem CLP é mapeado na
  hierarquia ISA-95 pelo manifesto (`asset_context.path`), e o `context`/
  `delivery` o levam ao UNS como `DBIRTH`/`DDATA` no tópico Sparkplug correto,
  exatamente como um device com CLP.

O `context` e o `delivery` **não** mudam. O caminho Modbus TCP da v2.0 segue
publicando **em paralelo**, no mesmo nó, sem regressão.

## Contrato da mensagem de ingestão

`schemas/interedge_ingest.md` + `schemas/interedge_ingest.schema.json`.

```
sida/ingest/{device_id}/profile     # retido, publicado no connect do dispositivo
sida/ingest/{device_id}/telemetry   # periódico
  { "device_id": "esp32_a", "ts": 1730000000000,
    "readings": { "temperature": 25.4, "running": true } }
```

As chaves de `readings` são os **nomes lógicos** das métricas — as mesmas
chaves do `metrics_mapping` do device no manifesto. O `profile` é informativo:
**o manifesto é a fonte da verdade** da contextualização ISA-95.

## Mapeamento ISA-95 (exemplo)

[`deploy/fleet/manifest.interedge.example.json`](deploy/fleet/manifest.interedge.example.json)
tem dois devices na mesma `Line_1`:

| Device | `connection.protocol` | Chaves do `metrics_mapping` | `asset_context.path` termina em |
|---|---|---|---|
| `pump_01` | `modbus_tcp` (host/port/scan_rate) | `40001`, `40002` (registradores) | `Pump_01` |
| `esp32_a` | `interedge` (sem transporte de sondagem) | `temperature`, `running` (nomes lógicos) | `ESP32_A` |

O `DDATA` de `esp32_a` sai em
`spBv1.0/{group}/DDATA/{edge_node}/Area_1_Line_1_ESP32_A`, com `Temperature`
trazendo `engUnit="°C"` no `DBIRTH` — prova do nível organizacional para uma
fonte **sem CLP na origem**.

## Frota local de teste (isolada)

`test/etapa2/compose.test.yml` sobe **um nó completo** (core + ingestion +
context + delivery) + **dois brokers distintos** (`mosquitto-uns` host `18832`,
`mqtt-ingest` host `18841`) + `plc-sim` (`oitc/modbus-server`, caminho v2.0) +
`esp32-sim` (mock de dispositivo Classe 1). Prefixo de container `e2-` (não
colide com a frota `e1-` da Etapa 1).

```bash
# semear o sida_config.db do nó (pump_01 Modbus + esp32_a interedge [+ extras])
python3 test/etapa2/seed_node_config.py --data-dir test/etapa2/_data/edge \
    --gateway-id sida_edge_e2 --broker-host mosquitto-uns --modbus-host plc-sim \
    --extra-interedge esp32_b

docker compose -f test/etapa2/compose.test.yml -p sida_e2 up -d --build
```

O `mqtt in` da ingestão usa `INGEST_TOPIC_FILTER` (o Node-RED só substitui
`${VAR}` quando é o valor **inteiro** da propriedade — o curinga fica na env):

```
INGEST_BROKER_HOST=mqtt-ingest   INGEST_BROKER_PORT=1883
INGEST_TOPIC_ROOT=sida/ingest    INGEST_TOPIC_FILTER=sida/ingest/+/telemetry
```

## Testes

```bash
# mesmas libs da Etapa 1 (paho-mqtt, requests, protobuf, pyzmq)
python3 -m pip install -r test/etapa1/requirements.txt

pytest test/etapa2                 # checkpoints leves
pytest test/etapa2 --run-heavy     # inclui os que sobem containers
```

Rodar por arquivo (as fixtures de frota usam nomes de container fixos e não
devem coexistir na mesma sessão):

| Sprint | Tasks | Teste *(todos heavy)* |
|---|---|---|
| S5 | `T2.4`, `T2.2a`, `T2.SIM` | `test_s5_interedge_contract.py` |
| S6 | `T2.2b`, `T2.3` | `test_s6_interedge_adapter.py` |
| S7 | `T2.5`, `T2.6`, `T2.RPT` | `test_s7_e2e_interedge.py` |

```bash
pytest test/etapa2/test_s5_interedge_contract.py --run-heavy
pytest test/etapa2/test_s6_interedge_adapter.py  --run-heavy
pytest test/etapa2/test_s7_e2e_interedge.py      --run-heavy

# não-regressão do caminho v2.0 (obrigatória a cada checkpoint)
pytest test/etapa1/test_s1_foundation.py::test_baseline_v2_pipeline --run-heavy
```

`test_s7_e2e_interedge.py::test_report_e_aceite` gera
`test/etapa2/report.json` (gitignored): latência sensor→UNS (p50/p95),
`interedge` publicadas vs. entregues (`perda == 0` no regime estável),
`isa95_ok`, `source_protocol` observado por device, e *overhead* CPU/RAM
(`docker stats`) de `mqtt-ingest` e `ingestion`. A sonda de latência é o
device `esp32_b` — semeado sem simulador; o teste publica a sua `telemetry`
com valores únicos e casa cada leitura com o `DDATA` correspondente no UNS.

## Firmware ESP32 (T2.1 — entregável de hardware, fora do loop)

O firmware C/C++ real (device/network profile InterEdge; encadeamento
Classe 0 → ESP32 → RPi) é validado **em bancada** e documentado em
`deploy/interedge-device/README.md`. Os checkpoints S5–S7 usam o simulador
(`test/etapa2/esp32_sim.py`), como a Etapa 1 usou `oitc/modbus-server` no
lugar do CLP.

## Ferramentas necessárias

`docker` + `docker compose` v2, `python3` (3.10+), `protobuf-compiler`
(`protoc`) para os testes que decodificam Sparkplug, e as libs de
`test/etapa2/requirements.txt`. O `sida-core` é compilado/testado dentro de um
contêiner `golang:alpine` pelos próprios testes — não é preciso Go nem `libzmq`
no host.
