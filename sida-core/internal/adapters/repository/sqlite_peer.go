package repository

import (
	"context"
	"database/sql"
	"encoding/json"

	"sida-core/internal/core/domain"

	_ "github.com/mattn/go-sqlite3"
)

// sqlitePeerRepo persiste o Controller Register do plano B na tabela
// `controllers` do mesmo sida_config.db (WAL). Segue o padrao de
// sqlite_repository.go: CREATE TABLE IF NOT EXISTS no construtor.
type sqlitePeerRepo struct {
	db *sql.DB
}

func NewSQLitePeerRepository(db *sql.DB) (*sqlitePeerRepo, error) {
	query := `
	CREATE TABLE IF NOT EXISTS controllers (
		controller_id                TEXT PRIMARY KEY,
		controller_name              TEXT NOT NULL DEFAULT '',
		connected_controllers        TEXT NOT NULL DEFAULT '[]',
		source_devices               TEXT NOT NULL DEFAULT '[]',
		destination_devices          TEXT NOT NULL DEFAULT '[]',
		condition_actions            TEXT NOT NULL DEFAULT '[]',
		probe_interval_ms            INTEGER NOT NULL DEFAULT 1000,
		peer_down_after_misses       INTEGER NOT NULL DEFAULT 3,
		controller_probe_interval_ms INTEGER NOT NULL DEFAULT 1000,
		updated_at                   DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	if _, err := db.Exec(query); err != nil {
		return nil, err
	}
	return &sqlitePeerRepo{db: db}, nil
}

func (r *sqlitePeerRepo) Save(ctx context.Context, reg domain.ControllerRegister) error {
	cc, _ := json.Marshal(nonNil(reg.ConnectedControllers))
	sd, _ := json.Marshal(nonNilStr(reg.SourceDevices))
	dd, _ := json.Marshal(nonNilStr(reg.DestinationDevices))
	ca, _ := json.Marshal(nonNilStr(reg.ConditionActions))

	query := `
	INSERT INTO controllers (
		controller_id, controller_name, connected_controllers,
		source_devices, destination_devices, condition_actions,
		probe_interval_ms, peer_down_after_misses, controller_probe_interval_ms, updated_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
	ON CONFLICT(controller_id) DO UPDATE SET
		controller_name=excluded.controller_name,
		connected_controllers=excluded.connected_controllers,
		source_devices=excluded.source_devices,
		destination_devices=excluded.destination_devices,
		condition_actions=excluded.condition_actions,
		probe_interval_ms=excluded.probe_interval_ms,
		peer_down_after_misses=excluded.peer_down_after_misses,
		controller_probe_interval_ms=excluded.controller_probe_interval_ms,
		updated_at=CURRENT_TIMESTAMP;`

	_, err := r.db.ExecContext(ctx, query,
		reg.ControllerID, reg.ControllerName, string(cc),
		string(sd), string(dd), string(ca),
		reg.ProbeIntervalMs, reg.PeerDownAfterMisses, reg.ControllerProbeIntervalMs,
	)
	return err
}

func (r *sqlitePeerRepo) Load(ctx context.Context, controllerID string) (*domain.ControllerRegister, error) {
	query := `
	SELECT controller_id, controller_name, connected_controllers,
		source_devices, destination_devices, condition_actions,
		probe_interval_ms, peer_down_after_misses, controller_probe_interval_ms
	FROM controllers WHERE controller_id = ?`

	row := r.db.QueryRowContext(ctx, query, controllerID)

	var reg domain.ControllerRegister
	var cc, sd, dd, ca string
	err := row.Scan(
		&reg.ControllerID, &reg.ControllerName, &cc,
		&sd, &dd, &ca,
		&reg.ProbeIntervalMs, &reg.PeerDownAfterMisses, &reg.ControllerProbeIntervalMs,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	_ = json.Unmarshal([]byte(cc), &reg.ConnectedControllers)
	_ = json.Unmarshal([]byte(sd), &reg.SourceDevices)
	_ = json.Unmarshal([]byte(dd), &reg.DestinationDevices)
	_ = json.Unmarshal([]byte(ca), &reg.ConditionActions)
	return &reg, nil
}

func nonNil(v []domain.PeerRef) []domain.PeerRef {
	if v == nil {
		return []domain.PeerRef{}
	}
	return v
}

func nonNilStr(v []string) []string {
	if v == nil {
		return []string{}
	}
	return v
}
