# SDD — SIDA Etapa 2 do Ciclo V3.0
### Ingestão de dispositivos de recursos restritos (Classe 0/1) sem CLP, no estilo dos perfis InterEdge — o dispositivo como "mais uma fonte de protocolo"

---

## 0. Contexto herdado (não é parte do loop, apenas referência)

Este SDD descreve a **Etapa 2 do Ciclo V3.0** do SIDA: **ampliar a camada de ingestão** para **dispositivos de recursos restritos** — **Classe 0** (ex.: Arduino Uno R3, sem rede) e **Classe 1** (ex.: ESP32, com Wi-Fi/BT) — em contextos industriais **sem CLP**. O dispositivo é tratado como **mais uma fonte de protocolo**: publica leituras por um transporte leve até o RPi, um **adaptador** novo na camada de ingestão normaliza a saída para o **payload interno do SIDA**, e o pipeline homologado (`context` ISA-95 → `delivery` Sparkplug B → UNS) segue **sem alteração**. A contribuição conceitual da etapa é provar o **nível organizacional do InterEdge** (mapeamento ISA-95) para uma fonte **sem CLP na origem**.

A **Etapa 1** (já concluída na branch `interedge` — 22 tasks, S1..S4, teste de aceite `test_fault_injection.py` verde) entregou a **frota descentralizada** e os **dois planos de coordenação**:

| Plano | Mecanismo | Transporte | Onde vive | Papel |
|---|---|---|---|---|
| **Norte** (borda → nuvem) | **A** — ciclo de vida Sparkplug B (`NBIRTH`/`DBIRTH`/`DDATA`/`NDEATH` + LWT) | MQTT → broker do UNS | camada **delivery** (`core/delivery/flows.json`, Node-RED) | autodescrição e observabilidade da frota |
| **Leste-oeste** (borda ↔ borda) | **B** — *controller-to-controller* do InterEdge (registro de pares, *probes*, roteamento) | ZeroMQ entre os `sida-core` (porta `PEER_PORT`, default `5557`) | **`sida-core`** (Go) | detecção **local** de queda de par |

**A Etapa 2 não toca nos planos A e B.** O trabalho é **exclusivamente** na **entrada** do pipeline (`core/ingestion/flows.json` + o modelo `Connection` em `sida-core`), mais um **transporte de ingestão** dedicado e um **simulador de dispositivo** para os checkpoints automatizados. O caminho Modbus TCP da v2.0 continua funcionando **em paralelo**, no mesmo nó.

### 0.1 Estado atual do código (levantado por inspeção — ponto de partida real)

- **Caminho de ingestão da v2.0 (Modbus) JÁ ESTÁ IMPLEMENTADO** em `core/ingestion/flows.json`. Verificado por inspeção:

  | Elemento | Estado hoje | Onde |
  |---|---|---|
  | Polling Modbus | ✅ `modbusPolling` (setInterval no `scan_rate_ms`) — lê holding/input registers via `modbus-serial` (`ModbusRTU`) e emite o payload interno | `core/ingestion/flows.json`, função `modbusPolling` |
  | Polling OPC UA | ✅ `opcuaPolling` — leitura em *bulk*, mesmo payload de saída | função `opcuaPolling` |
  | Setup de clientes | ✅ `setupClient` — percorre `manifest.config.plant.areas…devices`, abre um cliente por `dev.connection.protocol` (`modbus_tcp` / `opc_ua`) | função `setupClient` |
  | Payload interno emitido | ✅ `{ timestamp, gateway_id, source: { device_id, source_protocol }, data: { <metricKey>: <valor|[..]> } }` | fim de `modbusPolling`/`opcuaPolling` |
  | Saída para o `context` | ✅ `zeromq out` **Push** em `ipc:///tmp/.ipc/ingestion.ipc` | nó `ZQM Output` |
  | Manifesto | ✅ `getEdgeConfig` (`GET http://sida-core:8000/api/system/info`) + `getEdgeManifest` (HTTP) + `zeromq in` `ManifestUpdate` (`tcp://sida-core:5556`, tópico `sida/manifest`) | fluxo `Controller` |

- **O `context` NÃO precisa de alteração.** `contextualizeData` toma `payloadIn.source.device_id`, procura o device no `manifest.config.plant…devices[device_id]`, e monta o `asset_context` ISA-95 **a partir do manifesto** (`foundDevice.asset_context.path`), não do payload. Ou seja, o adaptador da Etapa 2 só precisa produzir o **payload interno base** (`timestamp`, `gateway_id`, `source.device_id`, `source.source_protocol`, `data`) — desde que o device esteja no manifesto com um `asset_context`.

- **`sida-core/internal/core/domain/manifest.go` — o modelo `Connection` hoje:**
  ```go
  Protocol   string `binding:"required,oneof=modbus_tcp modbus_rtu opc_ua s7"`
  ScanRateMs int    `binding:"required,min=50"`
  Host       string `binding:"required_unless=Protocol opc_ua,omitempty,ip|hostname"`
  Port       int    `binding:"required_unless=Protocol opc_ua,omitempty,min=1,max=65535"`
  ```
  e `Device` exige `AssetContext` (`binding:"required"`) e `MetricsMapping` (`binding:"required,dive"`); `MetricMapping.RegisterType` é `omitempty,oneof=holding input coil discrete`. Falta: aceitar `interedge` como protocolo e afrouxar as validações de *host/port/scan_rate/register_type* que não fazem sentido para um dispositivo **que empurra dados** (não é sondado).

- **Não existe transporte de ingestão local.** `test/etapa1/compose.test.yml` tem um Mosquitto isolado só para o **UNS de saída** (`spBv1.0/#`, host `18831`). A Etapa 2 adiciona um **broker de ingestão dedicado** (`mqtt-ingest`), sem relação com o UNS.

- **Não existe simulador de dispositivo Classe 0/1.** A Etapa 1 usou `oitc/modbus-server` (imagem pública) como *stand-in* do CLP; a Etapa 2 precisa de um **mock de ESP32** análogo (publica um *device profile* + leituras periódicas no broker de ingestão).

- **Infra de teste reusável (da Etapa 1):** `test/etapa1/conftest.py` (fixtures `require_compose`, `require_paho`, `spb_pb2`, `PlaneANode`/`FullFleet`, `reset_fleet_data`), `seed_node_config.py` (semeia `edge_manifests` no `sida_config.db`), `compose.test.yml`, `infra/Dockerfile` (Node-RED com `PROJECT_DIR`, `functionExternalModules: true`).

O loop **expande a entrada** — não reescreve `modbusPolling`/`opcuaPolling`, não toca em `core/context/flows.json` nem em `core/delivery/flows.json`, e não mexe nos planos A/B do `sida-core`.

---

## 1. OBJETIVO DO LOOP

**Frase de missão (colável em prompt de implementação):**

> Ampliar a **camada de ingestão** do SIDA para aceitar **dispositivos de recursos restritos Classe 0/1 sem CLP** como fonte, **tratando-os como mais um protocolo**: (1) estender o modelo `Connection` em `sida-core` para aceitar `protocol: "interedge"`, afrouxando as validações de *polling* (host/port/scan_rate/register_type) que não se aplicam a um dispositivo que **empurra** dados; (2) adicionar um **broker de ingestão dedicado** (`mqtt-ingest`) — **distinto** do broker do UNS de saída — por onde o dispositivo (ou o mock de ESP32) publica um *device profile* InterEdge e leituras periódicas; (3) adicionar um **sub-fluxo adaptador** em `core/ingestion/flows.json` que assina o tópico de ingestão, **normaliza** a mensagem do perfil para o **payload interno do SIDA** (`timestamp`, `gateway_id`, `source.device_id`, `source.source_protocol = "interedge"`, `data`) e a injeta no `zeromq out` `ipc:///tmp/.ipc/ingestion.ipc` — **sem tocar** no ramo Modbus/OPC UA existente; (4) mapear o dispositivo na **hierarquia ISA-95** via manifesto (`asset_context`), provando o **nível organizacional** para uma fonte sem CLP. Provar ponta a ponta que a leitura do sensor simulado chega ao UNS como `DDATA` no tópico Sparkplug correto, contextualizada por ISA-95, **enquanto o caminho Modbus da v2.0 segue publicando em paralelo, sem regressão**. O firmware C/C++ real do ESP32 (device/network profile, encadeamento Classe 0 → ESP32 → RPi) é **entregável de hardware**, validado em bancada e documentado — os checkpoints automatizados usam o **mock**.

