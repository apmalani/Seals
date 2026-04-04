import './App.css'

function App() {
  return (
    <div className="app-wrapper">
      
      {/* 1. The Placeholder Map */}
      <div className="placeholder-map">
        <h2>Map will go here</h2>
      </div>

      {/* 2. The Floating Zoom Buttons */}
      <div className="zoom-controls">
        <button className="icon-btn">+</button>
        <button className="icon-btn">−</button>
      </div>

    </div>
  )
}

export default App