export const METRIC_META = {
  heart_rate: { label: 'Heart rate', unit: 'bpm' },
  systolic_bp: { label: 'Systolic blood pressure', unit: 'mmHg' },
  diastolic_bp: { label: 'Diastolic blood pressure', unit: 'mmHg' },
  body_temperature: { label: 'Body temperature', unit: 'C' },
  oxygen_saturation: { label: 'Oxygen saturation', unit: '%' },
  sleep_duration: { label: 'Sleep duration', unit: 'hours' },
  physical_activity: { label: 'Physical activity', unit: 'minutes/day' },
  fatigue_level: { label: 'Fatigue level', unit: 'score (1-10)' },
}

export const CHART_METRICS = [
  'heart_rate',
  'sleep_duration',
  'fatigue_level',
  'oxygen_saturation',
]

export const SEVERITIES = [
  'SEVERE',
  'ANOMALY',
  'WATCH',
  'NORMAL',
  'NOT_EVALUATED',
]

export const SEVERITY_ORDER = {
  SEVERE: 0,
  ANOMALY: 1,
  WATCH: 2,
  NORMAL: 3,
  NOT_EVALUATED: 4,
}

export const SEVERITY_LABEL = {
  SEVERE: 'Severe',
  ANOMALY: 'Anomaly',
  WATCH: 'Watch',
  NORMAL: 'Normal',
  NOT_EVALUATED: 'Not evaluated',
}

export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—'
  }

  return Number(value).toFixed(digits)
}

export function formatMetric(value, unit) {
  if (value === null || value === undefined) {
    return '—'
  }

  const digits = Math.abs(value) >= 10 ? 1 : 2
  return `${formatNumber(value, digits)}${unit ? ` ${unit}` : ''}`
}

export function formatDate(value) {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatShortDate(value) {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

export function formatRelativeTime(value) {
  if (!value) {
    return 'No data'
  }

  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) {
    return 'Unknown'
  }

  const difference = Date.now() - timestamp
  const future = difference < 0
  const absolute = Math.abs(difference)

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  let amount
  let unit

  if (absolute < hour) {
    amount = Math.max(1, Math.round(absolute / minute))
    unit = 'minute'
  } else if (absolute < day) {
    amount = Math.round(absolute / hour)
    unit = 'hour'
  } else if (absolute < 30 * day) {
    amount = Math.round(absolute / day)
    unit = 'day'
  } else if (absolute < 365 * day) {
    amount = Math.round(absolute / (30 * day))
    unit = 'month'
  } else {
    amount = Math.round(absolute / (365 * day))
    unit = 'year'
  }

  const plural = amount === 1 ? unit : `${unit}s`
  return future ? `in ${amount} ${plural}` : `${amount} ${plural} ago`
}

export function statusClass(status) {
  return `status-badge status-${String(status).toLowerCase()}`
}

export function severityRank(severity) {
  return SEVERITY_ORDER[severity] ?? 9
}

export function chartMetricLabel(metric) {
  return METRIC_META[metric]?.label ?? metric
}