**Resultado concreto esperado:**
- `sida-core/internal/core/domain/manifest.go` com `interedge` no enum `Connection.Protocol` e as validações de *polling* condicionadas ao protocolo (dispositivo `interedge` **não** exige `host`/`port`/`scan_rate_ms`/`register_type`).
- Um serviço `mqtt-ingest` (Mosquitto) na `docker-compose.yml` e na `test/etapa2/compose.test.yml`, com tópico-raiz `sida/ingest/#` — **sem** relação com `spBv1.0/#` (UNS).
- `core/ingestion/flows.json` com um **sub-fluxo adaptador** novo (`mqtt in` `sida/ingest/#` → `interedgeAdapter` → `zeromq out`), **paralelo** ao ramo `modbusPolling`/`opcuaPolling` — que continua intacto.
- Um **simulador de dispositivo Classe 1** (`test/etapa2/esp32_sim.py` ou imagem) que publica *device profile* + leituras no broker de ingestão.
- Um manifesto de exemplo com um device `interedge` mapeado em ISA-95 (`deploy/fleet/manifest.interedge.example.json` + suporte no `seed_node_config.py`).
- Um pacote de testes em `test/etapa2/` que sobe um nó completo + `mqtt-ingest` + o simulador, verifica o pipeline `interedge → adapter → context → delivery → UNS`, confirma a **não-regressão do Modbus**, e emite `test/etapa2/report.json` (latência sensor→UNS, taxa de mensagens, verificação do mapeamento ISA-95, *overhead* CPU/RAM do broker de ingestão + `ingestion`).
- `deploy/interedge-device/` — firmware ESP32 (C/C++) com device/network profile InterEdge + README de bancada (encadeamento Classe 0 → ESP32 → RPi). **Entregável de hardware**, fora do checkpoint automatizado.
- `progress.json` (o **mesmo arquivo** da Etapa 1, na raiz, versionado) estendido com as tasks da Etapa 2 — com **um commit `[T…]` na branch `interedge` por task concluída** (seção 3.3.1).

---

## 2. FRONTEIRAS (O QUE NÃO FAZER)

A IA que executar este loop **não pode, em hipótese alguma**:

1. **Alterar o caminho de dados homologado.** `core/context/flows.json` e `core/delivery/flows.json` **não são tocados**. Em `core/ingestion/flows.json`, o adaptador é **adição** (novo sub-fluxo em paralelo) — **não** reescrever `modbusPolling`, `opcuaPolling`, `setupClient` nem o nó `ZQM Output`. O payload interno que o adaptador injeta tem **exatamente** o mesmo shape que o `modbusPolling` já emite (`{ timestamp, gateway_id, source: { device_id, source_protocol }, data }`).
2. **Confundir o broker/tópico de ingestão com o broker do UNS.** O transporte dispositivo→RPi é um broker **dedicado** (`mqtt-ingest`, tópico-raiz `sida/ingest/#`). O UNS de saída continua `spBv1.0/#` no broker de produção (ou no Mosquitto isolado de teste). Nunca publicar leitura de dispositivo em `spBv1.0/#`; nunca o adaptador assina `spBv1.0/#`.
3. **Mexer nos planos A e B da Etapa 1.** O ciclo de vida Sparkplug B (`delivery`) e a malha *controller-to-controller* (`sida-core`, `peer_service.go`, `:5557`, `/api/system/peers`, tabela `controllers`) **não são alterados**. A Etapa 2 é ortogonal.
4. **Dar controle/atuação ao dispositivo de campo.** O papel do Classe 0/1 é **exclusivamente sensoriamento**. Nenhum comando, escrita de registrador, `DCMD`/`NCMD` ou caminho reverso ao dispositivo.
5. **Reimplementar as 5 camadas do InterEdge** (physical/profile/register/service/control) no RPi ou no ESP32 como framework paralelo ao SIDA. Do lado do dispositivo, implementa-se um *device profile* + *network profile* **mínimos** (identidade, unidades, cadência, transporte); do lado do middleware, apenas o **adaptador de normalização**. O enquadramento InterEdge × SIDA é **mapeamento arquitetural**.
6. **Adicionar TLS/mTLS** ao broker de ingestão, ao MQTT, ao IPC ZeroMQ ou à malha de pares; **trocar o PIN** por OAuth2/JWT. Segurança criptográfica é trabalho futuro declarado — o broker de ingestão de teste é **anônimo e local**.
7. **Persistir/bufferizar leituras de dispositivo.** O adaptador é *stateless* (normaliza e encaminha). Sem *store-and-forward*, sem fila em disco. Se o `mqtt-ingest` ou o `ingestion` cair, a leitura daquele período pode ser perdida — a Etapa 2 mede **continuidade e contextualização**, não recuperação.
8. **Enriquecer o `asset_context` no adaptador.** O `asset_context` ISA-95 vem **do manifesto** (o `context` já resolve pelo `device_id`). O adaptador **não** inventa `path` ISA-95 nem `enterprise`/`site`. Se o device `interedge` não está no manifesto, a leitura é descartada com log claro — nunca contextualizada por *default*.
9. **Contornar falha de hardware/toolchain do ESP32.** Se a toolchain do ESP32 (Arduino-ESP32 / ESP-IDF) ou o encadeamento Classe 0→ESP32 não funcionar em bancada, **parar e reportar** no `progress.json` — não "simular" o firmware nem trocar o dispositivo alvo para "resolver". O mock cobre os checkpoints automatizados; o firmware real é entregável separado com DoD de bancada.
10. **Hardcodar identidade ou endpoint.** O broker de ingestão (`INGEST_BROKER_URL`), o tópico-raiz (`INGEST_TOPIC_ROOT`, default `sida/ingest`), o `EDGE_GATEWAY_ID` e o `device_id` vêm **sempre** de `.env`/manifesto — nunca fixos em `flows.json`, imagem ou firmware.
11. **Quebrar a não-regressão do Modbus.** A cada checkpoint, o teste `test_s1_foundation.py::test_baseline_v2_pipeline` (ou equivalente na frota de Etapa 2) **continua verde**: um device `modbus_tcp` no mesmo nó segue publicando `DDATA` no UNS **em paralelo** ao device `interedge`.

**Se a IA "resolver" o problema de um jeito indesejado** (ex.: o adaptador publicando direto no UNS pulando `context`; reusar o Mosquitto do UNS para ingestão; embutir o `asset_context` no adaptador; alterar `modbusPolling` "para unificar"; persistir leituras "para não perder"), isso é **falha da task** — a task é revertida e refeita respeitando as fronteiras acima.

---

## 3. MÉTRICA DE CONCLUSÃO (CRITÉRIO DE PARADA)

### 3.1 Teste de aceite final

O loop é considerado concluído quando um script de teste automatizado (`test/etapa2/test_interedge_ingestion.py`), executado contra um **nó completo do SIDA** (core + ingestion + context + delivery), um **broker de ingestão local** (`mqtt-ingest`), um **Mosquitto isolado de UNS** e o **simulador de dispositivo Classe 1**, cumpre integralmente:

