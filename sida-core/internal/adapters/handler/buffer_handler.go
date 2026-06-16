package handler

import (
	"context"
	"encoding/json"
	"io"
	"net/http"

	"sida-core/internal/core/ports"

	"github.com/gin-gonic/gin"
)

type BufferHandler struct {
	repo ports.BufferRepository
}

func NewBufferHandler(repo ports.BufferRepository) *BufferHandler {
	return &BufferHandler{
		repo: repo,
	}
}

func (h *BufferHandler) IngestBuffer(c *gin.Context) {
	payload, err := io.ReadAll(c.Request.Body)
	if err != nil || len(payload) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Payload de buffer inválido ou vazio",
			"details": err.Error(),
		})
		return
	}

	if err := h.repo.Save(c.Request.Context(), payload); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao salvar no buffer",
			"details": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success", 
		"message": "Payload recebido e armazenado no buffer",
	})
}

func (h *BufferHandler) FlushBuffer(c *gin.Context) {
	records, err := h.repo.Flush(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao flush do buffer",
			"details": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success", 
		"data": records,
	})
}