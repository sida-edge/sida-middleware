---
documento: "Guia de Implementação — Projeto SIDA-InterEdge (Ingestão Distribuída e Resiliente)"
candidato: "Jackson Raniel Florencio da Silva"
decisao_coordenacao: "Mecanismos A (Sparkplug/UNS) e B (controller-to-controller InterEdge) simultâneos, em planos distintos"
escopo: "Etapa 1 (frota descentralizada A+B) + Etapa 2 (ingestão Classe 0/1) + artefatos E01–E07"
referencia: "Ver Projeto_SIDA-InterEdge_Ingestao_Distribuida.md para fundamentação, objetivos e diagramas"
---

# Guia de Implementação — o que falta para executar o projeto

## Princípio de arquitetura: dois planos, dois mecanismos

A frota usa **A e B ao mesmo tempo**, cada um em um plano de comunicação distinto, para que **não conflitem** (transportes e responsabilidades diferentes):

| | **Mecanismo A — Sparkplug / UNS** | **Mecanismo B — controller-to-controller (InterEdge)** |
|---|---|---|
| Plano | **Norte** (borda → nuvem) | **Leste-oeste** (borda ↔ borda) |
| Transporte | MQTT para o broker do UNS (GCP) | ZeroMQ entre os `sida-core` dos RPi |
| Onde vive | Camada **delivery** (Node-RED) | **sida-core** (Go) — camadas controle/serviço/registro |
| Entrega | Ciclo de vida `NBIRTH`/`NDEATH`/`DDATA` + `LWT`; observabilidade da frota no namespace | Registro de pares (`ConnectedControllers`), *probes* periódicos, roteamento de mensagens; detecção de queda **local** |
| Papel no projeto | Resiliência e visibilidade *UNS-nativa* | Instanciação **genuína** do modelo InterEdge (plano de controle descentralizado) |

> **Sinergia:** dois sinais de liveness independentes — `NDEATH`/`LWT` (observado da nuvem) e *timeout* de *probe* (observado entre pares). O plano leste-oeste continua funcionando mesmo se o broker da nuvem cair.

A ordem recomendada de execução é: **Fase 0 → E01/E02 → Etapa 1A → Etapa 1B → Etapa 2 → Frota → Demonstração → Qualidade/Comunicação.** Cada tarefa tem **objetivo**, **onde**, **passos** e **critério de pronto (DoD)**.

---

## Fase 0 — Fundação e ambiente

### T0.1 — Recuperar e subir a baseline do SIDA v2.0
- **Objetivo:** ter o ponto de partida funcional antes de modificar qualquer coisa.
- **Onde:** repositório `sida-middleware/` (sida-core, core/ingestion|context|delivery, docker-compose.yml).
- **Passos:** clonar o repo; `docker-compose up -d --build`; rodar o `sida-simulator` (Modbus, porta 5020); confirmar fluxo Modbus → ISA-95 → Sparkplug B → broker, assinando `spBv1.0/#`.
- **DoD:** dado do simulador chega ao broker como `DDATA`; latência medida ~85–110 ms (referência da v2.0).

### T0.2 — Provisionar a frota física
- **Objetivo:** ≥ 3 Raspberry Pi prontos para receber a stack.
- **Passos:** 3× Raspberry Pi (4/8 GB, SO 64-bit), Docker + docker-compose instalados; IPs fixos/hostnames na LAN (necessário para o plano leste-oeste do Mecanismo B); broker MQTT acessível (o broker GCP existente **ou** um Mosquitto local para testes isolados).
- **DoD:** os 3 RPi se enxergam na LAN (ping/hostname) e alcançam o broker.

