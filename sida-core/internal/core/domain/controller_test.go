package domain

import "testing"

func TestParsePeers_OK(t *testing.T) {
	peers, err := ParsePeers("edge_002@edge2-core:5557,edge_003@edge3-core:5557")
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if len(peers) != 2 {
		t.Fatalf("esperava 2 pares, veio %d", len(peers))
	}
	if peers[0].ID != "edge_002" || peers[0].Endpoint != "tcp://edge2-core:5557" {
		t.Fatalf("par[0] inesperado: %+v", peers[0])
	}
	if peers[1].ID != "edge_003" || peers[1].Endpoint != "tcp://edge3-core:5557" {
		t.Fatalf("par[1] inesperado: %+v", peers[1])
	}
}

func TestParsePeers_Vazio(t *testing.T) {
	for _, s := range []string{"", "   ", ",", " , , "} {
		peers, err := ParsePeers(s)
		if err != nil {
			t.Fatalf("%q: erro inesperado: %v", s, err)
		}
		if len(peers) != 0 {
			t.Fatalf("%q: esperava 0 pares, veio %d", s, len(peers))
		}
	}
}

func TestParsePeers_Malformado(t *testing.T) {
	for _, s := range []string{
		"semarroba",
		"@edge2-core:5557",
		"edge_x@",
		"edge_x@hostsemporta",
		"edge_x@host:",
		"a@h:1,a@h:2", // ControllerID duplicado
	} {
		if _, err := ParsePeers(s); err == nil {
			t.Fatalf("%q: esperava erro, veio nil", s)
		}
	}
}

func TestNewControllerRegisterFromEnv(t *testing.T) {
	reg, err := NewControllerRegisterFromEnv("edge_001", "edge_002@edge2-core:5557", 0, 0)
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if reg.ControllerID != "edge_001" {
		t.Fatalf("ControllerID: %q", reg.ControllerID)
	}
	if len(reg.ConnectedControllers) != 1 {
		t.Fatalf("esperava 1 par, veio %d", len(reg.ConnectedControllers))
	}
	if reg.ProbeIntervalMs != 1000 || reg.PeerDownAfterMisses != 3 {
		t.Fatalf("defaults nao aplicados: %+v", reg)
	}
	if _, err := NewControllerRegisterFromEnv("edge_001", "lixo", 1000, 3); err == nil {
		t.Fatalf("esperava erro com PEERS malformado")
	}
}
