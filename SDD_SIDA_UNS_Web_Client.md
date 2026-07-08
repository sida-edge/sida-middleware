# SDD — SIDA UNS Web Client
### Cliente MQTT Web com decodificação Sparkplug B para o Unified Namespace do SIDA

---

## 0. Contexto herdado (não é parte do loop, apenas referência)

Este SDD descreve a **expansão** do ecossistema SIDA já validado nas Releases 1.0 e 2.0. O novo componente é um **consumidor** do UNS existente — ele não substitui, não modifica e não depende de alterações em `sida-core`, nos flows Node-RED (`sida-poc-ingestion`, `sida-poc-context`, `sida-poc-delivery`) ou no broker Mosquitto hospedado no GCP. O componente se conecta como "mais um cliente" na ponta de entrega (Camada 3 — UNS Delivery), consumindo o mesmo tópico raiz `spBv1.0/#` que hoje é escrito pelos flows de Delivery.

---

## 1. OBJETIVO DO LOOP

**Frase de missão (colável em prompt de implementação):**

> Construir um cliente MQTT web, empacotado em um container Docker, que se conecta via WebSocket a um broker Sparkplug B/MQTT já existente, exige login de usuário/senha em tela própria, decodifica nativamente o payload binário Sparkplug B (Protobuf) recebido em `spBv1.0/#`, descobre automaticamente a hierarquia Grupo/Nó/Dispositivo/Métrica a partir dos tópicos observados, mantém um buffer em memória do histórico recente de cada métrica, e renderiza um dashboard com gráficos de série temporal atualizados em tempo real — sem persistir nada em disco e sem alterar qualquer componente do backend SIDA já homologado.

**Resultado concreto esperado:**
- Uma imagem Docker (`sida-uns-client`) que, ao subir via `docker-compose`, expõe uma aplicação web estática servida por um servidor HTTP leve.
- A aplicação, ao ser aberta no navegador, apresenta uma tela de login (usuário/senha do broker MQTT) e, após autenticação bem-sucedida, um dashboard com árvore de dispositivos descobertos e gráficos de série temporal por métrica.
- Um arquivo de log de progresso persistente em disco (fora do container, montado como volume) que registra o avanço de cada task do loop, permitindo retomar o desenvolvimento após interrupção.

---

## 2. FRONTEIRAS (O QUE NÃO FAZER)

A IA que executar este loop **não pode, em hipótese alguma**:

1. Alterar, remover ou adicionar código nos repositórios/pastas `sida-core/`, `core/ingestion/`, `core/context/`, `core/delivery/` ou no `docker-compose.yml` já existente do SIDA — apenas **adicionar** um novo serviço a ele, sem tocar nos serviços atuais.
2. Alterar qualquer configuração do broker Mosquitto (listeners, portas, ACLs, usuários). O loop deve **assumir** que um listener MQTT-over-WebSocket já está disponível em um endereço configurável via variável de ambiente (`BROKER_WS_URL`); se essa premissa se mostrar falsa em teste, a IA deve **parar e reportar**, não tentar contornar reconfigurando o broker.
3. Instalar frameworks front-end pesados (React, Vue, Angular, Svelte etc.). Apenas JavaScript vanilla + a biblioteca `mqtt.js` (cliente MQTT sobre WebSocket) e uma biblioteca de decodificação Protobuf/Sparkplug B compatível com o schema da Eclipse Foundation.
4. Persistir credenciais de usuário em disco, em variável de ambiente do container, em cookies permanentes ou em qualquer armazenamento que sobreviva ao fechamento da aba do navegador. Credenciais só podem existir em memória da sessão do browser.
5. Persistir o histórico de métricas em disco, banco de dados ou `localStorage`/`sessionStorage`. O histórico vive exclusivamente em memória (variável JS) e é descartado ao recarregar a página.
6. Modificar o formato do payload Sparkplug B especificado no Anexo C do Tech Report v2.0 (estrutura `Message`/`Metric` compatível com o schema `.proto` da Eclipse Foundation) — o cliente é um leitor passivo desse contrato, nunca um transformador.
7. Adicionar autenticação alternativa (OAuth, tokens JWT próprios, etc.). Login é exclusivamente usuário/senha MQTT repassados diretamente ao broker na conexão.

**Se a IA "resolver" o problema de um jeito indesejado** (ex.: hardcodar credenciais, usar `localStorage` para "simplificar", ou pular a decodificação binária simulando com JSON fake), isso é considerado falha da task, não conclusão — a task deve ser revertida e refeita respeitando as fronteiras acima.

---

## 3. MÉTRICA DE CONCLUSÃO (CRITÉRIO DE PARADA)

