import { useMemo, useRef, useState } from 'react'
import {
  formatMetric,
  formatNumber,
  formatShortDate,
  METRIC_META,
} from '../lib/format'

const WIDTH = 820
const HEIGHT = 300
const MARGIN = { top: 18, right: 20, bottom: 34, left: 58 }
const DAY_MS = 24 * 60 * 60 * 1000

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export default function MetricTrendChart({
  readings,
  metric,
  baselineValue,
  rangeDays,
}) {
  const [hoverIndex, setHoverIndex] = useState(null)
  const svgRef = useRef(null)

  const meta = METRIC_META[metric] ?? { label: metric, unit: '' }

  const points = useMemo(() => {
    const sorted = readings
      .filter(
        (reading) =>
          reading[metric] !== null &&
          reading[metric] !== undefined,
      )
      .map((reading) => ({
        time: new Date(reading.recorded_at).getTime(),
        value: Number(reading[metric]),
        recorded_at: reading.recorded_at,
      }))
      .filter((point) => !Number.isNaN(point.time))
      .sort((left, right) => left.time - right.time)

    if (sorted.length === 0) {
      return []
    }

    if (rangeDays === 'all') {
      return sorted
    }

    const latest = sorted[sorted.length - 1].time
    const cutoff = latest - Number(rangeDays) * DAY_MS
    return sorted.filter((point) => point.time >= cutoff)
  }, [metric, rangeDays, readings])

  const geometry = useMemo(() => {
    const plotWidth = WIDTH - MARGIN.left - MARGIN.right
    const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
    const values = points.map((point) => point.value)

    if (
      baselineValue !== null &&
      baselineValue !== undefined &&
      Number.isFinite(Number(baselineValue))
    ) {
      values.push(Number(baselineValue))
    }

    let min = values.length ? Math.min(...values) : 0
    let max = values.length ? Math.max(...values) : 1

    if (min === max) {
      const offset = Math.abs(min) * 0.1 || 1
      min -= offset
      max += offset
    }

    const padding = (max - min) * 0.12
    min -= padding
    max += padding

    const firstTime = points.length ? points[0].time : 0
    const lastTime = points.length
      ? points[points.length - 1].time
      : 1
    const timeSpan = Math.max(lastTime - firstTime, 1)

    const xFor = (time) => {
      if (points.length <= 1) {
        return MARGIN.left + plotWidth / 2
      }
      return (
        MARGIN.left +
        ((time - firstTime) / timeSpan) * plotWidth
      )
    }

    const yFor = (value) =>
      MARGIN.top +
      plotHeight -
      ((value - min) / (max - min)) * plotHeight

    const coordinates = points.map((point) => ({
      ...point,
      x: xFor(point.time),
      y: yFor(point.value),
    }))

    const linePath = coordinates
      .map(
        (point, index) =>
          `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`,
      )
      .join(' ')

    const baselineY =
      baselineValue !== null &&
      baselineValue !== undefined &&
      Number.isFinite(Number(baselineValue))
        ? yFor(Number(baselineValue))
        : null

    const areaPath = coordinates.length
      ? `${linePath} L ${coordinates[coordinates.length - 1].x.toFixed(
          2,
        )} ${MARGIN.top + plotHeight} L ${coordinates[0].x.toFixed(
          2,
        )} ${MARGIN.top + plotHeight} Z`
      : ''

    const ticks = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4
      return {
        value: min + (max - min) * ratio,
        y: MARGIN.top + plotHeight - ratio * plotHeight,
      }
    })

    const xTickIndexes = points.length
      ? Array.from(
          new Set([
            0,
            Math.floor((points.length - 1) / 3),
            Math.floor(((points.length - 1) * 2) / 3),
            points.length - 1,
          ]),
        )
      : []

    const xTicks = xTickIndexes.map((index) => ({
      x: xFor(points[index].time),
      label: formatShortDate(points[index].recorded_at),
    }))

    return {
      plotWidth,
      plotHeight,
      min,
      max,
      coordinates,
      linePath,
      areaPath,
      baselineY,
      ticks,
      xTicks,
      xFor,
    }
  }, [baselineValue, points])

  function handleMove(event) {
    if (
      !svgRef.current ||
      geometry.coordinates.length === 0
    ) {
      return
    }

    const rect = svgRef.current.getBoundingClientRect()
    const pointerX =
      ((event.clientX - rect.left) / rect.width) * WIDTH

    let nearest = 0
    let best = Number.POSITIVE_INFINITY

    geometry.coordinates.forEach((point, index) => {
      const distance = Math.abs(point.x - pointerX)
      if (distance < best) {
        best = distance
        nearest = index
      }
    })

    setHoverIndex(nearest)
  }

  if (points.length === 0) {
    return (
      <p className="chart-empty">
        No {meta.label.toLowerCase()} readings are available for this
        period.
      </p>
    )
  }

  const latest = geometry.coordinates[geometry.coordinates.length - 1]
  const hovered =
    hoverIndex !== null
      ? geometry.coordinates[hoverIndex]
      : null
  const tooltipWidth = 152
  const tooltipX = hovered
    ? clamp(
        hovered.x + 12,
        MARGIN.left,
        WIDTH - MARGIN.right - tooltipWidth,
      )
    : 0

  return (
    <div className="chart-body">
      <div className="chart-meta">
        <span>
          Latest{' '}
          <strong>{formatMetric(latest.value, meta.unit)}</strong>
        </span>
        <span>
          {points.length} point{points.length === 1 ? '' : 's'}
        </span>
        {geometry.baselineY !== null && (
          <span>
            Baseline{' '}
            <strong>
              {formatMetric(Number(baselineValue), meta.unit)}
            </strong>
          </span>
        )}
      </div>

      <svg
        ref={svgRef}
        className="trend-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`${meta.label} trend`}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient
            id={`metric-fill-${metric}`}
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop
              offset="0%"
              stopColor="var(--accent)"
              stopOpacity="0.28"
            />
            <stop
              offset="100%"
              stopColor="var(--accent)"
              stopOpacity="0"
            />
          </linearGradient>
        </defs>

        {geometry.ticks.map((tick) => (
          <g key={tick.value}>
            <line
              className="chart-grid"
              x1={MARGIN.left}
              x2={WIDTH - MARGIN.right}
              y1={tick.y}
              y2={tick.y}
            />
            <text
              className="chart-axis-label"
              x={MARGIN.left - 10}
              y={tick.y + 4}
              textAnchor="end"
            >
              {formatNumber(
                tick.value,
                Math.abs(tick.value) >= 10 ? 1 : 2,
              )}
            </text>
          </g>
        ))}

        {geometry.xTicks.map((tick) => (
          <text
            key={`${tick.x}-${tick.label}`}
            className="chart-axis-label"
            x={tick.x}
            y={HEIGHT - 10}
            textAnchor="middle"
          >
            {tick.label}
          </text>
        ))}

        {geometry.areaPath && (
          <path
            d={geometry.areaPath}
            fill={`url(#metric-fill-${metric})`}
          />
        )}

        {geometry.baselineY !== null && (
          <>
            <line
              className="chart-baseline-line"
              x1={MARGIN.left}
              x2={WIDTH - MARGIN.right}
              y1={geometry.baselineY}
              y2={geometry.baselineY}
            />
            <text
              className="chart-baseline-label"
              x={WIDTH - MARGIN.right}
              y={geometry.baselineY - 6}
              textAnchor="end"
            >
              baseline
            </text>
          </>
        )}

        <path className="chart-line" d={geometry.linePath} />

        {geometry.coordinates.length <= 45 &&
          geometry.coordinates.map((point) => (
            <circle
              key={`${point.time}-${point.value}`}
              className="chart-point"
              cx={point.x}
              cy={point.y}
              r={2.5}
            />
          ))}

        <circle
          className="chart-point-latest"
          cx={latest.x}
          cy={latest.y}
          r={4.5}
        />

        {hovered && (
          <g className="chart-hover">
            <line
              x1={hovered.x}
              x2={hovered.x}
              y1={MARGIN.top}
              y2={MARGIN.top + geometry.plotHeight}
            />
            <circle
              cx={hovered.x}
              cy={hovered.y}
              r={5}
            />
            <rect
              x={tooltipX}
              y={MARGIN.top}
              width={tooltipWidth}
              height={48}
              rx={8}
            />
            <text
              x={tooltipX + 10}
              y={MARGIN.top + 19}
            >
              {formatShortDate(hovered.recorded_at)}
            </text>
            <text
              className="chart-tooltip-value"
              x={tooltipX + 10}
              y={MARGIN.top + 37}
            >
              {formatMetric(hovered.value, meta.unit)}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}
