package astronauts

import (
	"database/sql"
	"encoding/json"
	"io"
	"net/http"
	"strings"
)

type RegistrationResponse struct {
	Message     string `json:"message"`
	AstronautID string `json:"astronaut_id"`
	ID          int64  `json:"id"`
}

func RegistrationHandler(db *sql.DB) http.HandlerFunc {
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

		// Return success response.
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)

		json.NewEncoder(w).Encode(RegistrationResponse{
			Message:     "Astronaut registered successfully",
			AstronautID: request.Personal.AstronautID,
			ID:          id,
		})
	}
}
