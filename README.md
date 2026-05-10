# Perfume Formulation Calculator

A simple Flask web app that calculates the volumes of fragrance oil, alcohol, and distilled water needed to formulate a perfume based on your desired total volume and oil concentration.

## Features
- Input total volume (ml), oil %, and alcohol %
- Auto-calculates remaining water/dilutant volume
- Identifies perfume type (Parfum, EDP, EDT, EDC) based on oil concentration
- Input validation (e.g., percentages can't exceed 100%)

## Setup

1. Install Flask:
   ```bash
   pip install flask
   ```

2. Run the app:
   ```bash
   python app.py
   ```

3. Open your browser to: http://localhost:5000

## Project Structure
```
perfume_calculator/
├── app.py
└── templates/
    └── index.html
```

## How to Use
1. Enter the total volume of perfume you want to make (e.g., 50 ml)
2. Enter the fragrance oil percentage (e.g., 20%)
3. Enter the alcohol percentage (e.g., 70%)
4. Click "Calculate Formula" — the app fills in the remaining percentage with distilled water and tells you exactly how much of each ingredient you need.

## Perfume Concentration Reference
| Type | Oil % |
|------|-------|
| Parfum / Extrait | 20%+ |
| Eau de Parfum (EDP) | 15–20% |
| Eau de Toilette (EDT) | 10–15% |
| Eau de Cologne (EDC) | 5–10% |
| Eau Fraîche / Body Mist | <5% |
