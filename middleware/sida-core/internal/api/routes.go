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
				authService *services.AuthService) {

	router.Static("/assets", "./public/assets")
	router.StaticFile("/", "./public/index.html")
	router.NoRoute(func(c *gin.Context) {
		c.File("./public/index.html")
	})

	router.POST("/internal/unlock", authHandler.Unlock)

	apiConfig := router.Group("/internal")
	{
		// Manifest routes
		apiConfig.GET("/manifest", manifestHandler.GetManifest)
		apiConfig.POST("/manifest", RequireAuth(authService), manifestHandler.UploadManifest)
		apiConfig.PATCH("/:area/lines/:line/devices/:id/status", RequireAuth(authService), manifestHandler.ToggleDeviceStatus)
		
		// System routes
		apiConfig.GET("/health", systemHandler.HealthCheck)
		apiConfig.GET("/info", systemHandler.GetSystemInfo)
		apiConfig.POST("/setup", systemHandler.SetupEdgeGateway)

		// Telemetry routes
		apiConfig.GET("/telemetries", RequireAuth(authService), systemHandler.GetTelemetries)
	}
}