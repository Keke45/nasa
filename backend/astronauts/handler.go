package astronauts

import (
	"database/sql"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"strings"

	"astronaut-health-intelligence/intelligence"
)

type RegistrationResponse struct {
	Message          string `json:"message"`
	AstronautID      string `json:"astronaut_id"`
	ID               int64  `json:"id"`
	IntelligenceSync string `json:"intelligence_sync"`
}

func RegistrationHandler(
	db *sql.DB,
	intelligenceClients ...*intelligence.Client,
) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Limit request body size.
		r.Body = http.MaxBytesReader(w, r.Body, 1024*1024)

		// Decode JSON request.
		var request RegistrationRequest

		decoder := json.NewDecoder(r.Body)
		decoder.DisallowUnknownFields()

		if err := decoder.Decode(&request); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		// Reject additional JSON values.
		var extra interface{}
		if err := decoder.Decode(&extra); err != io.EOF {
			http.Error(w, "Request must contain only one JSON object", http.StatusBadRequest)
			return
		}

		// Validate request.
		if err := request.Validate(); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Register astronaut.
		id, err := Register(db, request)
		if err != nil {
			if strings.Contains(err.Error(), "UNIQUE constraint failed") {
				http.Error(w, "Astronaut ID or username already exists", http.StatusConflict)
				return
			}

			http.Error(w, "Astronaut registration failed", http.StatusInternalServerError)
			return
		}

		syncStatus := "not_configured"
		if len(intelligenceClients) > 0 && intelligenceClients[0] != nil {
			payload := intelligence.NewRegistrationPayload(
				request.Personal.AstronautID,
				intelligence.RegistrationHealth{
					RestingHeartRate: request.Health.RestingHeartRate,
					SystolicBP:       float64(request.Health.SystolicBP),
					DiastolicBP:      float64(request.Health.DiastolicBP),
					OxygenSaturation: request.Health.OxygenSaturation,
					BodyTemperature:  request.Health.BodyTemperature,
				},
			)

			if err := intelligenceClients[0].SyncRegistration(
				r.Context(),
				payload,
			); err != nil {
				log.Printf(
					"Intelligence registration sync failed for %s: %v",
					request.Personal.AstronautID,
					err,
				)
				syncStatus = "failed"
			} else {
				syncStatus = "synced"
			}
		}

		// Return success response.
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)

		json.NewEncoder(w).Encode(RegistrationResponse{
			Message:          "Astronaut registered successfully",
			AstronautID:      request.Personal.AstronautID,
			ID:               id,
			IntelligenceSync: syncStatus,
		})
	}
}
