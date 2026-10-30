# Tutorial SIDA — Ciclo V3.0

Guia único, instrutivo e verificável de ponta a ponta do **SIDA** depois do
Ciclo V3.0. Cobre o que subir, como subir e **como verificar cada caso de uso**
introduzido/alterado pelos três SDDs do ciclo, com comandos prontos e o teste
automatizado que serve de prova para cada um.

Documentos de referência (mais profundos, cada um no seu escopo):

| Documento | Escopo | Situação |
|---|---|---|
| [`SDD_SIDA_Etapa1_Ciclo_V3.md`](SDD_SIDA_Etapa1_Ciclo_V3.md) | Frota descentralizada e resiliente: ciclo de vida Sparkplug B (plano norte **A**) + malha *controller-to-controller* InterEdge (plano leste-oeste **B**) + injeção de falha | **Concluído** (22 tasks, `progress.json`) |
| [`SDD_SIDA_Etapa2_Ciclo_V3.md`](SDD_SIDA_Etapa2_Ciclo_V3.md) | Ingestão de dispositivos **Classe 0/1 sem CLP** (`protocol: "interedge"`) como "mais uma fonte de protocolo" | **Concluído** no loop automatizado (S5–S7); resta `T2.1` = firmware ESP32 (bancada) |
| [`SDD_SIDA_UNS_Web_Client.md`](SDD_SIDA_UNS_Web_Client.md) | Cliente web MQTT/WebSocket que **consome** o UNS, decodifica Sparkplug B e desenha o dashboard | **Concluído** |

READMEs operacionais que este tutorial consolida:
[`README-etapa1.md`](README-etapa1.md) · [`README-etapa2.md`](README-etapa2.md) ·
[`sida-uns-client/README.md`](sida-uns-client/README.md) ·
[`deploy/fleet/identities.md`](deploy/fleet/identities.md) ·
[`schemas/interedge_ingest.md`](schemas/interedge_ingest.md).

---

## 0. O que o Ciclo V3.0 mudou (mapa rápido)

O caminho de dados da v2.0 (**Modbus/OPC UA → contextualização ISA‑95 →
Sparkplug B → UNS**) **não foi alterado**. O V3 acrescentou quatro capacidades,
todas por **adição**:

| # | Capacidade | Onde vive | Como se verifica |
|---|---|---|---|
| A | **Delta de conformidade Sparkplug B**: `bdSeq` de sessão correlacionando `NBIRTH`↔`NDEATH`/LWT, `DBIRTH` declara `alias` por métrica, `DDATA` referencia **só alias**, `NDEATH` **gracioso** no encerramento limpo | `core/delivery/flows.json` (`setupConnectors`, `DeliveryProcessor`); `schemas/sparkplug_b.proto` versionado | `mosquitto_sub -t 'spBv1.0/#'` + decodificação; `test/etapa1/test_plane_a_lifecycle.py` |
| B | **Malha *controller-to-controller* (plano leste‑oeste)**: cada `sida-core` mantém uma malha ZeroMQ ROUTER/DEALER dedicada (`PEER_PORT`, default `5557`), registro de pares, *probes* periódicos, FSM de *liveness* local (`alive`/`suspect`/`down`), roteamento InterEdge | `sida-core` (Go): `internal/core/domain/controller.go`, `internal/adapters/repository/sqlite_peer.go`, `internal/core/services/peer_service.go`, `internal/adapters/handler/peer_handler.go`; endpoint `GET /api/system/peers` | `curl .../api/system/peers`; `test/etapa1/test_plane_b_peermesh.py`, `test/etapa1/test_fleet.py` |
| C | **Frota sem SPOF de borda**: `docker-compose.yml` parametrizada por `.env`; a mesma pilha sobe em qualquer nó trocando só o `--env-file`. Eliminação do SPOF comprovada por **injeção de falha** | `docker-compose.yml`, `.env.example`, `deploy/fleet/` | `test/etapa1/test_fault_injection.py` → `test/etapa1/report.json` |
| D | **Ingestão Classe 0/1 sem CLP** (`interedge`): enum `Connection.Protocol` estendido, broker de ingestão dedicado `mqtt-ingest` (`sida/ingest/#`, ≠ UNS), sub‑fluxo adaptador novo | `sida-core/internal/core/domain/manifest.go` + `manifest_validation.go`; `core/ingestion/flows.json` (grupo *InterEdge Ingest*); `schemas/interedge_ingest.{md,schema.json}` | `test/etapa2/*`; `test/etapa2/report.json` |
| E | **UNS Web Client** (consumidor) | `sida-uns-client/` + `docker-compose.override.yml` | `./sida-uns-client/test/run.sh` |

Fronteiras que o ciclo respeitou (não mexeu): `core/ingestion/flows.json` e
`core/context/flows.json` do caminho Modbus; *store‑and‑forward*; redundância do
broker de nuvem; TLS/mTLS; troca do PIN por OAuth2; atuação em campo.

---

## 1. Arquitetura em uma tela

```
                          ┌───────────────────────── NÓ (Raspberry Pi) ─────────────────────────┐
  CLP / sensor Modbus ───▶│  ingestion (Node-RED)                                                │
  ESP32 / Classe 0-1  ───▶│    ├─ ramo Modbus/OPC UA  ─┐                                         │
   via mqtt-ingest        │    └─ InterEdge Ingest  ───┤─▶ IPC ZeroMQ  ─▶ context (Node-RED)     │
   (sida/ingest/#)        │                            │   ipc:///tmp/.ipc/ingestion.ipc         │
                          │                            │        aplica ISA-95 (asset_context)    │
                          │                            ▼                                         │
                          │                        delivery (Node-RED) ── Sparkplug B / MQTT ───▶│──▶ UNS (broker MQTT nuvem)
                          │                          NBIRTH/DBIRTH/DDATA/NDEATH + LWT            │        spBv1.0/#
                          │                                                                     │        ▲
                          │  sida-core (Go)  HTTP :8000  ·  PUB manifesto :5556                 │        │
                          │    └─ peer-mesh ZeroMQ :5557 (ROUTER/DEALER)  ◀── plano leste-oeste ─┼──▶ outros nós
                          └─────────────────────────────────────────────────────────────────────┘

  sida-uns-client (browser)  ──WebSocket── UNS  ◀── consumidor passivo, decodifica Sparkplug B
```

