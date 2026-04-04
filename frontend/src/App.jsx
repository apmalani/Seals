import './App.css'

function App() {
  // Dummy functions for our buttons so they don't break when clicked
  const handleZoomIn = () => console.log("Zoom In");
  const handleZoomOut = () => console.log("Zoom Out");

  return (
    <div className="app-container">
      {/* 1. THE FAKE MAP BACKGROUND (We will replace this with Mapbox later) */}
      <div className="fake-map-layer">
        <h1 className="placeholder-text">Mapbox will go here!</h1>
      </div>

      {/* 2. LEFT SIDE UI (Like the 'Donate' button in your pic) */}
      <div className="left-panel">
        <button className="side-tab">Seal Info</button>
      </div>

      {/* 3. RIGHT SIDE CONTROLS (Zoom, Settings, etc.) */}
      <div className="right-controls">
        <button className="control-btn" onClick={handleZoomIn}>+</button>
        <button className="control-btn" onClick={handleZoomOut}>−</button>
        <div className="divider"></div>
        <button className="control-btn">📍</button>
        <button className="control-btn">⚙️</button>
      </div>

      {/* 4. THE PROBABILITY POPUP (Hidden by default, but here for you to style) */}
      <div className="probability-card">
        <h3>Click a location to test...</h3>
        <p>Waiting for Logistic Regression Model 🤖</p>
      </div>
    </div>
  )
}

export default App