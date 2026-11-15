package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"

	"astronaut-health-intelligence/astronauts"
	"astronaut-health-intelligence/database"
	"astronaut-health-intelligence/health"
)

type HealthResponse struct {
	Status   string `json:"status"`
	Database string `json:"database"`
}

func healthHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		if err := db.Ping(); err != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			json.NewEncoder(w).Encode(HealthResponse{
				Status:   "unhealthy",
				Database: "disconnected",
			})
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(HealthResponse{
			Status:   "running",
			Database: "connected",
		})
	}
}

func main() {
    // Call InitDB() instead of Initialize()
    database.InitDB()
    defer database.DB.Close()

    mux := http.NewServeMux()

    mux.HandleFunc("/api/health", healthHandler(database.DB))
    mux.HandleFunc("/api/astronauts", astronauts.RegistrationHandler(database.DB))

    // Register telemetry ingestion route
    health.RegisterHandlers(mux)

    log.Println("Astronaut Health Intelligence API running on :8080")

    if err := http.ListenAndServe(":8080", mux); err != nil {
        log.Fatal("Server failed:", err)
    }
}