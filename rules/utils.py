"""
Utility functions for Trading Rule Validation
Shared helper functions used across all rule scripts
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Tuple, Optional
import config

def load_csv(file_path: str) -> pd.DataFrame:
    """
    Load and perform basic validation on CSV file
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        DataFrame with parsed data
    """
    try:
        df = pd.read_csv(file_path)
        
        # Check for required columns
        missing_columns = [col for col in config.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Parse datetime columns - try multiple formats
        for col in ['Open Time', 'Close Time']:
            try:
                # Try US format first (original format)
                df[col] = pd.to_datetime(df[col], format='%m/%d/%Y, %I:%M:%S.%f %p')
            except (ValueError, pd.errors.ParserError):
                try:
                    # Try ISO format without microseconds
                    df[col] = pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S')
                except (ValueError, pd.errors.ParserError):
                    try:
                        # Try ISO8601 format
                        df[col] = pd.to_datetime(df[col], format='ISO8601')
                    except (ValueError, pd.errors.ParserError):
                        # Last resort: let pandas infer the format
                        df[col] = pd.to_datetime(df[col], format='mixed')
        
        # Convert to UTC (assuming input is in UTC or handle timezone as needed)
        df['Open Time'] = df['Open Time'].dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='infer')
        df['Close Time'] = df['Close Time'].dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='infer')
        
        # Handle Stop Loss and Take Profit (might contain '-' for missing values)
        if 'Stop Loss' in df.columns:
            df['Stop Loss'] = pd.to_numeric(df['Stop Loss'], errors='coerce')
        
        if 'Take Profit' in df.columns:
            df['Take Profit'] = pd.to_numeric(df['Take Profit'], errors='coerce')
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['Lots', 'Open Price', 'Close Price', 'PnL']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Swap Open/Close times if necessary
        swapped = df['Open Time'] > df['Close Time']
        if swapped.any():
            print(f"Warning: {swapped.sum()} rows had Open Time > Close Time. Swapping...")
            df.loc[swapped, ['Open Time', 'Close Time']] = df.loc[swapped, ['Close Time', 'Open Time']].values
        
        # Calculate duration in seconds
        df['Duration_Seconds'] = (df['Close Time'] - df['Open Time']).dt.total_seconds()
        
        return df
        
    except Exception as e:
        raise Exception(f"Error loading CSV: {str(e)}")


def validate_csv_quality(df: pd.DataFrame, min_valid_percent: float = 95.0) -> Tuple[bool, List[str]]:
    """
    Validate that at least 95% of rows are valid
    
    Args:
        df: DataFrame to validate
        min_valid_percent: Minimum percentage of valid rows required
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    total_rows = len(df)
    
    if total_rows == 0:
        return False, ["No data rows found in CSV"]
    
    # Check for null values in required columns
    for col in config.REQUIRED_COLUMNS:
        null_count = df[col].isna().sum()
        if null_count > 0:
            errors.append(f"Column '{col}' has {null_count} null values")
    
    # Count invalid rows (rows with any null in required columns)
    invalid_rows = df[config.REQUIRED_COLUMNS].isna().any(axis=1).sum()
    valid_percent = ((total_rows - invalid_rows) / total_rows) * 100
    
    if valid_percent < min_valid_percent:
        errors.append(f"Only {valid_percent:.1f}% of rows are valid (minimum required: {min_valid_percent}%)")
        return False, errors
    
    return True, errors


def check_time_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> Tuple[bool, float]:
    """
    Check if two time intervals overlap by at least 1 second
    
    Args:
        start1, end1: First interval
        start2, end2: Second interval
        
    Returns:
        Tuple of (has_overlap, overlap_duration_seconds)
    """
    # Find the overlap window
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    # Calculate overlap duration
    overlap_seconds = (overlap_end - overlap_start).total_seconds()
    
    # Apply tolerance
    has_overlap = overlap_seconds >= config.HEDGING_MIN_OVERLAP_SECONDS
    
    return has_overlap, max(0, overlap_seconds)