Os três Node-RED de um nó falam com **o `sida-core` daquele nó** pelo nome fixo
`sida-core` (alias de rede). O `bdSeq` de sessão do plano A é **persistido** em
`/tmp/.ipc/bdseq.<gateway_id>` (volume `sida_ipc`), sobrevive a `restart`/`stop`
de container e só zera no `docker compose down -v`.

---

## 2. Pré‑requisitos

- **Docker** + **Docker Compose v2** (`docker compose version`).
- **Python 3.10+**; para a suíte de testes:
  `python3 -m pip install -r test/etapa1/requirements.txt`
  (`pytest`, `paho-mqtt`, `requests`, `PyYAML`, `protobuf`, `pyzmq`; a Etapa 2
  reusa esse mesmo `requirements.txt`).
- **`protoc`** (`protobuf-compiler`) **ou** `pip install grpcio-tools` — para
  compilar `schemas/sparkplug_b.proto` e decodificar payloads Sparkplug B.
- **`mosquitto-clients`** (`mosquitto_sub` / `mosquitto_pub`) e **`jq`** — para a
  verificação manual.
- **Go e `libzmq` não são necessários no host**: o `sida-core` é compilado e
  testado dentro de um contêiner `golang:alpine` pelos próprios testes.
- Se `docker ps` der `permission denied` nesta máquina:
  `sudo setfacl -m u:jackson:rw /var/run/docker.sock` (a ACL some quando o
  socket é recriado — repetir se necessário).

---

## 3. Subir o SIDA

Há **três formas** de subir, conforme o que você quer exercitar. Todas isoladas
do broker de produção.

### 3.1 Um nó "produção‑like" (`docker-compose.yml` + `.env`)

Pilha completa de um nó + Neo4j + `ontology-builder`. A identidade vem **só** do
`.env`.

```bash
cp .env.example .env            # edite EDGE_GATEWAY_ID, GROUP_ID, BROKER_URL, PEERS, PIN…
docker compose up -d --build    # compose lê ./.env automaticamente
# ou, sem editar, usando uma identidade de frota pronta:
docker compose --env-file deploy/fleet/edge_001.env up -d --build
```

Portas: `sida-core` HTTP `:8000` e peer‑mesh `:${PEER_PORT:-5557}`;
`poc-ingestion` editor Node‑RED `:1881`, `poc-context` `:1882`,
`poc-delivery` `:1883`; Neo4j `:7474`/`:7687`.

Provisionar o manifesto ISA‑95 (device + `asset_context` + `metrics_mapping` +
receiver `uns`) — em produção, via UI ou `POST /api/config/manifest`
(ver §4.4, caso 6). Sem manifesto não há ingestão.

```bash
curl -s localhost:8000/api/health
curl -s localhost:8000/api/system/info        # {"provisioned":true,"gateway_id":"…"}  ou {"provisioned":false}
curl -s localhost:8000/api/system/peers | jq  # {"controller_id":"…","peers":[…]}
```

Derrubar: `docker compose down` (mantém o `bdSeq`) ou `down -v` (zera tudo).

### 3.2 Frota isolada de 3 nós (Etapa 1 — `test/etapa1/compose.test.yml`)

3 nós completos (`edge_001..003`) + 1 Mosquitto local (host `18831`) + 1
simulador Modbus público (`oitc/modbus-server`). É a bancada de verificação dos
planos A, B e da injeção de falha.

```bash
# 1) semear o sida_config.db de cada nó (plant + device Modbus + receiver mqtt)
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge1 --gateway-id sida_edge_001
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge2 --gateway-id sida_edge_002
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge3 --gateway-id sida_edge_003

# 2) subir (prefixo de container e1-, projeto sida_e1)
docker compose -f test/etapa1/compose.test.yml -p sida_e1 up -d --build
```

Mapeamento de portas no host:

| Nó | `sida-core` HTTP | peer‑mesh `:5557` | PUB manifesto `:5556` |
|---|---|---|---|
| edge_001 | `localhost:18001` | `15571` | `15561` (só este nó) |
| edge_002 | `localhost:18002` | `15572` | — |
| edge_003 | `localhost:18003` | `15573` | — |

Mosquitto do UNS: `localhost:18831`. Simulador Modbus: `localhost:55020`.
Esta frota embute `PEER_MESH_TEST=1` (liga os hooks `POST /api/system/peers/test/send`
e `GET /api/system/peers/test/inbox`).

> Ao **re‑semear**, o `sida_config.db` pode ter ficado `root:root` (bind mount de
> contêiner root). Apague antes com um contêiner descartável:
> `docker run --rm -v "$PWD/test/etapa1/_data:/d" alpine sh -c 'rm -rf /d/edge1 /d/edge2 /d/edge3'`

Derrubar: `docker compose -f test/etapa1/compose.test.yml -p sida_e1 down -v`.

### 3.3 Um nó com ingestão InterEdge (Etapa 2 — `test/etapa2/compose.test.yml`)

1 nó completo + **dois** brokers distintos (`mosquitto-uns` host `18832`,
`mqtt-ingest` host `18841`) + `plc-sim` (caminho Modbus v2.0) + `esp32-sim`
(mock de dispositivo Classe 1 publicando em `sida/ingest/esp32_a/*`).

