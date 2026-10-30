# Projeto SIDA × InterEdge — Ingestão Distribuída e Resiliente

Pacote de documentação e artefatos do projeto que evolui o middleware **SIDA (Smart Industrial DataOps Agent)** para uma **arquitetura de ingestão distribuída e resiliente**, eliminando o ponto único de falha (SPOF) na borda e integrando dispositivos de recursos restritos (Classe 0/1), fundamentado no framework **InterEdge**.

Este repositório reúne o **planejamento e a documentação**. A implementação ocorre sobre o código-fonte do SIDA (`sida-middleware`).

## Estrutura

```
.
├── README.md                       # este arquivo
├── CLAUDE.md                       # contexto persistente para o agente Claude Code
└── docs/
    ├── 01-projeto.md               # projeto experimental completo (SENAI/DSR)
    ├── 01-projeto.docx             # mesma versão, formato SENAI (Word)
    ├── 01-projeto.pdf              # mesma versão, PDF
    ├── 02-guia-implementacao.md    # guia passo a passo (tarefas T0.x–T5.x)
    ├── 03-release-notes-v3.md      # Release Notes v3.0 (com figuras)
    ├── 04-historico-decisoes.md    # registro cronológico das decisões de projeto
    └── figuras/                    # diagramas (referenciados pelas release notes)
```

## Por onde começar

1. **`CLAUDE.md`** — leia primeiro se você é um agente. Resume arquitetura, onde mexer no código e o escopo.
2. **`docs/04-historico-decisoes.md`** — por que o projeto é como é (decisões e alternativas descartadas).
3. **`docs/02-guia-implementacao.md`** — o que implementar, em ordem, com critérios de pronto (IDs `T…`).
4. **`docs/03-release-notes-v3.md`** — visão do ciclo v3.0, PoCs e critérios de aceite.
5. **`docs/01-projeto.md`** — fundamentação, objetivos, metodologia (DSR) e diagramas.

## Estado atual

- SIDA **v2.0 entregue** (MVP validado ponta a ponta: Modbus → ISA-95 → Sparkplug B → UNS).
- v3.0 **em planejamento/implementação**.
- **T0.3 (portabilidade ARM64) já validada** — o principal risco de fundação está descartado.
- Decisão de coordenação fechada: **Mecanismos A + B simultâneos** (planos norte e leste-oeste).

## Convenções de referência

As tarefas usam IDs estáveis (`T0.1`, `T1A.4`, `T1B.3`, `T2.3`, …) definidos em `docs/02-guia-implementacao.md`.
Os entregáveis usam `E01`–`E07` (detalhados em `docs/03-release-notes-v3.md`).
