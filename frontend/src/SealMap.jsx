import 'mapbox-gl/dist/mapbox-gl.css'
import { useCallback, useEffect, useRef, useState } from 'react'

const MAP_STYLE = 'mapbox://styles/minniekay-0/cmnkv4xcf004f01sg0yia4lv0'

/** Matches the working standalone Mapbox sample (Pittsburgh demo viewport). */
const INITIAL_CENTER = [-79.999732, 40.4374]
const INITIAL_ZOOM = 11

const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000').replace(/\/$/, '')

/**
 * Vite + Mapbox GL v3: default worker bundling often throws (worker parse / syntax).
 * CSP build + `?worker` is the supported pattern for bundlers.
 */
async function loadMapboxGL() {
  try {
    const { default: mapboxgl } = await import('mapbox-gl/dist/mapbox-gl-csp.js')
    const workerMod = await import('mapbox-gl/dist/mapbox-gl-csp-worker.js?worker')
    mapboxgl.workerClass = workerMod.default
    return mapboxgl
  } catch {
    const { default: mapboxgl } = await import('mapbox-gl')
    return mapboxgl
  }
}

const panelStyle = {
  position: 'absolute',
  top: 16,
  left: 16,
  zIndex: 10,
  width: 'min(360px, calc(100vw - 32px))',
  maxHeight: 'calc(100vh - 32px)',
  overflowY: 'auto',
  padding: '16px 18px',
  borderRadius: 12,
  background: 'rgba(255, 255, 255, 0.94)',
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
  fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
  fontSize: 14,
  color: '#1a1a2e',
}

const labelStyle = {
  display: 'block',
  fontSize: 11,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: '#64748b',
  marginBottom: 4,
}

const valueStyle = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: 15,
  marginBottom: 14,
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid #cbd5e1',
  fontSize: 14,
  marginBottom: 14,
  boxSizing: 'border-box',
}

const buttonStyle = {
  width: '100%',
  padding: '12px 16px',
  borderRadius: 8,
  border: 'none',
  background: '#0f766e',
  color: '#fff',
  fontSize: 15,
  fontWeight: 600,
  cursor: 'pointer',
}

const buttonDisabled = {
  ...buttonStyle,
  background: '#94a3b8',
  cursor: 'not-allowed',
}

const errorBox = {
  marginTop: 12,
  padding: 10,
  borderRadius: 8,
  background: '#fef2f2',
  color: '#b91c1c',
  fontSize: 13,
  lineHeight: 1.4,
}

const landNoticeBox = {
  marginTop: 12,
  padding: 14,
  borderRadius: 10,
  background: 'linear-gradient(165deg, #fffbeb 0%, #fef3c7 100%)',
  border: '1px solid #fbbf24',
  boxShadow: '0 2px 8px rgba(245, 158, 11, 0.12)',
  color: '#422006',
  fontSize: 14,
  lineHeight: 1.5,
}

const resultBox = {
  marginTop: 14,
  padding: 12,
  borderRadius: 8,
  background: '#f8fafc',
  border: '1px solid #e2e8f0',
  fontSize: 13,
}

function todayIsoDate() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function parseApiErrorDetail(data) {
  if (data == null) return 'Request failed'
  const d = data.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === 'object' && x.msg ? x.msg : JSON.stringify(x)))
      .join('; ')
  }
  if (typeof d === 'object' && d !== null && d.error === 'point_on_land') {
    return null
  }
  return typeof data.message === 'string' ? data.message : JSON.stringify(data)
}

/** FastAPI 422 `detail` when ETOPO says land */
function parsePointOnLandPayload(data) {
  const d = data?.detail
  if (d != null && typeof d === 'object' && !Array.isArray(d) && d.error === 'point_on_land') {
    return d
  }
  return null
}

function fmtNum(v, digits = 2) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toFixed(digits)
}

function makePinElement() {
  const el = document.createElement('div')
  el.title = 'Selected location'
  el.style.width = '22px'
  el.style.height = '22px'
  el.style.borderRadius = '50%'
  el.style.background = '#dc2626'
  el.style.border = '3px solid #fff'
  el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.35)'
  return el
}

