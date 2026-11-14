package astronauts

import (
	"database/sql"
	"os"
	"testing"

	"astronaut-health-intelligence/database"

	"golang.org/x/crypto/bcrypt"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()

	oldDir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}

	tempDir := t.TempDir()

	if err := os.Chdir(tempDir); err != nil {
		t.Fatal(err)
	}

	t.Cleanup(func() {
		os.Chdir(oldDir)
	})

	db, err := database.Initialize()
	if err != nil {
		t.Fatalf("Database initialization failed: %v", err)
	}

	t.Cleanup(func() {
		db.Close()
	})

	return db
}

func validRegistration() RegistrationRequest {
	return RegistrationRequest{
		Personal: PersonalInfo{
			AstronautID: "AST-001",
			FullName:    "Alex Morgan",
			DateOfBirth: "1995-04-12",
			Nationality: "American",
		},
		Mission: MissionInfo{
			MissionName:        "Artemis",
			MissionRole:        "Mission Specialist",
			StartDate:          "2026-12-01",
			ExpectedReturnDate: "2027-06-01",
		},
		Health: HealthInfo{
			HeightCM:         175,
			WeightKG:         72,
			RestingHeartRate: 65,
			SystolicBP:       120,
			DiastolicBP:      80,
			OxygenSaturation: 98,
			BodyTemperature:  36.8,
		},
		Account: AccountInfo{
			Username:        "alex",
			InitialPassword: "password123",
		},
	}
}

func TestRegisterAstronaut(t *testing.T) {
	db := setupTestDB(t)

	request := validRegistration()

	astronautID, err := Register(db, request)
	if err != nil {
		t.Fatalf("Registration failed: %v", err)
	}

	// Verify astronaut record.
	var fullName string

	err = db.QueryRow(
		"SELECT full_name FROM astronauts WHERE id = ?",
		astronautID,
	).Scan(&fullName)

	if err != nil || fullName != "Alex Morgan" {
		t.Fatalf("Astronaut record verification failed")
	}

	// Verify mission record.
	var missionName string

	err = db.QueryRow(
		"SELECT mission_name FROM missions WHERE astronaut_id = ?",
		astronautID,
	).Scan(&missionName)

	if err != nil || missionName != "Artemis" {
		t.Fatalf("Mission record verification failed")
	}

	// Verify health profile.
	var heartRate float64

	err = db.QueryRow(
		"SELECT resting_heart_rate FROM health_profiles WHERE astronaut_id = ?",
		astronautID,
	).Scan(&heartRate)

	if err != nil || heartRate != 65 {
		t.Fatalf("Health profile verification failed")
	}

	// Verify password hash.
	var passwordHash string

	err = db.QueryRow(
		"SELECT password_hash FROM users WHERE username = ?",
		"alex",
	).Scan(&passwordHash)

	if err != nil {
		t.Fatalf("Account verification failed: %v", err)
	}

	if passwordHash == request.Account.InitialPassword {
		t.Fatal("Password was stored as plain text")
	}

	if err := bcrypt.CompareHashAndPassword(
		[]byte(passwordHash),
		[]byte(request.Account.InitialPassword),
	); err != nil {
		t.Fatal("Password hash verification failed")
	}

	t.Log("All four registration records verified successfully")
}

func TestRegisterRollback(t *testing.T) {
	db := setupTestDB(t)

	// First registration succeeds.
	first := validRegistration()

	_, err := Register(db, first)
	if err != nil {
		t.Fatalf("Initial registration failed: %v", err)
	}

	// Second registration uses a duplicate username.
	second := validRegistration()
	second.Personal.AstronautID = "AST-002"
	second.Account.Username = "alex"

	_, err = Register(db, second)

	if err == nil {
		t.Fatal("Expected registration to fail due to duplicate username")
	}

	// Verify that the second astronaut was not saved.
	var count int

	err = db.QueryRow(
		"SELECT COUNT(*) FROM astronauts WHERE astronaut_id = ?",
		"AST-002",
	).Scan(&count)

	if err != nil {
		t.Fatal(err)
	}

	if count != 0 {
		t.Fatal("Transaction rollback failed: incomplete astronaut record exists")
	}

	t.Log("Transaction rollback verified successfully")
}
