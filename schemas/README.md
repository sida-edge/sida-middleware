# 📜 Schemas e Contratos de Dados

Este diretório atua como a única **Fonte da Verdade** para a estrutura de dados dentro do projeto SIDA. 

Como a arquitetura é poliglota e altamente distribuída, é vital que todos os microsserviços concordem exatamente com o formato da mensagem que está sendo transmitida, evitando quebras de compatibilidade entre as camadas.

## 📂 O que você encontra aqui:

1.  **Arquivos Protobuf (`.proto`):** O schema oficial do **Sparkplug B** da Eclipse Foundation (`sparkplug_b.proto`).
2.  **Modelos ISA-95:** Arquivos JSON documentando a estrutura de semântica imposta na Camada 2 (Contextualização) sobre os dados brutos de chão de fábrica.
<!-- 3.  **Contratos de Controle:** Definições dos payloads de Comando (`DCMD`, `NCMD`) para o controle reverso da Borda. -->

## ⚠️ Regra de Desenvolvimento

**Nenhum microsserviço deve possuir schemas próprios definidos "em código".** 
Se a Camada 1 precisa de uma atualização no formato do dado, a alteração deve ser feita primeiramente nesta pasta, garantindo que a Camada 2 tenha acesso imediato à nova regra antes do *deploy*.