export default function SealMap({ onPredictionResult } = {}) {
  const token = import.meta.env.VITE_MAPBOX_TOKEN

  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const mapboxglRef = useRef(null)
  const markerRef = useRef(null)

  const [pin, setPin] = useState(null)
  const [date, setDate] = useState(todayIsoDate)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [landNotice, setLandNotice] = useState(null)
  const [result, setResult] = useState(null)
  const [mapReady, setMapReady] = useState(false)
  const [mapLoading, setMapLoading] = useState(false)
  const [mapInitError, setMapInitError] = useState(null)

  useEffect(() => {
    if (!token || String(token).trim() === '') return undefined

    let cancelled = false
    let map = null
    const el = mapContainerRef.current

    setMapInitError(null)
    setMapReady(false)
    setMapLoading(true)
    mapboxglRef.current = null

    if (!el) {
      setMapLoading(false)
      return undefined
    }

    const ro = new ResizeObserver(() => {
      map?.resize()
    })
    ro.observe(el)

    ;(async () => {
      try {
        const mapboxgl = await loadMapboxGL()
        if (cancelled || mapContainerRef.current !== el) return

        mapboxglRef.current = mapboxgl
        mapboxgl.accessToken = token

        map = new mapboxgl.Map({
          container: el,
          style: MAP_STYLE,
          center: INITIAL_CENTER,
          zoom: INITIAL_ZOOM,
        })

        map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')

        map.on('click', (e) => {
          const { lng, lat } = e.lngLat
          setPin({ lng, lat })
          setError(null)
        })

        map.once('load', () => {
          if (!cancelled) {
            setMapReady(true)
            setMapLoading(false)
          }
        })

        map.on('error', (e) => {
          if (!cancelled && e?.error?.message) {
            setMapInitError((prev) => prev ?? e.error.message)
          }
        })

        mapRef.current = map
      } catch (e) {
        if (!cancelled) {
          setMapInitError(e instanceof Error ? e.message : String(e))
          setMapLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
      ro.disconnect()
      if (markerRef.current) {
        markerRef.current.remove()
        markerRef.current = null
      }
      if (map != null) {
        map.remove()
      }
      mapRef.current = null
      mapboxglRef.current = null
    }
  }, [token])

  useEffect(() => {
    const map = mapRef.current
    const mapboxgl = mapboxglRef.current
    if (!map || !mapboxgl || !mapReady) return

    if (pin == null) {
      if (markerRef.current) {
        markerRef.current.remove()
        markerRef.current = null
      }
      return
    }

    if (!markerRef.current) {
      markerRef.current = new mapboxgl.Marker({ element: makePinElement(), anchor: 'center' })
    }
    markerRef.current.setLngLat([pin.lng, pin.lat]).addTo(map)
  }, [pin, mapReady])

  const onPredict = useCallback(async () => {
    if (pin == null) return
    const parts = date.split('-')
    if (parts.length !== 3) {
      setError('Invalid date')
      return
    }
    const month = Number(parts[1])
    const day = Number(parts[2])
    if (!month || month < 1 || month > 12 || !day || day < 1 || day > 31) {
      setError('Invalid date')
      return
    }

    setLoading(true)
    setError(null)
    setLandNotice(null)
    setResult(null)

    const body = {
      latitude: Number(pin.lat.toFixed(4)),
      longitude: Number(pin.lng.toFixed(4)),
      month,
      day,
    }

    try {
      const res = await fetch(`${API_BASE}/api/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const land = parsePointOnLandPayload(data)
        if (land != null) {
          setLandNotice(land)
          return
        }
        setError(parseApiErrorDetail(data) || `HTTP ${res.status}`)
        return
      }
      setResult(data)
      onPredictionResult?.(data, {
        month,
        day,
        date,
        latitude: body.latitude,
        longitude: body.longitude,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setLoading(false)
    }
  }, [pin, date, onPredictionResult])

  if (!token || String(token).trim() === '') {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          minHeight: 240,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          textAlign: 'center',
          fontFamily: 'system-ui, sans-serif',
          background: '#0f172a',
          color: '#e2e8f0',
        }}
      >
        <div style={{ maxWidth: 480 }}>
          <h1 style={{ fontSize: 20, marginBottom: 12 }}>Mapbox token missing</h1>
          <p style={{ lineHeight: 1.6, color: '#94a3b8' }}>
            Create <code style={{ color: '#7dd3fc' }}>frontend/.env</code> with:
          </p>
          <pre
            style={{
              marginTop: 16,
              padding: 16,
              background: '#1e293b',
              borderRadius: 8,
              textAlign: 'left',
              overflow: 'auto',
              fontSize: 13,
            }}
          >
            VITE_MAPBOX_TOKEN=your_public_token_here
          </pre>
          <p style={{ marginTop: 16, fontSize: 13, color: '#94a3b8' }}>
            Restart <code style={{ color: '#7dd3fc' }}>npm run dev</code> after saving.
          </p>
        </div>
      </div>
    )
  }

  if (mapInitError != null) {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          minHeight: 240,
          padding: 24,
          fontFamily: 'system-ui, sans-serif',
          background: '#fef2f2',
          color: '#7f1d1d',
          boxSizing: 'border-box',
        }}
      >
        <h2 style={{ fontSize: 18, marginBottom: 12 }}>Map failed to start</h2>
        <pre
          style={{
            whiteSpace: 'pre-wrap',
            fontSize: 13,
            background: '#fff',
            padding: 16,
            borderRadius: 8,
            border: '1px solid #fecaca',
          }}
        >
          {mapInitError}
        </pre>
        <p style={{ marginTop: 12, fontSize: 14 }}>
          This is often a Mapbox + Vite worker issue. Try another browser, or open the console (F12)
          and hard-refresh. Build target is set to <code>esnext</code> in{' '}
          <code>vite.config.js</code>.
        </p>
      </div>
    )
  }

  const latStr = pin != null ? pin.lat.toFixed(4) : '—'
  const lonStr = pin != null ? pin.lng.toFixed(4) : '—'
  const btnStyle = pin != null && !loading ? buttonStyle : buttonDisabled

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 0, position: 'relative' }}>
      <div
        ref={mapContainerRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          background: '#dfe7f5',
        }}
      />

      {mapLoading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255,255,255,0.85)',
            fontFamily: 'system-ui, sans-serif',
            fontSize: 15,
            color: '#334155',
            pointerEvents: 'none',
          }}
        >
          Loading map…
        </div>
      )}

      <div style={panelStyle}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14, color: '#0f172a' }}>
          Seal presence
        </h2>

        <span style={labelStyle}>API</span>
        <div style={{ ...valueStyle, fontSize: 12, color: '#64748b' }}>{API_BASE}</div>

        <span style={labelStyle}>Latitude</span>
        <div style={valueStyle}>{latStr}</div>

        <span style={labelStyle}>Longitude</span>
        <div style={valueStyle}>{lonStr}</div>

        <span style={labelStyle}>Date</span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          style={inputStyle}
        />

        <button
          type="button"
          style={btnStyle}
          disabled={pin == null || loading}
          onClick={() => void onPredict()}
        >
          {loading ? 'Running prediction…' : 'Predict seal presence'}
        </button>

        {landNotice != null && (
          <div style={landNoticeBox}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#92400e' }}>
              This point is on land
            </div>
            <p style={{ margin: '0 0 12px', fontSize: 13, color: '#713f12' }}>
              {typeof landNotice.message === 'string'
                ? landNotice.message
                : 'Seal habitat models apply to ocean points only.'}
            </p>
            <div style={{ fontSize: 13, marginBottom: 8 }}>
              <span style={{ fontWeight: 600, color: '#78350f' }}>Place</span>
              <br />
              {landNotice.location_name ?? '—'}
            </div>
            {landNotice.covariates != null && (
              <div
                style={{
                  marginTop: 10,
                  paddingTop: 10,
                  borderTop: '1px solid rgba(251, 191, 36, 0.5)',
                  fontSize: 12,
                  color: '#854d0e',
                }}
              >
                <div style={{ marginBottom: 4 }}>
                  <strong>Land elevation (ETOPO)</strong>: {fmtNum(landNotice.covariates.bathy_elevation_m, 1)}{' '}
                  m
                </div>
                <div style={{ marginBottom: 4 }}>
                  <strong>Distance to ocean</strong>: {fmtNum(landNotice.covariates.distance_to_shore_km, 2)} km
                </div>
                {landNotice.covariates.note != null && (
                  <div style={{ marginTop: 8, fontStyle: 'italic' }}>{landNotice.covariates.note}</div>
                )}
              </div>
            )}
            <p style={{ margin: '14px 0 0', fontSize: 12, color: '#a16207' }}>
              Move the pin offshore to run the full prediction.
            </p>
          </div>
        )}

        {error != null && <div style={errorBox}>{error}</div>}

        {result != null && (
          <div style={resultBox}>
            <div style={{ fontWeight: 700, marginBottom: 8, color: '#0f172a' }}>Results</div>
            <div style={{ marginBottom: 6 }}>
              <strong>Place:</strong> {result.location_name}
            </div>
            <div style={{ marginBottom: 6 }}>
              <strong>P(seal):</strong> {(result.seal_probability * 100).toFixed(2)}% —{' '}
              {result.seal_present ? 'likely present' : 'likely absent'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8 }}>
              Model uses month/day + ref. year {result.reference_year_used} for ocean layers.
            </div>
            {result.warnings != null && result.warnings.length > 0 && (
              <div style={{ marginBottom: 8, color: '#b45309', fontSize: 12 }}>
                Warnings: {result.warnings.join(', ')}
              </div>
            )}
            {result.seal_present === true && (
              <>
                <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 6 }}>
                  Top species (given seal)
                </div>
                <ol style={{ margin: 0, paddingLeft: 18, lineHeight: 1.5 }}>
                  {result.species_top5?.map((s, i) => (
                    <li key={i} style={{ marginBottom: 6 }}>
                      <span style={{ fontWeight: 600 }}>{s.common_name}</span>
                      <span style={{ color: '#64748b', fontSize: 12 }}> ({s.species})</span>
                      <br />
                      <span style={{ fontSize: 12 }}>
                        {(s.probability * 100).toFixed(2)}% conditional ·{' '}
                        {(s.probability_joint * 100).toFixed(2)}% joint
                      </span>
                    </li>
                  ))}
                </ol>
              </>
            )}
            {result.seal_present === false && (
              <p style={{ marginTop: 12, fontSize: 12, color: '#64748b', lineHeight: 1.45 }}>
                Species breakdown is shown only when the model predicts seals as likely present at
                this point.
              </p>
            )}
          </div>
        )}

        <p style={{ marginTop: 12, fontSize: 12, color: '#64748b', lineHeight: 1.45 }}>
          Click the map to drop a pin, pick a date, then run the prediction against the FastAPI
          backend.
        </p>
      </div>
    </div>
  )
}
