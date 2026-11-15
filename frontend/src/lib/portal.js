import {
  formatDate,
  formatMetric,
  METRIC_META,
  severityRank,
} from './format'

export const PORTAL_ASTRONAUT_ID =
  import.meta.env.VITE_PORTAL_ASTRONAUT_ID || 'AST-001'

export const KEY_METRICS = [
  'heart_rate',
  'oxygen_saturation',
  'sleep_duration',
  'fatigue_level',
]

export const TREND_METRICS = KEY_METRICS

const DAY_MS = 24 * 60 * 60 * 1000

const PROFILE_FALLBACKS = {
  'AST-001': {
    full_name: 'Alex',
    mission_name: 'Artemis Mission',
    mission_role: 'Mission Specialist',
  },
}

const STATUS_COPY = {
  SEVERE: {
    label: 'Needs attention',
    description:
      'One or more measurements need review by mission medical personnel.',
  },
  ANOMALY: {
    label: 'Review advised',
    description:
      'Your latest measurements differ from your personal baseline.',
  },
  WATCH: {
    label: 'Monitor',
    description:
      'Some measurements are outside your usual range and should be watched.',
  },
  NORMAL: {
    label: 'Stable',
    description:
      'Your latest measurements are within your personal baselines.',
  },
  NOT_EVALUATED: {
    label: 'Awaiting assessment',
    description:
      'There is not enough evaluated data for a health assessment yet.',
  },
}

const RECOMMENDATIONS = {
  heart_rate: {
    ABOVE:
      'Rest, hydrate and repeat the measurement. Avoid strenuous activity until your heart rate returns toward your baseline.',
    BELOW:
      'Rest and repeat the measurement. Tell mission medical personnel if you feel dizzy or unusually tired.',
    DEFAULT:
      'Continue monitoring your heart rate and mention any palpitations or dizziness to mission medical personnel.',
  },
  oxygen_saturation: {
    BELOW:
      'Sit down, rest and repeat the measurement. Contact mission medical personnel promptly if the low reading persists.',
    DEFAULT:
      'Continue monitoring your oxygen saturation and report any breathlessness to mission medical personnel.',
  },
  sleep_duration: {
    BELOW:
      'Follow your assigned sleep and recovery schedule. Reduce non-essential tasks before your next sleep period.',
    ABOVE:
      'Keep your sleep and wake times consistent with your mission schedule and mention any unusual drowsiness to mission medical personnel.',
    DEFAULT:
      'Maintain your assigned sleep and recovery schedule and report persistent sleep changes.',
  },
  fatigue_level: {
    ABOVE:
      'Prioritise rest and light duties. Notify mission medical personnel if fatigue persists or worsens.',
    DEFAULT:
      'Balance activity with recovery and report persistent fatigue to mission medical personnel.',
  },
  physical_activity: {
    BELOW:
      'Review your activity plan with mission medical personnel and add light movement as approved.',
    ABOVE:
      'Include recovery time in your activity plan and report any unusual soreness or exhaustion.',
    DEFAULT:
      'Continue your assigned activity and recovery plan.',
  },
  systolic_bp: {
    ABOVE:
      'Rest and repeat the measurement. Contact mission medical personnel if the elevated reading persists.',
    BELOW:
      'Rest and repeat the measurement. Tell mission medical personnel if you feel light-headed.',
    DEFAULT:
      'Continue monitoring your blood pressure and report unusual symptoms.',
  },
  diastolic_bp: {
    ABOVE:
      'Rest and repeat the measurement. Contact mission medical personnel if the elevated reading persists.',
    BELOW:
      'Rest and repeat the measurement. Tell mission medical personnel if you feel light-headed.',
    DEFAULT:
      'Continue monitoring your blood pressure and report unusual symptoms.',
  },
  body_temperature: {
    ABOVE:
      'Hydrate, rest and repeat the measurement. Contact mission medical personnel if your temperature remains elevated.',
    DEFAULT:
      'Continue monitoring your temperature and report chills or fever to mission medical personnel.',
  },
}

export function profileFor(astronautId, directoryEntry) {
  const fallback = PROFILE_FALLBACKS[astronautId] || {}

  return {
    astronaut_id: astronautId,
    full_name:
      directoryEntry?.full_name ||
      directoryEntry?.name ||
      fallback.full_name ||
      `Astronaut ${astronautId}`,
    mission_name:
      directoryEntry?.mission_name ||
      fallback.mission_name ||
      'Active mission',
    mission_role:
      directoryEntry?.mission_role ||
      fallback.mission_role ||
      'Crew member',
    profile_picture:
      directoryEntry?.profile_picture ||
      directoryEntry?.avatar_url ||
      directoryEntry?.photo_url ||
      '',
    nationality: directoryEntry?.nationality || '',
    date_of_birth: directoryEntry?.date_of_birth || '',
    start_date: directoryEntry?.start_date || '',
    expected_return_date: directoryEntry?.expected_return_date || '',
  }
}

