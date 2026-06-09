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
	"sida-core/internal/core/services"
	"sida-core/internal/api"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

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

	zmqPub, err := services.NewZMQPublisher("/tmp/.ipc/manifest.ipc")
	if err != nil {
		log.Fatal("Erro fatal ao iniciar ZeroMQ:", err)
	}

	authService := services.NewAuthService()
	authHandler := handler.NewAuthHandler(authService)
	systemHandler := handler.NewSystemHandler()
	manifestHandler := handler.NewManifestHandler(repo, zmqPub)

	gin.SetMode(gin.ReleaseMode)
	router := gin.Default()

	api.SetupRoutes(router, manifestHandler, authHandler, systemHandler, authService)

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

	if err := zmqPub.Close(); err != nil {
		log.Println("Erro ao fechar socket ZMQ:", err)
	}

	log.Println("SIDA-Core encerrado")
}