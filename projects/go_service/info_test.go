package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestInfoEndpoint(t *testing.T) {
	cfg := Config{
		ServiceName:    "custom-service",
		ServiceVersion: "1.2.3",
		Environment:    "staging",
		Port:           "9000",
		WeatherAPIKey:  "secret-12345",
	}
	handler := setupRoutes(cfg, newTestLogger())

	req := httptest.NewRequest(http.MethodGet, "/info", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, rec.Code)
	}

	var body InfoResponse
	if err := json.NewDecoder(rec.Body).Decode(&body); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if body.Service != "custom-service" {
		t.Errorf("expected service 'custom-service', got '%s'", body.Service)
	}
	if body.Version != "1.2.3" {
		t.Errorf("expected version '1.2.3', got '%s'", body.Version)
	}
	if body.Environment != "staging" {
		t.Errorf("expected environment 'staging', got '%s'", body.Environment)
	}
}

func TestInfoEndpointMethodNotAllowed(t *testing.T) {
	cfg := loadConfig()
	handler := setupRoutes(cfg, newTestLogger())

	req := httptest.NewRequest(http.MethodPost, "/info", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected status %d, got %d", http.StatusMethodNotAllowed, rec.Code)
	}
}

func TestInfoDoesNotLeakSecrets(t *testing.T) {
	cfg := Config{
		ServiceName:    "test-service",
		ServiceVersion: "0.1.0",
		Environment:    "production",
		Port:           "8000",
		WeatherAPIKey:  "super-secret-key-that-must-not-leak",
	}
	handler := setupRoutes(cfg, newTestLogger())

	req := httptest.NewRequest(http.MethodGet, "/info", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	rawBody := rec.Body.String()
	forbidden := []string{"secret", "key", "password", "token", "credential", "super-secret"}
	for _, term := range forbidden {
		if strings.Contains(strings.ToLower(rawBody), term) {
			t.Errorf("forbidden term '%s' leaked in /info response: %s", term, rawBody)
		}
	}
}

func TestLoadConfigDefaults(t *testing.T) {
	os.Unsetenv("SERVICE_NAME")
	os.Unsetenv("SERVICE_VERSION")
	os.Unsetenv("ENVIRONMENT")
	os.Unsetenv("PORT")
	os.Unsetenv("WEATHER_API_KEY")

	cfg := loadConfig()
	if cfg.ServiceName != "go-service" {
		t.Errorf("expected default serviceName 'go-service', got '%s'", cfg.ServiceName)
	}
	if cfg.ServiceVersion != "0.1.0" {
		t.Errorf("expected default serviceVersion '0.1.0', got '%s'", cfg.ServiceVersion)
	}
	if cfg.Environment != "development" {
		t.Errorf("expected default environment 'development', got '%s'", cfg.Environment)
	}
	if cfg.Port != "8000" {
		t.Errorf("expected default port '8000', got '%s'", cfg.Port)
	}
}
