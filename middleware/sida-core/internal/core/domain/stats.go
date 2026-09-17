package domain

type SystemStats struct {
	CPU         string `json:"cpu"`
	RAM         string `json:"ram"`
	IsConnected bool   `json:"isConnected"`
}
