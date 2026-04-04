<<<<<<< HEAD
import { useState } from 'react'
import './App.css'
import sealFacts from './sealFacts'

function App() {
  
  const [showPopup, setShowPopup] = useState(false)
  const [currentFact, setCurrentFact] = useState("")

  const handleMapClick = () => {
    const species = sealFacts.find(s => s.common_name === "Harbor seal")
    const randomFact = species.fun_facts[Math.floor(Math.random() * species.fun_facts.length)]
    setCurrentFact(randomFact)
    setShowPopup(true)
  }

  const closePopup = () => {
    setShowPopup(false)
  }

  return (
    <div className="app-wrapper">

      <div
        className={`map-container ${showPopup ? 'popup-open' : ''}`}
        onClick={handleMapClick}
      >
        <div className="placeholder-map">
          <h2>Click anywhere on the blue background!</h2>
        </div>

        <div className="zoom-controls">
          <button className="icon-btn" onClick={e => e.stopPropagation()}>+</button>
          <button className="icon-btn" onClick={e => e.stopPropagation()}>−</button>
        </div>
      </div>

      {showPopup && (
        <div className="popup-panel" onClick={e => e.stopPropagation()}>
          <button className="close-btn" onClick={closePopup}>✖</button>

          <h2>Location Data</h2>

          <div className="data-list">
            <div className="data-item"><strong>Depth of Sea Floor:</strong><br />-- m</div>
            <div className="data-item"><strong>Slope of Sea Floor:</strong><br />-- °</div>
            <div className="data-item"><strong>Sea Surface Temp:</strong><br />-- °C</div>
            <div className="data-item"><strong>Sea Surface Wind Speed:</strong><br />-- knots</div>
            <div className="data-item"><strong>Distance to Nearest Shore:</strong><br />-- km (KDTree)</div>
            <div className="data-item"><strong>Month of Year:</strong><br />--</div>
            <div className="data-item"><strong>Latitude (Eq. Closeness):</strong><br />--</div>
          </div>

          <div className="fun-fact-box">
            <h3>💡 Fun Fact</h3>
            <p>{currentFact}</p>
          </div>
        </div>
      )}
    </div>
  )
=======
import SealMap from './SealMap.jsx'

function App() {
  return <SealMap />
>>>>>>> 0e333b1 (white orb)
}

export default App
