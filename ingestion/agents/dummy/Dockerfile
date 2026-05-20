FROM ubuntu:22.04

RUN apt-get update && apt-get install -y build-essential cmake libzmq3-dev

WORKDIR /app

# 1. Copia as libs globalmente
COPY ./libs /app/libs

# 2. Copia a pasta inteira de agentes (para ele enxergar o CMake geral)
COPY ./ingestion/agents /app/agents

WORKDIR /app/agents/build

# 3. O SEGREDO AQUI: 
# Gera o Makefile mestre e manda compilar APENAS o binário 'dummy_agent'
RUN cmake .. && make dummy_agent

# 4. Por padrão, o CMake joga o binário dentro da pasta do subdiretório
CMD ["./dummy/dummy_agent"]