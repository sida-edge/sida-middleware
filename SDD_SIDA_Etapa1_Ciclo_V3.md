# SDD — SIDA Etapa 1 do Ciclo V3.0
### Frota de borda descentralizada e resiliente: ciclo de vida Sparkplug B (plano norte) + malha *controller-to-controller* InterEdge (plano leste-oeste)

---

## 0. Contexto herdado (não é parte do loop, apenas referência)

Este SDD descreve a **Etapa 1 do Ciclo V3.0** do SIDA: transformar a topologia centralizada validada nas Releases 1.0/2.0 (um único gateway de borda) em uma **frota de gateways Raspberry Pi**, cada um executando a pilha completa do SIDA e publicando num **Unified Namespace (UNS)** compartilhado, **sem nó central de coordenação na borda**. A meta central, verificável, é **eliminar o ponto único de falha (SPOF) do plano de borda**, comprovada por **teste de injeção de falha**.

A coordenação da frota usa **dois mecanismos simultâneos, em planos de transporte distintos** (decisão de projeto já fechada — A + B juntos):

| Plano | Mecanismo | Transporte | Onde vive | Papel |
|---|---|---|---|---|
| **Norte** (borda → nuvem) | **A** — ciclo de vida Sparkplug B (`NBIRTH`/`DBIRTH`/`DDATA`/`NDEATH` + LWT) | MQTT → broker do UNS | camada **delivery** (`core/delivery/flows.json`, Node-RED) | autodescrição e observabilidade da frota no namespace |
| **Leste-oeste** (borda ↔ borda) | **B** — *controller-to-controller* do InterEdge (registro de pares, *probes*, roteamento) | ZeroMQ entre os `sida-core` | **`sida-core`** (Go) | detecção **local** de queda de par, independente da nuvem |

**Fora do escopo deste SDD** (têm SDD próprio ou são roadmap): a **Etapa 2** (ingestão de dispositivos Classe 0/1 sem CLP); o *store-and-forward* persistente; segurança TLS/mTLS e evolução de autenticação; redundância do broker de nuvem.

### 0.1 Estado atual do código (levantado por inspeção — ponto de partida real)

- **Plano A (ciclo de vida Sparkplug B) JÁ ESTÁ IMPLEMENTADO** em `core/delivery/flows.json` — a Etapa 1A **não constrói o ciclo de vida, apenas o torna conforme**. Verificado por inspeção nesta sessão:

  | Sinal / comportamento | Estado hoje | Onde |
  |---|---|---|
  | **`NBIRTH`** na subida | ✅ **Emite** — tópico `spBv1.0/{site}/NBIRTH/{gateway_id}`, `seq=0`, métrica `Node Control/Rebirth=false` | `DeliveryProcessor`, ramo `msg.topic === "connection_status"` |
  | **`NDEATH` via LWT** (queda abrupta) | ✅ **Configurado** — `will` do cliente MQTT: tópico `spBv1.0/{site}/NDEATH/{gateway_id}`, payload Sparkplug com métrica `bdSeq` | `setupConnectors` |
  | **`DBIRTH`** por dispositivo | ✅ **Emite** — 1ª vez que cada `device_id` aparece na sessão (mapa `born_devices`), tópico `.../DBIRTH/{gateway_id}/{device_id}` | `DeliveryProcessor`, ramo `msg.payload.data` |
  | **`DDATA`** | ✅ **Emite** — tópico `.../DDATA/{gateway_id}/{device_id}`, `seq` rolando `(seq+1) % 256` (global `spb_seq`), `properties.engUnit` quando há unidade | `DeliveryProcessor` |
  | Convenção de tópico | ✅ `group_id = {Enterprise}_{Site}` ; `edge_node_id = gateway_id` ; `device_id = area_line_equipment` do `asset_context` | — |
  | Libs | ✅ `sparkplug-payload` (schema Sparkplug B da Eclipse) + `mqtt` (mqtt.js) | — |
  | Retenção quando o broker cai | ✅ **Esboço já cabeado** — `retentionRouter` faz `POST` do payload para `sida-core /api/buffer`; na reconexão, `waitNBirth` (delay 2 s) → `pullBuffer` (`GET /api/buffer/flush`) → `bufferDistributor` reinjeta os pacotes retidos. **Fora do escopo desta etapa** (ver Fronteira 3) — atenção: as URLs apontam para `sida-core:8080`, mas o `sida-core` HTTP é `:8000` (divergência pré-existente, não é tarefa deste loop corrigir). |

  **Delta de conformidade da Etapa 1A (o único trabalho do plano A neste loop):**
  1. **`bdSeq` de sessão.** Hoje o `bdSeq` do LWT é **fixo em `0`** e o `NBIRTH` **não carrega** a métrica `bdSeq`. Falta: um contador de sessão que incrementa a cada conexão e é **o mesmo** no `NBIRTH` e no `NDEATH`/LWT daquela sessão.
  2. **Aliases.** Hoje o `DDATA` reenvia o `name` de cada métrica e o `DBIRTH` reenvia **valores**. Falta: `DBIRTH` declarar as **definições** de métrica com `alias` inteiro; `DDATA` referenciar **apenas** o `alias`.
  3. **`NDEATH` gracioso.** Hoje o `node.on('close')` de `setupConnectors` só faz `client.end()`. Falta: publicar um `NDEATH` explícito (mesmo `bdSeq` da sessão) **antes** de desconectar, para encerramento limpo (`SIGTERM`) — o LWT cobre apenas a queda abrupta.
  4. **`schemas/sparkplug_b.proto`.** A pasta `schemas/` só tem `README.md`. Falta: versionar o `.proto` Sparkplug B v3.0.0 (Eclipse) como fonte da verdade.
  5. *(menor)* Auditar a contabilidade de `seq` entre `NBIRTH`/`DBIRTH`/`DDATA` (hoje `seq=0` no `NBIRTH`, `(seq+1)%256` depois; garantir que não há salto/reuso) e reagir a `Node Control/Rebirth = true` (rebirth sob demanda de um *primary host*), se conveniente.
- **Plano B é *greenfield*** no `sida-core`. Estrutura atual relevante:
  - `internal/core/domain/manifest.go` — modelos; `internal/core/ports/repository.go` — `ManifestRepository`, `BufferRepository`.
  - `internal/core/services/` — `auth_service.go`, `zmq_service.go` (socket **PUB** ZeroMQ, `NewZMQPublisher("0.0.0.0:5556")`, tópico `sida/manifest/{gatewayID}`, consumido pelo `ontology-builder` via `ZMQ_ENDPOINT=tcp://sida-core:5556`).
  - `internal/adapters/repository/` — SQLite via `github.com/mattn/go-sqlite3`, DB em `./data/sida_config.db` (`?_journal_mode=WAL&_busy_timeout=5000`, `SetMaxOpenConns(1)`), `CREATE TABLE IF NOT EXISTS` inline no construtor de cada repositório.
  - `internal/api/routes.go` — grupo `apiSystem := router.Group("/api/system")` com `/info` e `/setup` (o endpoint novo `GET /api/system/peers` entra aqui). HTTP na porta `8000`.
  - `cmd/server/main.go` — carrega `/app/data/.env` (`godotenv`), abre SQLite, sobe o `ZMQPublisher`, monta o router `gin`, trata `SIGINT`/`SIGTERM` com *shutdown* de 5 s.
  - `go 1.26.3`; deps já presentes: `github.com/pebbe/zmq4 v1.4.0`, `google.golang.org/protobuf v1.36.10`, `github.com/joho/godotenv`.
- **`T0.3` (portabilidade ARM64) já foi validada** — compatibilidade da pilha, incluindo bindings ZeroMQ, confirmada no Raspberry Pi.

O loop **expande** esses componentes — não reescreve o caminho de dados da v2.0 (`ingestion → context ISA-95 → delivery`). O `context` **não deve precisar de alteração**.

---

## 1. OBJETIVO DO LOOP

**Frase de missão (colável em prompt de implementação):**

> Evoluir o SIDA para operar como uma **frota descentralizada de gateways Raspberry Pi sem nó central de borda**, entregando dois planos de coordenação simultâneos: **(A)** o **ciclo de vida Sparkplug B** na camada de *delivery* **já emite `NBIRTH`, `DBIRTH`, `DDATA` e `NDEATH` (via LWT)** — o trabalho é fechar o **delta de conformidade**: `bdSeq` de sessão que correlacione `NBIRTH` ↔ `NDEATH`/LWT (hoje fixo em `0` e ausente no `NBIRTH`), `DDATA` **por alias** com as definições de métrica declaradas no `DBIRTH` (hoje por `name`), `NDEATH` **gracioso** no encerramento limpo (hoje só o LWT cobre a queda abrupta), e o `schemas/sparkplug_b.proto` versionado como fonte da verdade; e **(B)** implementar no `sida-core` (Go) uma **malha *peer-to-peer* ZeroMQ dedicada** entre os `sida-core` da frota, com registro de pares (`ConnectedControllers`), *probes* periódicos, detecção **local** de queda de par por *timeout* e primitivas de roteamento *controller-to-controller* do InterEdge, expostas em `GET /api/system/peers`. Parametrizar a `docker-compose.yml` por `.env` para que a mesma pilha suba em qualquer nó trocando apenas a identidade. Provar a eliminação do SPOF de borda por **injeção de falha**: derrubar um nó e verificar que os sobreviventes seguem publicando, que o broker recebe o `NDEATH` do nó caído (plano A) e que os pares detectam o *timeout* localmente (plano B) — sem intervenção manual e sem alterar o caminho de dados homologado na v2.0.

