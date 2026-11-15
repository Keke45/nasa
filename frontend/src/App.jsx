
import { useEffect, useState } from "react";
import { checkServerHealth } from "./services/api";
import AstronautRegistration from "./admin/components/AstronautRegistration";
import AstronautRecords from "./admin/components/AstronautRecords";
import PersonnelDashboard from "./admin/components/PersonnelDashboard";
import CrewHealthMonitoring from "./admin/components/CrewHealthMonitoring";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);
  const [activePage, setActivePage] = useState("register");

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const data = await checkServerHealth();
        if (!cancelled) {
          setHealth(data);
        }
      } catch {
        if (!cancelled) {
          setHealth(null);
        }
      }
    }

    loadHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">A</div>

          <div>
            <h2>ASTRA</h2>
            <span>MISSION SYSTEM</span>
          </div>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-heading">PERSONNEL MANAGEMENT</p>

          <button
            className={`sidebar-link ${activePage === "dashboard" ? "active" : ""}`}
            onClick={() => setActivePage("dashboard")}
          >
            <span className="nav-icon">▦</span>
            <span>Dashboard</span>
          </button>

          <button
            className={`sidebar-link ${activePage === "register" ? "active" : ""}`}
            onClick={() => setActivePage("register")}
          >
            <span className="nav-icon">＋</span>
            <span>Register Astronaut</span>
          </button>

          <button
            className={`sidebar-link ${activePage === "records" ? "active" : ""}`}
            onClick={() => setActivePage("records")}
          >
            <span className="nav-icon">▤</span>
            <span>Astronaut Records</span>
          </button>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-heading">HEALTH MANAGEMENT</p>

          <button
            className={`sidebar-link ${activePage === "health" ? "active" : ""}`}
            onClick={() => setActivePage("health")}
          >
            <span className="nav-icon">♡</span>
            <span>Crew Health Monitoring</span>
          </button>
        </div>

        <div className="sidebar-footer">
          <div
            className={`connection-indicator ${health ? "connected" : "disconnected"}`}
          ></div>

          <div>
            <strong>System Status</strong>
            <span>
              {health ? "Server Connected" : "Connection Unavailable"}
            </span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activePage === "dashboard" && (
          <PersonnelDashboard onViewRecords={() => setActivePage("records")} />
        )}
        {activePage === "register" && <AstronautRegistration />}
        {activePage === "records" && <AstronautRecords />}
        {activePage === "health" && <CrewHealthMonitoring />}
      </main>
    </div>
  );
}

export default App;

