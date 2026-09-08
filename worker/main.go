package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"
	"context"
	"strings"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	proto "google.golang.org/protobuf/proto"
	neo4j "github.com/neo4j/neo4j-go-driver/v5/neo4j"

	influxdb2 "github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"

	spb "worker/internal/spb"
)

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}

func initInfluxDB(url, token, org, bucket string) (influxdb2.Client, api.WriteAPIBlocking) {
	client := influxdb2.NewClient(url, token)
	writeAPI := client.WriteAPIBlocking(org, bucket)
	return client, writeAPI
}

func initMemgraph(uri string) (neo4j.DriverWithContext, error) {
	auth := neo4j.BasicAuth("", "", "")
	driver, err := neo4j.NewDriverWithContext(uri, auth)
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	err = driver.VerifyConnectivity(ctx)
	if err != nil {
		return nil, err
	}
	
	return driver, nil
}

func processBirthMessage(ctx context.Context, driver neo4j.DriverWithContext, groupID, edgeNodeID, deviceID string) {
	session := driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	query := `
		MERGE (s:Site {name: $siteName})
		MERGE (e:EdgeNode {name: $edgeNodeId})
		MERGE (s)-[:HAS_EDGE_NODE]->(e)
	`
	params := map[string]any{
		"siteName":   groupID,
		"edgeNodeId": edgeNodeID,
	}

	if deviceID != "" {
		parts := strings.Split(deviceID, "_")
		
		if len(parts) >= 3 {
			params["areaName"] = parts[0]
			params["lineName"] = parts[1]
			params["deviceName"] = parts[2]

			query += `
			MERGE (a:Area {name: $areaName})
			MERGE (l:Line {name: $lineName})
			MERGE (d:Device {name: $deviceName})
			
			// Constrói a árvore semântica da fábrica
			MERGE (s)-[:CONTAINS]->(a)
			MERGE (a)-[:CONTAINS]->(l)
			MERGE (l)-[:CONTAINS]->(d)
			
			// Define qual Edge Node (CLP) controla fisicamente esse dispositivo
			MERGE (e)-[:CONTROLS]->(d)
			`
		} else {
			params["deviceName"] = deviceID
			query += `
			MERGE (d:Device {name: $deviceName})
			MERGE (s)-[:CONTAINS]->(d)
			MERGE (e)-[:CONTROLS]->(d)
			`
		}
	}

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		return tx.Run(ctx, query, params)
	})

	if err != nil {
		log.Printf("[ERRO] Falha ao gravar topologia no Memgraph: %v", err)
	} else {
		log.Printf("[MEMGRAPH] UNS atualizado! Site: %s | Edge: %s | Device: %s", groupID, edgeNodeID, deviceID)
	}
}

func processDataMessage(ctx context.Context, writeAPI api.WriteAPIBlocking, groupID, edgeNodeID, deviceID string, payload *spb.Payload) {

	tags := map[string]string{
		"site":      groupID,
		"edgeNode":  edgeNodeID,
	}

	if deviceID != "" {
		parts := strings.Split(deviceID, "_")
		if len(parts) >= 3 {
			tags["area"] = parts[0]
			tags["line"] = parts[1]
			tags["device"] = parts[2]
		} else {
			tags["device"] = deviceID
		}
	}

	for _, metric := range payload.Metrics {
		metricName := metric.GetName()
		if metricName == "" {
			log.Printf("[ERRO] Métrica sem nome recebida. Ignorando...")
			continue
		}

		var value interface{}
		switch v := metric.GetValue().(type) {
		case *spb.Payload_Metric_IntValue:
			value = v.IntValue
		case *spb.Payload_Metric_FloatValue:
			value = v.FloatValue
		case *spb.Payload_Metric_BooleanValue:
			value = v.BooleanValue
		case *spb.Payload_Metric_StringValue:
			value = v.StringValue
		default:
			log.Printf("[ERRO] Tipo de métrica desconhecido para %s. Ignorando...", metricName)
			continue
		}

		ts := time.Now()
		if metric.Timestamp != nil {
			ts = time.UnixMilli(int64(metric.GetTimestamp()))
		}

		point := influxdb2.NewPoint("telemetry",
			tags,
			map[string]interface{}{metricName: value},
			ts,
		)
		err := writeAPI.WritePoint(ctx, point)
		if err != nil {
			log.Printf("[ERRO] Falha ao escrever ponto no InfluxDB: %v", err)
		}
	}

	log.Printf("[INFLUXDB] Telemetria gravada! Site: %s | Edge: %s | Device: %s", groupID, edgeNodeID, deviceID)
}

