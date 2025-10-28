"""
Utility functions for the Trading Rule Validation Dashboard
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from typing import Tuple, Dict, List, Any
import streamlit as st
from rules import config, utils as rule_utils


def validate_csv_file(df: pd.DataFrame, filename: str) -> Tuple[bool, pd.DataFrame, List[str]]:
    """
    Validate uploaded CSV file
    
    Args:
        df: DataFrame to validate
        filename: Name of the file being validated
        
    Returns:
        Tuple of (is_valid, cleaned_df, error_messages)
    """
    errors = []
    valid_rows = []
    total_rows = len(df)
    
    # Check required columns
    missing_columns = [col for col in config.REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return False, df, errors
    
    # Validate each row
    for idx, row in df.iterrows():
        row_errors = []
        
        # Validate time columns
        try:
            open_time = pd.to_datetime(row['Open Time'], utc=True)
        except:
            row_errors.append(f"Invalid Open Time format")
        
        try:
            close_time = pd.to_datetime(row['Close Time'], utc=True)
        except:
            row_errors.append(f"Invalid Close Time format")
        
        # Check time order (and swap if needed)
        if not row_errors:
            if open_time > close_time:
                # Swap times
                df.at[idx, 'Open Time'] = close_time
                df.at[idx, 'Close Time'] = open_time
                st.warning(f"Row {idx+1}: Swapped Open Time and Close Time (Open was after Close)")
        
        # Validate numerical fields
        numerical_fields = ['Lots', 'Open Price', 'Close Price']
        for field in numerical_fields:
            try:
                value = pd.to_numeric(row[field])
                if pd.isna(value) or value <= 0:
                    row_errors.append(f"Invalid {field}: {row[field]}")
            except:
                row_errors.append(f"Invalid {field} format: {row[field]}")
        
        # Validate Position ID
        if pd.isna(row['Position ID']):
            row_errors.append("Missing Position ID")
        
        # Validate Side
        if row['Side'] not in ['BUY', 'SELL']:
            row_errors.append(f"Invalid Side: {row['Side']}")
        
        # Validate Instrument
        if pd.isna(row['Instrument']) or str(row['Instrument']).strip() == '':
            row_errors.append("Missing Instrument")
        
        # Clean Stop Loss and Take Profit - convert "-" to NaN
        if 'Stop Loss' in df.columns:
            if pd.notna(row['Stop Loss']) and str(row['Stop Loss']).strip() == '-':
                df.at[idx, 'Stop Loss'] = np.nan
            else:
                try:
                    df.at[idx, 'Stop Loss'] = pd.to_numeric(row['Stop Loss'], errors='coerce')
                except:
                    df.at[idx, 'Stop Loss'] = np.nan
        
        if 'Take Profit' in df.columns:
            if pd.notna(row['Take Profit']) and str(row['Take Profit']).strip() == '-':
                df.at[idx, 'Take Profit'] = np.nan
            else:
                try:
                    df.at[idx, 'Take Profit'] = pd.to_numeric(row['Take Profit'], errors='coerce')
                except:
                    df.at[idx, 'Take Profit'] = np.nan
        
        if row_errors:
            errors.append(f"Row {idx+1}: {'; '.join(row_errors)}")
        else:
            valid_rows.append(idx)
    
    # Check if at least 95% of rows are valid
    valid_percent = (len(valid_rows) / total_rows) * 100 if total_rows > 0 else 0
    
    if valid_percent < 95:
        errors.insert(0, f"Only {valid_percent:.1f}% of rows are valid (minimum required: 95%)")
        return False, df, errors
    
    # Filter to valid rows
    if len(valid_rows) < total_rows:
        df_clean = df.loc[valid_rows].copy()
        errors.insert(0, f"Removed {total_rows - len(valid_rows)} invalid rows. {len(valid_rows)} valid rows remaining.")
    else:
        df_clean = df.copy()
    
    # Convert timestamps to UTC
    df_clean = convert_timestamps_to_utc(df_clean)
    
    return True, df_clean, errors


def convert_timestamps_to_utc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert all timestamp columns to UTC timezone
    
    Args:
        df: DataFrame with timestamp columns
        
    Returns:
        DataFrame with UTC timestamps
    """
    df = df.copy()
    
    time_columns = ['Open Time', 'Close Time']
    
    for col in time_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)
    
    # Calculate Duration_Seconds if not present
    if 'Duration_Seconds' not in df.columns:
        df['Duration_Seconds'] = (df['Close Time'] - df['Open Time']).dt.total_seconds()
    
    return df


def format_timestamp_zurich(timestamp: pd.Timestamp) -> str:
    """
    Format timestamp in Europe/Zurich timezone
    
    Args:
        timestamp: UTC timestamp
        
    Returns:
        Formatted string in Zurich timezone
    """
    if pd.isna(timestamp):
        return "N/A"
    
    zurich_tz = pytz.timezone('Europe/Zurich')
    zurich_time = timestamp.astimezone(zurich_tz)
    return zurich_time.strftime('%Y-%m-%d %H:%M:%S %Z')


def group_files_by_phase(uploaded_files: Dict) -> Dict[str, pd.DataFrame]:
    """
    Group uploaded files by phase and merge DataFrames
    
    Args:
        uploaded_files: Dictionary of uploaded files with phase labels
        
    Returns:
        Dictionary mapping phase names to merged DataFrames
    """
    phases = {}
    
    for filename, file_data in uploaded_files.items():
        phase = file_data['phase']
        file_obj = file_data['file']
        
        # Read CSV
        try:
            df = pd.read_csv(file_obj)
            
            if phase in phases:
                # Merge with existing phase data
                phases[phase] = pd.concat([phases[phase], df], ignore_index=True)
            else:
                phases[phase] = df
        except Exception as e:
            st.error(f"Error reading {filename}: {str(e)}")
    
    return phases


