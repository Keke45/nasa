
package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"

	"astronaut-health-intelligence/database"
	"astronaut-health-intelligence/astronauts"
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
	db, err := database.Initialize()
	if err != nil {
		log.Fatal("Database initialization failed:", err)
	}
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/api/health", healthHandler(db))

	// Astronaut registration endpoint.
	mux.HandleFunc("/api/astronauts", astronauts.RegistrationHandler(db))

	log.Println("Astronaut Health Intelligence API running on :8080")

	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatal("Server failed:", err)
	}
}