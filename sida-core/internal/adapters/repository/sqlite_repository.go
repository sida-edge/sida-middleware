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

func NewSQLiteManifestRepository(dbPath string) (*sqliteManifestRepo, error) {
	dsn := dbPath + "?_journal_mode=WAL&_busy_timeout=5000"
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, err
	}

	query := `
	CREATE TABLE IF NOT EXISTS edge_manifests (
		gateway_id TEXT PRIMARY KEY,
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
	INSERT INTO edge_manifests (gateway_id, config_json, updated_at)
	VALUES (?, ?, ?)
	ON CONFLICT(gateway_id) DO UPDATE SET 
		config_json=excluded.config_json,
		updated_at=excluded.updated_at;`

	_, err = r.db.ExecContext(ctx, query, manifest.GatewayID, string(configBytes), manifest.UpdatedAt)
	return err
}

func (r *sqliteManifestRepo) GetByID(ctx context.Context, gatewayID string) (*domain.Manifest, error) {
	query := `SELECT gateway_id, config_json, updated_at FROM edge_manifests WHERE gateway_id = ?`
	
	row := r.db.QueryRowContext(ctx, query, gatewayID)

	var m domain.Manifest
	var configStr string

	err := row.Scan(&m.GatewayID, &configStr, &m.UpdatedAt)
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