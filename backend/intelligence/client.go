package intelligence

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const defaultBaseURL = "http://localhost:8000"

// Registration health values forwarded to the intelligence backend.
type RegistrationHealth struct {
	RestingHeartRate float64 `json:"resting_heart_rate"`
	SystolicBP       float64 `json:"systolic_bp"`
	DiastolicBP      float64 `json:"diastolic_bp"`
	OxygenSaturation float64 `json:"oxygen_saturation"`
	BodyTemperature  float64 `json:"body_temperature"`
}

// RegistrationPayload deliberately excludes account and mission details.
type RegistrationPayload struct {
	Personal struct {
		AstronautID string `json:"astronaut_id"`
	} `json:"personal"`
	Health RegistrationHealth `json:"health"`
}

func NewRegistrationPayload(
	astronautID string,
	health RegistrationHealth,
) RegistrationPayload {
	var payload RegistrationPayload
	payload.Personal.AstronautID = astronautID
	payload.Health = health
	return payload
}

type Client struct {
	BaseURL    string
	Token      string
	HTTPClient *http.Client
}

func NewClient(baseURL, token string, httpClient *http.Client) *Client {
	if strings.TrimSpace(baseURL) == "" {
		baseURL = defaultBaseURL
	}
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 5 * time.Second}
	}

	return &Client{
		BaseURL:    strings.TrimRight(baseURL, "/"),
		Token:      token,
		HTTPClient: httpClient,
	}
}

func NewClientFromEnv() *Client {
	return NewClient(
		os.Getenv("INTELLIGENCE_BASE_URL"),
		os.Getenv("INTELLIGENCE_INGEST_TOKEN"),
		nil,
	)
}

func (c *Client) SyncRegistration(
	ctx context.Context,
	payload RegistrationPayload,
) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("encode intelligence registration: %w", err)
	}

	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.BaseURL+"/api/registrations",
		bytes.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("create intelligence registration request: %w", err)
	}

	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Accept", "application/json")
	if c.Token != "" {
		request.Header.Set("X-Ingest-Token", c.Token)
	}

	response, err := c.HTTPClient.Do(request)
	if err != nil {
		return fmt.Errorf("send intelligence registration: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK ||
		response.StatusCode >= http.StatusMultipleChoices {
		detail, _ := io.ReadAll(io.LimitReader(response.Body, 512))
		return fmt.Errorf(
			"intelligence registration returned %d: %s",
			response.StatusCode,
			strings.TrimSpace(string(detail)),
		)
	}

	io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
	return nil
}
