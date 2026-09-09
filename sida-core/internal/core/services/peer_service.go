package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"strings"
	"sync"
	"time"

	"github.com/pebbe/zmq4"

	"sida-core/internal/core/domain"
)

func init() {
	// Mais de uma thread de I/O do ZeroMQ: assim, um DEALER preso num
	// getaddrinfo lento (par fora do ar, DNS falhando ~5s) não congela o
	// ROUTER nem os DEALERs dos outros pares. Precisa rodar antes de
	// qualquer socket ser criado.
	_ = zmq4.SetIoThreads(4)
}

// resolvePeerEndpoint troca o host de um endpoint "tcp://host:port" pelo IP
// resolvido em Go (com timeout curto), para o libzmq nunca fazer DNS
// bloqueante. Se não resolver, devolve o endpoint original.
func resolvePeerEndpoint(ep string) string {
	const pfx = "tcp://"
	if !strings.HasPrefix(ep, pfx) {
		return ep
	}
	hostPort := ep[len(pfx):]
	i := strings.LastIndex(hostPort, ":")
	if i <= 0 {
		return ep
	}
	host, port := hostPort[:i], hostPort[i+1:]
	if net.ParseIP(host) != nil {
		return ep
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	ips, err := net.DefaultResolver.LookupHost(ctx, host)
	if err != nil || len(ips) == 0 {
		return ep
	}
	return pfx + ips[0] + ":" + port
}

// Tipos de frame trocados na malha leste-oeste (plano B / InterEdge).
const (
	frameProbe    = "PROBE"
	frameProbeAck = "PROBE_ACK"
	frameMsg      = "MSG"
)

type outFrame struct {
	peerID string
	parts  []string
}

// peerLiveness — estado de liveness de um par (FSM alimentada pelo probe loop, T1B.4).
type peerLiveness struct {
	State      domain.LivenessState
	Missed     int
	LastAckAgo time.Time // relógio monotônico local
}

// PeerService implementa a malha controller-to-controller do InterEdge sobre
// ZeroMQ: um ROUTER escutando em PEER_PORT e um DEALER por par. Um único
// goroutine (run) é dono de todos os sockets; o resto do processo fala com ele
// por canais / estado protegido por mutex.
type PeerService struct {
	self     string
	bindAddr string
	peers    []domain.PeerRef

	router  *zmq4.Socket
	dealers map[string]*zmq4.Socket

	outbox chan outFrame
	stop   chan struct{}
	done   chan struct{}

	mu       sync.Mutex
	buffer   map[string][][]byte // MessageBuffer: seção dedicada por remetente
	liveness map[string]*peerLiveness

	probeIntervalMs     int
	peerDownAfterMisses int
}

// NewPeerService cria (sem iniciar) o serviço de malha a partir do Controller
// Register do nó. Chame Start para subir os sockets e os loops.
func NewPeerService(reg domain.ControllerRegister, peerPort string) *PeerService {
	s := &PeerService{
		self:                reg.ControllerID,
		bindAddr:            "tcp://0.0.0.0:" + peerPort,
		peers:               reg.ConnectedControllers,
		dealers:             make(map[string]*zmq4.Socket),
		outbox:              make(chan outFrame, 256),
		stop:                make(chan struct{}),
		done:                make(chan struct{}),
		buffer:              make(map[string][][]byte),
		liveness:            make(map[string]*peerLiveness),
		probeIntervalMs:     reg.ProbeIntervalMs,
		peerDownAfterMisses: reg.PeerDownAfterMisses,
	}
	for _, p := range s.peers {
		s.liveness[p.ID] = &peerLiveness{State: domain.PeerDown}
	}
	return s
}

// Start faz o bind do ROUTER, conecta um DEALER por par e sobe os loops
// (recepção + probe). Distinto do PUB de manifesto em :5556.
func (s *PeerService) Start() error {
	router, err := zmq4.NewSocket(zmq4.ROUTER)
	if err != nil {
		return err
	}
	if err := router.SetIdentity(s.self); err != nil {
		return err
	}
	if err := router.Bind(s.bindAddr); err != nil {
		return fmt.Errorf("bind ROUTER em %s: %w", s.bindAddr, err)
	}
	s.router = router

	for _, p := range s.peers {
		d, err := zmq4.NewSocket(zmq4.DEALER)
		if err != nil {
			return err
		}
		if err := d.SetIdentity(s.self); err != nil {
			return err
		}
		// HWM baixo: um par fora do ar não deve acumular um backlog gigante
		// que despeja tudo de uma vez quando ele voltar.
		_ = d.SetSndhwm(16)
		_ = d.SetLinger(0)
		// Connect é assíncrono/lazy no ZeroMQ: um par ainda fora do ar não é
		// erro — o socket reconecta sozinho quando ele subir. Resolvemos o
		// host para IP aqui para o libzmq não fazer DNS bloqueante depois.
		endpoint := resolvePeerEndpoint(p.Endpoint)
		if err := d.Connect(endpoint); err != nil {
			log.Printf("peer-mesh: connect DEALER -> %s (%s) adiado: %v", p.ID, endpoint, err)
		}
		s.dealers[p.ID] = d
	}

	log.Printf("peer-mesh: ROUTER em %s, %d DEALER(s) para pares", s.bindAddr, len(s.dealers))

	go s.run()
	go s.probeLoop()
	return nil
}

// Stop encerra os loops e fecha os sockets. Idempotente e com teto de tempo:
// nunca segura o shutdown do processo além de ~3s.
func (s *PeerService) Stop() {
	select {
	case <-s.stop:
	default:
		close(s.stop)
	}
	select {
	case <-s.done:
	case <-time.After(3 * time.Second):
		log.Println("peer-mesh: Stop() excedeu 3s; seguindo com o encerramento")
	}
}

func (s *PeerService) run() {
	defer close(s.done)

	poller := zmq4.NewPoller()
	poller.Add(s.router, zmq4.POLLIN)

	for {
		select {
		case <-s.stop:
			s.closeSockets()
			return
		default:
		}

		// Drena todo o outbox pendente (envios não-bloqueantes).
		draining := true
		for draining {
			select {
			case out := <-s.outbox:
				s.sendVia(out)
			default:
				draining = false
			}
		}

		sockets, err := poller.Poll(100 * time.Millisecond)
		if err != nil {
			// Poll é interrompido no shutdown; o select acima trata o stop.
			continue
		}
		for range sockets {
			for {
				frames, err := s.router.RecvMessage(zmq4.DONTWAIT)
				if err != nil {
					break // EAGAIN: fila do ROUTER vazia
				}
				if len(frames) >= 3 {
					s.handle(frames[0], frames[1], frames[2])
				}
			}
		}
	}
}

func (s *PeerService) sendVia(out outFrame) {
	d, ok := s.dealers[out.peerID]
	if !ok {
		log.Printf("peer-mesh: sem DEALER para %q, descartando frame %s", out.peerID, out.parts[0])
		return
	}
	// DONTWAIT: um par fora do ar (DEALER sem conexão) faria o SendMessage
	// bloquear e travar o único goroutine da malha. EAGAIN -> descarta o
	// frame. PROBE se recupera sozinho; MSG de dados não tem failover nesta
	// etapa (T1B.6, opcional).
	if _, err := d.SendMessageDontwait(out.parts); err != nil {
		log.Printf("peer-mesh: frame %s para %q descartado (%v)", out.parts[0], out.peerID, err)
	}
}

func (s *PeerService) handle(from, mtype, body string) {
	switch mtype {
	case frameProbe:
		s.enqueue(from, frameProbeAck, body)
		s.markAlive(from)
	case frameProbeAck:
		s.markAlive(from)
	case frameMsg:
		var env domain.Envelope
		if err := json.Unmarshal([]byte(body), &env); err != nil {
			log.Printf("peer-mesh: MSG malformada de %q: %v", from, err)
			return
		}
		s.route(env, from)
	}
}

// route implementa RouteMessage: lê o próximo ControllerID do Path; se for o
// próprio, entrega local (MessageBuffer); senão, encaminha ao próximo salto.
func (s *PeerService) route(env domain.Envelope, from string) {
	if len(env.Path) == 0 || env.Path[0] == s.self {
		s.mu.Lock()
		s.buffer[from] = append(s.buffer[from], env.Payload)
		s.mu.Unlock()
		return
	}
	next := env.Path[0]
	env.Path = env.Path[1:]
	b, _ := json.Marshal(env)
	s.enqueue(next, frameMsg, string(b))
}

func (s *PeerService) enqueue(peerID, mtype, body string) {
	select {
	case s.outbox <- outFrame{peerID: peerID, parts: []string{mtype, body}}:
	default:
		log.Printf("peer-mesh: outbox cheia, descartando %s para %q", mtype, peerID)
	}
}

// WriteMessage monta o Envelope (Path = rota até dst) e o injeta na malha.
// Etapa 1: pares diretos -> Path = [dst].
func (s *PeerService) WriteMessage(dst string, payload []byte) error {
	if _, ok := s.dealers[dst]; !ok {
		return fmt.Errorf("destino %q não é um par conhecido", dst)
	}
	env := domain.Envelope{Path: []string{dst}, Payload: payload, TS: time.Now().UnixMilli()}
	b, _ := json.Marshal(env)
	s.enqueue(dst, frameMsg, string(b))
	return nil
}

// ReadMessage drena o MessageBuffer (todas as seções por remetente).
func (s *PeerService) ReadMessage() [][]byte {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out [][]byte
	for sender, msgs := range s.buffer {
		out = append(out, msgs...)
		delete(s.buffer, sender)
	}
	return out
}

func (s *PeerService) closeSockets() {
	if s.router != nil {
		_ = s.router.Close()
	}
	for _, d := range s.dealers {
		_ = d.Close()
	}
}

// probeLoop envia um PROBE a cada par no ProbeInterval e, a cada tick, reavalia
// a FSM de liveness (SDD 5.2.2): alive -> suspect após 1 intervalo sem ACK ->
// down após PEER_DOWN_AFTER_MISSES intervalos sem ACK. Qualquer PROBE_ACK
// devolve o par a alive. Medição em relógio monotônico local (time.Since).
func (s *PeerService) probeLoop() {
	interval := time.Duration(s.probeIntervalMs) * time.Millisecond
	if interval <= 0 {
		interval = time.Second
	}
	misses := s.peerDownAfterMisses
	if misses <= 0 {
		misses = 3
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-s.stop:
			return
		case <-ticker.C:
			s.evaluateLiveness(interval, misses)
			ping := fmt.Sprintf(`{"from":%q,"ts":%d}`, s.self, time.Now().UnixMilli())
			for _, p := range s.peers {
				s.enqueue(p.ID, frameProbe, ping)
			}
		}
	}
}

