package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	influxdb2 "github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"
	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
	"github.com/sida-edge/sida-memory/schema"
	"google.golang.org/protobuf/proto"
)

const (
	brokerURL    = "tcp://mosquitto-local:1883"
	topic        = "spBv1.0/#"
	clientID     = "sida-memory-worker"
	
	influxURL    = "http://sida-influxdb:8086"
	influxToken  = "token-secreto-sida-123"
	influxOrg    = "sida"
	influxBucket = "telemetria"

	memgraphURI  = "bolt://sida-memgraph:7687"
)

var (
	writeAPI api.WriteAPI
	graphDb  neo4j.DriverWithContext
)

func processaTopologia(payload schema.Payload, partesTopico []string) {
	ctx := context.Background()
	session := graphDb.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	msgType := partesTopico[2]
	groupID := partesTopico[1]
	nodeID := partesTopico[3]

	var cypherQuery string
	var params map[string]interface{}
	var parentID string

	if msgType == "NBIRTH" {
		cypherQuery = `
			MERGE (g:Grupo {id: $group_id})
			MERGE (n:EdgeNode {id: $node_id})
			MERGE (g)-[:CONTEM]->(n)
			SET n.status = "ONLINE", n.ultima_atualizacao = timestamp()
		`
		params = map[string]interface{}{"group_id": groupID, "node_id": nodeID}
		parentID = nodeID
		fmt.Printf("[🕸️] Grafo: NBIRTH registrado (Grupo: %s -> Node: %s)\n", groupID, nodeID)

	} else if msgType == "DBIRTH" && len(partesTopico) == 5 {
		deviceID := partesTopico[4]
		cypherQuery = `
			MERGE (n:EdgeNode {id: $node_id})
			MERGE (d:Dispositivo {id: $device_id})
			MERGE (n)-[:CONTEM]->(d)
			SET d.status = "ONLINE", d.ultima_atualizacao = timestamp()
		`
		params = map[string]interface{}{"node_id": nodeID, "device_id": deviceID}
		parentID = deviceID
		fmt.Printf("[🕸️] Grafo: DBIRTH registrado (Node: %s -> Dispositivo: %s)\n", nodeID, deviceID)
	} else {
		return
	}

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
		return tx.Run(ctx, cypherQuery, params)
	})
	if err != nil {
		log.Printf("[❌] Erro ao gravar nó no Memgraph: %v", err)
		return
	}

	for _, metric := range payload.GetMetrics() {
		if metric.GetName() == "bdSeq" || metric.GetName() == "Node Control/Rebirth" {
			continue
		}
		
		metricQuery := `
			MATCH (pai {id: $parent_id})
			MERGE (m:Metrica {id: $metric_id})
			SET m.nome = $metric_name
			MERGE (pai)-[:MONITORA]->(m)
		`
		metricParams := map[string]interface{}{
			"parent_id":   parentID,
			"metric_id":   parentID + "_" + metric.GetName(),
			"metric_name": metric.GetName(),
		}
		_, _ = session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
			return tx.Run(ctx, metricQuery, metricParams)
		})
	}
}

func processaTelemetria(payload schema.Payload, partesTopico []string) {
	tags := map[string]string{
		"namespace":    partesTopico[0],
		"group_id":     partesTopico[1],
		"edge_node_id": partesTopico[3],
	}
	if len(partesTopico) == 5 {
		tags["device_id"] = partesTopico[4]
	}

	fields := make(map[string]interface{})
	for _, metric := range payload.GetMetrics() {
		if metric.GetName() == "seq" || metric.GetName() == "bdSeq" { continue }

		switch v := metric.Value.(type) {
		case *schema.Payload_Metric_IntValue: fields[metric.GetName()] = v.IntValue
		case *schema.Payload_Metric_LongValue: fields[metric.GetName()] = v.LongValue
		case *schema.Payload_Metric_FloatValue: fields[metric.GetName()] = v.FloatValue
		case *schema.Payload_Metric_DoubleValue: fields[metric.GetName()] = v.DoubleValue
		case *schema.Payload_Metric_BooleanValue: fields[metric.GetName()] = v.BooleanValue
		case *schema.Payload_Metric_StringValue: fields[metric.GetName()] = v.StringValue
		}
	}

	if len(fields) == 0 { return }

	payloadTime := time.UnixMilli(int64(payload.GetTimestamp()))
	if payload.GetTimestamp() == 0 { payloadTime = time.Now() }

	p := influxdb2.NewPoint("telemetria_industrial", tags, fields, payloadTime)
	writeAPI.WritePoint(p)
	fmt.Printf("[⚡] TSDB: Lote de telemetria recebido de %s -> %d métricas.\n", tags["edge_node_id"], len(fields))
}

// Roteador Principal
func handleMessage(client mqtt.Client, msg mqtt.Message) {
	var payload schema.Payload
	if err := proto.Unmarshal(msg.Payload(), &payload); err != nil {
		log.Printf("[❌] Erro ao decodificar: %v\n", err)
		return
	}

	partesTopico := strings.Split(msg.Topic(), "/")
	if len(partesTopico) < 4 { return }
	
	msgType := partesTopico[2]

	if msgType == "DDATA" || msgType == "NDATA" {
		processaTelemetria(payload, partesTopico)
	} else if msgType == "NBIRTH" || msgType == "DBIRTH" {
		processaTopologia(payload, partesTopico)
	}
}

func main() {
	var err error
	
	influxClient := influxdb2.NewClient(influxURL, influxToken)
	defer influxClient.Close()
	writeAPI = influxClient.WriteAPI(influxOrg, influxBucket)

	ctx := context.Background()
	graphDb, err = neo4j.NewDriverWithContext(memgraphURI, neo4j.BasicAuth("", "", ""))
	if err != nil {
		log.Fatalf("[🔥] Erro fatal ao criar driver do Memgraph: %v", err)
	}
	defer graphDb.Close(ctx)
	
	if err := graphDb.VerifyConnectivity(ctx); err != nil {
		log.Fatalf("[🔥] Memgraph não está acessível em %s: %v", memgraphURI, err)
	}
	fmt.Printf("[🚀] Conectado ao Memgraph!\n")

	opts := mqtt.NewClientOptions().AddBroker(brokerURL).SetClientID(clientID)
	opts.SetDefaultPublishHandler(handleMessage)

	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Fatalf("[🔥] Erro MQTT: %v", token.Error())
	}
	
	client.Subscribe(topic, 1, nil)
	fmt.Println("[📡] Worker de Ingestão Híbrida Rodando (InfluxDB + Memgraph)... Pressione Ctrl+C para sair.")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
	
	fmt.Println("\n[🛑] Desligando...")
	writeAPI.Flush()
}