**Resultado concreto esperado:**
- `core/delivery/flows.json` com o ciclo de vida Sparkplug B **já existente** ajustado para **conformidade** (verificável com `mosquitto_sub -t 'spBv1.0/#' -v`): `NBIRTH` passa a carregar a métrica `bdSeq` (`seq=0`); `DBIRTH` passa a declarar `alias` por métrica; `DDATA` passa a referenciar **apenas aliases**; `NDEATH` no encerramento **gracioso** (novo) além do já existente via LWT em queda abrupta, ambos com **o mesmo `bdSeq` da sessão**.
- `schemas/sparkplug_b.proto` (Sparkplug B v3.0.0 da Eclipse Foundation) versionado como *single source of truth*.
- `sida-core` com um novo serviço de **malha de pares** (`peer_service.go`), modelo de domínio `ControllerRegister`, tabela SQLite `controllers`, e o endpoint `GET /api/system/peers` retornando registro + *liveness* local.
- `docker-compose.yml` parametrizada por `.env` (interpolação `${VAR}`), com `.env.example` e uma tabela de identidades para ≥ 3 nós em `deploy/fleet/`.
- Um pacote de testes em `test/etapa1/` que sobe uma frota local (3 nós + Mosquitto isolado), executa a injeção de falha e emite um relatório de métricas (tempo-até-`NDEATH`, tempo-até-detecção-de-par, perda nos sobreviventes, *overhead* CPU/RAM por nó).
- Um `progress.json` persistente (fora da imagem, versionado) registrando o avanço de cada task, para retomada após interrupção — com **um commit `[T…]` na branch `interedge` por task concluída** (seção 3.3.1).

---

## 2. FRONTEIRAS (O QUE NÃO FAZER)

A IA que executar este loop **não pode, em hipótese alguma**:

1. **Alterar o caminho de dados da v2.0.** Os flows `core/ingestion/flows.json` e `core/context/flows.json` **não são tocados**. Em `core/delivery/flows.json`, o trabalho é o **delta de conformidade do ciclo de vida** (item 0.1) — não reescrever `DeliveryProcessor`/`setupConnectors`: o `DDATA` continua carregando exatamente as mesmas métricas que o `context` entrega (mesmo `asset_context` ISA-95, mesmos nomes/tipos/unidades), apenas referenciadas por `alias`. O SIDA-core mantém suas rotas e serviços atuais; o plano B é **adição**, não refatoração.
2. **Reutilizar o socket ZeroMQ de manifesto `tcp://sida-core:5556`** (PUB/SUB, tópico `sida/manifest/*`, consumido pelo `ontology-builder`) para o plano leste-oeste. O peer-mesh usa **socket e porta dedicados** (`PEER_PORT`, default `5557`), com papel próprio (`ROUTER`/`DEALER`).
3. **Mexer no *store-and-forward*.** O esboço de retenção já cabeado na *delivery* (`retentionRouter` → `sida-core /api/buffer` → `pullBuffer`/`bufferDistributor` na reconexão) **não é completado, hardeneado nem removido** neste loop — é roadmap separado (`historico-decisoes` §9). Não corrigir a divergência de porta `:8080`→`:8000` das URLs de buffer como parte desta etapa. O ciclo de vida (novo `bdSeq`/aliases/`NDEATH` gracioso) não deve **depender** desse caminho nem quebrá-lo. Se o broker estiver offline durante o teste de aceite, o `DDATA` daquele período pode ser perdido — a Etapa 1 mede **continuidade dos sobreviventes**, não recuperação do nó caído.
4. **Tornar o broker de nuvem redundante** ou introduzir um segundo broker no plano de dados. O UNS na nuvem continua o ponto único de convergência de **dados** — isso é inerente ao padrão UNS e está **fora do escopo de SPOF**, que aqui é só o **plano de borda**.
5. **Adicionar TLS/mTLS** ao MQTT, ao IPC ZeroMQ ou à malha de pares; **trocar o PIN** (`EDGE_ENGINEER_PIN` → token `session_<hash>`) por OAuth2/JWT. Segurança criptográfica é trabalho futuro declarado.
6. **Reimplementar literalmente as 5 camadas do InterEdge** (profile/register/service/control/physical) no RPi em paralelo ao SIDA. O enquadramento InterEdge × SIDA é **mapeamento arquitetural**; o plano B implementa apenas o **registro de pares + *probing* + roteamento *controller-to-controller***.
7. **Tratar failover de dados via par como requisito.** `RouteMessage` reencaminhando o `DDATA` de um nó sem broker para um par com conectividade é **extensão opcional (`T1B.6`)**, explicitamente fora do núcleo e **não** é critério de aceite. O núcleo do plano B é **consciência/coordenação de frota**.
8. **Quebrar a conformidade Sparkplug B:** nunca publicar `DATA` sem o `BIRTH` da sessão; o `bdSeq` do `NBIRTH` **tem** de ser igual ao do `NDEATH`/LWT da mesma sessão; `seq` contínuo e rolando `mod 256`; `DDATA` referenciando **apenas** aliases declarados no `DBIRTH`.
9. **Dar controle/atuação a dispositivos de campo** nem mexer em ingestão de Classe 0/1 — isso é a **Etapa 2**, com SDD próprio.
10. **Contornar falha de portabilidade ARM64.** Se os bindings nativos (`pebbe/zmq4`/`libzmq` no Go; `sparkplug-payload`/`mqtt` no Node-RED) falharem em algum RPi, **parar e reportar** — não trocar a biblioteca de transporte nem o formato do payload para "resolver".
11. **Hardcodar identidade.** `EDGE_GATEWAY_ID`, `GROUP_ID`, `CONTROLLER_ID`, `PEER_PORT`, `PEERS`, `BROKER_URL`, `EDGE_ENGINEER_PIN` vêm **sempre** de `.env` — nunca fixos em código, imagem ou `flows.json`.

**Se a IA "resolver" o problema de um jeito indesejado** (ex.: simular o `NDEATH` publicando manualmente em vez de configurar o LWT real do broker; pular aliases "para simplificar"; reusar o `:5556`; persistir histórico para "não perder dados"; embutir a identidade de um nó específico), isso é **falha da task**, não conclusão — a task é revertida e refeita respeitando as fronteiras acima.

---

## 3. MÉTRICA DE CONCLUSÃO (CRITÉRIO DE PARADA)

### 3.1 Teste de aceite final

O loop é considerado concluído quando um script de teste automatizado (`test/etapa1/test_fault_injection.py`), executado contra uma **frota local de 3 nós** e um **Mosquitto local isolado** (sem qualquer relação com o broker de produção do GCP), cumpre integralmente:

1. **Frota íntegra (t0).** Sobe os 3 nós (`edge_001`, `edge_002`, `edge_003`), cada um com a pilha completa e o seu `.env`. Confirma:
   - `mosquitto_sub -t 'spBv1.0/#' -v` mostra, para cada nó, `NBIRTH` (com métrica `bdSeq` e `seq=0`) → `DBIRTH` (métricas com `alias` e, quando houver, `properties.engUnit`) → `DDATA` (referenciando **aliases**, `seq` contínuo) — ao menos duas métricas por dispositivo, uma numérica e uma booleana.
   - `GET http://<nó>:8000/api/system/peers` em cada nó lista os outros dois com `state = "alive"`.
2. **Injeção de falha (t1).** Derruba o `edge_002` (`docker stop` do seu `sida-core` **e** do seu `delivery`, ou do nó inteiro) e cronometra.
3. **Verificação do plano A (norte).** O broker publica **automaticamente** o `NDEATH` de `edge_002` no tópico `spBv1.0/{group_id}/NDEATH/edge_002`, com o **mesmo `bdSeq`** do último `NBIRTH` de `edge_002` (LWT disparado pelo broker). Registra `t_ndeath`.
4. **Verificação do plano B (leste-oeste).** Em `edge_001` e `edge_003`, `GET /api/system/peers` passa a reportar `edge_002` com `state = "down"` dentro de `PROBE_INTERVAL_MS × PEER_DOWN_AFTER_MISSES`. Registra `t_peer_detect` (medido **localmente** em cada nó, relógio monotônico).
5. **Continuidade dos sobreviventes.** `edge_001` e `edge_003` **seguem publicando `DDATA`** durante e após a falha, sem intervenção manual, sem *rebirth* espúrio e **sem perder nenhum intervalo de publicação** (perda = 0 nos sobreviventes). O histórico/estado próprio dos sobreviventes não é afetado.
6. **Religamento (t2).** Sobe `edge_002` novamente. Ele emite um **novo `NBIRTH` com `bdSeq` incrementado**; `edge_001` e `edge_003` voltam a reportá-lo como `"alive"`.
7. **Relatório de métricas.** O script emite `test/etapa1/report.json` com: `t_ndeath`, `t_peer_detect` (por nó observador), contagem de perdas nos sobreviventes (deve ser `0`), e *overhead* de CPU/RAM por container (`docker stats` amostrado).

### 3.2 Ciclo de correção

Quando a verificação falhar, a IA segue o ciclo: **ler o erro → identificar a causa → corrigir → repetir o teste**.

**Número máximo de tentativas antes de escalar para o humano: 5.** Na 6ª falha consecutiva do mesmo teste, a IA para, registra em `progress.json` a causa raiz suspeita e as tentativas já feitas, e aguarda intervenção humana — nunca prossegue para a próxima task com esse teste ainda vermelho.

