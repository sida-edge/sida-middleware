package services

import (
	"log"
	"encoding/json"
	"time"

	"syscall"

	"github.com/pebbe/zmq4"

	"sida-core/internal/core/domain"
)

type ZMQService struct {
	pubSocket *zmq4.Socket
	subSocket *zmq4.Socket
}

func NewZMQService(pubPath string, subPath string, topic string) (*ZMQService, error) {
	pubSocket, err := zmq4.NewSocket(zmq4.PUB)
	if err != nil {
		return nil, err
	}

	address := "tcp://" + pubPath
	if err := pubSocket.Bind(address); err != nil {
		return nil, err
	}

	log.Printf("ZMQ Publisher service rodando em %s", address)

	subSocket, err := zmq4.NewSocket(zmq4.SUB)
	if err != nil {
		return nil, err
	}

	address = "tcp://" + subPath
	if err := subSocket.Bind(address); err != nil {
		return nil, err
	}

	monitorAddr := "inproc://monitor-sub"
	if err := subSocket.Monitor(monitorAddr, zmq4.EVENT_ACCEPTED|zmq4.EVENT_DISCONNECTED); err != nil {
		log.Printf("Aviso: Falha ao iniciar monitor do ZMQ: %v", err)
	} else {
		go func() {
			monSock, err := zmq4.NewSocket(zmq4.PAIR)
			if err != nil {
				log.Printf("Erro ao criar socket PAIR para monitoramento: %v", err)
				return
			}
			defer monSock.Close()

			if err := monSock.Connect(monitorAddr); err != nil {
				log.Printf("Erro ao conectar socket PAIR no monitor: %v", err)
				return
			}

			log.Println("Monitoramento de rede ZMQ (SUB) ativado.")

			for {
				event, addr, value, err := monSock.RecvEvent(0)
				if err != nil {
					break
				}

				switch event {
				case zmq4.EVENT_ACCEPTED:
					log.Printf("[ZMQ] -> Publisher conectado! Endereço: %s (Descritor: %d)", addr, value)
				case zmq4.EVENT_DISCONNECTED:
					log.Printf("[ZMQ] -> Publisher desconectado! Endereço: %s", addr)
				}
			}
		}()
	}
	
	subSocket.SetRcvtimeo(1 * time.Second) 

	log.Printf("ZMQ Subscriber service rodando em %s", address)

	if err := subSocket.SetSubscribe("sida/telemetry"); err != nil {
		return nil, err
	}

	log.Printf("ZMQ Subscriber inscrito no tópico: %s", topic)

	return &ZMQService{
		pubSocket: pubSocket, 
		subSocket: subSocket}, nil
}

func (p *ZMQService) PublishUpdate(manifest domain.Manifest) error {
	topic := "sida/manifest/" + manifest.GatewayID

	manifestJSON, err := json.Marshal(manifest)
	if err != nil {
		log.Printf("Erro ao serializar o manifesto: %v", err)
		return err
	}
	
	_, err = p.pubSocket.SendMessage(topic, string(manifestJSON))
	if err != nil {
		log.Printf("Erro ao publicar no ZMQ: %v", err)
		return err
	}

	log.Printf("Aviso de atualização disparado no tópico: %s", topic)
	return nil
}

func (p *ZMQService) SubscribeToUpdates(topic string) error {
	if err := p.subSocket.SetSubscribe(topic); err != nil {
		log.Printf("Erro ao se inscrever no tópico %s: %v", topic, err)
		return err
	}

	return nil
}

func (p *ZMQService) ReceiveUpdate() (string, error) {
	msg, err := p.subSocket.RecvMessage(zmq4.DONTWAIT)
	if err != nil {
		if (zmq4.AsErrno(err) == zmq4.Errno(syscall.ETIMEDOUT)) {
			return "", nil
		} else if (zmq4.AsErrno(err) == zmq4.Errno(syscall.EAGAIN)) {
			return "", nil
		}
		return "", err
	}

	payload := msg[1]

	return payload, nil
}

func (p *ZMQService) Close() error {
	if err := p.pubSocket.Close(); err != nil {
		log.Printf("Erro ao fechar o socket de publicação: %v", err)
		return err
	}

	if err := p.subSocket.Close(); err != nil {
		log.Printf("Erro ao fechar o socket de inscrição: %v", err)
		return err
	}

	log.Println("Sockets ZMQ fechados com sucesso.")
	return nil
}