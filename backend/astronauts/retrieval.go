package astronauts

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

type AstronautSummary struct {
	ID          int64  `json:"id"`
	AstronautID string `json:"astronaut_id"`
	FullName    string `json:"full_name"`
	DateOfBirth string `json:"date_of_birth"`
	Nationality string `json:"nationality"`
	CreatedAt   string `json:"created_at"`
}

func ListAstronautsHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		rows, err := db.Query(`
			SELECT id, astronaut_id, full_name, date_of_birth, nationality, created_at
			FROM astronauts
			ORDER BY created_at DESC
		`)
		if err != nil {
			http.Error(w, "Failed to retrieve astronauts", http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		astronauts := make([]AstronautSummary, 0)

		for rows.Next() {
			var astronaut AstronautSummary

			err := rows.Scan(
				&astronaut.ID,
				&astronaut.AstronautID,
				&astronaut.FullName,
				&astronaut.DateOfBirth,
				&astronaut.Nationality,
				&astronaut.CreatedAt,
			)
			if err != nil {
				http.Error(w, "Failed to process astronaut records", http.StatusInternalServerError)
				return
			}

			astronauts = append(astronauts, astronaut)
		}

		if err := rows.Err(); err != nil {
			http.Error(w, "Failed to read astronaut records", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"astronauts": astronauts,
		})
	}
}