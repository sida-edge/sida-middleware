package config

import "os"

type Config struct {
	Neo4jURI      string
	Neo4jUsername string
	Neo4jPassword string
	ZMQEndpoint   string
	ZMQTopic      string
}

func LoadConfig() *Config {
	return &Config{
		Neo4jURI:      getEnv("NEO4J_URI", "neo4j://localhost:7687"),
		Neo4jUsername: getEnv("NEO4J_USERNAME", "neo4j"),
		Neo4jPassword: getEnv("NEO4J_PASSWORD", "sida_password"),
		ZMQEndpoint:   getEnv("ZMQ_ENDPOINT", "tcp://localhost:5555"),
		ZMQTopic:      getEnv("ZMQ_TOPIC", "sida/manifest/"),
	}
}

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}