### T0.3 — Portar a stack para ARM64 ✅ CONCLUÍDA
- **Objetivo:** garantir que o SIDA roda no Raspberry Pi (a v2.0 foi validada em x86).
- **Onde:** `infra/Dockerfile`, imagens dos serviços.
- **Passos:** rebuild multi-arch (`docker buildx` para `linux/arm64`); confirmar **Go** (build arm64 do sida-core), **Node-RED 4.x** (arm ok) e **libzmq/ZeroMQ** disponíveis em arm64 (ponto de atenção: bindings nativos do ZeroMQ no Go e nos nós Node-RED).
- **DoD:** `docker-compose up` sobe os 4 contêineres num RPi sem erro de arquitetura; health check OK.
- **Status:** ✅ Validada. Compatibilidade ARM64 (incl. bindings ZeroMQ) confirmada — o principal risco da fundação está descartado.

### T0.4 — Definir identidades da frota
- **Objetivo:** identidade única por nó, nos dois planos.
- **Passos:** definir por RPi: `EDGE_GATEWAY_ID` (ex.: `sida_edge_001..003`), `edge_node_id` Sparkplug, `group_id` (derivado de Enterprise_Site_Area), e `controller_id` + endpoint do peer-mesh.
- **DoD:** tabela de identidades documentada e parametrizada por `.env`.

---

## Artefatos teórico e de decisão

### T-E01 — Mapeamento formal InterEdge × SIDA *(E01)*
- **Objetivo:** consolidar o artefato teórico.
- **Passos:** formalizar a tabela camada×componente (já esboçada no projeto) e a justificativa do **nível organizacional ≙ ISA-95**; revisar terminologia ("descentralizado" no sentido InterEdge = sem dependência da nuvem para decisões de interoperabilidade ≠ resiliência multi-gateway).
- **DoD:** documento E01 revisado e anexado ao relatório.

### T-E02 — Registro da decisão de coordenação A+B *(E02)*
- **Objetivo:** justificar formalmente a adoção simultânea.
- **Passos:** registrar a matriz de critérios; declarar a **separação de planos** (norte/leste-oeste) como garantia de não-conflito; definir os papéis de A (observabilidade/lifecycle) e B (coordenação/roteamento) e a sinergia de duplo liveness.
- **DoD:** relatório E02 com a decisão e o desenho dos dois planos.

---

## Etapa 1A — Ciclo de vida Sparkplug B (plano norte) *(E03)*

> Hoje a delivery emite **apenas `DDATA`**. Sparkplug exige `BIRTH` antes de `DATA` e correlação por `bdSeq`. Esta etapa completa o ciclo de vida.

### T1A.1 — Fonte da verdade do schema
- **Onde:** `schemas/sparkplug_b.proto` (o projeto já o prevê "a ser adicionado").
- **Passos:** adicionar o `.proto` do Sparkplug B (Eclipse) e referenciá-lo como *single source of truth*.
- **DoD:** `.proto` versionado em `/schemas`.

### T1A.2 — Gestão de `bdSeq` e `seq`
- **Onde:** `core/delivery/flows.json` (função `spbGenerator` e contexto do fluxo).
- **Passos:** implementar contador `bdSeq` (incrementa a cada novo ciclo de vida) e `seq` (0–255, rolando a cada mensagem), persistidos no contexto do nó.
- **DoD:** `seq` correto e contínuo em NBIRTH→DBIRTH→DDATA.

### T1A.3 — Configurar o LWT = `NDEATH`
- **Onde:** nó **MQTT Out** do Node-RED (ou cliente MQTT da delivery).
- **Passos:** registrar a *Will Message* como `NDEATH` no tópico `spBv1.0/{group_id}/NDEATH/{edge_node_id}`, com payload contendo o `bdSeq` corrente.
- **DoD:** ao matar o contêiner/nó, o broker publica o `NDEATH` automaticamente.

### T1A.4 — Publicar `NBIRTH` e `DBIRTH`
- **Onde:** inicialização do fluxo de delivery.
- **Passos:** ao conectar, publicar `NBIRTH` (`spBv1.0/{group_id}/NBIRTH/{edge_node_id}`, com `bdSeq` casando com o do LWT e *metrics* de nascimento); publicar `DBIRTH` por dispositivo, **definindo os aliases** de cada métrica.
- **DoD:** `mosquitto_sub -t 'spBv1.0/#' -v` mostra NBIRTH+DBIRTH na subida.