### 3.3 Estrutura de Sprints e Tasks (obrigatório para o loop)

O esforço é dividido em **4 sprints**, num total de **22 tasks** granulares. Cada task só é marcada `concluida` após cumprir o **checkpoint da seção 3.3.1** (teste funcional verde + `progress.json` atualizado + um commit), antes de a IA seguir para a próxima. Os IDs `T…` referenciam o Guia de Implementação do Ciclo V3.0.

| Sprint | Foco | Tasks | Critério de saída do sprint |
|---|---|---|---|
| **S1** | Fundação: identidade parametrizada + schema + baseline preservada | `T0.4`, `T1A.1`, `T3.1` | `docker-compose --env-file deploy/fleet/edge_001.env up` sobe os contêineres de **um** nó sem erro de arquitetura; o pipeline v2.0 (Modbus → ISA-95 → Sparkplug B → broker de teste) continua funcionando; `schemas/sparkplug_b.proto` versionado; nenhuma identidade hardcoded |
| **S2** | Plano A — **delta de conformidade** do ciclo de vida Sparkplug B (já emitido hoje; ver 0.1). Escopo: `bdSeq` de sessão, aliases no `DBIRTH`/`DDATA`, `NDEATH` gracioso, `.proto` | `T1A.2`–`T1A.7` | `mosquitto_sub -t 'spBv1.0/#' -v`: subida mostra `NBIRTH`(`seq=0`, **agora com métrica `bdSeq=N`**) → `DBIRTH`(**agora com `alias` por métrica**) ; operação mostra `DDATA` **por alias** com `seq` contínuo ; `docker kill` → `NDEATH`(`bdSeq=N`) via LWT (**já funciona hoje — validar correlação**) ; `docker stop` → `NDEATH` gracioso explícito (**novo**) |
| **S3** | Plano B — malha *controller-to-controller* (plano leste-oeste) | `T1B.1`–`T1B.5` | Dois `sida-core` trocam uma mensagem de teste pela malha ZeroMQ dedicada ; ao derrubar um par, o outro marca `down` dentro do intervalo configurado ; `GET /api/system/peers` reflete o registro e o *liveness* local |
| **S4** | Frota multi-RPi + demonstração de resiliência | `T3.2`, `T3.3`, `T4.1`–`T4.6` | Os 3 nós ativos simultaneamente nos dois planos ; os 7 passos do teste de aceite (3.1) passam ; `report.json` gerado |

O **critério de saída do sprint** é uma checagem **integradora**, verificada **depois** que todas as tasks do sprint estão `concluida` e commitadas — não substitui os checkpoints por task.

### 3.3.1 Checkpoint obrigatório por task concluída (Definition of Done)

Nenhuma task avança para a próxima sem cumprir, **nesta ordem**, os três passos abaixo. Uma task só é `concluida` quando os três passam:

1. **Teste funcional verde.** Cada task tem um **teste funcional automatizado** próprio (comportamento observável ponta a ponta, não teste de unidade isolado), nomeado na tabela 3.3.2 (`arquivo::caso`). Ele roda contra a **frota local de teste** (`test/etapa1/compose.test.yml` + Mosquitto isolado) e **deve passar**. Os testes das tasks já concluídas **continuam verdes** — rodar a suíte acumulada do sprint corrente a cada checkpoint (sem regressão).
2. **`progress.json` atualizado.** Marcar a task `concluida` com timestamp, no mesmo passo (contrato da seção 3.4).
3. **Um commit por task.** Criar **exatamente um commit** na branch de trabalho (`interedge`) contendo o código/artefatos da task, o(s) teste(s) funcional(is) dela e o `progress.json` atualizado. Mensagem: `<tipo>(<escopo>): <descrição curta> [<ID da task>]` (ex.: `feat(delivery): bdSeq de sessão correlacionando NBIRTH e NDEATH/LWT [T1A.2]`), seguindo a convenção de commits e o trailer de atribuição vigentes no projeto. **Não** fazer squash das tasks nem emendar (`--amend`) commits de tasks já concluídas.

**Se o teste funcional não passar em até 5 tentativas** (seção 3.2): a task fica `bloqueada` em `progress.json` (causa raiz suspeita + nº de tentativas), **nenhum commit é feito** para ela, e o loop para para intervenção humana.

**Se uma task já commitada se revelar incorreta depois** (violou uma fronteira da seção 2, ou quebrou um teste anterior): **reverter** com um novo commit (`git revert` ou correção referenciando o `[ID da task]`) e refazê-la — nunca reescrever o histórico de tasks anteriores.

### 3.3.2 Detalhamento das tasks (entrega + teste funcional + commit)

Os IDs `T…` referenciam o Guia de Implementação do Ciclo V3.0; as colunas *Entrega* e *Teste funcional* derivam das seções 5 e 6 deste SDD. Todos os testes rodam contra a frota local isolada.

**S1 — Fundação**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T0.4` | Harness de frota local: `test/etapa1/compose.test.yml` (esqueleto de 3 nós + Mosquitto isolado) e smoke da baseline v2.0 | `test_s1_foundation.py::test_baseline_v2_pipeline` — sobe 1 nó com a imagem atual **sem alterações**, injeta uma leitura Modbus simulada, confirma `DDATA` em `spBv1.0/#` no Mosquitto isolado (pipeline Modbus→ISA-95→Sparkplug intacto) | `test(etapa1): harness de frota local + smoke da baseline v2.0 [T0.4]` |
| `T1A.1` | `schemas/sparkplug_b.proto` (Sparkplug B v3.0.0 da Eclipse) + `schemas/README.md` apontando para ele | `test_s1_foundation.py::test_sparkplug_proto_valido` — `protoc --proto_path=schemas -o /dev/null schemas/sparkplug_b.proto` retorna 0 e o descriptor contém `Payload`, `Payload.Metric`, `Payload.Template` | `feat(schemas): sparkplug_b.proto v3.0.0 como fonte da verdade [T1A.1]` |
| `T3.1` | `docker-compose.yml` com interpolação `${VAR}` (identidade/pares/broker/PIN em `sida-core` e `poc-delivery`, porta `${PEER_PORT}` publicada) + `.env.example` + `deploy/fleet/edge_001.env` | `test_s1_foundation.py::test_compose_parametrizado` — `docker compose --env-file deploy/fleet/edge_001.env config` resolve sem `variable is not set`, mostra `EDGE_GATEWAY_ID=edge_001` e a porta do peer-mesh; `grep -RniE` não acha identidade hardcoded em `sida-core/`/`core/`; `up -d` sobe 1 nó sem erro de arquitetura e o smoke `T0.4` segue verde | `feat(deploy): compose parametrizado por .env + deploy/fleet [T3.1]` |

