import { useEffect, useState } from 'react'
import { checkServerHealth, getAnalysis } from './services/api'
import './App.css'

const INITIAL_ASTRONAUT_ID = 'AST-001'

const METRIC_META = {
  heart_rate: { label: 'Heart rate', unit: 'bpm' },
  systolic_bp: { label: 'Systolic blood pressure', unit: 'mmHg' },
  diastolic_bp: { label: 'Diastolic blood pressure', unit: 'mmHg' },
  body_temperature: { label: 'Body temperature', unit: 'C' },
  oxygen_saturation: { label: 'Oxygen saturation', unit: '%' },
  sleep_duration: { label: 'Sleep duration', unit: 'hours' },
  physical_activity: { label: 'Physical activity', unit: 'minutes/day' },
  fatigue_level: { label: 'Fatigue level', unit: 'score (1-10)' },
}

const SEVERITY_ORDER = {
  SEVERE: 0,
  ANOMALY: 1,
  WATCH: 2,
  NORMAL: 3,
  NOT_EVALUATED: 4,
}

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—'
  }

  return Number(value).toFixed(digits)
}

function formatMetric(value, unit) {
  if (value === null || value === undefined) {
    return '—'
  }

  const digits = Math.abs(value) >= 10 ? 1 : 2
  return `${formatNumber(value, digits)}${unit ? ` ${unit}` : ''}`
}