### T1A.5 — Migrar `DDATA` para usar aliases
- **Passos:** ajustar `spbGenerator` para emitir `DDATA` referenciando os aliases declarados no `DBIRTH` (conformidade Sparkplug).
- **DoD:** `DDATA` válido pós-BIRTH; consumidor consegue resolver aliases.

### T1A.6 — `NDEATH` em *shutdown* gracioso
- **Passos:** publicar `NDEATH` explícito ao encerrar normalmente (além do LWT para quedas abruptas).
- **DoD:** parada limpa também gera `NDEATH`.

### T1A.7 — Teste do ciclo de vida
- **Passos:** subir → ver BIRTH; rodar → ver DDATA; `docker stop` → ver NDEATH (LWT).
- **DoD:** ciclo completo observável no namespace.

---

## Etapa 1B — Plano de coordenação peer-to-peer (plano leste-oeste, InterEdge) *(E03)*

> Aqui mora a instanciação **genuína** do InterEdge. Implementado no **sida-core (Go)**, reusando a competência ZeroMQ do SIDA. É o item de **maior risco de engenharia** (o InterEdge só foi validado em ESP32/Arduino, redes pequenas, texto simples).

### T1B.1 — Modelar o Controller Register no domínio
- **Onde:** `sida-core/internal/core/domain/` (novo `controller.go`) + `ports/` + `repository` (SQLite).
- **Passos:** struct com `ControllerId`, `ConnectedControllers` (lista de pares: id + endpoint), `ControllerProbeIntervals`, `MessageBuffer`, `SourceDevices`/`DestinationDevices` (roteamento), espelhando o registro do InterEdge (Azad). Nova tabela SQLite `controllers`.
- **DoD:** CRUD do controller register persistido; carga em memória na inicialização.

### T1B.2 — Transporte do peer-mesh (ZeroMQ)
- **Onde:** `sida-core/internal/core/services/` (novo `peer_service.go`).
- **Passos:** cada `sida-core` expõe um socket peer (ex.: `ROUTER`) em `tcp://<rpi-ip>:<porta_peer>`; mantém `DEALER`/sockets para cada par em `ConnectedControllers`. **Distinto** do socket de controle existente (`tcp://sida-core:5556`, PUB/SUB do manifesto) — não reutilizar a mesma porta/papel.
- **DoD:** dois `sida-core` trocam uma mensagem de teste pela malha.

### T1B.3 — Scheduler e *probes* (ControllerProgram loop)
- **Onde:** `peer_service.go`.
- **Passos:** loop contínuo que faz *probe* (heartbeat) aos pares em `ControllerProbeIntervals`; mantém estado de liveness; *timeout* ⇒ par considerado caído (**sinal leste-oeste, independente do LWT da nuvem**).
- **DoD:** ao derrubar um par, os demais detectam o *timeout* localmente em ≤ intervalo configurado.

### T1B.4 — Primitivas de transmissão do InterEdge
- **Passos:** implementar, adaptadas a Go, as primitivas do modelo: `WriteMessage`, `RouteMessage`, `ReadMessage` (mensagem = dados + informação de roteamento), e a tabela de roteamento Controller/SourceDevice/DestinationDevice.
- **DoD:** uma mensagem roteia corretamente entre `sida-core` A→B→C conforme a tabela.

### T1B.5 — Expor o estado da malha
- **Onde:** API REST do sida-core (`internal/api/routes.go`).
- **Passos:** novo endpoint `GET /api/system/peers` (estado/liveness dos pares); opcionalmente publicar o estado da malha no UNS para o dashboard.
- **DoD:** o estado da frota (visão leste-oeste) é consultável e/ou visível no namespace.

### T1B.6 *(opcional, declarado)* — Failover de dados via par
- **Passos:** se o broker da nuvem estiver inacessível a um nó, rotear seus dados a um par com conectividade que os republica no UNS (usa `RouteMessage`).
- **DoD/Escopo:** marcado como **extensão opcional** — encosta no *store-and-forward* (roadmap do SIDA); o núcleo de B é o plano de **coordenação/consciência**, não o failover de dados.

