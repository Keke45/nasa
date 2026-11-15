import { useEffect, useState } from "react";
import { getAstronauts, getHealthProfiles } from "../../services/api";
import "../styles/personnel-dashboard.css";

function PersonnelDashboard({ onViewRecords }) {
  const [astronauts, setAstronauts] = useState([]);
  const [healthProfiles, setHealthProfiles] = useState([]);
  const [totalAstronauts, setTotalAstronauts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        setLoading(true);
        setError("");

        const [astronautData, healthData] = await Promise.all([
          getAstronauts(),
          getHealthProfiles(),
        ]);

        const astronautRecords = astronautData.astronauts || [];
        const profileRecords = healthData.health_profiles || [];

        setAstronauts(astronautRecords);
        setHealthProfiles(profileRecords);
        setTotalAstronauts(astronautRecords.length);
      } catch (err) {
        setError(err.message || "Unable to retrieve dashboard information");
      } finally {
        setLoading(false);
      }
    }

    fetchDashboardData();
  }, []);

  const totalProfiles = healthProfiles.length;

  const missingProfiles = Math.max(0, (totalAstronauts ?? 0) - totalProfiles);

  const profileCoverage =
    totalAstronauts > 0
      ? Math.round((totalProfiles / totalAstronauts) * 100)
      : 0;

  const overviewCards = [
    {
      title: "Total Astronauts",
      value: loading ? "..." : error ? "—" : totalAstronauts,
      description: "Registered personnel",
      icon: "♙",
      type: "primary",
      status: error ? "Unavailable" : "Live data",
    },
    {
      title: "Health Profiles",
      value: loading ? "..." : error ? "—" : totalProfiles,
      description: "Registered health profiles",
      icon: "♡",
      type: "secondary",
      status: error ? "Unavailable" : "Live data",
    },
    {
      title: "Missing Profiles",
      value: loading ? "..." : error ? "—" : missingProfiles,
      description: "Astronauts without profiles",
      icon: "⚑",
      type: "secondary",
      status: error ? "Unavailable" : "Live data",
    },
    {
      title: "Profile Coverage",
      value: loading ? "..." : error ? "—" : `${profileCoverage}%`,
      description: "Health profile completion",
      icon: "◉",
      type: "secondary",
      status: error ? "Unavailable" : "Live data",
    },
  ];

  return (
    <div className="personnel-dashboard">
      {/* Dashboard Header */}
      <header className="dashboard-header">
        <div>
          <span className="dashboard-eyebrow">
            ASTRA / PERSONNEL MANAGEMENT
          </span>

          <h1>Personnel Dashboard</h1>

          <p>
            Overview of astronaut personnel, mission operations and crew
            wellbeing.
          </p>
        </div>

        <div className="dashboard-date">
          <span> SYSTEM OVERVIEW </span>
          <strong>
            {new Date().toLocaleDateString("en-GB", {
              day: "2-digit",
              month: "long",
              year: "numeric",
            })}
          </strong>
        </div>
      </header>

      {/* Error Message */}
      {error && (
        <div className="dashboard-error">
          Unable to load astronaut statistics: {error}
        </div>
      )}

      {/* Overview Cards */}
      <section className="dashboard-overview">
        <div className="dashboard-section-heading">
          <div>
            <h2>System Overview</h2>
            <p>Key personnel and operational indicators</p>
          </div>
        </div>

        <div className="overview-grid">
          {overviewCards.map((card, index) => (
            <div className={`overview-card ${card.type}`} key={index}>
              <div className="overview-card-top">
                <div className="overview-icon">{card.icon}</div>

                <span className="overview-status">{card.status}</span>
              </div>

              <div className="overview-card-content">
                <p>{card.title}</p>

                <h3>{card.value}</h3>

                <span>{card.description}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Personnel Overview */}
        <section className="personnel-overview-section">
          <div className="dashboard-section-heading">
            <div>
              <h2>Personnel Overview</h2>
              <p>Recently registered astronauts</p>
            </div>

            <button className="view-all-button" onClick={onViewRecords}>
              View All Records →
            </button>
          </div>

          <div className="personnel-table-container">
            {loading ? (
              <div className="personnel-empty-state">
                Loading astronaut records...
              </div>
            ) : error ? (
              <div className="personnel-empty-state">
                Unable to retrieve astronaut records.
              </div>
            ) : astronauts.length === 0 ? (
              <div className="personnel-empty-state">
                No astronauts have been registered yet.
              </div>
            ) : (
              <table className="personnel-table">
                <thead>
                  <tr>
                    <th>Astronaut</th>
                    <th>Astronaut ID</th>
                    <th>Nationality</th>
                    <th>Registration Date</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {astronauts.slice(0, 5).map((astronaut) => (
                    <tr key={astronaut.id}>
                      <td className="personnel-name">
                        <strong>{astronaut.full_name}</strong>
                      </td>

                      <td>{astronaut.astronaut_id}</td>

                      <td>{astronaut.nationality || "Not specified"}</td>

                      <td>
                        {astronaut.created_at
                          ? new Date(astronaut.created_at).toLocaleDateString(
                              "en-GB",
                              {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                              },
                            )
                          : "—"}
                      </td>

                      <td>
                        <button
                          className="personnel-view-button"
                          onClick={onViewRecords}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </section>
    </div>
  );
}

export default PersonnelDashboard;