// evaluateLiveness recomputa o estado de cada par a partir de quanto tempo
// (em intervalos) faz desde o último ACK. Sem ACK ainda => down.
func (s *PeerService) evaluateLiveness(interval time.Duration, downAfterMisses int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	for _, p := range s.peers {
		lv := s.liveness[p.ID]
		if lv == nil {
			lv = &peerLiveness{State: domain.PeerDown}
			s.liveness[p.ID] = lv
		}

		if lv.LastAckAgo.IsZero() {
			lv.Missed = downAfterMisses
			lv.State = domain.PeerDown
			continue
		}

		// Meio-intervalo de folga absorve jitter de RTT: só conta como
		// "perdido" o silêncio que passa de 1.5, 2.5, ... intervalos.
		missed := int((time.Since(lv.LastAckAgo) - interval/2) / interval)
		if missed < 0 {
			missed = 0
		}
		lv.Missed = missed
		switch {
		case missed <= 0:
			lv.State = domain.PeerAlive
		case missed >= downAfterMisses:
			lv.State = domain.PeerDown
		default:
			lv.State = domain.PeerSuspect
		}
	}
}

func (s *PeerService) markAlive(peerID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	lv, ok := s.liveness[peerID]
	if !ok {
		lv = &peerLiveness{}
		s.liveness[peerID] = lv
	}
	lv.State = domain.PeerAlive
	lv.Missed = 0
	lv.LastAckAgo = time.Now()
}

// PeerStatus é a visão externa (handler /api/system/peers) do liveness local.
type PeerStatus struct {
	ID        string `json:"id"`
	Endpoint  string `json:"endpoint"`
	State     string `json:"state"`
	LastAckMs int64  `json:"last_ack_ms"`
	Missed    int    `json:"missed"`
}

// Snapshot devolve o registro + o liveness local de cada par.
func (s *PeerService) Snapshot() (string, []PeerStatus) {
	s.mu.Lock()
	defer s.mu.Unlock()

	out := make([]PeerStatus, 0, len(s.peers))
	for _, p := range s.peers {
		st := PeerStatus{ID: p.ID, Endpoint: p.Endpoint, State: string(domain.PeerDown)}
		if lv, ok := s.liveness[p.ID]; ok {
			st.State = string(lv.State)
			st.Missed = lv.Missed
			if !lv.LastAckAgo.IsZero() {
				st.LastAckMs = time.Since(lv.LastAckAgo).Milliseconds()
			}
		}
		out = append(out, st)
	}
	return s.self, out
}
