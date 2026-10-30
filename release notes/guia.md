# Guia Pedagógico: Implementação do SIDA-Middleware

## Sobre este Guia

Este guia foi criado para estudantes da segunda metade do curso de graduação em Sistemas de Informação, com conhecimentos básicos em programação, redes e bancos de dados.

### Pré-requisitos Recomendados

Antes de começar, você deve ter familiaridade com:

1. **Programação básica** - variáveis, estruturas de controle, funções
2. **Conceitos de redes** - TCP/IP,端 ports, HTTP, APIs REST
3. **Banco de dados relacional** - conceitos de tabelas, queries básicas
4. **Git e GitHub** - commit, push, pull, branches

Se você ainda não tem esses conhecimentos, sugiro os seguintes recursos gratuitos:

| Conceito | Recurso |
|----------|---------|
| Programação em JavaScript | [JavaScript.info](https://javascript.info/) |
| Fundamentos de Redes | [Computer Networking - Kurose & Ross](https://gaia.cs.umass.edu/kurose_ross/) |
| Node-RED | [Node-RED Official Docs](https://nodered.org/docs/) |
| Docker | [Docker Get Started](https://docs.docker.com/get-started/) |

---

## Parte 1: Conceitos Fundamentais

### 1.1 O que é o SIDA-Middleware?

O **SIDA** (*Smart Industrial DataOps Agent*) é um middleware de Edge Computing que atua como ponte entre o chão de fábrica (OT - Operational Technology) e os sistemas corporativos (IT - Information Technology).

#### O Desafio Industrial

Imagine uma fábrica com:
- **CLPs** (Controladores Lógicos Programáveis) fabricados por diferentes empresas (Siemens, Rockwell, etc.)
- Cada CLP usa um **protocolo diferente** (Modbus, OPC UA, S7)
- Os dados dos CLPs são apenas valores numéricos sem contexto (ex: "60.5" no endereço DB1.DBX0.0)

O problema: Como transformar esses dados brutos em informações úteis para sistemas de análise?

#### A Solução SIDA

O SIDA resolve isso em **3 camadas**:

```
┌─────────────────────────────────────────────────────────────┐
│                    SIDA Architecture                        │
├─────────────────────────────────────────────────────────────┤
│  Camada 1: Ingestão                                         │
│  ┌──────────────┐  Modbus   ┌──────────────┐               │
│  │   CLP A      │ ─────────> │ Ingestion    │               │
│  └──────────────┘           └──────┬────────┘               │
│                                     │                        │
│  ┌──────────────┐  OPC UA    ┌────┴──────┐                  │
│  │   CLP B      │ ──────────>│           │                  │
│  └──────────────┘            └───────────┘                  │
│                                                             │
│  Camada 2: Context Engine (ISA-95)                        │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Enterprise > Site > Area > Line > Equipment >     │   │
│  │  Telemetry                                         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  Camada 3: Delivery (Unified Namespace)                    │
│  ┌──────────────────┐   MQTT   ┌────────────────────┐    │
│  │  sida-poc-delivery├─────────>│   Unified Namespace│    │
│  └──────────────────┘          └────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Protocolos Industriais

#### Modbus
- **O que é:** Protocolo de comunicação síncrono, simples e amplamente adotado
- **Como funciona:** Cliente (master) envia requisições para servidores (slaves)
- **Tipos:** Modbus TCP (via Ethernet) e Modbus RTU (via serial)
- **Conceitos importantes:**
  - **Register:** Endereço de memória no CLP (ex: 40001)
  - **Holding Register:** Registers que podem ser escritos
  - **Input Register:** Registers de leitura apenas

**Recurso para aprendizado:**
- [Modbus Protocol Specification (Modbus.org)](https://modbus.org/specs.php)
- [Modbus TCP Wikipedia](https://en.wikipedia.org/wiki/Modbus#Modbus_TCP)

#### OPC UA (Open Platform Communications Unified Architecture)
- Protocolo mais moderno e seguro
- Suporta criptografia, autenticação e modelagem de dados
- Complexidade maior, mas mais robusto

### 1.3 Unified Namespace (UNS)

O **Unified Namespace** é um conceito de organização de dados em tempo real.

#### Exemplo de Hierarquia UNS:

```
spBv1.0/Enterprise_Site_Area/DDATA/Line/Equipment
```

Onde:
- `spBv1.0` - Versão do Sparkplug B
- `Enterprise_Site_Area` - Identificador do grupo ( Enterprise, Site, Area concatenados)
- `DDATA` - Tipo de mensagem (Data)
- `Line` - Node ID (identifica a linha)
- `Equipment` - Device ID (identifica o equipamento)

#### Sparkplug B
- **O que é:** Especificação da Eclipse Foundation para mensagens MQTT em ambientes industriais
- **Vantagens:**
  - Compressão eficiente (usa Protocol Buffers)
  - Tipos de dados padronizados
  - Suporte a estado de conexão (birth/death messages)

**Recurso:**
- [Sparkplug B Specification](https://www.eclipse.org/tahu/sparkplug-b/) (Eclipse Foundation)

### 1.4 ISA-95: Modelo de Referência para Automação

ISA-95 é um conjunto de padrões que define como organizar sistemas de automação.

#### Hierarquia ISA-95:

```
Nível 4: Enterprise (Empresa)
         └── Nível 3: Site (Planta/Fábrica)
             └── Nível 2: Area (Área da planta)
                 └── Nível 1: Line (Linha de produção)
                     └── Nível 0: Equipment (Equipamento)
```

Essa modelagem permite:
- Rastreabilidade de dados
- organização lógica que corresponde à estrutura física da fábrica
- Facilidade para busca e agrupamento de dados

**Recurso:**
- [ISA-95 Wikipedia](https://en.wikipedia.org/wiki/ISA-95)

---

## Parte 2: Setup Inicial

### 2.1 Instalando as Ferramentas Necessárias

#### 1. Git (Controle de Versão)

Git é o sistema de controle de versão mais usado. Ele permite rastrear mudanças no código.

**Instalação:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install git

# Windows
# Baixe em: https://git-scm.com/download/win
```

**Conceitos básicos:**
- **Repository (Repo):** O repositório onde o código é armazenado
- **Commit:** Uma "snapshot" do código em um momento específico
- **Branch:** Uma linha de desenvolvimento independente

**Comandos essenciais:**
```bash
git clone <url>           # Clona um repositório
git status               # Mostra o status dos arquivos
git add <arquivo>        # Adiciona arquivos para commit
git commit -m "msg"      # Salva as mudanças
git push                 # Envia para o repositório remoto
```

**Recurso:** [Learn Git Branching](https://learngitbranching.js.org/)

#### 2. Node.js e Node-RED

**Node.js:** Ambiente de execução JavaScript no servidor.

**Node-RED:** Ferramenta de fluxo visual para IoT e integração de APIs.

**Instalação:**
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# Node-RED (via npm)
npm install -g node-red

# Windows/Mac
# Baixe em: https://nodejs.org/
```

**Verificação:**
```bash
node --version   # Exibe a versão do Node
npm --version    # Exibe a versão do npm
node-red --version
```

**Recurso:** [Node-RED Official Documentation](https://nodered.org/docs/)

#### 3. Docker e Docker Compose

Docker permite criar ambientes isolados (containers) para cada serviço.

**Instalação:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# Windows/Mac
# Instale Docker Desktop
```

**Conceitos:**
- **Image:** Modelo para criar containers
- **Container:** Instância em execução de uma image
- **Volume:** Pasta compartilhada entre host e container
- **Network:** Rede virtual entre containers

**Comandos essenciais:**
```bash
docker images          # Lista imagens
docker ps             # Lista containers em execução
docker-compose up -d  # Sube todos os serviços
docker-compose down   # Para todos os serviços
docker-compose logs -f # Ver logs em tempo real
```

**Recurso:** [Docker Get Started](https://docs.docker.com/get-started/)

#### 4. Go (Golang)

Go é a linguagem usada para o sida-core.

**Instalação:**
```bash
# Ubuntu/Debian
sudo apt install golang

# Windows/Mac
# Baixe em: https://go.dev/dl/
```

**Verificação:**
```bash
go version
```

### 2.2 Clonando o Repositório

```bash
cd ~/projetos  # ou qualquer diretório de sua escolha
git clone <URL-do-repositorio-sida-middleware>
cd sida-middleware
```

---

## Parte 3: Entendendo a Estrutura do Projeto

### 3.1 Organização de Arquivos

```
sida-middleware/
├── core/                      # Microsserviços Node-RED
│   ├── ingestion/            # PoC 1 - Gateway de Aquisição Edge
│   │   ├── flows.json        # Fluxos do Node-RED (lógica visual)
│   │   ├── package.json      # Dependências JavaScript
│   │   └── .config.nodes.json
│   ├── context/              # PoC 2 - Motor de Enriquecimento
│   │   └── flows.json
│   └── delivery/             # PoC 3 - Ponte de Telemetria Cloud
│       └── flows.json
│
├── sida-core/                # Core service em Go
│   ├── cmd/server/main.go    # Entry point da aplicação
│   ├── internal/             # Código interno
│   │   ├── api/             # Roteamento HTTP
│   │   ├── adapters/        # Handlers e Repository
│   │   └── core/            # Lógica de negócio
│   ├── go.mod               # Gerenciamento de dependências
│   └── Dockerfile
│
├── infra/                    # Orquestração
│   ├── Dockerfile           # Dockerfile genérico para Node-RED
│   └── README.md
│
├── schemas/                 # Contratos de dados
│   ├── README.md
│   └── sparkplug_b.proto    # Schema Sparkplug B (a ser implementado)
│
├── docker-compose.yml       # Orquestração de todos os serviços
├── .gitignore
└── README.md
```

### 3.2 O que Cada Componente Faz

| Componente | Função | Tecnologia |
|------------|--------|------------|
| `core/ingestion` | Lê dados dos CLPs via Modbus | Node-RED + modbus-serial |
| `core/context` | Recebe dados e prepara para delivery | Node-RED |
| `core/delivery` | Envia dados para MQTT no GCP | Node-RED + Sparkplug B |
| `sida-core` | API REST para gerenciar configurações | Go + Gin |
| `docker-compose.yml` | Orquestra todos os containers | Docker |

---

## Parte 4: Implementação Detalhada

### 4.1 Camada 1: Ingestão (Node-RED)

#### 4.1.1 O que é Ingestão?

Ingestão é o processo de **coletar dados brutos** dos dispositivos industriais.

No SIDA, isso é feito através de:
1. **Polling:** Leitura periódica dos registers do CLP
2. **Subscrição:** Recebimento de dados quando disponíveis (menos comum em Modbus)

#### 4.1.2 Estrutura do Fluxo de Ingestão

O arquivo `core/ingestion/flows.json` contém três tabs (abas):

**Tab 1: Messaging**
- Controla a comunicação ZeroMQ
- Envia dados para o próximo estágio

**Tab 2: Processing**
- Realiza o polling dos CLPs
- Formata os dados em JSON

**Tab 3: Controller**
- Consulta o sida-core por configurações
- Reconfigura automaticamente quando o manifesto muda

#### 4.1.3 O código do nó "setupModbus"

Este nó JavaScript configura as conexões Modbus dinamicamente:

```javascript
const manifest = global.get("manifest");
const areas = manifest.config.plant.areas;

for (const areaId of Object.keys(areas)) {
    const lines = areas[areaId].lines;
    for (const lineId of Object.keys(lines)) {
        const devices = lines[lineId].devices;
        for (const deviceId of Object.keys(devices)) {
            const dev = devices[deviceId];
            if (dev.enabled && dev.connection.protocol === "modbus_tcp") {
                // Cria conexão Modbus
                const client = new ModbusRTU();
                await client.connectTCP(dev.connection.host, { port: dev.connection.port });
                client.setID(dev.connection.unit_id);
            }
        }
    }
}
```

**Conceitos aqui:**
- **Loop `for...in`:** Itera sobre chaves de objetos JavaScript
- **Assíncrono (`async/await`):** Permite operações I/O sem bloquear o evento loop
- **Conditional (`if...else`):** Lógica condicional básica

#### 4.1.4 O código do nó "Polling"

Este nó lê os registers do CLP periodicamente:

```javascript
Object.keys(active_clients).forEach((deviceId) => {
    const { client, config, gateway_id } = active_clients[deviceId];
    
    // Freqüência de leitura
    const scanRate = config.connection.scan_rate_ms;
    
    setInterval(async () => {
        let data_payload = {};
        for (let addrKey of Object.keys(config.metrics_mapping)) {
            const metric = config.metrics_mapping[addrKey];
            
            // Converte address Modbus para índice
            let address = parseInt(addrKey);
            if (address >= 40001 && address <= 49999) address -= 40001;
            
            // Lê register do CLP
            let data = await client.readHoldingRegisters(address, quantity);
            
            data_payload[addrKey] = data.data[0];
        }
        
        // Envia payload formatado
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

**Conceitos importantes:**
- **`setInterval`:** Executa código periodicamente
- **`Date.now()`:** Timestamp em milliseconds
- **Objetos aninhados:** Estrutura de dados hierárquica

### 4.2 Camada 2: Context Engine (ISA-95)

#### 4.2.1 O que é Context Engine?

É o processo de **adicionar significado aos dados brutos** usando a modelagem ISA-95.

#### 4.2.2 A função `spbGenerator`

No arquivo `core/delivery/flows.json`, esta função transforma dados:

```javascript
const payloadIn = msg.payload;
const pathArray = payloadIn.asset_context.path;

// Função auxiliar para buscar no caminho
const getContextId = (targetType) => {
    const item = pathArray.find(p => p.type === targetType);
    return item ? item.id : "unknown";
};

// Extrai componentes do caminho
const enterprise = getContextId("enterprise");
const site = getContextId("site");
const area = getContextId("area");

// Monta o grupo UNS
const groupId = `${enterprise}_${site}_${area}`;
const nodeId = getContextId("line");
const deviceId = getContextId("equipment");
```

**Conceitos:**
- **`.find()`:** Busca elemento em array que satisfaz condição
- **Template literals:** String interpolation com `${}`
- **Conditional operator:** `condition ? value1 : value2`

#### 4.2.3 Montagem do Payload Sparkplug B

```javascript
const dataMetrics = dataRaw.map(item => {
    let sparkplugType = "String";
    
    // Determina tipo Sparkplug B
    const explicitType = item.data_type.toLowerCase();
    if (explicitType === "float") sparkplugType = "Float";
    else if (explicitType === "boolean") sparkplugType = "Boolean";
    
    const metric = {
        name: item.name,
        value: item.value,
        type: sparkplugType,
        timestamp: dataTimestamp
    };
    
    if (item.unit) {
        metric.properties = {
            engUnit: { type: "String", value: item.unit }
        };
    }
    
    return metric;
});

msg.topic = `spBv1.0/${groupId}/DDATA/${nodeId}/${deviceId}`;
msg.payload = { metrics: dataMetrics };
```

**Conceito:**
- **`.map()`:** Transforma cada elemento de um array

### 4.3 Camada 3: SIDA-Core (Go)

#### 4.3.1 Clean Architecture em Go

O sida-core segue o padrão **Clean Architecture**:

```
┌─────────────────────────────────────────────────┐
│            adapters (infrastructure)           │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Handler │  │ Repository│  │  Middleware │  │
│  └──────────┘  └──────────┘  └─────────────┘  │
└─────────────────────────────────────────────────┘
                  │       │
                  ▼       ▼
┌─────────────────────────────────────────────────┐
│              core (domain)                      │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Domain  │  │   Ports  │  │  Services   │  │
│  └──────────┘  └──────────┘  └─────────────┘  │
└─────────────────────────────────────────────────┘
```

**O que significa:**
- **adapters:** Implementação de interfaces (API, banco de dados)
- **core:** Lógica de negócio pura, sem dependências externas
- **Ports:** Interfaces que adapters devem implementar
- **Dependency Inversion:** Módulos de alto nível não dependem de baixo nível

#### 4.3.2 Go Modules (`go.mod`)

O `go.mod` gerencia dependências:

```go
module sida-core

go 1.26.3

require (
    github.com/gin-gonic/gin v1.12.0
    github.com/mattn/go-sqlite3 v1.14.44
)
```

**Conceitos:**
- **Módulo:** Pacote principal do Go
- **Versionamento:** Semver (Semantic Versioning)

#### 4.3.3 O Arquivo `main.go`

```go
package main

import (
    "log"
    "os"
    
    "sida-core/internal/adapters/handler"
    "sida-core/internal/adapters/repository"
    "sida-core/internal/core/services"
    "sida-core/internal/api"
    
    "github.com/gin-gonic/gin"
)

func main() {
    // Carrega variáveis de ambiente
    _ = godotenv.Load("/app/data/.env")
    
    // Inicializa banco de dados
    repo, err := repository.NewSQLiteManifestRepository("./data/sida_config.db")
    
    // Inicializa serviço ZMQ
    zmqPub, err := services.NewZMQPublisher("0.0.0.0:5556")
    
    // Inicializa handlers e serviços
    authService := services.NewAuthService()
    authHandler := handler.NewAuthHandler(authService)
    manifestHandler := handler.NewManifestHandler(repo, zmqPub)
    
    // Configura roteamento
    router := gin.Default()
    api.SetupRoutes(router, manifestHandler, authHandler, systemHandler, authService)
    
    // Inicia servidor HTTP
    srv := &http.Server{Addr: ":8000", Handler: router}
    srv.ListenAndServe()
}
```

**Conceitos:**
- **`package main`:** Pacote principal, ponto de entrada
- **`import`:** Importa pacotes externos
- **`:=`:** Declaração com inferência de tipo

#### 4.3.4 Handlers HTTP

O handler de manifesto:

```go
func (h *ManifestHandler) UploadManifest(c *gin.Context) {
    // Recebe JSON da requisição
    var payload domain.Manifest
    if err := c.ShouldBindJSON(&payload); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "JSON inválido"})
        return
    }
    
    // Salva no banco
    manifest := domain.Manifest{
        GatewayID: payload.GatewayID,
        Config:    payload.Config,
        UpdatedAt: time.Now(),
    }
    
    if err := h.repo.Save(c.Request.Context(), manifest); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "DB error"})
        return
    }
    
    // Notifica via ZMQ
    _ = h.zmq.PublishUpdate(manifest.GatewayID)
    
    c.JSON(http.StatusOK, gin.H{
        "status": "success",
        "message": "Manifesto atualizado",
    })
}
```

**Conceitos:**
- **`*gin.Context`:** Contexto da requisição HTTP
- **`:=`:** Inferência de tipo em Go
- **`gin.H`:** Mapa para JSON (`map[string]interface{}`)

#### 4.3.5 Repository Pattern

```go
type sqliteManifestRepo struct {
    db *sql.DB
}

