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

	manifestHandler := handler.NewManifestHandler(repo)
	// .Save .GetByID => SQLiteManifestRepository

	gin.SetMode(gin.ReleaseMode)
	router := gin.Default()

	api.SetupRoutes(router, manifestHandler)

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