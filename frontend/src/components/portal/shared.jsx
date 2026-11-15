import MetricTrendChart from '../MetricTrendChart'
import PortalIcon from './PortalIcon'
import {
  formatDate,
  formatMetric,
  formatNumber,
  formatRelativeTime,
  METRIC_META,
  SEVERITY_LABEL,
  statusClass,
} from '../../lib/format'
import {
  anomalyFor,
  assessmentFor,
  formatDelta,
  initialsFor,
  latestValue,
  trendFor,
} from '../../lib/portal'

const RANGE_OPTIONS = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 'all', label: 'All' },
]

const METRIC_ICONS = {
  heart_rate: 'health',
  oxygen_saturation: 'oxygen',
  sleep_duration: 'sleep',
  fatigue_level: 'fatigue',
  physical_activity: 'activity',
}

export function Avatar({ profile, size = 'medium' }) {
  const image = profile?.profile_picture

  return (
    <span className={`portal-avatar avatar-${size}`}>
      {image ? (
        <img src={image} alt="" />
      ) : (
        <span>{initialsFor(profile?.full_name)}</span>
      )}
    </span>
  )
}

export function StatusPill({ severity = 'NOT_EVALUATED', label }) {
  return (
    <span className={statusClass(severity)}>
      {label ?? SEVERITY_LABEL[severity] ?? severity}
    </span>
  )
}

