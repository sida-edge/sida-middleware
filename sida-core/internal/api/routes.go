package api

import (
	"os"
	"log"
	"fmt"
	"time"
	"net/http"
	"crypto/sha256"

	"sida-core/internal/adapters/handler"
	"github.com/gin-gonic/gin"
)

func RequireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		
		expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")
		if expectedPIN == "" {
			log.Println("ERROR: O PIN no servidor está VAZIO. O godotenv não carregou a memória.")
		}

		hash := sha256.Sum256([]byte(expectedPIN))
        expectedToken := fmt.Sprintf("Bearer session_%x", hash)

		if token != expectedToken {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Acesso não autorizado",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

func SetupRoutes(router *gin.Engine, manifestHandler *handler.ManifestHandler) {
	router.Static("/assets", "./public/assets")
	router.StaticFile("/", "./public/index.html")
	router.NoRoute(func(c *gin.Context) {
		c.File("./public/index.html")
	})

	router.GET("/api/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":		"UP",
			"service":		"sida-core",
			"timestamp": 	time.Now().Format(time.RFC3339),
		})
	})

	// TODO: Separar funcao de verificacao de PIN 
	router.POST("/api/auth/unlock", func(c *gin.Context) {
		var login struct { PIN string `json:"pin"` }
		
		if err := c.ShouldBindJSON(&login); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Dados inválidos",
			})
			return
		}

		expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")

		if expectedPIN != "" && login.PIN == expectedPIN {
			hash := sha256.Sum256([]byte(expectedPIN))
        	secureToken := fmt.Sprintf("session_%x", hash)
			c.JSON(http.StatusOK, gin.H{
				"status": "unlocked",
				"token":  secureToken,
			})
		} else {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "PIN incorreto",
			})
		}
	})

	apiConfig := router.Group("/api/config")
	{
		apiConfig.GET("/manifest", manifestHandler.GetManifest)
		apiConfig.POST("/manifest", RequireAuth(), manifestHandler.UploadManifest)
		apiConfig.DELETE("/device/:id", RequireAuth(), manifestHandler.RemoveDevice)

	}

	apiSystem := router.Group("/api/system")
	{
		apiSystem.GET("/info", handler.GetSystemInfo)
		apiSystem.POST("/setup", handler.SetupEdgeGateway)
	}
}