```bash
python3 test/etapa2/seed_node_config.py --data-dir test/etapa2/_data/edge \
    --gateway-id sida_edge_e2 --broker-host mosquitto-uns --modbus-host plc-sim \
    --extra-interedge esp32_b

docker compose -f test/etapa2/compose.test.yml -p sida_e2 up -d --build
```

Portas no host: `sida-core` HTTP `localhost:18011`; UNS `localhost:18832`;
ingestão `localhost:18841`; Modbus `localhost:55021`.
O manifesto semeado tem `pump_01` (`modbus_tcp`), `esp32_a` (`interedge`,
alimentado pelo `esp32-sim`) e `esp32_b` (`interedge`, sem simulador — é a
**sonda de latência** dos testes; você publica a `telemetry` dele à mão).

Derrubar: `docker compose -f test/etapa2/compose.test.yml -p sida_e2 down -v`.

### 3.4 UNS Web Client (consumidor)

Adicionado à `sida_network` por **override**, sem tocar no `docker-compose.yml`:

```bash
BROKER_WS_URL=wss://seu-broker:9001 docker compose up -d sida-uns-client
# UI em http://localhost:8080
```

Standalone: `docker build -t sida-uns-client ./sida-uns-client && \
docker run -e BROKER_WS_URL=ws://SEU_BROKER:9001 -p 8080:80 sida-uns-client`.
Exige um listener **MQTT‑over‑WebSocket** no broker. Login = usuário/senha MQTT
(repassados direto ao broker; nada é persistido).

---

## 4. Verificação dos casos de uso

Convenções de tópico Sparkplug B (todas as etapas):
`group_id = GROUP_ID` (`Enterprise_Site`); `edge_node_id = EDGE_GATEWAY_ID`
(ex.: `sida_edge_001`); `device_id` = concatenação `Area_1_Line_1_Pump_01` do
`asset_context.path`.

### 4.0 Ferramenta: observar o UNS decodificado

`mosquitto_sub -t 'spBv1.0/#' -v` mostra o tópico, mas o *payload* é Protobuf
binário. Para ler os valores, use este observador (salve em
`/tmp/spb_watch.py`) — compila o `.proto` versionado e imprime `seq`, `bdSeq`,
`alias`, `name`, tipo e valor de cada métrica:

```python
import sys, subprocess, tempfile, importlib, pathlib
import paho.mqtt.client as mqtt

REPO = pathlib.Path(__file__).resolve().parent  # ajuste se necessário
proto = REPO / "schemas" / "sparkplug_b.proto"
out = tempfile.mkdtemp()
subprocess.run(["protoc", f"--proto_path={proto.parent}", f"--python_out={out}", proto.name], check=True)
sys.path.insert(0, out)
spb = importlib.import_module("sparkplug_b_pb2")

HOST, PORT = sys.argv[1] if len(sys.argv) > 1 else "localhost", int(sys.argv[2]) if len(sys.argv) > 2 else 18831

def on_msg(_c, _u, m):
    p = spb.Payload(); p.ParseFromString(m.payload)
    seq = p.seq if p.HasField("seq") else None
    print(f"\n{m.topic}   seq={seq}")
    for met in p.metrics:
        ident = met.name or f"alias:{met.alias}"
        val = met.WhichOneof("value")
        print(f"   {ident:<28} type={met.datatype} {val}={getattr(met, val) if val else None}"
              + (f"  engUnit={met.properties.keys}" if met.properties.keys else ""))

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message = on_msg
c.connect(HOST, PORT); c.subscribe("spBv1.0/#"); c.loop_forever()
```

```bash
python3 /tmp/spb_watch.py localhost 18831      # frota Etapa 1
python3 /tmp/spb_watch.py localhost 18832      # nó Etapa 2 (UNS)
```

---

### 4.1 Plano A — ciclo de vida Sparkplug B (Etapa 1)

Bancada: §3.2. Deixe `/tmp/spb_watch.py` rodando em `localhost 18831`.
Teste que cobre tudo abaixo: **`test/etapa1/test_plane_a_lifecycle.py`**
(`--run-heavy`).

#### Caso A1 — Ciclo de vida feliz (`NBIRTH → DBIRTH → DDATA`)
- **Pré‑condição:** frota no ar; `context` entregando `Temperature` (float, °C) e `Running` (bool) de `Area_1_Line_1_Pump_01`.
- **Passos:** só observe o `spb_watch` desde a subida do nó.
- **Esperado, nesta ordem:**
  1. `spBv1.0/Enterprise_Site/NBIRTH/sida_edge_001` — `seq=0`, métrica `bdSeq=N` (inteiro), `Node Control/Rebirth=false`.
  2. `.../DBIRTH/sida_edge_001/Area_1_Line_1_Pump_01` — `Temperature` com `alias` inteiro e `engUnit="°C"`; `Running` com `alias` distinto; **definições sem valor**.
  3. `.../DDATA/sida_edge_001/Area_1_Line_1_Pump_01` — métricas **só por `alias`** (sem `name`), `seq` incrementando 1, 2, 3…
  - Nenhum `DDATA` antes do `DBIRTH`.
- **Prova automatizada:** `test_nbirth_bdseq_e_reset`, `test_dbirth_define_aliases`, `test_ddata_por_alias`.

#### Caso A2 — Morte abrupta via LWT (`docker kill`)
- **Passos:**
  ```bash
  docker compose -f test/etapa1/compose.test.yml -p sida_e1 kill -s SIGKILL edge1-delivery
  ```
- **Esperado:** o **broker** publica `spBv1.0/Enterprise_Site/NDEATH/sida_edge_001` **automaticamente**, com `bdSeq = N` **igual** ao do último `NBIRTH`. Nenhuma ação do SIDA.
- **Prova automatizada:** `test_bdseq_sessao_no_lwt`.

#### Caso A3 — Morte graciosa (`docker stop` / SIGTERM)
- **Passos:** (religue o delivery antes, se veio do A2: `... start edge1-delivery`)
  ```bash
  docker compose -f test/etapa1/compose.test.yml -p sida_e1 stop -t 20 edge1-delivery
  ```
