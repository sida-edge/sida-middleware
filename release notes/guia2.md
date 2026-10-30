Aqui está a versão reformulada do seu **Guia Pedagógico**.

Removi os links e revisões de pré-requisitos genéricos do início, transformando o guia em um material **autossuficiente** e **direto ao ponto**. Agora, os conceitos de sintaxe (como async/await, .map() e ponteiros em Go) e os padrões arquiteturais são explicados **contextualmente**, exatamente no momento em que aparecem no código.

# Guia Pedagógico Interativo: Implementação do SIDA-Middleware

## Sobre este Guia

Este guia prático foi desenhado para consolidar seus conhecimentos de redes, bancos de dados e programação através da construção do **SIDA** (_Smart Industrial DataOps Agent_).

Em vez de fazer você parar a leitura para buscar tutoriais externos, **tudo o que você precisa para entender a implementação está integrado aqui**, de forma contextualizada.

## Parte 1: O Desafio e a Arquitetura SIDA

### 1.1 O Cenário Industrial vs. TI

Imagine o chão de fábrica de uma grande indústria: existem Controladores Lógicos Programáveis (CLPs) da Siemens, Rockwell e Schneider. Cada um fala um protocolo diferente (Modbus TCP, OPC UA, S7) e gera dados brutos sem qualquer contexto (por exemplo, o valor decimal 60.5 isolado na memória).

O **SIDA** é um middleware de _Edge Computing_ que atua como tradutor e organizador, transformando esses dados brutos em informações estruturadas e prontas para sistemas de nuvem ou ERPs, utilizando o conceito de **Unified Namespace (UNS)** sob a norma **ISA-95**.

### 1.2 Arquitetura em 3 Camadas

O sistema opera de forma modularizado através de microsserviços integrados:

┌─────────────────────────────────────────────────────────────┐

│ SIDA Architecture │

├─────────────────────────────────────────────────────────────┤

│ Camada 1: Ingestão (Node-RED) │

│ Lê registros brutos dos CLPs via Modbus/OPC UA │

│ │

│ Camada 2: Context Engine (Node-RED + ISA-95) │

│ Organiza os dados na estrutura: Empresa > Fábrica > Área │

│ │

│ Camada 3: Delivery (Node-RED + Sparkplug B) │

│ Compacta os dados e publica via MQTT para a Nuvem │

└─────────────────────────────────────────────────────────────┘

▲

│ Configurações via ZeroMQ

▼

┌─────────────────────────────────────────────────────────────┐

│ SIDA-Core (Go) │

│ API REST central que gerencia os manifestos e regras │

└─────────────────────────────────────────────────────────────┘

## Parte 2: Estrutura do Projeto

Antes de rodar o ambiente, entenda como o código está organizado:

sida-middleware/

├── core/ # Fluxos visuais do Node-RED

│ ├── ingestion/ # Camada 1: Coleta de dados Edge

│ ├── context/ # Camada 2: Motor de Contexto (ISA-95)

│ └── delivery/ # Camada 3: Envio Cloud (Sparkplug B)

├── sida-core/ # API Central desenvolvida em Go

│ ├── cmd/server/main.go # Ponto de entrada da aplicação

│ ├── internal/ # Lógica de negócio e adaptadores

│ └── go.mod # Dependências do Go

├── infra/ # Infraestrutura Docker

└── docker-compose.yml # Orquestrador de todos os serviços

## Parte 3: Implementação Detalhada e Códigos comentados

### 3.1 Camada 1: Ingestão Dinâmica (Node-RED)

A Ingestão realiza a leitura periódica (_polling_) de tabelas de memória dos CLPs. No Node-RED, usamos nós de código JavaScript para processar essas conexões dinamicamente com base em um arquivo de configuração (Manifesto) enviado pelo sida-core.

#### Nó: setupModbus

Este trecho varre as configurações do Manifesto e abre canais de comunicação TCP com os equipamentos.

JavaScript

