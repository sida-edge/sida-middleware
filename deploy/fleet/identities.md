# Identidades da frota — SIDA Etapa 1 do Ciclo V3.0

Cada nó Raspberry Pi roda a pilha completa do SIDA e recebe sua identidade
**exclusivamente** por `--env-file` (ou `/app/data/.env`). Nenhum identificador é
fixo em código, imagem ou `flows.json` (Fronteira 11 do SDD).

A mesma `docker-compose.yml` sobe em qualquer nó — muda-se só o arquivo `.env`:

```bash
docker compose --env-file deploy/fleet/edge_001.env up -d
```

## Tabela de identidades

| Nó        | `EDGE_GATEWAY_ID` | `CONTROLLER_ID` | `GROUP_ID`        | `PEER_PORT` | Pares (`PEERS`)                                  |
|-----------|-------------------|-----------------|------------------|-------------|-------------------------------------------------|
| edge_001  | `sida_edge_001`   | `edge_001`      | `Enterprise_Site` | `5557`      | `edge_002@edge2-core:5557,edge_003@edge3-core:5557` |
| edge_002  | `sida_edge_002`   | `edge_002`      | `Enterprise_Site` | `5557`      | `edge_001@edge1-core:5557,edge_003@edge3-core:5557` |
| edge_003  | `sida_edge_003`   | `edge_003`      | `Enterprise_Site` | `5557`      | `edge_001@edge1-core:5557,edge_002@edge2-core:5557` |

- **`EDGE_GATEWAY_ID`** = `edge_node_id` Sparkplug (clientId MQTT; tópico
  `spBv1.0/{GROUP_ID}/+/{EDGE_GATEWAY_ID}`). Único por nó.
- **`CONTROLLER_ID`** = identidade do nó na malha *controller-to-controller*
  (plano B). Único por nó.
- **`GROUP_ID`** = `{Enterprise}_{Site}` — igual para nós do mesmo sítio.
- **`PEERS`** — lista `id@host:port` dos outros nós. Os `host` acima são os
  nomes de serviço da frota **de teste** (`test/etapa1/compose.test.yml`); numa
  frota física, troque por hostnames/IPs fixos na LAN.
- **`BROKER_URL`** — broker MQTT do UNS. Teste isolado: `mqtt://mosquitto:1883`.
  Produção: o broker do GCP.
- **`EDGE_ENGINEER_PIN`** — segredo real **não** vai aqui nem nos `.env`
  versionados; nos arquivos da frota de teste é um valor descartável.

> Arquivos `deploy/fleet/edge_00X.env` são a **definição da frota de teste** e
> são versionados (sem segredos reais). O `.env` de um nó de produção contém o
> PIN real e fica fora do versionamento (`.gitignore`: `**/.env`).
