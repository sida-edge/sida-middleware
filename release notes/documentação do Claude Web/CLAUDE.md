# CLAUDE.md — Contexto do projeto SIDA × InterEdge (v3.0)

Guia persistente para trabalhar neste projeto com o Claude Code. Leia antes de codar.

## O que é o projeto

Evoluir o middleware **SIDA (Smart Industrial DataOps Agent)** da topologia centralizada (v2.0) para uma **frota descentralizada de gateways Raspberry Pi**, cada um rodando a pilha completa do SIDA e publicando num **Unified Namespace (UNS)** compartilhado — **sem nó central de coordenação na borda** (elimina o SPOF de borda). Também amplia a ingestão para **dispositivos Classe 0/1** (sem CLP). Fundamentação: framework **InterEdge**.

Meta central, verificável: **eliminar o SPOF de borda**, comprovado por **teste de injeção de falha** (derrubar um nó; os demais seguem publicando).

## Arquitetura de coordenação: DOIS PLANOS (decisão fechada — A + B juntos)

| Plano | Mecanismo | Transporte | Onde vive | Responsabilidade |
|---|---|---|---|---|
| **Norte** (borda→nuvem) | **A** — ciclo de vida Sparkplug B | MQTT → broker UNS (GCP) | camada **delivery** (Node-RED) | `NBIRTH`/`DBIRTH`/`DDATA`/`NDEATH` + LWT; observabilidade da frota |
| **Leste-oeste** (borda↔borda) | **B** — controller-to-controller (InterEdge) | ZeroMQ entre `sida-core` | **sida-core** (Go) | registro de pares, *probes*, roteamento; detecção de queda local |

Os planos usam **transportes e portas distintos** — não podem se confundir. Dão dois sinais de liveness independentes.

## Mapa do código do SIDA (onde mexer)

Repositório-alvo: `sida-middleware/`. Componentes relevantes (da arquitetura v2.0):

- `core/delivery/flows.json` — **Plano A**. Função `spbGenerator`; estender para `NBIRTH`/`DBIRTH`, `bdSeq`/`seq`, LWT=`NDEATH`, `DDATA` com aliases.
- `core/ingestion/flows.json` — **Etapa 2**. Adicionar sub-fluxo **adaptador** que normaliza a saída do dispositivo Classe 0/1 para o payload interno do SIDA.
- `core/context/flows.json` — aplica ISA-95; **não deve precisar de alteração** (o adaptador entrega o payload já no formato esperado).
- `sida-core/internal/core/domain/manifest.go` — modelos. Adicionar `interedge` ao enum `Connection.Protocol`. Criar modelo do **controller register** (Plano B).
- `sida-core/internal/core/services/` — **Plano B**: novo `peer_service.go` (malha ZeroMQ, scheduler de probes, primitivas de roteamento).
- `sida-core/internal/core/ports/` — interfaces do repositório de pares.
- `sida-core/internal/adapters/repository/` — persistência SQLite (nova tabela `controllers`).
- `sida-core/internal/api/routes.go` — novo endpoint `GET /api/system/peers`.
- `schemas/sparkplug_b.proto` — **adicionar** (single source of truth do Sparkplug B).
- `docker-compose.yml` + `.env` — parametrizar por nó (`EDGE_GATEWAY_ID`, `edge_node_id`, `group_id`, pares, broker, `EDGE_ENGINEER_PIN`).

## Formatos e convenções (não inventar)

- **Payload interno do SIDA** (ingestão→contexto, via ZeroMQ IPC Push/Pull):
  ```json
  { "timestamp": 0, "gateway_id": "sida_edge_001",
    "source": { "device_id": "esp32-A", "source_protocol": "interedge" },
    "data": { "...": 0 },
    "asset_context": { "standard": "ISA-95", "path": [ {"type":"...","id":"..."} ] } }
  ```
- **Tópico Sparkplug B (saída):** `spBv1.0/{group_id}/DDATA/{node_id}/{device_id}`, onde
  `group_id = Enterprise_Site_Area`, `node_id = Line`, `device_id = Equipment`.
- **Ciclo de vida (novo):** `spBv1.0/{group_id}/NBIRTH|NDEATH/{node_id}` e `.../DBIRTH/{node_id}/{device_id}`.
- **ZeroMQ existente:** IPC Push/Pull entre camadas (`ipc:///tmp/.ipc/ingestion.ipc`, `.../context.ipc`); controle PUB/SUB do manifesto em `tcp://sida-core:5556` (tópico `sida/manifest/{gateway_id}`, payload `RELOAD`).
  - **Plano B usa um socket peer NOVO e dedicado** — não reutilizar `:5556`.
- **Auth (v2.0):** PIN (`EDGE_ENGINEER_PIN`) → token SHA256 `session_<hash>`; header `Authorization: Bearer session_<hash>`.
- **SQLite:** WAL, `/app/data/sida_config.db`, tabela `edge_manifests`.

## Escopo — o que NÃO fazer (delimitações do projeto)

- **Não** tornar o broker da nuvem redundante — ele permanece ponto de convergência de dados (fora do escopo de SPOF).
- **Não** implementar store-and-forward persistente com WAL (roadmap separado; instabilidade RPi↔nuvem).
- **Não** implementar TLS/mTLS nem trocar o PIN por OAuth2 neste ciclo (trabalho futuro).
- **Não** dar controle/atuação local aos dispositivos Classe 0/1 — apenas sensoriamento.
- **Failover de dados via par** (Plano B reencaminhar dados de nó isolado) é **opcional**, não núcleo.

## Ordem de implementação (ver `docs/02-guia-implementacao.md`)

1. Fundação (`T0.1`–`T0.4`) — **`T0.3` ARM64 já concluída**.
2. Artefatos teóricos: mapeamento (`T-E01`) e decisão A+B (`T-E02`).
3. **Plano A** — ciclo Sparkplug (`T1A.1`–`T1A.7`) na delivery.
4. **Plano B** — peer-mesh InterEdge (`T1B.1`–`T1B.5`) no sida-core. **Maior risco de engenharia.**
5. Etapa 2 — ingestão Classe 0/1 (`T2.1`–`T2.6`).
6. Frota multi-RPi (`T3.1`–`T3.3`).
7. Demonstração/avaliação (`T4.1`–`T4.6`) + qualidade (`T5.1`–`T5.4`).

## Riscos ativos

1. **Plano B em escala de RPi/Go** — o InterEdge só foi validado em ESP32/Arduino (redes pequenas, texto simples). Reimplementar no sida-core é trabalho novo; reservar folga.
2. **Conformidade Sparkplug** — `BIRTH` antes de `DATA`, `bdSeq`/`seq` corretos; erros quebram consumidores silenciosamente.
3. **Confusão de brokers** — o MQTT **de ingestão** (entrada, Etapa 2) ≠ o MQTT **do UNS** (saída).

## Terminologia (evitar ambiguidade)

"Descentralizado" no InterEdge = decisões de interoperabilidade na borda sem depender da nuvem. **Não** confundir com resiliência multi-gateway/SPOF, que é a propriedade que este projeto adiciona.
