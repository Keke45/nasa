package astronauts

import "testing"

func TestRegistrationValidation(t *testing.T) {

	validRequest := RegistrationRequest{
		Personal: PersonalInfo{
			AstronautID: "AST-001",
			FullName:    "Alex Morgan",
			DateOfBirth: "1995-04-12",
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

	t.Run("Valid registration", func(t *testing.T) {
		if err := validRequest.Validate(); err != nil {
			t.Fatalf("Expected valid registration, got error: %v", err)
		}
	})

	t.Run("Missing astronaut ID", func(t *testing.T) {
		request := validRequest
		request.Personal.AstronautID = ""

		if err := request.Validate(); err == nil {
			t.Fatal("Expected validation error for missing astronaut ID")
		}
	})

	t.Run("Invalid oxygen saturation", func(t *testing.T) {
		request := validRequest
		request.Health.OxygenSaturation = 150

		if err := request.Validate(); err == nil {
			t.Fatal("Expected validation error for invalid oxygen saturation")
		}
	})

	t.Run("Invalid mission dates", func(t *testing.T) {
		request := validRequest
		request.Mission.ExpectedReturnDate = "2026-11-01"

		if err := request.Validate(); err == nil {
			t.Fatal("Expected validation error for invalid mission dates")
		}
	})
}