### 3.1 Teste de aceite final
O loop é considerado concluído quando um script de teste automatizado, executado contra um broker MQTT local de teste (ex.: Mosquitto em container isolado, sem relação com o broker de produção do GCP):

1. Publica uma sequência `NBIRTH` → `DBIRTH` → `DDATA` simulando um dispositivo (`groupId/nodeId/deviceId` fictícios, com ao menos duas métricas, uma numérica e uma booleana).
2. Confirma que a interface web, após login bem-sucedido, exibe:
   - O dispositivo na árvore de descoberta, no caminho correto (Grupo → Nó → Dispositivo).
   - Um gráfico de série temporal por métrica numérica, com o primeiro ponto plotado corretamente (valor, timestamp e unidade, se presente em `properties.engUnit`).
   - O estado da métrica booleana refletido corretamente (não necessariamente como gráfico — pode ser indicador textual/visual).
3. Publica uma segunda mensagem `DDATA` com novo valor e confirma que o gráfico é atualizado incrementando um novo ponto (não substituindo o anterior), respeitando o buffer de histórico em memória.
4. Publica uma mensagem `NDEATH` para o nó e confirma que a UI sinaliza visualmente que o nó está offline (sem apagar o histórico já acumulado).

### 3.2 Ciclo de correção
Quando a verificação falhar, a IA deve seguir o ciclo: **ler o erro → identificar a causa → corrigir → repetir o teste**. 

**Número máximo de tentativas antes de escalar para o humano: 5.** Na 6ª falha consecutiva do mesmo teste, a IA deve parar, registrar no log de progresso a causa raiz suspeita e as tentativas já feitas, e aguardar intervenção humana — nunca prosseguir para a próxima task com esse teste ainda vermelho.

### 3.3 Estrutura de Sprints e Tasks (obrigatório para o loop)

O esforço deve ser dividido em **4 sprints**, cada um com tasks granulares. Cada task deve ser marcada como concluída **somente** após passar em sua verificação local antes de a IA seguir para a próxima.

| Sprint | Foco | Critério de saída do sprint |
|---|---|---|
| S1 | Esqueleto Docker + servidor estático + conexão MQTT WS crua (sem decodificação) | Container sobe via `docker-compose up`; console do browser mostra "conectado" ao broker de teste |
| S2 | Decodificação Sparkplug B + descoberta automática de hierarquia | Payloads binários de teste são decodificados e a árvore Grupo/Nó/Dispositivo é montada dinamicamente |
| S3 | Tela de login + buffer de histórico em memória + gráficos de série temporal | Login funcional; gráficos atualizam em tempo real a partir de `DDATA` |
| S4 | Casos extremos (reconexão, DDATA sem NBIRTH, NDEATH/DDEATH, payload corrompido) + teste de aceite final (3.1) | Todos os 4 passos do teste de aceite passam |

### 3.4 Registro de progresso (para interrupção/retomada)

A IA **deve** manter um arquivo `progress.json` na raiz do projeto (fora da imagem Docker, versionado no repositório), atualizado **imediatamente após cada task concluída**, com este contrato:

- Uma lista de tasks, cada uma com: identificador do sprint, identificador da task, descrição curta, status (`pendente` | `em_andamento` | `concluida` | `bloqueada`), timestamp da última atualização, e — se `bloqueada` — o motivo e o número de tentativas já feitas.

**Antes de iniciar qualquer trabalho em uma nova sessão**, a IA deve ler `progress.json` primeiro e retomar exatamente da última task não concluída, sem repetir tasks já marcadas como `concluida`.

---

## 4. ESTADO DO SISTEMA

| Variável | Tipo | Valores possíveis | Estado inicial |
|---|---|---|---|
| `connection_status` | enum | `desconectado`, `conectando`, `conectado`, `erro` | `desconectado` |
| `auth_status` | enum | `nao_autenticado`, `autenticando`, `autenticado`, `credenciais_invalidas` | `nao_autenticado` |
| `device_tree` | estrutura hierárquica em memória | mapa de `groupId` → `nodeId` → `deviceId` → lista de métricas conhecidas | vazio |
| `node_liveness` | mapa `groupId/nodeId` → enum | `online`, `offline` | ausente até primeiro `NBIRTH` |
| `metric_history_buffer` | mapa `deviceId/metricName` → lista de pontos `(timestamp, valor)` | tamanho máximo configurável (ver 7.4) | vazio |
| `alias_table` | mapa `groupId/nodeId` → mapa `alias numérico` → `nome da métrica` | populado a partir de `NBIRTH`/`DBIRTH` | vazio |
| `progress.json` (persistente, fora do runtime da aplicação) | arquivo | lista de tasks com status | conforme seção 3.4 |