**S2 — Plano A (delta de conformidade Sparkplug B)**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T1A.2` | Contador `bdSeq` de sessão no contexto do fluxo (`(bdSeq_ant+1) mod 2⁶⁴`, `0` na 1ª sessão do processo) e sua injeção no **LWT** de `setupConnectors` (`qos 1`, `retain false`) | `test_plane_a_lifecycle.py::test_bdseq_sessao_no_lwt` — assina `NBIRTH`/`NDEATH`; após uma reconexão MQTT forçada, o `bdSeq` do LWT publicado pelo broker é igual ao do último `NBIRTH` da mesma sessão e incrementou em relação à sessão anterior | `feat(delivery): bdSeq de sessão no LWT/NDEATH [T1A.2]` |
| `T1A.3` | Métrica `bdSeq` no `NBIRTH` (= valor da sessão, `seq=0`); limpeza de `alias_map`/`born_devices`/`seq` e `node_state=birthed` a cada `NBIRTH` | `test_plane_a_lifecycle.py::test_nbirth_bdseq_e_reset` — `NBIRTH` carrega `bdSeq` == `bdSeq` do LWT; após reconexão, `DBIRTH` é reemitido para todos os devices ativos (mapas limpos) | `feat(delivery): bdSeq no NBIRTH e reset de estado da sessão [T1A.3]` |
| `T1A.4` | `DBIRTH` passa a declarar **definições** de métrica (`name`, datatype Sparkplug, `alias` inteiro único no nó gravado em `alias_map`), mantendo `properties.engUnit` | `test_plane_a_lifecycle.py::test_dbirth_define_aliases` — `DBIRTH` de `Line_1/Pump_01` traz `Temperature` (alias inteiro, `engUnit="°C"`) e `Running` (alias distinto), como definições e não valores | `feat(delivery): DBIRTH declara definições de métrica com alias [T1A.4]` |
| `T1A.5` | `DDATA` referencia cada métrica **apenas por `alias`** (sem `name`), resolvido em `alias_map`; emite `DBIRTH` primeiro se o device chega sem birth na sessão | `test_plane_a_lifecycle.py::test_ddata_por_alias` — todo `DDATA` capturado tem `alias` e **não** tem `name`; os aliases batem com os do `DBIRTH`; nenhum `DDATA` antes do `DBIRTH` da sessão | `feat(delivery): DDATA por alias [T1A.5]` |
| `T1A.6` | `NDEATH` gracioso em `node.on('close')`/`SIGTERM`: publica `NDEATH` explícito (`bdSeq` da sessão, `seq` próximo) **antes** de `client.end()`; `node_state=dead` | `test_plane_a_lifecycle.py::test_ndeath_gracioso` — `docker stop` (SIGTERM) gera um `NDEATH` explícito com o `bdSeq` da sessão e encerra a conexão limpa; o LWT **não** dispara em duplicidade | `feat(delivery): NDEATH gracioso no encerramento limpo [T1A.6]` |
| `T1A.7` | Auditoria da contabilidade de `seq` (`NBIRTH=0 → DBIRTH → DDATA…`, rolagem `255→0` sem salto/reuso, `bdSeq` inalterado na rolagem); reação opcional a `Node Control/Rebirth=true` | `test_plane_a_lifecycle.py::test_contabilidade_seq` — captura > 256 mensagens de uma sessão e verifica `seq` contínuo `mod 256`, sem lacuna nem repetição, `bdSeq` constante | `test(delivery): auditoria de seq e rolagem mod 256 [T1A.7]` |

**S3 — Plano B (malha *controller-to-controller*)**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T1B.1` | `sida-core/internal/core/domain/controller.go` (`ControllerRegister`, `PeerRef`, `Envelope`, `LivenessState`) + `ports.PeerRepository`; parsing de `PEERS` (`id@host:port,…`) | `test_plane_b_peermesh.py::test_registro_carrega_de_env` — `sida-core` sobe com `PEERS=edge_002@…,edge_003@…` e loga `peer register: 2 pares`; sobe igual com `PEERS` vazio (0 pares); `go test ./internal/core/domain/...` verde | `feat(sida-core): domínio ControllerRegister + PeerRepository [T1B.1]` |
| `T1B.2` | `adapters/repository/sqlite_peer.go` — tabela `controllers` no `sida_config.db` (WAL, `CREATE TABLE IF NOT EXISTS` no construtor), CRUD do registro | `test_plane_b_peermesh.py::test_persistencia_controllers` — após o boot, `controllers` existe (`.tables`), `journal_mode=wal`; `docker restart` do `sida-core` preserva o registro de pares | `feat(sida-core): repositório SQLite da tabela controllers [T1B.2]` |
| `T1B.3` | `peer_service.go` — `bind` `ROUTER` em `PEER_PORT` (5557), `DEALER` por par, `WriteMessage`/`RouteMessage`/`ReadMessage`, `MessageBuffer` por remetente | `test_plane_b_peermesh.py::test_troca_mensagem_mesh` — em 2 `sida-core`, A `WriteMessage(B, payload)` e B recebe o payload íntegro via `ReadMessage()`; a troca usa `:5557` e o `:5556` (PUB de manifesto) segue intacto | `feat(sida-core): malha ZeroMQ ROUTER/DEALER + primitivas InterEdge [T1B.3]` |
| `T1B.4` | Loop de `probe` (`ticker` em `PROBE_INTERVAL_MS`), FSM `alive→suspect→down` (relógio monotônico, `PEER_DOWN_AFTER_MISSES`) e `GET /api/system/peers` no grupo `apiSystem` | `test_plane_b_peermesh.py::test_probe_e_liveness` — frota de 3 nós (`1000`/`3`): t0 todos `alive`; `docker stop edge_002` → em ≤ ~3 s `edge_001` e `edge_003` reportam `edge_002` `down` (via `suspect`), com `missed`/`last_ack_ms` coerentes | `feat(sida-core): probe loop, FSM de liveness e GET /api/system/peers [T1B.4]` |
| `T1B.5` | Wiring em `cmd/server/main.go`: sobe o `peer_service` no boot, encerra a malha no `shutdown` (`SIGTERM`), sem tocar no `ZMQPublisher` `:5556` nem nas rotas existentes | `test_plane_b_peermesh.py::test_wiring_e_shutdown` — boot loga peer-mesh em `:5557` e o `ontology-builder` ainda recebe manifesto por `:5556`; `/api/system/info` segue `200`; `docker stop` encerra a malha em ≤ 5 s sem vazar goroutine | `feat(sida-core): wiring do peer_service no ciclo de vida do servidor [T1B.5]` |

**S4 — Frota multi-RPi + resiliência**

| Task | Entrega | Teste funcional (`arquivo::caso`) | Commit (sugestão) |
|---|---|---|---|
| `T3.2` | `deploy/fleet/identities.md` + `edge_001.env … edge_003.env` completos (3 nós, `PEERS` cruzados, `CONTROLLER_ID`/`EDGE_GATEWAY_ID` distintos) | `test_fleet.py::test_frota_3_nos` — os 3 nós sobem sem colisão de porta/rede; `GET /api/system/peers` em cada nó lista os outros dois | `feat(deploy): identidades da frota de 3 nós com PEERS cruzados [T3.2]` |
| `T3.3` | `test/etapa1/compose.test.yml` final (3 nós + Mosquitto isolado) + `README-etapa1.md` | `test_fleet.py::test_compose_test_isolado` — `docker compose -f test/etapa1/compose.test.yml up -d` sobe frota + Mosquitto; `mosquitto_sub -t 'spBv1.0/#'` recebe tráfego dos 3 nós; nenhuma referência ao broker do GCP | `test(etapa1): compose de teste frota + Mosquitto isolado [T3.3]` |
| `T4.1` | Suíte funcional consolidada do plano A (`test_plane_a_lifecycle.py`, casos 1–3 e 8) verde na frota de teste | `pytest test/etapa1/test_plane_a_lifecycle.py` — todos os casos verdes na frota de 3 nós | `test(etapa1): suíte funcional do plano A [T4.1]` |
| `T4.2` | Suíte funcional consolidada do plano B (`test_plane_b_peermesh.py`, casos 4, 6, 7, 9) verde | `pytest test/etapa1/test_plane_b_peermesh.py` — todos os casos verdes, inclusive partição parcial (caso 7) e colisão de identidade (caso 9) | `test(etapa1): suíte funcional do plano B [T4.2]` |
| `T4.3` | `test_fault_injection.py` — passos 1–2 de 3.1: frota íntegra em t0 (dois planos verdes) + injeção de falha em t1 com cronometragem | `test_fault_injection.py::test_frota_integra_e_injecao` — em t0 os sinais do passo 1 conferem; `docker stop edge_002` registra `t1` | `test(etapa1): harness de injeção de falha (t0 + derrubada) [T4.3]` |
| `T4.4` | Verificação dos dois planos sob falha (passos 3–5 de 3.1): `NDEATH` via LWT com `bdSeq` casado (A); pares marcam `down` dentro de `PROBE_INTERVAL_MS × PEER_DOWN_AFTER_MISSES` (B); sobreviventes publicam sem perda | `test_fault_injection.py::test_deteccao_dois_planos` — `t_ndeath` e `t_peer_detect` (por observador) capturados; perdas nos sobreviventes `== 0`; sem `rebirth` espúrio | `test(etapa1): verificação dos dois planos sob falha [T4.4]` |
| `T4.5` | Verificação de religamento (passo 6): `edge_002` volta, emite novo `NBIRTH` com `bdSeq` incrementado; pares o remarcam `alive` | `test_fault_injection.py::test_religamento` — novo `NBIRTH` de `edge_002` com `bdSeq` maior que o anterior; `GET /api/system/peers` volta a `alive` nos observadores | `test(etapa1): verificação de religamento e rebirth [T4.5]` |
| `T4.6` | Geração de `test/etapa1/report.json` (passo 7): `t_ndeath`, `t_peer_detect` por observador, perdas (`0`), overhead CPU/RAM por container (`docker stats`). **Fecha o teste de aceite 3.1.** | `test_fault_injection.py::test_report_e_aceite` — o cenário completo de 3.1 roda ponta a ponta, `report.json` valida contra o schema esperado e `perdas == 0` | `feat(etapa1): report.json de métricas da injeção de falha [T4.6]` |

### 3.4 Registro de progresso (para interrupção/retomada)

A IA **deve** manter um arquivo `progress.json` na raiz do projeto (fora das imagens Docker, versionado), atualizado **imediatamente após cada task concluída**, com este contrato:

- Uma lista de tasks, cada uma com: identificador do sprint, identificador da task (`T…`), descrição curta, status (`pendente` | `em_andamento` | `concluida` | `bloqueada`), timestamp da última atualização, o hash do commit da task (quando `concluida`), e — se `bloqueada` — o motivo e o número de tentativas já feitas.

O `progress.json` e o **commit da task** (seção 3.3.1) são gravados no **mesmo checkpoint**: o estado de progresso confiável é o `progress.json` **cruzado com o `git log` da branch `interedge`** (um commit `[T…]` por task `concluida`). Uma task `concluida` sem commit correspondente — ou um commit `[T…]` sem a task `concluida` no `progress.json` — indica um checkpoint interrompido no meio; a IA completa o passo que faltou antes de seguir.

**Antes de iniciar qualquer trabalho em uma nova sessão**, a IA lê o `progress.json` **e** o `git log` da branch `interedge`, e retoma exatamente da primeira task sem checkpoint completo, sem repetir tasks já `concluida` e commitadas.

---

## 4. ESTADO DO SISTEMA

Estado **por nó** da frota. Nada aqui é compartilhado entre nós — cada `sida-core`/`delivery` mantém o seu.

