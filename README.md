# See-A-Seal 🦭

An interactive web app that predicts the likelihood of seal presence at any ocean location using real environmental data.

## What it does

Click anywhere on the ocean to drop a pin, pick a date, and get an instant prediction powered by a machine learning model trained on thousands of real seal sightings. The app returns:

- Probability of seal presence at that location
- Top predicted seal species
- Real environmental conditions (ocean depth, sea surface temperature, wind speed, distance to shore)
- A fun seal fact 🦭

## Tech Stack

- **Frontend**: React, Mapbox GL JS, Vite
- **Backend**: FastAPI (Python)
- **Model**: Two-stage Logistic Regression trained on OBIS global seal occurrence data

## Running Locally

### Prerequisites
- Node.js
- Python 3.10+
- A Mapbox public token (free at mapbox.com)

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env`:
VITE_MAPBOX_TOKEN=your_mapbox_token_here
VITE_API_BASE=http://localhost:8000

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

## Team
Arun Malani, Ryan Tapia, Emily Hames, Minnie Kay
