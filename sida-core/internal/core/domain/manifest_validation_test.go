package domain

import "testing"

func TestValidateConnection_PorProtocolo(t *testing.T) {
	cases := []struct {
		name string
		c    Connection
		ok   bool
	}{
		{"interedge sem transporte", Connection{Protocol: "interedge"}, true},
		{"modbus_tcp completo", Connection{Protocol: "modbus_tcp", Host: "plc-sim", Port: 502, ScanRateMs: 1000}, true},
		{"modbus_tcp sem host", Connection{Protocol: "modbus_tcp", Port: 502, ScanRateMs: 1000}, false},
		{"modbus_tcp sem port", Connection{Protocol: "modbus_tcp", Host: "plc-sim", ScanRateMs: 1000}, false},
		{"modbus_tcp scan_rate baixo", Connection{Protocol: "modbus_tcp", Host: "plc-sim", Port: 502, ScanRateMs: 10}, false},
		{"opc_ua com endpoint", Connection{Protocol: "opc_ua", EndpointURL: "opc.tcp://x:4840"}, true},
		{"opc_ua sem endpoint", Connection{Protocol: "opc_ua"}, false},
		{"protocolo desconhecido", Connection{Protocol: "carrier_pigeon"}, false},
		{"protocolo vazio", Connection{}, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidateConnection(tc.c)
			if tc.ok && err != nil {
				t.Fatalf("esperava valido, veio erro: %v", err)
			}
			if !tc.ok && err == nil {
				t.Fatalf("esperava erro, veio nil")
			}
		})
	}
}