- **Esperado:** o nó publica um `NDEATH` **explícito** (`bdSeq = N`, `seq` = próximo) **antes** de fechar o MQTT; a desconexão é limpa, então o LWT **não** dispara — **um só** `NDEATH`, sem conflito.
- **Prova automatizada:** `test_ndeath_gracioso`.

#### Caso A4 — Rolagem de `seq` (estouro de 255)
- **Passos:** deixe o nó publicar > 256 mensagens sem reconectar (a fixture usa `scan_rate_ms=300`, ~80 s).
- **Esperado:** `seq` vai `…254, 255, 0, 1…` **contínuo**; `bdSeq` **inalterado**; **um só** `NBIRTH` em toda a janela; consumidor não interpreta como *rebirth*.
- **Prova automatizada:** `test_contabilidade_seq`.

#### Caso A5 — `bdSeq` sobrevive a `restart`/`stop` de container
- **Passos:**
  ```bash
  curl -s ... # anote o bdSeq atual no NBIRTH
  docker compose -f test/etapa1/compose.test.yml -p sida_e1 restart edge1-delivery
  ```
- **Esperado:** o novo `NBIRTH` traz `bdSeq` **estritamente maior** (lido de `/tmp/.ipc/bdseq.sida_edge_001`). Só `down -v` zera.
- **Prova automatizada:** sessão C de `test_bdseq_sessao_no_lwt`; e `religamento_bdseq_incrementado` no `report.json` da injeção de falha.

---

### 4.2 Plano B — malha *controller‑to‑controller* (Etapa 1)

Bancada: §3.2. Verificação por HTTP:
`curl -s localhost:1800X/api/system/peers | jq`. Resposta:
```json
{ "controller_id": "edge_001",
  "peers": [ { "id": "edge_002", "endpoint": "…", "state": "alive|suspect|down",
               "last_ack_ms": 123, "missed": 0 } ] }
```
Teste que cobre: **`test/etapa1/test_plane_b_peermesh.py`** e
**`test/etapa1/test_fleet.py`** (`--run-heavy`).

#### Caso B1 — Registro carrega do `.env` e persiste
- **Esperado:** cada nó lista os **outros dois** pares (de `PEERS`); o boot loga `peer register: 2 pares`; a tabela SQLite `controllers` (em `_data/edgeN/sida_config.db`) tem os pares gravados.
- **Prova:** `test_registro_carrega_de_env`, `test_persistencia_controllers`, `test_frota_3_nos`.

#### Caso B2 — Todos `alive` em regime
- **Passos:** `for p in 18001 18002 18003; do curl -s localhost:$p/api/system/peers | jq -c; done`
- **Esperado:** os 3 nós reportam os outros dois com `state="alive"` e `missed=0`.

#### Caso B3 — Troca de mensagem pela malha (primitivas InterEdge)
- **Passos:** (hooks de teste, `PEER_MESH_TEST=1`)
  ```bash
  curl -s -XPOST localhost:18001/api/system/peers/test/send \
       -H 'Content-Type: application/json' -d '{"peer":"edge_002","payload":"ola"}'
  curl -s localhost:18002/api/system/peers/test/inbox | jq
  ```
- **Esperado:** `{"sent":true}` no envio; `{"messages":["ola"]}` na `inbox` do `edge_002` (roteamento `WriteMessage`/`RouteMessage`/`ReadMessage`, `MessageBuffer` por remetente).
- **Prova:** `test_troca_mensagem_mesh`.

#### Caso B4 — Detecção de queda de par (FSM local)
- **Passos:**
  ```bash
  docker compose -f test/etapa1/compose.test.yml -p sida_e1 stop edge2-core
  ```
- **Esperado:** em ≤ `PROBE_INTERVAL_MS × PEER_DOWN_AFTER_MISSES` (~3 s), `edge_001` **e** `edge_003` passam a reportar `edge_002` com `state="down"` (via `suspect`). `edge_001`/`edge_003` **seguem publicando `DDATA`** sem interrupção. Medição local, relógio monotônico — **sem consenso**.
- **Prova:** `test_probe_e_liveness`; `test_deteccao_dois_planos`.

#### Caso B5 — Religamento de par (*flap* + histerese)
- **Passos:** `... stop edge2-core` e, ~5 s depois, `... start edge2-core`.
- **Esperado:** `edge_002` vai a `down` e, ao primeiro `PROBE_ACK`, volta a `alive`; a histerese (`suspect` + `PEER_DOWN_AFTER_MISSES`) evita oscilação; nenhum estado de par corrompido.
- **Prova:** `test_flap_religamento`.

#### Caso B6 — Partição parcial (visão local diverge — e está certo)
- **Passos:** bloqueie só `edge_001 ↔ edge_003` (o teste usa `iptables -I ... DROP` no *netns* de cada contêiner).
- **Esperado:** `edge_001` vê `edge_003=down` e `edge_002=alive`; `edge_003` vê o simétrico; `edge_002` vê **ambos `alive`**. Nenhuma tentativa de eleição/quórum.
- **Prova:** `test_particao_parcial`.

#### Caso B7 — Broker de nuvem cai, malha sobrevive
- **Passos:** torne o `BROKER_URL` inacessível (ex.: `... stop mosquitto`) por ~30 s, **sem** derrubar nenhum nó.
- **Esperado:** `GET /api/system/peers` continua reportando todos `alive` (os *probes* ZeroMQ não passam pelo broker). Ao voltar o broker, cada nó reconecta e emite **novo `NBIRTH` com `bdSeq` incrementado**.
- **Prova:** coberto pela lógica de `test_probe_e_liveness` + caso A5 (SDD Etapa 1 §5.4 caso 5).

