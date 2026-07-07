package repository

import (
	"context"
	"database/sql"
	"encoding/json"
)

type sqliteBufferRepo struct {
	db *sql.DB
}

func NewSQLiteBufferRepository(db *sql.DB) (*sqliteBufferRepo, error) {
	query := `
	CREATE TABLE IF NOT EXISTS spb_buffer (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		payload TEXT NOT NULL,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`
	
	if _, err := db.Exec(query); err != nil {
		return nil, err
	}

	return &sqliteBufferRepo{db: db}, nil
}

func (r *sqliteBufferRepo) Save(ctx context.Context, payload []byte) error {
	query := `INSERT INTO spb_buffer (payload) VALUES (?)`
	
	_, err := r.db.ExecContext(ctx, query, string(payload))
	return err
}

func (r *sqliteBufferRepo) Flush(ctx context.Context) ([]json.RawMessage, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}

	defer tx.Rollback()

	query := `SELECT id, payload FROM spb_buffer ORDER BY id ASC`
	rows, err := tx.QueryContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var payloads []json.RawMessage

	for rows.Next() {
		var id int
		var payloadStr string
		
		if err := rows.Scan(&id, &payloadStr); err != nil {
			return nil, err
		}

		payloads = append(payloads, json.RawMessage(payloadStr))
	}

	if len(payloads) == 0 {
		return payloads, nil
	}

	deleteQuery := `DELETE FROM spb_buffer`
	if _, err := tx.ExecContext(ctx, deleteQuery); err != nil {
		return nil, err
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}

	return payloads, nil
}