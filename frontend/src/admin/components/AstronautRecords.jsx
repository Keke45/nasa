import { useEffect, useMemo, useState } from "react";
import { getAstronauts } from "../../services/api";
import "./astronaut-records.css";

function AstronautRecords() {
  const [astronauts, setAstronauts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // New: search and filter states
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNationality, setSelectedNationality] = useState("");

  async function fetchAstronauts() {
    setLoading(true);
    setError("");

    try {
      const data = await getAstronauts();
      setAstronauts(data.astronauts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAstronauts();
  }, []);

  // Get unique nationalities for the filter dropdown
  const nationalities = useMemo(() => {
    return [
      ...new Set(
        astronauts
          .map((astronaut) => astronaut.nationality?.trim())
          .filter(Boolean),
      ),
    ].sort();
  }, [astronauts]);

  // Apply search and nationality filtering
  const filteredAstronauts = useMemo(() => {
    return astronauts.filter((astronaut) => {
      const search = searchTerm.toLowerCase().trim();

      const matchesSearch =
        astronaut.full_name?.toLowerCase().includes(search) ||
        astronaut.astronaut_id?.toLowerCase().includes(search);

      const matchesNationality =
        !selectedNationality || astronaut.nationality === selectedNationality;

      return matchesSearch && matchesNationality;
    });
  }, [astronauts, searchTerm, selectedNationality]);

  // Reset search and filter
  function clearFilters() {
    setSearchTerm("");
    setSelectedNationality("");
  }

  const hasActiveFilters = searchTerm !== "" || selectedNationality !== "";

  return (
    <div className="records-page">
      <div className="records-header">
        <div>
          <p className="records-label">PERSONNEL MANAGEMENT</p>
          <h1>Astronaut Records</h1>
          <p className="records-description">
            View and manage registered astronaut information.
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={fetchAstronauts}
          disabled={loading}
        >
          {loading ? "Loading..." : "↻ Refresh Records"}
        </button>
      </div>

      <div className="records-summary">
        <div className="summary-card">
          <span>Total Registered Astronauts</span>
          <h2>{astronauts.length}</h2>
        </div>
      </div>

      <div className="records-table-container">
        <div className="table-heading">
          <h2>Registered Astronauts</h2>
          <span>{astronauts.length} Records</span>
        </div>

        {/* New: Search and filter controls */}
        <div className="records-filters">
          <div className="search-container">
            <label htmlFor="astronaut-search">Search Astronauts</label>

            <div className="search-input-wrapper">
              <span className="search-icon">⌕</span>

              <input
                id="astronaut-search"
                type="text"
                placeholder="Search by name or astronaut ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="nationality-filter">
            <label htmlFor="nationality-filter">Filter by Nationality</label>

            <select
              id="nationality-filter"
              value={selectedNationality}
              onChange={(e) => setSelectedNationality(e.target.value)}
            >
              <option value="">All Nationalities</option>

              {nationalities.map((nationality) => (
                <option key={nationality} value={nationality}>
                  {nationality}
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button className="clear-filters-button" onClick={clearFilters}>
              Clear Filters
            </button>
          )}
        </div>

        {loading ? (
          <div className="records-message">Loading astronaut records...</div>
        ) : error ? (
          <div className="records-error">{error}</div>
        ) : astronauts.length === 0 ? (
          <div className="records-message">
            No astronauts have been registered yet.
          </div>
        ) : filteredAstronauts.length === 0 ? (
          <div className="records-message">
            No astronauts match your search or filter.
          </div>
        ) : (
          <div className="table-scroll">
            <table className="astronaut-table">
              <thead>
                <tr>
                  <th>Astronaut ID</th>
                  <th>Full Name</th>
                  <th>Date of Birth</th>
                  <th>Nationality</th>
                  <th>Registration Date</th>
                </tr>
              </thead>

              <tbody>
                {filteredAstronauts.map((astronaut) => (
                  <tr key={astronaut.id}>
                    <td className="astronaut-id">{astronaut.astronaut_id}</td>
                    <td>{astronaut.full_name}</td>
                    <td>{astronaut.date_of_birth}</td>
                    <td>{astronaut.nationality}</td>
                    <td>
                      {astronaut.created_at
                        ? new Date(astronaut.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default AstronautRecords;
