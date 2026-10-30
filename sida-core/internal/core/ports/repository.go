package ports

import (
	"encoding/json"
	"context"
	"sida-core/internal/core/domain"
)

type ManifestRepository interface {
	Save(ctx context.Context, manifest domain.Manifest) error
	GetByID(ctx context.Context, gatewayID string) (*domain.Manifest, error)
}

type BufferRepository interface {
	Save(ctx context.Context, payload []byte) error
	Flush(ctx context.Context) ([]json.RawMessage, error)
}

// PeerRepository — persistência do Controller Register do plano B (tabela
// controllers no sida_config.db). CRUD do registro de pares deste nó.
type PeerRepository interface {
	Save(ctx context.Context, reg domain.ControllerRegister) error
	Load(ctx context.Context, controllerID string) (*domain.ControllerRegister, error)
}