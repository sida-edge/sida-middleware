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

func main() {
	log.Println("Iniciando SIDA-Core...")

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

	api := router.Group("/api/config")
	{
		api.POST("/manifest", manifestHandler.UploadManifest)
		api.GET("/manifest", manifestHandler.GetManifest)
	}

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