func NewSQLiteManifestRepository(dbPath string) (*sqliteManifestRepo, error) {
    db, err := sql.Open("sqlite3", dbPath+"?_journal_mode=WAL&_busy_timeout=5000")
    // Cria tabela se não existir
    query := `CREATE TABLE IF NOT EXISTS edge_manifests (...)`
    db.Exec(query)
    return &sqliteManifestRepo{db: db}, nil
}

func (r *sqliteManifestRepo) Save(ctx context.Context, manifest domain.Manifest) error {
    configBytes, _ := json.Marshal(manifest.Config)
    query := `INSERT INTO edge_manifests VALUES (?, ?, ?) ON CONFLICT(...)`
    r.db.ExecContext(ctx, query, manifest.GatewayID, string(configBytes), manifest.UpdatedAt)
    return err
}
```

**Conceitos:**
- **Pattern Repository:** Abstração para acesso a dados
- **SQL Injection prevention:** Use parametrized queries
- **WAL mode:** Write-Ahead Logging para concorrência

#### 4.3.6 ZeroMQ Service

```go
type ZMQPublisher struct {
    socket *zmq4.Socket
}

func NewZMQPublisher(tcpPath string) (*ZMQPublisher, error) {
    socket, err := zmq4.NewSocket(zmq4.PUB)
    address := "tcp://" + tcpPath
    socket.Bind(address)  // Bind para PUB socket
    return &ZMQPublisher{socket: socket}, nil
}