---

## Etapa 2 — Ingestão de dispositivos Classe 0/1 *(E05)*

### T2.1 — Firmware com perfis InterEdge (dispositivo)
- **Onde:** ESP32 (C/C++), no estilo Azad et al. (2025).
- **Passos:** implementar *device profile* + *network profile*; ler sensor (DHT11/TMP36); para sensor Classe 0 (Arduino sem rede), encadear: **sensor Classe 0 → ESP32 (Classe 1) → RPi**.
- **DoD:** ESP32 publica leituras periódicas pela rede.

### T2.2 — Transporte dispositivo → RPi
- **Passos:** escolher **MQTT local** (tópico de *ingestão*, **separado** do UNS de saída) ou **HTTP POST** a um endpoint da ingestão. Recomendado: MQTT local (nó MQTT In nativo do Node-RED).
- **DoD:** mensagem do ESP32 chega ao `sida-poc-ingestion`.
- **Atenção:** não confundir o broker/tópico **de ingestão** (entrada) com o broker **do UNS** (saída).

### T2.3 — Adaptador de ingestão (componente novo)
- **Onde:** `core/ingestion/flows.json` (novo sub-fluxo).
- **Passos:** receber a saída do dispositivo, mapear via perfil para o **payload interno do SIDA** (`timestamp`, `gateway_id`, `source{device_id, source_protocol:"interedge"}`, `data{...}`) e injetar no socket **ZMQ Push** para o context (`ipc:///tmp/.ipc/ingestion.ipc`).
- **DoD:** o context recebe o payload normalizado sem alterações nele.

### T2.4 — Estender o modelo de Connection
- **Onde:** `sida-core/internal/core/domain/manifest.go`.
- **Passos:** adicionar `interedge` ao enum `Connection.Protocol` (hoje `modbus_tcp/modbus_rtu/opc_*`); garantir validação do manifesto.
- **DoD:** manifesto com dispositivo `interedge` é aceito e validado.

### T2.5 — Mapear o dispositivo na hierarquia ISA-95
- **Passos:** definir o `asset_context` (path Enterprise→…→Equipment) do dispositivo no manifesto — provando o **nível organizacional** para uma fonte **sem CLP**.
- **DoD:** `DDATA` do dispositivo sai no tópico Sparkplug correto (`spBv1.0/{group}/DDATA/{line}/{equipment}`).

### T2.6 — Teste ponta a ponta da Etapa 2
- **Passos:** sensor → ESP32 → ingestão(adaptador) → context(ISA-95) → delivery(Sparkplug) → UNS.
- **DoD:** leitura do sensor aparece contextualizada no UNS.

---

## Frota e orquestração *(E04)*

### T3.1 — `docker-compose` parametrizado para multi-RPi
- **Passos:** parametrizar por `.env`: `EDGE_GATEWAY_ID`, `edge_node_id`, `group_id`, lista de pares (B), URL do broker (A), `EDGE_ENGINEER_PIN`.
- **DoD:** a mesma compose sobe em qualquer RPi mudando apenas o `.env`.

### T3.2 — Rede do peer-mesh
- **Passos:** IPs fixos/hostnames e portas peer abertas entre os RPi; `ConnectedControllers` preenchido em cada nó.
- **DoD:** cada `sida-core` lista e alcança seus pares.

### T3.3 — Subir e validar os 3 nós
- **Passos:** subir os 3 RPi; confirmar que cada um publica `NBIRTH/DDATA` (A) **e** enxerga os pares (B).
- **DoD:** os dois planos ativos simultaneamente nos 3 nós.

---

## Demonstração e avaliação *(E06)*

### T4.1 — Cenário t0 (frota íntegra)
- **Passos:** `mosquitto_sub -t 'spBv1.0/#' -v`; confirmar dados dos 3 nós; consultar `GET /api/system/peers` em cada um.
- **DoD:** 3 nós vivos nos dois planos.

### T4.2 — Injeção de falha
- **Passos:** derrubar o RPi#2 (`docker stop` ou desligar).
- **DoD:** falha aplicada e cronometrada.

