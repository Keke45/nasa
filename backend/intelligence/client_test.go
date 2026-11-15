package intelligence

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func testPayload() RegistrationPayload {
	return NewRegistrationPayload("AST-001", RegistrationHealth{
		RestingHeartRate: 65,
		SystolicBP:       120,
		DiastolicBP:      80,
		OxygenSaturation: 98,
		BodyTemperature:  36.8,
	})
}

func TestSyncRegistration(t *testing.T) {
	var method, path, token, contentType string
	var body RegistrationPayload

	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			method = r.Method
			path = r.URL.Path
			token = r.Header.Get("X-Ingest-Token")
			contentType = r.Header.Get("Content-Type")

			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				t.Errorf("decode request: %v", err)
			}

			w.WriteHeader(http.StatusCreated)
			w.Write([]byte(`{"created": true}`))
		},
	))
	defer server.Close()

	client := NewClient(server.URL, "secret-token", server.Client())

	if err := client.SyncRegistration(
		context.Background(),
		testPayload(),
	); err != nil {
		t.Fatalf("SyncRegistration failed: %v", err)
	}

	if method != http.MethodPost {
		t.Fatalf("expected POST, got %s", method)
	}
	if path != "/api/registrations" {
		t.Fatalf("unexpected path: %s", path)
	}
	if token != "secret-token" {
		t.Fatalf("unexpected ingest token: %s", token)
	}
	if contentType != "application/json" {
		t.Fatalf("unexpected content type: %s", contentType)
	}
	if body.Personal.AstronautID != "AST-001" {
		t.Fatalf("unexpected astronaut ID: %s", body.Personal.AstronautID)
	}
	if body.Health.RestingHeartRate != 65 {
		t.Fatalf("unexpected heart rate: %v", body.Health.RestingHeartRate)
	}
}

func TestSyncRegistrationRejectsErrorStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, "invalid health metric", http.StatusBadRequest)
		},
	))
	defer server.Close()

	client := NewClient(server.URL, "", server.Client())

	err := client.SyncRegistration(context.Background(), testPayload())
	if err == nil {
		t.Fatal("expected an error for a non-2xx response")
	}

	message := err.Error()
	if !strings.Contains(message, "400") {
		t.Fatalf("expected status code in error, got: %s", message)
	}
	if !strings.Contains(message, "invalid health metric") {
		t.Fatalf("expected response detail in error, got: %s", message)
	}
}

func TestNewClientDefaults(t *testing.T) {
	client := NewClient("", "", nil)

	if client.BaseURL != defaultBaseURL {
		t.Fatalf("unexpected default base URL: %s", client.BaseURL)
	}
	if client.HTTPClient == nil || client.HTTPClient.Timeout == 0 {
		t.Fatal("expected an HTTP client with a timeout")
	}
}

func TestRegistrationPayloadExcludesSecrets(t *testing.T) {
	body, err := json.Marshal(testPayload())
	if err != nil {
		t.Fatal(err)
	}

	for _, forbidden := range []string{
		"username",
		"password",
		"account",
		"full_name",
		"mission",
	} {
		if strings.Contains(string(body), forbidden) {
			t.Fatalf("payload unexpectedly contains %q: %s", forbidden, body)
		}
	}
}

func TestSyncRegistrationDrainsBody(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			io.Copy(io.Discard, r.Body)
			w.WriteHeader(http.StatusOK)
			w.Write([]byte(`{"ok": true}`))
		},
	))
	defer server.Close()

	client := NewClient(server.URL, "", server.Client())
	if err := client.SyncRegistration(
		context.Background(),
		testPayload(),
	); err != nil {
		t.Fatalf("SyncRegistration failed: %v", err)
	}
}
