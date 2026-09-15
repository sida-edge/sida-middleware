package handler

import (
	"fmt"
	"net/http"
	"os"
	"time"
	"encoding/json"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"sida-core/internal/core/services"
	"sida-core/internal/core/domain"
)

type SystemHandler struct{
	zmq *services.ZMQService
}


func NewSystemHandler(zmq *services.ZMQService) *SystemHandler {
	return &SystemHandler{
		zmq: zmq,
	}
}

type ProvisionPayload struct {
	GatewayID string `json:"gateway_id" binding:"required"`
	PIN       string `json:"pin" binding:"required"`
}

func (h *SystemHandler) SetupEdgeGateway(c *gin.Context) {
	var payload ProvisionPayload

	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Dados inválidos.",
		})
		return
	}

	envPath := "/app/data/.env"
	envContent := fmt.Sprintf("EDGE_GATEWAY_ID=%s\nEDGE_ENGINEER_PIN=%s\n", payload.GatewayID, payload.PIN)

	err := os.WriteFile(envPath, []byte(envContent), 0644)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Falha ao gravar identidade.",
		})
		return
	}

	_ = godotenv.Load(envPath)

	c.JSON(http.StatusOK, gin.H{
		"message": "Edge provisionado!",
		"gateway_id": os.Getenv("EDGE_GATEWAY_ID"),
	})
}

func (h *SystemHandler) GetSystemInfo(c *gin.Context) {
	gatewayID := os.Getenv("EDGE_GATEWAY_ID")
	if gatewayID == "" {
		c.JSON(http.StatusOK, gin.H{
			"provisioned": false,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"provisioned": true,
		"gateway_id": gatewayID,
	})
}

func (h *SystemHandler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": 	"UP",
		"service":  "sida-core",
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

func (h *SystemHandler) GetTelemetry(c *gin.Context) {
	payload, err := h.zmq.ReceiveUpdate()
	if err != nil {
		if payload == "timeout" {
			c.JSON(http.StatusOK, gin.H{
				"message": "Nenhuma telemetria disponível no momento.",
			})
			return
		} else if payload == "failed" {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Falha ao receber telemetria.",
				"details": err.Error(),
			})
			return
		} else if payload == "error" {
			fmt.Printf("Erro ao receber telemetria: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Erro ao receber telemetria.",
				"details": err.Error(),
			})
			return
		}
		fmt.Printf("Erro ao receber telemetria: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao receber telemetria.",
			"details": err.Error(),
		})
		return
	}

	if payload == "" {
		c.JSON(http.StatusOK, gin.H{
			"message": "Nenhuma telemetria disponível no momento.",
		})
		return
	}
	
	var telemetry domain.Telemetry
	err = json.Unmarshal([]byte(payload), &telemetry)
	if err != nil {
		fmt.Printf("Erro ao processar telemetria: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Erro ao processar telemetria.",
			"details": err.Error(),
		})
		return
	}

	fmt.Printf("Telemetria recebida: %v", telemetry)
	c.JSON(http.StatusOK, telemetry)
}