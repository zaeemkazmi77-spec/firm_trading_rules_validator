"""
Rule 1: Hedging Ban

It is strictly forbidden to hold Long and Short positions on the same instrument 
at the same time, across any accounts.

An overlap occurs if the duration of opposing trades overlaps by 1 second or more.
If one position closes exactly before the other opens → allowed.
If any overlap ≥ 1 second → Violation.
"""

import pandas as pd
import sys
from datetime import datetime
import config
import utils

def check_hedging_violation(df: pd.DataFrame) -> dict:
    """
    Check for hedging violations (simultaneous long and short positions on same instrument)
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Dictionary with rule results
    """
    violations = []
    
    # Group by instrument
    instruments = df['Instrument'].unique()
    
    for instrument in instruments:
        # Get all trades for this instrument
        instrument_trades = df[df['Instrument'] == instrument].copy()
        instrument_trades = instrument_trades.sort_values('Open Time')
        
        # Check each trade against all other trades
        for i, trade1 in instrument_trades.iterrows():
            for j, trade2 in instrument_trades.iterrows():
                if i >= j:  # Skip same trade and already compared pairs
                    continue
                
                # Check if trades are in opposite directions
                if trade1['Side'] == trade2['Side']:
                    continue  # Same direction, not hedging
                
                # Check for time overlap
                has_overlap, overlap_seconds = utils.check_time_overlap(
                    trade1['Open Time'], trade1['Close Time'],
                    trade2['Open Time'], trade2['Close Time']
                )
                
                if has_overlap:
                    # Create detailed explanation
                    reason = (
                        f"HEDGING VIOLATION: Position {trade1['Position ID']} ({trade1['Side']}) and "
                        f"Position {trade2['Position ID']} ({trade2['Side']}) on {instrument} overlapped for "
                        f"{overlap_seconds:.1f} seconds. "
                        f"Trade 1 was open from {trade1['Open Time'].strftime('%Y-%m-%d %H:%M:%S')} to "
                        f"{trade1['Close Time'].strftime('%Y-%m-%d %H:%M:%S')}. "
                        f"Trade 2 was open from {trade2['Open Time'].strftime('%Y-%m-%d %H:%M:%S')} to "
                        f"{trade2['Close Time'].strftime('%Y-%m-%d %H:%M:%S')}. "
                        f"Rule: It is forbidden to hold Long and Short positions simultaneously on the same instrument "
                        f"with overlap ≥1 second."
                    )
                    
                    violations.append({
                        'Instrument': instrument,
                        'Trade1_ID': trade1['Position ID'],
                        'Trade1_Side': trade1['Side'],
                        'Trade1_Open': trade1['Open Time'],
                        'Trade1_Close': trade1['Close Time'],
                        'Trade2_ID': trade2['Position ID'],
                        'Trade2_Side': trade2['Side'],
                        'Trade2_Open': trade2['Open Time'],
                        'Trade2_Close': trade2['Close Time'],
                        'Overlap_Seconds': overlap_seconds,
                        'Violation_Reason': reason
                    })
    
    # Prepare results
    result = {
        'rule_number': 1,
        'rule_name': 'Hedging Ban',
        'total_trades': len(df),
        'violations_found': len(violations),
        'status': config.STATUS_VIOLATED if len(violations) > 0 else config.STATUS_PASSED,
        'violations': violations
    }
    
    return result


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Total trades analyzed: {result['total_trades']}")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} hedging violation(s)"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Trade 1:")
            print(f"    - Position ID: {violation['Trade1_ID']}")
            print(f"    - Side: {violation['Trade1_Side']}")
            print(f"    - Open Time: {violation['Trade1_Open']}")
            print(f"    - Close Time: {violation['Trade1_Close']}")
            print(f"  Trade 2:")
            print(f"    - Position ID: {violation['Trade2_ID']}")
            print(f"    - Side: {violation['Trade2_Side']}")
            print(f"    - Open Time: {violation['Trade2_Open']}")
            print(f"    - Close Time: {violation['Trade2_Close']}")
            print(f"  Overlap Duration: {utils.format_duration(violation['Overlap_Seconds'])}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No hedging violations detected. No simultaneous long/short positions found."
        )


def export_results(result: dict, output_prefix: str = "Rule_1"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Violations Found': result['violations_found']
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    # Export violations if any
    if result['violations']:
        violations_df = pd.DataFrame(result['violations'])
        violations_df.to_csv(f"{output_prefix}_violations.csv", index=False)
        print(f"Violations exported to: {output_prefix}_violations.csv")


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
        
        # Check for hedging violations
        result = check_hedging_violation(df)
        
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
