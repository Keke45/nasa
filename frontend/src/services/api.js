const API_BASE_URL = "/api";

export async function checkServerHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("Unable to connect to the backend");
  }

  return response.json();
}
