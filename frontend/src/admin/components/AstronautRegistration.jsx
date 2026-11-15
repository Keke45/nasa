import { useState } from "react";
import { registerAstronaut } from "../../services/api";
import "../styles/registration.css";

function AstronautRegistration() {
  const [currentStep, setCurrentStep] = useState(1);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Keep all registration information in one shared state.
  const [formData, setFormData] = useState({
    personal: {
      astronaut_id: "",
      full_name: "",
      date_of_birth: "",
      nationality: "",
    },
    mission: {
      mission_name: "",
      mission_role: "",
      start_date: "",
      expected_return_date: "",
    },
    health: {
      height_cm: "",
      weight_kg: "",
      resting_heart_rate: "",
      systolic_bp: "",
      diastolic_bp: "",
      oxygen_saturation: "",
      body_temperature: "",
    },
    account: {
      username: "",
      initial_password: "",
    },
  });

  // Update the appropriate section of the form.
  function handleChange(section, e) {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [name]: value,
      },
    }));
  }

  // Move to the next step.
  async function handleSubmit(e) {
    e.preventDefault();

    // Steps 1 and 2 only move the user forward.
    if (currentStep < 3) {
      setCurrentStep((prev) => prev + 1);
      return;
    }

    // Step 3 submits the complete registration.
    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const payload = {
        ...formData,

        health: {
          height_cm: Number(formData.health.height_cm),
          weight_kg: Number(formData.health.weight_kg),
          resting_heart_rate: Number(formData.health.resting_heart_rate),
          systolic_bp: Number(formData.health.systolic_bp),
          diastolic_bp: Number(formData.health.diastolic_bp),
          oxygen_saturation: Number(formData.health.oxygen_saturation),
          body_temperature: Number(formData.health.body_temperature),
        },
      };

      const result = await registerAstronaut(payload);

      setSuccess(
        `Astronaut registered successfully! ID: ${result.astronaut_id}`,
      );

      console.log("Registration response:", result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  // Move to the previous step.
  function handleBack() {
    setCurrentStep((prev) => prev - 1);
  }

  return (
    <div className="registration-page">
      {/* Header */}
      <header className="registration-header">
        <div className="brand">
          <span className="brand-icon">✦</span>
          <span>ASTRA</span>
        </div>

        <div className="system-status">
          <span className="status-indicator"></span>
          System Operational
        </div>
      </header>

      <main className="registration-container">
        {/* Page heading */}
        <div className="registration-heading">
          <p className="eyebrow">CREW MANAGEMENT</p>
          <h1>Astronaut Registration</h1>
          <p>
            Register a new astronaut and establish their personal and mission
            profile.
          </p>
        </div>

        {/* Progress indicator */}
        <div className="progress-section">
          <div className={`progress-step ${currentStep >= 1 ? "active" : ""}`}>
            <span>{currentStep > 1 ? "✓" : "01"}</span>
            <div>
              <strong>Personal</strong>
              <small>Basic information</small>
            </div>
          </div>

          <div className="progress-line"></div>

          <div className={`progress-step ${currentStep >= 2 ? "active" : ""}`}>
            <span>{currentStep > 2 ? "✓" : "02"}</span>
            <div>
              <strong>Mission</strong>
              <small>Mission details</small>
            </div>
          </div>

          <div className="progress-line"></div>

          <div className={`progress-step ${currentStep >= 3 ? "active" : ""}`}>
            <span>03</span>
            <div>
              <strong>Health & Account</strong>
              <small>Baseline and access</small>
            </div>
          </div>
        </div>

        {/* Registration form */}
        <section className="form-card">
          <div className="form-heading">
            <div>
              <p className="section-label">STEP 0{currentStep}</p>

              <h2>
                {currentStep === 1
                  ? "Personal Information"
                  : currentStep === 2
                    ? "Mission Information"
                    : "Health & Account"}
              </h2>

              <p>
                {currentStep === 1
                  ? "Enter the astronaut's identification and personal details."
                  : currentStep === 2
                    ? "Provide the astronaut’s mission assignment details."
                    : "The next stage will collect health baselines and account details."}
              </p>
            </div>

            <span className="section-icon">
              {currentStep === 1 ? "♙" : currentStep === 2 ? "🚀" : "♡"}
            </span>
          </div>

          <form onSubmit={handleSubmit}>
            {/* STEP 1: PERSONAL INFORMATION */}
            {currentStep === 1 && (
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="astronaut_id">Astronaut ID</label>
                  <input
                    id="astronaut_id"
                    type="text"
                    name="astronaut_id"
                    placeholder="e.g. AST-001"
                    value={formData.personal.astronaut_id}
                    onChange={(e) => handleChange("personal", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="full_name">Full Name</label>
                  <input
                    id="full_name"
                    type="text"
                    name="full_name"
                    placeholder="Enter full name"
                    value={formData.personal.full_name}
                    onChange={(e) => handleChange("personal", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="date_of_birth">Date of Birth</label>
                  <input
                    id="date_of_birth"
                    type="date"
                    name="date_of_birth"
                    value={formData.personal.date_of_birth}
                    onChange={(e) => handleChange("personal", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="nationality">Nationality</label>
                  <input
                    id="nationality"
                    type="text"
                    name="nationality"
                    placeholder="Enter nationality"
                    value={formData.personal.nationality}
                    onChange={(e) => handleChange("personal", e)}
                  />
                </div>
              </div>
            )}

            {/* STEP 2: MISSION INFORMATION */}
            {currentStep === 2 && (
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="mission_name">Mission Name</label>
                  <input
                    id="mission_name"
                    type="text"
                    name="mission_name"
                    placeholder="e.g. Artemis Mission"
                    value={formData.mission.mission_name}
                    onChange={(e) => handleChange("mission", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="mission_role">Mission Role</label>
                  <input
                    id="mission_role"
                    type="text"
                    name="mission_role"
                    placeholder="e.g. Mission Specialist"
                    value={formData.mission.mission_role}
                    onChange={(e) => handleChange("mission", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="start_date">Mission Start Date</label>
                  <input
                    id="start_date"
                    type="date"
                    name="start_date"
                    value={formData.mission.start_date}
                    onChange={(e) => handleChange("mission", e)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="expected_return_date">
                    Expected Return Date
                  </label>
                  <input
                    id="expected_return_date"
                    type="date"
                    name="expected_return_date"
                    min={formData.mission.start_date || undefined}
                    value={formData.mission.expected_return_date}
                    onChange={(e) => handleChange("mission", e)}
                    required
                  />
                </div>
              </div>
            )}

            {/* STEP 3: HEALTH BASELINE & ACCOUNT */}
            {currentStep === 3 && (
              <>
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="height_cm">Height (cm)</label>
                    <input
                      id="height_cm"
                      type="number"
                      name="height_cm"
                      min="1"
                      max="300"
                      step="any"
                      placeholder="e.g. 175"
                      value={formData.health.height_cm}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="weight_kg">Weight (kg)</label>
                    <input
                      id="weight_kg"
                      type="number"
                      name="weight_kg"
                      min="1"
                      max="500"
                      step="any"
                      placeholder="e.g. 72"
                      value={formData.health.weight_kg}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="resting_heart_rate">
                      Resting Heart Rate (bpm)
                    </label>
                    <input
                      id="resting_heart_rate"
                      type="number"
                      name="resting_heart_rate"
                      min="1"
                      max="250"
                      placeholder="e.g. 70"
                      value={formData.health.resting_heart_rate}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="systolic_bp">
                      Systolic Blood Pressure (mmHg)
                    </label>
                    <input
                      id="systolic_bp"
                      type="number"
                      name="systolic_bp"
                      min="1"
                      max="300"
                      placeholder="e.g. 120"
                      value={formData.health.systolic_bp}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="diastolic_bp">
                      Diastolic Blood Pressure (mmHg)
                    </label>
                    <input
                      id="diastolic_bp"
                      type="number"
                      name="diastolic_bp"
                      min="1"
                      max="200"
                      placeholder="e.g. 80"
                      value={formData.health.diastolic_bp}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="oxygen_saturation">
                      Oxygen Saturation (%)
                    </label>
                    <input
                      id="oxygen_saturation"
                      type="number"
                      name="oxygen_saturation"
                      min="0"
                      max="100"
                      step="any"
                      placeholder="e.g. 98"
                      value={formData.health.oxygen_saturation}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="body_temperature">
                      Body Temperature (°C)
                    </label>
                    <input
                      id="body_temperature"
                      type="number"
                      name="body_temperature"
                      min="0.1"
                      max="50"
                      step="any"
                      placeholder="e.g. 36.8"
                      value={formData.health.body_temperature}
                      onChange={(e) => handleChange("health", e)}
                      required
                    />
                  </div>
                </div>

                <div className="form-divider">
                  <h3>Account Setup</h3>
                  <p>Create login credentials for the astronaut.</p>
                </div>

                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="username">Username</label>
                    <input
                      id="username"
                      type="text"
                      name="username"
                      placeholder="Choose a username"
                      value={formData.account.username}
                      onChange={(e) => handleChange("account", e)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="initial_password">Initial Password</label>
                    <input
                      id="initial_password"
                      type="password"
                      name="initial_password"
                      minLength="8"
                      placeholder="Minimum 8 characters"
                      value={formData.account.initial_password}
                      onChange={(e) => handleChange("account", e)}
                      required
                    />
                  </div>
                </div>
              </>
            )}

            {/* Navigation buttons */}
            <div className="form-actions">
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}

              {success && (
                <p className="form-success" role="status">
                  {success}
                </p>
              )}
              <span>Step {currentStep} of 3</span>

              <div className="navigation-buttons">
                {currentStep > 1 && (
                  <button
                    type="button"
                    className="back-button"
                    onClick={handleBack}
                  >
                    ← Back
                  </button>
                )}

                {currentStep < 3 ? (
                  <button type="submit" className="next-button">
                    Continue →
                  </button>
                ) : (
                  <button
                    type="submit"
                    className="next-button"
                    disabled={submitting}
                  >
                    {submitting ? "Registering..." : "Register Astronaut"}
                  </button>
                )}
              </div>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}

export default AstronautRegistration;
