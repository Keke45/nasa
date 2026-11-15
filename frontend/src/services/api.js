const API_BASE_URL = "/api";

export async function checkServerHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("Unable to connect to the backend");
  }

  return response.json();
}

// Register a new astronaut.
export async function registerAstronaut(formData) {
  const response = await fetch(`${API_BASE_URL}/astronauts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(formData)
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error || data.message || "Registration failed"
    );
  }

  return data;
}

// Retrieve all registered astronauts.
export async function getAstronauts() {
  const response = await fetch(`${API_BASE_URL}/astronauts`);

  if (!response.ok) {
    throw new Error("Unable to retrieve astronaut records");
  }

  return response.json();
}

// Retrieve all registered astronaut health profiles.
export async function getHealthProfiles() {
  const response = await fetch(`${API_BASE_URL}/health-profiles`);

  if (!response.ok) {
    throw new Error("Unable to retrieve health profiles");
  }

  return response.json();
}