# TRAID Project Checklist & Architecture Decisions

## 1. Project Setup
- [x] Initialize Git repository
- [x] Create virtual environment
- [x] Setup basic project structure
- [x] Create requirements.txt
- [x] Setup basic CI/CD pipeline
- [x] Create initial test framework

## 2. Data Architecture
### ADR 1: Data Sources

- [x] Define which cryptocurrency data to use
    - All trading pairs available on Kraken
    - Focus on USDT pairs (e.g., BTC/USDT, ETH/USDT)
    - Include all market cap sizes for comprehensive testing

- [x] Choose data provider/API
    - Selected Kraken API
    - Using REST API for historical data
    - Using WebSocket for real-time data

- [x] Define data structure
    -  Using standard OHLCV format:
        - timestamp: int (Unix timestamp)
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: float
    - Additional data:
        - trade_count: int
        - vwap: float (Volume Weighted Average Price)
- [ ] Implement data fetching
- [ ] Setup data storage

## 3. Trading Bot Architecture
### ADR 3: Core Components
- [ ] Define bot architecture
- [ ] Implement basic trading logic
- [ ] Setup risk management
- [ ] Create position sizing logic
- [ ] Implement order execution

### ADR 4: Machine Learning Implementation
- [ ] Choose TensorFlow models
- [ ] Define feature engineering
- [ ] Create training pipeline
- [ ] Implement prediction logic
- [ ] Setup model evaluation

## 4. Testing Strategy
### ADR 5: Testing Framework
- [ ] Unit tests
- [ ] Integration tests
- [ ] Backtesting framework
- [ ] Performance metrics
- [ ] Paper trading tests

## 5. Documentation
- [ ] Setup documentation structure
- [ ] Write technical documentation
- [ ] Create API documentation
- [ ] Document trading strategies
- [ ] Create user guide

## 6. Performance Monitoring
### ADR 6: Monitoring System
- [ ] Define KPIs
- [ ] Setup logging
- [ ] Implement monitoring dashboard
- [ ] Create alert system
- [ ] Performance reporting

## 7. Project Report Components
- [ ] Abstract
- [ ] Introduction
  - [ ] Problem statement
  - [ ] Project goals
- [ ] Main section
  - [ ] Methodology
  - [ ] Implementation
  - [ ] Results
- [ ] Discussion
- [ ] Conclusion and outlook
- [ ] Create presentation
- [ ] Prepare handout

## Directory Structure
```
TRAID/
├── docs/
├── src/
│   ├── data/         # Data handling
│   ├── models/       # ML models
│   ├── trading/      # Trading logic
│   └── utils/        # Utilities
├── tests/
│   ├── unit/
│   └── integration/
├── notebooks/        # Jupyter notebooks for analysis
├── configs/          # Configuration files
└── results/          # Trading results and analysis
```

## Important Deadlines
- [ ] Project proposal submission
- [ ] Midterm review
- [ ] Testing phase completion
- [ ] Documentation completion
- [ ] Final presentation
- [ ] Project submission

## Notes
- Remember to update this checklist regularly
- Each ADR should be documented separately with:
  - Context
  - Decision
  - Consequences
  - Status
