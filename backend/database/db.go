package database

import (
    "database/sql"
    "log"

    _ "modernc.org/sqlite"
)

var DB *sql.DB

func InitDB() {
    var err error
    DB, err = sql.Open("sqlite", "./astronaut_health.db")
    if err != nil {
        log.Fatalf("Failed to connect to database: %v", err)
    }

    // Create HealthReadings table if it doesn't exist
    createTableQuery := `
    CREATE TABLE IF NOT EXISTS HealthReadings (
        id TEXT PRIMARY KEY,
        astronaut_id TEXT NOT NULL,
        heart_rate INTEGER NOT NULL,
        systolic_bp INTEGER NOT NULL,
        diastolic_bp INTEGER NOT NULL,
        body_temperature REAL NOT NULL,
        oxygen_saturation REAL NOT NULL,
        sleep_duration REAL NOT NULL,
        physical_activity INTEGER NOT NULL,
        fatigue_level INTEGER NOT NULL,
        source TEXT NOT NULL,
        recorded_at DATETIME NOT NULL
    );`

    _, err = DB.Exec(createTableQuery)
    if err != nil {
        log.Fatalf("Failed to create HealthReadings table: %v", err)
    }
}