| Variável | Onde vive | Tipo | Valores possíveis | Estado inicial |
|---|---|---|---|---|
| `sparkplug.bdSeq` | `delivery` (contexto do fluxo) | inteiro de sessão (0 … 2⁶⁴-1) | incrementa a cada nova conexão MQTT; `NBIRTH` e `NDEATH`/LWT da mesma sessão usam **o mesmo valor** | `0` na primeira sessão |
| `sparkplug.seq` | `delivery` (contexto do fluxo) | `uint8` rolando | `+1 mod 256` a cada mensagem após o `NBIRTH`; o `NBIRTH` reseta para `0` | `0` |
| `sparkplug.node_state` | `delivery` | enum | `offline`, `birthed`, `dead` | `offline` |
| `sparkplug.born_devices` | `delivery` (global) | mapa `device_id → bool` | marca que o `DBIRTH` daquele device já saiu **nesta sessão** | vazio |
| `sparkplug.alias_map` | `delivery` (global) | mapa `device_id/metric_name → alias` (inteiro único no nó) | atribuído no `DBIRTH`, usado no `DDATA` | vazio |
| `peer.registry` (`ConnectedControllers`) | `sida-core` (memória + SQLite `controllers`) | mapa `peer_id → {endpoint, probe_interval_ms}` | carregado do SQLite e/ou do env `PEERS` na subida | conforme `.env` |
| `peer.liveness` | `sida-core` (memória) | mapa `peer_id → {state, last_ack_monotonic, missed_count}` | `state ∈ {alive, suspect, down}`; `suspect` após 1 *probe* sem ACK; `down` após `PEER_DOWN_AFTER_MISSES` | `alive` ao carregar o registro |
| `peer.message_buffer` (`MessageBuffer`) | `sida-core` (memória) | mapa `sender_id → fila de Envelope` | seção **dedicada por remetente** (evita conflito de escrita concorrente — cf. InterEdge) | vazio |
| `peer.routing_table` | `sida-core` (memória, de `SourceDevices`/`DestinationDevices`) | mapa `source_device → destination_path ([]controller_id)` | preenchido do Controller Register | vazio |
| `node_identity` | env (`/app/data/.env` + compose) | struct | `EDGE_GATEWAY_ID`, `edge_node_id`, `GROUP_ID`, `BROKER_URL`, `EDGE_ENGINEER_PIN`, `CONTROLLER_ID`, `PEER_PORT`, `PEERS`, `PROBE_INTERVAL_MS`, `PEER_DOWN_AFTER_MISSES` | do `.env` do nó |
| `progress.json` (fora do runtime) | repositório | arquivo | lista de tasks com status | conforme seção 3.4 |

---

## 5. ALGORITMOS E REGRAS DE NEGÓCIO

### 5.1 Plano A — ciclo de vida Sparkplug B (plano norte, `core/delivery/flows.json`)

> **Já implementado** (ver 0.1): `NBIRTH`, `DBIRTH`, `DDATA` e `NDEATH` via LWT já são publicados por `setupConnectors` / `DeliveryProcessor`, com a convenção de tópico abaixo, `seq` rolando e `engUnit`. Os passos marcados **`[delta]`** são o trabalho da Etapa 1A; os marcados **`[mantém]`** já existem e só precisam ser preservados/validados.

Tópicos (mantêm a convenção atual): `group_id = {Enterprise}_{Site}` ; `edge_node_id = EDGE_GATEWAY_ID` ; `device_id` = concatenação `area_line_equipment` do `asset_context`.

1. **Ao conectar ao broker** (`setupConnectors`):
   - **`[delta]`** `bdSeq_sessão = (bdSeq_anterior + 1) mod 2⁶⁴`, persistido no contexto do fluxo (sobrevive à reconexão, não ao restart do container — aceitável). Hoje o valor é fixo em `0`.
   - **`[mantém]`** o **LWT** já é registrado em `spBv1.0/{group_id}/NDEATH/{edge_node_id}` com payload Sparkplug B contendo a métrica `bdSeq`. **`[delta]`**: esse `bdSeq` passa a ser `bdSeq_sessão` (não `0`); `qos: 1`, `retain: false`.
2. **`NBIRTH`** (após `connect`, `DeliveryProcessor` no ramo `connection_status`):
   - **`[mantém]`** já publica em `spBv1.0/{group_id}/NBIRTH/{edge_node_id}` com `seq = 0` e a métrica `Node Control/Rebirth = false`.
   - **`[delta]`** incluir a métrica `bdSeq` (= `bdSeq_sessão`, **igual ao do LWT**) e limpar também o `alias_map` (hoje só zera `born_devices` e `spb_seq`). `node_state = birthed`.
3. **`DBIRTH`** (primeira vez que um `device_id` aparece na sessão — lógica de `born_devices` **`[mantém]`**):
   - **`[mantém]`** tópico `spBv1.0/{group_id}/DBIRTH/{edge_node_id}/{device_id}`; `seq` = próximo valor; `properties.engUnit` quando a métrica trouxer unidade.
   - **`[delta]`** o payload passa a ser as **definições** de cada métrica (`name`, `type` datatype Sparkplug, `alias` inteiro único no nó gravado em `alias_map`) — hoje reenvia valores.
4. **`DDATA`** (cada leitura subsequente do device):
   - **`[mantém]`** tópico `spBv1.0/{group_id}/DDATA/{edge_node_id}/{device_id}`; `seq` = próximo valor.
   - **`[delta]`** cada métrica referenciada **por `alias`** (resolvido em `alias_map`), **sem `name`** — hoje reenvia `name`. Se um `device_id` chega sem `DBIRTH` prévio na sessão (corrida na conexão), emitir o `DBIRTH` primeiro **`[mantém]`**.
5. **`NDEATH` gracioso** **`[delta]`** (`node.on('close')` / `SIGTERM`): publicar explicitamente `NDEATH` em `spBv1.0/{group_id}/NDEATH/{edge_node_id}` com `bdSeq = bdSeq_sessão` e `seq` = próximo valor, **antes** de encerrar o cliente MQTT. Hoje o `close` só faz `client.end()`. `node_state = dead`.
6. **`NDEATH` abrupto** **`[mantém]`**: em `docker kill`/`SIGKILL`/queda de energia/perda de rede, o **broker** publica o LWT automaticamente. Nenhum código adicional — só garantir que o LWT do passo 1 carrega o `bdSeq_sessão`.
7. **Rolagem de `seq`** **`[mantém]` / `[delta: auditar]`**: ao passar de `255`, volta a `0` e continua; `bdSeq_sessão` **não** muda. Consumidores não interpretam isso como *rebirth*. Auditar a sequência `NBIRTH(0) → DBIRTH → DDATA…` para garantir que não há salto nem reuso de `seq`.
8. **`schemas/sparkplug_b.proto`** **`[delta]`**: versionar como fonte da verdade do contrato (Sparkplug B v3.0.0 da Eclipse). Serve de referência para revisão/validação e para consumidores/plano B; o Node-RED continua usando o schema embutido na lib `sparkplug-payload` (equivalente).

### 5.2 Plano B — coordenação leste-oeste (`sida-core`, InterEdge)

1. **Inicialização** (`cmd/server/main.go`): carregar o `ControllerRegister` do SQLite (`controllers`) e completar/sobrepor com o env `PEERS` (`id@host:port,…`). Fazer `bind` de um socket **`ROUTER`** em `tcp://0.0.0.0:{PEER_PORT}` (default `5557`) e abrir um **`DEALER`** para cada par de `ConnectedControllers`. **Distinto** do `PUB` de manifesto em `:5556`.
2. **Loop de *probe*** (goroutine com *ticker* em `ProbeIntervalMs`): enviar `PROBE{from, seq, ts}` a cada par e aguardar `PROBE_ACK`. FSM de *liveness*: `alive` → `suspect` após 1 intervalo sem ACK → `down` após `PEER_DOWN_AFTER_MISSES` intervalos sem ACK. Qualquer `PROBE_ACK` recebido devolve o par a `alive`. O *timeout* de par é o **sinal de queda leste-oeste — independente do LWT da nuvem** e medido em relógio **monotônico** local.
3. **Mensageria (primitivas do InterEdge, adaptadas a Go):**
   - `Envelope{ Path []ControllerID, Payload []byte, TS int64 }` — mensagem = **dados + caminho** (cadeia de IDs de controlador terminando no destino).
   - `WriteMessage(dst, payload)` — monta o `Path` a partir de `DestinationDevices` do Controller Register.
   - `RouteMessage(env)` — lê o **próximo `ControllerID`** do `Path`; se ≠ ao `CONTROLLER_ID` próprio, encaminha ao `DEALER` do próximo salto; senão, entrega local.
   - `ReadMessage()` — drena o `MessageBuffer` (seção por remetente).
4. **Exposição**: `GET /api/system/peers` (no grupo `apiSystem` de `routes.go`) retorna
   `{ "controller_id": "...", "peers": [ { "id": "...", "endpoint": "...", "state": "alive|suspect|down", "last_ack_ms": <int>, "missed": <int> } ] }`.
   Opcionalmente, publicar o mesmo resumo no UNS para o *dashboard* (não obrigatório).
5. **Persistência**: tabela `controllers` no **mesmo** `sida_config.db` (WAL), criada via `CREATE TABLE IF NOT EXISTS` no construtor do novo repositório, seguindo o padrão de `sqlite_repository.go`. Colunas espelham o Controller Register do InterEdge (ver 6.2).
6. **O plano B não publica no UNS e não depende do broker.** Se o broker de nuvem estiver inacessível para este nó, os *probes* entre pares alcançáveis continuam normalmente.
7. **`T1B.6` (opcional, fora do núcleo — não é aceite):** se o broker estiver inacessível a este nó, `RouteMessage` **pode** encaminhar o `DDATA` a um par com conectividade que o republica no UNS. Marcado como extensão; encosta no *store-and-forward* (roadmap).