1. **Nó íntegro (t0).** Sobe o nó com o seu `.env` e um manifesto que contém **dois** devices na mesma linha ISA-95: `pump_01` (`protocol: modbus_tcp`, sondado pelo simulador Modbus) e `esp32_a` (`protocol: interedge`, mapeado em `Enterprise → Site → Area_1 → Line_1 → ESP32_A`). Confirma que ambos aparecem em `GET /api/config/manifest`.
2. **Ingestão InterEdge.** O simulador publica em `sida/ingest/esp32_a/telemetry` (broker `mqtt-ingest`), a cada `~1 s`, uma mensagem no formato do *device profile* (identidade + `readings` com ≥ 2 métricas: uma numérica, uma booleana). `mosquitto_sub -t 'sida/ingest/#' -v` mostra o tráfego. **Nada** aparece em `spBv1.0/#` vindo do dispositivo diretamente.
3. **Adaptação.** O sub-fluxo `interedgeAdapter` normaliza cada mensagem para o payload interno (`source.source_protocol == "interedge"`, `source.device_id == "esp32_a"`, `data` com as métricas do perfil) e a injeta em `ipc:///tmp/.ipc/ingestion.ipc`. O `context` a recebe **sem alteração no `context`**.
4. **Contextualização ISA-95.** O `context` resolve `esp32_a` no manifesto e monta o `asset_context` ISA-95 (`path` até `ESP32_A`), exatamente como faz para `pump_01`.
5. **Entrega no UNS.** O `delivery` publica, para `esp32_a`, `DBIRTH` (métricas com `alias`, `engUnit` quando houver) → `DDATA` (por alias, `seq` contínuo) no tópico `spBv1.0/{group_id}/DDATA/{edge_node_id}/Area_1_Line_1_ESP32_A` do Mosquitto isolado. Os **valores** batem com os que o simulador publicou (dentro da escala do manifesto).
6. **Não-regressão do Modbus.** Durante todo o cenário, `pump_01` (`modbus_tcp`) **continua** publicando `DBIRTH`/`DDATA` no UNS, no seu próprio tópico, sem lacuna atribuível ao adaptador `interedge`.
7. **Robustez do adaptador.** (a) Uma mensagem de ingestão **malformada** (JSON inválido / sem `device_id` / `device_id` não presente no manifesto) é **descartada com log claro** e **não** derruba o fluxo nem contamina outras leituras. (b) Ao reiniciar o `mqtt-ingest`, o adaptador reconecta sozinho e volta a entregar, sem intervenção.
8. **Relatório de métricas.** O script emite `test/etapa2/report.json` com: latência **sensor→UNS** (do `publish` no `mqtt-ingest` ao `DDATA` correspondente no UNS), taxa de mensagens `interedge` entregues vs. publicadas (perda), verificação booleana do mapeamento ISA-95 (`asset_context.path` termina em `ESP32_A`), `source_protocol` observado, e *overhead* de CPU/RAM (`docker stats` amostrado) do `mqtt-ingest` e do `ingestion`.

### 3.2 Ciclo de correção

Quando a verificação falhar, a IA segue o ciclo: **ler o erro → identificar a causa → corrigir → repetir o teste**.

**Número máximo de tentativas antes de escalar para o humano: 5.** Na 6ª falha consecutiva do mesmo teste, a IA para, registra em `progress.json` a causa raiz suspeita e as tentativas já feitas, e aguarda intervenção humana — nunca prossegue para a próxima task com esse teste ainda vermelho.

### 3.3 Estrutura de Sprints e Tasks (obrigatório para o loop)

O esforço é dividido em **3 sprints**, num total de **9 tasks** granulares. Cada task só é marcada `concluida` após cumprir o **checkpoint da seção 3.3.1** (teste funcional verde + `progress.json` atualizado + um commit), antes de a IA seguir para a próxima. Os IDs `T2.…` referenciam o Guia de Implementação do Ciclo V3.0 (as sub-tasks `T2.x.y` são refinamento deste SDD para checkpoint granular).

| Sprint | Foco | Tasks | Critério de saída do sprint |
|---|---|---|---|
| **S5** | Contrato `interedge` no `sida-core` + transporte de ingestão + simulador | `T2.4`, `T2.2a`, `T2.SIM` | manifesto com device `protocol: interedge` (sem `host`/`port`/`scan_rate_ms`) é **aceito**; `mqtt-ingest` sobe e o simulador publica em `sida/ingest/#`; `go test ./internal/core/domain/...` verde |
| **S6** | Adaptador de ingestão (`core/ingestion/flows.json`) | `T2.2b`, `T2.3` | `mqtt in` `sida/ingest/#` recebe a mensagem do simulador; `interedgeAdapter` produz o payload interno normalizado e o injeta no `ipc:///tmp/.ipc/ingestion.ipc`; o ramo Modbus/OPC UA segue intacto |
| **S7** | Contextualização ISA-95 + demonstração E2E + relatório | `T2.5`, `T2.6`, `T2.RPT` | os 8 passos do teste de aceite (3.1) passam; `report.json` gerado; `test_s1_foundation.py::test_baseline_v2_pipeline` (não-regressão do Modbus) continua verde |

**Fora do loop automatizado — entregável de hardware:** `T2.1` (firmware ESP32 com device/network profile InterEdge; encadeamento Classe 0 → ESP32 → RPi). DoD = leitura de sensor real chega ao `mqtt-ingest` e atravessa o pipeline até o UNS **em bancada**, registrado em `deploy/interedge-device/README.md`. Os checkpoints S5–S7 usam o **simulador** (`T2.SIM`) como *stand-in*, exatamente como a Etapa 1 usou `oitc/modbus-server` no lugar do CLP.

O **critério de saída do sprint** é uma checagem **integradora**, verificada **depois** que todas as tasks do sprint estão `concluida` e commitadas — não substitui os checkpoints por task.

### 3.3.1 Checkpoint obrigatório por task concluída (Definition of Done)

Nenhuma task avança para a próxima sem cumprir, **nesta ordem**, os três passos abaixo. Uma task só é `concluida` quando os três passam:

1. **Teste funcional verde.** Cada task tem um **teste funcional automatizado** próprio (comportamento observável ponta a ponta, não teste de unidade isolado), nomeado na tabela 3.3.2 (`arquivo::caso`). Ele roda contra a frota local de teste (`test/etapa2/compose.test.yml` + `mqtt-ingest` + Mosquitto isolado + simulador) e **deve passar**. Os testes das tasks já concluídas — **desta e das etapas anteriores** — **continuam verdes**: rodar a suíte acumulada da Etapa 2 a cada checkpoint **e** `test/etapa1/test_s1_foundation.py::test_baseline_v2_pipeline` (não-regressão do caminho v2.0). Sem regressão.
2. **`progress.json` atualizado.** Marcar a task `concluida` com timestamp, no mesmo passo (contrato da seção 3.4). É o **mesmo `progress.json`** da Etapa 1 — apenas acrescido das tasks `T2.…`.
3. **Um commit por task.** Criar **exatamente um commit** na branch `interedge` contendo o código/artefatos da task, o(s) teste(s) funcional(is) dela e o `progress.json` atualizado. Mensagem: `<tipo>(<escopo>): <descrição curta> [<ID da task>]` (ex.: `feat(ingestion): sub-fluxo adaptador InterEdge [T2.3]`), com o trailer de atribuição vigente. **Não** fazer squash das tasks nem emendar (`--amend`) commits de tasks já concluídas.

**Se o teste funcional não passar em até 5 tentativas** (seção 3.2): a task fica `bloqueada` em `progress.json` (causa raiz suspeita + nº de tentativas), **nenhum commit é feito** para ela, e o loop para para intervenção humana.

**Se uma task já commitada se revelar incorreta depois** (violou uma fronteira da seção 2, ou quebrou um teste anterior): **reverter** com um novo commit referenciando o `[ID da task]` e refazê-la — nunca reescrever o histórico.

### 3.3.2 Detalhamento das tasks (entrega + teste funcional + commit)

Todos os testes rodam contra a frota local isolada. Os testes de Etapa 1 continuam válidos e são executados como não-regressão.

