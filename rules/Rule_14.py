"""
Rule 14: Gambling Definition

If more than 50% of all trades are held for less than 60 seconds, the account is 
classified as gambling → Violation.
If 50% or fewer are under 60 seconds → No violation.
Tolerance: ±1 second.
"""

import pandas as pd
import sys
import config
import utils

def check_gambling(df: pd.DataFrame) -> dict:
    """
    Check for gambling behavior (too many short-duration trades)
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Dictionary with rule results
    """
    total_trades = len(df)
    
    # Count trades held for less than 60 seconds (with tolerance)
    threshold = config.GAMBLING_THRESHOLD_SECONDS + config.TOLERANCES['time']
    short_trades = df[df['Duration_Seconds'] < threshold]
    short_trade_count = len(short_trades)
    
    # Calculate percentage
    short_trade_percent = (short_trade_count / total_trades * 100) if total_trades > 0 else 0
    
    # Check for violation
    is_violation = short_trade_percent > config.GAMBLING_THRESHOLD_PERCENT
    
    # Build detailed violation reason
    violation_reason = None
    if is_violation:
        violation_reason = (
            f"GAMBLING VIOLATION: {short_trade_count} out of {total_trades} trades ({short_trade_percent:.2f}%) "
            f"were held for less than {config.GAMBLING_THRESHOLD_SECONDS} seconds (±{config.TOLERANCES['time']}s tolerance), "
            f"which exceeds the maximum allowed threshold of {config.GAMBLING_THRESHOLD_PERCENT:.0f}%. "
            f"This pattern indicates gambling behavior rather than strategic trading. "
            f"[Rule 14: Gambling Definition - >50% trades <60s = Violation]"
        )
    
    status = config.STATUS_VIOLATED if is_violation else config.STATUS_PASSED
    
    return {
        'rule_number': 14,
        'rule_name': 'Gambling Definition',
        'status': status,
        'total_trades': total_trades,
        'short_trades_count': short_trade_count,
        'short_trades_percent': short_trade_percent,
        'threshold_seconds': config.GAMBLING_THRESHOLD_SECONDS,
        'threshold_percent': config.GAMBLING_THRESHOLD_PERCENT,
        'short_trades': short_trades,
        'violation_reason': violation_reason
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Total trades: {result['total_trades']}")
    print(f"Trades < {result['threshold_seconds']} seconds: {result['short_trades_count']}")
    print(f"Percentage: {result['short_trades_percent']:.2f}%")
    print(f"Threshold: > {result['threshold_percent']:.0f}%\n")
    
    if result['status'] == config.STATUS_VIOLATED:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Gambling behavior detected. {result['short_trades_percent']:.2f}% of trades "
            f"are held for less than {result['threshold_seconds']} seconds."
        )
        
        print("\n📋 VIOLATION REASON:")
        print(f"   {result['violation_reason']}\n")
        
        print("SHORT DURATION TRADES:")
        print("-" * 80)
        
        # Show some examples
        short_trades = result['short_trades']
        for idx, (_, trade) in enumerate(short_trades.head(10).iterrows(), 1):
            print(f"{idx}. Position {trade['Position ID']}: {trade['Instrument']} {trade['Side']}, "
                  f"Duration: {utils.format_duration(trade['Duration_Seconds'])}")
        
        if len(short_trades) > 10:
            print(f"... and {len(short_trades) - 10} more short-duration trades")
        
        print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            f"No gambling behavior detected. Only {result['short_trades_percent']:.2f}% of trades "
            f"are held for less than {result['threshold_seconds']} seconds."
        )


def export_results(result: dict, output_prefix: str = "Rule_14"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Short Trades Count': result['short_trades_count'],
        'Short Trades Percent': f"{result['short_trades_percent']:.2f}%",
        'Threshold': f"> {result['threshold_percent']:.0f}%"
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    # Export short trades if violation
    if result['status'] == config.STATUS_VIOLATED:
        short_trades_df = result['short_trades'][['Position ID', 'Instrument', 'Side', 'Open Time', 'Close Time', 'Duration_Seconds']]
        short_trades_df.to_csv(f"{output_prefix}_short_trades.csv", index=False)
        print(f"Short trades exported to: {output_prefix}_short_trades.csv")


def main():
    """Main execution function"""
    # Check command line arguments
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "Trades121.csv"
    
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
        
        # Check for gambling
        result = check_gambling(df)
        
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
