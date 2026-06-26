package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/sida-edge/sida-ontology-builder/internal/config"
	"github.com/sida-edge/sida-ontology-builder/internal/messaging"
	"github.com/sida-edge/sida-ontology-builder/internal/repository"
)

func main() {
	log.Println("Starting SIDA Ontology Builder...")
	
	cfg := config.LoadConfig()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	repo, err := repository.NewNeo4jRepository(cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	log.Printf("Connecting to Neo4j at %s with user %s and password %s", cfg.Neo4jURI, cfg.Neo4jUsername, cfg.Neo4jPassword)
	if err != nil {
		log.Fatalf("Failed to connect to Neo4j: %v", err)
	}
	defer repo.Close(ctx)

	subscriber := messaging.NewZMQSubscriber(cfg.ZMQEndpoint, cfg.ZMQTopic, repo)

	go func() {
		if err := subscriber.Start(ctx); err != nil {
			log.Fatalf("ZMQ Subscriber error: %v", err)
		}
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	<-sigChan
	log.Println("Shutting down SIDA Ontology Builder...")
	cancel()
}