---

## 5. ALGORITMOS E REGRAS DE NEGÓCIO

### 5.1 Fluxo de autenticação e conexão
1. Usuário abre a aplicação → tela de login é exibida, nenhuma conexão MQTT é feita ainda.
2. Usuário informa usuário e senha → a aplicação tenta abrir a conexão WebSocket com o broker usando essas credenciais.
3. Se a conexão for aceita pelo broker → `auth_status = autenticado`, `connection_status = conectado`, subscrição automática em `spBv1.0/#` é feita.
4. Se o broker rejeitar (erro de autenticação) → `auth_status = credenciais_invalidas`, a tela de login exibe mensagem de erro, nenhum dado em memória é populado.
5. Se a conexão cair após autenticada (rede, broker fora do ar) → `connection_status = erro`, a UI exibe banner de "reconectando", tenta reconectar automaticamente com backoff exponencial, reenviando as mesmas credenciais já digitadas (mantidas em memória da sessão).

### 5.2 Descoberta de hierarquia e decodificação
1. Toda mensagem recebida em `spBv1.0/{groupId}/{tipo}/{nodeId}[/{deviceId}]` é decodificada do formato binário Protobuf para uma estrutura de métricas.
2. Se `tipo = NBIRTH`: a tabela de alias do nó (`alias_table[groupId/nodeId]`) é (re)construída a partir da lista de métricas do payload; `node_liveness[groupId/nodeId] = online`.
3. Se `tipo = DBIRTH`: o dispositivo é adicionado a `device_tree` sob o nó correspondente; suas métricas iniciais populam `metric_history_buffer` com o primeiro ponto.
4. Se `tipo = DDATA`: cada métrica do payload é resolvida (por nome ou por alias, usando `alias_table`) e um novo ponto é adicionado ao buffer de histórico da métrica correspondente.
5. Se `tipo = NDEATH`: `node_liveness[groupId/nodeId] = offline`; todos os dispositivos sob esse nó são marcados como offline na árvore; histórico já acumulado **não é apagado**.
6. Se `tipo = DDEATH`: o dispositivo específico é marcado como offline; seu histórico permanece visível, mas sem novos pontos.

### 5.3 Casos de teste (few-shot, mínimo 5)

**Caso 1 — Fluxo feliz completo**
- Entrada: login válido → `NBIRTH` (nó `Line_1`) → `DBIRTH` (dispositivo `Pump_01`, métrica `Temperature`, valor 60.5, unidade `°C`) → `DDATA` (mesma métrica, valor 61.2)
- Saída esperada: árvore mostra `Line_1 > Pump_01`; gráfico de `Temperature` com 2 pontos (60.5 depois 61.2); unidade `°C` exibida.

**Caso 2 — Credenciais inválidas**
- Entrada: login com senha incorreta
- Saída esperada: `auth_status = credenciais_invalidas`; nenhuma subscrição MQTT é feita; nenhum dado aparece na árvore.

**Caso 3 — DDATA antes de NBIRTH (alias não resolvido)**
- Entrada: `DDATA` chega referenciando um alias numérico sem `NBIRTH`/`DBIRTH` prévio para aquele nó
- Saída esperada: a mensagem é descartada com log interno de aviso; nenhum ponto é adicionado ao histórico; a aplicação não trava nem lança exceção não tratada.

**Caso 4 — Queda e reconexão do WebSocket**
- Entrada: conexão MQTT cai após autenticada; broker de teste volta a responder após 5 segundos
- Saída esperada: UI mostra banner "reconectando" durante a queda; ao restabelecer, a subscrição em `spBv1.0/#` é refeita automaticamente; `node_liveness` de nós que não emitiram `NDEATH` permanece como estava antes da queda (não é resetado para offline apenas pela perda de conexão do client).

**Caso 5 — Payload corrompido/não-Protobuf válido**
- Entrada: mensagem chega em um tópico `spBv1.0/...` mas o binário não é um Protobuf Sparkplug B válido
- Saída esperada: a mensagem é descartada silenciosamente do ponto de vista da UI (sem crash), com registro em log de console; o restante do sistema continua operando normalmente.

**Caso 6 — NDEATH seguido de novo NBIRTH (religamento do nó)**
- Entrada: nó emite `NDEATH` → depois emite novo `NBIRTH` com a mesma identidade
- Saída esperada: nó volta a `online`; a tabela de alias é reconstruída a partir do novo `NBIRTH`; histórico anterior de métricas permanece no gráfico (não é zerado).

---

