package domain

import "github.com/go-playground/validator/v10"

// RegisterConnectionValidation prende a validacao por protocolo do Connection
// no engine de validacao (o do gin). Chame no boot, depois de o gin criar o
// validador. Exigencias que dependem do valor de `Protocol` (e que o
// go-playground/validator nao expressa bem por tag com OR) vivem aqui.
func RegisterConnectionValidation(v *validator.Validate) {
	v.RegisterStructValidation(connectionStructLevel, Connection{})
}

func connectionStructLevel(sl validator.StructLevel) {
	c := sl.Current().Interface().(Connection)

	switch c.Protocol {
	case "modbus_tcp", "modbus_rtu", "s7":
		if c.Host == "" {
			sl.ReportError(c.Host, "Host", "host", "required_for_protocol", c.Protocol)
		}
		if c.Port == 0 {
			sl.ReportError(c.Port, "Port", "port", "required_for_protocol", c.Protocol)
		}
		if c.ScanRateMs < 50 {
			sl.ReportError(c.ScanRateMs, "ScanRateMs", "scan_rate_ms", "min", "50")
		}
	case "opc_ua":
		if c.EndpointURL == "" {
			sl.ReportError(c.EndpointURL, "EndpointURL", "endpoint_url", "required_for_protocol", c.Protocol)
		}
	case "interedge":
		// Sem transporte de sondagem: nada exigido aqui. O device_id e o
		// metrics_mapping vem do manifesto; o asset_context continua
		// obrigatorio (tag `binding:"required"` em Device).
	}
}

// ValidateConnection roda a validacao (tags + struct-level) sobre um Connection
// isolado — util para testes de unidade do dominio.
func ValidateConnection(c Connection) error {
	v := validator.New()
	v.SetTagName("binding")
	RegisterConnectionValidation(v)
	return v.Struct(c)
}
