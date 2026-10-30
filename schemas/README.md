# 📜 Schemas e Contratos de Dados

Este diretório atua como a única **Fonte da Verdade** para a estrutura de dados dentro do projeto SIDA. 

Como a arquitetura é poliglota e altamente distribuída, é vital que todos os microsserviços concordem exatamente com o formato da mensagem que está sendo transmitida, evitando quebras de compatibilidade entre as camadas.

## 📂 O que você encontra aqui:

1.  **`sparkplug_b.proto`** — schema normativo do **Sparkplug B Payload** (Eclipse Sparkplug 3.0.0 / projeto Eclipse Tahu), cópia *verbatim* do upstream. É a **fonte única da verdade** do contrato Sparkplug B do SIDA (SDD Etapa 1 do Ciclo V3.0, tarefa `T1A.1`).
2.  **Modelos ISA-95:** Arquivos JSON documentando a estrutura de semântica imposta na Camada 2 (Contextualização) sobre os dados brutos de chão de fábrica.
<!-- 3.  **Contratos de Controle:** Definições dos payloads de Comando (`DCMD`, `NCMD`) para o controle reverso da Borda. -->

### Sobre o `sparkplug_b.proto`

- **Uso:** referência para revisão/validação e para consumidores que precisam decodificar o payload (inclusive o **plano B** em Go). **Não** é carregado em runtime pelo Node-RED — a lib `sparkplug-payload` já embute o schema equivalente.
- **Upstream:** `github.com/eclipse-sparkplug/sparkplug` — `specification/src/main/protobuf/sparkplug_b.proto` (Eclipse Public License 2.0).
- **Não editar** para adaptar a um consumidor: se o formato precisar mudar, discutir o contrato aqui antes de qualquer *deploy*.

## ⚠️ Regra de Desenvolvimento

**Nenhum microsserviço deve possuir schemas próprios definidos "em código".** 
Se a Camada 1 precisa de uma atualização no formato do dado, a alteração deve ser feita primeiramente nesta pasta, garantindo que a Camada 2 tenha acesso imediato à nova regra antes do *deploy*.