**S5 — Contrato `interedge` + transporte + simulador**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T2.4` | `sida-core/internal/core/domain/manifest.go`: `interedge` no enum `Connection.Protocol`; `host`/`port`/`scan_rate_ms` passam a `omitempty` (ou `required_unless` incluindo `interedge`); `MetricMapping.RegisterType` não é exigido para `interedge`. Documento do *device profile*/mensagem de ingestão em `schemas/interedge_ingest.md` (+ `schemas/interedge_ingest.schema.json`). | `test_s5_interedge_contract.py::test_manifesto_interedge_aceito` — POST de um manifesto com device `{"connection":{"protocol":"interedge"}, "asset_context":{...}, "metrics_mapping":{...}}` retorna `200`; o mesmo device **sem** `asset_context` é rejeitado (`400`); um device `modbus_tcp` **sem** `host` segue rejeitado (regressão da validação); `go test ./sida-core/internal/core/domain/...` verde | `feat(sida-core): protocolo interedge no modelo Connection [T2.4]` |
| `T2.2a` | Serviço `mqtt-ingest` (`eclipse-mosquitto:2`, listener anônimo) na `docker-compose.yml` (profile ou serviço regular) e em `test/etapa2/compose.test.yml` (porta host dedicada, ex.: `18841`); `mosquitto.ingest.conf`; env `INGEST_BROKER_URL` / `INGEST_TOPIC_ROOT` nos serviços `poc-ingestion`/`edge*-ingestion` e no `.env.example`. **Sem** relação com o broker do UNS. | `test_s5_interedge_contract.py::test_broker_ingestao_isolado` — `docker compose -f test/etapa2/compose.test.yml up -d mqtt-ingest` sobe; um cliente publica em `sida/ingest/x` e outro recebe; `grep` na compose não acha o `mqtt-ingest` mapeado no mesmo host:porta do Mosquitto do UNS; `spBv1.0/#` no UNS **não** recebe nada do broker de ingestão | `feat(deploy): broker de ingestao dedicado mqtt-ingest [T2.2a]` |
| `T2.SIM` | `test/etapa2/esp32_sim.py` (ou imagem `python:3-slim` + `paho-mqtt`): publica no boot um *device profile* retido em `sida/ingest/{device}/profile` e, a cada `INTERVAL_MS`, uma leitura em `sida/ingest/{device}/telemetry` com `{ device_id, ts, readings: { temperature: <float>, running: <bool> } }`. Parametrizável por env (`DEVICE_ID`, `INGEST_BROKER_URL`, `INTERVAL_MS`, faixa dos valores). | `test_s5_interedge_contract.py::test_simulador_publica_perfil_e_leituras` — sobe o simulador; `mosquitto_sub -t 'sida/ingest/#'` recebe o `profile` (retido) e ≥ 3 `telemetry` em ≤ 10 s, cada um com `readings` contendo uma métrica numérica e uma booleana | `test(etapa2): simulador de dispositivo Classe 1 (mock ESP32) [T2.SIM]` |

**S6 — Adaptador de ingestão**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T2.2b` | Em `core/ingestion/flows.json`, um nó **`mqtt in`** novo assinando `${INGEST_TOPIC_ROOT}/+/telemetry` no broker `${INGEST_BROKER_URL}` (config-node de broker próprio, **não** o do UNS), num **novo grupo/aba** (`InterEdge Ingest`), sem fio para nenhum nó do ramo Modbus. Debug/hook de contagem. | `test_s6_interedge_adapter.py::test_mqtt_in_recebe_do_simulador` — com o nó e o simulador no ar, uma sonda (endpoint de debug do Node-RED ou um `zeromq`/HTTP hook de teste atrás de `INGEST_TEST_HOOKS=1`) confirma que o `mqtt in` recebeu ≥ 3 mensagens do tópico de ingestão; o `modbusPolling` segue emitindo em paralelo | `feat(ingestion): entrada MQTT do transporte de ingestao InterEdge [T2.2b]` |
| `T2.3` | Função **`interedgeAdapter`**: valida a mensagem (JSON, `device_id`, presença no manifesto global do fluxo), mapeia `readings → data` conforme o `metrics_mapping` do device (chave da métrica, escala/tipo), monta `{ timestamp: (msg.ts||Date.now()), gateway_id, source: { device_id, source_protocol: "interedge" }, data }` e faz `node.send` para o **mesmo `zeromq out`** (`ipc:///tmp/.ipc/ingestion.ipc`) que o ramo Modbus usa. Mensagem inválida → `node.warn` + descarte (sem `send`). | `test_s6_interedge_adapter.py::test_adapter_normaliza_e_injeta` — o `context` (assinando o IPC) recebe, para `esp32_a`, um payload com `source.source_protocol=="interedge"` e `data` com as chaves do `metrics_mapping`; uma mensagem malformada publicada em seguida **não** gera payload no IPC nem quebra o fluxo (a próxima leitura válida passa normalmente) | `feat(ingestion): sub-fluxo adaptador InterEdge [T2.3]` |

