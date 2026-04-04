import { useCallback, useMemo, useState } from 'react'
import Map, { Marker, NavigationControl } from 'react-map-gl/mapbox'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAP_STYLE = 'mapbox://styles/minniekay-0/cmnkv4xcf004f01sg0yia4lv0'

const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000').replace(/\/$/, '')

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

const pinDotStyle = {
  width: 22,
  height: 22,
  borderRadius: '50%',
  background: '#dc2626',
  border: '3px solid #fff',
  boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
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
  return typeof data.message === 'string' ? data.message : JSON.stringify(data)
}

export default function SealMap() {
  const token = import.meta.env.VITE_MAPBOX_TOKEN

  const [pin, setPin] = useState(null)
  const [date, setDate] = useState(todayIsoDate)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const initialViewState = useMemo(
    () => ({
      longitude: -150,
      latitude: 28,
      zoom: 2.6,
      pitch: 0,
      bearing: 0,
    }),
    []
  )

  const onMapClick = useCallback((e) => {
    const { lng, lat } = e.lngLat
    setPin({ lng, lat })
    setError(null)
  }, [])

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
        setError(parseApiErrorDetail(data) || `HTTP ${res.status}`)
        return
      }
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setLoading(false)
    }
  }, [pin, date])

  if (!token || String(token).trim() === '') {
    return (
      <div
        style={{
          width: '100%',
          height: '100vh',
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

  const latStr = pin != null ? pin.lat.toFixed(4) : '—'
  const lonStr = pin != null ? pin.lng.toFixed(4) : '—'
  const btnStyle = pin != null && !loading ? buttonStyle : buttonDisabled

  return (
    <div style={{ width: '100%', height: '100vh', position: 'relative' }}>
      <Map
        mapboxAccessToken={token}
        mapStyle={MAP_STYLE}
        initialViewState={initialViewState}
        onClick={onMapClick}
        style={{ width: '100%', height: '100%' }}
        cursor="crosshair"
        reuseMaps
      >
        <NavigationControl position="top-right" showCompass={false} />
        {pin != null && (
          <Marker longitude={pin.lng} latitude={pin.lat} anchor="center">
            <div style={pinDotStyle} title="Selected location" />
          </Marker>
        )}
      </Map>

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
            <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 6 }}>Top species (given seal)</div>
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
