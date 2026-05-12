# Sequence of Return Risk (SORR) Teaching Application

An interactive Streamlit game that teaches users about **Sequence of Return Risk** by managing an investment portfolio over 25 years.

## Project Overview

This application gamifies the concept of Sequence of Return Risk through an engaging scenario:
- **Start**: €10,000 capital + €5,000 annual savings
- **Goal 1**: Accumulate €75,000 to buy a capybara farm by year 15
- **Goal 2**: Maximize wealth by year 30 for the Capybara Foundation
- **Challenge**: Make 6 strategic allocation decisions (stocks vs. cash) across 5-year periods
- **Twist**: Random historical return sequences show how timing impacts outcomes

### Key Concepts Demonstrated
- The impact of sequence of returns on portfolio outcomes
- How allocation decisions at different life stages matter
- The role of regular savings in mitigating sequence risk
- Comparison between different investment strategies

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Once dependencies are installed:

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## How to Play

1. **Review the Game Rules** (in sidebar)
2. **Choose Stock Allocation** (0-100% in 10% increments)
3. **Click "Simulate Period"** to run 5 years with:
   - Random historical returns (1995-2025 data)
   - Annual portfolio rebalancing
   - €5,000 annual savings added
   - Check at year 15 for €75,000 purchase feasibility
4. **Repeat** for 6 periods (30 years total)
5. **View Results**:
   - Your final portfolio value (0 if bust)
   - Compare against alternative strategies
   - See how sequence affected your outcome

## Comparison Strategies (Post-Game)

After completing your game, view how other strategies performed:
- **All Cash**: Just savings, no investment returns
- **100% Stocks**: Everything in stocks with your return sequence
- **50/50 Mix**: Balanced portfolio with your return sequence
- **Glidepath Strategy**: Professional allocation (75→50→25→100)

## Project Structure

```
SORR tool/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── Returns.csv                 # Historical real returns (2000-2025)
├── Specs.txt                   # Game rules (French)
├── README.md                   # This file
└── .github/
    └── copilot-instructions.md # Workspace setup guide
```

## Game Mechanics

### Simulation Process (Each Period)
For each of the 5 years in a period:
1. **Apply Returns**: Stock portion gets annual return from historical data
2. **Rebalance**: Adjust stock/cash to maintain chosen allocation %
3. **Save**: Add €5,000 to portfolio
4. **Check Purchase**: At year 15, verify €75,000 is available

### Data Source
- Historical real (inflation-adjusted) returns: 1995-2025
- 5-year blocks are randomly selected (each used once)
- All calculations in real (inflation-corrected) euros
- No fees, no taxes in simulation

### Bust Condition
If portfolio < €75,000 at year 15:
- Purchase cannot be made
- Game ends immediately
- Final score = €0

## Technologies Used

- **Streamlit** 1.55+ - Interactive web framework
- **Pandas** 2.3+ - Data manipulation
- **Plotly** 6.7+ - Interactive visualizations
- **NumPy** - Numerical computing

## Educational Value

This application teaches:
- Historical returns data from real markets (2000-2025)
- How timing of cash flows (savings, purchases) interacts with market returns
- Why identical average returns can produce different outcomes
- The importance of strategic asset allocation over time
- Risk management through rebalancing

## Notes

- All values are in real (inflation-adjusted) euros
- Portfolio is rebalanced annually to maintain allocation percentage
- Random 5-year blocks ensure each game is unique
- The same total return applies across all players; only the sequence differs

## Future Enhancements

Potential additions:
- Difficulty levels (different savings rates, goals)
- Leaderboard (best final scores)
- Historical replay (play with actual historical sequence)
- Advanced metrics (Sharpe ratio, maximum drawdown)
- Multi-player comparisons