func (p *ZMQPublisher) PublishUpdate(gatewayID string) error {
    topic := "sida/manifest/" + gatewayID
    _, err := p.socket.SendMessage(topic, "RELOAD")
    return err
}
```

**Conceitos de ZeroMQ:**
- **PUB/SUB:** Publish/Subscribe - um para muitos
- **Bind vs Connect:** PUB faz Bind, SUB faz Connect
- **Topics:** Filtragem por prefixo

### 4.4 Comunicação entre Microsserviços

#### 4.4.1 ZeroMQ Protocolos

| Tipo | Uso | Padrão |
|------|-----|--------|
| **PUB/SUB** | Broadcast de mensagens | Publisher Bind, Subscriber Connect |
| **PUSH/PULL** | Distribuição de workload | Pull Connect, Push Bind |
| **REQ/REP** | Request/Response síncrono | - |

No SIDA:
- **Ingestion → Context:** PUSH/PULL (IPC)
- **Context → Delivery:** PUSH/PULL (IPC)
- **Core → Todos:** PUB/SUB (TCP)

#### 4.4.2 Endereçamento ZeroMQ

```go
// IPC (Inter-Process Communication) - localhost
"ipc:///tmp/.ipc/ingestion.ipc"

// TCP (TCP/IP Network)
"tcp://sida-core:5556"
```

**Conceitos:**
- **IPC:** Comunicação rápida entre processos na mesma máquina
- **TCP:** Comunicação em rede

---

## Parte 5: Orquestração com Docker Compose

### 5.1 Docker Compose YAML

```yaml
version: '3.8'

