package services

import (
	"log"
	"encoding/json"

	"github.com/pebbe/zmq4"

	"sida-core/internal/core/domain"
)

type ZMQPublisher struct {
	socket *zmq4.Socket
}

func NewZMQPublisher(tcpPath string) (*ZMQPublisher, error) {
	socket, err := zmq4.NewSocket(zmq4.PUB)
	if err != nil {
		return nil, err
	}

	address := "tcp://" + tcpPath
	if err := socket.Bind(address); err != nil {
		return nil, err
	}

	log.Printf("ZMQ Publisher rodando em %s", address)
	return &ZMQPublisher{socket: socket}, nil
}

func (p *ZMQPublisher) PublishUpdate(manifest domain.Manifest) error {
	topic := "sida/manifest/" + manifest.GatewayID

	manifestJSON, err := json.Marshal(manifest)
	if err != nil {
		log.Printf("Erro ao serializar o manifesto: %v", err)
		return err
	}
	
	_, err = p.socket.SendMessage(topic, string(manifestJSON))
	if err != nil {
		log.Printf("Erro ao publicar no ZMQ: %v", err)
		return err
	}

	log.Printf("Aviso de atualização disparado no tópico: %s", topic)
	return nil
}

func (p *ZMQPublisher) Close() error {
	return p.socket.Close()
}