#### Caso B8 — Colisão de identidade (erro de `.env`)
- **Passos:** suba dois nós com o mesmo `CONTROLLER_ID`.
- **Esperado:** o `peer_service` detecta o ID duplicado no *handshake*, recusa o par e loga (rate‑limited); condição **visível em log**, não *flap* silencioso.
- **Prova:** `test_colisao_identidade`.

#### Caso B9 — Encerramento limpo da malha
- **Passos:** `docker compose ... stop edge1-core` e veja `docker compose ... logs edge1-core`.
- **Esperado:** `peer-mesh encerrada` → `SIDA-Core encerrado` em poucos segundos (teto de 3 s no `Stop()`).
- **Prova:** `test_wiring_e_shutdown`.

---

### 4.3 Injeção de falha — eliminação do SPOF de borda (aceite Etapa 1 §3.1)

É o **teste de aceite final** da Etapa 1: derrubar um nó e comprovar que os
sobreviventes seguem publicando **nos dois planos, sem perda**.

**Automatizado (recomendado):**
```bash
pytest test/etapa1/test_fault_injection.py --run-heavy
cat test/etapa1/report.json
```
`report.json` deve trazer: `t_ndeath_s` (~0,1 s), `t_peer_detect_s` por nó
observador (~4–5 s com `probe=1000ms`/`misses=3`),
`perdas_ddata_sobreviventes` **= 0** em cada sobrevivente,
`religamento_bdseq_incrementado: true`, *overhead* CPU/RAM por contêiner
(`sida-core` ~6 MiB, < 0,2 % CPU), e **`aceite: true`**.

**Manual (os 7 passos do §3.1):**
```bash
# t0 — frota íntegra
python3 /tmp/spb_watch.py localhost 18831 &     # NBIRTH+bdSeq / DBIRTH+alias / DDATA por alias dos 3 nós
for p in 18001 18002 18003; do curl -s localhost:$p/api/system/peers | jq -c; done   # todos alive

# t1 — injeção de falha em edge_002 (core + delivery, ou o nó inteiro)
docker compose -f test/etapa1/compose.test.yml -p sida_e1 stop \
  edge2-core edge2-ingestion edge2-context edge2-delivery

# passo 3 (plano A): o broker publica NDEATH/sida_edge_002 com o bdSeq do último NBIRTH
# passo 4 (plano B): edge_001 e edge_003 marcam edge_002 = down em ~3 s
watch -n1 'curl -s localhost:18001/api/system/peers | jq -c ".peers[] | select(.id==\"edge_002\")"'

# passo 5: edge_001 e edge_003 seguem publicando DDATA — sem lacuna, sem rebirth espúrio

# t2 — religamento
docker compose -f test/etapa1/compose.test.yml -p sida_e1 start \
  edge2-core edge2-ingestion edge2-context edge2-delivery
#   → NBIRTH de sida_edge_002 com bdSeq incrementado; edge_001/edge_003 voltam a vê-lo alive
```

---

### 4.4 Ingestão Classe 0/1 sem CLP — `interedge` (Etapa 2)

Bancada: §3.3. Dois observadores úteis:
```bash
mosquitto_sub -h localhost -p 18841 -t 'sida/ingest/#' -v      # ingestão (JSON legível)
python3 /tmp/spb_watch.py localhost 18832                       # UNS decodificado
```
Testes que cobrem: **`test/etapa2/test_s5_interedge_contract.py`**,
**`test/etapa2/test_s6_interedge_adapter.py`**,
**`test/etapa2/test_s7_e2e_interedge.py`** (`--run-heavy`).

#### Caso D1 — Contrato `interedge` aceito no manifesto; validações de *polling* afrouxadas
- **Passos:** `POST /api/config/manifest` (autenticado — token abaixo) com um device `interedge` **sem** `host`/`port`/`scan_rate_ms`/`register_type`:
  ```bash
  TOKEN="session_$(printf '000000' | sha256sum | cut -d' ' -f1)"
  curl -s -o /dev/null -w '%{http_code}\n' -XPOST localhost:18011/api/config/manifest \
       -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
       -d @deploy/fleet/manifest.interedge.example.json
  ```
- **Esperado:** `200` (`{"status":"success",...}`). Um device `interedge` **sem `asset_context`** → `400`. Um `modbus_tcp` **sem `host`** → `400` (não‑regressão das validações existentes).
- **Nota:** o `UploadManifest` grava o manifesto sob o `gateway_id` **do corpo**; para que o nó `sida_edge_e2` realmente o adote, o campo `gateway_id` do JSON deve ser `sida_edge_e2` (o exemplo traz `sida_edge_001` — troque, ou use só para checar o *status code* da validação).
- **Prova:** `test_manifesto_interedge_aceito` (+ `go test ./internal/core/domain/...`).

#### Caso D2 — Broker de ingestão dedicado e isolado do UNS
- **Passos:** publique em `mqtt-ingest` (`18841`) e observe o UNS (`18832`).
  ```bash
  mosquitto_pub -h localhost -p 18841 -t sida/ingest/probe/telemetry \
       -m '{"device_id":"probe","readings":{"x":1}}'
  ```
- **Esperado:** o `mqtt-ingest` entrega pub/sub; **nada** de `sida/ingest/#` aparece no UNS. Portas host distintas (`18841` ≠ `18832`).
- **Prova:** `test_broker_ingestao_isolado`.

#### Caso D3 — Ingestão feliz sem CLP (ponta a ponta)
- **Pré‑condição:** `esp32-sim` publicando `sida/ingest/esp32_a/telemetry` a cada 1 s; `esp32_a` no manifesto (`asset_context` até `ESP32_A`; `metrics_mapping`: `temperature` float °C, `running` bool).
- **Esperado no UNS:** `DBIRTH .../Area_1_Line_1_ESP32_A` com `Temperature` (`alias` + `engUnit="°C"`) e `Running` (`alias` distinto) → `DDATA` por `alias`, `seq` contínuo. Valores de `DDATA` ≈ os publicados no `mqtt-ingest` (dentro da escala). O payload interno carregou `source.source_protocol = "interedge"`.
- **Prova:** `test_pipeline_interedge_ponta_a_ponta`, `test_adapter_normaliza_e_injeta`, `test_mqtt_in_recebe_do_simulador`.

