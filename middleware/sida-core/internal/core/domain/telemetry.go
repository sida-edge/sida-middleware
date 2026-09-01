package domain

import "time"

type Telemetry struct {
	Service string   `json:"service" binding:"required"`
	Status string   `json:"status" binding:"required"`
	TimeStamp time.Time `json:"timestamp" binding:"required"`
}