def get_account_configuration(account_type: str) -> Dict[str, Any]:
    """
    Get account configuration from config
    
    Args:
        account_type: Selected account type
        
    Returns:
        Dictionary with account configuration
    """
    return config.ACCOUNT_TYPES.get(account_type, {})


def determine_active_rules(account_type: str, addon_enabled: bool) -> List[int]:
    """
    Determine which rules should be active based on configuration
    
    Args:
        account_type: Selected account type
        addon_enabled: Whether add-on is enabled
        
    Returns:
        List of active rule numbers
    """
    all_rules = [1, 3, 4, 12, 13, 14, 15, 16, 17, 18, 19, 23]
    active_rules = []
    
    for rule_num in all_rules:
        # Skip Rules 18 & 19 if add-on is enabled
        if addon_enabled and rule_num in [18, 19]:
            continue
        
        # Rule 17 only for Direct Funding
        if rule_num == 17 and account_type != "Direct Funding":
            continue
        
        active_rules.append(rule_num)
    
    return active_rules


def get_rule_descriptions() -> Dict[int, Dict[str, str]]:
    """
    Get rule descriptions for display
    
    Returns:
        Dictionary mapping rule numbers to descriptions
    """
    return {
        1: {
            "name": "Hedging Ban",
            "description": "No simultaneous long and short positions on same instrument"
        },
        3: {
            "name": "Strategy Consistency",
            "description": "Trading behavior must be consistent between phases"
        },
        4: {
            "name": "Prohibited EAs",
            "description": "No use of automated trading systems"
        },
        12: {
            "name": "All-or-Nothing Trading",
            "description": "No single trade may risk entire account"
        },
        13: {
            "name": "Maximum Margin Usage",
            "description": "Margin usage must not exceed 80% of equity"
        },
        14: {
            "name": "Gambling Definition",
            "description": "Less than 50% of trades held under 60 seconds"
        },
        15: {
            "name": "One-Sided Bets",
            "description": "Max 2 trades in same direction on same symbol"
        },
        16: {
            "name": "Abuse of Simulated Environment",
            "description": "Volume and no-SL trading restrictions"
        },
        17: {
            "name": "Max 2% Risk per Trade Idea",
            "description": "Risk per trade idea limited to 2% (Direct Funding only)"
        },
        18: {
            "name": "News Trading Restriction",
            "description": "No trading within 5 minutes of news releases"
        },
        19: {
            "name": "Weekend Trading",
            "description": "No trading Friday 22:00 UTC to Sunday 22:00 UTC"
        },
        23: {
            "name": "Minimum Trading Days",
            "description": "Minimum trading days requirement based on account type"
        }
    }


def format_currency(value: float) -> str:
    """Format value as currency"""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:.2f}%"


def get_status_color(status: str) -> str:
    """Get color for status"""
    if "PASSED" in status:
        return "green"
    elif "VIOLATED" in status:
        return "red"
    else:
        return "orange"


def get_status_emoji(status: str) -> str:
    """Get emoji for status"""
    if "PASSED" in status:
        return "✅"
    elif "VIOLATED" in status:
        return "❌"
    else:
        return "⚠️"


def create_violation_summary_text(results: List[Dict]) -> str:
    """
    Create human-readable summary of violations
    
    Args:
        results: List of rule results
        
    Returns:
        Formatted text summary
    """
    summary_lines = []
    
    for result in results:
        if result.get('status') == config.STATUS_VIOLATED:
            rule_num = result.get('rule_number')
            rule_name = result.get('rule_name')
            
            summary_lines.append(f"\n{'='*80}")
            summary_lines.append(f"RULE {rule_num}: {rule_name} - VIOLATED")
            summary_lines.append('='*80)
            
            # Add violation reason if available
            if 'violation_reason' in result:
                summary_lines.append(f"\n{result['violation_reason']}")
            
            # Add specific violation details
            if 'violations' in result and result['violations']:
                summary_lines.append(f"\nTotal Violations: {len(result['violations'])}")
                
                for idx, violation in enumerate(result['violations'][:5], 1):  # Show first 5
                    if isinstance(violation, dict):
                        summary_lines.append(f"\nViolation #{idx}:")
                        
                        # Format violation details based on available data
                        if 'Violation_Reason' in violation:
                            summary_lines.append(f"  {violation['Violation_Reason']}")
                        elif 'violation_reason' in violation:
                            summary_lines.append(f"  {violation['violation_reason']}")
                
                if len(result['violations']) > 5:
                    summary_lines.append(f"\n... and {len(result['violations']) - 5} more violations")
    
    if not summary_lines:
        return "✅ All rules passed! No violations detected."
    
    return "\n".join(summary_lines)


def calculate_overall_status(results: List[Dict]) -> Tuple[str, Dict[str, int]]:
    """
    Calculate overall validation status
    
    Args:
        results: List of rule results
        
    Returns:
        Tuple of (overall_status, counts_dict)
    """
    passed = sum(1 for r in results if r.get('status') == config.STATUS_PASSED)
    violated = sum(1 for r in results if r.get('status') == config.STATUS_VIOLATED)
    not_testable = sum(1 for r in results if r.get('status') == config.STATUS_NOT_TESTABLE)
    
    counts = {
        'passed': passed,
        'violated': violated,
        'not_testable': not_testable,
        'total': len(results)
    }
    
    if violated > 0:
        overall = "FAILED"
    elif passed > 0 and violated == 0:
        overall = "PASSED"
    else:
        overall = "INCOMPLETE"
    
    return overall, counts