function formatDate(value) {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function statusClass(status) {
  return `status-badge status-${String(status).toLowerCase()}`
}

function App() {
  const [astronautId, setAstronautId] = useState(INITIAL_ASTRONAUT_ID)
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [analysisError, setAnalysisError] = useState('')
  const [loading, setLoading] = useState(true)

  async function runAnalysis(id) {
    setLoading(true)
    setAnalysisError('')

    try {
      const data = await getAnalysis(id)
      setAnalysis(data)
      setAstronautId(id)
    } catch (error) {
      setAnalysis(null)
      setAnalysisError(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true

    async function loadHealth() {
      try {
        const data = await checkServerHealth()
        if (active) {
          setHealth(data)
        }
      } catch (error) {
        if (active) {
          setHealthError(error.message)
        }
      }
    }

    async function loadInitialAnalysis() {
      try {
        const data = await getAnalysis(INITIAL_ASTRONAUT_ID)
        if (active) {
          setAnalysis(data)
        }
      } catch (error) {
        if (active) {
          setAnalysisError(error.message)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadHealth()
    loadInitialAnalysis()

    return () => {
      active = false
    }
  }, [])

  function handleSubmit(event) {
    event.preventDefault()
    const nextId = astronautId.trim()

    if (nextId) {
      runAnalysis(nextId)
    }
  }

  const summary = analysis?.summary
  const baseline = analysis?.baseline
  const ml = analysis?.ml_anomaly
  const anomalies = analysis
    ? [...analysis.anomalies].sort(
        (left, right) =>
          (SEVERITY_ORDER[left.severity] ?? 9) -
          (SEVERITY_ORDER[right.severity] ?? 9),
      )
    : []

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Mission Health Intelligence</p>
          <h1>Astronaut Health Intelligence</h1>
          <p className="subtitle">
            Personal baselines, rule-based alerts, trend analysis and
            per-astronaut machine learning.
          </p>
        </div>

        <div className={healthError ? 'connection bad' : 'connection good'}>
          <span className="connection-dot" />
          <span>
            {healthError
              ? healthError
              : health
                ? `API ${health.status} · Database ${health.database}`
                : 'Checking API…'}
          </span>
        </div>
      </header>

      <section className="panel controls">
        <form onSubmit={handleSubmit}>
          <label htmlFor="astronaut-id">Astronaut ID</label>
          <div className="control-row">
            <input
              id="astronaut-id"
              value={astronautId}
              onChange={(event) => setAstronautId(event.target.value)}
              placeholder="AST-001"
              autoComplete="off"
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Analysing…' : 'Analyse health'}
            </button>
          </div>
        </form>
        <p className="hint">
          Uses the latest recorded reading and the current RECENT baseline.
        </p>
      </section>

      {analysisError && (
        <section className="alert alert-error">
          <strong>Analysis unavailable.</strong> {analysisError}
        </section>
      )}

      {loading && !analysis && (
        <section className="panel placeholder">Loading analysis…</section>
      )}

      {analysis && (
        <>
          {summary.requires_review && (
            <section className="alert alert-review">
              <strong>Review recommended.</strong> The latest reading exceeds
              at least one personalised threshold or is flagged by the ML
              model.
            </section>
          )}

          <section className="summary-grid">
            <article className="summary-card">
              <span className="summary-label">Astronaut</span>
              <strong>{analysis.astronaut_id}</strong>
              <span className="summary-note">
                Reading {analysis.reading.id} ·{' '}
                {formatDate(analysis.reading.recorded_at)}
              </span>
            </article>

            <article className="summary-card">
              <span className="summary-label">Baseline</span>
              <strong>
                {baseline.version ? `Version ${baseline.version}` : 'None'}
              </strong>
              <span className="summary-note">
                {baseline.usable_count}/{baseline.metric_count} usable ·{' '}
                {baseline.window_days} day window
              </span>
            </article>

            <article className="summary-card">
              <span className="summary-label">Rule alerts</span>
              <strong>{summary.anomaly.alert_count}</strong>
              <span className="summary-note">
                Highest severity: {summary.anomaly.highest_severity}
              </span>
            </article>

            <article className="summary-card">
              <span className="summary-label">ML anomaly model</span>
              <strong>{ml.status}</strong>
              <span className="summary-note">
                {ml.anomaly_score === null
                  ? 'No score available'
                  : `Score ${formatNumber(ml.anomaly_score, 3)}`}
              </span>
            </article>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Current reading</h2>
                <p className="section-note">
                  Source: {analysis.reading.source} ·{' '}
                  {formatDate(analysis.reading.recorded_at)}
                </p>
              </div>
              <span className={statusClass(analysis.reading.source)}>
                {analysis.reading.source}
              </span>
            </div>

            <div className="metric-grid">
              {Object.entries(analysis.reading.values).map(
                ([metric, value]) => {
                  const meta = METRIC_META[metric] ?? {
                    label: metric,
                    unit: '',
                  }
                  return (
                    <article className="metric-card" key={metric}>
                      <span>{meta.label}</span>
                      <strong>{formatMetric(value, meta.unit)}</strong>
                    </article>
                  )
                },
              )}
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Anomaly flags</h2>
                <p className="section-note">
                  Personal Z-scores against the current baseline.
                </p>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Severity</th>
                    <th>Current</th>
                    <th>Baseline</th>
                    <th>Z-score</th>
                    <th>Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((item) => (
                    <tr key={item.metric}>
                      <td>
                        <strong>{item.metric_label}</strong>
                        {item.outside_observed_range && (
                          <span className="table-note">
                            Outside observed range
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={statusClass(item.severity)}>
                          {item.severity}
                        </span>
                      </td>
                      <td>{formatMetric(item.current_value, item.unit)}</td>
                      <td>{formatMetric(item.baseline_value, item.unit)}</td>
                      <td>
                        {item.z_score === null
                          ? '—'
                          : formatNumber(item.z_score, 2)}
                      </td>
                      <td>{item.direction ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>Trends</h2>
                <p className="section-note">
                  Calendar-time regression with 7-day projections.
                </p>
              </div>
            </div>

            <div className="trend-grid">
              {Object.values(analysis.trends).map((trend) => (
                <article className="trend-card" key={trend.metric}>
                  <div className="trend-heading">
                    <strong>{trend.metric_label}</strong>
                    <span className={statusClass(trend.direction)}>
                      {trend.direction}
                    </span>
                  </div>
                  <dl>
                    <div>
                      <dt>Slope / week</dt>
                      <dd>
                        {formatNumber(trend.slope_per_week, 2)} {trend.unit}
                      </dd>
                    </div>
                    <div>
                      <dt>R²</dt>
                      <dd>{formatNumber(trend.r_squared, 2)}</dd>
                    </div>
                    <div>
                      <dt>7-day projection</dt>
                      <dd>
                        {formatMetric(trend.projected_value, trend.unit)}
                      </dd>
                    </div>
                  </dl>
                  {!trend.reliable && trend.direction === 'STABLE' && (
                    <p className="trend-note">Weak model fit.</p>
                  )}
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>ML anomaly model</h2>
                <p className="section-note">
                  Personal Isolation Forest trained on this astronaut's
                  readings.
                </p>
              </div>
              <span className={statusClass(ml.status)}>{ml.status}</span>
            </div>

            <div className="ml-grid">
              <div>
                <span className="detail-label">Anomaly score</span>
                <strong>
                  {ml.anomaly_score === null
                    ? '—'
                    : formatNumber(ml.anomaly_score, 3)}
                </strong>
              </div>
              <div>
                <span className="detail-label">Decision score</span>
                <strong>
                  {ml.decision_score === null
                    ? '—'
                    : formatNumber(ml.decision_score, 3)}
                </strong>
              </div>
              <div>
                <span className="detail-label">Training samples</span>
                <strong>{ml.model?.sample_count ?? '—'}</strong>
              </div>
              <div>
                <span className="detail-label">In sample</span>
                <strong>{ml.in_sample ? 'Yes' : 'No'}</strong>
              </div>
            </div>

            {ml.reason && <p className="section-note">{ml.reason}</p>}

            {ml.top_deviating_metrics?.length > 0 && (
              <div className="deviation-list">
                {ml.top_deviating_metrics.map((item) => (
                  <article key={item.metric}>
                    <span>{item.metric_label}</span>
                    <strong>{formatMetric(item.value, item.unit)}</strong>
                    <span>
                      Z {formatNumber(item.z_score, 2)}
                    </span>
                  </article>
                ))}
              </div>
            )}
          </section>

          {analysis.warnings.length > 0 && (
            <section className="panel warnings">
              <h2>Warnings</h2>
              <ul>
                {analysis.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  )
}

export default App
