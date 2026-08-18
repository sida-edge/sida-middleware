package ports

import (
	"context"
	"sida-core/internal/core/domain"
)

type ManifestRepository interface {
	Save(ctx context.Context, manifest domain.Manifest) error
	Get(ctx context.Context) (*domain.Manifest, error)
}