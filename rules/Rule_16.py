"""
Rule 16: Abuse of Simulated Environment

Within any 24-hour period, total traded volume must not exceed 10× account equity.
If within that period ≥ 80% of trades were opened without a Stop-Loss and total volume 
≥ 10× equity → Violation.
If one condition fails → No violation.
"""

import pandas as pd
import sys
from datetime import timedelta
import config
import utils

def check_abuse_of_sim_environment(df: pd.DataFrame, account_equity: float) -> dict:
    """
    Check for abuse of simulated environment
    
    Args:
        df: DataFrame with trade data
        account_equity: Account equity
        
    Returns:
        Dictionary with rule results
    """
    violations = []
    
    # Sort by open time
    df_sorted = df.sort_values('Open Time').copy()
    
    # Sliding 24-hour window
    window_hours = config.ABUSE_WINDOW_HOURS
    
    for idx, trade in df_sorted.iterrows():
        window_start = trade['Open Time']
        window_end = window_start + timedelta(hours=window_hours)
        
        # Get all trades in this window
        window_trades = df_sorted[
            (df_sorted['Open Time'] >= window_start) & 
            (df_sorted['Open Time'] < window_end)
        ]
        
        if len(window_trades) == 0:
            continue
        
        # Calculate total notional volume (in currency, not lots)
        total_volume = 0
        for _, trade in window_trades.iterrows():
            notional = utils.calculate_notional_volume(
                trade['Lots'], 
                trade['Instrument'], 
                trade['Open Price']
            )
            total_volume += notional
        
        # Calculate percentage of trades without SL (NaN or 0)
        no_sl_mask = window_trades['Stop Loss'].isna() | (window_trades['Stop Loss'] == 0)
        trades_without_sl = no_sl_mask.sum()
        no_sl_percent = (trades_without_sl / len(window_trades)) * 100
        
        # Check both conditions
        volume_threshold = account_equity * config.ABUSE_VOLUME_MULTIPLIER
        volume_exceeds = total_volume >= volume_threshold
        no_sl_exceeds = no_sl_percent >= config.ABUSE_NO_SL_THRESHOLD
        
        # Both conditions must be true for violation
        if volume_exceeds and no_sl_exceeds:
            # Check if we already recorded this window
            is_duplicate = False
            for v in violations:
                if abs((v['Window_Start'] - window_start).total_seconds()) < 3600:  # Within 1 hour
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                violation_reason = (
                    f"SIMULATED ENVIRONMENT ABUSE VIOLATION: During the 24-hour window from "
                    f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} to {window_end.strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"{len(window_trades)} trade(s) with total notional volume of ${total_volume:,.2f} were executed, "
                    f"which exceeds {config.ABUSE_VOLUME_MULTIPLIER}× the account equity "
                    f"(threshold: ${volume_threshold:,.2f}). Additionally, {trades_without_sl} trade(s) "
                    f"({no_sl_percent:.1f}%) were opened without Stop-Loss, exceeding the {config.ABUSE_NO_SL_THRESHOLD:.0f}% threshold. "
                    f"Both conditions being met indicates abuse of the simulated trading environment. "
                    f"[Rule 16: Notional Volume ≥10× equity AND ≥80% trades without SL = Violation]"
                )
                
                violations.append({
                    'Window_Start': window_start,
                    'Window_End': window_end,
                    'Trades_In_Window': len(window_trades),
                    'Total_Notional_Volume': total_volume,
                    'Volume_Threshold': volume_threshold,
                    'Trades_Without_SL': trades_without_sl,
                    'No_SL_Percent': no_sl_percent,
                    'Account_Equity': account_equity,
                    'Violation_Reason': violation_reason
                })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 16,
        'rule_name': 'Abuse of Simulated Environment',
        'status': status,
        'total_trades': len(df),
        'violations_found': len(violations),
        'violations': violations,
        'account_equity': account_equity
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Account Equity: ${result['account_equity']:,.2f}")
    print(f"Total trades: {result['total_trades']}")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} 24-hour window(s) with excessive volume and no-SL trades"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Window: {violation['Window_Start']} to {violation['Window_End']}")
            print(f"  Trades in Window: {violation['Trades_In_Window']}")
            print(f"  Total Notional Volume: ${violation['Total_Notional_Volume']:,.2f}")
            print(f"  Volume Threshold (10× equity): ${violation['Volume_Threshold']:,.2f}")
            print(f"  Trades without SL: {violation['Trades_Without_SL']} ({violation['No_SL_Percent']:.1f}%)")
            print(f"  Required for violation: ≥80% without SL")
            print("  ❌ Both conditions met")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No abuse of simulated environment detected."
        )


def export_results(result: dict, output_prefix: str = "Rule_16"):
    """Export results to CSV"""
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Violations Found': result['violations_found'],
        'Account Equity': result['account_equity']
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
        account_equity = float(sys.argv[2])
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        account_equity = 100000
        print(f"⚠️  Using default equity: ${account_equity:,.2f}")
        print("Usage: python Rule_16.py <csv_file> <account_equity>\n")
    
    print(f"Loading data from: {csv_file}")
    
    try:
        df = utils.load_csv(csv_file)
        print(f"Successfully loaded {len(df)} trades\n")
        
        is_valid, errors = utils.validate_csv_quality(df)
        if not is_valid:
            print("CSV Validation Failed:")
            for error in errors:
                print(f"  - {error}")
            return
        
        result = check_abuse_of_sim_environment(df, account_equity)
        print_results(result)
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
