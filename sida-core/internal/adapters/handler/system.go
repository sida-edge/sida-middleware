package handler

import (
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

type ProvisionPayload struct {
	GatewayID string `json:"gateway_id" binding:"required"`
	PIN       string `json:"pin" binding:"required"`
}

func SetupEdgeGateway(c *gin.Context) {
	var payload ProvisionPayload

	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Dados inválidos."})
		return
	}

	envPath := "/app/data/.env"
	envContent := fmt.Sprintf("EDGE_GATEWAY_ID=%s\nEDGE_ENGINEER_PIN=%s\n", payload.GatewayID, payload.PIN)

	err := os.WriteFile(envPath, []byte(envContent), 0644)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Falha ao gravar identidade."})
		return
	}

	_ = godotenv.Load(envPath)

	c.JSON(http.StatusOK, gin.H{
		"message": "Edge provisionado!",
		"gateway_id": os.Getenv("EDGE_GATEWAY_ID"),
	})
}

func GetSystemInfo(c *gin.Context) {
	gatewayID := os.Getenv("EDGE_GATEWAY_ID")
	if gatewayID == "" {
		c.JSON(http.StatusOK, gin.H{"provisioned": false})
		return
	}
	c.JSON(http.StatusOK, gin.H{"provisioned": true, "gateway_id": gatewayID})
}