def calculate_sl_distance(entry_price: float, stop_loss: float, side: str) -> float:
    """
    Calculate the distance from entry to stop loss
    
    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        side: 'BUY' or 'SELL'
        
    Returns:
        Absolute distance
    """
    if pd.isna(stop_loss):
        return np.nan
    
    return abs(entry_price - stop_loss)


def calculate_tp_distance(entry_price: float, take_profit: float, side: str) -> float:
    """
    Calculate the distance from entry to take profit
    
    Args:
        entry_price: Entry price
        take_profit: Take profit price
        side: 'BUY' or 'SELL'
        
    Returns:
        Absolute distance
    """
    if pd.isna(take_profit):
        return np.nan
    
    return abs(entry_price - take_profit)


def calculate_trade_risk(entry_price: float, stop_loss: float, lots: float, 
                        instrument: str, equity: float) -> Tuple[float, float]:
    """
    Calculate the risk of a trade in dollars and as percentage of equity
    
    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        lots: Position size in lots
        instrument: Trading instrument
        equity: Account equity at trade entry
        
    Returns:
        Tuple of (risk_dollars, risk_percent)
    """
    if pd.isna(stop_loss) or stop_loss == 0:
        return np.nan, np.nan
    
    # Get value per point for the instrument
    value_per_point = get_value_per_point(instrument)
    
    # Calculate SL distance
    sl_distance = abs(entry_price - stop_loss)
    
    # Calculate risk in dollars
    # Risk = SL distance × Position size × Value per point
    risk_dollars = sl_distance * lots * value_per_point * 100  # *100 to scale for lots
    
    # Calculate risk as percentage of equity
    risk_percent = (risk_dollars / equity) * 100 if equity > 0 else np.nan
    
    return risk_dollars, risk_percent


def get_value_per_point(instrument: str) -> float:
    """
    Get the value per point/pip for an instrument
    
    Args:
        instrument: Trading instrument symbol
        
    Returns:
        Value per point (for 0.01 lot)
    """
    # Try exact match first
    if instrument in config.VALUE_PER_POINT:
        return config.VALUE_PER_POINT[instrument]
    
    # Try partial match (e.g., EURUSD.a -> EURUSD)
    for key in config.VALUE_PER_POINT:
        if instrument.startswith(key):
            return config.VALUE_PER_POINT[key]
    
    # Default value if not found
    print(f"Warning: No value per point configured for {instrument}, using default 0.1")
    return 0.1


def calculate_margin_required(lots: float, instrument: str, price: float, leverage: int) -> float:
    """
    Calculate the margin required for a position
    
    Args:
        lots: Position size in lots
        instrument: Trading instrument
        price: Current price
        leverage: Account leverage
        
    Returns:
        Required margin in account currency
    """
    # Get contract size
    contract_size = config.CONTRACT_SIZES["standard"]
    
    # Calculate notional value
    notional_value = lots * contract_size * price
    
    # Calculate required margin
    required_margin = notional_value / leverage
    
    return required_margin


def calculate_notional_volume(lots: float, instrument: str, price: float) -> float:
    """
    Calculate notional volume (traded value in currency)
    
    Args:
        lots: Position size in lots
        instrument: Trading instrument/symbol (e.g., "XAUUSD", "NAS100", "EURUSD.a")
        price: Entry price
        
    Returns:
        Notional volume in currency (USD)
    """
    # Clean instrument name (remove suffixes like .a, .b, etc.)
    instrument_base = instrument.split('.')[0].upper()
    
    # Get instrument-specific contract size, fallback to standard if not found
    contract_size = config.CONTRACT_SIZES.get(
        instrument_base, 
        config.CONTRACT_SIZES["standard"]
    )
    
    # Calculate notional value: lots × contract_size × price
    notional_value = abs(lots) * contract_size * price
    
    return notional_value


