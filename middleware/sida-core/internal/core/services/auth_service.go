package services

import (
	"crypto/sha256"
	"fmt"
	"os"
)

type AuthService struct{}

func NewAuthService() *AuthService {
	return &AuthService{}
}

func (s *AuthService) ValidatePIN(pin string) bool {
	expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")
	return expectedPIN != "" && pin == expectedPIN
}

func (s *AuthService) GenerateToken(pin string) string {
	hash := sha256.Sum256([]byte(pin))
	return fmt.Sprintf("session_%x", hash)
}

func (s *AuthService) GetExpectedBearer() string {
	expectedPIN := os.Getenv("EDGE_ENGINEER_PIN")
	hash := sha256.Sum256([]byte(expectedPIN))
	return fmt.Sprintf("Bearer session_%x", hash)
}

