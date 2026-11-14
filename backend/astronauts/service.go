package astronauts

import (
	"database/sql"
	"fmt"

	"golang.org/x/crypto/bcrypt"
)

func Register(db *sql.DB, request RegistrationRequest) (int64, error) {

	// 1. Validate registration information.
	if err := request.Validate(); err != nil {
		return 0, err
	}

	// 2. Hash the initial password.
	passwordHash, err := bcrypt.GenerateFromPassword(
		[]byte(request.Account.InitialPassword),
		bcrypt.DefaultCost,
	)
	if err != nil {
		return 0, fmt.Errorf("password hashing failed: %w", err)
	}

	// 3. Begin database transaction.
	tx, err := db.Begin()
	if err != nil {
		return 0, fmt.Errorf("could not begin transaction: %w", err)
	}

	// Roll back automatically if the transaction hasn't committed.
	defer tx.Rollback()

	// 4. Insert astronaut.
	result, err := tx.Exec(`
		INSERT INTO astronauts (
			astronaut_id,
			full_name,
			date_of_birth,
			nationality
		)
		VALUES (?, ?, ?, ?)
	`,
		request.Personal.AstronautID,
		request.Personal.FullName,
		request.Personal.DateOfBirth,
		request.Personal.Nationality,
	)

	if err != nil {
		return 0, fmt.Errorf("astronaut insertion failed: %w", err)
	}

	astronautID, err := result.LastInsertId()
	if err != nil {
		return 0, fmt.Errorf("could not retrieve astronaut ID: %w", err)
	}

	// 5. Insert mission information.
	_, err = tx.Exec(`
		INSERT INTO missions (
			astronaut_id,
			mission_name,
			mission_role,
			start_date,
			expected_return_date
		)
		VALUES (?, ?, ?, ?, ?)
	`,
		astronautID,
		request.Mission.MissionName,
		request.Mission.MissionRole,
		request.Mission.StartDate,
		request.Mission.ExpectedReturnDate,
	)

	if err != nil {
		return 0, fmt.Errorf("mission insertion failed: %w", err)
	}

	// 6. Insert health baseline.
	_, err = tx.Exec(`
		INSERT INTO health_profiles (
			astronaut_id,
			height_cm,
			weight_kg,
			resting_heart_rate,
			systolic_bp,
			diastolic_bp,
			oxygen_saturation,
			body_temperature
		)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`,
		astronautID,
		request.Health.HeightCM,
		request.Health.WeightKG,
		request.Health.RestingHeartRate,
		request.Health.SystolicBP,
		request.Health.DiastolicBP,
		request.Health.OxygenSaturation,
		request.Health.BodyTemperature,
	)

	if err != nil {
		return 0, fmt.Errorf("health profile insertion failed: %w", err)
	}

	// 7. Create astronaut login account.
	_, err = tx.Exec(`
		INSERT INTO users (
			username,
			password_hash,
			role,
			astronaut_id
		)
		VALUES (?, ?, 'ASTRONAUT', ?)
	`,
		request.Account.Username,
		string(passwordHash),
		astronautID,
	)

	if err != nil {
		return 0, fmt.Errorf("account creation failed: %w", err)
	}

	// 8. Commit transaction.
	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("transaction commit failed: %w", err)
	}

	return astronautID, nil
}