networks:
  sida_network:
    driver: bridge

services:
  sida-core:
    build: ./sida-core
    container_name: sida-core
    ports:
      - "8000:8000"  # Host:Container
    volumes:
      - ./sida-core/data:/app/data  # Compartilhamento de dados
    networks:
      - sida_network
    restart: unless-stopped
    depends_on:
      - poc-ingestion  # Ordem de inicialização

  poc-ingestion:
    build:
      context: .
      dockerfile: ./infra/Dockerfile
      args:
        - PROJECT_DIR=./core/ingestion
    container_name: sida-poc-ingestion
    environment:
      - TZ=America/Recife
      - FLOWS=flows.json
    ports:
      - "1881:1880"  # Node-RED porta padrão
    volumes:
      - ./core/ingestion:/data
      - sida_ipc:/tmp/.ipc  # Volume compartilhado para IPC
    networks:
      - sida_network
    extra_hosts:
      - "host.docker.internal:host-gateway"  # Acesso ao host
    restart: unless-stopped
    depends_on:
      - sida-core
```

**Conceitos:**
- **ports:** Mapeamento de portas Host → Container
- **volumes:** Persistência e compartilhamento
- **networks:** Isolamento e comunicação
- **depends_on:** Ordem de inicialização

### 5.2 Construção de Imagens

O Dockerfile do sida-core usa **multi-stage build**:

```dockerfile
# Stage 1: Frontend build
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# Stage 2: Backend build
FROM golang:alpine AS builder
RUN apk add --no-cache gcc musl-dev pkgconfig zeromq-dev
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=1 GOOS=linux go build -ldflags="-s -w" -o sida-core cmd/server/main.go

