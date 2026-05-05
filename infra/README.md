# 🐳 Infraestrutura e Orquestração

Esta pasta contém o ambiente de desenvolvimento dockerizado do SIDA.

O orquestrador sobe os microsserviços do SIDA, estabelece a rede interna para comunicação entre os containers e conecta a saída da última camada ao broker MQTT.

## 🚀 Como rodar o ambiente local

**Pré-requisitos:**
*   Docker Engine
*   Docker Compose

**Passo a passo:**

1.  Acesse a pasta de infraestrutura:
    ```bash
    cd infra
    ```
2.  (Opcional) Edite as variáveis de ambiente no arquivo `docker-compose.yml`, como o IP do broker MQTT, caso necessário.
3.  Inicie a arquitetura do SIDA:
    ```bash
    docker-compose up -d --build
    ```
4.  O comando `--build` garantirá que todos os microsserviços no diretório `/core` sejam recompilados na hora.
<!-- 5.  Acesse `http://localhost:1880` para visualizar o Node-RED rodando localmente (se o serviço analítico estiver habilitado no compose). -->

**Para encerrar o ambiente:**
```bash
docker-compose down