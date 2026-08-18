package repository

import (
	"context"
	"database/sql"
	"encoding/json"
	"sida-core/internal/core/domain"

	_ "github.com/mattn/go-sqlite3"
)

type sqliteManifestRepo struct {
	db *sql.DB
}

func NewSQLiteManifestRepository(db *sql.DB) (*sqliteManifestRepo, error) {
	query := `
	CREATE TABLE IF NOT EXISTS edge_manifest (
		id INTEGER PRIMARY KEY CHECK (id = 1),
		config_json TEXT NOT NULL,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	
	if _, err := db.Exec(query); err != nil {
		return nil, err
	}

	return &sqliteManifestRepo{db: db}, nil
}

func (r *sqliteManifestRepo) Save(ctx context.Context, manifest domain.Manifest) error {
	configBytes, err := json.Marshal(manifest.Config)
	if err != nil {
		return err
	}

	query := `
	INSERT INTO edge_manifest (id, config_json, updated_at)
	VALUES (1, ?, ?)
	ON CONFLICT(id) DO UPDATE SET 
		config_json=excluded.config_json,
		updated_at=excluded.updated_at;`

	_, err = r.db.ExecContext(ctx, query, string(configBytes), manifest.UpdatedAt)
	return err
}

func (r *sqliteManifestRepo) Get(ctx context.Context) (*domain.Manifest, error) {
	query := `SELECT config_json, updated_at FROM edge_manifest WHERE id = 1`
	
	row := r.db.QueryRowContext(ctx, query)

	var m domain.Manifest
	var configStr string

	err := row.Scan(&configStr, &m.UpdatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil 
		}
		return nil, err
	}

	err = json.Unmarshal([]byte(configStr), &m.Config)
	if err != nil {
		return nil, err
	}

	return &m, nil
}