### T4.3 — Verificação dos dois planos
- **Passos:** confirmar **(A)** `NDEATH`/`LWT` do #2 no UNS; **(B)** #1 e #3 detectam o *timeout* do par; #1 e #3 **seguem publicando** sem intervenção.
- **DoD:** continuidade dos sobreviventes comprovada e os dois sinais de liveness observados.

### T4.4 — Métricas
- **Passos:** registrar continuidade (zero perda nos sobreviventes), **tempo-até-`NDEATH`** (plano A), **tempo-até-detecção-de-par** (plano B) e *overhead* CPU/RAM por RPi.
- **DoD:** planilha/tabela de evidências consolidada.

### T4.5 *(se T1B.6 implementado)* — Failover de dados
- **Passos:** isolar um nó do broker e demonstrar reroteamento via par.
- **DoD:** dados do nó isolado chegam ao UNS por um par.

### T4.6 — Evidências
- **Passos:** salvar logs, capturas do `mosquitto_sub`, saídas de `/api/system/peers`, métricas.
- **DoD:** pacote de evidências anexável ao relatório.

---

## Qualidade e comunicação

### T5.1 — Testes automatizados *(limitação conhecida da v2.0: nenhum)*
- **Passos:** testes unitários do **adaptador de ingestão** e do **controller register/peer-mesh**; teste de integração do **ciclo Sparkplug** (BIRTH→DATA→DEATH).
- **DoD:** suíte mínima rodando (idealmente em CI).

### T5.2 — Observabilidade mínima
- **Passos:** logs estruturados nos pontos novos (lifecycle, probes, adaptador). Prometheus/Grafana é roadmap — manter leve.
- **DoD:** logs suficientes para diagnosticar a demonstração.

### T5.3 — Documentação de deploy
- **Passos:** README de implantação multi-RPi; atualizar `/schemas`; diagrama da topologia A+B.
- **DoD:** outro operador consegue subir a frota a partir do README.

### T5.4 — Relatório e artigo *(E06, E07)*
- **Passos:** relatório técnico com resultados; artigo científico.
- **DoD:** E06 e E07 submetidos.

---

## Mapa de tarefas → entregáveis → cronograma

| Entregável | Tarefas | Meses (cronograma) |
|---|---|---|
| E01 Mapeamento | T-E01 | M1–M2 |
| E02 Decisão A+B | T-E02 | M2–M3 |
| E03 Coordenação (A+B) | Fase 0 (T0.1–T0.4), Etapa 1A (T1A.*), Etapa 1B (T1B.*) | M3–M4 |
| E04 Frota multi-RPi | T3.1–T3.3 | M4–M5 |
| E05 Ingestão Classe 0/1 | T2.1–T2.6 | M5–M6 |
| E06 Demonstração | T4.1–T4.6, T5.1–T5.3 | M6–M7 |
| E07 Artigo | T5.4 | M7–M8 |

---

## Principais riscos e pontos de atenção

1. **Build ARM64 / bindings ZeroMQ (T0.3):** ✅ **resolvido** — compatibilidade validada; deixa de ser risco ativo. O maior risco de engenharia passa a ser o Mecanismo B (item 3).
2. **Conformidade Sparkplug (T1A.*):** `BIRTH` antes de `DATA`, correlação `bdSeq`, `seq` rolando — erros silenciosos quebram consumidores.
3. **Mecanismo B em escala de RPi (T1B.*):** validado só em ESP32/Arduino; no `sida-core`/Go é implementação nova — maior risco de engenharia e de cronograma.
4. **Dois planos MQTT não podem se confundir (T2.2):** broker/tópico de **ingestão** (entrada) ≠ broker do **UNS** (saída).
5. **Segurança (declarada fora de escopo):** ZeroMQ IPC/peer não criptografado e PIN são limitações conhecidas; TLS/mTLS fica como trabalho futuro.
6. **Escopo do failover (T1B.6/T4.5):** opcional; o núcleo de B é coordenação/consciência, não *store-and-forward* de dados (roadmap).
