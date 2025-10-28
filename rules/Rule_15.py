"""
Rule 15: One-Sided Bets

A trader may not have more than 2 trades open simultaneously in the same direction 
(Long or Short) on the same symbol.
If 3 or more same-direction trades overlap in time → Violation.
Otherwise → No violation.
"""

import pandas as pd
import sys
import config
import utils

def check_one_sided_bets(df: pd.DataFrame) -> dict:
    """
    Check for one-sided bet violations (too many same-direction trades on same symbol)
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Dictionary with rule results
    """
    violations = []
    
    # Group by instrument and direction
    instruments = df['Instrument'].unique()
    
    for instrument in instruments:
        instrument_trades = df[df['Instrument'] == instrument]
        
        for direction in ['BUY', 'SELL']:
            direction_trades = instrument_trades[instrument_trades['Side'] == direction].copy()
            
            if len(direction_trades) < 3:
                continue  # Can't have violation with less than 3 trades
            
            # Check for overlaps
            direction_trades = direction_trades.sort_values('Open Time')
            
            # For each point in time, count how many trades are open
            for _, trade in direction_trades.iterrows():
                # Count overlapping trades at this trade's open time
                overlapping = direction_trades[
                    (direction_trades['Open Time'] <= trade['Open Time']) & 
                    (direction_trades['Close Time'] > trade['Open Time'])
                ]
                
                if len(overlapping) > config.MAX_SAME_DIRECTION_TRADES:
                    # Found a violation
                    violation_key = f"{instrument}_{direction}_{trade['Open Time']}"
                    
                    # Avoid duplicate violations
                    if not any(v.get('key') == violation_key for v in violations):
                        # Build detailed positions string
                        positions_detail = []
                        for _, t in overlapping.iterrows():
                            positions_detail.append(
                                f"Position {t['Position ID']} ({t['Lots']} lots, "
                                f"opened {t['Open Time'].strftime('%Y-%m-%d %H:%M:%S')}, "
                                f"closed {t['Close Time'].strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                        
                        violation_reason = (
                            f"ONE-SIDED BET VIOLATION: At {trade['Open Time'].strftime('%Y-%m-%d %H:%M:%S')}, "
                            f"{len(overlapping)} {direction} trade(s) on {instrument} were open simultaneously, "
                            f"which exceeds the maximum allowed {config.MAX_SAME_DIRECTION_TRADES} trades in the same direction. "
                            f"Overlapping positions: {'; '.join(positions_detail)}. "
                            f"[Rule 15: Maximum {config.MAX_SAME_DIRECTION_TRADES} same-direction trades per symbol]"
                        )
                        
                        violations.append({
                            'key': violation_key,
                            'Instrument': instrument,
                            'Direction': direction,
                            'Timestamp': trade['Open Time'],
                            'Overlapping_Trades_Count': len(overlapping),
                            'Position_IDs': list(overlapping['Position ID']),
                            'Trade_Details': overlapping[['Position ID', 'Open Time', 'Close Time', 'Lots']].to_dict('records'),
                            'Violation_Reason': violation_reason
                        })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 15,
        'rule_name': 'One-Sided Bets',
        'status': status,
        'total_trades': len(df),
        'violations_found': len(violations),
        'violations': violations,
        'max_allowed': config.MAX_SAME_DIRECTION_TRADES
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Total trades: {result['total_trades']}")
    print(f"Maximum allowed same-direction trades: {result['max_allowed']}")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} instance(s) where more than {result['max_allowed']} "
            f"same-direction trades overlapped"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Direction: {violation['Direction']}")
            print(f"  Timestamp: {violation['Timestamp']}")
            print(f"  Overlapping Trades: {violation['Overlapping_Trades_Count']} ❌")
            print(f"  Position IDs: {', '.join(str(pid) for pid in violation['Position_IDs'])}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("\n  Trade Details:")
            for trade_detail in violation['Trade_Details']:
                print(f"    - Position {trade_detail['Position ID']}: "
                      f"Open {trade_detail['Open Time']}, Close {trade_detail['Close Time']}, "
                      f"Lots: {trade_detail['Lots']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            f"No one-sided bet violations detected. Never more than {result['max_allowed']} "
            f"same-direction trades open simultaneously."
        )


def export_results(result: dict, output_prefix: str = "Rule_15"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Max Allowed': result['max_allowed'],
        'Violations Found': result['violations_found']
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    # Export violations if any
    if result.get('violations'):
        violations_flat = []
        for v in result['violations']:
            violations_flat.append({
                'Instrument': v['Instrument'],
                'Direction': v['Direction'],
                'Timestamp': v['Timestamp'],
                'Overlapping_Trades_Count': v['Overlapping_Trades_Count'],
                'Position_IDs': ', '.join(str(pid) for pid in v['Position_IDs'])
            })
        
        violations_df = pd.DataFrame(violations_flat)
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
        
        # Check for one-sided bets
        result = check_one_sided_bets(df)
        
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
