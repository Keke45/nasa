package health

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

type HealthProfile struct {
	ID               int64   `json:"id"`
	AstronautID      string  `json:"astronaut_id"`
	FullName         string  `json:"full_name"`
	HeightCM         float64 `json:"height_cm"`
	WeightKG         float64 `json:"weight_kg"`
	RestingHeartRate float64 `json:"resting_heart_rate"`
	SystolicBP       int     `json:"systolic_bp"`
	DiastolicBP      int     `json:"diastolic_bp"`
	OxygenSaturation float64 `json:"oxygen_saturation"`
	BodyTemperature  float64 `json:"body_temperature"`
	UpdatedAt        string  `json:"updated_at"`
}

func ListHealthProfilesHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		rows, err := db.Query(`
			SELECT
				hp.id,
				a.astronaut_id,
				a.full_name,
				hp.height_cm,
				hp.weight_kg,
				hp.resting_heart_rate,
				hp.systolic_bp,
				hp.diastolic_bp,
				hp.oxygen_saturation,
				hp.body_temperature,
				hp.updated_at
			FROM health_profiles hp
			JOIN astronauts a ON hp.astronaut_id = a.id
			ORDER BY hp.updated_at DESC
		`)

		if err != nil {
			http.Error(w, "Failed to retrieve health profiles", http.StatusInternalServerError)
			return
		}

		defer rows.Close()

		profiles := make([]HealthProfile, 0)

		for rows.Next() {
			var profile HealthProfile

			err := rows.Scan(
				&profile.ID,
				&profile.AstronautID,
				&profile.FullName,
				&profile.HeightCM,
				&profile.WeightKG,
				&profile.RestingHeartRate,
				&profile.SystolicBP,
				&profile.DiastolicBP,
				&profile.OxygenSaturation,
				&profile.BodyTemperature,
				&profile.UpdatedAt,
			)

			if err != nil {
				http.Error(w, "Failed to process health profiles", http.StatusInternalServerError)
				return
			}

			profiles = append(profiles, profile)
		}

		if err := rows.Err(); err != nil {
			http.Error(w, "Failed to read health profiles", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")

		json.NewEncoder(w).Encode(map[string]interface{}{
			"health_profiles": profiles,
		})
	}
}