# Stage 3: Runtime
FROM alpine:latest
RUN apk --no-cache add ca-certificates tzdata zeromq
WORKDIR /app
COPY --from=builder /app/sida-core .
COPY --from=frontend-builder /app/dist ./public
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["./sida-core"]
```

**Conceitos:**
- **Multi-stage build:** Reduz tamanho final da imagem
- **Alpine Linux:** Image minimalista (~5MB)
- **Layer caching:** Reutilização de layers para builds rápidos

---

## Parte 6: Configuração e Deploy

### 6.1 Variáveis de Ambiente

```bash
# Arquivo: sida-core/data/.env
EDGE_GATEWAY_ID=sida_edge_001
EDGE_ENGINEER_PIN=1234
```

**Variáveis:**
- `EDGE_GATEWAY_ID`: Identificador único do gateway
- `EDGE_ENGINEER_PIN`: PIN para autenticação (SHA256)

### 6.2 Fluxo de Dados Completo

```
┌──────────────┐
│   CLP A      │  Modbus TCP
│ 192.168.0.10 │  Porta 5020
└──────┬───────┘
       │
       │  (Ingestion Node-RED)
       ▼
┌──────────────────┐
│  sida-poc-       │
│  ingestion:1881  │
└────────┬─────────┘
         │ ZeroMQ IPC
         ▼