### 5.3 Identidade e frota (`docker-compose.yml` + `.env`)

1. Cada nó recebe via `--env-file` (ou `/app/data/.env`): `EDGE_GATEWAY_ID` (= `edge_node_id` Sparkplug), `GROUP_ID`, `BROKER_URL`, `EDGE_ENGINEER_PIN`, `CONTROLLER_ID`, `PEER_PORT`, `PEERS`, `PROBE_INTERVAL_MS`, `PEER_DOWN_AFTER_MISSES`.
2. A `docker-compose.yml` passa a usar interpolação `${VAR:-default}` para essas chaves — **sem** mudar a topologia de serviços, nomes de rede (`sida_network`), volumes (`sida_ipc`, `./sida-core/data`) nem o caminho de dados. Adiciona-se a porta `${PEER_PORT}` ao serviço `sida-core` e as variáveis de identidade aos serviços `sida-core` e `poc-delivery`.
3. `deploy/fleet/identities.md` documenta a tabela de identidades dos ≥ 3 nós; `deploy/fleet/edge_00X.env` são os arquivos por nó (segredos reais **não** versionados; `.env.example` é o template).
4. A mesma `docker-compose.yml` sobe em qualquer RPi trocando apenas o `--env-file`. Nenhum identificador fixo em código ou imagem.

### 5.4 Casos de teste (few-shot, mínimo 6)

**Caso 1 — Ciclo de vida feliz (plano A)**
- Entrada: nó sobe → conecta ao broker → `context` entrega uma leitura do device `Line_1/Pump_01` com métricas `Temperature` (float, `°C`) e `Running` (bool).
- Saída esperada: broker recebe, nesta ordem, `NBIRTH`(`seq=0`, métrica `bdSeq=N`) → `DBIRTH`(`Line_1/Pump_01`, `Temperature` com `alias=1` e `engUnit="°C"`, `Running` com `alias=2`) → `DDATA` referenciando `alias 1` e `alias 2`, `seq` incrementando. Nenhum `DDATA` antes do `DBIRTH`.

**Caso 2 — Morte abrupta via LWT (plano A)**
- Entrada: `docker kill` no container de `delivery` de um nó com `bdSeq_sessão = N`.
- Saída esperada: o broker publica `NDEATH` em `spBv1.0/{group_id}/NDEATH/{edge_node_id}` com métrica `bdSeq = N` (igual ao último `NBIRTH`), sem qualquer ação do SIDA.

**Caso 3 — Morte graciosa (plano A)**
- Entrada: `docker stop` (`SIGTERM`) no mesmo nó.
- Saída esperada: o nó publica um `NDEATH` explícito (`bdSeq = N`, `seq` = próximo) **antes** de fechar a conexão; a conexão é encerrada limpa. Não há dois `NDEATH` conflitantes (o LWT não dispara porque a desconexão foi limpa).

**Caso 4 — Detecção de queda de par (plano B)**
- Entrada: frota de 3 nós com `PROBE_INTERVAL_MS=1000`, `PEER_DOWN_AFTER_MISSES=3`; derruba-se `edge_002`.
- Saída esperada: em ≤ ~3 s, `GET /api/system/peers` em `edge_001` e `edge_003` reporta `edge_002` como `down`; `edge_001` e `edge_003` seguem publicando `DDATA` sem interrupção; `edge_002` some do broker via `NDEATH` (plano A) **independentemente** da detecção do plano B.

**Caso 5 — Broker de nuvem cai, malha leste-oeste sobrevive**
- Entrada: torna-se o `BROKER_URL` inacessível para toda a frota por 30 s; nenhum nó é derrubado.
- Saída esperada: `GET /api/system/peers` em todos os nós continua reportando os pares como `alive` (os *probes* ZeroMQ não passam pelo broker); ao voltar o broker, cada nó reconecta e emite **novo `NBIRTH` com `bdSeq` incrementado**. A recuperação do `DDATA` do período de queda depende do esboço de retenção pré-existente (fora do escopo/aceite desta etapa) — o critério da Etapa 1 é a **continuidade dos demais nós**, não a recuperação deste.

**Caso 6 — Religamento de par (flap)**
- Entrada: `edge_002` é derrubado e volta em ~5 s.
- Saída esperada: `edge_001`/`edge_003` marcam `edge_002` como `down` e, ao receber novo `PROBE_ACK`, voltam-no a `alive`; a histerese (`suspect` + `PEER_DOWN_AFTER_MISSES`) evita oscilação; o novo `NBIRTH` de `edge_002` traz `bdSeq` incrementado; nenhum estado de par é corrompido.

**Caso 7 — Partição parcial (liveness local diverge — aceitável)**
- Entrada: regra de rede que permite `edge_001 ↔ edge_002` e `edge_002 ↔ edge_003`, mas bloqueia `edge_001 ↔ edge_003`.
- Saída esperada: `edge_001` reporta `edge_003` como `down` e `edge_002` como `alive`; `edge_003` reporta o simétrico; `edge_002` reporta ambos `alive`. Isso é **correto** — o plano B dá visão **local**, não consenso. A UI/relatório não tenta reconciliar via eleição/quórum.

**Caso 8 — `seq` estoura 255 (plano A)**
- Entrada: nó publica mais de 256 mensagens sem reconectar.
- Saída esperada: `seq` rola `255 → 0` e continua contínuo; `bdSeq_sessão` inalterado; consumidor não vê isso como *rebirth*.

**Caso 9 — Colisão de identidade (erro de `.env`)**
- Entrada: dois nós sobem com o mesmo `CONTROLLER_ID` / `EDGE_GATEWAY_ID`.
- Saída esperada: o `peer_service` detecta o `CONTROLLER_ID` duplicado no *handshake* e recusa o par com log claro; o broker derruba um dos `clientId` MQTT idênticos — a condição é **visível em log**, não um *flap* silencioso.

---

## 6. SEPARAÇÃO DE RESPONSABILIDADES

### 6.1 Estrutura de arquivos

```
# ── Plano A — ciclo de vida Sparkplug B (Node-RED / delivery) ──
core/delivery/flows.json                 # setupConnectors  : LWT com bdSeq da sessão (qos 1)
                                         # DeliveryProcessor: NBIRTH(seq 0, bdSeq), DBIRTH(definições + alias),
                                         #                    DDATA(por alias), seq contínuo, NDEATH gracioso no close
schemas/sparkplug_b.proto                # NOVO — fonte da verdade do payload Sparkplug B v3.0.0 (Eclipse)
schemas/README.md                        # atualizar: apontar para o .proto

# ── Plano B — malha controller-to-controller (Go / sida-core) ──
sida-core/internal/core/domain/controller.go            # NOVO — ControllerRegister, PeerRef, Envelope, LivenessState
sida-core/internal/core/ports/repository.go             # + PeerRepository (interface)
sida-core/internal/core/services/peer_service.go        # NOVO — malha ZeroMQ ROUTER/DEALER, loop de probe,
                                                        #        FSM de liveness, WriteMessage/RouteMessage/ReadMessage
sida-core/internal/adapters/repository/sqlite_peer.go   # NOVO — tabela `controllers` (WAL, sida_config.db)
sida-core/internal/adapters/handler/peer_handler.go     # NOVO — GET /api/system/peers
sida-core/internal/api/routes.go                        # + rota no grupo apiSystem
sida-core/cmd/server/main.go                            # wiring: carrega Controller Register, sobe peer_service,
                                                        #         encerra a malha no shutdown (SIGTERM)

# ── Frota / orquestração ──
docker-compose.yml                       # interpolação ${VAR}; env de identidade em sida-core e poc-delivery;
                                         # publica ${PEER_PORT} no sida-core — SEM mudar topologia/rede/volumes
.env.example                             # NOVO — template de identidade por nó
deploy/fleet/identities.md               # NOVO — tabela de identidades dos ≥ 3 nós
deploy/fleet/edge_001.env … edge_003.env # NOVO — um .env por nó (segredos reais não versionados)

# ── Testes e loop ──
test/etapa1/compose.test.yml             # 3 nós + Mosquitto local isolado (broker de teste)
test/etapa1/test_s1_foundation.py        # NOVO — checkpoints das tasks S1 (T0.4, T1A.1, T3.1)
test/etapa1/test_plane_a_lifecycle.py    # NBIRTH/DBIRTH/DDATA/NDEATH + bdSeq/seq/alias — checkpoints S2 (T1A.2–T1A.7) + casos 1–3, 8
test/etapa1/test_plane_b_peermesh.py     # troca de mensagem, probe/timeout, /api/system/peers — checkpoints S3 (T1B.1–T1B.5) + casos 4, 6, 7, 9
test/etapa1/test_fleet.py                # NOVO — checkpoints T3.2/T3.3 (frota de 3 nós, compose de teste isolado)
test/etapa1/test_fault_injection.py      # teste de aceite 3.1 (PoC 5) — checkpoints T4.3–T4.6 + coleta de métricas → report.json
progress.json                            # log do loop (seção 3.4); um commit [T…] por task concluída
README-etapa1.md                         # como subir a frota e rodar os testes
```

### 6.2 Responsabilidades por módulo

