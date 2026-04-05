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
    const topName = data?.seal_present === true ? data?.species_top5?.[0]?.common_name : null
    const speciesData = sealFacts.find(s => s.common_name === topName) || sealFacts.find(s => s.common_name === 'Harbor seal')
    setInsight({
      result: data,
      meta,
      fact: speciesData.fun_facts[Math.floor(Math.random() * speciesData.fun_facts.length)],
      image: speciesData.images[Math.floor(Math.random() * speciesData.images.length)]
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

          {/* Close button */}
          <button type="button" className="close-btn" onClick={closePopup} style={{ alignSelf: 'flex-start' }}>
            <svg width="25" height="25" viewBox="0 0 25 25" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5.20825 19.7917L12.4999 12.5M12.4999 12.5L19.7916 5.20837M12.4999 12.5L5.20825 5.20837M12.4999 12.5L19.7916 19.7917" stroke="black" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          {/* Title Card */}
          <div className="title-card">
            <h1 className="main-title">
              {r?.seal_present === true && r?.species_top5?.[0] ? r.species_top5[0].common_name : 'Ocean Point'}
            </h1>
            <p className="scientific-name">
              {r?.seal_present === true ? (r?.species_top5?.[0]?.species ?? '') : ''}
            </p>

            <img
              src={insight.image}
              alt="seal"
              style={{ width: '100%', height: '180px', objectFit: 'cover', borderRadius: '12px' }}
            />

            <div className="likelihood-section">
              <div className="likelihood-bar-wrap">
                <div
                  className="likelihood-bar-fill"
                  style={{ width: `${((r?.seal_probability ?? 0) * 100).toFixed(0)}%` }}
                />
              </div>
              <p className="likelihood-text">
                Today's Sighting Likelihood:{' '}
                <strong>{r != null ? `${(r.seal_probability * 100).toFixed(0)}%` : '—'}</strong>
              </p>
              <p className="place-text">Place: {r?.location_name ?? '—'}</p>
            </div>
          </div>

          {/* Low probability message OR fun fact + species */}
          {r?.seal_present === false ? (
            <div className="info-card">
              <p className="body-text" style={{ textAlign: 'center', color: '#464444', fontStyle: 'italic', width: '100%' }}>
                It is unlikely a seal will be spotted around here.
              </p>
            </div>
          ) : (
            <>
              {/* Fun Fact Card */}
              <div className="info-card">
                <h2 className="card-header">Did you know?</h2>
                <p className="body-text truncate-text">{insight.fact}</p>
              </div>

              {/* Top Species Card */}
              <div className="info-card">
                <h2 className="card-header">Top Species</h2>
                {(r?.species_top5 ?? []).slice(0, 2).map((sp, i) => (
                  <div key={sp.species} className="species-row">
                    <span className="body-text">
                      <strong>{i + 1}. {sp.common_name}</strong>
                      {' '}<span className="body-text-2">({sp.species})</span>
                    </span>
                    <span className="body-text-2">
                      {(sp.probability * 100).toFixed(2)}% conditional · {(sp.probability_joint * 100).toFixed(2)}% joint
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Conditions Card — always shown */}
          <div className="info-card">
            <h2 className="card-header">Conditions</h2>
            <div className="conditions-grid">
              <span className="body-text">Slope of Sea Floor</span>
              <span className="body-text">{c != null ? fmtCov(c.seafloor_slope, '°', 1) : '—'}</span>
              <span className="body-text">Sea Floor Depth</span>
              <span className="body-text">{c != null ? fmtCov(c.ocean_depth_m, 'm', 0) : '—'}</span>
              <span className="body-text">Sea Surface Temperature</span>
              <span className="body-text">{c != null ? fmtCov(c.sea_surface_temperature_c, '°C', 1) : '—'}</span>
              <span className="body-text">Sea Surface Wind Speed</span>
              <span className="body-text">{c != null ? fmtCov(c.wind_speed_10m, 'm/s', 1) : '—'}</span>
              <span className="body-text">Distance to Nearest Shore</span>
              <span className="body-text">{c != null ? fmtCov(c.distance_to_shore_km, 'km', 1) : '—'}</span>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default App