# SIDA UNS Web Client

Cliente MQTT **web** (JavaScript vanilla) que se conecta via **WebSocket** a um
broker **MQTT/Sparkplug B** existente, decodifica nativamente o payload binário
Sparkplug B (Protobuf) recebido em `spBv1.0/#`, descobre automaticamente a
hierarquia **Grupo → Nó → Dispositivo → Métrica** e renderiza um dashboard com
gráficos de série temporal atualizados em tempo real.

> É um **consumidor** do UNS já homologado (Camada 3 — Delivery). Não altera
> `sida-core`, os flows Node-RED nem o broker Mosquitto de produção.

## Princípios / fronteiras

- **Nada é persistido** em disco, `localStorage`, `sessionStorage` ou cookies —
  nem credenciais nem histórico. Tudo vive apenas na memória da aba e é
  descartado ao recarregar/fechar.
- **Sem frameworks de UI.** Apenas JS vanilla + [`mqtt.js`](https://github.com/mqttjs/MQTT.js)
  (MQTT sobre WebSocket) + [`protobufjs`](https://github.com/protobufjs/protobuf.js)
  (decodificação Sparkplug B contra o schema oficial da Eclipse Foundation).
- **Login** é exclusivamente usuário/senha MQTT, repassados diretamente ao
  broker na conexão. Se o broker rejeitar, a tela de login exibe o erro.

## Configuração

| Variável | Descrição | Padrão |
|---|---|---|
| `BROKER_WS_URL` | Endereço do listener MQTT-over-WebSocket do broker (ex.: `wss://broker.host:9001`). Injetado em `config.js` no start do container. | `ws://localhost:9001` |
| `HISTORY_MAX_POINTS` | Tamanho máximo do buffer circular de histórico por métrica. | `300` |

Nenhuma credencial é passada por variável de ambiente — elas só existem na aba.

## Como subir

O serviço é adicionado à `sida_network` existente via **override**, sem tocar no
`docker-compose.yml` original:

```bash
# na raiz do repositório
BROKER_WS_URL=wss://seu-broker:9001 docker compose up -d sida-uns-client
# UI em http://localhost:8080
```

Ou standalone:

```bash
docker build -t sida-uns-client ./sida-uns-client
docker run -e BROKER_WS_URL=wss://seu-broker:9001 -p 8080:80 sida-uns-client
```docker run -e BROKER_WS_URL=ws://34.134.241.250:9001 -p 8080:80 sida-uns-client
```

## Estrutura

```
sida-uns-client/
├── src/
│   ├── auth/session.js        # credenciais em memória (nunca persistidas)
│   ├── mqtt/client.js         # WebSocket, subscribe spBv1.0/#, reconexão c/ backoff
│   ├── sparkplug/             # sparkplug_b.proto + decoder.js (Protobuf -> métricas)
│   ├── state/store.js         # device_tree, node_liveness, alias_table, buffer (regras 5.2)
│   ├── ui/                    # login, árvore, gráficos canvas, dashboard
│   ├── app.js                 # bootstrap
│   └── index.html
├── test/                      # teste de aceite (SDD 3.1) containerizado
├── Dockerfile                 # multi-stage: vendoriza mqtt.js/protobufjs -> nginx
├── docker-entrypoint.sh       # injeta BROKER_WS_URL em config.js
└── nginx.conf
```

## Teste de aceite (SDD 3.1)

Totalmente containerizado — não requer Node/Python/navegador no host, e usa um
broker Mosquitto **isolado** (sem relação com produção):

```bash
./sida-uns-client/test/run.sh
```

Sobe `Mosquitto (WS+TCP)` + `sida-uns-client` + um runner **Playwright** que
publica a sequência `NBIRTH → DBIRTH → DDATA → DDATA → NDEATH` e verifica no DOM:
descoberta da árvore, primeiro ponto com valor/unidade, métrica booleana,
atualização incremental de DDATA, e sinalização de NDEATH sem apagar o histórico.
Cobre ainda os casos 2 (credenciais inválidas), 3 (DDATA sem NBIRTH), 5 (payload
corrompido) e 6 (rebirth). Exit code 0 = todos os passos passaram.
