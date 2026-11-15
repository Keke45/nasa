import { useMemo, useState } from 'react'
import {
  formatDate,
  formatMetric,
  formatNumber,
  SEVERITY_LABEL,
  statusClass,
} from '../lib/format'

function displayName(astronautId, directory) {
  return directory[astronautId]?.full_name || astronautId
}

function missionLabel(astronautId, directory) {
  const entry = directory[astronautId]
  return [entry?.mission_role, entry?.mission_name]
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

function AlertCard({ alert, directory, onSelectAstronaut }) {
  const mission = missionLabel(alert.astronaut_id, directory)

  return (
    <article
      className={`alert-card severity-${String(
        alert.severity,
      ).toLowerCase()}`}
    >
      <div className="alert-card-head">
        <div>
          <p className="eyebrow">Health insight</p>
          <h3>
            {displayName(alert.astronaut_id, directory)} ·{' '}
            {alert.metric_label}
          </h3>
          <span className="table-note">
            {alert.astronaut_id}
            {mission ? ` · ${mission}` : ''}
          </span>
        </div>
        <div className="alert-badges">
          <span className={statusClass(alert.severity)}>
            {SEVERITY_LABEL[alert.severity] ?? alert.severity}
          </span>
          <span className={statusClass(alert.status)}>
            {alert.status}
          </span>
        </div>
      </div>

      <p className="observation">{alert.observation}</p>

      <div className="evidence-grid">
        <div>
          <span>Current</span>
          <strong>
            {formatMetric(alert.current_value, alert.unit)}
          </strong>
        </div>
        <div>
          <span>Personal baseline</span>
          <strong>
            {formatMetric(alert.baseline_value, alert.unit)}
          </strong>
        </div>
        <div>
          <span>Difference</span>
          <strong>
            {formatMetric(alert.difference, alert.unit)}
          </strong>
        </div>
        <div>
          <span>Z-score</span>
          <strong>{formatNumber(alert.z_score, 2)}</strong>
        </div>
        <div>
          <span>Direction</span>
          <strong>{alert.direction ?? '—'}</strong>
        </div>
      </div>

      {alert.contributing_factors?.length > 0 && (
        <>
          <span className="detail-label">Contributing factors</span>
          <ul className="factor-list">
            {alert.contributing_factors.map((factor) => (
              <li key={factor}>{factor}</li>
            ))}
          </ul>
        </>
      )}

      <div className="alert-recommendations">
        <span className="detail-label">Recommended actions</span>
        {alert.recommended_actions?.length > 0 ? (
          <ul className="recommendation-list">
            {alert.recommended_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        ) : (
          <p className="section-note">
            No recommendations are attached to this finding yet.
          </p>
        )}
      </div>

      <div className="alert-actions">
        <span className="table-note">
          Baseline {alert.baseline_status ?? 'unknown'}
          {alert.baseline_version
            ? ` · v${alert.baseline_version}`
            : ''}{' '}
          · Reading {formatDate(alert.recorded_at)}
        </span>
        <button
          className="secondary-button"
          type="button"
          onClick={() => onSelectAstronaut(alert.astronaut_id)}
        >
          View astronaut
        </button>
      </div>
    </article>
  )
}

export default function AlertsView({
  overview,
  directory,
  onSelectAstronaut,
}) {
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [query, setQuery] = useState('')

  const alerts = useMemo(
    () => overview?.alerts ?? [],
    [overview],
  )

  const summary = useMemo(() => {
    const astronauts = new Set(
      alerts.map((alert) => alert.astronaut_id),
    )

    return {
      total: alerts.length,
      severe: alerts.filter(
        (alert) => alert.severity === 'SEVERE',
      ).length,
      anomaly: alerts.filter(
        (alert) => alert.severity === 'ANOMALY',
      ).length,
      watch: alerts.filter(
        (alert) => alert.severity === 'WATCH',
      ).length,
      astronauts: astronauts.size,
    }
  }, [alerts])

  const filteredAlerts = useMemo(() => {
    const needle = query.trim().toLowerCase()

    return alerts.filter((alert) => {
      if (
        severityFilter !== 'ALL' &&
        alert.severity !== severityFilter
      ) {
        return false
      }

      if (!needle) {
        return true
      }

      const haystack = [
        alert.astronaut_id,
        displayName(alert.astronaut_id, directory),
        alert.metric_label,
        alert.observation,
      ]
        .join(' ')
        .toLowerCase()

      return haystack.includes(needle)
    })
  }, [alerts, directory, query, severityFilter])

  if (!overview) {
    return (
      <section className="panel placeholder">
        Loading alerts and insights…
      </section>
    )
  }

  return (
    <>
      <section className="summary-grid dashboard-summary">
        <SummaryCard
          label="Active findings"
          value={summary.total}
          note="Derived from the latest reading"
          tone="warn"
        />
        <SummaryCard
          label="Severe findings"
          value={summary.severe}
          note="Immediate review recommended"
          tone="alert"
        />
        <SummaryCard
          label="Watch and anomaly"
          value={summary.anomaly + summary.watch}
          note="Monitor or review"
          tone="neutral"
        />
        <SummaryCard
          label="Astronauts affected"
          value={summary.astronauts}
          note="At least one finding"
          tone="neutral"
        />
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Alerts and insights</h2>
            <p className="section-note">
              Each finding explains the measurement, the personal
              baseline and the factors that contributed to it. Status
              reflects the latest analysis; acknowledgement tracking is
              not stored yet.
            </p>
          </div>
          <span className="last-updated">
            {filteredAlerts.length} of {alerts.length} shown
          </span>
        </div>

        <div className="table-controls">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by astronaut or metric"
            aria-label="Search alerts"
          />
          <select
            value={severityFilter}
            onChange={(event) =>
              setSeverityFilter(event.target.value)
            }
            aria-label="Filter alerts by severity"
          >
            <option value="ALL">All severities</option>
            <option value="SEVERE">Severe</option>
            <option value="ANOMALY">Anomaly</option>
            <option value="WATCH">Watch</option>
          </select>
        </div>

        {filteredAlerts.length === 0 ? (
          <p className="empty-state">
            No findings match the current filters. The latest readings
            are within personalised thresholds.
          </p>
        ) : (
          <div className="alert-stream">
            {filteredAlerts.map((alert) => (
              <AlertCard
                key={`${alert.astronaut_id}-${alert.metric}`}
                alert={alert}
                directory={directory}
                onSelectAstronaut={onSelectAstronaut}
              />
            ))}
          </div>
        )}
      </section>
    </>
  )
}
