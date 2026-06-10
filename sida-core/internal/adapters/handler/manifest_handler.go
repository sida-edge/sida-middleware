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

func (h *ManifestHandler) RemoveArea(c *gin.Context) {
	areaID := c.Param("id")

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

	if manifest.Config.Plant.Areas == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há áreas para remover",
		})
		return
	}

	if _, exists := manifest.Config.Plant.Areas[areaID]; !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Área '" + areaID + "' não encontrada",
		})
		return
	}

	delete(manifest.Config.Plant.Areas, areaID)
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
		"status": "success",
		"message": "Área '" + areaID + "' removida com sucesso",
	})
}

func (h *ManifestHandler) RemoveLine(c *gin.Context) {
	areaID := c.Param("area")
	lineID := c.Param("id")
	
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
	
	if manifest.Config.Plant.Areas == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há áreas para remover linhas",
		})
		return
	}
	
	area, areaExists := manifest.Config.Plant.Areas[areaID]
	if !areaExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Área '" + areaID + "' não encontrada",
		})
		return
	}

	if _, lineExists := area.Lines[lineID]; !lineExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Linha '" + lineID + "' não encontrada na área '" + areaID + "'",
		})
		return
	}
	
	delete(area.Lines, lineID)
	manifest.Config.Plant.Areas[areaID] = area
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
		"status": "success",
		"message": "Linha '" + lineID + "' removida com sucesso da área '" + areaID + "'",
	})
}

func (h *ManifestHandler) RemoveDevice(c *gin.Context) {
	areaID := c.Param("area")
	lineID := c.Param("line")
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

	if manifest.Config.Plant.Areas == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há áreas para remover equipamentos",
		})
		return
	}

	area, areaExists := manifest.Config.Plant.Areas[areaID]
	if !areaExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Área '" + areaID + "' não encontrada",
		})
		return
	}
	
	line, lineExists := area.Lines[lineID]
	if !lineExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Linha '" + lineID + "' não encontrada na área '" + areaID + "'",
		})
		return
	}
	
	if _, deviceExists := line.Devices[deviceID]; !deviceExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Equipamento '" + deviceID + "' não encontrado na linha '" + lineID + "' da área '" + areaID + "'",
		})
		return
	}

	delete(line.Devices, deviceID)
	area.Lines[lineID] = line
	manifest.Config.Plant.Areas[areaID] = area
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
		"status": "success",
		"message": "Equipamento '" + deviceID + "' removido com sucesso da linha '" + lineID + "' da área '" + areaID + "'",
	})
}

func (h *ManifestHandler) ToggleDeviceStatus(c *gin.Context) {
	areaID := c.Param("area")
	lineID := c.Param("line")
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

	if manifest.Config.Plant.Areas == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "O manifesto está vazio, não há áreas para atualizar equipamentos",
		})
		return
	}

	area, areaExists := manifest.Config.Plant.Areas[areaID]
	if !areaExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Área '" + areaID + "' não encontrada",
		})
		return
	}
	
	line, lineExists := area.Lines[lineID]
	if !lineExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Linha '" + lineID + "' não encontrada na área '" + areaID + "'",
		})
		return
	}
	
	device, deviceExists := line.Devices[deviceID]
	if !deviceExists {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Equipamento '" + deviceID + "' não encontrado na linha '" + lineID + "' da área '" + areaID + "'",
		})
		return
	}

	device.Enabled = *payload.Enabled
	line.Devices[deviceID] = device
	area.Lines[lineID] = line
	manifest.Config.Plant.Areas[areaID] = area
	manifest.UpdatedAt = time.Now()

	if err := h.repo.Save(c.Request.Context(), *manifest); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao atualizar o status no banco",
			"details": err.Error(),
		})
		return
	}

	_ = h.zmq.PublishUpdate(manifest.GatewayID)

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"message": "Status do equipamento '" + deviceID + "' atualizado para " + strconv.FormatBool(device.Enabled),
	})
}