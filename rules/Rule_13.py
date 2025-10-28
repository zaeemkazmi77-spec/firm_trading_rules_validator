"""
Rule 13: Maximum Margin Usage (80%)

Used margin must never exceed 80% of account equity.
If margin usage > 80.1% → Violation.
Otherwise → No violation.
This ensures at least 20% equity reserve.
"""

import pandas as pd
import sys
import numpy as np
import config
import utils

def check_margin_usage(df: pd.DataFrame, account_equity: float, account_type: str = "Funded Phase") -> dict:
    """
    Check for margin usage violations
    
    Args:
        df: DataFrame with trade data
        account_equity: Account equity
        account_type: Type of account (determines leverage)
        
    Returns:
        Dictionary with rule results
    """
    # Get leverage for account type
    leverage = config.ACCOUNT_TYPES[account_type]['leverage']
    
    # Sort trades by open time
    df_sorted = df.sort_values('Open Time').copy()
    
    violations = []
    
    # Track open positions at each point in time
    # We need to check margin usage whenever a trade opens or closes
    check_points = []
    
    # Collect all time points where we need to check margin
    for _, trade in df_sorted.iterrows():
        check_points.append(('open', trade['Open Time'], trade))
        check_points.append(('close', trade['Close Time'], trade))
    
    # Sort check points by time
    check_points.sort(key=lambda x: x[1])
    
    # Check margin usage at each point
    for event_type, timestamp, current_trade in check_points:
        # Find all trades that are open at this timestamp
        open_trades = df_sorted[
            (df_sorted['Open Time'] <= timestamp) & 
            (df_sorted['Close Time'] > timestamp)
        ]
        
        if len(open_trades) == 0:
            continue
        
        # Calculate total margin required
        total_margin = 0
        for _, trade in open_trades.iterrows():
            margin = utils.calculate_margin_required(
                trade['Lots'],
                trade['Instrument'],
                trade['Open Price'],
                leverage
            )
            total_margin += margin
        
        # Calculate margin usage percentage
        margin_usage_percent = (total_margin / account_equity) * 100 if account_equity > 0 else 0
        
        # Check for violation
        if margin_usage_percent > config.MAX_MARGIN_USAGE_PERCENT:
            # Build detailed positions string
            positions_detail = []
            for _, trade in open_trades.iterrows():
                margin = utils.calculate_margin_required(
                    trade['Lots'],
                    trade['Instrument'],
                    trade['Open Price'],
                    leverage
                )
                positions_detail.append(
                    f"Position {trade['Position ID']} ({trade['Instrument']}, {trade['Lots']} lots, "
                    f"margin: ${margin:,.2f})"
                )
            
            violation_reason = (
                f"MARGIN USAGE VIOLATION: At {timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({event_type.upper()} of Position {current_trade['Position ID']}), "
                f"total margin required for {len(open_trades)} open position(s) was ${total_margin:,.2f}, which is "
                f"{margin_usage_percent:.2f}% of the ${account_equity:,.2f} equity. This exceeds the maximum allowed "
                f"margin usage of {config.MAX_MARGIN_USAGE_PERCENT:.1f}%. "
                f"Open positions: {'; '.join(positions_detail)}. "
                f"[Rule 13: Maximum Margin Usage ≤80%]"
            )
            
            violations.append({
                'Timestamp': timestamp,
                'Event': event_type,
                'Trigger_Position_ID': current_trade['Position ID'],
                'Open_Positions': len(open_trades),
                'Total_Margin_Required': total_margin,
                'Account_Equity': account_equity,
                'Margin_Usage_Percent': margin_usage_percent,
                'Leverage': leverage,
                'Violation_Reason': violation_reason
            })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 13,
        'rule_name': 'Maximum Margin Usage (80%)',
        'status': status,
        'total_trades': len(df),
        'violations_found': len(violations),
        'violations': violations,
        'account_equity': account_equity,
        'leverage': leverage
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Account Equity: ${result['account_equity']:,.2f}")
    print(f"Account Leverage: 1:{result['leverage']}")
    print(f"Total trades: {result['total_trades']}")
    print(f"Maximum allowed margin usage: {config.MAX_MARGIN_USAGE_PERCENT:.1f}%")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} instance(s) where margin usage exceeded 80%"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Timestamp: {violation['Timestamp']}")
            print(f"  Event: {violation['Event'].upper()}")
            print(f"  Trigger Position ID: {violation['Trigger_Position_ID']}")
            print(f"  Open Positions: {violation['Open_Positions']}")
            print(f"  Total Margin Required: ${violation['Total_Margin_Required']:,.2f}")
            print(f"  Account Equity: ${violation['Account_Equity']:,.2f}")
            print(f"  Margin Usage: {violation['Margin_Usage_Percent']:.2f}% ❌")
            print(f"  Leverage: 1:{violation['Leverage']}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No margin usage violations detected. Margin usage always stayed below 80%."
        )


def export_results(result: dict, output_prefix: str = "Rule_13"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Violations Found': result['violations_found'],
        'Account Equity': result['account_equity'],
        'Leverage': f"1:{result['leverage']}"
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    # Export violations if any
    if result.get('violations'):
        violations_df = pd.DataFrame(result['violations'])
        violations_df.to_csv(f"{output_prefix}_violations.csv", index=False)
        print(f"Violations exported to: {output_prefix}_violations.csv")


def main():
    """Main execution function"""
    # Check command line arguments
    if len(sys.argv) >= 4:
        csv_file = sys.argv[1]
        account_equity = float(sys.argv[2])
        account_type = sys.argv[3]
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        account_equity = 100000  # Default
        account_type = "Funded Phase"  # Default
        print(f"⚠️  Using defaults - Equity: ${account_equity:,.2f}, Type: {account_type}")
        print("Usage: python Rule_13.py <csv_file> <account_equity> <account_type>")
        print('Example: python Rule_13.py Trades121.csv 100000 "Funded Phase"\n')
    
    print(f"Loading data from: {csv_file}")
    
    try:
        # Load CSV
        df = utils.load_csv(csv_file)
        print(f"Successfully loaded {len(df)} trades\n")
        
        # Validate CSV quality
        is_valid, errors = utils.validate_csv_quality(df)
        if not is_valid:
            print("CSV Validation Failed:")
            for error in errors:
                print(f"  - {error}")
            return
        
        # Check for margin usage violations
        result = check_margin_usage(df, account_equity, account_type)
        
        # Print results
        print_results(result)
        
        # Export results
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