const manifest = global.get("manifest");

const areas = manifest.config.plant.areas;

for (const areaId of Object.keys(areas)) {

const lines = areas\[areaId\].lines;

for (const lineId of Object.keys(lines)) {

const devices = lines\[lineId\].devices;

for (const deviceId of Object.keys(devices)) {

const dev = devices\[deviceId\];

if (dev.enabled && dev.connection.protocol === "modbus_tcp") {

const client = new ModbusRTU();

// Conexão assíncrona ao CLP

await client.connectTCP(dev.connection.host, { port: dev.connection.port });

client.setID(dev.connection.unit_id);

}

}

}

}

🔬 **Conceitos de Sintaxe Aplicada:**

- **Object.keys(areas)**: Transforma as propriedades de um objeto em uma lista (Array) de strings para podermos usar loops sobre estruturas JSON dinâmicas.
- **async/await**: Como a conexão de rede (connectTCP) demora milissegundos para responder, o JavaScript travaria o processamento inteiro se fosse síncrono. O await avisa o motor do Node-RED para pausar essa função específica até a conexão concluir, liberando o sistema para outras tarefas nesse meio tempo.

#### Nó: Polling

Executa leituras cíclicas em intervalos de tempo definidos (ex: a cada 500ms) nos registradores de memória do CLP.

JavaScript