#### Caso D4 — Convivência com Modbus (não‑regressão)
- **Esperado:** `pump_01` (`modbus_tcp`) e `esp32_a` (`interedge`) publicam `DDATA` no UNS **em paralelo e continuamente**, em tópicos distintos, sem lacuna em `pump_01` atribuível ao adaptador.
- **Prova:** `test_report_e_aceite` (`nao_regressao_modbus: true`) + `pytest test/etapa1/test_s1_foundation.py::test_baseline_v2_pipeline --run-heavy` verde.

#### Caso D5 — Mensagem malformada é descartada sem derrubar o fluxo
- **Passos:**
  ```bash
  mosquitto_pub -h localhost -p 18841 -t sida/ingest/esp32_b/telemetry -m 'nao-e-json'
  mosquitto_pub -h localhost -p 18841 -t sida/ingest/esp32_b/telemetry -m '{"readings":{"temperature":1}}'   # sem device_id
  docker compose -f test/etapa2/compose.test.yml -p sida_e2 logs edge-ingestion | grep '\[interedge\] descartado'
  ```
- **Esperado:** cada malformada gera `node.warn("[interedge] descartado: …")` e **nenhuma** injeção no IPC; o fluxo **não** cai; a próxima mensagem válida passa normalmente.
- **Prova:** SDD Etapa 2 §5.5 caso 3 (coberto em `test_s6`/`test_s7`).

#### Caso D6 — `device_id` fora do manifesto
- **Passos:**
  ```bash
  mosquitto_pub -h localhost -p 18841 -t sida/ingest/esp32_ghost/telemetry \
       -m '{"device_id":"esp32_ghost","readings":{"temperature":25}}'
  ```
- **Esperado:** log `[interedge] descartado: device_id 'esp32_ghost' ausente no manifesto`; **nenhum** `DBIRTH`/`DDATA` de `esp32_ghost` no UNS.
- **Prova:** SDD Etapa 2 §5.5 caso 5.

#### Caso D7 — Dispositivo provisionado sem simulador + manifesto em *runtime*
- **Pré‑condição:** o `seed` de §3.3 já inclui `esp32_b` no manifesto (`--extra-interedge esp32_b`), **sem** contêiner simulador.
- **Passos:** publique a `telemetry` de `esp32_b` à mão:
  ```bash
  mosquitto_pub -h localhost -p 18841 -t sida/ingest/esp32_b/telemetry \
       -m '{"device_id":"esp32_b","ts":0,"readings":{"temperature":25.4,"running":true}}'
  ```
- **Esperado:** `esp32_b` é contextualizado e publica `DBIRTH`/`DDATA` no UNS (`Area_1_Line_1_ESP32_B`), **sem reiniciar o nó** — é a sonda de latência do `report.json`.
- **Variante "manifesto em runtime" (SDD §5.5 caso 6):** com o nó no ar, `POST /api/config/manifest` (token do §6.2) com o corpo trazendo `gateway_id: "sida_edge_e2"` e a planta acrescida de um device novo. O `ingestion`/`context` recebem o `ManifestUpdate` por `sida/manifest` (ZeroMQ), atualizam o `deviceCache` e passam a contextualizar o device novo — sem *restart*.
- **Prova:** `test_isa95_mapeia_dispositivo_sem_clp`, `test_report_e_aceite`.

#### Caso D8 — Rótulo de origem preservado + nível organizacional ISA‑95
- **Esperado:** o `report.json` registra `source_protocol_observado` por device
  (`Area_1_Line_1_ESP32_B → interedge`, `Area_1_Line_1_Pump_01 → modbus_tcp`),
  `isa95_ok: true`, `perda: 0`, latência sensor→UNS p50/p95 (ordem de ms) e
  **`aceite: true`**. É a prova do **nível organizacional do InterEdge** para uma
  fonte **sem CLP na origem**: o mesmo `DBIRTH`/`DDATA` contextualizado que um
  device com CLP.
- **Prova:** `pytest test/etapa2/test_s7_e2e_interedge.py --run-heavy && cat test/etapa2/report.json`.

#### Caso D9 — Firmware ESP32 real (`T2.1` — bancada, fora do loop)
- Encadeamento `sensor Classe 0 → (UART) → ESP32 Classe 1 → Wi‑Fi/MQTT → mqtt-ingest`; o `device_id` publicado é o do **ESP32**. Checklist de validação e registro em [`deploy/interedge-device/README.md`](deploy/interedge-device/README.md). Os checkpoints S5–S7 usam o `esp32_sim.py` como *stand‑in*.

---

### 4.5 UNS Web Client (Etapa consumidor)

Bancada containerizada e isolada (Mosquitto WS+TCP + a imagem real + um runner
Playwright que publica `NBIRTH → DBIRTH → DDATA → DDATA → NDEATH`):

```bash
./sida-uns-client/test/run.sh        # exit code 0 = todos os passos passaram
```

Casos verificados (SDD UNS Web Client §5.3):

| Caso | Entrada | Esperado |
|---|---|---|
| E1 — Fluxo feliz | login válido → `NBIRTH` → `DBIRTH`(`Temperature` 60.5 °C) → `DDATA`(61.2) | árvore `Line_1 > Pump_01`; gráfico com 2 pontos; unidade `°C` exibida |
| E2 — Credenciais inválidas | senha errada | `auth_status=credenciais_invalidas`; **nenhuma** subscrição; árvore vazia |
| E3 — `DDATA` sem `NBIRTH` | `DDATA` com alias não resolvido | mensagem descartada com log; sem ponto novo; sem exceção |
| E4 — Queda e reconexão WS | conexão cai, broker volta em ~5 s | banner "reconectando"; ressubscrição automática em `spBv1.0/#`; `node_liveness` não é resetado para offline só pela perda de conexão |
| E5 — Payload corrompido | binário não‑Protobuf em `spBv1.0/...` | descartado sem *crash*, log no console; resto segue |
| E6 — `NDEATH` + novo `NBIRTH` | nó morre e religa | volta a `online`; `alias_table` reconstruída; **histórico do gráfico não é zerado** |

