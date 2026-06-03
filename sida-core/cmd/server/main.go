package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"sida-core/internal/adapters/handler"
	"sida-core/internal/adapters/repository"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*") 
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	}
}

func RequireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")
		
		expectedToken := "Bearer session_" + expectedPIN

		log.Printf("🔒 [Segurança] Tentativa de Escrita - Token Recebido: '%s' | Token Esperado: '%s'\n", token, expectedToken)

		if expectedPIN == "" {
			log.Println("⚠️ ERRO CRÍTICO: O PIN no servidor está VAZIO. O godotenv não carregou a memória.")
		}

		if token != expectedToken {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Acesso não autorizado pelo Go. Tokens não coincidem."})
			c.Abort()
			return
		}
		
		c.Next()
	}
}

func main() {
	log.Println("Iniciando SIDA-Core...")

	_ = godotenv.Load("/app/data/.env")

	dbPath := "./data/sida_config.db"
	os.MkdirAll(filepath.Dir(dbPath), os.ModePerm)

	repo, err := repository.NewSQLiteManifestRepository(dbPath)
	if err != nil {
		log.Fatal("SQLite fatal error:", err)
	}
	log.Println("Database connected.")

	manifestHandler := handler.NewManifestHandler(repo)

	gin.SetMode(gin.ReleaseMode)
	router := gin.Default()
	router.Use(CORSMiddleware())

	router.Static("/assets", "./public/assets")
	router.StaticFile("/", "./public/index.html")

	router.NoRoute(func(c *gin.Context) {
		c.File("./public/index.html")
	})

	router.GET("/api/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "UP", 
			"service": "sida-core", 
			"timestamp": time.Now().Format(time.RFC3339),
		})
	})

	router.POST("/api/auth/unlock", func(c *gin.Context) {
		var login struct { PIN string `json:"pin"` }
		if err := c.ShouldBindJSON(&login); err != nil {
			c.JSON(400, gin.H{"error": "Dados inválidos"})
			return
		}

		expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")
		
		if expectedPIN != "" && login.PIN == expectedPIN {
			c.JSON(200, gin.H{
				"status": "unlocked",
				"token": "session_" + expectedPIN, 
			})
		} else {
			c.JSON(401, gin.H{"error": "PIN incorreto"})
		}
	})

	api := router.Group("/api/config")
	{
		api.GET("/manifest", manifestHandler.GetManifest)
		api.POST("/manifest", RequireAuth(), manifestHandler.UploadManifest)
	}

	router.GET("/api/system/info", handler.GetSystemInfo)
	router.POST("/api/system/setup", handler.SetupEdgeGateway)

	srv := &http.Server{
		Addr:    ":8000",
		Handler: router,
	}

	go func() {
		log.Println("SIDA-Core rodando na porta 8000")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Erro crítico no servidor HTTP: %s\n", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit 
	
	log.Println("Encerrando SIDA-Core...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Desligamento forçado do servidor:", err)
	}

	log.Println("SIDA-Core encerrado")
}