┌──────────────────┐
│  sida-poc-       │
│  context:1882    │
└────────┬─────────┘
         │ ZeroMQ IPC
         ▼
┌──────────────────┐
│  sida-poc-       │
│  delivery:1883   │
└────────┬─────────┘
         │ MQTT
         ▼
┌──────────────────┐
│  GCP Cloud       │
│  MQTT Broker     │
│  34.134.241.250  │
└──────────────────┘
```

### 6.3 Comandos de Deploy

```bash
# Build e start de todos os serviços
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (atenção: apaga dados!)
docker-compose down -v
```

### 6.4 Testando a Implementação

**1. Verificar containers:**
```bash
docker-compose ps
# Deve mostrar todos os containers como "Up"
```

**2. Acessar Node-RED (Ingestão):**
```
http://localhost:1881
```

**3. Verificar API do sida-core:**
```bash
curl http://localhost:8000/api/health
# Resposta: {"status":"UP","service":"sida-core","timestamp":"..."}
```

**4. Verificar logs em tempo real:**
```bash
docker-compose logs -f sida-core
docker-compose logs -f sida-poc-ingestion
docker-compose logs -f sida-poc-delivery
```

---

## Parte 7: Protocolos e Padrões

### 7.1 Protocolo Modbus

#### Estrutura da Mensagem Modbus TCP

```
┌─────────────────────────────────────────────────────────────┐
│                     Modbus TCP PDU                         │
├─────────────────────────────────────────────────────────────┤
│  MBAP Header (7 bytes)     │  Function Code (1 byte)       │
│  Transaction ID (2)        │  Protocol ID (2) = 0          │
│  Length (2)                │  Unit ID (1)                  │
│  Request/Response Data     │                               │
└─────────────────────────────────────────────────────────────┘
```

#### Funções Principais

| Código | Função | Descrição |
|--------|--------|-----------|
| 01 | Read Coils | Ler bits |
| 02 | Read Discrete Inputs | Inputs binários |
| 03 | Read Holding Registers | Ler registers (16-bit) |
| 04 | Read Input Registers | Registers de entrada |
| 06 | Write Single Register | Escrever register único |
| 16 | Write Multiple Registers | Escrever múltiplos registers |

#### Exemplo de Leitura

```javascript
// Ler holding register 40001 (endereço interno 0)
const data = await client.readHoldingRegisters(0, 1);
// Retorna: { address, data: [valor] }
```

**Recurso:** [Modbus Protocol Specification](https://modbus.org/specs.php)

### 7.2 Sparkplug B Protocol

#### Estrutura do Payload

```
┌─────────────────────────────────────────────────────────────┐
│                  Sparkplug B Message                        │
├─────────────────────────────────────────────────────────────┤
│  Topic: spBv1.0/GroupID/DDATA/Node/Device                  │
│  Payload: protobuf-encoded                                  │
│    - MessageType (DDATA = 3)                               │
│    - Timestamp                                             │
│    - Metrics[]                                             │
│      - Name                                                │
│      - Type (Int32, Float, String, etc.)                   │
│      - Value                                               │
│      - Properties (engUnit, etc.)                          │
└─────────────────────────────────────────────────────────────┘
```

#### Tipos de Mensagem

| Tipo | Código | Uso |
|------|--------|-----|
| DATA | 0 | Mensagem de dados |
| NBIRTH | 1 | Nascimento do Node |
| DBIRTH | 2 | Nascimento do Device |
| DDATA | 3 | Dados do Device |
| DEATH | 4 | Morte do Device |
| DCMD | 5 | Comando para Device |
| SCMD | 6 | Comando de sistema |

---

## Parte 8: Solução de Problemas

### 8.1 Erros Comuns

#### Error: "Connection refused"

**Causa:** Serviço não está rodando

**Solução:**
```bash
docker-compose ps
docker-compose logs <service-name>
```

#### Error: "Cannot find module"

**Causa:** Dependências Node-RED não instaladas

**Solução:**
```bash
docker-compose down
docker-compose up --build
```

#### Error: "ZMQ connection failed"

**Causa:** Problema de comunicação IPC ou rede

**Solução:**
```bash
# Verificar volumes
docker volume ls | grep sida_ipc
docker-compose down -v  # Remove volumes
docker-compose up       # Recria
```

### 8.2 Logs Úteis

**sida-core:**
```bash
docker-compose logs -f sida-core | grep -i "error\|zmq"
```

**Ingestão:**
```bash
docker-compose logs -f sida-poc-ingestion | grep -i "modbus\|error"
```

**Delivery:**
```bash
docker-compose logs -f sida-poc-delivery | grep -i "mqtt\|error"
```

---

## Parte 9: Próximos Passos

### 9.1 Extensões Sugeridas

1. **Adicionar OPC UA Support**
   - Usar `node-red-contrib-opcua`
   - Implementar similar ao Modbus

2. **Implementar Store and Forward**
   - Buffer de mensagens em SQLite
   - Sincronização quando conexão MQTT restabelecida

3. **Adicionar Prometheus Metrics**
   - Endpoint `/metrics` no sida-core
   - Exportar contadores de mensagens, latência

4. **Implementar CI/CD**
   - Testes automatizados com Jest
   - Build no GitHub Actions

### 9.2 Recursos de Aprofundamento

| Tema | Recurso |
|------|---------|
| Go Programming | [Go by Example](https://gobyexample.com/) |
| Node-RED Advanced | [Node-RED Cookbook](https://nodered.org/docs/recipes/) |
| MQTT Patterns | [Eclipse Hono](https://www.eclipse.org/hono/) |
| Docker Best Practices | [12 Factor App](https://12factor.net/) |
| Industrial IoT | [Industrial Internet Consortium](https://www.iiconsortium.org/) |

---

## Conclusão

Este guia abrangeu os principais conceitos e técnicas envolvidos na implementação do SIDA-Middleware. A jornada de implementação envolve:

1. **Entendimento do domínio:** Conhecer os protocolos industriais e a arquitetura UNS
2. **Setup técnico:** Instalar e configurar as ferramentas (Node.js, Docker, Go)
3. **Implementação:** Codificar as camadas (Ingestão, Contexto, Delivery, Core)
4. **Orquestração:** Gerenciar múltiplos microsserviços com Docker Compose
5. **Monitoramento:** Acompanhar logs e métricas

A arquitetura do SIDA demonstra boas práticas de engenharia de software:
- **Separação de responsabilidades** (Clean Architecture)
- **Isolamento** (containers Docker)
- **Resiliência** (reconn automático, buffer)
- **Escalabilidade** (microserviços independentes)

Boa implementação! 🏭

---

## Índice de Referências Rápidas

### Comandos Docker
```bash
docker-compose up -d        # Iniciar
docker-compose down         # Parar
docker-compose logs -f      # Ver logs
docker-compose ps           # Status
```

### Endpoints da API
```
GET  /api/health            # Health check
POST /api/auth/unlock       # Login (PIN)
GET  /api/config/manifest   # Obter config
POST /api/config/manifest   # Atualizar config
GET  /api/system/info       # Informações do gateway
```

### Portas
```
8000  - sida-core (API)
1881  - sida-poc-ingestion
1882  - sida-poc-context
1883  - sida-poc-delivery
5020  - Simulador Modbus
```

### Ports ZeroMQ
```
ipc:///tmp/.ipc/ingestion.ipc   # Ingestion → Context
ipc:///tmp/.ipc/context.ipc     # Context → Delivery
tcp://sida-core:5556            # Core broadcast
```