Verificação manual: `docker compose up -d sida-uns-client`, abra
`http://localhost:8080`, faça login com as credenciais do seu broker e publique
uma sequência Sparkplug B (ou aponte para o UNS de uma frota de §3.2/§3.3 com
listener WS).

---

## 5. Suíte automatizada — mapa completo

```bash
python3 -m pip install -r test/etapa1/requirements.txt      # cobre Etapa 1 e Etapa 2
# se 'externally-managed-environment': acrescente --user --break-system-packages

# --- leves (sem containers) ---
pytest test/etapa1
pytest test/etapa2

# --- pesados: sobem containers. Rode UM arquivo por vez (nomes de container fixos) ---
pytest test/etapa1/test_s1_foundation.py       --run-heavy   # T0.4 / T1A.1 / T3.1  (baseline v2.0, .proto, compose .env)
pytest test/etapa1/test_plane_a_lifecycle.py   --run-heavy   # T1A.2–T1A.7          (ciclo de vida Sparkplug B)
pytest test/etapa1/test_plane_b_peermesh.py    --run-heavy   # T1B.1–T1B.5 + casos 6/7/9
pytest test/etapa1/test_fleet.py               --run-heavy   # T3.2 / T3.3          (frota de 3 nós, isolamento)
pytest test/etapa1/test_fault_injection.py     --run-heavy   # T4.3–T4.6            (aceite §3.1 → report.json)

pytest test/etapa2/test_s5_interedge_contract.py --run-heavy # T2.4 / T2.2a / T2.SIM
pytest test/etapa2/test_s6_interedge_adapter.py  --run-heavy # T2.2b / T2.3
pytest test/etapa2/test_s7_e2e_interedge.py      --run-heavy # T2.5 / T2.6 / T2.RPT (→ report.json)

./sida-uns-client/test/run.sh                                # UNS Web Client (SDD 3.1) — Docker only
```

| Sprint | Tasks | Arquivo de teste |
|---|---|---|
| E1·S1 | `T0.4`, `T1A.1`, `T3.1` | `test/etapa1/test_s1_foundation.py` |
| E1·S2 | `T1A.2`…`T1A.7` | `test/etapa1/test_plane_a_lifecycle.py` |
| E1·S3 | `T1B.1`…`T1B.5` | `test/etapa1/test_plane_b_peermesh.py` |
| E1·S4 | `T3.2`, `T3.3`, `T4.1`…`T4.6` | `test/etapa1/test_fleet.py`, `test/etapa1/test_fault_injection.py` |
| E2·S5 | `T2.4`, `T2.2a`, `T2.SIM` | `test/etapa2/test_s5_interedge_contract.py` |
| E2·S6 | `T2.2b`, `T2.3` | `test/etapa2/test_s6_interedge_adapter.py` |
| E2·S7 | `T2.5`, `T2.6`, `T2.RPT` | `test/etapa2/test_s7_e2e_interedge.py` |
| E2·T2.1 | firmware ESP32 | manual — `deploy/interedge-device/README.md` |

O avanço por task está em [`progress.json`](progress.json) (mesma lista para as
duas etapas). Cada teste pula com mensagem acionável se faltar ferramenta
(nunca falha por ambiente).

---

## 6. Referência rápida

### 6.1 Portas

| Serviço | Produção (`docker-compose.yml`) | Frota E1 (`test/etapa1`) | Nó E2 (`test/etapa2`) |
|---|---|---|---|
| `sida-core` HTTP | `8000` | `18001` / `18002` / `18003` | `18011` |
| peer‑mesh ZeroMQ | `${PEER_PORT:-5557}` | `15571` / `15572` / `15573` | — |
| PUB manifesto ZeroMQ | `5556` (interno) | `15561` (só edge_001) | `15511` |
| Broker UNS (MQTT) | — (externo, `BROKER_URL`) | `18831` | `18832` |
| Broker ingestão `mqtt-ingest` | local ao RPi | — | `18841` |
| Simulador Modbus | `5020` (profile `sim`) | `55020` | `55021` |
| Node‑RED editores | `1881`/`1882`/`1883` | — | — |
| UNS Web Client | `8080` | — | — |
| Neo4j | `7474` / `7687` | — | — |

