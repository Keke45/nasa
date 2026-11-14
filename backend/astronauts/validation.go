package astronauts

import (
	"fmt"
	"strings"
	"time"
)

func (r RegistrationRequest) Validate() error {

	// Personal information
	if strings.TrimSpace(r.Personal.AstronautID) == "" {
		return fmt.Errorf("astronaut ID is required")
	}

	if strings.TrimSpace(r.Personal.FullName) == "" {
		return fmt.Errorf("full name is required")
	}

	dob, err := time.Parse("2006-01-02", r.Personal.DateOfBirth)
	if err != nil || !dob.Before(time.Now()) {
		return fmt.Errorf("valid date of birth is required")
	}

	// Mission information
	if strings.TrimSpace(r.Mission.MissionName) == "" {
		return fmt.Errorf("mission name is required")
	}

	if strings.TrimSpace(r.Mission.MissionRole) == "" {
		return fmt.Errorf("mission role is required")
	}

	start, err := time.Parse("2006-01-02", r.Mission.StartDate)
	if err != nil {
		return fmt.Errorf("invalid mission start date")
	}

	end, err := time.Parse("2006-01-02", r.Mission.ExpectedReturnDate)
	if err != nil || !end.After(start) {
		return fmt.Errorf("expected return date must be after mission start date")
	}

	if !dob.Before(start) {
		return fmt.Errorf("date of birth must be before mission start date")
	}

	// Health information
	h := r.Health

	if h.HeightCM <= 0 || h.HeightCM > 300 {
		return fmt.Errorf("invalid height")
	}

	if h.WeightKG <= 0 || h.WeightKG > 500 {
		return fmt.Errorf("invalid weight")
	}

	if h.RestingHeartRate <= 0 || h.RestingHeartRate > 250 {
		return fmt.Errorf("invalid resting heart rate")
	}

	if h.SystolicBP <= 0 || h.SystolicBP > 300 {
		return fmt.Errorf("invalid systolic blood pressure")
	}

	if h.DiastolicBP <= 0 || h.DiastolicBP > 200 {
		return fmt.Errorf("invalid diastolic blood pressure")
	}

	if h.OxygenSaturation < 0 || h.OxygenSaturation > 100 {
		return fmt.Errorf("invalid oxygen saturation")
	}

	if h.BodyTemperature <= 0 || h.BodyTemperature > 50 {
		return fmt.Errorf("invalid body temperature")
	}

	// Account information
	if strings.TrimSpace(r.Account.Username) == "" {
		return fmt.Errorf("username is required")
	}

	if len(r.Account.InitialPassword) < 8 {
		return fmt.Errorf("password must contain at least 8 characters")
	}

	return nil
}
