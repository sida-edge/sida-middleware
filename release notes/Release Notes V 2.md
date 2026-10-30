## **Ciclo de Prototipação e Validação de Arquitetura**

#### **Objetivo**

O desenvolvimento do SIDA (Semantic Industrial Data Agent) entra agora na versão 2.0, focada exclusivamente na validação técnica das três camadas fundamentais da arquitetura. O objetivo deste ciclo é utilizar estratégias de prototipação rápida para validar regras de negócio, latência, conectividade borda-nuvem e a correta aplicação da semântica industrial (ISA-95). O foco é garantir que o conceito arquitetural funciona de ponta a ponta, isolando riscos de integração precoce.

#### **Stack Tecnológica**

Para garantir agilidade extrema nesta etapa de validação, adotaremos as seguintes tecnologias:

| Tecnologia                           | Descrição                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Node-RED**                         | _Ferramenta central para orquestração visual dos fluxos de dados, execução da lógica de contextualização (via JavaScript) e testes rápidos de conectividade._ |
| **Docker / Docker Compose**          | _Infraestrutura de base para garantir que cada camada rode em um contêiner isolado, simulando fielmente um ambiente de microsserviços distribuídos._          |
| **Google Cloud Platform (GCP)**      | _Provedor da infraestrutura de nuvem._                                                                                                                        |
| **Eclipse Mosquitto**                | _Broker MQTT para validação da camada de delivery._                                                                                                           |
| **Protocolos Industriais e de Rede** | _Modbus (para simulação de chão de fábrica) e definição de barramento interno (a ser fechado entre ZeroMQ, MQTT Local ou HTTP REST)._                         |

#### Estrutura das Provas de Conceito (PoCs)

O desenvolvimento será fatiado em 4 entregáveis distintos e isolados. Cada PoC possui seu próprio ambiente de execução e valida um critério de sucesso específico.

| PoC                                                              | Descrição                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PoC 1 - Gateway de Aquisição Edge (Ingestão)**                 | **Foco:** Extração de dados brutos na borda.<br><br>**Ação:** Leitura contínua (polling) de um dispositivo simulador Modbus local.<br><br>**Valor:** Provar que o SIDA consegue manter uma conexão estável e realizar leituras em tempo real sem perda de pacotes, disponibilizando o dado bruto para a rede interna.                                                                                                        |
| **PoC 2 - Motor de Enriquecimento Semântico (Contextualização)** | **Foco:** Inteligência e transformação de dados.<br><br>**Ação:** Interceptar o payload bruto e aplicar a modelagem hierárquica baseada no padrão ISA-95.<br><br>**Valor:** Provar a capacidade de transformar dados isolados em informações com contexto de negócio, gerando automaticamente a taxonomia do _Unified Namespace_ (UNS).                                                                                      |
| **PoC 3 - Ponte de Telemetria Cloud (Entrega)**                  | **Foco:** Conectividade remota e segurança.<br><br>**Ação:** Estabelecer uma via de mão única segura e autenticada com o broker MQTT rodando em uma máquina virtual no GCP.<br><br>**Valor:** Validar latência, regras de firewall e garantir que os dados de borda conseguem penetrar as camadas de segurança corporativas até chegarem à nuvem.                                                                            |
| **PoC 4 - SIDA Core: Pipeline End-to-End (Integração)**          | **Foco:** Orquestração completa.<br><br>**Ação:** Unir os três contêineres anteriores em uma única rede Docker (Bridge). O fluxo de comunicação do sistema será validado em sua totalidade.<br><br>**Valor:** A arquitetura roda sem intervenção humana. O dado nasce no simulador (PoC 1), ganha contexto semântico (PoC 2) e deságua estruturado na nuvem (PoC 3) em tempo real, validando o desenho arquitetural do SIDA. |

#### Critérios de Aceite

Para que cada PoC seja considerada _"concluída"_ e validada para a integração final, ela deve obrigatoriamente cumprir os seguintes requisitos isolados:

PoC 1 - Gateway de Aquisição Edge (Ingestão)

- O contêiner do Node-RED deve subir via _docker-compose_ de forma isolada.
- O fluxo deve realizar a leitura de um dado (via simulador Modbus local) a uma taxa de pelo menos 10 Hz.
- O dado bruto deve ser exposto para fora do contêiner utilizando um protocolo de rede real, provando que microsserviços externos podem consumi-lo.

**Gatilho de Sucesso:** É possível conectar um cliente externo (script simples) na porta exposta e enxergar o JSON bruto chegando continuamente.

PoC 2 - Motor de Enriquecimento Semântico (Contextualização)

- O fluxo deve escutar uma porta de rede aguardando o payload bruto.
- O nó de transformação (Function) deve ler o _JSON_ bruto e injetar a estrutura ISA-95 (Empresa > Site > Área > Linha > Equipamento).
- O nó de transformação deve ser capaz de gerar dinamicamente o tópico de destino (Unified Namespace) com base na origem do dado.

**Gatilho de Sucesso:** Ao injetar manualmente um dado de teste na entrada, a saída de rede exibe o payload formatado e com o tópico correto para o UNS.

PoC 3 - Ponte de Telemetria Cloud (Entrega)

- O fluxo deve estabelecer conexão autenticada com o broker Mosquitto rodando na VM do Google Cloud Platform.
- O sistema deve ser capaz de lidar com credenciais (usuário/senha) de forma segura no nó MQTT Out.

**Gatilho de Sucesso:** Client externo assina o tópico remotamente e recebe um payload de teste disparado pelo Node-RED, validando as regras de firewall e a latência da nuvem.

PoC 4: SIDA Core (Fluxo Completo)

- Um único arquivo docker-compose.yml deve ser capaz de orquestrar os três contêineres simultaneamente na mesma rede virtual.

**Gatilho de Sucesso:** A arquitetura roda _end-to-end_. O dado nasce no simulador Modbus (PoC 1), ganha contexto ISA-95 (PoC 2) e bate na nuvem do GCP (PoC 3) em tempo real.

#### Cronograma

<div class="joplin-table-wrapper"><table><thead><tr><th><p>Etapa/Data</p></th><th><p>Descrição</p></th></tr></thead><tbody><tr><td><p><strong>Setup </strong>/ [20.05 - 22.05]</p></td><td><ul><li>Definilção de contratos.</li><li>Criação do repositorio base no GitHub.</li><li>Validação de setup local (Node-RED) e VM no Google Cloud Plataform.</li></ul></td></tr><tr><td><p>Desenvolvimento / [25.05 - 29.05]</p></td><td><ul><li>Trabalho em paralelo.</li><li>PoCs 1, 2 e 3 commitadas e 100% funcionais isoladas.</li></ul></td></tr><tr><td><p>Integração / [01.06 - 04.06]</p></td><td><ul><li>Conectar os contêineres e garantir a estabilidade do fluxo.</li><li>Debug (<em>timestamps, payloads, quedas</em>).</li><li>Teste de resistência (<em>run contínuo</em>) para estabilidade</li></ul></td></tr><tr><td><p><strong>Entrega do MVP SIDA v2.0</strong> / [05.06]</p></td><td></td></tr></tbody></table></div>