## 6. SEPARAÇÃO DE RESPONSABILIDADES

### 6.1 Estrutura de arquivos do projeto

```
sida-uns-client/
├── src/
│   ├── auth/            # Tela e lógica de login (usuário/senha, estado de sessão)
│   ├── mqtt/             # Conexão WebSocket, subscrição, reconexão com backoff
│   ├── sparkplug/         # Decodificação/codificação Protobuf Sparkplug B, resolução de alias
│   ├── state/             # device_tree, node_liveness, metric_history_buffer, alias_table (em memória)
│   ├── ui/                # Renderização da árvore de dispositivos e dos gráficos de série temporal
│   └── index.html / entrypoint estático
├── test/
│   └── casos de teste descritos na seção 5.3, executáveis contra um broker de teste local
├── Dockerfile
├── docker-compose.override.yml   # Adiciona o novo serviço à rede sida_network existente, sem tocar no compose atual
├── progress.json          # Log de progresso do loop (seção 3.4)
└── README.md
```

### 6.2 Responsabilidades por módulo

| Módulo | Faz | NÃO faz |
|---|---|---|
| `auth/` | Coleta credenciais, controla `auth_status`, aciona conexão MQTT | Não decide o que fazer com os dados recebidos; não persiste credenciais |
| `mqtt/` | Abre/mantém WebSocket, subscreve `spBv1.0/#`, entrega mensagens brutas ao módulo `sparkplug/` | Não decodifica Protobuf; não conhece a estrutura de UI |
| `sparkplug/` | Decodifica payload binário, resolve alias, classifica tipo de mensagem (NBIRTH/DBIRTH/DDATA/NDEATH/DDEATH) | Não escreve na tela; não guarda estado de longo prazo — apenas retorna estrutura decodificada |
| `state/` | Mantém `device_tree`, `node_liveness`, `metric_history_buffer`, `alias_table` em memória; aplica as regras da seção 5.2 | Não faz I/O de rede; não renderiza nada |
| `ui/` | Lê o estado em memória e desenha árvore + gráficos; reage a mudanças de `connection_status`/`auth_status` | Não decodifica payload; não gerencia conexão MQTT diretamente |
| `Dockerfile` / `docker-compose.override.yml` | Empacota a aplicação estática e um servidor HTTP leve; adiciona o serviço à rede `sida_network` | Não altera nenhum outro serviço do `docker-compose.yml` original do SIDA |

---

## 7. CASOS EXTREMOS

1. **Broker sem listener WebSocket disponível na URL configurada** — a aplicação deve exibir erro claro na tela de login ("não foi possível conectar ao endereço configurado") e não deve tentar adivinhar outra porta/protocolo.
2. **DDATA referenciando alias não resolvido** — descartar a métrica pontual sem quebrar a renderização das demais (caso 3 da seção 5.3).
3. **Mensagens fora de ordem** (ex.: `DDATA` chega antes do `DBIRTH` correspondente, mas depois do `NBIRTH` do nó) — tratar como métrica "órfã": manter em buffer temporário local até que o `DBIRTH` chegue, com timeout curto após o qual é descartada.
4. **Volume alto de métricas/dispositivos** — o buffer de histórico em memória por métrica deve ter um tamanho máximo configurável (ex.: últimos N pontos), descartando os mais antigos primeiro (estrutura tipo fila circular), para não estourar a memória do navegador em sessões longas.
5. **Múltiplas abas/sessões do mesmo usuário** — cada aba mantém seu próprio estado em memória e sua própria conexão MQTT; não há sincronização entre abas (consequência direta da fronteira de não persistir nada em disco/localStorage).
6. **Reconexão perde mensagens intermediárias** — ao reconectar, a aplicação deve assumir que perdeu mensagens durante a queda e não deve inferir estado; deve aguardar novos `NBIRTH`/`DBIRTH`/`DDATA` para reconstruir o que for necessário, sem travar a UI enquanto isso.
7. **NDEATH de um nó que nunca teve NBIRTH visto por este client** (client conectou depois do nó já estar de pé) — tratar sem erro: se não há registro do nó, o `NDEATH` é ignorado silenciosamente (não há estado prévio para marcar como offline).

---

## 8. STACK TÉCNICA

