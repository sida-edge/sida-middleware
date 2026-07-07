package domain

import "time"

type Manifest struct {
	GatewayID string    `json:"gateway_id" binding:"required"`
	Config    Config    `json:"config" binding:"required"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Config struct {
	Plant     Plant                         `json:"plant" binding:"required"`
	Receivers map[string]ReceiverConnection `json:"receivers" binding:"omitempty,dive"`
}

type Plant struct {
	Enterprise string           `json:"enterprise" binding:"required"`
	Site       string           `json:"site" binding:"required"`
	Areas      map[string]Areas `json:"areas" binding:"omitempty,dive"`
}

type Areas struct {
	Lines map[string]Line `json:"lines" binding:"omitempty,dive"`
}

type Line struct {
	Devices map[string]Device `json:"devices" binding:"omitempty,dive"`
}

type ReceiverConnection struct {
	Protocol string `json:"protocol" binding:"required,oneof=http mqtt"`
	Host     string `json:"host" binding:"required,ip|hostname"`
	Port     int    `json:"port" binding:"required,min=1,max=65535"`
	Endpoint string `json:"endpoint" binding:"required_if=Protocol http"`
	Username string `json:"username" binding:"omitempty"`
	Password string `json:"password" binding:"omitempty"`
}

type Device struct {
	Enabled        bool                     `json:"enabled"`
	Connection     Connection               `json:"connection" binding:"required"`
	AssetContext   AssetContext             `json:"asset_context" binding:"required"`
	MetricsMapping map[string]MetricMapping `json:"metrics_mapping" binding:"required,dive"`
}

type Connection struct {
	Protocol   string `json:"protocol" binding:"required,oneof=modbus_tcp modbus_rtu opc_ua s7"`
	ScanRateMs int    `json:"scan_rate_ms" binding:"required,min=50"`
	
	Host       string `json:"host" binding:"required_unless=Protocol opc_ua,omitempty,ip|hostname"`
	Port       int    `json:"port" binding:"required_unless=Protocol opc_ua,omitempty,min=1,max=65535"`
	UnitID     *int   `json:"unit_id" binding:"omitempty,gte=0,lte=255"` // Ponteiro para permitir valor 0
	ByteOrder  string `json:"byte_order" binding:"omitempty,oneof=ABCD CDAB BADC DCBA"`

	EndpointURL    string `json:"endpoint_url" binding:"required_if=Protocol opc_ua"`
	SecurityPolicy string `json:"security_policy" binding:"omitempty,oneof=None Basic128Rsa15 Basic256 Basic256Sha256"`
	SecurityMode   string `json:"security_mode" binding:"omitempty,oneof=None Sign SignAndEncrypt"`
	AuthUsername   string `json:"auth_username" binding:"omitempty"`
	AuthPassword   string `json:"auth_password" binding:"omitempty"`
}

type AssetContext struct {
	Standard string      `json:"standard" binding:"required,eq=ISA-95"`
	Path     []AssetNode `json:"path" binding:"required,min=1,dive"`
}

type AssetNode struct {
	Type string `json:"type" binding:"required,oneof=area line equipment"`
	ID   string `json:"id" binding:"required"`
}

type MetricMapping struct {
	Name        string  `json:"name" binding:"required"`
	ScaleFactor float64 `json:"scale_factor" binding:"required"`
	Unit        string  `json:"unit" binding:"required"`
	DataType    string  `json:"data_type" binding:"required,oneof=float int16 int32 uint16 bool string"`
	
	RegisterType string `json:"register_type,omitempty" binding:"omitempty,oneof=holding input coil discrete"`

	NodeID       string `json:"node_id,omitempty"`
}