def get_distinct_trading_days(df: pd.DataFrame) -> int:
    """
    Count distinct trading days (days with at least one trade)
    
    Args:
        df: DataFrame with 'Open Time' column
        
    Returns:
        Number of distinct trading days
    """
    return df['Open Time'].dt.date.nunique()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h, 15m, 30s")
    """
    if pd.isna(seconds):
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return ", ".join(parts)


def export_results_to_csv(results: Dict, output_file: str):
    """
    Export rule results to CSV file
    
    Args:
        results: Dictionary containing rule results
        output_file: Output CSV file path
    """
    df = pd.DataFrame([results])
    df.to_csv(output_file, index=False)
    print(f"Results exported to: {output_file}")


def print_rule_header(rule_number: int, rule_name: str):
    """
    Print a formatted header for rule output
    
    Args:
        rule_number: Rule number
        rule_name: Rule name
    """
    print("\n" + "=" * 80)
    print(f"RULE {rule_number}: {rule_name}")
    print("=" * 80 + "\n")


def print_rule_result(status: str, message: str, details: Optional[Dict] = None):
    """
    Print formatted rule result
    
    Args:
        status: Rule status (PASSED, VIOLATED, NOT TESTABLE)
        message: Result message
        details: Optional dictionary with additional details
    """
    print(f"Status: {status}")
    print(f"Result: {message}\n")
    
    if details:
        print("Details:")
        for key, value in details.items():
            print(f"  - {key}: {value}")
    
    print("\n" + "-" * 80 + "\n")


def get_instrument_currency_pairs(instrument: str) -> Tuple[str, str]:
    """
    Extract base and quote currency from instrument symbol
    
    Args:
        instrument: Trading instrument (e.g., 'EURUSD', 'XAUUSD')
        
    Returns:
        Tuple of (base_currency, quote_currency)
    """
    # Handle special cases
    if instrument.startswith('XAU'):
        return 'XAU', 'USD'  # Gold
    elif instrument.startswith('XAG'):
        return 'XAG', 'USD'  # Silver
    
    # Standard forex pairs
    if len(instrument) >= 6:
        return instrument[:3], instrument[3:6]
    
    # Indices and other instruments don't have currency pairs
    return None, None


def is_weekend(dt: datetime) -> bool:
    """
    Check if a datetime falls within the weekend trading ban window
    Friday 22:00 UTC to Sunday 22:00 UTC
    
    Args:
        dt: Datetime to check (should be UTC)
        
    Returns:
        True if within weekend window
    """
    # Ensure datetime is in UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    
    day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
    hour = dt.hour
    
    # Friday after 22:00
    if day_of_week == 4 and hour >= 22:
        return True
    
    # All day Saturday
    if day_of_week == 5:
        return True
    
    # Sunday before 22:00
    if day_of_week == 6 and hour < 22:
        return True
    
    return False


def get_weekend_windows(start_date: datetime, end_date: datetime) -> list:
    """
    Generate all weekend window periods between start and end dates
    Weekend window: Friday 22:00 UTC to Sunday 22:00 UTC
    
    Args:
        start_date: Start datetime (UTC)
        end_date: End datetime (UTC)
        
    Returns:
        List of tuples (weekend_start, weekend_end) covering the date range
    """
    # Ensure UTC
    if start_date.tzinfo is None:
        start_date = pytz.UTC.localize(start_date)
    else:
        start_date = start_date.astimezone(pytz.UTC)
    
    if end_date.tzinfo is None:
        end_date = pytz.UTC.localize(end_date)
    else:
        end_date = end_date.astimezone(pytz.UTC)
    
    weekend_windows = []
    
    # Start from the first Friday at or before start_date
    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Go back to find the previous or current Friday
    days_since_friday = (current.weekday() - 4) % 7
    current = current - pd.Timedelta(days=days_since_friday)
    
    # Generate weekend windows
    while current <= end_date + pd.Timedelta(days=7):
        # Friday 22:00 UTC
        weekend_start = current.replace(hour=22, minute=0, second=0, microsecond=0)
        
        # Sunday 22:00 UTC (2 days later)
        weekend_end = weekend_start + pd.Timedelta(days=2)
        
        # Only include if it overlaps with our date range
        if weekend_end >= start_date and weekend_start <= end_date:
            weekend_windows.append((weekend_start, weekend_end))
        
        # Move to next Friday
        current = current + pd.Timedelta(days=7)
    
    return weekend_windows
    
    return False
