# Streamlit Return Risk Teaching App - Workspace Setup

## Project Overview
A Streamlit application designed to teach users about the Sequence of Return Risk (SORR) using a gamified portfolio management scenario with financial returns time series data and interactive visualizations.

## Completed Steps
- [x] Verify copilot-instructions.md file
- [x] Scaffold the Project
- [x] Customize the Project
- [x] Install Required Extensions
- [x] Compile the Project
- [x] Create and Run Task
- [x] Launch the Project
- [x] Ensure Documentation is Complete

## Project Features Implemented

### Core Gameplay
- 30-year portfolio simulation divided into 6 five-year periods
- Interactive stock allocation slider (0-100% in 10% increments)
- Random historical return sequences (1995-2025 data)
- Real-time portfolio value tracking
- Purchase requirement at year 15 (€75,000 for capybara farm)

### Simulation Engine
- Annual portfolio calculations with:
  - Stock return application
  - Portfolio rebalancing to target allocation
  - Annual savings injection (€5,000)
  - Bust detection if purchase target cannot be met
- Multiple strategy comparisons:
  - All cash (baseline)
  - 100% stocks
  - 50/50 balanced
  - Glidepath professional allocation (75/50/25/100)

### User Interface
- Left column: Controls and portfolio information
- Right column: Interactive charts with Plotly
- Real-time graph updates as periods complete
- Comparison mode for alternative strategies
- Game state management with Streamlit session

### Data & Files
- Returns.csv: 31 years of historical real returns (1995-2025)
- European decimal format support (comma as decimal separator)
- Automatic extraction of 5-year blocks
- No duplicate block usage in single game

## Technology Stack
- Streamlit 1.55.0
- Pandas 2.3.3
- Plotly 6.7.0
- Python 3.7+

## Application Status
✅ **LIVE AND FULLY FUNCTIONAL**

The application is running on `http://localhost:8501` and ready for use.

### How to Run
```bash
cd "c:\Users\vince\OneDrive\Bureau\SORR tool"
streamlit run app.py
```

### Game Instructions
1. Set stock allocation (0-100%)
2. Click "Simulate Period" 
3. Watch 5-year portfolio evolution
4. Make new allocation decisions for next period
5. Complete all 6 periods or bust at year 15
6. Compare your strategy against alternatives

## Files Modified/Created
- app.py - Complete game implementation (450+ lines)
- requirements.txt - Updated with compatible versions
- README.md - Full documentation
- .github/copilot-instructions.md - This file

## Testing Status
✅ Dependencies installed successfully
✅ Application launches without errors
✅ UI displays correctly
✅ All controls functional
✅ Data loads properly (Returns.csv parsed correctly)

## Notes
- Portfolio is rebalanced annually
- All calculations in real (inflation-adjusted) euros
- No fees or taxes in simulation
- Random block selection ensures unique sequences per game
- Session state preserves game progress
