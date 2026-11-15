import { useEffect, useState } from "react";
import { getAstronauts, getHealthProfiles } from "../../services/api";
import "../styles/crew-health-monitoring.css";

function CrewHealthMonitoring() {
  const [astronauts, setAstronauts] = useState([]);
  const [healthProfiles, setHealthProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchHealthData() {
      try {
        setLoading(true);
        setError("");

        const [astronautData, healthData] = await Promise.all([
          getAstronauts(),
          getHealthProfiles(),
        ]);

        setAstronauts(astronautData.astronauts || []);
        setHealthProfiles(healthData.health_profiles || []);
      } catch (err) {
        setError(err.message || "Unable to retrieve health information");
      } finally {
        setLoading(false);
      }
    }

    fetchHealthData();
  }, []);

  const totalAstronauts = astronauts.length;
  const totalProfiles = healthProfiles.length;

  const missingProfiles = Math.max(0, totalAstronauts - totalProfiles);

  const profileCoverage =
    totalAstronauts > 0
      ? Math.round((totalProfiles / totalAstronauts) * 100)
      : 0;

  function formatDate(date) {
    if (!date) return "—";

    return new Date(date.replace(" ", "T")).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  const overviewCards = [
    {
      title: "Health Profiles",
      value: totalProfiles,
      description: "Registered health profiles",
      icon: "♡",
    },
    {
      title: "Missing Profiles",
      value: missingProfiles,
      description: "Astronauts without profiles",
      icon: "⚑",
    },
    {
      title: "Profile Coverage",
      value: `${profileCoverage}%`,
      description: "Health profile completion",
      icon: "◉",
    },
  ];

  return (
    <div className="crew-health-monitoring">
      <header className="health-page-header">
        <div>
          <span className="dashboard-eyebrow">ASTRA / HEALTH MANAGEMENT</span>

          <h1>Crew Health Monitoring</h1>

          <p>
            Monitor astronaut health information and review recorded
            physiological measurements.
          </p>
        </div>
      </header>

      {error && (
        <div className="dashboard-error">
          Unable to load health information: {error}
        </div>
      )}

      {/* Health Overview */}
      <section className="health-overview">
        <div className="dashboard-section-heading">
          <div>
            <h2>Health Overview</h2>
            <p>Summary of astronaut health profile availability</p>
          </div>
        </div>

        <div className="health-overview-grid">
          {overviewCards.map((card) => (
            <div className="health-overview-card" key={card.title}>
              <div className="health-card-icon">{card.icon}</div>

              <div>
                <p>{card.title}</p>

                <h3>{loading || error ? "—" : card.value}</h3>

                <span>{card.description}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Health Records */}
      <section className="health-records-section">
        <div className="dashboard-section-heading">
          <div>
            <h2>Crew Health Records</h2>
            <p>Recorded physiological measurements</p>
          </div>
        </div>

        <div className="health-table-container">
          {loading ? (
            <div className="personnel-empty-state">
              Loading health records...
            </div>
          ) : error ? (
            <div className="personnel-empty-state">
              Unable to retrieve health records.
            </div>
          ) : healthProfiles.length === 0 ? (
            <div className="personnel-empty-state">
              No health profiles have been registered yet.
            </div>
          ) : (
            <table className="health-records-table">
              <thead>
                <tr>
                  <th>Astronaut</th>
                  <th>Heart Rate</th>
                  <th>Blood Pressure</th>
                  <th>Oxygen Saturation</th>
                  <th>Temperature</th>
                  <th>Last Updated</th>
                </tr>
              </thead>

              <tbody>
                {healthProfiles.map((profile) => (
                  <tr key={profile.id}>
                    <td className="health-astronaut-name">
                      <strong>{profile.full_name}</strong>
                      <span>{profile.astronaut_id}</span>
                    </td>

                    <td>{profile.resting_heart_rate} bpm</td>

                    <td>
                      {profile.systolic_bp}/{profile.diastolic_bp} mmHg
                    </td>

                    <td>{profile.oxygen_saturation}%</td>

                    <td>{profile.body_temperature} °C</td>

                    <td>{formatDate(profile.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

export default CrewHealthMonitoring;
