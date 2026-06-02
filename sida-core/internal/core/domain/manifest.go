package domain

import "time"

type Manifest struct {
	GatewayID string
	Config    map[string]interface{}
	UpdatedAt time.Time
}