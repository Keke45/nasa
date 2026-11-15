package health

import (
    "errors"
    "time"
)

type HealthReading struct {
    ID               string    `json:"id"`
    AstronautID      string    `json:"astronaut_id"`
    HeartRate        int       `json:"heart_rate"`
    SystolicBP       int       `json:"systolic_bp"`
    DiastolicBP      int       `json:"diastolic_bp"`
    BodyTemp         float64   `json:"body_temperature"`
    OxygenSaturation float64   `json:"oxygen_saturation"`
    SleepDuration    float64   `json:"sleep_duration"`
    PhysicalActivity int       `json:"physical_activity"`
    FatigueLevel     int       `json:"fatigue_level"`
    Source           string    `json:"source"` // "manual" or "simulation"
    RecordedAt       time.Time `json:"recorded_at"`
}

func (r *HealthReading) Validate() error {
    if r.AstronautID == "" {
        return errors.New("astronaut_id is required")
    }
    if r.HeartRate < 30 || r.HeartRate > 220 {
        return errors.New("heart_rate out of realistic range (30-220 BPM)")
    }
    if r.OxygenSaturation < 50 || r.OxygenSaturation > 100 {
        return errors.New("oxygen_saturation must be between 50% and 100%")
    }
    if r.FatigueLevel < 1 || r.FatigueLevel > 10 {
        return errors.New("fatigue_level must be on scale 1-10")
    }
    if r.SleepDuration < 0 || r.SleepDuration > 24 {
        return errors.New("sleep_duration must be between 0 and 24 hours")
    }
    return nil
}