**S7 — ISA-95 + E2E + relatório**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T2.5` | `deploy/fleet/manifest.interedge.example.json` + suporte em `test/etapa2/seed_node_config.py` (ou reuso do de Etapa 1 com `--interedge-device`): device `esp32_a` com `connection.protocol="interedge"`, `asset_context.path` `Enterprise→Site→Area_1→Line_1→ESP32_A`, `metrics_mapping` (`temperature` float/`°C`, `running` bool). Documentação do mapeamento no `README-etapa2.md`. | `test_s7_e2e_interedge.py::test_isa95_mapeia_dispositivo_sem_clp` — semeia o manifesto; o `DBIRTH`/`DDATA` de `esp32_a` sai no tópico `spBv1.0/{group}/…/{edge_node}/Area_1_Line_1_ESP32_A`; o `asset_context` resolvido pelo `context` termina em `ESP32_A`; `Temperature` traz `engUnit="°C"` | `feat(deploy): manifesto ISA-95 para dispositivo interedge sem CLP [T2.5]` |
| `T2.6` | Nada de código novo além do harness: `test/etapa2/compose.test.yml` final (nó completo + `mqtt-ingest` + Mosquitto UNS isolado + `plc-sim` Modbus + `esp32_sim`) + `README-etapa2.md`. Cenário ponta a ponta dos passos 1–7 de 3.1. | `test_s7_e2e_interedge.py::test_pipeline_interedge_ponta_a_ponta` — sensor simulado → `mqtt-ingest` → `interedgeAdapter` → `context` (ISA-95) → `delivery` (Sparkplug) → UNS isolado: `DDATA` de `esp32_a` **e** de `pump_01` (Modbus) chegam em paralelo; valores de `esp32_a` batem com os publicados; mensagem malformada é descartada; bounce do `mqtt-ingest` → adaptador reconecta e volta a entregar | `test(etapa2): pipeline interedge ponta a ponta + nao-regressao Modbus [T2.6]` |
| `T2.RPT` | Geração de `test/etapa2/report.json` (gitignored): latência sensor→UNS (p50/p95), mensagens `interedge` publicadas vs. entregues (perda), verificação ISA-95 (bool), `source_protocol` observado, *overhead* CPU/RAM (`docker stats`) de `mqtt-ingest` e `ingestion`. **Fecha o aceite da Etapa 2.** | `test_s7_e2e_interedge.py::test_report_e_aceite` — o cenário de 3.1 roda ponta a ponta, `report.json` valida contra o schema esperado, `perda == 0` no regime estável, `isa95_ok == true`, e o `test_baseline_v2_pipeline` da Etapa 1 segue verde | `feat(etapa2): report.json de metricas da ingestao InterEdge [T2.RPT]` |

### 3.4 Registro de progresso (para interrupção/retomada)

A IA **deve** manter o **mesmo `progress.json`** da Etapa 1 (raiz do projeto, versionado), acrescentando as tasks `T2.…` à lista `tasks`, com o contrato já vigente: por task — identificador do sprint (`S5`/`S6`/`S7`), identificador da task, descrição curta, status (`pendente` | `em_andamento` | `concluida` | `bloqueada`), timestamp, o commit da task (quando `concluida`), e — se `bloqueada` — motivo e nº de tentativas.

O `progress.json` e o **commit da task** são gravados no **mesmo checkpoint**: o estado confiável é o `progress.json` **cruzado com o `git log` da branch `interedge`** (um commit `[T…]` por task `concluida`). **Antes de iniciar qualquer trabalho em uma nova sessão**, a IA lê o `progress.json` **e** o `git log` da branch `interedge` e retoma da primeira task `T2.…` sem checkpoint completo, sem repetir tasks já `concluida` e commitadas, e sem tocar nas 22 tasks da Etapa 1.

---

## 4. ESTADO DO SISTEMA

Estado **por nó**. A Etapa 2 acrescenta apenas o que está marcado **(novo E2)**; o restante é herdado da Etapa 1 e **não muda**.

| Variável | Onde vive | Tipo | Valores possíveis | Estado inicial |
|---|---|---|---|---|
| `ingest.mqtt_client` **(novo E2)** | `ingestion` (contexto do fluxo) | cliente MQTT | conectado ao `INGEST_BROKER_URL`; assina `${INGEST_TOPIC_ROOT}/+/telemetry`; reconecta sozinho | desconectado |
| `ingest.device_manifest` **(novo E2)** | `ingestion` (global, já carregado para o ramo Modbus) | mapa `device_id → Device` | usado pelo `interedgeAdapter` para validar o `device_id` e ler o `metrics_mapping` | do manifesto |
| `sparkplug.bdSeq` / `sparkplug.seq` / `alias_map` / `born_devices` / `node_state` | `delivery` | — | **herdado da Etapa 1, sem alteração** — o device `interedge` entra no mesmo ciclo de vida (`DBIRTH`/`DDATA` por alias) que um device Modbus | — |
| `peer.registry` / `peer.liveness` / `controllers` (SQLite) | `sida-core` | — | **herdado da Etapa 1, sem alteração** | — |
| `node_identity` | env (`/app/data/.env` + compose) | struct | herda tudo da Etapa 1 **+** `INGEST_BROKER_URL`, `INGEST_TOPIC_ROOT` **(novo E2)** | do `.env` do nó |
| `progress.json` (fora do runtime) | repositório | arquivo | lista de tasks (22 da Etapa 1 + 9 da Etapa 2) | conforme seção 3.4 |

---

## 5. ALGORITMOS E REGRAS DE NEGÓCIO

### 5.1 Transporte de ingestão (dispositivo → RPi)

1. **Broker dedicado.** `mqtt-ingest` = Mosquitto local, listener anônimo, **sem** ponte para o broker do UNS. Tópico-raiz `INGEST_TOPIC_ROOT` (default `sida/ingest`). Convenção: `sida/ingest/{device_id}/profile` (retido, publicado 1× no boot do dispositivo/mock) e `sida/ingest/{device_id}/telemetry` (leitura periódica).
2. **Isolamento.** Em produção, `mqtt-ingest` roda **no próprio RPi** (localhost) — o dispositivo Classe 1 na LAN publica nele; o RPi encaminha ao UNS pelo `delivery`. O UNS de produção (GCP) **nunca** recebe conexão de dispositivo. No teste, `mqtt-ingest` é um serviço da `compose.test.yml` com porta host própria.
3. **Sem QoS/retained no telemetry.** `telemetry` é `qos 0`, não retido (fire-and-forget, como o `DDATA`). `profile` é retido para o adaptador conhecer o device mesmo se subir depois.

### 5.2 *Device profile* / mensagem de ingestão (contrato InterEdge, mínimo)

`schemas/interedge_ingest.md` + `schemas/interedge_ingest.schema.json` definem:

- **`profile`** (retido, `sida/ingest/{device_id}/profile`):
  ```json
  { "device_id": "esp32_a", "class": 1, "vendor": "espressif",
    "network_profile": { "transport": "mqtt", "interval_ms": 1000 },
    "device_profile": { "metrics": {
       "temperature": { "type": "float", "unit": "°C" },
       "running":     { "type": "bool" } } } }
  ```
- **`telemetry`** (`sida/ingest/{device_id}/telemetry`):
  ```json
  { "device_id": "esp32_a", "ts": 1731000000000,
    "readings": { "temperature": 23.7, "running": true } }
  ```
- O `profile` é **informativo** (diagnóstico/observabilidade). A **verdade da contextualização** é o **manifesto** do SIDA (`asset_context` + `metrics_mapping`), resolvido pelo `context` via `device_id`. Divergência `profile` × manifesto → o manifesto vence; o adaptador loga um aviso.

### 5.3 Adaptador de ingestão (`core/ingestion/flows.json`, sub-fluxo novo — plano de entrada)

1. **Entrada.** `mqtt in` no broker `${INGEST_BROKER_URL}`, tópico `${INGEST_TOPIC_ROOT}/+/telemetry`. Config-node de broker **próprio** (id distinto do broker do UNS). Aba/grupo `InterEdge Ingest`, isolado do ramo Modbus/OPC UA.
2. **`interedgeAdapter`** (function node):
   - **`[valida]`** `msg.payload` é JSON objeto; tem `device_id` string; o `device_id` existe em `global.get("manifest").config.plant…devices` (mesmo `deviceCache` que o `setupClient` já monta). Falha em qualquer ponto → `node.warn("[interedge] descartado: <motivo>")` e **retorna sem `node.send`**.
   - **`[normaliza]`** para cada `k` em `readings`: se `k` está no `metrics_mapping` do device, aplica `scale_factor`/`data_type` (mesma semântica do `context`/`modbusPolling`); a chave em `data` é a **chave do `metrics_mapping`** (ex.: `"40001"` no Modbus, ou o nome lógico no `interedge` — o manifesto define). Chave não mapeada → ignorada com `node.warn`.
   - **`[emite]`** `node.send({ payload: { timestamp: Number(msg.payload.ts) || Date.now(), gateway_id: global.get("gateway_id"), source: { device_id, source_protocol: "interedge" }, data } })`.
3. **Saída.** O `node.send` vai para o **mesmo `zeromq out`** (`ZQM Output`, `ipc:///tmp/.ipc/ingestion.ipc`) que o ramo Modbus. Um `link in`/`link out` ou fio direto — **sem** passar por `modbusPolling`/`opcuaPolling`.
4. **Stateless.** Nenhum contador, buffer ou dedupe. Uma leitura → zero ou uma injeção no IPC.
5. **Reconexão.** O `mqtt in` do Node-RED reconecta sozinho ao `mqtt-ingest`; ao voltar, retoma a assinatura. Nenhuma leitura do período offline é recuperada (Fronteira 7).

### 5.4 Modelo `Connection` no `sida-core` (`manifest.go`)

1. `Protocol` passa a `oneof=modbus_tcp modbus_rtu opc_ua s7 interedge`.
2. `ScanRateMs`: `binding:"omitempty,min=50"` — não exigido para `interedge` (dispositivo empurra na sua própria cadência; a cadência real vem do `network_profile`/dispositivo).
3. `Host`/`Port`: `binding:"required_unless=Protocol opc_ua interedge,omitempty,…"` — `interedge` não tem host/porta (é o dispositivo que conecta ao `mqtt-ingest`).
4. `MetricMapping.RegisterType`: continua `omitempty` — para `interedge` a chave do `metrics_mapping` é o **nome lógico** da métrica no `readings` (ex.: `"temperature"`), não um registrador.
5. `Device.AssetContext` continua `required` — um device `interedge` **sem** `asset_context` é rejeitado (Fronteira 8: sem contexto ISA-95 não há ingestão).
6. Validações **existentes de outros protocolos não mudam** (regressão): `modbus_tcp` sem `host` segue `400`; `opc_ua` sem `endpoint_url` segue `400`.

### 5.5 Casos de teste (few-shot, mínimo 6)

