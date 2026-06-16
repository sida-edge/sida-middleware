package ports

import (
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