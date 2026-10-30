# Guia Auto-Instrucional: Implementação do SIDA-Middleware

## Sobre este Guia

Este guia foi desenhado para ser **completamente autossuficiente**: você não precisará pausar a leitura para buscar tutoriais externos. Cada conceito de protocolo, padrão arquitetural, sintaxe de linguagem e ferramenta é explicado **no exato momento em que aparece**, contextualizado pelo problema que ele resolve.

Ao concluir, você terá construído o **SIDA** (_Smart Industrial DataOps Agent_) e compreendido as decisões de design que tornam cada componente necessário.

---

## Checklist de Tarefas: GitHub Project

Esta seção contém todas as tarefas necessárias para concluir o projeto, organizadas na ordem de execução. Cada item é **atômico** — representa uma entrega única e verificável.

### Como adicionar estas tarefas ao GitHub Project

1. **Crie o repositório** em [github.com/new](https://github.com/new) com o nome `sida-middleware`.
2. **Crie um Project** vinculado ao repositório:
   - Acesse a aba **Projects** no repositório → clique em **New project**.
   - Escolha o template **Board** (Kanban) ou **Table**, conforme preferir.
   - Nomeie o projeto (ex: `SIDA Middleware — Implementação`).
3. **Adicione as tarefas como Issues** e as vincule ao Project:
   - Para cada tarefa abaixo, acesse **Issues → New issue**.
   - Use o título exato da tarefa como título da issue.
   - No corpo da issue, cole a descrição correspondente.
   - Ao criar, clique em **Projects** (barra lateral direita) e selecione o project criado.
   - A issue aparecerá automaticamente no board na coluna **Todo**.
4. **Organize o board** criando as colunas: `Todo` → `In Progress` → `Done`. Mova cada card conforme avançar no guia.

> **💡 Dica:** você pode criar todas as issues de uma vez antes de começar a implementar, usando o GitHub CLI com o comando `gh issue create --title "TÍTULO" --body "DESCRIÇÃO" --project "NOME DO PROJECT"`. Isso agiliza bastante a configuração inicial.

---

### Épico 1 — Entendimento e Planejamento

- [ ] **[SIDA-01] Ler e compreender o cenário industrial do SIDA**
  Estudar a seção 1.1: entender o problema de heterogeneidade de CLPs, os protocolos Modbus TCP / OPC UA / S7, e o conceito de dado bruto sem contexto semântico.

- [ ] **[SIDA-02] Compreender a arquitetura em 3 camadas**
  Estudar a seção 1.2: identificar a responsabilidade de cada camada (Ingestão, Context Engine, Delivery) e o papel do `sida-core` como API central. Desenhar o diagrama no caderno antes de prosseguir.

- [ ] **[SIDA-03] Mapear a estrutura de diretórios do projeto**
  Estudar a seção 2: entender o que reside em cada pasta (`core/`, `sida-core/`, `infra/`) e a relação entre os arquivos antes de criar qualquer código.

---

### Épico 2 — Camada 1: Ingestão

- [ ] **[SIDA-04] Criar o fluxo da Camada 1 no Node-RED**
  Abrir a interface do Node-RED (`http://localhost:1881`) e criar a aba "Camada 1: Ingestão" com os 5 nós conforme o mapa visual da seção 3.1.

- [ ] **[SIDA-05] Adicionar e configurar o nó ZMQ SUB (Manifesto)**
  Instalar o pacote `node-red-contrib-zeromq` via Paleta de Nós. Adicionar o nó `zmq sub` configurado para escutar `tcp://sida-core:5556`.

- [ ] **[SIDA-06] Implementar o nó Function `setupModbus`**
  Escrever o código JavaScript do nó `setupModbus`: iterar sobre as áreas, linhas e dispositivos do Manifesto, e instanciar os clientes Modbus TCP para cada equipamento habilitado (`dev.enabled === true`).

- [ ] **[SIDA-07] Configurar o nó Inject (Gatilho de Polling)**
  Adicionar o nó `Inject` e configurá-lo para disparar em intervalo fixo (ex: 1 segundo), gerando o pulso de ativação cíclica do sistema.

- [ ] **[SIDA-08] Implementar o nó Function `Polling`**
  Escrever o código JavaScript do nó `Polling`: ler os clientes Modbus da memória global, executar `readHoldingRegisters` para cada registrador mapeado (aplicando o ajuste de offset `address -= 40001`) e montar o JSON de dados brutos com `Date.now()`.

- [ ] **[SIDA-09] Adicionar e conectar o nó ZMQ PUSH (Ingestion)**
  Adicionar o nó `zmq push` configurado para `ipc:///tmp/.ipc/ingestion.ipc` e conectá-lo à saída do nó `Polling`.

- [ ] **[SIDA-10] Verificar o fluxo completo da Camada 1**
  Usar o painel de debug do Node-RED para confirmar que mensagens com `timestamp`, `gateway_id` e `data` estão sendo geradas e enviadas corretamente pelo ZMQ PUSH.

---

### Épico 3 — Camada 2: Context Engine

- [ ] **[SIDA-11] Criar o fluxo da Camada 2 no Node-RED**
  Criar a aba "Camada 2: Context" com os 3 nós em série conforme o mapa visual da seção 3.2.

- [ ] **[SIDA-12] Adicionar e configurar o nó ZMQ PULL (Context)**
  Adicionar o nó `zmq pull` configurado para consumir de `ipc:///tmp/.ipc/ingestion.ipc`.

- [ ] **[SIDA-13] Implementar o nó Function `EnrichContext`**
  Escrever o código JavaScript de enriquecimento: usar `pathArray.find()` para extrair os identificadores ISA-95 (enterprise, site, area, line, equipment) e injetar o caminho completo e o `groupId` no payload de saída.

- [ ] **[SIDA-14] Adicionar e conectar o nó ZMQ PUSH (Context)**
  Adicionar o nó `zmq push` configurado para `ipc:///tmp/.ipc/context.ipc` e conectá-lo à saída do `EnrichContext`.

- [ ] **[SIDA-15] Verificar enriquecimento de contexto**
  Usar o debug do Node-RED para confirmar que o payload de saída da Camada 2 contém os campos ISA-95 (`groupId`, `nodeId`, `deviceId`) corretamente preenchidos.

---

### Épico 4 — Camada 3: Delivery

- [ ] **[SIDA-16] Criar o fluxo da Camada 3 no Node-RED**
  Criar a aba "Camada 3: Delivery" com os 4 nós sequenciais conforme o mapa visual da seção 3.3.

- [ ] **[SIDA-17] Adicionar e configurar o nó ZMQ PULL (Delivery)**
  Adicionar o nó `zmq pull` configurado para consumir de `ipc:///tmp/.ipc/context.ipc`.

- [ ] **[SIDA-18] Implementar o nó Function `spbGenerator`**
  Escrever o código JavaScript de montagem do Unified Namespace: extrair os identificadores ISA-95 e gerar o `groupId` via template literal.

- [ ] **[SIDA-19] Implementar o nó Function `Payload Formatter`**
  Escrever o código de conversão de tipos Sparkplug B usando `.map()`: mapear cada métrica bruta para o tipo correto (Float, Boolean, String) e montar o tópico MQTT no formato `spBv1.0/{groupId}/DDATA/{nodeId}/{deviceId}`.

- [ ] **[SIDA-20] Configurar o nó MQTT Out**
  Adicionar o nó `mqtt out`, configurar a conexão com o Broker MQTT externo e deixar o campo "Tópico" vazio (o tópico será lido dinamicamente de `msg.topic`).

- [ ] **[SIDA-21] Verificar publicação MQTT end-to-end**
  Usar um cliente MQTT (ex: MQTT Explorer ou `mosquitto_sub`) para confirmar que mensagens Sparkplug B estão chegando no broker com o tópico e payload corretos.

---

### Épico 5 — SIDA-Core (Go)

- [ ] **[SIDA-22] Estruturar o projeto Go com Clean Architecture**
  Criar os diretórios `cmd/server/`, `internal/adapters/handler/`, `internal/adapters/repository/` e `internal/core/services/`. Inicializar o módulo com `go mod init sida-core`.

- [ ] **[SIDA-23] Implementar o repositório SQLite (`repository.go`)**
  Escrever a struct `sqliteManifestRepo` e o método `Save` com a query de Upsert (`ON CONFLICT DO UPDATE`). Garantir que o banco crie a tabela `edge_manifests` na inicialização.

- [ ] **[SIDA-24] Implementar o publisher ZeroMQ (`zmq_publisher.go`)**
  Escrever a struct `ZMQPublisher` e o método `PublishUpdate` que envia o sinal `"RELOAD"` no tópico `sida/manifest/{gatewayID}` via socket PUB.

- [ ] **[SIDA-25] Implementar o handler HTTP (`handler.go`)**
  Escrever o handler `UploadManifest`: receber o JSON via POST, persistir via repositório e acionar o publisher ZeroMQ.

- [ ] **[SIDA-26] Implementar o ponto de entrada (`main.go`)**
  Instanciar o repositório, o publisher e o handler; injetar as dependências; configurar as rotas do Gin e subir o servidor na porta 8000.

- [ ] **[SIDA-27] Testar o endpoint de saúde da API**
  Executar `curl http://localhost:8000/api/health` e confirmar resposta `{"status":"UP"}`.

- [ ] **[SIDA-28] Testar o upload de Manifesto e a propagação via ZeroMQ**
  Enviar um Manifesto de exemplo via `curl -X POST` e verificar nos logs do Node-RED que o nó `ZMQ SUB` recebeu o sinal `RELOAD` e o `setupModbus` reconectou os CLPs.

---

### Épico 6 — Infraestrutura Docker

- [ ] **[SIDA-29] Escrever o Dockerfile com Multi-Stage Build**
  Criar o `Dockerfile` do `sida-core` com dois estágios: `builder` (compilação Go) e `runtime` (Alpine), copiando apenas o binário final entre os estágios.

- [ ] **[SIDA-30] Escrever o `docker-compose.yml`**
  Declarar os serviços `sida-core`, `poc-ingestion`, `poc-context` e `poc-delivery` com suas portas, volumes, networks e as dependências de inicialização (`depends_on`).

- [ ] **[SIDA-31] Configurar o volume compartilhado `sida_ipc`**
  Garantir que o volume nomeado `sida_ipc` esteja mapeado em `/tmp/.ipc` em todos os containers Node-RED, habilitando a comunicação ZeroMQ IPC entre eles.

- [ ] **[SIDA-32] Executar `docker-compose up --build` e validar todos os containers**
  Rodar o comando de build completo e verificar com `docker-compose ps` que todos os containers estão com status `healthy` ou `running`.

---

### Épico 7 — Validação Final

- [ ] **[SIDA-33] Executar teste de integração ponta a ponta**
  Com todos os containers ativos, subir um simulador de CLP Modbus (ex: `diagslave` ou `ModRSsim2`), enviar um Manifesto apontando para ele, e confirmar que a leitura percorre as 3 camadas até chegar como mensagem Sparkplug B no broker MQTT.

- [ ] **[SIDA-34] Validar tamanho das imagens Docker geradas**
  Executar `docker images` e confirmar que a imagem do `sida-core` está abaixo de 60 MB, evidenciando o resultado do Multi-Stage Build.

- [ ] **[SIDA-35] Revisar e documentar o projeto no README**
  Escrever o `README.md` do repositório com: descrição do SIDA, diagrama de arquitetura, pré-requisitos, instruções de execução e tabela de portas.

---

## Parte 1: O Desafio e a Arquitetura SIDA

### 1.1 O Cenário: Por Que Precisamos de um Middleware Industrial?

Imagine o chão de fábrica de uma grande indústria. Existem Controladores Lógicos Programáveis (CLPs) da Siemens, da Rockwell e da Schneider. Cada fabricante desenvolveu seu próprio protocolo de comunicação ao longo de décadas: Modbus TCP, OPC UA, S7. Além disso, os CLPs geram dados brutos sem qualquer contexto semântico — o valor decimal `60.5` na posição de memória `40001` não diz se é uma temperatura, uma pressão ou a velocidade de um motor.

> **💡 O que é um CLP?** Um Controlador Lógico Programável é um computador industrial robusto que controla máquinas e processos. Diferente de um PC, ele opera em tempo real e suporta condições adversas como vibração, temperatura extrema e interferência elétrica. Sua memória é dividida em registradores numerados que guardam leituras de sensores e estados de atuadores.

O problema é claro: como integrar equipamentos heterogêneos de chão de fábrica com sistemas modernos de nuvem, ERPs e dashboards?

O **SIDA** é um middleware de _Edge Computing_ que resolve exatamente isso. Ele atua como um tradutor e organizador, transformando dados brutos em informações estruturadas e prontas para consumo, utilizando dois padrões industriais:

- **Unified Namespace (UNS):** um modelo de organização de dados baseado na hierarquia física da planta industrial.
- **ISA-95:** norma internacional que define como organizar a estrutura de uma empresa industrial em camadas (Empresa → Fábrica → Área → Linha → Equipamento).

> **💡 O que é Edge Computing?** É o paradigma de processar dados próximo de onde eles são gerados — no "borde" da rede — em vez de enviá-los todos para a nuvem antes de qualquer tratamento. No contexto industrial, um gateway de borda (como o SIDA) reduz latência, economiza banda de rede e funciona mesmo com conectividade instável.

### 1.2 Arquitetura em 3 Camadas

O SIDA opera de forma modular através de microsserviços integrados. Cada camada tem uma responsabilidade única e se comunica com a próxima via mensageria de alta velocidade:

```
┌─────────────────────────────────────────────────────────────┐
│                      SIDA Architecture                      │
├─────────────────────────────────────────────────────────────┤
│  Camada 1: Ingestão (Node-RED)                              │
│  Lê registros brutos dos CLPs via Modbus TCP                │
│                                                             │
│  Camada 2: Context Engine (Node-RED + ISA-95)               │
│  Organiza os dados em: Empresa > Fábrica > Área > Linha     │
│                                                             │
│  Camada 3: Delivery (Node-RED + Sparkplug B)                │
│  Compacta os dados e publica via MQTT para a Nuvem          │
└─────────────────────────────────────────────────────────────┘
                             ▲
                             │ Configurações via ZeroMQ
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      SIDA-Core (Go)                         │
│     API REST central que gerencia os manifestos e regras    │
└─────────────────────────────────────────────────────────────┘
```

> **💡 O que é um Microsserviço?** É um estilo arquitetural onde cada componente do sistema roda como um processo independente, com sua própria responsabilidade bem definida. A vantagem é que você pode atualizar, escalar ou reiniciar o serviço de ingestão sem afetar o de contexto ou o de entrega.

---

## Parte 2: Estrutura do Projeto

Antes de começar a codificar, entenda como o código está organizado no repositório. Essa visão de alto nível ajuda a navegar pelo projeto durante a implementação:

```
sida-middleware/
├── core/                   # Fluxos visuais do Node-RED
│   ├── ingestion/          # Camada 1: Coleta de dados Edge
│   ├── context/            # Camada 2: Motor de Contexto (ISA-95)
│   └── delivery/           # Camada 3: Envio Cloud (Sparkplug B)
├── sida-core/              # API Central desenvolvida em Go
│   ├── cmd/server/main.go  # Ponto de entrada da aplicação
│   ├── internal/           # Lógica de negócio e adaptadores
│   └── go.mod              # Dependências do Go
├── infra/                  # Infraestrutura Docker
└── docker-compose.yml      # Orquestrador de todos os serviços
```

> **💡 O que é o Node-RED?** É uma plataforma de programação visual baseada em Node.js. Em vez de escrever todo o código manualmente, você arrasta e conecta "nós" (nodes) em um editor gráfico, formando fluxos de processamento de dados. Cada nó tem uma entrada, uma saída e pode conter código JavaScript personalizado. É amplamente utilizado em automação industrial e IoT.

---

## Parte 3: Implementação Detalhada

Esta é a seção central do guia. Cada camada é apresentada com três elementos integrados:

1. **O que o código faz** — explicação contextual do problema e da solução.
2. **O código comentado** — implementação com anotações explicativas.
3. **O fluxo visual no Node-RED** — como conectar os nós na interface gráfica para que o código ganhe vida.

> **💡 Por que integrar código e fluxo visual juntos?** No Node-RED, a lógica de um fluxo só faz sentido completo quando você entende tanto o _o que o código dentro do nó faz_ quanto _como os nós se conectam entre si_. Estudar um sem o outro deixa lacunas.

---

### 3.1 Camada 1: Ingestão Dinâmica

**O problema:** precisamos conectar-nos a múltiplos CLPs de fabricantes diferentes, com endereços IP, portas e taxas de leitura distintas — e fazer isso de forma dinâmica, sem reiniciar o sistema quando uma configuração muda.

**A solução:** o Node-RED lê um arquivo de configuração central (o **Manifesto**) enviado pelo `sida-core`, abre conexões TCP com cada CLP habilitado e realiza leituras cíclicas (_polling_) em seus registradores de memória.

#### Mapa Visual do Fluxo

Este é o diagrama da aba **Camada 1: Ingestão** no editor do Node-RED. Antes de implementar os nós, visualize o fluxo completo:

```
[ZMQ SUB (Manifesto)] ───> [setupModbus (Function)]
                                      │
                           (dados salvos na memória global)
                                      │
                                      ▼
[Gatilho (Inject)] ──────> [Polling (Function)] ───> [ZMQ PUSH (Ingestion)]
```

O fluxo tem **duas "pernas" independentes** que se comunicam pela memória global do Node-RED: a perna superior recebe e processa a configuração; a perna inferior executa leituras cíclicas usando essa configuração.

#### Nó 1: ZMQ SUB (Manifesto)

- **Tipo do Nó:** `zmq sub` — adicione via Paleta de Nós buscando por `node-red-contrib-zeromq`.
- **Para que serve:** Funciona como um receptor de rádio permanentemente sintonizado. Ele fica escutando a porta TCP 5556 do container `sida-core`. Sempre que uma configuração de fábrica (Manifesto) é criada ou alterada na API, este nó captura o novo JSON automaticamente.
- **Conexão:** ligue a **saída** deste nó na **entrada** do nó `setupModbus`.

> **💡 O que é ZeroMQ (ZMQ)?** É uma biblioteca de mensageria de altíssima performance que cria sockets persistentes sobre TCP ou IPC (Inter-Process Communication). Diferente do HTTP tradicional, que exige uma negociação (_handshake_) a cada requisição, o ZeroMQ mantém canais abertos e transfere mensagens com latência mínima — ideal para sincronização em tempo real entre microsserviços.

> **💡 O padrão PUB/SUB:** No modelo Publisher/Subscriber, um publicador (o `sida-core` em Go) transmite mensagens para um canal. Todos os assinantes (as camadas do Node-RED) que estão escutando aquele canal recebem a mensagem simultaneamente. Nenhum assinante precisa "pedir" — eles são notificados automaticamente quando há novidade.

#### Nó 2: setupModbus (Function)

- **Tipo do Nó:** `Function` — nó nativo do Node-RED para executar JavaScript personalizado.
- **Para que serve:** Recebe o Manifesto JSON, armazena-o na memória de longo prazo do Node-RED (`global.set(...)`) e instancia os clientes de comunicação Modbus TCP para cada equipamento habilitado.
- **Conexão:** recebe dados na **entrada** vindo do `ZMQ SUB`. Como sua função é preparar o ambiente e salvar na memória global — que outros nós consultarão de forma independente —, **não há fios conectados à sua saída**.

```javascript
// Recupera o Manifesto que acabou de chegar via ZeroMQ
const manifest = global.get("manifest");

const areas = manifest.config.plant.areas;

for (const areaId of Object.keys(areas)) {
    const lines = areas[areaId].lines;

    for (const lineId of Object.keys(lines)) {
        const devices = lines[lineId].devices;

        for (const deviceId of Object.keys(devices)) {
            const dev = devices[deviceId];

            if (dev.enabled && dev.connection.protocol === "modbus_tcp") {
                const client = new ModbusRTU();

                // Conexão assíncrona ao CLP via TCP
                await client.connectTCP(dev.connection.host, { port: dev.connection.port });
                client.setID(dev.connection.unit_id);
            }
        }
    }
}
```

> **💡 `Object.keys(areas)`:** Quando trabalhamos com configurações vindas de JSON, os equipamentos costumam ser representados como propriedades de um objeto (`{ "clp_01": {...}, "clp_02": {...} }`). `Object.keys()` converte essas propriedades em um array de strings (`["clp_01", "clp_02"]`), permitindo iterar sobre elas com `for...of`.

> **💡 `async/await`:** A instrução `connectTCP` envolve comunicação de rede — ela pode levar dezenas de milissegundos para completar. Se o JavaScript esperasse esse tempo de forma bloqueante, nenhuma outra tarefa seria executada no meio tempo, travando o sistema inteiro. O `await` instrui o motor do Node.js a pausar *apenas essa função*, liberando a thread principal para outras tarefas enquanto aguarda a resposta da rede. O `async` na assinatura da função sinaliza que ela pode conter operações `await`.

#### Nó 3: Gatilho (Inject)

- **Tipo do Nó:** `Inject` — nó nativo de injeção de fluxos.
- **Para que serve:** É o "metrônomo" do sistema. Configure-o nas propriedades visuais para disparar repetidamente em um intervalo fixo (ex: a cada 1 segundo), enviando um timestamp simples que serve apenas como sinal de "hora de ler".
- **Conexão:** ligue a **saída** deste nó na **entrada** do nó `Polling`.

#### Nó 4: Polling (Function)

- **Tipo do Nó:** `Function`.
- **Para que serve:** É o coração da coleta. Cada vez que o nó Gatilho dispara, o código acorda, lê da memória global a lista de conexões com os CLPs, executa a varredura física dos registradores de memória (`readHoldingRegisters`) e monta um JSON de dados brutos com carimbo de tempo.
- **Conexão:** recebe o pulso na **entrada** vindo do Gatilho. Ligue a **saída** na **entrada** do nó `ZMQ PUSH (Ingestion)`.

```javascript
// Itera sobre todos os CLPs que têm conexão ativa
Object.keys(active_clients).forEach((deviceId) => {
    const { client, config, gateway_id } = active_clients[deviceId];

    const scanRate = config.connection.scan_rate_ms;

    setInterval(async () => {
        let data_payload = {};

        for (let addrKey of Object.keys(config.metrics_mapping)) {
            let address = parseInt(addrKey);

            // Conversão do endereço comercial Modbus para o endereço real de rede
            if (address >= 40001 && address <= 49999) address -= 40001;

            // Leitura do Holding Register do CLP
            let data = await client.readHoldingRegisters(address, 1);
            data_payload[addrKey] = data.data[0];
        }

        node.send({
            payload: {
                timestamp: Date.now(),
                gateway_id: gateway_id,
                source: { device_id: deviceId },
                data: data_payload
            }
        });

    }, scanRate);
});
```

> **💡 `setInterval(..., scanRate)`:** Registra uma função para ser executada repetidamente no intervalo definido em `scanRate` (em milissegundos). Cada CLP pode ter sua própria taxa de leitura configurada no Manifesto — um sensor crítico pode ser lido a cada 100ms, enquanto um medidor de energia pode ser consultado a cada 5 segundos.

> **💡 O ajuste `address -= 40001`:** No protocolo Modbus, os Holding Registers são referenciados comercialmente no intervalo 40001–49999. Porém, no datagrama TCP real que trafega na rede, o primeiro registrador é identificado como endereço `0`. Essa subtração faz a conversão do endereço "legível pelo ser humano" para o endereço "entendido pelo protocolo".

#### Nó 5: ZMQ PUSH (Ingestion)

- **Tipo do Nó:** `zmq push` — do pacote `node-red-contrib-zeromq`.
- **Para que serve:** Pega o JSON estruturado pelo nó `Polling` e despacha para fora do container por um canal de alta velocidade baseado em IPC (_Inter-Process Communication_), no endereço `ipc:///tmp/.ipc/ingestion.ipc`.
- **Conexão:** ligue a **entrada** na **saída** do nó `Polling`. Este nó encerra o fluxo da Camada 1, portanto sua saída fica livre.

> **💡 IPC vs. TCP:** A comunicação por IPC (arquivos de socket no sistema operacional) é drasticamente mais rápida que TCP entre containers, porque os dados não passam pela pilha de rede virtual do Docker — eles são copiados diretamente na memória do sistema. Usamos IPC para a comunicação *interna* entre camadas do SIDA e TCP apenas para comunicação com o `sida-core`, que corre em um processo separado.

---

### 3.2 Camada 2: Context Engine (ISA-95)

**O problema:** o dado bruto que saiu da Camada 1 é uma sequência de bytes anônimos (`40001 = 60.5`). Ele não carrega informação sobre de qual equipamento veio, em qual linha de produção esse equipamento opera, ou em qual área da fábrica aquela linha está instalada.

**A solução:** a Camada 2 cruza o ID do equipamento com o Manifesto de configuração e injeta no payload o caminho completo segundo a norma ISA-95, transformando o dado bruto em um dado **contextualizado**.

#### Mapa Visual do Fluxo

Na aba **Camada 2: Context** do Node-RED, o fluxo é linear e composto por **3 nós em série**:

```
[ZMQ PULL (Context)] ───> [EnrichContext (Function)] ───> [ZMQ PUSH (Context)]
```

#### Nó 1: ZMQ PULL (Context)

- **Tipo do Nó:** `zmq pull`.
- **Para que serve:** É a porta de entrada da Camada 2. Fica escutando o arquivo de socket `ipc:///tmp/.ipc/ingestion.ipc` e consome instantaneamente as mensagens enviadas pelo nó terminal da Camada 1.
- **Conexão:** ligue a **saída** na **entrada** do nó `EnrichContext`.

> **💡 O padrão PUSH/PULL:** Enquanto PUB/SUB distribui a mesma mensagem para todos os assinantes, o padrão PUSH/PULL cria uma fila de trabalho. O nó PUSH envia; o nó PULL consome. Se houver múltiplos consumidores PULL, o ZeroMQ distribui as mensagens entre eles de forma balanceada — útil para escalar o processamento.

#### Nó 2: EnrichContext (Function)

- **Tipo do Nó:** `Function`.
- **Para que serve:** Contém a lógica de enriquecimento semântico. Lê o ID do equipamento, busca no Manifesto global as informações de sua localização física e injeta no payload o caminho completo segundo ISA-95.
- **Conexão:** recebe na **entrada** do `ZMQ PULL`. Ligue a **saída** na **entrada** do `ZMQ PUSH (Context)`.

```javascript
const payloadIn = msg.payload;

// O caminho ISA-95 é um array de objetos: [{type:"enterprise", id:"acme"}, {type:"site", id:"planta_sp"}, ...]
const pathArray = payloadIn.asset_context.path;

// Função auxiliar: busca o identificador de um nível específico da hierarquia
const getContextId = (targetType) => {
    const item = pathArray.find(p => p.type === targetType);
    return item ? item.id : "unknown";
};

const enterprise = getContextId("enterprise");
const site       = getContextId("site");
const area       = getContextId("area");

// Montagem do identificador de grupo no Unified Namespace
const groupId = `${enterprise}_${site}_${area}`;
const nodeId   = getContextId("line");
const deviceId = getContextId("equipment");
```

> **💡 `pathArray.find(...)`:** O método `.find()` percorre um array e retorna o **primeiro elemento** que satisfaz o critério da função passada como argumento. Aqui, buscamos o objeto cujo campo `type` seja igual ao tipo desejado (ex: `"enterprise"`). Se não encontrar, retornamos `"unknown"` como valor-padrão — uma prática defensiva para evitar que `undefined` quebre o fluxo.

> **💡 Template Literals `` `${...}` ``:** Permitem construir strings com variáveis embutidas de forma legível. O resultado `"acme_planta_sp_linha_a"` é o identificador de grupo que identifica unicamente aquele trecho da fábrica no barramento MQTT — sem concatenação com `+` e sem risco de esquecimento de separadores.

> **💡 A Norma ISA-95:** Define uma hierarquia padrão para representar a estrutura de plantas industriais: Empresa (_Enterprise_) → Sítio/Fábrica (_Site_) → Área → Linha de Produção → Equipamento. Ao organizar os dados nessa hierarquia, qualquer sistema externo — de um ERP a um dashboard — consegue entender de onde o dado veio sem precisar de documentação adicional.

#### Nó 3: ZMQ PUSH (Context)

- **Tipo do Nó:** `zmq push`.
- **Para que serve:** Encaminha o pacote de dados completamente contextualizado para a Camada 3 pelo canal `ipc:///tmp/.ipc/context.ipc`.
- **Conexão:** ligue a **entrada** na **saída** do `EnrichContext`. É o nó final desta aba.

---

### 3.3 Camada 3: Delivery (Unified Namespace & Sparkplug B)

**O problema:** sistemas de nuvem industriais não falam o mesmo idioma de dados brutos dos CLPs. Eles esperam mensagens em um formato padronizado, com tipagem explícita, publicadas em endereços de tópico que sigam uma convenção reconhecível.

**A solução:** a Camada 3 converte os dados contextualizados para o padrão **Sparkplug B** e os publica em um Broker MQTT externo (ex: na nuvem GCP) usando o esquema de tópicos do **Unified Namespace**.

#### Mapa Visual do Fluxo

Na aba **Camada 3: Delivery** do Node-RED, o fluxo tem **4 nós sequenciais**:

```
[ZMQ PULL (Delivery)] ───> [spbGenerator (Function)] ───> [Payload Formatter (Function)] ───> [MQTT Out]
```

#### Nó 1: ZMQ PULL (Delivery)

- **Tipo do Nó:** `zmq pull`.
- **Para que serve:** Captura os dados ricos em contexto postados pela Camada 2 no canal `ipc:///tmp/.ipc/context.ipc`.
- **Conexão:** ligue a **saída** na **entrada** do nó `spbGenerator`.

#### Nó 2: spbGenerator (Function)

- **Tipo do Nó:** `Function`.
- **Para que serve:** Percorre o caminho ISA-95 e gera dinamicamente o identificador de grupo (`groupId`) no esquema do Unified Namespace.
- **Conexão:** recebe na **entrada** do `ZMQ PULL`. Ligue a **saída** na **entrada** do `Payload Formatter`.

```javascript
const payloadIn = msg.payload;
const pathArray = payloadIn.asset_context.path;

const getContextId = (targetType) => {
    const item = pathArray.find(p => p.type === targetType);
    return item ? item.id : "unknown";
};

const enterprise = getContextId("enterprise");
const site       = getContextId("site");
const area       = getContextId("area");

// Gera o identificador de grupo do Unified Namespace
const groupId  = `${enterprise}_${site}_${area}`;
const nodeId   = getContextId("line");
const deviceId = getContextId("equipment");

msg.uns = { groupId, nodeId, deviceId };
return msg;
```

#### Nó 3: Payload Formatter (Function)

- **Tipo do Nó:** `Function`.
- **Para que serve:** Converte as métricas brutas para os tipos de dados aceitos pelo padrão Sparkplug B e monta o endereço de tópico MQTT definitivo.
- **Conexão:** recebe na **entrada** do `spbGenerator`. Ligue a **saída** na **entrada** do `MQTT Out`.

```javascript
const dataRaw = msg.payload.data;
const { groupId, nodeId, deviceId } = msg.uns;

// Conversão de tipos: cada métrica precisa de tipagem explícita no Sparkplug B
const dataMetrics = dataRaw.map(item => {
    let sparkplugType = "String"; // Tipo padrão seguro

    const explicitType = item.data_type.toLowerCase();

    if (explicitType === "float")   sparkplugType = "Float";
    else if (explicitType === "boolean") sparkplugType = "Boolean";

    return {
        name:      item.name,
        value:     item.value,
        type:      sparkplugType,
        timestamp: Date.now()
    };
});

// Montagem do tópico MQTT no padrão Sparkplug B
msg.topic   = `spBv1.0/${groupId}/DDATA/${nodeId}/${deviceId}`;
msg.payload = { metrics: dataMetrics };

return msg;
```

> **💡 `.map()`:** É um método de programação funcional que transforma cada elemento de um array aplicando uma função e retorna um *novo* array com os resultados. Diferente de um `for` que modifica o array original, `.map()` é imutável — o array de entrada (`dataRaw`) permanece intacto. É a forma idiomática de converter listas de dados industriais em formatos padronizados.

> **💡 Sparkplug B:** É uma especificação publicada pela Eclipse Foundation que define como estruturar payloads MQTT para automação industrial. Ela exige tipagem explícita de cada métrica (Float, Boolean, String, etc.) e padroniza o esquema de tópicos: `spBv1.0/{groupId}/{messageType}/{nodeId}/{deviceId}`. O tipo `DDATA` significa _Device Data_ — dados periódicos de telemetria. Com esse padrão, qualquer sistema de nuvem que "fala" Sparkplug B processa o payload sem engenharia reversa.

#### Nó 4: MQTT Out

- **Tipo do Nó:** `mqtt out` — nó de rede nativo do Node-RED.
- **Para que serve:** Mantém um túnel TCP persistente com o Broker MQTT externo (ex: EMQX na nuvem GCP) e publica o payload no tópico gerado dinamicamente em `msg.topic` pelo nó anterior. Ao configurar o nó, deixe o campo "Tópico" em branco — ele usará o valor de `msg.topic`.
- **Conexão:** ligue a **entrada** na **saída** do `Payload Formatter`. Este nó é o ponto final absoluto de toda a arquitetura de processamento do SIDA-Middleware.

> **💡 MQTT:** É um protocolo de mensageria leve baseado no padrão publicador/assinante, projetado para redes com largura de banda limitada e dispositivos com pouca memória — características comuns em ambientes industriais e IoT. Um Broker MQTT (como o EMQX ou o Mosquitto) centraliza o roteamento: quem publica em um tópico não sabe quem está assinando, e vice-versa.

---

### 3.4 O Core do Sistema: SIDA-Core (Go)

**O problema:** precisamos de uma API central que persista as configurações de configuração (_manifestos_) das fábricas em um banco de dados local e notifique as camadas Node-RED instantaneamente quando uma configuração muda — tudo isso com alta performance e baixo consumo de recursos.

**A solução:** escrevemos a API em **Go**, uma linguagem compilada projetada para concorrência e networking de alta eficiência. A API segue os princípios da **Clean Architecture**.

> **💡 Por Go e não Python ou Node.js?** Go compila para um binário estático nativo — sem runtime externo, sem interpretador. O resultado é uma aplicação que inicia em milissegundos, consome poucos megabytes de RAM e lida com milhares de conexões simultâneas sem dificuldade. Em dispositivos de borda com recursos limitados, essas características fazem diferença real.

> **💡 Clean Architecture:** É um padrão de organização de código que separa rigidamente a lógica de negócio (o que o sistema *faz*) dos detalhes de infraestrutura (como o banco de dados ou o protocolo de transporte). Se amanhã você quiser trocar o SQLite por PostgreSQL, ou o ZeroMQ por outro mecanismo de mensageria, apenas os adaptadores externos mudam — a lógica central permanece intacta.

#### O Arquivo Principal: `main.go`

Responsável por instanciar os repositórios, injetar as dependências e iniciar o servidor HTTP.

```go
package main

import (
    "net/http"
    "sida-core/internal/adapters/handler"
    "sida-core/internal/adapters/repository"
    "sida-core/internal/core/services"
    "github.com/gin-gonic/gin"
)

func main() {
    // Inicializa o banco SQLite local de borda
    repo, _ := repository.NewSQLiteManifestRepository("./data/sida_config.db")

    // Inicializa o barramento ZeroMQ para notificar os nós Node-RED em tempo real
    zmqPub, _ := services.NewZMQPublisher("0.0.0.0:5556")

    // Injeta as dependências no handler HTTP
    manifestHandler := handler.NewManifestHandler(repo, zmqPub)

    router := gin.Default()
    router.POST("/api/config/manifest", manifestHandler.UploadManifest)

    srv := &http.Server{Addr: ":8000", Handler: router}
    srv.ListenAndServe()
}
```

> **💡 Operador `:=` (Short Variable Declaration):** Em Go, você não precisa declarar o tipo da variável explicitamente se a inicializar no momento da criação. `repo := repository.New...` cria a variável e infere seu tipo a partir do retorno da função. É a forma idiomática de criar variáveis locais em Go.

> **💡 O identificador `_` (Blank Identifier):** Em Go, toda função que pode falhar retorna **dois valores**: o dado e um objeto de erro. O compilador exige que você use todos os valores retornados — ou descarte explicitamente os que não usará. O `_` sinaliza ao compilador: "estou ciente de que há um segundo valor de retorno e estou intencionalmente o ignorando". Em produção, nunca ignore erros; no exemplo acima, fazemos isso apenas para simplificar a leitura.

> **💡 Injeção de Dependências:** Em vez de cada componente criar suas próprias dependências internamente, elas são criadas fora e *injetadas* por parâmetro. O `manifestHandler` não sabe como o banco ou o ZeroMQ foram criados — ele apenas os usa. Isso torna o código testável: em testes unitários, você pode injetar versões falsas (mocks) dessas dependências.

#### O Padrão de Persistência: `repository.go`

Gerencia o armazenamento local usando SQLite com resiliência a falhas de conectividade.

```go
type sqliteManifestRepo struct {
    db *sql.DB
}

func (r *sqliteManifestRepo) Save(ctx context.Context, manifest domain.Manifest) error {
    configBytes, _ := json.Marshal(manifest.Config)

    // Upsert: insere ou atualiza atomicamente, sem checagem prévia
    query := `INSERT INTO edge_manifests (gateway_id, config, updated_at)
              VALUES (?, ?, ?)
              ON CONFLICT(gateway_id) DO UPDATE SET config=excluded.config`

    _, err := r.db.ExecContext(ctx, query, manifest.GatewayID, string(configBytes), manifest.UpdatedAt)
    return err
}
```

> **💡 `*sql.DB` — Ponteiro para Struct:** Em Go, variáveis de tipo struct são passadas por *valor* por padrão (uma cópia é criada). O `*` indica que `db` é um **ponteiro** — uma referência ao endereço de memória onde o objeto real reside. Passar um ponteiro evita a cópia desnecessária de grandes estruturas e permite que múltiplas partes do código operem sobre o mesmo objeto de conexão com o banco.

> **💡 `ON CONFLICT(...) DO UPDATE` (Upsert):** Um dispositivo de borda pode perder conexão ou reiniciar a qualquer momento. Quando o `sida-core` recebe novamente o Manifesto daquele gateway, ele não sabe se já existe um registro no banco ou não. Em vez de fazer um `SELECT` para verificar e depois decidir entre `INSERT` ou `UPDATE`, o Upsert combina as duas operações em uma única instrução SQL atômica: insira se não existir, atualize se já existir. Isso garante que a operação seja segura mesmo com reinicializações inesperadas.

#### Comunicação Inter-Microsserviços: ZeroMQ Publisher

```go
func (p *ZMQPublisher) PublishUpdate(gatewayID string) error {
    topic := "sida/manifest/" + gatewayID

    // Envia um sinal de recarga para todos os nós assinantes no Node-RED
    _, err := p.socket.SendMessage(topic, "RELOAD")
    return err
}
```

**Como a mensageria ZeroMQ funciona no SIDA:**

- **PUB/SUB (TCP, porta 5556):** O `sida-core` (Go) é o Publisher. Todas as instâncias do Node-RED são Subscribers. Quando uma configuração é alterada via API REST, o Go transmite `"RELOAD"` no barramento. Cada instância Node-RED recebe o sinal e se reconfigura dinamicamente, sem derrubar os containers.

- **PUSH/PULL (IPC):** Entre os blocos internos do Node-RED, usamos caminhos de socket em arquivos do sistema (`ipc:///tmp/.ipc/ingestion.ipc`). Os dados não passam pela pilha de rede TCP — eles são transferidos diretamente pela memória do host, com latência próxima de zero.

---

## Parte 4: Orquestração e Deploy com Docker

Para garantir que o ambiente seja **idêntico em qualquer máquina** — seja o notebook de desenvolvimento ou um computador industrial na fábrica —, usamos o Docker Compose para orquestrar todos os serviços.

> **💡 O que é Docker?** Uma tecnologia de conteinerização que empacota uma aplicação e todas as suas dependências em uma unidade isolada chamada container. O container roda de forma idêntica em qualquer sistema operacional que tenha o Docker instalado. Pense nele como uma "máquina virtual leve" com startup em segundos.

> **💡 O que é Docker Compose?** Uma ferramenta que permite definir e gerenciar múltiplos containers como um único serviço. Em vez de iniciar cada container manualmente com longos comandos, você descreve toda a infraestrutura em um arquivo YAML e sobe tudo com um único comando.

### 4.1 O Arquivo de Infraestrutura: `docker-compose.yml`

```yaml
version: '3.8'

networks:
  sida_network:
    driver: bridge           # Rede virtual privada entre os containers

volumes:
  sida_ipc:                  # Volume compartilhado para comunicação ZeroMQ IPC

services:
  sida-core:
    build: ./sida-core
    container_name: sida-core
    ports:
      - "8000:8000"          # Expõe a API REST para o host
    volumes:
      - ./sida-core/data:/app/data
    networks:
      - sida_network

  poc-ingestion:
    build:
      context: .
      dockerfile: ./infra/Dockerfile
    container_name: sida-poc-ingestion
    ports:
      - "1881:1880"          # Expõe a interface web do Node-RED
    volumes:
      - ./core/ingestion:/data
      - sida_ipc:/tmp/.ipc   # Monta o volume de comunicação IPC compartilhado
    networks:
      - sida_network
    depends_on:
      - sida-core             # Só inicia após o sida-core estar pronto
```

> **💡 `volumes / sida_ipc`:** Ao mapear o mesmo volume nomeado em múltiplos containers, criamos uma "pasta compartilhada" no sistema de arquivos do host que todos os containers enxergam. Os arquivos de socket ZeroMQ IPC (`/tmp/.ipc/*.ipc`) criados pelo container de Ingestão ficam acessíveis ao container de Contexto sem trafegar dados pelas interfaces de rede virtuais do Docker.

> **💡 `depends_on`:** Garante a ordem de inicialização. O container do Node-RED só sobe após o `sida-core` estar em execução, evitando erros de conexão durante a inicialização do sistema.

### 4.2 Otimização de Imagem: Multi-Stage Build

Em ambientes industriais, a imagem Docker precisa ser **pequena**: redes fabris são lentas, e dispositivos de borda têm armazenamento limitado.

```dockerfile
# ─── Estágio 1: Compilação (ambiente pesado, descartado ao final) ───────────
FROM golang:alpine AS builder

RUN apk add --no-cache gcc musl-dev zeromq-dev

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Compila o binário estático para Linux
RUN CGO_ENABLED=1 GOOS=linux go build -o sida-core cmd/server/main.go


# ─── Estágio 2: Runtime limpo (apenas o necessário para executar) ────────────
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata zeromq

WORKDIR /app

# Copia APENAS o binário gerado no estágio anterior
COPY --from=builder /app/sida-core .

EXPOSE 8000
CMD ["./sida-core"]
```

> **💡 Por que Multi-Stage Build?** Se gerarmos a imagem com todo o compilador Go, as bibliotecas de desenvolvimento e o cache do `go mod download`, o container final passa facilmente de **800 MB**. Com o Multi-Stage Build, o primeiro estágio realiza toda a compilação e depois é **descartado**. O segundo estágio pega exclusivamente o binário final (~20 MB) e o roda sobre uma base Alpine Linux minimalista. O resultado é uma imagem final de aproximadamente **40 MB** — uma redução de 95%, ideal para deploy em redes industriais.

---

## Parte 5: Executando o Ambiente na Prática

Com toda a teoria e implementação compreendidas, execute os passos abaixo para subir e validar o sistema completo.

### 5.1 Comandos de Inicialização

No terminal, dentro da pasta raiz do projeto clonado:

```bash
# Constrói as imagens otimizadas e inicia todos os serviços em segundo plano
docker-compose up -d --build

# Verifica o status de integridade de cada container
docker-compose ps
```

### 5.2 Testando as Interfaces e APIs

**Interface visual do Node-RED (Ingestão):**
```
http://localhost:1881
```
Abra no navegador para visualizar e interagir com os fluxos da Camada 1.

**Validação da API do Core:**
```bash
curl http://localhost:8000/api/health
```
A resposta esperada é um JSON com `"status": "UP"`, confirmando que o microsserviço Go está respondendo.

**Monitoramento de Logs em Tempo Real:**
```bash
# Acompanha a sincronização via ZeroMQ ao vivo
docker-compose logs -f sida-core
```

---

## Resumo: Componentes e Portas Locais

| Componente        | Função                          | Porta Padrão | Protocolos de Comunicação                    |
|-------------------|---------------------------------|--------------|----------------------------------------------|
| **sida-core**     | Gerenciador de Manifestos (Go)  | 8000         | REST HTTP / ZeroMQ PUB (TCP 5556)            |
| **poc-ingestion** | Coletor de dados CLP (Node-RED) | 1881         | Modbus TCP / ZeroMQ SUB / ZeroMQ PUSH (IPC)  |
| **poc-context**   | Motor ISA-95 (Node-RED)         | 1882         | ZeroMQ PULL (IPC) / ZeroMQ PUSH (IPC)        |
| **poc-delivery**  | Envio para Nuvem (Node-RED)     | 1883         | ZeroMQ PULL (IPC) / MQTT Sparkplug B         |

---

## Mapa Conceitual: Tecnologias e Onde São Usadas

| Tecnologia / Padrão     | Onde aparece no SIDA                            | Por que foi escolhida                                         |
|-------------------------|-------------------------------------------------|---------------------------------------------------------------|
| **Modbus TCP**          | Camada 1 — comunicação com CLPs                 | Protocolo industrial legado universalmente suportado por CLPs |
| **ZeroMQ PUB/SUB**      | sida-core → Node-RED (TCP 5556)                 | Notificação em tempo real, sem polling HTTP                   |
| **ZeroMQ PUSH/PULL**    | Entre camadas Node-RED (IPC)                    | Latência mínima para transferência local de dados             |
| **ISA-95**              | Camada 2 — enriquecimento de contexto           | Padrão internacional para hierarquia industrial               |
| **Unified Namespace**   | Camada 3 — montagem do tópico MQTT              | Modelo de dados que elimina integrações ponto-a-ponto         |
| **Sparkplug B**         | Camada 3 — formato do payload MQTT              | Tipagem explícita e compressão para dados industriais         |
| **SQLite**              | sida-core — persistência local                  | Banco leve, sem servidor, ideal para edge                     |
| **Clean Architecture**  | sida-core — organização do código Go            | Separa lógica de negócio de detalhes de infraestrutura        |
| **Docker Multi-Stage**  | Dockerfile do sida-core                         | Reduz imagem de 800 MB para ~40 MB                            |
