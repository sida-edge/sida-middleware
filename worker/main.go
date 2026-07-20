package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"worker/internal/spb" 
	"google.golang.org/protobuf/proto"
)

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}

var messagePubHandler mqtt.MessageHandler = func(client mqtt.Client, msg mqtt.Message) {
	payload := msg.Payload()
	
	var spbPayload schema.Payload
	err := proto.Unmarshal(payload, &spbPayload)
	if err != nil {
	    log.Printf("[ERRO] Falha ao decodificar Protobuf: %v", err)
	    return
	}

	log.Printf("[SUCESSO] Recebido no tópico: %s | Tamanho: %d bytes", msg.Topic(), len(payload))
}

func main() {
	brokerURL := getEnv("MQTT_BROKER_URL", "tcp://mosquitto-local:1883")
	clientID := getEnv("MQTT_CLIENT_ID", "sida-worker-ingestor")
	topic := getEnv("MQTT_TOPIC", "spBv1.0/#")

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