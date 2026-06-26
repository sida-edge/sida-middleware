package messaging

import (
	"context"
	"log"
	"encoding/json"

	zmq "github.com/pebbe/zmq4"
	"github.com/sida-edge/sida-ontology-builder/internal/domain"
	"github.com/sida-edge/sida-ontology-builder/internal/repository"
)

type ZMQSubscriber struct {
	endpoint   string
	topic      string
	repository repository.OntologyRepository
}

func NewZMQSubscriber(endpoint, topic string, repository repository.OntologyRepository) *ZMQSubscriber {
	return &ZMQSubscriber{
		endpoint:   endpoint,
		topic:      topic,
		repository: repository,
	}
}

func (s *ZMQSubscriber) Start(ctx context.Context) error {
	zctx, _ := zmq.NewContext()
	subscriber, err := zctx.NewSocket(zmq.SUB)
	if err != nil {
		return err
	}
	defer subscriber.Close()

	if err := subscriber.Connect(s.endpoint); err != nil {
		return err
	}
	if err := subscriber.SetSubscribe(s.topic); err != nil {
		return err
	}
	log.Printf("Subscribed to ZMQ topic: %s at endpoint: %s", s.topic, s.endpoint)

	for {
		select {
		case <-ctx.Done():
			log.Println("ZMQ subscriber shutting down...")
			return nil
		default:
			msg, err := subscriber.RecvMessage(zmq.DONTWAIT)
			if err != nil {
				continue
			}

			if len(msg) >= 2 {
				log.Println("Received message on topic:", msg[0])

				var manifest domain.Manifest
				if err := json.Unmarshal([]byte(msg[1]), &manifest); err != nil {
					log.Printf("Error unmarshalling message: %v", err)
					continue
				}

				if err := s.repository.UpsertManifest(context.Background(), &manifest); err != nil {
					log.Printf("Error upserting manifest to Neo4j: %v", err)
				}
			}
		}
	}
}