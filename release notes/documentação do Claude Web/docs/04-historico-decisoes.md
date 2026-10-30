# Histórico de Decisões do Projeto

Registro cronológico das decisões de design tomadas durante a concepção do projeto (derivado da conversa de planejamento). Cada entrada traz a **decisão**, o **racional** e, quando relevante, as **alternativas descartadas**. Serve como memória de projeto para o Claude Code e para a banca.

---

## 0. Ponto de partida

**Contexto.** Existiam dois trabalhos distintos com sobreposição de domínio (IIoT/interoperabilidade):

- **SIDA** — middleware de borda em implementação pela equipe (Releases v1.0 e v2.0; pré-projeto do desafio por E. R. S. Araujo). Pipeline: ingestão → contextualização ISA-95 → entrega Sparkplug B → UNS (broker MQTT no GCP). Arquitetura de microsserviços (sida-core em Go/Gin/Clean Architecture; ingestão/contexto/entrega em Node-RED; ZeroMQ; SQLite).
- **Projeto individual (SENAI, D1)** — proposta de expandir o framework **InterEdge** (Azad et al.) com o protocolo MQTT, avaliada por experimento controlado (ROM/RAM/latência; DSR + GQM/ANOVA) em ESP32.

**Fontes acadêmicas do InterEdge:** Azad et al. 2023 (IEEE IoT J — modelo/framework), 2025 (Computer Communications — nível de rede, Wi-Fi/Bluetooth), 2025 (JISA — níveis sintático e semântico).

---

## 1. Decisão: mudar o projeto individual

**Decisão.** Abandonar o escopo original (InterEdge + MQTT com experimento ROM/RAM/latência) e adotar uma **extensão da capacidade de ingestão do SIDA em duas etapas**:

- **Etapa 1** — SIDA distribuído em vários Raspberry Pi, provendo arquitetura descentralizada; gerenciamento de frota sem nó central.
- **Etapa 2** — dispositivos Classe 0/1 alimentando a camada de ingestão do SIDA.

**Racional.** Aproveita o código já entregue do SIDA e o background do candidato no InterEdge, atacando problemas reais (resiliência de borda e cobertura de fontes).

---

## 2. Esclarecimento: o que significa "sem nó central"

**Decisão.** "Sem nó central" = **cada Raspberry Pi roda a stack completa do SIDA** (incluindo seu `sida-core` local) e **publica no mesmo UNS**. Elimina-se o SPOF **do plano de borda**, não a centralização do broker.

**Racional.** O broker MQTT/UNS na nuvem permanece ponto de convergência de dados — isso é inerente ao padrão UNS e é **aceitável**. A frota se coordena pela autodescrição no namespace, sem um coordenador de borda.

**Ambiguidade resolvida.** "Gerenciamento de frota" não contradiz "sem nó central": a frota se autodescreve (padrão birth/death do Sparkplug), e qualquer assinante observa o estado sem que um nó dependa de outro.

---

## 3. Decisão: relação entre Etapa 1 e Etapa 2

**Decisão.** O dispositivo Classe 0/1 é tratado como **"mais uma fonte de protocolo"** pela camada de ingestão (como o SIDA já faz com Modbus), preservando a separação de responsabilidades (ingestão traduz; contexto semantiza). **Apenas sensoriamento** — sem controle/atuação local.

**Alternativas descartadas.**
- Dispositivo aplicar sua própria contextualização e publicar Sparkplug direto no UNS → criaria dois motores de contextualização e violaria o *single source of truth* do SIDA.
- Dispositivo fazer controle local (soft-PLC) → escopo muito maior.

---

## 4. Decisão: mapear o InterEdge sobre o SIDA (não reimplementar)

**Decisão.** Tanto os RPi quanto os dispositivos Classe 0/1 são enquadrados na arquitetura InterEdge por **mapeamento arquitetural** — demonstrando que os artefatos que o SIDA já possui realizam as camadas do framework — e **não** por reimplementação das camadas.