**Caso 1 — Ingestão feliz sem CLP**
- Entrada: manifesto com `esp32_a` (`interedge`, `asset_context` até `ESP32_A`, `metrics_mapping`: `temperature` float `°C`, `running` bool); simulador publica `telemetry` a cada 1 s.
- Saída esperada: o broker do UNS recebe, para `esp32_a`, `DBIRTH`(`temperature` com `alias`+`engUnit="°C"`, `running` com `alias` distinto) → `DDATA`(por alias, `seq` contínuo). Valores de `DDATA` ≈ valores publicados no `mqtt-ingest` (dentro da escala).

**Caso 2 — Convivência com Modbus (não-regressão)**
- Entrada: o mesmo nó tem `pump_01` (`modbus_tcp`, sondado pelo `plc-sim`) e `esp32_a` (`interedge`) na mesma `Line_1`.
- Saída esperada: ambos publicam `DDATA` no UNS, em tópicos distintos, **em paralelo e continuamente**; nenhuma lacuna em `pump_01` atribuível ao adaptador; `test_baseline_v2_pipeline` (Etapa 1) verde.

**Caso 3 — Mensagem malformada**
- Entrada: o simulador publica um `telemetry` com JSON inválido, depois um sem `device_id`, depois um com `device_id` ausente do manifesto — e volta a publicar mensagens válidas.
- Saída esperada: cada malformada gera `node.warn` e **nenhuma** injeção no IPC; o fluxo **não** cai; a leitura válida seguinte passa normalmente.

**Caso 4 — `mqtt-ingest` cai e volta**
- Entrada: `docker restart mqtt-ingest` durante o regime; o dispositivo/simulador segue publicando (perde o período offline).
- Saída esperada: o `mqtt in` do `ingestion` reconecta sozinho em ≤ ~10 s e volta a entregar `DDATA` de `esp32_a` no UNS; nenhuma intervenção manual; o adaptador não trava nem duplica.

**Caso 5 — Device `interedge` fora do manifesto**
- Entrada: o simulador publica `telemetry` de `esp32_ghost`, que **não** está no manifesto.
- Saída esperada: o adaptador descarta com log claro (`[interedge] descartado: device_id 'esp32_ghost' ausente no manifesto`); **nada** chega ao `context`; nenhum `DBIRTH`/`DDATA` de `esp32_ghost` no UNS.

**Caso 6 — Manifesto atualizado em runtime**
- Entrada: com o nó no ar, o manifesto é reenviado (`POST /api/config/manifest`) adicionando `esp32_b`; o simulador começa a publicar `esp32_b`.
- Saída esperada: o `ingestion` recebe o `ManifestUpdate` (`sida/manifest`), o `deviceCache` do fluxo é atualizado, e `esp32_b` passa a ser contextualizado e a publicar `DDATA` no UNS — sem reiniciar o nó.

**Caso 7 — Rótulo de origem preservado**
- Entrada: um `DDATA` de `esp32_a` capturado no UNS.
- Saída esperada: rastreabilidade — o `context`/`delivery` trataram o payload com `source.source_protocol == "interedge"` (visível em log/observabilidade); o `report.json` registra `source_protocol` observado por device.

**Caso 8 — ESP32 encadeando um sensor Classe 0** *(bancada, `T2.1`)*
- Entrada: sensor Classe 0 (ex.: TMP36 num Arduino sem rede) → UART → ESP32 (Classe 1) → Wi-Fi → `mqtt-ingest` do RPi.
- Saída esperada: a leitura do sensor Classe 0 aparece contextualizada no UNS como `DDATA` de um device `interedge`; o `device_id` identifica o **ESP32** (o Classe 0 é fonte física, o Classe 1 é o "controlador"). Validado manualmente, registrado em `deploy/interedge-device/README.md`.

---

## 6. SEPARAÇÃO DE RESPONSABILIDADES

### 6.1 Estrutura de arquivos

```
# ── Contrato do dispositivo / ingestão ──
sida-core/internal/core/domain/manifest.go   # + "interedge" no enum Connection.Protocol; validações de polling condicionais
schemas/interedge_ingest.md                  # NOVO — device profile + mensagem de telemetry (contrato InterEdge mínimo)
schemas/interedge_ingest.schema.json         # NOVO — JSON Schema da mensagem de ingestão

# ── Adaptador (Node-RED / ingestion) ──
core/ingestion/flows.json                    # NOVO sub-fluxo "InterEdge Ingest": mqtt in (sida/ingest/+/telemetry) → interedgeAdapter → ZQM Output
                                             # (ramo modbusPolling/opcuaPolling/setupClient/ZQM Output: INTACTO)

# ── Transporte / orquestração ──
docker-compose.yml                           # + serviço mqtt-ingest (Mosquitto local, listener anônimo); env INGEST_BROKER_URL / INGEST_TOPIC_ROOT
.env.example                                 # + INGEST_BROKER_URL, INGEST_TOPIC_ROOT
deploy/fleet/manifest.interedge.example.json # NOVO — device interedge mapeado em ISA-95
deploy/interedge-device/                      # NOVO — firmware ESP32 (C/C++) + README de bancada (T2.1, hardware)

# ── Testes e loop ──
test/etapa2/compose.test.yml                 # NOVO — nó completo + mqtt-ingest + Mosquitto UNS isolado + plc-sim + esp32_sim
test/etapa2/mosquitto.ingest.conf            # NOVO — Mosquitto de ingestão (anônimo, local)
test/etapa2/esp32_sim.py                     # NOVO — simulador de dispositivo Classe 1 (mock ESP32)
test/etapa2/seed_node_config.py              # NOVO (ou --interedge-device no de etapa1) — semeia manifesto com device interedge
test/etapa2/conftest.py                      # NOVO — fixtures (reusa require_compose/require_paho/spb_pb2 da etapa1)
test/etapa2/test_s5_interedge_contract.py    # checkpoints S5 (T2.4, T2.2a, T2.SIM)
test/etapa2/test_s6_interedge_adapter.py     # checkpoints S6 (T2.2b, T2.3)
test/etapa2/test_s7_e2e_interedge.py         # checkpoints S7 (T2.5, T2.6, T2.RPT) + casos 1–7
test/etapa2/report.json                      # gerado por T2.RPT (gitignored)
progress.json                                # MESMO arquivo da Etapa 1 — + tasks T2.… (um commit [T…] por task)
README-etapa2.md                             # como subir o nó com ingestão InterEdge e rodar os testes
```

### 6.2 Responsabilidades por módulo

| Módulo | Faz | NÃO faz |
|---|---|---|
| `manifest.go` — `Connection` | Aceita `protocol: "interedge"`; condiciona `host`/`port`/`scan_rate_ms`/`register_type` ao protocolo | Não remove/afrouxa validação de `modbus_*`/`opc_ua`; não torna `asset_context` opcional |
| `schemas/interedge_ingest.*` | Documenta o *device profile* e a mensagem de `telemetry` (contrato mínimo) | Não é carregado em runtime; não substitui o manifesto na contextualização |
| `core/ingestion` — `mqtt in` (novo) | Assina `${INGEST_TOPIC_ROOT}/+/telemetry` no broker **de ingestão** | Não assina `spBv1.0/#`; não usa o broker do UNS |
| `core/ingestion` — `interedgeAdapter` | Valida o `device_id` contra o manifesto, normaliza `readings → data`, emite o payload interno no **mesmo IPC** do ramo Modbus | Não enriquece `asset_context`; não persiste; não altera `modbusPolling`/`opcuaPolling`; não fala com o UNS |
| `mqtt-ingest` (broker) | Transporte local dispositivo → RPi (`sida/ingest/#`), anônimo, isolado | Não faz ponte para o UNS; não roda TLS; não persiste |
| `esp32_sim.py` | Publica *profile* retido + `telemetry` periódica no `mqtt-ingest` | Não fala com o `sida-core` nem com o UNS; não atua |
| `core/context` / `core/delivery` | **Inalterados** — contextualizam e entregam o device `interedge` pelo mesmo caminho do Modbus | — |
| `test/etapa2/` | Sobe o nó + broker de ingestão + simulador, verifica `interedge → adapter → context → delivery → UNS`, mede latência/perda, checa não-regressão do Modbus | Não toca no broker de produção; não valida hardware (isso é `T2.1`, bancada) |

