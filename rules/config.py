"""
Configuration file for Trading Rule Validation App
Contains all constants, account configurations, and tolerances
"""

# ============================================================================
# ACCOUNT CONFIGURATIONS
# ============================================================================

ACCOUNT_TYPES = {
    "2-Step Phase 1": {
        "leverage": 100,
        "contract_size": "standard",
        "news_addon_allowed": True,
        "weekend_addon_allowed": True,
        "min_trading_days": 0
    },
    "2-Step Phase 2": {
        "leverage": 100,
        "contract_size": "standard",
        "news_addon_allowed": True,
        "weekend_addon_allowed": True,
        "min_trading_days": 0
    },
    "Funded Phase": {
        "leverage": 50,
        "contract_size": "standard",
        "news_addon_allowed": True,
        "weekend_addon_allowed": True,
        "min_trading_days": 4
    },
    "Direct Funding": {
        "leverage": 30,
        "contract_size": "standard",
        "news_addon_allowed": True,
        "weekend_addon_allowed": True,
        "min_trading_days": 7
    }
}

# Available account sizes
ACCOUNT_SIZES = [5000, 10000, 20000, 25000, 35000, 50000, 100000, 150000, 200000]

# ============================================================================
# CONTRACT SIZES AND VALUE PER POINT
# ============================================================================

# Standard lot sizes (units of base currency)
CONTRACT_SIZES = {
    "standard": 100000,
    "mini": 10000,
    "micro": 1000
}

# Value per point/pip for different instruments
# This determines how much 1 point movement equals in USD
VALUE_PER_POINT = {
    # Forex pairs (per 0.01 lot)
    "EURUSD": 0.1,  # $10 per pip for 1 standard lot
    "GBPUSD": 0.1,
    "USDJPY": 0.1,
    "USDCHF": 0.1,
    "AUDUSD": 0.1,
    "NZDUSD": 0.1,
    "USDCAD": 0.1,
    
    # Indices (per 0.01 lot)
    "US30": 0.1,     # Dow Jones - $1 per point for 1 lot
    "NAS100": 0.2,   # Nasdaq - $2 per point for 1 lot
    "SPX500": 0.1,   # S&P 500
    "GER40": 0.1,    # DAX
    "UK100": 0.1,    # FTSE
    
    # Commodities
    "XAUUSD": 0.1,   # Gold - $1 per pip for 1 lot
    "XAGUSD": 0.1,   # Silver
    "USOIL": 0.1,    # Crude Oil
    "UKOIL": 0.1,    # Brent Oil
}

# ============================================================================
# GLOBAL TOLERANCES
# ============================================================================

TOLERANCES = {
    "time": 1,          # ±1 second
    "price": 0.00001,   # ±0.00001 for price comparisons
    "lots": 0.0001,     # ±0.0001 for lot size comparisons
}

# ============================================================================
# RULE-SPECIFIC CONSTANTS
# ============================================================================

# Rule 1: Hedging Ban
HEDGING_MIN_OVERLAP_SECONDS = 1

# Rule 3: Strategy Consistency
STRATEGY_CONSISTENCY_MIN_TRADES = 20
STRATEGY_CONSISTENCY_THRESHOLD = 3.0  # 200% difference = 3x ratio

# Rule 4: Prohibited EAs
EA_DETECTION_MIN_TRADES = 10
EA_DETECTION_MIN_DAYS = 3

# Rule 12: All-or-Nothing Trading
MAX_RISK_PERCENT = 100.0  # 100% of equity

# Rule 13: Maximum Margin Usage
MAX_MARGIN_USAGE_PERCENT = 80.1  # >80.1% is violation

# Rule 14: Gambling Definition
GAMBLING_THRESHOLD_SECONDS = 60
GAMBLING_THRESHOLD_PERCENT = 50.0  # >50% of trades

# Rule 15: One-Sided Bets
MAX_SAME_DIRECTION_TRADES = 2  # 3 or more is violation

# Rule 16: Abuse of Simulated Environment
ABUSE_VOLUME_MULTIPLIER = 10  # 10x equity
ABUSE_NO_SL_THRESHOLD = 80.0  # 80% without SL
ABUSE_WINDOW_HOURS = 24

# Rule 17: Max 2% Risk per Trade Idea
MAX_RISK_PERCENT_DIRECT = 2.05  # >2.05% is violation
TRADE_IDEA_GAP_SECONDS = 300  # 5 minutes
TRADE_IDEA_GAP_XAUUSD_SECONDS = 60  # 60 seconds for XAUUSD

# Rule 18: News Trading Restriction
NEWS_BUFFER_SECONDS = 300  # ±5 minutes (300 seconds)

# Rule 19: Weekend Trading
WEEKEND_START_DAY = 4  # Friday (0=Monday)
WEEKEND_START_HOUR = 22  # 22:00 UTC
WEEKEND_END_DAY = 6  # Sunday
WEEKEND_END_HOUR = 22  # 22:00 UTC

# ============================================================================
# CSV COLUMN NAMES
# ============================================================================

REQUIRED_COLUMNS = [
    "Open Time",
    "Close Time",
    "Position ID",
    "Side",
    "Instrument",
    "Lots",
    "Open Price",
    "Close Price"
]

OPTIONAL_COLUMNS = [
    "PnL",
    "Net PnL",
    "Fee",
    "Swap",
    "Stop Loss",
    "Take Profit",
    "Close Order ID",
    "Close Trade ID",
    "Open Order ID",
    "Duration"
]

# ============================================================================
# OUTPUT FORMATS
# ============================================================================

STATUS_PASSED = "✅ PASSED"
STATUS_VIOLATED = "❌ VIOLATED"
STATUS_NOT_TESTABLE = "⚠️ NOT TESTABLE"

# ============================================================================
# TIMEZONE SETTINGS
# ============================================================================

INTERNAL_TIMEZONE = "UTC"
DISPLAY_TIMEZONE = "Europe/Zurich"
