package domain

type Telemetry struct {
	Service string `json:"service" binding:"required"`
	Data    string `json:"data" binding:"required"`
}