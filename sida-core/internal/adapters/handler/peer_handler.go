package handler

import (
	"net/http"
	"os"

	"github.com/gin-gonic/gin"

	"sida-core/internal/core/services"
)

// PeerHandler expõe o estado da malha leste-oeste (plano B). Os hooks de teste
// ficam atrás de PEER_MESH_TEST=1 (só a frota de teste os liga).
type PeerHandler struct {
	svc *services.PeerService
}

func NewPeerHandler(svc *services.PeerService) *PeerHandler {
	return &PeerHandler{svc: svc}
}

// GetPeers — GET /api/system/peers: registro + liveness local (a FSM é do T1B.4).
func (h *PeerHandler) GetPeers(c *gin.Context) {
	if h.svc == nil {
		c.JSON(http.StatusOK, gin.H{"controller_id": "", "peers": []any{}})
		return
	}
	id, peers := h.svc.Snapshot()
	c.JSON(http.StatusOK, gin.H{"controller_id": id, "peers": peers})
}

func (h *PeerHandler) testEnabled() bool {
	return h.svc != nil && os.Getenv("PEER_MESH_TEST") == "1"
}

// TestSend — POST /api/system/peers/test/send {"peer":"...","payload":"..."}
func (h *PeerHandler) TestSend(c *gin.Context) {
	if !h.testEnabled() {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	var body struct {
		Peer    string `json:"peer" binding:"required"`
		Payload string `json:"payload"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.svc.WriteMessage(body.Peer, []byte(body.Payload)); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusAccepted, gin.H{"sent": true})
}

// TestInbox — GET /api/system/peers/test/inbox: drena o MessageBuffer.
func (h *PeerHandler) TestInbox(c *gin.Context) {
	if !h.testEnabled() {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	msgs := h.svc.ReadMessage()
	out := make([]string, 0, len(msgs))
	for _, m := range msgs {
		out = append(out, string(m))
	}
	c.JSON(http.StatusOK, gin.H{"messages": out})
}