### 6.2 Endpoints `sida-core`

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/api/health` | `{"status":"UP",...}` |
| `GET` | `/api/system/info` | `{"provisioned":bool,"gateway_id":"…"}` |
| `POST` | `/api/system/setup` | grava `EDGE_GATEWAY_ID`/`PIN` em `/app/data/.env` |
| `GET` | `/api/system/peers` | registro + *liveness* local (plano B) |
| `POST` | `/api/system/peers/test/send` | injeta `Envelope` na malha — **só** com `PEER_MESH_TEST=1` |
| `GET` | `/api/system/peers/test/inbox` | drena o `MessageBuffer` — **só** com `PEER_MESH_TEST=1` |
| `GET` | `/api/config/manifest` | manifesto atual |
| `POST` | `/api/config/manifest` | novo manifesto — header `Authorization: Bearer session_<sha256hex(PIN)>` |
| `POST` | `/api/buffer/` · `GET /api/buffer/flush` | esboço de *store‑and‑forward* (**fora do escopo V3**) |

Token para PIN `000000`:
`TOKEN="session_$(printf '000000' | sha256sum | cut -d' ' -f1)"`.

### 6.3 Tópicos MQTT

| Plano | Tópico | Retido | Payload |
|---|---|---|---|
| UNS (norte) | `spBv1.0/{GROUP_ID}/NBIRTH/{EDGE_GATEWAY_ID}` | não | Sparkplug B — `seq=0`, métrica `bdSeq` |
| UNS | `spBv1.0/{GROUP_ID}/DBIRTH/{EDGE_GATEWAY_ID}/{device_id}` | não | definições de métrica com `alias` + `properties.engUnit` |
| UNS | `spBv1.0/{GROUP_ID}/DDATA/{EDGE_GATEWAY_ID}/{device_id}` | não | valores **por `alias`**, `seq` rolando mod 256 |
| UNS | `spBv1.0/{GROUP_ID}/NDEATH/{EDGE_GATEWAY_ID}` | não | `bdSeq` da sessão — via LWT (abrupto) ou explícito (gracioso) |
| Ingestão (E2) | `sida/ingest/{device_id}/profile` | **sim** | *device profile* InterEdge (informativo) |
| Ingestão (E2) | `sida/ingest/{device_id}/telemetry` | não (`qos 0`) | `{ "device_id", "ts", "readings": { … } }` |
| Interno | `sida/manifest` (ZeroMQ PUB `:5556`) | — | `ManifestUpdate` para `ingestion`/`context`/`ontology-builder` |

`device_id` no UNS = `path` do `asset_context` concatenado
(`Area_1` + `Line_1` + `ESP32_A` → `Area_1_Line_1_ESP32_A`).
As chaves de `readings` (E2) e do `metrics_mapping` são os **nomes lógicos**
(`temperature`, `running`) — no Modbus são os registradores (`40001`, `40002`).

### 6.4 Variáveis de ambiente do nó (só do `.env` — nada hardcoded)

| Variável | Plano | Exemplo |
|---|---|---|
| `EDGE_GATEWAY_ID` | A — `edge_node_id` Sparkplug (clientId MQTT) | `sida_edge_001` |
| `GROUP_ID` | A — `{Enterprise}_{Site}` | `Enterprise_Site` |
| `BROKER_URL` | A — broker do UNS | `mqtt://mosquitto:1883` |
| `EDGE_ENGINEER_PIN` | auth do `sida-core` | `000000` (descartável) |
| `CONTROLLER_ID` | B — identidade na malha | `edge_001` |
| `PEER_PORT` | B — porta ROUTER/DEALER (**nunca** 5556) | `5557` |
| `PEERS` | B — `id@host:port,…` | `edge_002@edge2-core:5557,edge_003@edge3-core:5557` |
| `PROBE_INTERVAL_MS` / `PEER_DOWN_AFTER_MISSES` | B — cadência do probe / misses até `down` | `1000` / `3` |
| `INGEST_BROKER_HOST` / `INGEST_BROKER_PORT` | D (E2) | `mqtt-ingest` / `1883` |
| `INGEST_TOPIC_ROOT` / `INGEST_TOPIC_FILTER` | D (E2) — o filtro **já com o curinga** | `sida/ingest` / `sida/ingest/+/telemetry` |
| `BROKER_WS_URL` | E — listener WebSocket p/ o UNS Web Client | `wss://broker:9001` |

---

## 7. Troubleshooting (armadilhas conhecidas)

- **`docker ps` → permission denied:** `sudo setfacl -m u:jackson:rw /var/run/docker.sock` (repetir se o socket for recriado).
- **Re‑semear a frota falha com "readonly database":** o `sida_config.db` ficou `root:root` no bind mount. Apague via contêiner: `docker run --rm -v "$PWD/test/etapa1/_data:/d" alpine sh -c 'rm -rf /d/edge1 /d/edge2 /d/edge3'`.
- **`interedge`: `mqtt in` nunca casa o tópico:** o Node‑RED só substitui `${VAR}` quando é o **valor inteiro** da propriedade. Por isso o filtro é a env `INGEST_TOPIC_FILTER=sida/ingest/+/telemetry` (curinga embutido), não `${INGEST_TOPIC_ROOT}/+/telemetry`.
- **"*Rebirth*" nos testes = `docker restart` do `delivery`**, não *bounce* do broker. Ao derrubar o `mosquitto-uns`, o cliente MQTT do `delivery` (`reconnectPeriod:0` + reconexão manual) fica preso desconectado; só um `delivery` novo re‑emite `NBIRTH`+`DBIRTH`. Não há listener de `NCMD`/`Rebirth`.
- **`bdSeq` não incrementa no `restart`:** confirme que o volume `sida_ipc` (`/tmp/.ipc`) está montado no `delivery`. O contador vive em `/tmp/.ipc/bdseq.<gateway_id>` e só zera no `down -v`.
- **Simulador Modbus (`oitc/modbus-server`, `zero_mode=False`):** a chave `N` do `holdingRegister` é servida no fio `N-1`. O flow lê `40001`→fio 0 e `40002`→fio 1; por isso as chaves em `test/etapa1/modbus.test.json` são `"1"` e `"2"` (`235` → 23,5 °C com `scale_factor 0.1`; `1` → `Running=true`).
- **`test_baseline_v2_pipeline` polui `core/ingestion/.config.nodes.json.backup`** (tracked): `git checkout -- core/ingestion/.config.nodes.json.backup` antes de commitar.
- **`protobuf` ausente:** `pip install --user --break-system-packages protobuf` (necessário para o `spb_watch.py` e para os testes do plano A / E2).
- **`test_baseline_v2_pipeline` pesado leva ~3 min:** normal (build Go + Node‑RED + pipeline Modbus completo até o broker).
- **Não rode duas frotas pesadas ao mesmo tempo:** os nomes de contêiner são fixos (`e1-…`, `e2-…`) — um arquivo de teste pesado por vez, e não deixe uma frota manual (`-p sida_e1`) de pé enquanto o pytest sobe a dele.