Object.keys(active_clients).forEach((deviceId) => {

const { client, config, gateway_id } = active_clients\[deviceId\];

const scanRate = config.connection.scan_rate_ms;

setInterval(async () => {

let data_payload = {};

for (let addrKey of Object.keys(config.metrics_mapping)) {

let address = parseInt(addrKey);

// Ajuste de offset do protocolo Modbus

if (address >= 40001 && address <= 49999) address -= 40001;

// Lê o Holding Register do CLP

let data = await client.readHoldingRegisters(address, 1);

data_payload\[addrKey\] = data.data\[0\];

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

🔬 **Conceitos de Sintaxe e Protocolo:**

- **setInterval(..., scanRate)**: Um temporizador nativo que repete o bloco de código infinitamente com base no tempo (scanRate) configurado para aquele equipamento específico.
- **Ajuste de Endereço (address -= 40001)**: Na automação industrial, a faixa 40001-49999 representa mapeamentos lógicos de _Holding Registers_. No entanto, na mensagem binária real trafegada na rede TCP, o primeiro registrador é referenciado como endereço 0. Essa subtração faz a conversão do endereço comercial para o endereço real de rede.

### 3.2 Camada 2 e 3: Mecanismo de Contexto e Sparkplug B

Uma vez coletado o dado bruto da memória do CLP (ex: endereço 40001 = 60), ele precisa ser envelopado dentro da árvore lógica da empresa (Norma ISA-95) e convertido para o protocolo **Sparkplug B** (um padrão industrial baseado em MQTT que compacta dados via Protocol Buffers).

#### Função: spbGenerator (Preparação do Tópico UNS)

Este código varre o caminho físico do ativo e monta o endereço de publicação estruturado.

JavaScript

const payloadIn = msg.payload;

const pathArray = payloadIn.asset_context.path;

// Busca o identificador correto com base no tipo de hierarquia

const getContextId = (targetType) => {

const item = pathArray.find(p => p.type === targetType);

return item ? item.id : "unknown";

};

const enterprise = getContextId("enterprise");

const site = getContextId("site");

const area = getContextId("area");

// Montagem do Unified Namespace (UNS)

const groupId = \`\${enterprise}\_\${site}\_\${area}\`;

const nodeId = getContextId("line");

const deviceId = getContextId("equipment");

🔬 **Conceitos de Sintaxe Aplicada:**

- **pathArray.find(...)**: Método que percorre um vetor de objetos e retorna o primeiro elemento que atenda ao critério. Substitui loops complexos de busca.
- **Template Literals (\`\${...}\`)**: Permite concatenar strings e variáveis sem a necessidade de usar operadores de soma (+), tornando o código de formação de tópicos de rede muito mais legível.

#### Função: Payload Formatter

Formata as métricas brutas gerando tipos de dados explícitos aceitos em sistemas de TI.

JavaScript

const dataMetrics = dataRaw.map(item => {

let sparkplugType = "String";

const explicitType = item.data_type.toLowerCase();

if (explicitType === "float") sparkplugType = "Float";

else if (explicitType === "boolean") sparkplugType = "Boolean";

return {

name: item.name,

value: item.value,

type: sparkplugType,

timestamp: Date.now()

};

});

msg.topic = \`spBv1.0/\${groupId}/DDATA/\${nodeId}/\${deviceId}\`;

msg.payload = { metrics: dataMetrics };

🔬 **Conceitos de Sintaxe e Arquitetura:**

- **dataRaw.map(...)**: Padrão de programação funcional. Ele pega o array bruto, aplica uma transformação em cada item internamente e retorna um _novo_ array modificado com o mesmo tamanho, ideal para converter listas de dados industriais em JSONs padronizados.
- **spBv1.0/.../DDATA/...**: Padrão estrito do Sparkplug B. Sistemas de nuvem que escutam esse tópico já sabem de imediato que DDATA significa _Device Data_ e conseguem processar o payload sem precisar de engenharia reversa.

### 3.3 O Core do Sistema: SIDA-Core (Go)

A API central é escrita em Go devido à sua alta performance e facilidade em lidar com concorrência e redes de baixa latência. Ela segue os princípios da **Clean Architecture**, isolando o banco de dados e os protocolos de transporte da lógica de negócio central.

#### O Arquivo Principal (main.go)

Responsável por instanciar os repositórios, injetar dependências e subir o servidor HTTP.

Go

package main

import (

"net/http"

"sida-core/internal/adapters/handler"

"sida-core/internal/adapters/repository"

"sida-core/internal/core/services"

"github.com/gin-gonic/gin"

)

func main() {

// Inicialização do banco SQLite local de borda

repo, \_:= repository.NewSQLiteManifestRepository("./data/sida_config.db")

// Inicialização do barramento ZeroMQ para atualizar os nós Node-RED em tempo real

zmqPub, \_ := services.NewZMQPublisher("0.0.0.0:5556")

manifestHandler := handler.NewManifestHandler(repo, zmqPub)

router := gin.Default()

router.POST("/api/config/manifest", manifestHandler.UploadManifest)

srv := &http.Server{Addr: ":8000", Handler: router}

srv.ListenAndServe()

}

🔬 **Entendendo as Particularidades do Go:**

- **Operador de Inferência de Tipo (:=)**: Em Go, você não precisa declarar o tipo explicitamente se inicializar a variável no momento da criação. repo := ... cria e tipa a variável automaticamente com base no retorno da função.
- **Tratamento de Erros Explícito (\_)**: Go não possui estruturas de try/catch. Funções que podem falhar retornam o dado e um objeto de erro juntos. O caractere \_ (blank identifier) avisa ao compilador que estamos ignorando o erro intencionalmente naquele ponto para fins de simplificação do exemplo.

#### O Padrão de Persistência (repository.go)

Gerencia o armazenamento local usando SQLite com recursos avançados de concorrência.

Go

type sqliteManifestRepo struct {

db \*sql.DB

}

func (r \*sqliteManifestRepo) Save(ctx context.Context, manifest domain.Manifest) error {

configBytes, \_ := json.Marshal(manifest.Config)

query := \`INSERT INTO edge_manifests (gateway_id, config, updated_at)

VALUES (?, ?, ?)

ON CONFLICT(gateway_id) DO UPDATE SET config=excluded.config\`

\_, err := r.db.ExecContext(ctx, query, manifest.GatewayID, string(configBytes), manifest.UpdatedAt)

return err

}

🔬 **Conceito de Banco de Dados de Borda:**

- **ON CONFLICT(...) DO UPDATE (Upsert)**: Dispositivos de borda (_edge_) frequentemente perdem conexão ou reiniciam. Em vez de disparar um erro se a configuração daquele gateway já existir no banco, a query atualiza o registro existente de forma atômica, garantindo resiliência de dados sem necessidade de checagens prévias no código.

### 3.4 Comunicação Inter-Microsserviços: O Papel do ZeroMQ

Como o sida-core (Go) e as camadas de Ingestão e Contexto (Node-RED) rodam em containers separados, precisamos de uma comunicação de altíssima velocidade e baixíssima latência para sincronizá-los. Usamos o **ZeroMQ (ZMQ)**.

Ao contrário do HTTP tradicionais que exigem um handshake pesado para cada requisição, o ZeroMQ cria sockets persistentes diretamente sobre o protocolo TCP ou IPC (Inter-Process Communication).

#### Mecanismo do Publisher em Go

Go

func (p \*ZMQPublisher) PublishUpdate(gatewayID string) error {

topic := "sida/manifest/" + gatewayID

// Envia um sinalizador de recarga para os nós assinantes no Node-RED

\_, err := p.socket.SendMessage(topic, "RELOAD")

return err

}

#### Arquitetura de Mensageria Interna do SIDA

- **PUB/SUB (TCP):** O sida-core atua como **Publisher** (publicador) na porta 5556. Todas as instâncias do Node-RED atuam como **Subscribers** (assinantes). Quando você altera uma configuração no painel web, o Go grita "RELOAD" no barramento e todas as camadas de ingestão se reconfiguram sozinhas de forma dinâmica, sem derrubar os containers.
- **PUSH/PULL (IPC):** Entre os blocos do Node-RED, usamos caminhos de socket locais em arquivos do sistema (ipc:///tmp/.ipc/ingestion.ipc). Isso evita overhead de pilha de rede TCP, trafegando dados na velocidade da memória RAM da máquina local.

## Parte 4: Orquestração e Deploy com Docker

Para consolidar todos esses módulos e garantir que o ambiente seja idêntico em qualquer computador ou computador industrial, usamos o Docker Compose com técnicas de otimização de imagens.

### 4.1 O Arquivo de Infraestrutura (docker-compose.yml)

YAML

version: '3.8'

networks:

sida_network:

driver: bridge

volumes:

sida_ipc: # Volume compartilhado em memória para comunicação ZeroMQ IPC

services:

sida-core:

build: ./sida-core

container_name: sida-core

ports:

\- "8000:8000"

volumes:

\- ./sida-core/data:/app/data

networks:

\- sida_network

poc-ingestion:

build:

context: .

dockerfile: ./infra/Dockerfile

container_name: sida-poc-ingestion

ports:

\- "1881:1880"

volumes:

\- ./core/ingestion:/data

\- sida_ipc:/tmp/.ipc # Monta o diretório de comunicação veloz

networks:

\- sida_network

depends_on:

\- sida-core

🔬 **Conceitos de Infraestrutura como Código:**

- **volumes / sida_ipc**: Ao mapear o mesmo volume nomeado em múltiplos containers, criamos uma ponte no sistema de arquivos do Host que permite ao container de Ingestão e ao de Contexto trocarem mensagens via ZeroMQ IPC diretamente, sem trafegar dados pelas interfaces de rede virtuais do Docker.
- **depends_on**: Garante a ordem correta de inicialização do ecossistema. O container do Node-RED só iniciará após o container do sida-core estar pronto em execução.

### 4.2 Otimização de Imagem: Multi-Stage Build

No desenvolvimento profissional de sistemas embarcados e Edge, criar imagens leves é obrigatório. Veja como o Dockerfile do sida-core reduz drasticamente o tamanho final utilizando estágios múltiplos:

Dockerfile

\# Estágio 1: Compilação do Executável Go (Ambiente pesado de compilação)

FROM golang:alpine AS builder

RUN apk add --no-cache gcc musl-dev zeromq-dev

WORKDIR /app

COPY go.mod go.sum ./

RUN go mod download

COPY . .

RUN CGO_ENABLED=1 GOOS=linux go build -o sida-core cmd/server/main.go

\# Estágio 2: Ambiente de Execução Limpo (Runtime)

FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata zeromq

WORKDIR /app

\# Copia APENAS o binário compilado no estágio anterior

COPY --from=builder /app/sida-core .

EXPOSE 8000

CMD \["./sida-core"\]

🔬 **Por que fazemos isso?**

Se gerássemos a imagem contendo todo o compilador do Go, bibliotecas de desenvolvimento e histórico de arquivos, o container final passaria facilmente de **800 MB**. Com o _Multi-Stage Build_, o primeiro estágio descarta todo o lixo de compilação após gerar o binário estático. O segundo estágio pega apenas esse binário final (~20MB) e roda sobre uma imagem Alpine Linux minimalista. O resultado é uma imagem final de aproximadamente **40 MB**, ideal para transmissão e deploy em redes industriais limitadas.

## Parte 5: Executando o Ambiente na Prática

Com toda a teoria e mecânica de código assimiladas em seus respectivos blocos, execute os passos abaixo para subir e validar a aplicação:

### 5.1 Comandos de Inicialização

No terminal, dentro da pasta raiz do projeto clonado, execute:

Bash

\# Constrói as imagens otimizadas e inicia os serviços em segundo plano (-d)

docker-compose up -d --build

\# Confere o status de integridade de cada container

docker-compose ps

### 5.2 Testando as Interfaces e APIs

- **Acesso à Ingestão Visual:** Abra o navegador e digite <http://localhost:1881> para visualizar e interagir com as conexões lógicas estruturadas no Node-RED.
- **Validação da API do Core:** Teste se o microsserviço Go está respondendo corretamente via prompt de comando:

Bash

curl <http://localhost:8000/api/health>

A resposta esperada deve ser um JSON estruturado indicando status ativo ("status":"UP").

- **Monitoramento de Logs de Redes de Comunicação:** Caso queira verificar a sincronização dinâmica acontecendo via ZeroMQ em tempo real, use:

Bash

docker-compose logs -f sida-core

## Resumo dos Componentes e Portas Locais

| **Componente**    | **Função**                      | **Porta Padrão** | **Canal de Comunicação**                    |
| ----------------- | ------------------------------- | ---------------- | ------------------------------------------- |
| **sida-core**     | Gerenciador de Manifestos (Go)  | 8000             | REST HTTP / ZeroMQ PUB (5556)               |
| **poc-ingestion** | Coletor de dados CLP (Node-RED) | 1881             | Modbus TCP / ZeroMQ SUB / ZeroMQ PUSH (IPC) |
| **poc-context**   | Motor ISA-95 (Node-RED)         | 1882             | ZeroMQ PULL (IPC) / ZeroMQ PUSH (IPC)       |
| **poc-delivery**  | Envio Nuvem (Node-RED)          | 1883             | ZeroMQ PULL (IPC) / MQTT Sparkplug B        |

## Parte 6: Detalhamento dos Nós do Node Red

Para tornar o guia completamente didático, autossuficiente e claro para os estudantes, precisamos detalhar a **anatomia visual dos fluxos do Node-RED**. Na automação e integração de sistemas com Node-RED, entender o **tipo do nó** e a **topologia das conexões (fios/wires)** é tão importante quanto o código que roda dentro deles.

### 6.1 Camada 1: Ingestão Dinâmica (Node-RED)

A Ingestão realiza a leitura periódica (_polling_) de tabelas de memória dos CLPs. Na aba **Camada 1: Ingestão** do Node-RED, a arquitetura dinâmica funciona através de **5 nós conectados estrategicamente**:

#### Mapa Visual do Fluxo

\[ZMQ SUB (Manifesto)\] ───> \[setupModbus (Function)\]

│ (Comunicação via Memória Global)

▼

\[Gatilho (Inject)\] ───> \[Polling (Function)\] ───> \[ZMQ PUSH (Ingestion)\]

#### Detalhamento dos Nós e Conexões

- **Nó: ZMQ SUB (Manifesto)**
  - **Tipo do Nó:** zmq sub _(adicionado via Paleta de Nós: node-red-contrib-zeromq)_.
  - **Para que serve:** Atua como um receptor de rádio. Ele fica escutando a rede na porta TCP 5556 do container sida-core. Sempre que o arquivo de configuração da fábrica (Manifesto) muda na API, este nó captura o novo JSON.
  - **Conexões:** Conecte a **saída** deste nó diretamente na **entrada** do nó setupModbus.
- **Nó: setupModbus**
  - **Tipo do Nó:** Function _(nó nativo para execução de JavaScript)_.
  - **Para que serve:** Recebe o Manifesto vindo do nó anterior, armazena essas configurações na memória de longo prazo do Node-RED (global.set("manifest", ...)) e instancia os clientes Modbus TCP na memória para cada equipamento ativo.
  - **Conexões:** Recebe dados na sua **entrada** a partir do ZMQ SUB (Manifesto). Como sua função é preparar o ambiente e salvar os dados na memória global que outros nós lerão, ele **não precisa de fios conectados à sua saída**.
- **Nó: Gatilho (Polling Trigger)**
  - **Tipo do Nó:** Inject _(nó nativo de injeção de fluxos)_.
  - **Para que serve:** Funciona como o "metrônomo" ou o _clock_ do sistema. Deve ser configurado nas propriedades visuais para disparar repetidamente em um intervalo fixo (ex: a cada 1 segundo), enviando um timestamp simples apenas para iniciar a leitura.
  - **Conexões:** Conecte a **saída** deste nó diretamente na **entrada** do nó Polling.
- **Nó: Polling**
  - **Tipo do Nó:** Function.
  - **Para que serve:** É o coração da coleta. Toda vez que o nó Gatilho bate, o código JavaScript dentro deste nó acorda, lê a lista de conexões dos CLPs salvas na memória global, executa a varredura física dos registradores (readHoldingRegisters) e monta o JSON de dados brutos com um carimbo de tempo (Date.now()).
  - **Conexões:** Recebe o pulso de ativação na sua **entrada** vindo do nó Gatilho. Conecte a sua **saída** diretamente na **entrada** do nó ZMQ PUSH (Ingestion).
- **Nó: ZMQ PUSH (Ingestion)**
  - **Tipo do Nó:** zmq push _(do pacote node-red-contrib-zeromq)_.
  - **Para que serve:** Pega o JSON estruturado pelo nó Polling e despacha para fora do container utilizando comunicação entre processos (IPC) de alta velocidade através do endereço de socket ipc:///tmp/.ipc/ingestion.ipc.
  - **Conexões:** Conecte a sua **entrada** na **saída** do nó Polling. Este nó encerra o fluxo da Camada 1, portanto sua saída fica livre.

### 6.2 Camada 2: Context Engine (ISA-95)

Na aba **Camada 2: Context**, o Node-RED tem a missão de pegar o dado bruto e dizer de onde ele veio no organograma do chão de fábrica. O fluxo é linear e utiliza **3 nós conectados em série**:

#### Mapa Visual do Fluxo

\[ZMQ PULL (Context)\] ───> \[EnrichContext (Function)\] ───> \[ZMQ PUSH (Context)\]

#### Detalhamento dos Nós e Conexões

- **Nó: ZMQ PULL (Context)**
  - **Tipo do Nó:** zmq pull.
  - **Para que serve:** É a porta de entrada da Camada 2. Ele fica escutando o arquivo de socket compartilhado ipc:///tmp/.ipc/ingestion.ipc e suga instantaneamente as mensagens enviadas pelo nó terminal da Camada 1.
  - **Conexões:** Conecte a sua **saída** diretamente na **entrada** do nó EnrichContext.
- **Nó: EnrichContext**
  - **Tipo do Nó:** Function.
  - **Para que serve:** Contém o código de cruzamento de dados. Ele lê o ID do equipamento que gerou o dado, busca no Manifesto global as informações de sua localização física e injeta no payload o caminho completo segundo a norma ISA-95 (Empresa -> Fábrica -> Área -> Linha -> Equipamento).
  - **Conexões:** Recebe dados na sua **entrada** vindo do ZMQ PULL (Context). Conecte a sua **saída** diretamente na **entrada** do nó ZMQ PUSH (Context).
- **Nó: ZMQ PUSH (Context)**
  - **Tipo do Nó:** zmq push.
  - **Para que serve:** Encaminha o pacote de dados completamente contextualizado para a próxima etapa através de um novo canal IPC localizado em ipc:///tmp/.ipc/context.ipc.
  - **Conexões:** Conecte a sua **entrada** na **saída** do nó EnrichContext. É o nó final desta aba.

### 6.3 Camada 3: Delivery (Unified Namespace & Sparkplug B)

Na aba **Camada 3: Delivery**, traduzimos a estrutura industrial para regras de comunicação em Nuvem (TI). Este fluxo é composto por **4 nós sequenciais**:

#### Mapa Visual do Fluxo

\[ZMQ PULL (Delivery)\] ───> \[spbGenerator (Function)\] ───> \[Payload Formatter (Function)\] ───> \[MQTT Out\]

#### Detalhamento dos Nós e Conexões

- **Nó: ZMQ PULL (Delivery)**
  - **Tipo do Nó:** zmq pull.
  - **Para que serve:** Captura os dados ricos em contexto que a Camada 2 postou no canal IPC ipc:///tmp/.ipc/context.ipc.
  - **Conexões:** Conecte a sua **saída** diretamente na **entrada** do nó spbGenerator.
- **Nó: spbGenerator**
  - **Tipo do Nó:** Function.
  - **Para que serve:** Executa o código JavaScript que vasculha o caminho da árvore ISA-95 e extrai os nomes textuais da Empresa, Planta e Área. Ele junta essas strings usando caracteres de sublinhado para gerar dinamicamente o identificador de grupo (groupId) do ecossistema Unified Namespace (UNS).
  - **Conexões:** Recebe dados do ZMQ PULL (Delivery) na sua **entrada**. Conecte a sua **saída** diretamente na **entrada** do nó Payload Formatter.
- **Nó: Payload Formatter**
  - **Tipo do Nó:** Function.
  - **Para que serve:** Formata as métricas numéricas convertendo-as para os tipos aceitos pelo padrão Sparkplug B (Float, Boolean, String), monta o payload final em formato de objeto de métricas e escreve na propriedade obrigatória msg.topic o endereço oficial do barramento MQTT industrial (spBv1.0/GroupId/DDATA/NodeId/DeviceId).
  - **Conexões:** Conecte a sua **entrada** na **saída** do nó spbGenerator. Conecte a sua **saída** diretamente na **entrada** do nó MQTT Out.
- **Nó: MQTT Out**
  - **Tipo do Nó:** mqtt out _(nó de rede nativo do Node-RED)_.
  - **Para que serve:** Abre e gerencia um túnel TCP persistente com o Broker MQTT externo (ex: Nuvem GCP). Ele ignora tópicos estáticos preenchidos na interface gráfica e publica o conteúdo de msg.payload usando o endereço gerado de forma dinâmica em msg.topic pelo nó anterior.
  - **Conexões:** Conecte a sua **entrada** na **saída** do nó Payload Formatter. Como este nó despacha as informações diretamente para a internet/nuvem, ele é o ponto final absoluto de toda a arquitetura de processamento do SIDA-Middleware.
