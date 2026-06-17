package api

import (
	"log"
	"net/http"

	"sida-core/internal/adapters/handler"
	"sida-core/internal/core/services"

	"github.com/gin-gonic/gin"
)

func RequireAuth(authService *services.AuthService) gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		expectedToken := authService.GetExpectedBearer()
		
		if token != expectedToken {
			log.Println("Tentativa de acesso bloqueada: Token inválido")
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Acesso não autorizado",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

func SetupRoutes(router *gin.Engine,
				manifestHandler *handler.ManifestHandler,
				authHandler *handler.AuthHandler,
				systemHandler *handler.SystemHandler,
				authService *services.AuthService,
				bufferHandler *handler.BufferHandler) {

	router.Static("/assets", "./public/assets")
	router.StaticFile("/", "./public/index.html")
	router.NoRoute(func(c *gin.Context) {
		c.File("./public/index.html")
	})

	router.GET("/api/health", systemHandler.HealthCheck)
	router.POST("/api/auth/unlock", authHandler.Unlock)

	apiConfig := router.Group("/api/config")
	{
		apiConfig.GET("/manifest", manifestHandler.GetManifest)
		apiConfig.POST("/manifest", RequireAuth(authService), manifestHandler.UploadManifest)
		apiConfig.DELETE("/area/:area", RequireAuth(authService), manifestHandler.RemoveArea)
		apiConfig.DELETE("/:area/lines/:line", RequireAuth(authService), manifestHandler.RemoveLine)
		apiConfig.DELETE("/:area/lines/:line/devices/:id", RequireAuth(authService), manifestHandler.RemoveDevice)
		apiConfig.PATCH("/:area/lines/:line/devices/:id/status", RequireAuth(authService), manifestHandler.ToggleDeviceStatus)
	}

	apiSystem := router.Group("/api/system")
	{
		apiSystem.GET("/info", systemHandler.GetSystemInfo)
		apiSystem.POST("/setup", systemHandler.SetupEdgeGateway)
	}

	apiBuffer := router.Group("/api/buffer")
    {
        apiBuffer.POST("/", bufferHandler.IngestBuffer)
        apiBuffer.GET("/flush", bufferHandler.FlushBuffer)
    }
}