import { useCallback, useState } from 'react'
import './App.css'
import sealFacts from './sealFacts'
import SealMap from './SealMap.jsx'

function pickRandomFactForSpecies(commonName) {
  const normalized = (commonName || '').trim()
  const species =
    sealFacts.find((s) => s.common_name === normalized) ||
    sealFacts.find(
      (s) => s.common_name.toLowerCase() === normalized.toLowerCase()
    ) ||
    sealFacts.find((s) => s.common_name === 'Harbor seal')
  const facts = species.fun_facts
  return facts[Math.floor(Math.random() * facts.length)]
}

function fmtCov(v, unit = '', digits = 2) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  const n = Number(v)
  const s = digits === 0 ? String(Math.round(n)) : n.toFixed(digits)
  return unit ? `${s} ${unit}` : s
}

function App() {
  const [showPopup, setShowPopup] = useState(false)
  const [insight, setInsight] = useState(null)

  const handlePredictionResult = useCallback((data, meta) => {
    const topName =
      data?.seal_present === true ? data?.species_top5?.[0]?.common_name : null
    setInsight({
      result: data,
      meta,
      fact: pickRandomFactForSpecies(topName),
    })
    setShowPopup(true)
  }, [])

  const closePopup = () => {
    setShowPopup(false)
  }

  const r = insight?.result
  const m = insight?.meta
  const c = r?.covariates

  return (
    <div className="app-wrapper">
      <div className={`map-container ${showPopup ? 'popup-open' : ''}`}>
        <SealMap onPredictionResult={handlePredictionResult} />
      </div>

      {showPopup && insight != null && (
        <div className="popup-panel" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="close-btn" onClick={closePopup}>
            ✖
          </button>

          <h2>Location data</h2>

          <div className="data-list">
            <div className="data-item">
              <strong>Place</strong>
              <br />
              {r?.location_name ?? '—'}
            </div>
            <div className="data-item">
              <strong>P(seal)</strong>
              <br />
              {r != null && typeof r.seal_probability === 'number'
                ? `${(r.seal_probability * 100).toFixed(2)}%`
                : '—'}
            </div>
            <div className="data-item">
              <strong>Depth of sea floor</strong>
              <br />
              {c != null ? fmtCov(c.ocean_depth_m, 'm', 1) : '—'}
            </div>
            <div className="data-item">
              <strong>Slope of sea floor</strong>
              <br />
              {c != null ? fmtCov(c.seafloor_slope, '', 4) : '—'}
            </div>
            <div className="data-item">
              <strong>Sea surface temp</strong>
              <br />
              {c != null ? fmtCov(c.sea_surface_temperature_c, '°C', 2) : '—'}
            </div>
            <div className="data-item">
              <strong>Sea surface wind (10 m)</strong>
              <br />
              {c != null ? fmtCov(c.wind_speed_10m, 'm/s', 2) : '—'}
            </div>
            <div className="data-item">
              <strong>Distance to nearest shore</strong>
              <br />
              {c != null ? fmtCov(c.distance_to_shore_km, 'km', 2) : '—'}
            </div>
            <div className="data-item">
              <strong>Month of year</strong>
              <br />
              {m != null ? m.month : '—'}
            </div>
            <div className="data-item">
              <strong>Latitude</strong>
              <br />
              {m != null ? m.latitude : '—'}
            </div>
            <div className="data-item">
              <strong>Longitude</strong>
              <br />
              {m != null ? m.longitude : '—'}
            </div>
            {(r?.reference_year_used != null || c?.reference_year != null) && (
              <div className="data-item">
                <strong>Reference year (ocean layers)</strong>
                <br />
                {r?.reference_year_used ?? c?.reference_year}
              </div>
            )}
            {c?.bathy_elevation_m != null && (
              <div className="data-item">
                <strong>Bathy elevation (ETOPO)</strong>
                <br />
                {fmtCov(c.bathy_elevation_m, 'm', 1)}
              </div>
            )}
          </div>

          <div className="fun-fact-box">
            <h3>💡 Fun Fact</h3>
            {r?.seal_present === false && (
              <p style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>
                With seals unlikely here, here is a general seal fact (not from the species model).
              </p>
            )}
            <p>{insight.fact}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
