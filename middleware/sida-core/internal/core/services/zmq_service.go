package services

import (
	"log"
	"encoding/json"

	"github.com/pebbe/zmq4"

	"sida-core/internal/core/domain"
)

type ZMQService struct {
	pubSocket *zmq4.Socket
	subSocket *zmq4.Socket
}

func NewZMQService(pubPath string, subPaths []string, topicFilter string) (*ZMQService, error) {
	pubSocket, err := zmq4.NewSocket(zmq4.PUB)
	if err != nil {
		return nil, err
	}

	pubAddress := "tcp://" + pubPath
	if err := pubSocket.Bind(pubAddress); err != nil {
		return nil, err
	}

	log.Printf("ZMQ Publisher rodando em %s", pubAddress)

	subSocket, err := zmq4.NewSocket(zmq4.SUB)
	if err != nil {
		return nil, err
	}

	for _, subPath := range subPaths {
		subAddress := "tcp://" + subPath

		if err := subSocket.Connect(subAddress); err != nil {
			pubSocket.Close()
			subSocket.Close()
			return nil, err
		}
		log.Printf("ZMQ Subscriber conectado a %s", subAddress)
	}

	if err := subSocket.SetSubscribe(topicFilter); err != nil {
		pubSocket.Close()
		subSocket.Close()
		return nil, err
	}

	return &ZMQService{
		pubSocket: pubSocket, 
		subSocket: subSocket,
	}, nil
}

func (s *ZMQService) PublishUpdate(manifest domain.Manifest) error {
	topic := "sida/manifest/" + manifest.GatewayID

	manifestJSON, err := json.Marshal(manifest)
	if err != nil {
		log.Printf("Erro ao serializar o manifesto: %v", err)
		return err
	}
	
	_, err = s.pubSocket.SendMessage(topic, string(manifestJSON))
	if err != nil {
		log.Printf("Erro ao publicar no ZMQ: %v", err)
		return err
	}

	log.Printf("Aviso de atualização disparado no tópico: %s", topic)
	return nil
}

func (s *ZMQService) Listen() ([]domain.Telemetry, error) {
	telemetries []domain.Telemetry
	for {
		msg, err := s.subSocket.RecvMessage(0)
		if err != nil {
			return err
		}

		if len(msg) < 2 {
			log.Println("Mensagem ZMQ inválida recebida")
			continue
		}

		topic := msg[0]
		message := msg[1]
	
		var telemetry domain.Telemetry
		if err := json.Unmarshal([]byte(message), &telemetry); err != nil {
			log.Printf("Erro ao desserializar a telemetria: %v", err)
			continue
		}
		telemetries = append(telemetries, telemetry)

		log.Printf("Telemetria recebida no tópico %s: %+v", topic, telemetry)

	}
	return telemetries, nil
}

func (c *ZMQClient) Close() error {
	if err := c.pubSocket.Close(); err != nil {
		c.subSocket.Close()
		return err
	}

	return nil
}