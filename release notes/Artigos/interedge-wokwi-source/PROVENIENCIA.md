# Código-fonte de referência do InterEdge (autores)

Extraído em 2026-09-09 do projeto Wokwi público dos autores (Tanzima Azad, Griffith University),
citado no artigo **"Syntactic and Semantic Edge Interoperability"** (JISA 2025, DOI 10.5753/jisa.2025.4996 —
arquivo `../Azad10458806.pdf`).

- **Wokwi:** https://wokwi.com/projects/396638811657719809 (nome interno do projeto: "HDEI")
- **Tinkercad (cenário multi-controlador):** https://www.tinkercad.com/things/i8c4z51qvzQ-syntactic-n-semantic
  — **não** extraído (exige login). O modelo de roteamento multi-controlador está descrito no
  artigo JISA (Tabelas 15–17) e, com algoritmos completos, no artigo fundacional
  **"Hierarchical Decentralised Edge Interoperability"** (IEEE IoT J 2023, DOI 10.1109/JIOT.2023.3340298),
  Algoritmos 1–4.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `hdei.h` | Classe `HDEI`: protótipos + **profiles/registers como variáveis privadas** (`_DevProfile_*`, `_DataProfile_*`, `_CtrlProfileESP32_*`, `_CtrlProfileUno_*`, `_DevRegister1/2_*`, `_CtrlRegisterESP32/Uno_*`). Substituem os arquivos-texto em EEPROM (limitação do simulador). |
| `hdei.cpp` | Implementação. `formula()` (avaliador de expressão **pós-fixa** por pilha) e `ReadData()`/`DataReadingSchedule()` completos. `NeedAction`, `NeedRouting`, `WriteData`, `WriteMessage`, `ReadMessage`, `RouteMessage`, `MessageReadingSchedule` são **stubs vazios** neste cenário (1 controlador, sem atuadores, sem malha). |
| `OurEsp32Solution.ino` / `OurUnoSolution.ino` | `ControllerProgram` mínimo: `DataReadingSchedule` → `ReadData`. Versões isoladas p/ medir ROM/RAM/latência. |
| `sketch.ino` | Harness de benchmark: cronometra a solução InterEdge vs SOS / SensorThings API / EdgeX Foundry. |
| `SOS*.ino`, `SensorThings*.ino`, `EdgeXFoundry*.ino` | Implementações concorrentes (HTTP p/ nuvem) usadas só na comparação de desempenho. |
| `diagram.json` | Circuito Wokwi: ESP32 + sensor NTC de temperatura no pino D15. |

## Observações para o SIDA (Plano B)

- O registro relevante é o **Controller Register** (`hdei.h`, campos `_CtrlRegister*_*`):
  `ControllerId`, `ConnectedDevices`, `ConnectedControllers`, `SourceDevices`, `ConditionActions`,
  `DestinationDevices`, `DeviceProbeIntervals`, `MessageBuffer`, `ControllerProbeIntervals`.
- Roteamento (JISA Tab. 17 / IoT-J Alg. 2): a mensagem carrega **dados + caminho** como cadeia de IDs
  de controlador terminando no dispositivo (ex.: `C1-C2-C5-C7-D2`). `RouteMessage` lê o próximo ID;
  se ≠ ao próprio, encaminha. `MessageBuffer` é um **array com seção dedicada por remetente**
  (evita conflito de escrita concorrente).
- Loop de controle (IoT-J Alg. 3–4): `InitSchedule` (lê `DeviceProbeIntervals` e `ControllerProbeIntervals`)
  → `while true`: `DataReadingScheduled` → `ReadData` → `NeedAction` → se `NeedRouting`
  então `WriteMessage`+`RouteMessage` senão `WriteData`; depois `MessageReadingScheduled` → `ReadMessage`
  → roteia/entrega; `UpdateSchedule`.
- **Não há descoberta dinâmica de pares nem detecção de falha explícita** no InterEdge original:
  `ConnectedControllers` é estático (pré-configurado) e o probe serve para agendar leitura de mensagens,
  não para heartbeat de liveness. O SIDA precisa **adicionar** a semântica de timeout/queda de par.
