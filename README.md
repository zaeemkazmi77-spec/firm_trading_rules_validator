# Trading Rule Validation Dashboard

## 📊 Overview

A comprehensive Streamlit-based web application for validating trading data against proprietary firm compliance rules. This dashboard analyzes CSV trade history files and checks them against 11 different trading rules to ensure compliance with firm regulations.

**Key Features:**
- ✅ Multi-file upload with phase management
- ✅ Real-time rule validation
- ✅ Detailed violation tracking with trade-level information
- ✅ Professional PDF reports with complete violation summaries
- ✅ Dual CSV exports (summary + detailed violations)
- ✅ Independent News Trading and Weekend Holding add-ons
- ✅ Comprehensive error handling and logging

## 🚀 Quick Start

### Installation

1. **Clone the repository or navigate to the project directory:**
   ```bash
   cd trading_rule
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## 📋 Features

### Core Functionality

- **Multi-File Upload**: Upload one or more CSV files representing different trading phases
- **Account Configuration**: 
  - Select account type (2-Step Phase 1/2, Funded Phase, Direct Funding)
  - Choose account size ($5K - $200K)
  - Enable/disable **News Trading Add-on** (independent control)
  - Enable/disable **Weekend Holding Add-on** (independent control)
  - Both add-ons available for all account types
- **Automated Rule Validation**: Tests 11 different trading rules
- **Comprehensive Reporting**: 
  - Color-coded results (✅ Passed, ❌ Violated, ⚠️ Not Testable)
  - Detailed violation explanations
  - Affected trade identification
- **Export Options**:
  - **CSV Export**: Generates TWO CSV files:
    - Summary file with overall rule results (normalized [PASSED]/[VIOLATED]/[NOT TESTABLE] status)
    - Detailed violations file with all affected trades and violation specifics
  - **PDF Report**: Professional report with comprehensive violation details, affected trade information, and trade-level summaries

## 📁 CSV File Requirements

### Required Columns

Your CSV file(s) must contain the following columns:

- `Open Time` - Trade opening timestamp
- `Close Time` - Trade closing timestamp
- `Position ID` - Unique identifier for the position
- `Side` - Direction of trade (`BUY` or `SELL`)
- `Instrument` - Trading instrument/symbol (e.g., `NAS100`, `US30`, `EURUSD`)
- `Lots` - Position size in lots
- `Open Price` - Entry price
- `Close Price` - Exit price

### Optional Columns

- `Stop Loss` - Stop loss level (required for some rule validations)
- `Take Profit` - Take profit level
- `PnL` - Profit/Loss
- `Net PnL` - Net Profit/Loss after fees
- `Fee` - Trading fees
- `Swap` - Swap/rollover charges
- `Duration` - Trade duration (will be calculated if not provided)

### Data Quality Requirements

- At least **95% of rows must be valid** for the file to be accepted
- All timestamps must be parseable
- Numerical fields must contain valid numbers
- `Open Time` must be before `Close Time` (will be auto-swapped if incorrect)

### Example CSV Format

```csv
Open Time,Close Time,Position ID,Side,Instrument,Lots,Open Price,Close Price,PnL,Net PnL,Stop Loss,Take Profit
"10/22/2025, 03:34:13.000 PM","10/22/2025, 03:34:40.000 PM",7277816997851545485,SELL,NAS100,0.02,24890.8,24870.2,41.2,41.2,-,24869.98
"10/22/2025, 03:11:29.000 PM","10/22/2025, 03:22:13.000 PM",7277816997851543042,SELL,NAS100,0.02,24982.7,24905,155.4,155.4,24966.2,24905.55
```

## 🎯 Account Types

### 2-Step Challenge Phase 1
- **Leverage**: 1:100
- **News Trading Add-on**: Available
- **Weekend Holding Add-on**: Available
- **Minimum Trading Days**: None
- **Active Rules**: All standard rules (Rules 18 & 19 become informational if respective add-on enabled)

### 2-Step Challenge Phase 2
- **Leverage**: 1:100
- **News Trading Add-on**: Available
- **Weekend Holding Add-on**: Available
- **Minimum Trading Days**: None
- **Active Rules**: All standard rules (Rules 18 & 19 become informational if respective add-on enabled)

### Funded Phase
- **Leverage**: 1:50
- **News Trading Add-on**: Available
- **Weekend Holding Add-on**: Available
- **Minimum Trading Days**: 4
- **Active Rules**: All standard rules (Rules 18 & 19 become informational if respective add-on enabled)

### Direct Funding
- **Leverage**: 1:30
- **News Trading Add-on**: Available
- **Weekend Holding Add-on**: Available
- **Minimum Trading Days**: 7
- **Active Rules**: All rules including Rule 17 (Max 2% Risk) (Rules 18 & 19 become informational if respective add-on enabled)

## 📜 Trading Rules

### Rule 1: Hedging Ban
Prohibits holding simultaneous long and short positions on the same instrument. Any overlap of 1 second or more is a violation.

### Rule 3: Strategy Consistency
Requires consistent trading behavior between evaluation and funded phases. Compares:
- Median trade duration
- Average trades per day
- Median risk per trade

**Violation**: If 2 out of 3 metrics differ by ≥200% between phases.

### Rule 4: Prohibited Third-Party Strategies (EAs)
Detects use of automated trading systems. 

**Violation**: If ≥10 trades show identical patterns (SL, TP, duration, lot size) across ≥3 distinct days.

### Rule 12: All-or-Nothing Trading
Prevents risking the entire account on single trades or trade groups.

**Violation**: If total risk ≥100% of account equity.

### Rule 13: Maximum Margin Usage
Limits margin usage to maintain adequate reserve.

**Violation**: If margin usage >80.1% at any point.

### Rule 14: Gambling Definition
Prevents excessive scalping behavior.

**Violation**: If >50% of trades are held for <60 seconds.

### Rule 15: One-Sided Bets
Limits simultaneous same-direction positions.

**Violation**: If ≥3 trades in same direction on same symbol overlap.

### Rule 16: Abuse of Simulated Environment
Detects volume manipulation and reckless trading.

**Violation**: If volume ≥10× equity in 24 hours AND ≥80% of trades opened without stop loss.

### Rule 17: Max 2% Risk per Trade Idea (Direct Funding Only)
Limits risk per trade idea to 2% of equity.

**Violation**: If trade idea risk >2.05% of equity.

### Rule 18: News Trading Restriction
Prohibits trading around major economic news releases.

**Violation**: Trading within ±5 minutes of relevant high-impact news (becomes informational if News Trading Add-on is enabled).

### Rule 19: Weekend Trading and Holding
Prohibits weekend trading (Friday 22:00 UTC - Sunday 22:00 UTC).

**Violation**: Trading or holding positions during weekend window (becomes informational if Weekend Holding Add-on is enabled).

**Violation**: Opening, closing, or holding positions during weekend window (skipped if add-on enabled).

### Rule 23: Minimum Trading Days
Requires minimum number of active trading days.

**Violation**: 
- Funded Phase: <4 days
- Direct Funding: <7 days
- Phase 1/2: No minimum

## 🎨 Using the Dashboard

### Step 1: Configure Account
1. Select your **account type** from the sidebar
2. Choose your **account size**
3. Enable **News Trading Add-on** if needed (available for all account types)
4. Enable **Weekend Holding Add-on** if needed (available for all account types)
   - Both add-ons work independently
   - When enabled, respective rules (18 & 19) become informational only

### Step 2: Upload Files
1. Click **"Browse files"** to upload CSV file(s)
2. For each file, select the **phase** it represents:
   - Single Phase (for single file analysis)
   - Phase 1 (evaluation phase 1)
   - Phase 2 (evaluation phase 2)
   - Funded Phase (funded account)

### Step 3: Run Validation
1. Review the configuration summary
2. Click **"🚀 Run Validation"** button
3. Wait for validation to complete (progress bar will show status)

### Step 4: Review Results
- **Summary Metrics**: View total trades, rules tested, pass/fail counts
- **Results Table**: See all rules with color-coded status
- **Violation Details**: Expand violated rules to see detailed information
- **Text Summary**: Read human-readable violation descriptions

### Step 5: Export Results
- **CSV Export**: Downloads TWO CSV files:
  1. **Summary CSV**: Overall rule results with normalized status ([PASSED]/[VIOLATED]/[NOT TESTABLE])
  2. **Violations CSV**: Detailed breakdown of all violations with affected trade information
- **PDF Export**: Professional report with comprehensive violation details, trade-level summaries, and formatted tables

## 🔧 Troubleshooting

### Common Issues

**Issue**: "Missing required columns" error
- **Solution**: Ensure your CSV has all required columns with exact names (case-sensitive)

**Issue**: "Only X% of rows are valid" error
- **Solution**: Check for:
  - Invalid dates/times
  - Non-numeric values in price/lot fields
  - Missing required data

**Issue**: Rule 3 shows "Not Testable"
- **Solution**: Upload separate CSV files for Phase 1 and Phase 2, each with at least 20 trades

**Issue**: Rule 18 shows "Not Testable"
- **Solution**: Rule 18 requires fetching news data from ForexFactory. If the API is unavailable or there are network issues, the rule becomes non-testable. Enable the News Trading Add-on to make this rule informational only.

**Issue**: Dashboard is slow with large files
- **Solution**: 
  - Split very large CSV files into multiple smaller files
  - Close other browser tabs
  - Refresh the page if needed

## 📊 Technical Details

### Technology Stack
- **Framework**: Streamlit 1.28.0+
- **Data Processing**: Pandas 2.0.0+, NumPy 1.24.0+
- **Timezone Handling**: pytz 2023.3+, python-dateutil 2.8.2+
- **Web Scraping**: requests, beautifulsoup4, lxml (for Rule 18 news data)
- **PDF Generation**: fpdf2 2.7.6+
- **Python Version**: 3.11+ recommended

### Data Processing
- All timestamps converted to UTC internally
- Display timestamps shown in Europe/Zurich timezone
- 95% validation threshold for data quality
- Tolerances:
  - Time: ±1 second
  - Price: ±0.00001
  - Lot size: ±0.0001

### Export Features
- **CSV**: 
  - Deterministic column ordering
  - Normalized status values for machine readability
  - Clean data with proper type coercion
  - Separate detailed violations file with trade-level information
- **PDF**: 
  - ASCII-safe text encoding (Unicode symbols converted)
  - Automatic page break management
  - Comprehensive violation summaries
  - Trade-level detail tables

## 📝 Project Structure

```
trading_rule/
├── app.py                 # Main Streamlit application (~860 lines)
├── dashboard_utils.py     # Utility functions for dashboard
├── rule_executor.py       # Rule execution coordinator
├── requirements.txt       # Python dependencies (simplified)
├── README.md             # This file
├── .gitignore            # Git exclusion rules
├── Trades121.csv         # Sample data file
├── rules/                # Rule validation modules
│   ├── config.py         # Configuration constants and account types
│   ├── utils.py          # Shared utilities
│   ├── Rule_1.py         # Hedging Ban
│   ├── Rule_3.py         # Strategy Consistency
│   ├── Rule_4.py         # Prohibited EAs
│   ├── Rule_12.py        # All-or-Nothing Trading
│   ├── Rule_13.py        # Maximum Margin Usage
│   ├── Rule_14.py        # Gambling Definition
│   ├── Rule_15.py        # One-Sided Bets
│   ├── Rule_16.py        # Abuse of Environment
│   ├── Rule_17.py        # Max 2% Risk (Direct Funding only)
│   ├── Rule_18.py        # News Trading (with ForexFactory scraping)
│   ├── Rule_19.py        # Weekend Trading
│   └── Rule_23.py        # Minimum Trading Days
└── Temp/                 # Archived/unused files (excluded from git)
```

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the sample CSV format
3. Ensure all requirements are met
4. Check the terminal/console for detailed error messages

## 📄 License

This project is proprietary software for trading compliance validation.

## 🔄 Version History

**Version 1.0.2** (October 2025)
- 🔧 **Rule 16 Final Compliance Updates**:
  - **"No SL" detection**: Now treats both `NaN` and `0` as missing Stop Loss (consistent with risk calculations elsewhere)
  - **Instrument-specific contract sizes**: Notional volume calculation now uses correct contract sizes per instrument
    - Gold (XAUUSD): 100 oz per lot
    - Silver (XAGUSD): 5,000 oz per lot
    - Indices (NAS100, US30, etc.): 1 unit per lot
    - Forex pairs: 100,000 units per lot (standard)
    - Oil (USOIL, UKOIL): 1,000 barrels per lot
  - **Suffix handling**: Correctly strips instrument suffixes (e.g., `XAUUSD.a` → `XAUUSD`)
  - Rule 16 is now **fully compliant** with project specification

**Version 1.0.1** (October 2025)
- 🔧 **Rule 16 Fix**: Corrected volume calculation to use notional volume (currency) instead of lots
  - Now properly compares total traded value ($) against 10× equity ($)
  - Formula: `notional_volume = lots × contract_size × price`
  - This aligns with the spec's definition of "volume" as traded value

**Version 1.0.0** (October 2025)
- ✅ Initial release with full rule validation suite
- ✅ 11 trading rules implemented and tested
- ✅ Dual CSV export (summary + detailed violations)
- ✅ Professional PDF reports with comprehensive violation details
- ✅ Multi-phase support (Phase 1, Phase 2, Funded)
- ✅ Independent News Trading and Weekend Holding add-ons
- ✅ Add-ons available for all account types (2-Step, Funded, Direct Funding)
- ✅ Enhanced data quality validation (95% threshold)
- ✅ Comprehensive error handling and logging
- ✅ Timezone-aware processing (UTC ↔ Europe/Zurich)
- ✅ ForexFactory news data integration (Rule 18)

---

**Built with ❤️ for prop trading compliance validation**