- **Linguagem/runtime de build e testes:** Python 3.10 ou superior (para os scripts de teste de aceite que publicam mensagens Sparkplug B de simulação contra o broker de teste).
- **Front-end:** JavaScript vanilla (sem framework de UI). Biblioteca de conexão: `mqtt.js` (MQTT sobre WebSocket). Biblioteca de decodificação: qualquer implementação JS compatível com o schema Protobuf Sparkplug B da Eclipse Foundation (mesmo contrato descrito no Anexo C do Tech Report v2.0).
- **Empacotamento:** Docker, com servidor HTTP estático leve servindo os arquivos da pasta `src/`.
- **Orquestração:** o novo serviço deve ser adicionável à rede `sida_network` já existente via um arquivo de override do `docker-compose`, sem editar o `docker-compose.yml` original.
- **Restrições de dependências:** nenhuma dependência de backend adicional (sem banco de dados, sem servidor de aplicação com estado); o container deve ser stateless entre reinicializações, exceto pelo arquivo `progress.json` do loop de desenvolvimento (que não faz parte do artefato de produção).

---

## 9. PROMPT PRONTO PARA O LOOP

```
Você vai implementar o SIDA UNS Web Client seguindo este SDD.

OBJETIVO: Construir um cliente MQTT web (JavaScript vanilla + mqtt.js), empacotado em
Docker, que exige login usuário/senha, conecta via WebSocket a um broker MQTT/Sparkplug B
existente (endereço configurável via variável de ambiente BROKER_WS_URL), decodifica
nativamente o payload binário Sparkplug B, descobre automaticamente a hierarquia
Grupo/Nó/Dispositivo a partir dos tópicos spBv1.0/#, mantém um buffer em memória do
histórico recente de cada métrica, e renderiza um dashboard com gráficos de série
temporal atualizados em tempo real. Nada é persistido em disco, localStorage ou
sessionStorage — nem credenciais, nem histórico.

FRONTEIRAS:
- Não altere nenhum arquivo dos serviços sida-core, sida-poc-ingestion, sida-poc-context
  ou sida-poc-delivery, nem o docker-compose.yml original. Adicione o novo serviço via
  arquivo de override.
- Não reconfigure o broker Mosquitto. Assuma que o listener WebSocket já existe no
  endereço fornecido; se a conexão falhar, reporte o erro — não tente contornar.
- Não use frameworks de UI (React/Vue/Angular). Apenas JS vanilla + mqtt.js + uma lib de
  decodificação Protobuf Sparkplug B.
- Não persista credenciais nem histórico de métricas em nenhum armazenamento que
  sobreviva ao fechamento da aba.

MÉTRICA DE CONCLUSÃO: O loop termina quando o teste de aceite da seção 3.1 deste SDD
passa integralmente (NBIRTH→DBIRTH→DDATA exibidos corretamente, atualização incremental
de DDATA, sinalização de NDEATH sem apagar histórico). Em cada falha: leia o erro,
identifique a causa, corrija, repita. Máximo de 5 tentativas por task antes de parar e
escalar para o humano, registrando a causa suspeita em progress.json.

PROCESSO: Siga a divisão em sprints S1-S4 da seção 3.3. Antes de começar, leia
progress.json e retome da última task não concluída. Atualize progress.json
imediatamente após cada task concluída, com status, timestamp e (se bloqueada) motivo
e número de tentativas.

Consulte as seções 4 a 8 deste SDD para o contrato de estado, as regras de negócio com
os casos de teste, a estrutura de arquivos e a stack técnica obrigatória.
```

---

## Histórico de decisões deste SDD

| # | Decisão | Origem |
|---|---|---|
| 1 | Entrega obrigatória em container Docker | Confirmado pelo usuário |
| 2 | Entrega/verificação: SPA estática + servidor leve, verificação via teste automatizado contra broker local | Decidido pela IA (não havia preferência explícita) |
| 3 | Stack: JS vanilla + mqtt.js, sem framework pesado | Confirmado pelo usuário |
| 4 | Nenhuma alteração em sida-core, Node-RED ou Mosquitto | Confirmado pelo usuário |
| 5 | Decodificação Sparkplug B binária nativa no browser | Confirmado pelo usuário |
| 6 | Teste de aceite via injeção NBIRTH→DBIRTH→DDATA em broker local | Confirmado pelo usuário |
| 7 | Máximo de 5 tentativas antes de escalar | Decidido pela IA (mantida a sugestão original) |
| 8 | Casos extremos: reconexão, alias não resolvido, NDEATH/DDEATH, payload corrompido | Confirmado pelo usuário |
| 9 | Auto-discovery via subscrição wildcard `spBv1.0/#` | Confirmado pelo usuário |
| 10 | Visualização: gráficos de série temporal | Confirmado pelo usuário (rodada 2) |
| 11 | Autenticação: tela de login com usuário/senha | Confirmado pelo usuário (rodada 2) |
| 12 | Histórico: buffer em memória para tendência recente | Confirmado pelo usuário (rodada 2) |
