package health

import (
    "math/rand"
    "time"
)

func GenerateSimulatedReading(astronautID string, scenario string) HealthReading {
    rand.Seed(time.Now().UnixNano())
    
    hr := 65 + rand.Intn(10)
    sleep := 7.5 + (rand.Float64() * 1.0)
    fatigue := 2 + rand.Intn(2)

    if scenario == "physiological_strain" {
        hr = 85 + rand.Intn(12)
        sleep = 4.5 + (rand.Float64() * 0.5)
        fatigue = 8 + rand.Intn(2)
    }

    return HealthReading{
        ID:               time.Now().Format("20060102150405") + "-sim",
        AstronautID:      astronautID,
        HeartRate:        hr,
        SystolicBP:       120 + rand.Intn(10),
        DiastolicBP:      80 + rand.Intn(8),
        BodyTemp:         36.6 + (rand.Float64() * 0.4),
        OxygenSaturation: 97.0 + (rand.Float64() * 2.5),
        SleepDuration:    sleep,
        PhysicalActivity: 30 + rand.Intn(20),
        FatigueLevel:     fatigue,
        Source:           "simulation",
        RecordedAt:       time.Now(),
    }
}