---

## 7. CASOS EXTREMOS

1. **`telemetry` chega antes do manifesto carregar** (corrida no boot do `ingestion`) — o `interedgeAdapter` descarta com log (`manifesto ainda não carregado`) até o `deviceCache` existir; nenhuma leitura é contextualizada por *default*. As leituras seguintes, já com manifesto, passam.
2. **Relógio do dispositivo dessincronizado** — `msg.payload.ts` do dispositivo pode divergir do RPi. A latência sensor→UNS do `report.json` é medida no **RPi** (do `on_message` do `mqtt in` ao `DDATA` no UNS), nunca por diferença de *wall-clock* com o dispositivo. O `timestamp` do payload interno usa `msg.ts` se plausível, senão `Date.now()`.
3. **Métrica no `readings` fora do `metrics_mapping`** — ignorada com `node.warn`; as métricas mapeadas seguem. Nunca propagar chave não declarada (o `DBIRTH`/`alias_map` do `delivery` só conhece o que o manifesto define).
4. **Device `interedge` com `enabled: false` no manifesto** — o `interedgeAdapter` descarta suas leituras (mesma semântica do `setupClient` que não abre cliente para device desabilitado).
5. **Dois dispositivos publicando o mesmo `device_id`** — o adaptador não distingue origem (é MQTT anônimo); as leituras se intercalam. Aceitável para sensoriamento; documentar. Colisão real é erro de provisionamento do dispositivo, não do middleware.
6. **`mqtt-ingest` inacessível no boot** — o `mqtt in` fica em estado *connecting* e reconecta quando o broker sobe; o ramo Modbus **não** é afetado (broker/transporte independentes).
7. **Volume alto de dispositivos/leituras** — o `interedgeAdapter` é `O(1)` por mensagem e *stateless*; o gargalo é o `mqtt-ingest` e o IPC Push, dimensionados como o ramo Modbus. Sem buffer, o *backpressure* é o do próprio ZeroMQ Push (igual ao Modbus).
8. **Payload `interedge` idêntico ao de um device Modbus** (mesmo `device_id`) — proibido por provisionamento (um `device_id` tem **um** `connection.protocol` no manifesto). Se ocorrer, o `context` usa o `metrics_mapping` do manifesto — o `source_protocol` do payload é só rótulo.
9. **Firmware ESP32 não builda/roda em bancada (`T2.1`)** — parar e reportar; **não** trocar o alvo nem "simular" o firmware. Os checkpoints S5–S7 seguem com o `esp32_sim`; `T2.1` fica `bloqueada` com a causa registrada.
10. **Sensor Classe 0 sem rede (`T2.1`, caso 8)** — o encadeamento é `sensor → (UART/analógico) → ESP32 → Wi-Fi → mqtt-ingest`; o `device_id` no `mqtt-ingest` é o do **ESP32** (controlador Classe 1), não o do sensor. O manifesto mapeia o ESP32 na hierarquia.

---

## 8. STACK TÉCNICA

- **Adaptador:** Node-RED 4.x (imagem ARM64 já validada), nós **`mqtt in`** nativo + `function` (`interedgeAdapter`) em `core/ingestion/flows.json`. Config-node de broker MQTT dedicado (não o do UNS). `functionExternalModules: true` já está ligado; nada novo de npm é necessário.
- **Transporte de ingestão:** `eclipse-mosquitto:2` (`mqtt-ingest`), listener `1883` interno, anônimo, **local ao RPi** em produção; porta host dedicada no teste. Sem TLS.
- **`sida-core`:** Go (mesma toolchain, `go 1.26.3`, `linux/arm64`); só `manifest.go` muda (enum + *tags* de validação `binding`). `go-playground/validator` já resolve `oneof`/`required_unless`. Sem novas dependências.
- **Simulador:** Python 3.10+ + `paho-mqtt` (imagem `python:3-slim` ou script direto) — *stand-in* do ESP32 para os checkpoints, análogo ao `oitc/modbus-server` da Etapa 1.
- **Firmware (T2.1, hardware):** ESP32 (Arduino-ESP32 **ou** ESP-IDF), C/C++; `PubSubClient`/`esp-mqtt` para o `mqtt-ingest`; leitura de sensor (DHT11/TMP36); UART para o encadeamento com Classe 0. **Fora do build do repositório** — entregável em `deploy/interedge-device/`.
- **Testes:** Python 3.10+ (`pytest`), `paho-mqtt` (assina `sida/ingest/#` e `spBv1.0/#`), `requests` (`/api/config/manifest`), `protobuf`+`protoc` (decodifica Sparkplug B, reuso da fixture `spb_pb2` da Etapa 1), `docker` CLI. Broker do UNS = **Mosquitto isolado** (`test/etapa2/compose.test.yml`), sem relação com o de produção.
- **Restrições de dependências:** nenhum banco novo, nenhum *message broker* adicional **além do `mqtt-ingest`** (que é local e descartável). O `ingestion` continua *stateless*. O adaptador não persiste nada.

---

## 9. PROMPT PRONTO PARA O LOOP

