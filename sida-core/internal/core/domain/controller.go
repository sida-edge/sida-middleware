package domain

import (
	"fmt"
	"strings"
)

// LivenessState — estado da FSM de liveness de um par na malha leste-oeste
// (plano B / InterEdge). Transições: alive -> suspect (1 intervalo sem ACK) ->
// down (PeerDownAfterMisses intervalos sem ACK). Qualquer PROBE_ACK volta a alive.
type LivenessState string

const (
	PeerAlive   LivenessState = "alive"
	PeerSuspect LivenessState = "suspect"
	PeerDown    LivenessState = "down"
)

// PeerRef identifica um controlador par e onde alcançá-lo na malha ZeroMQ.
type PeerRef struct {
	ID       string `json:"id"`
	Endpoint string `json:"endpoint"` // tcp://host:port
}

// Envelope — unidade de mensagem do InterEdge: dados + caminho. O Path é a
// cadeia de ControllerIDs até o destino (o próximo salto é Path[0]).
type Envelope struct {
	Path    []string `json:"path"`
	Payload []byte   `json:"payload"`
	TS      int64    `json:"ts"`
}

// ControllerRegister espelha o Controller Register do InterEdge (Azad et al.),
// recortado ao que a coordenação de frota da Etapa 1 usa. Os campos de
// roteamento estático (SourceDevices/DestinationDevices/ConditionActions) são
// mantidos por fidelidade ao modelo, mas não são exercitados nesta etapa.
type ControllerRegister struct {
	ControllerID              string    `json:"controller_id"`
	ControllerName            string    `json:"controller_name"`
	ConnectedControllers      []PeerRef `json:"connected_controllers"`
	SourceDevices             []string  `json:"source_devices"`
	DestinationDevices        []string  `json:"destination_devices"`
	ConditionActions          []string  `json:"condition_actions"`
	ProbeIntervalMs           int       `json:"probe_interval_ms"`
	PeerDownAfterMisses       int       `json:"peer_down_after_misses"`
	ControllerProbeIntervalMs int       `json:"controller_probe_interval_ms"`
}

// ParsePeers converte a env PEERS ("id@host:port,id@host:port,...") em PeerRefs.
// String vazia (ou só espaços/vírgulas) -> nil, sem erro. Entrada malformada ou
// ControllerID de par duplicado -> erro (nunca falha em silêncio).
func ParsePeers(raw string) ([]PeerRef, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, nil
	}

	var peers []PeerRef
	seen := make(map[string]bool)

	for _, tok := range strings.Split(raw, ",") {
		tok = strings.TrimSpace(tok)
		if tok == "" {
			continue
		}

		at := strings.Index(tok, "@")
		if at <= 0 || at == len(tok)-1 {
			return nil, fmt.Errorf("par malformado %q: esperado id@host:port", tok)
		}

		id := tok[:at]
		hostPort := tok[at+1:]

		colon := strings.LastIndex(hostPort, ":")
		if colon <= 0 || colon == len(hostPort)-1 {
			return nil, fmt.Errorf("par %q sem host:port válido", tok)
		}

		if seen[id] {
			return nil, fmt.Errorf("ControllerID de par duplicado: %q", id)
		}
		seen[id] = true

		peers = append(peers, PeerRef{ID: id, Endpoint: "tcp://" + hostPort})
	}

	return peers, nil
}

// NewControllerRegisterFromEnv monta o registro do controlador a partir das
// envs de identidade do nó (CONTROLLER_ID, PEERS, PROBE_INTERVAL_MS,
// PEER_DOWN_AFTER_MISSES). PEERS malformado devolve erro.
func NewControllerRegisterFromEnv(controllerID, peersRaw string, probeIntervalMs, peerDownAfterMisses int) (ControllerRegister, error) {
	peers, err := ParsePeers(peersRaw)
	if err != nil {
		return ControllerRegister{}, err
	}
	if probeIntervalMs <= 0 {
		probeIntervalMs = 1000
	}
	if peerDownAfterMisses <= 0 {
		peerDownAfterMisses = 3
	}
	return ControllerRegister{
		ControllerID:              controllerID,
		ControllerName:            controllerID,
		ConnectedControllers:      peers,
		ProbeIntervalMs:           probeIntervalMs,
		PeerDownAfterMisses:       peerDownAfterMisses,
		ControllerProbeIntervalMs: probeIntervalMs,
	}, nil
}
