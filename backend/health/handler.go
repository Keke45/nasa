package health

import (
	"encoding/json"
	"net/http"
	"time"

	"astronaut-health-intelligence/database" // Updated with your repository/module name from go.mod
)

// RegisterHandlers registers the telemetry routes with CORS enabled
func RegisterHandlers(mux *http.ServeMux) {
	mux.HandleFunc("/api/telemetry", enableCORS(handleTelemetrySubmission))
}

// enableCORS adds the required headers for cross-origin frontend-to-backend requests
func enableCORS(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// Handle preflight OPTIONS requests immediately
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next(w, r)
	}
}

func handleTelemetrySubmission(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var reading HealthReading
	err := json.NewDecoder(r.Body).Decode(&reading)
	if err != nil {
		http.Error(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Assign ID and timestamp if missing
	if reading.ID == "" {
		reading.ID = time.Now().Format("20060102150405") + "-rec"
	}
	if reading.RecordedAt.IsZero() {
		reading.RecordedAt = time.Now()
	}

	// Validate data
	if err := reading.Validate(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Insert into SQLite
	query := `
	INSERT INTO HealthReadings (id, astronaut_id, heart_rate, systolic_bp, diastolic_bp, body_temperature, oxygen_saturation, sleep_duration, physical_activity, fatigue_level, source, recorded_at)
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	_, err = database.DB.Exec(query,
		reading.ID, reading.AstronautID, reading.HeartRate, reading.SystolicBP, reading.DiastolicBP,
		reading.BodyTemp, reading.OxygenSaturation, reading.SleepDuration, reading.PhysicalActivity,
		reading.FatigueLevel, reading.Source, reading.RecordedAt,
	)

	if err != nil {
		http.Error(w, "Database write error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{"status": "success", "message": "Telemetry reading stored successfully"})
}