| Módulo | Faz | NÃO faz |
|---|---|---|
| `core/delivery` — `setupConnectors` | Configura o cliente MQTT com **LWT = `NDEATH`** carregando o `bdSeq` da sessão corrente | Não incrementa `seq`; não decide métricas; não fala com pares |
| `core/delivery` — `DeliveryProcessor` | Emite `NBIRTH`(`seq 0`, `bdSeq`), `DBIRTH`(definições + `alias`) uma vez por device/sessão, `DDATA`(**por alias**), `seq` rolando; `NDEATH` gracioso no `node.on('close')` | Não persiste histórico (sem *store-and-forward*); **não altera** o payload SIDA vindo do `context`; não coordena a frota |
| `schemas/sparkplug_b.proto` | Fonte da verdade do contrato Sparkplug B v3.0.0 (referência/validação e consumidores) | Não é carregado em runtime pelo Node-RED (a lib traz o schema equivalente) |
| `domain/controller.go` | Define `ControllerRegister` (espelha o *Controller Register* do InterEdge: `ControllerID`, `ControllerName`, `ConnectedDevices`, `ConnectedControllers []PeerRef`, `SourceDevices`, `ConditionActions`, `DestinationDevices`, `ProbeIntervalMs`, `MessageBuffer`, `ControllerProbeIntervalMs`), `PeerRef{ID,Endpoint}`, `Envelope{Path,Payload,TS}` | Não faz I/O; não conhece ZeroMQ nem HTTP |
| `ports.PeerRepository` | Contrato de persistência do registro de pares (CRUD do Controller Register) | Não implementa; não conhece SQLite |
| `adapters/repository/sqlite_peer.go` | CRUD da tabela `controllers` no `sida_config.db` (WAL), `CREATE TABLE IF NOT EXISTS` no construtor | Não faz *probing*; não roteia |
| `services/peer_service.go` | `bind` `ROUTER` em `PEER_PORT`; `DEALER` por par; loop de *probe* no `ProbeInterval`; FSM `alive`/`suspect`/`down`; `WriteMessage`/`RouteMessage`/`ReadMessage`; `MessageBuffer` por remetente | **Não** usa `:5556`; não publica no UNS; não decide consenso global; não faz failover de dados (`T1B.6` é opcional) |
| `adapters/handler/peer_handler.go` | Expõe `GET /api/system/peers` (registro + *liveness* local) | Não muta estado; não dispara *probes* sob demanda |
| `cmd/server/main.go` | Carrega o Controller Register, instancia e sobe o `peer_service`, encerra a malha no `shutdown` | Não muda a inicialização do `ZMQPublisher` `:5556` nem das rotas existentes |
| `docker-compose.yml` + `.env` | Parametriza identidade/pares/broker por nó via interpolação; publica `${PEER_PORT}` | **Não** muda topologia de serviços, rede, volumes nem o caminho de dados v2.0; não embute segredos |
| `test/etapa1/` | Sobe frota local + Mosquitto isolado, injeta falha, verifica os dois planos, coleta métricas | **Não** toca no broker de produção (GCP); não valida contra a nuvem |

---

## 7. CASOS EXTREMOS

1. **`DDATA` antes do `NBIRTH` da sessão** (corrida entre `connect` e a primeira leitura do `context`) — segurar as métricas até o `NBIRTH` sair; **nunca** publicar `DATA` sem o `BIRTH` da sessão.
2. **Reconexão MQTT do próprio nó** (queda de rede curta) — nova sessão ⇒ **novo `bdSeq`**, novo `NBIRTH` (`seq=0`), `born_devices` e `alias_map` limpos, `DBIRTH` reemitido para todos os devices ativos. Não reaproveitar aliases antigos sem reemitir `DBIRTH`.
3. **Broker inacessível por período prolongado** — o `retentionRouter` já desvia o payload para `sida-core /api/buffer` enquanto o cliente está offline e o `bufferDistributor` reinjeta na reconexão; **esse caminho não é alterado neste loop** e não faz parte do critério de aceite (a divergência `:8080`/`:8000` pode fazê-lo não funcionar hoje — não é tarefa desta etapa). O que a Etapa 1 garante é a **continuidade dos sobreviventes**, não a recuperação do histórico do nó que caiu. O plano B (peer-mesh) **não** é afetado — os *probes* continuam entre os nós alcançáveis.
4. **Partição de rede parcial** — `peer.liveness` é **local** e pode divergir entre nós (A diz C `down`, B diz C `alive`). Aceitável: o plano B fornece visão local, não consenso. Documentar; **não** tentar reconciliar via eleição/quórum.
5. **Par em *flap*** (`alive → down → alive` em segundos) — aplicar histerese (`suspect` intermediário + `PEER_DOWN_AFTER_MISSES`) para não oscilar; ao voltar, aceitar novo *handshake* e reidratar a rota.
6. **`NDEATH` de um par que este nó nunca "viu nascer"** (nó entrou na frota depois) — se não há registro do par, ignorar sem erro.
7. **Colisão de `CONTROLLER_ID`/`EDGE_GATEWAY_ID`** por erro de `.env` — o `peer_service` recusa o par duplicado no *handshake* com log claro; a colisão de `clientId` MQTT precisa aparecer em log, não virar *flap* silencioso.
8. **Relógios dessincronizados entre RPi** — o `timestamp` Sparkplug e o `TS` do `Envelope` podem divergir; toda métrica de "tempo-até-detecção" é medida **localmente** em relógio monotônico, nunca por diferença de *wall-clock* entre nós.
9. **`docker stop` vs `docker kill`** — `SIGTERM` dá tempo do `NDEATH` gracioso; `SIGKILL`/queda de energia só dispara o LWT. **Ambos** resultam em `NDEATH` no broker; a diferença é só a latência (gracioso ≈ imediato; LWT ≈ *keepalive* do broker).
10. **Restart do container** (não só reconexão) — `bdSeq` reinicia de `0` (não há persistência de `bdSeq` entre restarts nesta etapa). Aceitável: o `bdSeq` só precisa ser monotônico **dentro** da vida do processo; um novo `NBIRTH` com `bdSeq=0` após restart é válido.
11. **Volume alto de devices por nó** — `alias_map` e `MessageBuffer` são `O(devices)` e `O(pares)`; sem *buffer* de histórico no plano B (só *liveness* em memória e registro em SQLite), o footprint é limitado.

---

## 8. STACK TÉCNICA

- **Plano A:** Node-RED 4.x (imagem ARM64 já validada), lib `sparkplug-payload` (schema Sparkplug B v3.0.0 da Eclipse Foundation) + `mqtt` (mqtt.js), JS nos *function nodes* de `core/delivery/flows.json`. `schemas/sparkplug_b.proto` versionado como fonte da verdade (referência/validação — o Node-RED usa o schema embutido na lib).
- **Plano B:** Go (mesma toolchain do `sida-core`, `go 1.26.3`, build `linux/arm64`), `github.com/pebbe/zmq4 v1.4.0` + `libzmq`, `github.com/gin-gonic/gin` (endpoint), SQLite via `github.com/mattn/go-sqlite3` (WAL, `./data/sida_config.db`, `SetMaxOpenConns(1)` — respeitar o padrão de acesso serial já existente). Sem novas dependências de plano de dados.
- **Orquestração:** Docker + `docker-compose` com interpolação `${VAR}` por `--env-file`; `docker buildx` multi-arch. Frota física: ≥ 3 Raspberry Pi 4/8 GB, SO 64-bit, IPs fixos/hostnames na LAN, `PEER_PORT` aberta entre os nós.
- **Testes:** Python 3.10+ (harness de injeção de falha e verificação dos dois planos), `paho-mqtt` para publicar/assinar `spBv1.0/#` contra o Mosquitto de teste, `requests` para `GET /api/system/peers`, `docker` CLI para `stop`/`start`/`stats`. O broker de teste é um **Mosquitto local isolado** (`test/etapa1/compose.test.yml`), sem relação com o broker de produção do GCP.
- **Restrições de dependências:** nenhum banco novo, nenhum *message broker* adicional. O container `sida-core` continua *stateless* entre reinicializações, exceto pelo `sida_config.db` (que passa a ter também a tabela `controllers`). O peer-mesh não persiste histórico — só o registro de pares (SQLite) e o *liveness* (memória).

---

## 9. PROMPT PRONTO PARA O LOOP

