package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
)

type Config struct {
	ServiceName    string
	ServiceVersion string
	Environment    string
	Port           string
	WeatherAPIKey  string
}

func loadConfig() Config {
	serviceName := os.Getenv("SERVICE_NAME")
	if serviceName == "" {
		serviceName = "go-service"
	}
	serviceVersion := os.Getenv("SERVICE_VERSION")
	if serviceVersion == "" {
		serviceVersion = "0.1.0"
	}
	env := os.Getenv("ENVIRONMENT")
	if env == "" {
		env = "development"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	return Config{
		ServiceName:    serviceName,
		ServiceVersion: serviceVersion,
		Environment:    env,
		Port:           port,
		WeatherAPIKey:  os.Getenv("WEATHER_API_KEY"),
	}
}

type HealthResponse struct {
	Status string `json:"status"`
}

type InfoResponse struct {
	Service     string `json:"service"`
	Version     string `json:"version"`
	Environment string `json:"environment"`
}

func setupRoutes(cfg Config, logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		logger.Info("health check requested")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
	})

	mux.HandleFunc("/info", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(InfoResponse{
			Service:     cfg.ServiceName,
			Version:     cfg.ServiceVersion,
			Environment: cfg.Environment,
		})
	})

	return mux
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	cfg := loadConfig()
	handler := setupRoutes(cfg, logger)

	addr := ":" + cfg.Port
	logger.Info("starting go-service", "addr", addr, "environment", cfg.Environment)
	if err := http.ListenAndServe(addr, handler); err != nil && err != http.ErrServerClosed {
		logger.Error("server failed", "error", err)
		os.Exit(1)
	}
}