func processDeathMessage(ctx context.Context, driver neo4j.DriverWithContext, messageType, edgeNodeID, deviceID string) {
	session := driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	var query string
	params := map[string]any{
		"edgeNodeId": edgeNodeID,
		"timestamp":  time.Now().UnixMilli(),
	}

	if messageType == "DDEATH" && deviceID != "" {
		// Pega só o último pedaço (deviceName) caso venha no formato Area_Linha_Equip
		parts := strings.Split(deviceID, "_")
		params["deviceName"] = parts[len(parts)-1] 

		// Atualiza apenas o dispositivo específico
		query = `
		MATCH (e:EdgeNode {name: $edgeNodeId})-[:CONTROLS]->(d:Device {name: $deviceName})
		SET d.status = 'Offline', d.lastSeen = $timestamp
		`
	} else if messageType == "NDEATH" {
		// Atualiza o Edge Node E, em cascata, todos os dispositivos que ele controla
		query = `
		MATCH (e:EdgeNode {name: $edgeNodeId})
		SET e.status = 'Offline', e.lastSeen = $timestamp
		WITH e
		OPTIONAL MATCH (e)-[:CONTROLS]->(d:Device)
		SET d.status = 'Offline', d.lastSeen = $timestamp
		`
	}

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		return tx.Run(ctx, query, params)
	})

	if err != nil {
		log.Printf("[ERRO] Falha ao registrar Óbito (%s) no Memgraph: %v", messageType, err)
	} else {
		log.Printf("[MEMGRAPH] Status atualizado para OFFLINE! Edge: %s | Device: %s", edgeNodeID, deviceID)
	}
}

func main() {
	brokerURL := getEnv("MQTT_BROKER_URL", "tcp://mosquitto-local:1883")
	clientID := getEnv("MQTT_CLIENT_ID", "sida-worker-ingestor")
	topic := getEnv("MQTT_TOPIC", "spBv1.0/#")
	memgraphURL := getEnv("MEMGRAPH_URL", "bolt://sida-memgraph:7687")
	
	log.Println("Conectando ao Memgraph...")
	dbDriver, err := initMemgraph(memgraphURL)
	if err != nil {
		log.Fatalf("[FATAL] Erro ao conectar no Memgraph: %v", err)
	}
	defer dbDriver.Close(context.Background())
	log.Println("[OK] Conectado ao Memgraph!")

	influxURL := getEnv("INFLUXDB_URL", "http://sida-influxdb:8086")
	influxToken := getEnv("INFLUXDB_TOKEN", "token-super-secreto-sida-edge")
	influxOrg := getEnv("INFLUXDB_ORG", "sida")
	influxBucket := getEnv("INFLUXDB_BUCKET", "telemetry")

	log.Println("Conectando ao InfluxDB...")
	influxClient, influxWriteAPI := initInfluxDB(influxURL, influxToken, influxOrg, influxBucket)
	defer influxClient.Close()
	log.Println("[OK] Conectado ao InfluxDB!")

	var messagePubHandler mqtt.MessageHandler = func(client mqtt.Client, msg mqtt.Message) {
		// Tópico padrão: spBv1.0/GroupId/MessageType/EdgeNodeId/[DeviceId]
		topicParts := strings.Split(msg.Topic(), "/")
		if len(topicParts) < 4 {
			return 
		}

		groupID := topicParts[1]
		messageType := topicParts[2]
		edgeNodeID := topicParts[3]
		deviceID := ""
		if len(topicParts) == 5 {
			deviceID = topicParts[4]
		}

		var spbPayload spb.Payload
		if err := proto.Unmarshal(msg.Payload(), &spbPayload); err != nil {
			log.Printf("[ERRO] Falha ao decodificar Protobuf: %v", err)
			return
		}

		ctx := context.Background()
		switch messageType {
		case "NBIRTH", "DBIRTH":
			log.Printf("Processando Nascimento (%s)...", messageType)
			processBirthMessage(ctx, dbDriver, groupID, edgeNodeID, deviceID)
			
		case "NDATA", "DDATA":
			log.Printf("Processando Telemetria (%s)...", messageType)
			processDataMessage(ctx, influxWriteAPI, groupID, edgeNodeID, deviceID, &spbPayload)

		case "NDEATH", "DDEATH":
			log.Printf("Processando Óbito (%s)...", messageType)
			processDeathMessage(ctx, dbDriver, messageType, edgeNodeID, deviceID)
		}
	}

	opts := mqtt.NewClientOptions()
	opts.AddBroker(brokerURL)
	opts.SetClientID(clientID)
	opts.SetDefaultPublishHandler(messagePubHandler)
	opts.SetCleanSession(false)
	
	opts.SetAutoReconnect(true)
	opts.SetMaxReconnectInterval(10 * time.Second)
	opts.SetConnectionLostHandler(func(c mqtt.Client, err error) {
		log.Printf("[ALERTA] Conexão com broker %s perdida: %v", brokerURL, err)
	})
	opts.SetOnConnectHandler(func(c mqtt.Client) {
		log.Printf("[OK] Conectado ao broker: %s", brokerURL)
		if token := c.Subscribe(topic, 1, nil); token.Wait() && token.Error() != nil {
			log.Printf("[ERRO] Falha ao assinar tópico: %v", token.Error())
		} else {
			log.Printf("[OK] Assinando tópico: %s", topic)
		}
	})

	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Fatalf("[FATAL] Erro ao iniciar conexão MQTT: %v", token.Error())
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	
	<-sigChan
	log.Println("Sinal recebido. Encerrando o worker de forma limpa...")
	client.Disconnect(250)
	log.Println("Worker encerrado.")
}