```
Você vai implementar a Etapa 2 do Ciclo V3.0 do SIDA seguindo este SDD. A Etapa 1
(frota descentralizada + planos A/B) JÁ ESTÁ CONCLUÍDA na branch interedge (22 tasks,
progress.json, teste de aceite verde) — NÃO a altere.

OBJETIVO: ampliar a camada de INGESTÃO para aceitar dispositivos Classe 0/1 sem CLP
como "mais uma fonte de protocolo", pelo caminho:
  dispositivo/mock -> broker de ingestão local (mqtt-ingest, sida/ingest/#)
  -> sub-fluxo adaptador novo em core/ingestion/flows.json (mqtt in -> interedgeAdapter)
  -> MESMO zeromq out (ipc:///tmp/.ipc/ingestion.ipc) do ramo Modbus
  -> core/context (ISA-95, INALTERADO) -> core/delivery (Sparkplug, INALTERADO) -> UNS.

TRABALHO (não reescrever nada existente):
  1. sida-core/internal/core/domain/manifest.go: "interedge" no enum
     Connection.Protocol; host/port/scan_rate_ms NÃO exigidos para interedge;
     asset_context CONTINUA obrigatório. Validações de modbus_*/opc_ua INTACTAS.
  2. Serviço mqtt-ingest (Mosquitto anônimo local) no docker-compose.yml e no
     test/etapa2/compose.test.yml; env INGEST_BROKER_URL / INGEST_TOPIC_ROOT.
     NUNCA reusar o broker do UNS. schemas/interedge_ingest.{md,schema.json}.
  3. test/etapa2/esp32_sim.py: mock de ESP32 (profile retido + telemetry periódica
     em sida/ingest/{device}/...). Stand-in dos checkpoints (como o oitc/modbus-server
     foi na Etapa 1). O firmware C/C++ real (T2.1) é entregável de HARDWARE, bancada.
  4. core/ingestion/flows.json: NOVO sub-fluxo "InterEdge Ingest" (mqtt in
     sida/ingest/+/telemetry -> interedgeAdapter -> ZQM Output), em paralelo ao
     modbusPolling/opcuaPolling/setupClient, que ficam INTACTOS. O interedgeAdapter
     valida o device_id contra o manifesto, normaliza readings->data pelo
     metrics_mapping e emite { timestamp, gateway_id, source:{device_id,
     source_protocol:"interedge"}, data } — MESMO shape do modbusPolling. Malformada
     -> node.warn + descarte. Stateless.
  5. deploy/fleet/manifest.interedge.example.json + seed: device esp32_a
     (protocol interedge) mapeado em Enterprise->Site->Area_1->Line_1->ESP32_A,
     metrics_mapping temperature(float/°C) e running(bool).

FRONTEIRAS:
- Não tocar em core/context/flows.json, core/delivery/flows.json, nem nos planos A/B
  do sida-core (peer_service, :5557, /api/system/peers, tabela controllers).
- Não reescrever modbusPolling/opcuaPolling/setupClient/ZQM Output — adaptador é ADIÇÃO.
- Broker/tópico de INGESTÃO (sida/ingest/#, mqtt-ingest) != broker do UNS (spBv1.0/#).
  O adaptador nunca assina spBv1.0/#; o dispositivo nunca publica em spBv1.0/#.
- Não dar atuação/controle ao dispositivo. Só sensoriamento.
- Não persistir/bufferizar leituras (sem store-and-forward). Não enriquecer
  asset_context no adaptador (vem do manifesto; device sem asset_context -> descarte).
- Não adicionar TLS/mTLS; broker de ingestão de teste é anônimo e local.
- Não contornar falha de toolchain/hardware do ESP32 (T2.1): parar e reportar.
- O caminho Modbus da v2.0 NÃO pode regredir: test/etapa1/test_s1_foundation.py::
  test_baseline_v2_pipeline continua verde a cada checkpoint.
- Identidade/endpoint sempre via .env/manifesto — nada hardcoded em flows.json/imagem.

MÉTRICA DE CONCLUSÃO: test/etapa2/test_s7_e2e_interedge.py passa integralmente
(nó completo + mqtt-ingest + Mosquitto UNS isolado + plc-sim + esp32_sim): a leitura
do sensor simulado chega ao UNS como DDATA de esp32_a no tópico Sparkplug correto,
contextualizada por ISA-95 (asset_context termina em ESP32_A), com valores íntegros,
ENQUANTO pump_01 (modbus_tcp) segue publicando em paralelo sem regressão; mensagem
malformada é descartada com log e não quebra o fluxo; bounce do mqtt-ingest ->
adaptador reconecta; report.json com latência sensor->UNS, perda (=0 no regime
estável), isa95_ok=true e overhead CPU/RAM. Em cada falha: leia o erro, identifique a
causa, corrija, repita. Máximo 5 tentativas por task antes de parar e escalar,
registrando a causa suspeita em progress.json.

PROCESSO: siga a divisão em sprints S5-S7 e o detalhamento da seção 3.3.2
(S5 contrato interedge + transporte + simulador; S6 adaptador; S7 ISA-95 + E2E +
relatório). Antes de começar, leia progress.json E o git log da branch interedge;
retome da primeira task T2.* sem checkpoint completo, sem repetir as 22 tasks da
Etapa 1.
CHECKPOINT OBRIGATÓRIO POR TASK (seção 3.3.1), nesta ordem:
  1. o teste funcional da task (tabela 3.3.2: arquivo::caso) passa contra a frota
     local, os testes das tasks T2.* anteriores continuam verdes E
     test/etapa1/test_s1_foundation.py::test_baseline_v2_pipeline (não-regressão);
  2. progress.json marca a task concluida (status, timestamp, commit; se bloqueada,
     motivo e nº de tentativas);
  3. UM único commit na branch interedge com o código + o teste funcional + o
     progress.json, mensagem "<tipo>(<escopo>): <descrição> [<ID da task>]".
Sem teste funcional verde NÃO há commit e a task NÃO é concluida. Falhou 5x: task
bloqueada, sem commit, pare e escale. Sem squash; não emende commits anteriores.

Consulte as seções 0.1 (estado atual), 4 (contrato de estado), 5 (regras de negócio +
casos de teste), 6 (estrutura e responsabilidades), 7 (casos extremos) e 8 (stack).
```

---

## Histórico de decisões deste SDD

| # | Decisão | Origem |
|---|---|---|
| 1 | Escopo = Etapa 2 do Ciclo V3.0: **ingestão de dispositivos Classe 0/1 sem CLP** (`T2.1`–`T2.6` do Guia), tratando o dispositivo como "mais uma fonte de protocolo". A Etapa 1 (frota A+B) tem SDD próprio, já concluído. | Guia de Implementação do Ciclo V3.0, §"Etapa 2"; Release Notes V3.0 §PoC 4 |
| 2 | **Nada dos planos A/B da Etapa 1 é alterado.** A Etapa 2 é ortogonal — só a **entrada** do pipeline (`core/ingestion` + `Connection` no `sida-core`). O `context` e o `delivery` não mudam. | Guia §T2.3 (DoD "o context recebe o payload normalizado sem alterações nele"); inspeção de `contextualizeData` |
| 3 | Transporte dispositivo→RPi = **broker MQTT de ingestão dedicado** (`mqtt-ingest`, `sida/ingest/#`), local ao RPi, **separado** do broker do UNS. Alternativa HTTP POST descartada por simplicidade e pelo nó `mqtt in` nativo do Node-RED. | Guia §T2.2 ("Recomendado: MQTT local"); Riscos §4 ("dois planos MQTT não podem se confundir") |
| 4 | O **manifesto** (não o *device profile* do dispositivo) é a fonte da verdade da contextualização ISA-95 — o adaptador só valida o `device_id` e normaliza `readings→data`. Prova do **nível organizacional** do InterEdge para fonte sem CLP. | Guia §T2.5; `01-projeto.md` §1.3 e §4.1 (nível organizacional ≙ ISA-95, contribuição inédita) |
| 5 | O **firmware ESP32** (`T2.1`) é **entregável de hardware**, validado em bancada e documentado em `deploy/interedge-device/` — **fora do loop automatizado**. Os checkpoints S5–S7 usam um **simulador** (`esp32_sim.py`), análogo ao `oitc/modbus-server` que substituiu o CLP na Etapa 1. | Natureza do artefato (firmware C/C++ não builda no repo); precedente do simulador de CLP na Etapa 1 |
| 6 | `Connection.Protocol` ganha `interedge`; `host`/`port`/`scan_rate_ms`/`register_type` deixam de ser exigidos para esse protocolo (dispositivo empurra, não é sondado); `asset_context` **continua obrigatório**. Validações dos demais protocolos **intactas** (regressão coberta por teste). | Guia §T2.4; inspeção de `manifest.go` (`oneof`/`required_unless` do validator) |
| 7 | Adaptador **stateless**, sem *store-and-forward* nem buffer. Se `mqtt-ingest`/`ingestion` cair, a leitura do período é perdida — a Etapa 2 mede **contextualização e continuidade em regime**, não recuperação (roadmap). | Delimitações consolidadas (§9 do Histórico de Decisões da Etapa 1); Fronteira 7 |
| 8 | Não-regressão do Modbus é **critério de checkpoint**: a cada task, `test_baseline_v2_pipeline` (Etapa 1) e a suíte `T2.*` acumulada continuam verdes; o device `interedge` publica **em paralelo** ao `modbus_tcp` no mesmo nó. | Fronteira 1/11; método de checkpoint da Etapa 1 (seção 3.3.1) |
| 9 | Fora de escopo, por decisão: firmware Classe 0 além do encadeamento mínimo; atuação/controle no dispositivo; TLS/mTLS no `mqtt-ingest`; *store-and-forward*; dashboard/observabilidade além de logs estruturados; qualquer alteração nos planos A/B. | `01-projeto.md` §"Delimitações"; `CLAUDE.md` §"Escopo" |
| 10 | Molde herdado do `SDD_SIDA_Etapa1_Ciclo_V3.md`: sprints numerados (aqui **S5–S7**, continuando a numeração), checkpoint por task (teste funcional nomeado + `progress.json` + **um** commit `[T…]` na branch `interedge`, sem squash/`--amend`), máx. 5 tentativas antes de escalar, teste de aceite automatizado contra broker local isolado, `report.json` de métricas. **Mesmo `progress.json`**, apenas acrescido das 9 tasks `T2.…`. | `SDD_SIDA_Etapa1_Ciclo_V3.md` (seções 3.3.1/3.3.2/3.4) |