export function Panel({ children, className = '', id }) {
  return (
    <section className={`panel portal-panel ${className}`} id={id}>
      {children}
    </section>
  )
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}) {
  return (
    <div className="portal-section-heading">
      <div>
        {eyebrow && <p className="portal-kicker">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && (
          <p className="section-note">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}

export function MeasurementCard({ metric, analysis }) {
  const meta = METRIC_META[metric] ?? { label: metric, unit: '' }
  const value = latestValue(analysis, metric)
  const assessment = assessmentFor(analysis, metric)
  const anomaly = assessment.anomaly

  return (
    <article className="measurement-card">
      <div className="measurement-top">
        <span className="measurement-icon">
          <PortalIcon name={METRIC_ICONS[metric] ?? 'activity'} />
        </span>
        <StatusPill
          severity={assessment.severity}
          label={assessment.label}
        />
      </div>
      <strong className="measurement-value">
        {formatMetric(value, meta.unit)}
      </strong>
      <span className="measurement-label">{meta.label}</span>
      {anomaly?.baseline_value !== null &&
        anomaly?.baseline_value !== undefined && (
          <span className="measurement-delta">
            {formatDelta(anomaly.difference, meta.unit)} vs baseline
          </span>
        )}
    </article>
  )
}

export function RangeTabs({ value, onChange }) {
  return (
    <div className="range-tabs" aria-label="Trend range">
      {RANGE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          className={option.value === value ? 'active' : ''}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export function TrendGrid({
  analysis,
  readings,
  metrics,
  rangeDays,
}) {
  return (
    <div className="portal-trend-grid">
      {metrics.map((metric) => {
        const meta = METRIC_META[metric] ?? {
          label: metric,
          unit: '',
        }
        const anomaly = anomalyFor(analysis, metric)
        const trend = trendFor(analysis, metric)
        const assessment = assessmentFor(analysis, metric)

        return (
          <article className="trend-chart-card" key={metric}>
            <div className="trend-chart-head">
              <div>
                <h3>{meta.label}</h3>
                <span className="section-note">
                  {trend?.direction
                    ? `Trend: ${trend.direction.toLowerCase()}`
                    : 'Measurement history'}
                </span>
              </div>
              <StatusPill
                severity={assessment.severity}
                label={assessment.label}
              />
            </div>

            <div className="trend-chart-values">
              <span>
                Latest{' '}
                <strong>
                  {formatMetric(
                    latestValue(analysis, metric),
                    meta.unit,
                  )}
                </strong>
              </span>
              <span>
                Baseline{' '}
                <strong>
                  {formatMetric(anomaly?.baseline_value, meta.unit)}
                </strong>
              </span>
            </div>

            <MetricTrendChart
              readings={readings}
              metric={metric}
              baselineValue={anomaly?.baseline_value ?? null}
              rangeDays={rangeDays}
            />
          </article>
        )
      })}
    </div>
  )
}

export function InsightCard({ insight }) {
  return (
    <article
      className={`insight-card severity-${String(
        insight.severity,
      ).toLowerCase()}`}
    >
      <div className="insight-head">
        <span className="insight-icon">
          <PortalIcon
            name={
              insight.severity === 'NORMAL'
                ? 'insights'
                : 'alert'
            }
          />
        </span>
        <div>
          <p className="portal-kicker">
            {insight.severity === 'NORMAL'
              ? 'Informational'
              : 'Health insight'}
          </p>
          <h3>{insight.title}</h3>
        </div>
        <StatusPill
          severity={insight.severity}
          label={SEVERITY_LABEL[insight.severity]}
        />
      </div>

      <p className="insight-observation">{insight.observation}</p>

      {insight.current_value !== null &&
        insight.current_value !== undefined && (
          <div className="insight-evidence">
            <span>
              Current{' '}
              <strong>
                {formatMetric(
                  insight.current_value,
                  insight.unit,
                )}
              </strong>
            </span>
            <span>
              Baseline{' '}
              <strong>
                {formatMetric(
                  insight.baseline_value,
                  insight.unit,
                )}
              </strong>
            </span>
            <span>
              Difference{' '}
              <strong>
                {formatDelta(insight.difference, insight.unit)}
              </strong>
            </span>
            <span>
              Z-score{' '}
              <strong>{formatNumber(insight.z_score, 2)}</strong>
            </span>
          </div>
        )}

      <div className="recommendation-box">
        <span className="portal-kicker">Recommendation</span>
        <p>{insight.recommendation}</p>
      </div>
    </article>
  )
}

const NOTIFICATION_ICONS = {
  Assessment: 'insights',
  'Health alert': 'alert',
  Sleep: 'sleep',
  Monitoring: 'activity',
  Message: 'message',
}

export function NotificationItem({ notification }) {
  return (
    <li className="notification-item">
      <span className="notification-icon">
        <PortalIcon
          name={NOTIFICATION_ICONS[notification.category] ?? 'alert'}
        />
      </span>
      <div className="notification-copy">
        <div className="notification-head">
          <span className="notification-category">
            {notification.category}
          </span>
          <span className="notification-time">
            {formatRelativeTime(notification.timestamp)}
          </span>
        </div>
        <strong>{notification.title}</strong>
        <p>{notification.body}</p>
      </div>
      {notification.unread && (
        <span className="unread-dot" aria-label="Unread" />
      )}
    </li>
  )
}

export function HistoryTable({ readings, limit = 12 }) {
  const recent = [...readings].reverse().slice(0, limit)

  if (recent.length === 0) {
    return (
      <EmptyState
        title="No measurements yet"
        description="Health readings will appear here once monitoring begins."
      />
    )
  }

  return (
    <div className="table-wrap">
      <table className="portal-history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Heart rate</th>
            <th>Oxygen</th>
            <th>Sleep</th>
            <th>Fatigue</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((reading) => (
            <tr key={reading.id}>
              <td>{formatDate(reading.recorded_at)}</td>
              <td>
                {formatMetric(
                  reading.heart_rate,
                  METRIC_META.heart_rate.unit,
                )}
              </td>
              <td>
                {formatMetric(
                  reading.oxygen_saturation,
                  METRIC_META.oxygen_saturation.unit,
                )}
              </td>
              <td>
                {formatMetric(
                  reading.sleep_duration,
                  METRIC_META.sleep_duration.unit,
                )}
              </td>
              <td>
                {formatMetric(
                  reading.fatigue_level,
                  METRIC_META.fatigue_level.unit,
                )}
              </td>
              <td>
                <span className={statusClass(reading.source)}>
                  {reading.source}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function EmptyState({ icon, title, description }) {
  return (
    <div className="portal-empty">
      {icon && (
        <span className="portal-empty-icon">
          <PortalIcon name={icon} />
        </span>
      )}
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </div>
  )
}

export function InfoNote({ children }) {
  return <p className="portal-info-note">{children}</p>
}
