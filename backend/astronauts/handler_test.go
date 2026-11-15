package astronauts

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"astronaut-health-intelligence/intelligence"
)

func registrationRequestJSON(t *testing.T) []byte {
	t.Helper()

	body, err := json.Marshal(validRegistration())
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func serveRegistration(
	t *testing.T,
	db *sql.DB,
	client *intelligence.Client,
	body []byte,
) *httptest.ResponseRecorder {
	t.Helper()

	request := httptest.NewRequest(
		http.MethodPost,
		"/api/astronauts",
		bytes.NewReader(body),
	)
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	RegistrationHandler(
		db,
		client,
	).ServeHTTP(recorder, request)

	return recorder
}

func TestRegistrationHandlerSyncsIntelligence(t *testing.T) {
	db := setupTestDB(t)

	var captured map[string]any
	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			if r.Method != http.MethodPost {
				t.Errorf("unexpected method: %s", r.Method)
			}
			if r.URL.Path != "/api/registrations" {
				t.Errorf("unexpected path: %s", r.URL.Path)
			}
			if err := json.NewDecoder(r.Body).Decode(&captured); err != nil {
				t.Errorf("decode payload: %v", err)
			}
			w.WriteHeader(http.StatusCreated)
			w.Write([]byte(`{"created": true}`))
		},
	))
	defer server.Close()

	recorder := serveRegistration(
		t,
		db,
		intelligence.NewClient(server.URL, "", server.Client()),
		registrationRequestJSON(t),
	)

	if recorder.Code != http.StatusCreated {
		t.Fatalf(
			"expected 201, got %d: %s",
			recorder.Code,
			recorder.Body.String(),
		)
	}

	var response RegistrationResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if response.IntelligenceSync != "synced" {
		t.Fatalf(
			"expected synced status, got %q",
			response.IntelligenceSync,
		)
	}

	personal := captured["personal"].(map[string]any)
	if personal["astronaut_id"] != "AST-001" {
		t.Fatalf("unexpected personal payload: %v", personal)
	}

	health := captured["health"].(map[string]any)
	if health["resting_heart_rate"] != float64(65) {
		t.Fatalf("unexpected health payload: %v", health)
	}
	for _, forbidden := range []string{"account", "mission"} {
		if _, exists := captured[forbidden]; exists {
			t.Fatalf("payload unexpectedly contains %q", forbidden)
		}
	}
}

func TestRegistrationHandlerSurvivesIntelligenceFailure(t *testing.T) {
	db := setupTestDB(t)

	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, "service unavailable", http.StatusServiceUnavailable)
		},
	))
	defer server.Close()

	recorder := serveRegistration(
		t,
		db,
		intelligence.NewClient(server.URL, "", server.Client()),
		registrationRequestJSON(t),
	)

	if recorder.Code != http.StatusCreated {
		t.Fatalf(
			"expected registration to succeed, got %d: %s",
			recorder.Code,
			recorder.Body.String(),
		)
	}

	var response RegistrationResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if response.IntelligenceSync != "failed" {
		t.Fatalf(
			"expected failed sync status, got %q",
			response.IntelligenceSync,
		)
	}

	var count int
	if err := db.QueryRow(
		"SELECT COUNT(*) FROM astronauts WHERE astronaut_id = ?",
		"AST-001",
	).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("expected astronaut to be saved, found %d rows", count)
	}
}

func TestRegistrationHandlerWithoutIntelligenceClient(t *testing.T) {
	db := setupTestDB(t)

	request := httptest.NewRequest(
		http.MethodPost,
		"/api/astronauts",
		bytes.NewReader(registrationRequestJSON(t)),
	)
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	RegistrationHandler(db).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d", recorder.Code)
	}

	var response RegistrationResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if response.IntelligenceSync != "not_configured" {
		t.Fatalf(
			"unexpected sync status: %q",
			response.IntelligenceSync,
		)
	}
}
