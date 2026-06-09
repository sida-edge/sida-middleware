package handler

import (
	"net/http"
	"time"
	"os"

	"sida-core/internal/core/domain"
	"sida-core/internal/core/ports"
	"sida-core/internal/core/services"

	"github.com/gin-gonic/gin"
)

type ManifestHandler struct {
	repo ports.ManifestRepository
	zmq  *services.ZMQPublisher
}

func NewManifestHandler(repo ports.ManifestRepository, zmq *services.ZMQPublisher) *ManifestHandler {
	return &ManifestHandler{
		repo: repo,
		zmq:  zmq,
	}
}

func (h *ManifestHandler) UploadManifest(c *gin.Context) {
	var payload domain.Manifest

	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Payload de configuração inválido",
			"details": err.Error(),
		})
		return
	}

	manifest := domain.Manifest{
		GatewayID: payload.GatewayID,
		Config:    payload.Config,
		UpdatedAt: time.Now(),
	}

	if err := h.repo.Save(c.Request.Context(), manifest); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao salvar no banco",
			"details": err.Error(),
		})
		return
	}

	_ = h.zmq.PublishUpdate(manifest.GatewayID)

	c.JSON(http.StatusOK, gin.H{
		"status": "success", 
		"message": "Manifesto atualizado para " + payload.GatewayID,
	})
}


func (h *ManifestHandler) GetManifest(c *gin.Context) {
	gatewayID := c.Query("gateway_id")
	if gatewayID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "O parâmetro gateway_id é obrigatório",
		})
		return
	}

	manifest, err := h.repo.GetByID(c.Request.Context(), gatewayID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro interno no banco de dados",
			"details": err.Error(),
		})
		return
	}

	if manifest == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Nenhum manifesto encontrado para este gateway",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"gateway_id": manifest.GatewayID,
		"config":     manifest.Config,
	})
}

func (h *ManifestHandler) RemoveDevice(c *gin.Context) {
	deviceID := c.Param("id")

	gatewayID := os.Getenv("EDGE_GATEWAY_ID")
	if gatewayID == "" {
		gatewayID = "sida_edge_001"
	}

	manifest, err := h.repo.GetByID(c.Request.Context(), gatewayID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao ler o manifesto atual do banco",
			"details": err.Error(),
		})
		return
	}

	if manifest.Config.Devices == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há equipamentos para remover",
		})
		return
	}

	if _, exists := manifest.Config.Devices[deviceID]; !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Equipamento '" + deviceID + "' não encontrado",
		})
		return
	}

	delete(manifest.Config.Devices, deviceID)
	manifest.UpdatedAt = time.Now()

	if err := h.repo.Save(c.Request.Context(), *manifest); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao persistir a exclusão no banco",
			"details": err.Error(),
		})
		return
	}

	_ = h.zmq.PublishUpdate(manifest.GatewayID)

	c.JSON(http.StatusOK, gin.H{
		"status": "sucess",
		"message": "Equipamento '" + deviceID + "' removido com sucesso",
	})
}

func (h *ManifestHandler) ToggleDeviceStatus(c *gin.Context) {
	deviceID := c.Param("id")

	var payload struct {
		Enabled *bool `json:"enabled" binding:"required"`
	}

	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Payload inválido. Envie {'enabled': true/false}",
			"details": err.Error(),
		})
		return
	}

	gatewayID := os.Getenv("EDGE_GATEWAY_ID")
	if gatewayID == "" {
		gatewayID = "sida_edge_001"
	}

	manifest, err := h.repo.GetByID(c.Request.Context(), gatewayID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao ler o manifesto",
		})
		return
	}

	if manifest.Config.Devices == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há equipamentos para remover",
		})
		return
	}

	device, exists := manifest.Config.Devices[deviceID]
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Equipamento '" + deviceID + "' não encontrado",
		})
		return
	}

	device.Enabled = *payload.Enabled
	manifest.Config.Devices[deviceID] = device

	manifest.UpdatedAt = time.Now()

	if err := h.repo.Save(c.Request.Context(), *manifest); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao salvar alteração",
		})
		return
	}

	_ = h.zmq.PublishUpdate(manifest.GatewayID)

	statusStr := "disabled"
	if *payload.Enabled {
		statusStr = "enabled"
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "sucesso",
		"message": "Equipamento '" + deviceID + "' " + statusStr + " com sucesso",
	})
}