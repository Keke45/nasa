package database

import (
	"database/sql"
	"os"

	_ "modernc.org/sqlite"
)

func Initialize() (*sql.DB, error) {
	if err := os.MkdirAll("data", 0755); err != nil {
		return nil, err
	}

	db, err := sql.Open("sqlite", "./data/astronaut_health.db")
	if err != nil {
		return nil, err
	}

	// Keep one connection so SQLite connection-level settings
	// remain consistent.
	db.SetMaxOpenConns(1)

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}

	// Enable foreign key enforcement.
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		db.Close()
		return nil, err
	}

	if err := createTables(db); err != nil {
		db.Close()
		return nil, err
	}

	return db, nil
}

func createTables(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS astronauts (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		astronaut_id TEXT NOT NULL UNIQUE,
		full_name TEXT NOT NULL,
		date_of_birth TEXT NOT NULL,
		nationality TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS missions (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		astronaut_id INTEGER NOT NULL UNIQUE,
		mission_name TEXT NOT NULL,
		mission_role TEXT NOT NULL,
		start_date TEXT NOT NULL,
		expected_return_date TEXT NOT NULL,

		FOREIGN KEY (astronaut_id)
			REFERENCES astronauts(id)
			ON DELETE CASCADE
	);

	CREATE TABLE IF NOT EXISTS health_profiles (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		astronaut_id INTEGER NOT NULL UNIQUE,
		height_cm REAL NOT NULL CHECK(height_cm > 0),
		weight_kg REAL NOT NULL CHECK(weight_kg > 0),
		resting_heart_rate REAL NOT NULL CHECK(resting_heart_rate > 0),
		systolic_bp INTEGER NOT NULL CHECK(systolic_bp > 0),
		diastolic_bp INTEGER NOT NULL CHECK(diastolic_bp > 0),
		oxygen_saturation REAL NOT NULL CHECK(
			oxygen_saturation >= 0 AND oxygen_saturation <= 100
		),
		body_temperature REAL NOT NULL CHECK(body_temperature > 0),
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

		FOREIGN KEY (astronaut_id)
			REFERENCES astronauts(id)
			ON DELETE CASCADE
	);

	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT NOT NULL UNIQUE,
		password_hash TEXT NOT NULL,
		role TEXT NOT NULL CHECK(
			role IN ('PERSONNEL', 'ASTRONAUT')
		),
		astronaut_id INTEGER UNIQUE,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

		FOREIGN KEY (astronaut_id)
			REFERENCES astronauts(id)
			ON DELETE CASCADE,

		CHECK (
			(role = 'PERSONNEL' AND astronaut_id IS NULL)
			OR
			(role = 'ASTRONAUT' AND astronaut_id IS NOT NULL)
		)
	);
	`

	_, err := db.Exec(schema)
	return err
}