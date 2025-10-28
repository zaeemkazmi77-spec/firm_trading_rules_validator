"""
Rule 19: Weekend Trading and Holding

From Friday 22:00 UTC to Sunday 22:00 UTC, opening, closing, or holding positions is 
strictly prohibited.
If a position is active or modified during this window → Violation.
If Add-on = ON → No violation.
"""

import pandas as pd
import sys
import config
import utils

def check_weekend_trading(df: pd.DataFrame, addon_enabled: bool = False) -> dict:
    """
    Check for weekend trading violations
    
    Args:
        df: DataFrame with trade data
        addon_enabled: Whether weekend holding add-on is enabled
        
    Returns:
        Dictionary with rule results
    """
    # If add-on is enabled, skip this rule
    if addon_enabled:
        return {
            'rule_number': 19,
            'rule_name': 'Weekend Trading and Holding',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'Weekend Holding Add-on is enabled. This rule is skipped.',
            'total_trades': len(df),
            'addon_enabled': True
        }
    
    violations = []
    
    # Get all weekend windows covering the trade period
    min_date = df['Open Time'].min()
    max_date = df['Close Time'].max()
    weekend_windows = utils.get_weekend_windows(min_date, max_date)
    
    for _, trade in df.iterrows():
        violation_details = []
        
        # Check if trade opens during weekend
        if utils.is_weekend(trade['Open Time']):
            violation_details.append(('OPEN', trade['Open Time']))
        
        # Check if trade closes during weekend
        if utils.is_weekend(trade['Close Time']):
            violation_details.append(('CLOSE', trade['Close Time']))
        
        # Check if trade is HELD during weekend using interval overlap
        # Only check if we haven't already flagged OPEN or CLOSE
        if not any(v[0] in ['OPEN', 'CLOSE'] for v in violation_details):
            for weekend_start, weekend_end in weekend_windows:
                # Check if trade interval overlaps with weekend window
                has_overlap, overlap_seconds = utils.check_time_overlap(
                    trade['Open Time'], trade['Close Time'],
                    weekend_start, weekend_end
                )
                
                # If overlap ≥1 second (tolerance), it's a HELD violation
                if has_overlap and overlap_seconds >= config.TOLERANCES['time']:
                    # Use the weekend start as the event time for reporting
                    violation_details.append(('HELD', weekend_start))
                    break  # Only need one HELD violation per trade
        
        # Add violations for this trade
        for event_type, event_time in violation_details:
            violation_reason = (
                f"WEEKEND TRADING VIOLATION: Position {trade['Position ID']} ({trade['Instrument']} {trade['Side']}) "
                f"was {event_type} during the prohibited weekend period. "
                f"Event occurred at {event_time.strftime('%Y-%m-%d %H:%M:%S')} UTC "
                f"(Day: {event_time.strftime('%A')}, Hour: {event_time.hour}:00). "
                f"Weekend trading window is Friday 22:00 UTC to Sunday 22:00 UTC. "
                f"Trade opened at {trade['Open Time'].strftime('%Y-%m-%d %H:%M:%S')} and "
                f"closed at {trade['Close Time'].strftime('%Y-%m-%d %H:%M:%S')}. "
                f"[Rule 19: No trading/holding during weekend period]"
            )
            
            violations.append({
                'Position_ID': trade['Position ID'],
                'Instrument': trade['Instrument'],
                'Side': trade['Side'],
                'Event_Type': event_type,
                'Event_Time': event_time,
                'Open_Time': trade['Open Time'],
                'Close_Time': trade['Close Time'],
                'Violation_Reason': violation_reason
            })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 19,
        'rule_name': 'Weekend Trading and Holding',
        'status': status,
        'total_trades': len(df),
        'violations_found': len(violations),
        'violations': violations,
        'addon_enabled': False
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    if result['status'] == config.STATUS_NOT_TESTABLE:
        utils.print_rule_result(
            config.STATUS_NOT_TESTABLE,
            result['message'],
            {
                'Total Trades': result['total_trades'],
                'Add-on Enabled': result['addon_enabled']
            }
        )
        return
    
    print(f"Total trades: {result['total_trades']}")
    print(f"Weekend window: Friday 22:00 UTC to Sunday 22:00 UTC")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} weekend trading/holding violation(s)"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Position ID: {violation['Position_ID']}")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Side: {violation['Side']}")
            print(f"  Violation Type: {violation['Event_Type']} ❌")
            print(f"  Event Time: {violation['Event_Time']}")
            print(f"  Trade Open Time: {violation['Open_Time']}")
            print(f"  Trade Close Time: {violation['Close_Time']}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No weekend trading violations detected."
        )


def export_results(result: dict, output_prefix: str = "Rule_19"):
    """Export results to CSV"""
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Violations Found': result.get('violations_found', 0),
        'Add-on Enabled': result['addon_enabled']
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    if result.get('violations'):
        violations_df = pd.DataFrame(result['violations'])
        violations_df.to_csv(f"{output_prefix}_violations.csv", index=False)
        print(f"Violations exported to: {output_prefix}_violations.csv")


def main():
    """Main execution function"""
    if len(sys.argv) >= 3:
        csv_file = sys.argv[1]
        addon_enabled = sys.argv[2].lower() in ['true', '1', 'yes', 'on']
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        addon_enabled = False
        print(f"⚠️  Using default: Add-on disabled")
        print("Usage: python Rule_19.py <csv_file> <addon_enabled>")
        print("Example: python Rule_19.py Trades121.csv false\n")
    
    print(f"Loading data from: {csv_file}")
    print(f"Weekend Holding Add-on: {'Enabled' if addon_enabled else 'Disabled'}\n")
    
    try:
        df = utils.load_csv(csv_file)
        print(f"Successfully loaded {len(df)} trades\n")
        
        is_valid, errors = utils.validate_csv_quality(df)
        if not is_valid:
            print("CSV Validation Failed:")
            for error in errors:
                print(f"  - {error}")
            return
        
        result = check_weekend_trading(df, addon_enabled)
        print_results(result)
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
