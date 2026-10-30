package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
	"database/sql"

	"sida-core/internal/adapters/handler"
	"sida-core/internal/adapters/repository"
	"sida-core/internal/core/domain"
	"sida-core/internal/core/services"
	"sida-core/internal/api"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
	"github.com/go-playground/validator/v10"
	"github.com/joho/godotenv"
)

func atoiOr(s string, def int) int {
	if n, err := strconv.Atoi(strings.TrimSpace(s)); err == nil {
		return n
	}
	return def
}

func main() {
	log.Println("Iniciando SIDA-Core...")

	_ = godotenv.Load("/app/data/.env")

	// Plano B (leste-oeste / InterEdge): registro de pares a partir das envs de
	// identidade do nó. O peer_service em si é cabeado no T1B.5.
	controllerReg, err := domain.NewControllerRegisterFromEnv(
		os.Getenv("CONTROLLER_ID"),
		os.Getenv("PEERS"),
		atoiOr(os.Getenv("PROBE_INTERVAL_MS"), 1000),
		atoiOr(os.Getenv("PEER_DOWN_AFTER_MISSES"), 3),
	)
	if err != nil {
		log.Printf("PEERS malformado, seguindo sem pares: %v", err)
	}
	log.Printf("peer register: %d pares", len(controllerReg.ConnectedControllers))
	dbPath := "./data/sida_config.db"
	os.MkdirAll(filepath.Dir(dbPath), os.ModePerm)

	dsn := dbPath + "?_journal_mode=WAL&_busy_timeout=5000"
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		log.Fatal("SQLite fatal error:", err)
	}

	defer db.Close()
	db.SetMaxOpenConns(1)

	manifestRepo, err := repository.NewSQLiteManifestRepository(db)
	if err != nil {
		log.Fatal("SQLite fatal error:", err)
	}

	bufferRepo, err := repository.NewSQLiteBufferRepository(db)
	if err != nil {
		log.Fatal(err)
	}

	// Plano B: tabela `controllers` no mesmo sida_config.db (WAL). Persiste o
	// registro deste nó a cada boot para retomada apos restart.
	peerRepo, err := repository.NewSQLitePeerRepository(db)
	if err != nil {
		log.Fatal("SQLite (controllers) fatal error:", err)
	}
	if controllerReg.ControllerID != "" {
		if err := peerRepo.Save(context.Background(), controllerReg); err != nil {
			log.Printf("nao consegui persistir o Controller Register: %v", err)
		}
	}
	log.Println("Database connected.")

	zmqPub, err := services.NewZMQPublisher("0.0.0.0:5556")
	if err != nil {
		log.Fatal("Erro fatal ao iniciar ZeroMQ:", err)
	}

	// Plano B (leste-oeste): malha ZeroMQ ROUTER/DEALER em PEER_PORT, dedicada
	// e distinta do PUB de manifesto em :5556. Só sobe se o nó tem CONTROLLER_ID.
	var peerSvc *services.PeerService
	if controllerReg.ControllerID != "" {
		peerPort := strings.TrimSpace(os.Getenv("PEER_PORT"))
		if peerPort == "" {
			peerPort = "5557"
		}
		peerSvc = services.NewPeerService(controllerReg, peerPort)
		if err := peerSvc.Start(); err != nil {
			log.Printf("peer-mesh nao subiu: %v", err)
			peerSvc = nil
		}
	}

	authService := services.NewAuthService()
	authHandler := handler.NewAuthHandler(authService)
	systemHandler := handler.NewSystemHandler()
	manifestHandler := handler.NewManifestHandler(manifestRepo, zmqPub)
	bufferHandler := handler.NewBufferHandler(bufferRepo)
	peerHandler := handler.NewPeerHandler(peerSvc)

	gin.SetMode(gin.ReleaseMode)

	// Validacao por protocolo do Connection (inclui o novo `interedge` da Etapa 2).
	if v, ok := binding.Validator.Engine().(*validator.Validate); ok {
		domain.RegisterConnectionValidation(v)
	}

	router := gin.Default()

	api.SetupRoutes(router, manifestHandler, authHandler, systemHandler, authService, bufferHandler, peerHandler)

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

	if peerSvc != nil {
		peerSvc.Stop()
		log.Println("peer-mesh encerrada")
	}

	if err := zmqPub.Close(); err != nil {
		log.Println("Erro ao fechar socket ZMQ:", err)
	}

	log.Println("SIDA-Core encerrado")
}