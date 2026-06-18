package handler

import (
	"net/http"

	"sida-core/internal/core/services"
	"github.com/gin-gonic/gin"
)

type AuthHandler struct {
	authService *services.AuthService
}

func NewAuthHandler(svc *services.AuthService) *AuthHandler {
	return &AuthHandler{authService: svc}
}

func (h *AuthHandler) Unlock(c *gin.Context) {
	var login struct {
		PIN string `json:"pin" binding:"required"`
	}

	if err := c.ShouldBindJSON(&login); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Dados inválidos",
		})
		return
	}

	if h.authService.ValidatePIN(login.PIN) {
		secureToken := h.authService.GenerateToken(login.PIN)
		c.JSON(http.StatusOK, gin.H{
			"status": "unlocked",
			"token":  secureToken,
		})
	} else {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "PIN incorreto",
		})
	}
}