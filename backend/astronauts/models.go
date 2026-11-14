package astronauts

type RegistrationRequest struct {
	Personal PersonalInfo `json:"personal"`
	Mission  MissionInfo  `json:"mission"`
	Health   HealthInfo   `json:"health"`
	Account  AccountInfo  `json:"account"`
}

type PersonalInfo struct {
	AstronautID string `json:"astronaut_id"`
	FullName    string `json:"full_name"`
	DateOfBirth string `json:"date_of_birth"`
	Nationality string `json:"nationality"`
}

type MissionInfo struct {
	MissionName        string `json:"mission_name"`
	MissionRole        string `json:"mission_role"`
	StartDate          string `json:"start_date"`
	ExpectedReturnDate string `json:"expected_return_date"`
}

type HealthInfo struct {
	HeightCM         float64 `json:"height_cm"`
	WeightKG         float64 `json:"weight_kg"`
	RestingHeartRate float64 `json:"resting_heart_rate"`
	SystolicBP       int     `json:"systolic_bp"`
	DiastolicBP      int     `json:"diastolic_bp"`
	OxygenSaturation float64 `json:"oxygen_saturation"`
	BodyTemperature  float64 `json:"body_temperature"`
}

type AccountInfo struct {
	Username        string `json:"username"`
	InitialPassword string `json:"initial_password"`
}