```
Você vai implementar a Etapa 1 do Ciclo V3.0 do SIDA seguindo este SDD.

OBJETIVO: Entregar dois planos de coordenação de frota, simultâneos e em transportes
distintos.
(A) PLANO NORTE — o ciclo de vida Sparkplug B em core/delivery/flows.json JÁ EMITE
    NBIRTH, DBIRTH, DDATA e NDEATH via LWT (setupConnectors / DeliveryProcessor). O
    trabalho é só o DELTA DE CONFORMIDADE, sem reescrever esses nós:
      1. bdSeq de sessão: contador que incrementa a cada conexão; hoje o LWT usa bdSeq=0
         fixo e o NBIRTH não carrega bdSeq. Passar a incluir a métrica bdSeq no NBIRTH e
         usar o MESMO valor no NDEATH/LWT da sessão.
      2. Aliases: DBIRTH passa a declarar as DEFINIÇÕES de métrica com alias inteiro;
         DDATA passa a referenciar APENAS o alias (hoje reenvia name).
      3. NDEATH gracioso: publicar NDEATH explícito no node.on('close') antes do
         client.end() (hoje o close só encerra a conexão; o LWT cobre só a queda abrupta).
      4. Adicionar schemas/sparkplug_b.proto (Sparkplug B v3.0.0 da Eclipse) como fonte
         da verdade.
      5. Auditar a contabilidade de seq (NBIRTH=0 → DBIRTH → DDATA…), sem salto/reuso.
(B) PLANO LESTE-OESTE — no sida-core (Go): modelo de domínio ControllerRegister
    (espelha o Controller Register do InterEdge), tabela SQLite `controllers` no
    sida_config.db (WAL), serviço peer_service.go com malha ZeroMQ ROUTER/DEALER numa
    PORTA DEDICADA (PEER_PORT, default 5557 — NUNCA reusar o :5556 do manifesto), loop
    de probe com FSM de liveness (alive/suspect/down por timeout, relógio monotônico
    local) e primitivas WriteMessage/RouteMessage/ReadMessage. Expor GET
    /api/system/peers no grupo apiSystem de routes.go.
FROTA: parametrizar docker-compose.yml por .env (interpolação ${VAR}) — identidade,
    pares, broker, PIN — SEM mudar topologia/rede/volumes nem o caminho de dados v2.0.
    Criar .env.example e deploy/fleet/ (identities.md + edge_001..003.env).

FRONTEIRAS:
- Não tocar em core/ingestion/flows.json nem core/context/flows.json. Em
  core/delivery/flows.json, aplicar só o delta de conformidade acima — NÃO reescrever
  setupConnectors/DeliveryProcessor. O DDATA carrega as mesmas métricas que o context
  entrega, agora por alias.
- Não reusar o socket ZeroMQ :5556 (PUB/SUB de manifesto, consumido pelo
  ontology-builder) para o peer-mesh. Porta e papel (ROUTER/DEALER) dedicados.
- Não completar, hardenear nem remover o esboço de retenção/store-and-forward já cabeado
  na delivery (retentionRouter → sida-core /api/buffer → pullBuffer/bufferDistributor);
  é roadmap. Não corrigir a divergência de porta :8080→:8000 dessas URLs neste loop.
  Não tornar o broker de nuvem redundante. Não adicionar TLS/mTLS nem trocar o PIN por
  OAuth2.
- Não reimplementar as 5 camadas do InterEdge no RPi — só registro de pares, probing e
  roteamento controller-to-controller.
- Failover de dados via par (T1B.6) é OPCIONAL e não é critério de aceite.
- Nunca publicar DATA sem o BIRTH da sessão; bdSeq do NBIRTH == bdSeq do NDEATH/LWT.
- Identidade sempre via .env — nada hardcoded.
- Se a portabilidade ARM64 (pebbe/zmq4/libzmq, sparkplug-payload) falhar, PARAR e
  REPORTAR — não trocar de biblioteca nem de formato de payload para contornar.

MÉTRICA DE CONCLUSÃO: o loop termina quando test/etapa1/test_fault_injection.py passa
integralmente (frota de 3 nós + Mosquitto local isolado): frota íntegra publicando nos
dois planos; ao derrubar um nó, o broker recebe seu NDEATH via LWT (plano A) e os pares
o marcam como down dentro de PROBE_INTERVAL_MS*PEER_DOWN_AFTER_MISSES (plano B); os
sobreviventes seguem publicando sem perda e sem rebirth; ao religar o nó, novo NBIRTH
com bdSeq incrementado e pares o remarcam alive; report.json com t_ndeath,
t_peer_detect, perda nos sobreviventes (=0) e overhead CPU/RAM. Em cada falha: leia o
erro, identifique a causa, corrija, repita. Máximo de 5 tentativas por task antes de
parar e escalar, registrando a causa suspeita em progress.json.

PROCESSO: siga a divisão em sprints S1-S4 e o detalhamento de tasks da seção 3.3.2
(S1 fundação/identidade/proto; S2 plano A; S3 plano B; S4 frota + injeção de falha).
Antes de começar, leia progress.json E o git log da branch interedge; retome da
primeira task sem checkpoint completo.
CHECKPOINT OBRIGATÓRIO POR TASK (seção 3.3.1), nesta ordem, antes de passar à próxima:
  1. o teste funcional da task (tabela 3.3.2: arquivo::caso) passa contra a frota local
     de teste, e os testes das tasks anteriores continuam verdes (sem regressão);
  2. progress.json marca a task concluida (status, timestamp, hash do commit; se
     bloqueada, motivo e nº de tentativas);
  3. UM único commit na branch interedge com o código + o teste funcional + o
     progress.json, mensagem "<tipo>(<escopo>): <descrição> [<ID da task>]".
Sem teste funcional verde NÃO há commit e a task NÃO é concluida. Falhou 5x: task
bloqueada, sem commit, pare e escale. Sem squash; não emende commits de tasks
anteriores. Task já commitada que depois se revele incorreta: reverta com um novo
commit e refaça.

Consulte as seções 0.1 (estado atual do código), 4 (contrato de estado), 5 (regras de
negócio + casos de teste), 6 (estrutura de arquivos e responsabilidades), 7 (casos
extremos) e 8 (stack) deste SDD.
```

---

## Histórico de decisões deste SDD

| # | Decisão | Origem |
|---|---|---|
| 1 | Escopo = Etapa 1 do Ciclo V3.0 (planos de coordenação A + B, frota multi-RPi e demonstração por injeção de falha — `T0.4`, `T1A.*`, `T1B.1`–`T1B.5`, `T3.*`, `T4.*`). A Etapa 2 (ingestão Classe 0/1) tem SDD próprio. | Guia de Implementação do Ciclo V3.0 |
| 2 | Adoção **simultânea** dos mecanismos A e B, em planos de transporte distintos (norte MQTT/Sparkplug ao UNS; leste-oeste ZeroMQ entre `sida-core`). | Decisão de coordenação fechada (Histórico de Decisões §7) |
| 3 | **`NBIRTH`, `DBIRTH`, `DDATA` e `NDEATH` (via LWT) já são emitidos** por `setupConnectors`/`DeliveryProcessor` em `core/delivery/flows.json` (com `seq` rolando e `engUnit`). O plano A **não é *greenfield*** — é um **delta de conformidade** de 4 itens: (i) `bdSeq` de sessão correlacionando `NBIRTH`↔`NDEATH`/LWT (hoje `0` fixo, ausente no `NBIRTH`); (ii) aliases no `DDATA` + definições no `DBIRTH` (hoje por `name`); (iii) `NDEATH` gracioso no `close` (hoje só o LWT); (iv) `schemas/sparkplug_b.proto`. | Inspeção de `core/delivery/flows.json` nesta sessão (ajuste pedido pelo usuário) |
| 3b | O esboço de **retenção/*store-and-forward*** já está cabeado na *delivery* (`retentionRouter` → `sida-core /api/buffer` → `pullBuffer`/`bufferDistributor`), com as URLs apontando para `sida-core:8080` enquanto o HTTP real é `:8000`. **Não é tocado neste loop** (nem completado, nem removido, nem a porta corrigida) — é roadmap; o ciclo de vida não pode depender dele. | Inspeção nesta sessão + `historico-decisoes` §9 |
| 4 | Peer-mesh no `sida-core` (Go) com socket ZeroMQ **dedicado** (`PEER_PORT`, default `5557`), sem reusar o `:5556` do manifesto (consumido pelo `ontology-builder`). | `CLAUDE.md` do projeto + inspeção (`zmq_service.go`, `docker-compose.yml`) |
| 5 | `schemas/sparkplug_b.proto` adicionado como fonte da verdade (a pasta `schemas/` hoje só tem `README.md`). | Guia `T1A.1` + inspeção |
| 6 | `docker-compose.yml` **é** parametrizada por `.env` nesta etapa (interpolação, sem mudar topologia). Diferente da fronteira do `SDD_SIDA_UNS_Web_Client.md` (que proíbe tocar no compose) — lá era um add-on externo; aqui é evolução do próprio core. | Guia `T3.1` + confronto com o SDD irmão |
| 7 | Teste de aceite = PoC 5 (injeção de falha) com verificação dos **dois** planos + métricas (tempo-até-`NDEATH`, tempo-até-detecção-de-par, perda nos sobreviventes = 0, *overhead* CPU/RAM). | Release Notes V3.0 — Critérios de Aceite PoC 5 |
| 8 | *Liveness* do plano B é **local, sem consenso/quórum**; divergência entre nós sob partição é aceitável e documentada, não um bug. | Natureza do modelo InterEdge (registro de pares local, *probe* ≠ heartbeat de consenso) |
| 9 | Fora de escopo, por decisão: *store-and-forward* com WAL, TLS/mTLS, PIN→OAuth2, failover de dados via par (`T1B.6`), redundância do broker de nuvem. | Delimitações consolidadas (Histórico de Decisões §9) |
| 10 | Molde herdado do `SDD_SIDA_UNS_Web_Client.md`: 4 sprints, máx. 5 tentativas por task antes de escalar, `progress.json` para retomada, teste de aceite automatizado contra broker local isolado. | `SDD_SIDA_UNS_Web_Client.md` |
| 11 | `bdSeq` não persiste entre *restarts* do container (só é monotônico dentro da vida do processo); `NBIRTH` com `bdSeq=0` após *restart* é válido. | Decidido pela IA — evita persistência extra fora do escopo; conforme ao Sparkplug |
| 12 | **Checkpoint por task com teste funcional + um commit por task** (seções 3.3.1/3.3.2): cada uma das 22 tasks tem um teste funcional automatizado nomeado (`arquivo::caso`); a task só é `concluida` com o teste verde, o `progress.json` atualizado e **um** commit `[T…]` na branch `interedge` — sem squash, sem `--amend` de tasks anteriores; task incorreta é revertida por novo commit. O critério de saída do sprint vira checagem integradora sobre tasks já commitadas. | Pedido do usuário nesta sessão |
