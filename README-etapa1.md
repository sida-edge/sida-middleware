# SIDA — Etapa 1 do Ciclo V3.0: frota descentralizada e resiliente

Guia operacional para subir a frota e rodar os testes. O plano completo está em
[`SDD_SIDA_Etapa1_Ciclo_V3.md`](SDD_SIDA_Etapa1_Ciclo_V3.md); o avanço por task
em [`progress.json`](progress.json).

## O que a Etapa 1 entrega

- **Plano norte (A)** — delta de conformidade do ciclo de vida Sparkplug B em
  `core/delivery/flows.json` (`bdSeq` de sessão, aliases, `NDEATH` gracioso).
- **Plano leste-oeste (B)** — malha *controller-to-controller* ZeroMQ entre os
  `sida-core` (`PEER_PORT`, default `5557`), com registro de pares, *probes* e
  `GET /api/system/peers`.
- **Frota** — `docker-compose.yml` parametrizado por `.env`; a mesma pilha sobe
  em qualquer nó trocando só o `--env-file`.
- **Aceite** — injeção de falha (PoC 5): derrubar um nó e comprovar que os
  sobreviventes seguem publicando, nos dois planos, sem perda.

## Identidade da frota

Cada nó recebe a identidade **exclusivamente** por `.env` (nada hardcoded):

```bash
docker compose --env-file deploy/fleet/edge_001.env up -d --build
```

Variáveis em [`.env.example`](.env.example); tabela dos 3 nós em
[`deploy/fleet/identities.md`](deploy/fleet/identities.md).

## Frota local de teste (isolada)

`test/etapa1/compose.test.yml` sobe 3 nós completos + um **Mosquitto local**
(porta host `18831`) + um simulador Modbus TCP público (`oitc/modbus-server`,
registradores em `test/etapa1/modbus.test.json`) — **sem** relação com o broker
de produção. Cada nó fica numa rede própria (`edgeN_net`, alias `sida-core`) e
os `*-core` compartilham `mesh_net` para o peer-mesh.

```bash
# semear o sida_config.db de cada nó (plant + device Modbus + receiver mqtt)
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge1 --gateway-id sida_edge_001
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge2 --gateway-id sida_edge_002
python3 test/etapa1/seed_node_config.py --data-dir test/etapa1/_data/edge3 --gateway-id sida_edge_003

docker compose -f test/etapa1/compose.test.yml up -d --build
```

## Testes

```bash
python3 -m venv test/etapa1/.venv && . test/etapa1/.venv/bin/activate
pip install -r test/etapa1/requirements.txt

pytest test/etapa1                 # checkpoints leves (config, proto)
pytest test/etapa1 --run-heavy     # inclui os que sobem containers
```

Cada task tem um checkpoint funcional (SDD 3.3.1) que libera seu commit `[T…]`:

| Sprint | Task | Teste |
|---|---|---|
| S1 | `T0.4`  | `test_s1_foundation.py::test_baseline_v2_pipeline` *(heavy)* |
| S1 | `T1A.1` | `test_s1_foundation.py::test_sparkplug_proto_valido` |
| S1 | `T3.1`  | `test_s1_foundation.py::test_compose_parametrizado` |
| S2 | `T1A.2`–`T1A.7` | `test_plane_a_lifecycle.py` |
| S3 | `T1B.1`–`T1B.5` | `test_plane_b_peermesh.py` |
| S4 | `T3.2`–`T4.6`   | `test_fleet.py`, `test_fault_injection.py` |

## Ferramentas necessárias

`docker` + `docker compose` v2, `python3` (3.10+), e as libs de
`test/etapa1/requirements.txt`. Para o teste do `.proto` (`T1A.1`):
`protobuf-compiler` (`protoc`) **ou** `pip install grpcio-tools`.
