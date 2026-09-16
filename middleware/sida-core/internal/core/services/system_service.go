package services

import (
	"fmt"
	"math"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
)

type SystemStats struct {
	CPU         string `json:"cpu"`
	RAM         string `json:"ram"`
	IsConnected bool   `json:"isConnected"`
}

func GetSystemStats() (SystemStats, error) {
	cpuPercent, err := cpu.Percent(time.Second, false)
	if err != nil {
		return SystemStats{}, fmt.Errorf("erro ao obter uso da CPU: %v", err)
	}

	vMem, err := mem.VirtualMemory()
	if err != nil {
		return SystemStats{}, fmt.Errorf("erro ao obter uso da RAM: %v", err)
	}

	cpuUsage := fmt.Sprintf("%.1f", cpuPercent[0])
	
	ramGB := float64(vMem.Used) / math.Pow(1024, 3)
	ramUsage := fmt.Sprintf("%.1f", ramGB)

	return SystemStats{
		CPU:         cpuUsage,
		RAM:         ramUsage,
		IsConnected: true,
	}, nil
}