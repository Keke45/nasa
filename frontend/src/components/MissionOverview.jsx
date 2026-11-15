import { useMemo, useState } from 'react'
import {
  formatDate,
  formatRelativeTime,
  SEVERITIES,
  SEVERITY_LABEL,
  severityRank,
  statusClass,
} from '../lib/format'

function displayName(astronautId, directory) {
  return directory[astronautId]?.full_name || astronautId
}

function missionLabel(astronautId, directory) {
  const entry = directory[astronautId]
  const parts = [entry?.mission_role, entry?.mission_name].filter(Boolean)
  return parts.join(' · ')
}

function identityNote(astronautId, directory) {
  const name = displayName(astronautId, directory)

  return [
    name !== astronautId ? astronautId : '',
    missionLabel(astronautId, directory),
  ]
    .filter(Boolean)
    .join(' · ')
}

function SummaryCard({ label, value, note, tone }) {
  return (
    <article className={`summary-card summary-${tone}`}>
      <span className="summary-label">{label}</span>
      <strong>{value}</strong>
      <span className="summary-note">{note}</span>
    </article>
  )
}

export default function MissionOverview({
  overview,
  directory,
  loading,
  error,
  onSelectAstronaut,
  onViewAlerts,
  onRefresh,
}) {
  const [query, setQuery] = useState('')
  const [severityFilter, setSeverityFilter] = useState('ALL')

  const summary = overview?.summary
  const astronauts = useMemo(
    () => overview?.astronauts ?? [],
    [overview],
  )
  const alerts = overview?.alerts ?? []

  const filteredAstronauts = useMemo(() => {
    const needle = query.trim().toLowerCase()

    return [...astronauts]
      .filter((entry) => {
        if (
          severityFilter !== 'ALL' &&
          entry.severity !== severityFilter
        ) {
          return false
        }

        if (!needle) {
          return true
        }

        const haystack = [
          entry.astronaut_id,
          displayName(entry.astronaut_id, directory),
          missionLabel(entry.astronaut_id, directory),
        ]
          .join(' ')
          .toLowerCase()

        return haystack.includes(needle)
      })
      .sort((left, right) => {
        const rank =
          severityRank(left.severity) - severityRank(right.severity)

        if (rank !== 0) {
          return rank
        }

        return String(left.astronaut_id).localeCompare(
          String(right.astronaut_id),
        )
      })
  }, [astronauts, directory, query, severityFilter])

  const topFindings = alerts.slice(0, 4)
  const severityCounts = summary?.severity_counts ?? {}

  if (error && !overview) {
    return (
      <section className="alert alert-error">
        <strong>Mission overview unavailable.</strong> {error}
        {onRefresh && (
          <button
            className="inline-button"
            type="button"
            onClick={onRefresh}
          >
            Try again
          </button>
        )}
      </section>
    )
  }

  if (loading && !overview) {
    return (
      <section className="panel placeholder">
        Loading mission overview…
      </section>
    )
  }

  return (
    <>
      {error && (
        <section className="alert alert-error">
          <strong>Refresh failed.</strong> Showing the last known data.
          {error}
        </section>
      )}

      <section className="summary-grid dashboard-summary">
        <SummaryCard
          label="Registered astronauts"
          value={summary?.total_astronauts ?? 0}
          note="Astronauts with a health record"
          tone="neutral"
        />
        <SummaryCard
          label="Currently monitored"
          value={summary?.monitored ?? 0}
          note="Receiving health measurements"
          tone="neutral"
        />
        <SummaryCard
          label="Active alerts"
          value={summary?.active_alerts ?? 0}
          note="Rule-based findings on latest readings"
          tone="warn"
        />
        <SummaryCard
          label="Requiring attention"
          value={summary?.requiring_attention ?? 0}
          note="Astronauts with review flags"
          tone="alert"
        />
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Mission health profile</h2>
            <p className="section-note">
              Distribution of the highest severity per astronaut.
            </p>
          </div>
          <span className="last-updated">
            Last reading {formatRelativeTime(summary?.last_reading_at)}
          </span>
        </div>

        <div className="severity-bar" aria-hidden="true">
          {SEVERITIES.map((severity) =>
            severityCounts[severity] ? (
              <span
                key={severity}
                className={`sev-${severity.toLowerCase()}`}
                style={{ flex: severityCounts[severity] }}
                title={`${SEVERITY_LABEL[severity]}: ${
                  severityCounts[severity]
                }`}
              />
            ) : null,
          )}
        </div>

        <div className="severity-legend">
          {SEVERITIES.map((severity) => (
            <span key={severity}>
              <span
                className={`severity-dot sev-${severity.toLowerCase()}`}
              />
              {SEVERITY_LABEL[severity]} ·{' '}
              {severityCounts[severity] ?? 0}
            </span>
          ))}
        </div>
      </section>

      <div className="mission-layout">
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Astronaut overview</h2>
              <p className="section-note">
                Sorted by attention level, then astronaut ID.
              </p>
            </div>
            <span className="last-updated">
              {filteredAstronauts.length} shown
            </span>
          </div>

          <div className="table-controls">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by name, ID or mission"
              aria-label="Search astronauts"
            />
            <select
              value={severityFilter}
              onChange={(event) =>
                setSeverityFilter(event.target.value)
              }
              aria-label="Filter by severity"
            >
              <option value="ALL">All severities</option>
              {SEVERITIES.map((severity) => (
                <option key={severity} value={severity}>
                  {SEVERITY_LABEL[severity]}
                </option>
              ))}
            </select>
          </div>

          {filteredAstronauts.length === 0 ? (
            <p className="empty-state">
              No astronauts match the current filters.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Astronaut</th>
                    <th>Status</th>
                    <th>Alerts</th>
                    <th>ML model</th>
                    <th>Last reading</th>
                    <th>Freshness</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filteredAstronauts.map((entry) => (
                    <tr key={entry.astronaut_id}>
                      <td>
                        <strong>
                          {displayName(
                            entry.astronaut_id,
                            directory,
                          )}
                        </strong>
                        {identityNote(
                          entry.astronaut_id,
                          directory,
                        ) && (
                          <span className="table-note">
                            {identityNote(
                              entry.astronaut_id,
                              directory,
                            )}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={statusClass(entry.severity)}>
                          {SEVERITY_LABEL[entry.severity] ??
                            entry.severity}
                        </span>
                        {entry.requires_review && (
                          <span className="table-note">
                            Review recommended
                          </span>
                        )}
                      </td>
                      <td>{entry.alert_count}</td>
                      <td>
                        <span className={statusClass(entry.ml_status)}>
                          {entry.ml_status}
                        </span>
                      </td>
                      <td>
                        {formatDate(entry.last_reading_at)}
                        <span className="table-note">
                          {entry.reading_count} readings
                        </span>
                      </td>
                      <td>
                        {formatRelativeTime(entry.last_reading_at)}
                      </td>
                      <td>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() =>
                            onSelectAstronaut(entry.astronaut_id)
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel findings-panel">
          <div className="section-heading">
            <div>
              <h2>Latest findings</h2>
              <p className="section-note">
                Observations from the latest analysed reading.
              </p>
            </div>
            <button
              className="link-button"
              type="button"
              onClick={onViewAlerts}
            >
              View all
            </button>
          </div>

          {topFindings.length === 0 ? (
            <p className="empty-state">No active findings.</p>
          ) : (
            <ul className="findings-list">
              {topFindings.map((alert) => (
                <li key={`${alert.astronaut_id}-${alert.metric}`}>
                  <button
                    className="finding-item"
                    type="button"
                    onClick={() =>
                      onSelectAstronaut(alert.astronaut_id)
                    }
                  >
                    <span className="finding-top">
                      <span className="finding-id">
                        {displayName(
                          alert.astronaut_id,
                          directory,
                        )}
                      </span>
                      <span className={statusClass(alert.severity)}>
                        {alert.severity}
                      </span>
                    </span>
                    <span className="finding-text">
                      {alert.observation}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  )
}