export function initialsFor(name) {
  const parts = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (parts.length === 0) {
    return 'A'
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase()
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export function greetingFor(date = new Date()) {
  const hour = date.getHours()

  if (hour < 12) {
    return 'Good morning'
  }

  if (hour < 18) {
    return 'Good afternoon'
  }

  return 'Good evening'
}

export function missionInfoFor(readings, profile) {
  const firstReading = readings[0]?.recorded_at
  const latestReading = readings[readings.length - 1]?.recorded_at
  const startRaw = profile.start_date || firstReading
  const endRaw = latestReading || new Date().toISOString()
  const start = startRaw ? new Date(startRaw) : null
  const end = new Date(endRaw)

  if (!start || Number.isNaN(start.getTime())) {
    return {
      days: null,
      start: null,
      end: Number.isNaN(end.getTime()) ? null : end,
      startLabel: '—',
      latestLabel: Number.isNaN(end.getTime())
        ? '—'
        : formatDate(end.toISOString()),
      status: 'Awaiting monitoring data',
    }
  }

  const days = Math.max(
    1,
    Math.ceil((end.getTime() - start.getTime()) / DAY_MS),
  )

  return {
    days,
    start,
    end: Number.isNaN(end.getTime()) ? null : end,
    startLabel: formatDate(start.toISOString()),
    latestLabel: Number.isNaN(end.getTime())
      ? '—'
      : formatDate(end.toISOString()),
    status: 'Mission active',
  }
}

export function anomalyFor(analysis, metric) {
  return (
    analysis?.anomalies?.find((item) => item.metric === metric) ?? null
  )
}

export function trendFor(analysis, metric) {
  return analysis?.trends?.[metric] ?? null
}

export function latestValue(analysis, metric) {
  return analysis?.reading?.values?.[metric] ?? null
}

export function assessmentFor(analysis, metric) {
  const anomaly = anomalyFor(analysis, metric)
  const severity = anomaly?.evaluated
    ? anomaly.severity
    : 'NOT_EVALUATED'
  let label = STATUS_COPY[severity]?.label ?? severity

  if (severity === 'NORMAL' && metric === 'sleep_duration') {
    label = 'On track'
  }

  if (severity === 'NORMAL' && metric === 'physical_activity') {
    label = 'On track'
  }

  return {
    severity,
    label,
    anomaly,
  }
}

export function healthStatusFor(analysis) {
  const ruleSeverity =
    analysis?.summary?.anomaly?.highest_severity ?? 'NOT_EVALUATED'
  const mlStatus = analysis?.ml_anomaly?.status
  const severity =
    ruleSeverity === 'NORMAL' && mlStatus === 'ANOMALY'
      ? 'ANOMALY'
      : ruleSeverity
  const copy = STATUS_COPY[severity] || STATUS_COPY.NOT_EVALUATED

  return {
    severity,
    label: copy.label,
    description: copy.description,
    requiresReview: Boolean(
      analysis?.summary?.requires_review ||
        analysis?.ml_anomaly?.is_anomaly,
    ),
  }
}

export function observationForAnomaly(item) {
  if (item?.reason) {
    return item.reason
  }

  const label = item?.metric_label || item?.metric || 'Measurement'
  const direction = item?.direction
  const difference = item?.difference
  const unit = item?.unit

  if (
    difference !== null &&
    difference !== undefined &&
    (direction === 'ABOVE' || direction === 'BELOW')
  ) {
    const amount = Math.abs(Number(difference)).toFixed(1)
    const measure = unit ? `${amount} ${unit}` : amount
    return `${label} is ${measure} ${direction.toLowerCase()} your personal baseline.`
  }

  return `${label} is outside your personal baseline range.`
}

export function recommendationFor(metric, direction, severity) {
  const metricGuidance = RECOMMENDATIONS[metric] || {}
  const base =
    metricGuidance[direction] ||
    metricGuidance.DEFAULT ||
    'Continue monitoring and contact mission medical personnel if you have concerns.'

  if (severity === 'SEVERE') {
    return `Contact mission medical personnel promptly. ${base}`
  }

  return base
}

export function buildInsights(analysis) {
  const flagged = (analysis?.anomalies || [])
    .filter(
      (item) =>
        item.evaluated &&
        item.severity !== 'NORMAL' &&
        item.severity !== 'NOT_EVALUATED',
    )
    .sort(
      (left, right) =>
        severityRank(left.severity) - severityRank(right.severity),
    )

  if (flagged.length === 0) {
    return [
      {
        id: 'stable',
        severity: 'NORMAL',
        metric: null,
        metric_label: 'Health overview',
        title: 'Your measurements are currently stable',
        observation:
          'Your latest evaluated measurements are within your personal baselines.',
        recommendation:
          'Maintain your assigned sleep, activity and recovery schedule. Continue recording measurements as scheduled.',
        direction: null,
        difference: null,
        unit: '',
        current_value: null,
        baseline_value: null,
        z_score: null,
      },
    ]
  }

  return flagged.map((item) => ({
    id: item.metric,
    severity: item.severity,
    metric: item.metric,
    metric_label: item.metric_label,
    title: `${item.metric_label} ${
      item.direction ? item.direction.toLowerCase() : 'deviation'
    } baseline`,
    observation: observationForAnomaly(item),
    recommendation: recommendationFor(
      item.metric,
      item.direction,
      item.severity,
    ),
    direction: item.direction,
    difference: item.difference,
    unit: item.unit,
    current_value: item.current_value,
    baseline_value: item.baseline_value,
    z_score: item.z_score,
  }))
}

export function buildNotifications(analysis) {
  const reading = analysis?.reading
  const notifications = []

  if (!reading) {
    return notifications
  }

  const status = healthStatusFor(analysis)
  const timestamp = reading.recorded_at
  const flagged = (analysis?.anomalies || [])
    .filter(
      (item) =>
        item.evaluated &&
        item.severity !== 'NORMAL' &&
        item.severity !== 'NOT_EVALUATED',
    )
    .sort(
      (left, right) =>
        severityRank(left.severity) - severityRank(right.severity),
    )

  notifications.push({
    id: `assessment-${reading.id}`,
    category: 'Assessment',
    title: 'New health assessment available',
    body: `Your latest reading has been assessed as ${status.label.toLowerCase()}.`,
    timestamp,
    order: 0,
    tone: status.severity,
    unread: true,
  })

  flagged.forEach((item, index) => {
    notifications.push({
      id: `alert-${reading.id}-${item.metric}`,
      category: 'Health alert',
      title: `${item.metric_label} ${
        item.direction ? item.direction.toLowerCase() : 'deviation'
      } baseline`,
      body: observationForAnomaly(item),
      timestamp,
      order: 1 + index,
      tone: item.severity,
      unread: true,
    })
  })

  const sleepAlert = flagged.find(
    (item) => item.metric === 'sleep_duration',
  )
  const sleepTrend = trendFor(analysis, 'sleep_duration')

  if (
    sleepAlert ||
    (sleepTrend?.reliable && sleepTrend.direction === 'DECREASING')
  ) {
    notifications.push({
      id: `sleep-${reading.id}`,
      category: 'Sleep',
      title: 'Sleep recovery guidance',
      body: recommendationFor(
        'sleep_duration',
        'BELOW',
        sleepAlert?.severity || 'WATCH',
      ),
      timestamp,
      order: 20,
      tone: sleepAlert?.severity || 'WATCH',
      unread: true,
    })
  }

  notifications.push({
    id: `monitoring-${reading.id}`,
    category: 'Monitoring',
    title: 'Monitoring data received',
    body: `A ${reading.source || 'health'} reading was recorded and compared with baseline version ${
      analysis?.baseline?.version ?? '—'
    }.`,
    timestamp,
    order: 30,
    tone: 'NORMAL',
    unread: false,
  })

  return notifications.sort(
    (left, right) => left.order - right.order,
  )
}

export function formatDelta(value, unit) {
  if (value === null || value === undefined) {
    return '—'
  }

  if (Math.abs(Number(value)) < 0.005) {
    return 'At baseline'
  }

  const sign = Number(value) > 0 ? '+' : ''
  return `${sign}${formatMetric(value, unit)}`
}

export function average(values) {
  const numbers = values
    .map(Number)
    .filter((value) => Number.isFinite(value))

  if (numbers.length === 0) {
    return null
  }

  return (
    numbers.reduce((total, value) => total + value, 0) /
    numbers.length
  )
}

export function metricStats(analysis, readings, metric) {
  const values = readings
    .map((reading) => reading[metric])
    .filter(
      (value) => value !== null && value !== undefined,
    )
    .map(Number)
    .filter((value) => Number.isFinite(value))

  const anomaly = anomalyFor(analysis, metric)
  const trend = trendFor(analysis, metric)
  const latest =
    latestValue(analysis, metric) ??
    (values.length ? values[values.length - 1] : null)

  return {
    metric,
    label: METRIC_META[metric]?.label ?? metric,
    unit: METRIC_META[metric]?.unit ?? '',
    latest,
    baseline: anomaly?.baseline_value ?? null,
    difference: anomaly?.difference ?? null,
    severity: anomaly?.evaluated
      ? anomaly.severity
      : 'NOT_EVALUATED',
    trend,
    recentAverage: average(values.slice(-7)),
    periodAverage: average(values),
    values,
    minimum: values.length ? Math.min(...values) : null,
    maximum: values.length ? Math.max(...values) : null,
  }
}