**Contribuição identificada.** Os artigos do InterEdge declaram que o **nível organizacional nunca foi implementado**. O motor ISA-95 do SIDA realiza esse nível na prática. O projeto posiciona o SIDA como **primeira realização concreta do nível organizacional**, enquanto estende o nível mais baixo (rede/física) para dispositivos Classe 0/1.

**Alternativa descartada.** Reimplementar literalmente as camadas InterEdge (profile/register/service/control) no RPi, em paralelo ao SIDA — trabalho de engenharia redundante.

---

## 5. Decisão: avaliação por injeção de falha

**Decisão.** A meta central (eliminar SPOF de borda) é **qualitativa**; adota-se **teste de injeção de falha** como avaliação (derrubar um nó; verificar continuidade dos sobreviventes e detecção via `NDEATH`).

**Racional.** Substitui o experimento controlado ROM/RAM/latência do projeto original (que deixou de fazer sentido com a mudança de escopo). Alinha-se aos critérios de aceite de resiliência já praticados no SIDA.

---

## 6. Análise: e se o projeto contiver só a Etapa 1?

**Constatação.** Sem a Etapa 2, a instanciação do InterEdge fica **incompleta justamente no nível de rede** (o que dá nome ao framework). Além disso, a Etapa 1 (frota/SPOF) é **ortogonal** ao modelo de camadas do InterEdge — o quanto ela é "InterEdge" depende do mecanismo de coordenação escolhido:

- Coordenação por **Sparkplug/UNS** → resiliência UNS-nativa; vínculo fraco com o InterEdge.
- Coordenação por **controller-to-controller** → instancia literalmente o modelo multi-controlador descentralizado do InterEdge; vínculo forte.

---

## 7. Decisão final: adotar A e B simultaneamente

**Decisão.** Usar **os dois mecanismos ao mesmo tempo**, em **planos distintos**:

- **A — Sparkplug/UNS**, plano **norte** (borda→nuvem): ciclo de vida + observabilidade da frota.
- **B — controller-to-controller (InterEdge)**, plano **leste-oeste** (borda↔borda): malha ZeroMQ de pares, *probes*, roteamento; detecção de queda local.

**Racional.** B garante que a frota seja uma **instanciação InterEdge genuína** (plano de controle descentralizado) e completa o enquadramento teórico; A entrega resiliência/observabilidade nativas da stack. Juntos, fornecem **dois sinais de liveness independentes**, e o plano leste-oeste sobrevive a uma queda do broker. Os planos não conflitam por usarem transportes/portas distintos.

**Consequência.** O núcleo de B é **coordenação/consciência de frota**; usar B para *failover de dados* de um nó isolado é **extensão opcional** (encosta no store-and-forward, que é roadmap).

---

## 8. Status de implementação registrado

- **T0.3 (portabilidade ARM64):** ✅ **validada**. Compatibilidade da stack (incl. bindings ZeroMQ) confirmada no Raspberry Pi. O principal risco de fundação está descartado; o maior risco ativo passa a ser o **Plano B** (reimplementação em Go/RPi).

---

## 9. Delimitações de escopo consolidadas

Fora de escopo, por decisão:

- Redundância do broker da nuvem (SPOF de dados) — inerente ao UNS.
- Store-and-forward persistente com WAL (instabilidade RPi↔nuvem) — roadmap.
- Segurança TLS/mTLS e evolução de auth (PIN → OAuth2) — trabalho futuro.
- Controle/atuação local em dispositivos Classe 0/1 — apenas sensoriamento.
- Failover de dados via par — extensão opcional.

---

## Metodologia adotada

**Design Science Research (DSR)** (Hevner 2004; Peffers 2007), com artefatos: mapeamento formal (teórico), decisão de coordenação (decisão) e frota + adaptador (software); demonstração em bancada; avaliação por injeção de falha; comunicação por relatório técnico + artigo.
