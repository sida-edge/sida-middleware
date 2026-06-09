package services

import (
	"log"

	"github.com/pebbe/zmq4"
)

type ZMQPublisher struct {
	socket *zmq4.Socket
}

func NewZMQPublisher(ipcPath string) (*ZMQPublisher, error) {
	socket, err := zmq4.NewSocket(zmq4.PUB)
	if err != nil {
		return nil, err
	}

	address := "ipc://" + ipcPath
	if err := socket.Bind(address); err != nil {
		return nil, err
	}

	log.Printf("ZMQ Publisher rodando em %s", address)
	return &ZMQPublisher{socket: socket}, nil
}

func (p *ZMQPublisher) PublishUpdate(gatewayID string) error {
	topic := "sida/manifest/" + gatewayID

	_, err := p.socket.SendMessage(topic, "RELOAD")
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