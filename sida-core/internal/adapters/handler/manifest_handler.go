package handler

import (
	"net/http"
	"time"

	"sida-core/internal/core/domain"
	"sida-core/internal/core/ports"

	"github.com/gin-gonic/gin"
)

type ManifestHandler struct {
	repo ports.ManifestRepository
}

func NewManifestHandler(repo ports.ManifestRepository) *ManifestHandler {
	return &ManifestHandler{
		repo: repo,
	}
}

// Payload de entrada para o POST
type manifestRequest struct {
	GatewayID string                 `json:"gateway_id" binding:"required"`
	Config    map[string]interface{} `json:"config" binding:"required"`
}

// lida com a rota POST
func (h *ManifestHandler) UploadManifest(c *gin.Context) {
	var req manifestRequest

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Formato de JSON inválido: " + err.Error()})
		return
	}

	manifest := domain.Manifest{
		GatewayID: req.GatewayID,
		Config:    req.Config,
		UpdatedAt: time.Now(),
	}

	if err := h.repo.Save(c.Request.Context(), manifest); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Erro ao salvar no banco: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success", "message": "Manifesto atualizado para " + req.GatewayID})
}

// lida com a rota GET
func (h *ManifestHandler) GetManifest(c *gin.Context) {
	gatewayID := c.Query("gateway_id")
	if gatewayID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "O parâmetro gateway_id é obrigatório"})
		return
	}

	manifest, err := h.repo.GetByID(c.Request.Context(), gatewayID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Erro interno no banco de dados"})
		return
	}

	if manifest == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Nenhum manifesto encontrado para este gateway"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"gateway_id": manifest.GatewayID,
		"config":     manifest.Config,
	})
}