"""
Rule 12: All-or-Nothing Trading

No single trade or grouped trade idea may risk the entire account.

If the total risk of the idea (based on Stop-Loss distances and trade sizes) is ≥ 100% 
of account equity → Violation.
If no Stop-Loss is set → Not testable (but not counted as violation).
"""

import pandas as pd
import sys
import numpy as np
import config
import utils

def check_all_or_nothing(df: pd.DataFrame, account_equity: float, account_type: str = "Funded Phase") -> dict:
    """
    Check for all-or-nothing trading violations
    
    Args:
        df: DataFrame with trade data
        account_equity: Account equity
        account_type: Type of account (for configuration)
        
    Returns:
        Dictionary with rule results
    """
    # Filter trades with Stop Loss
    df_with_sl = df[df['Stop Loss'].notna()].copy()
    
    if len(df_with_sl) == 0:
        return {
            'rule_number': 12,
            'rule_name': 'All-or-Nothing Trading',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'No trades have Stop Loss values. Cannot calculate risk.',
            'total_trades': len(df),
            'trades_with_sl': 0
        }
    
    # Calculate risk for each trade
    violations = []
    
    for idx, trade in df_with_sl.iterrows():
        risk_dollars, risk_percent = utils.calculate_trade_risk(
            trade['Open Price'],
            trade['Stop Loss'],
            trade['Lots'],
            trade['Instrument'],
            account_equity
        )
        
        if pd.notna(risk_percent) and risk_percent >= config.MAX_RISK_PERCENT:
            # Create detailed explanation
            reason = (
                f"ALL-OR-NOTHING VIOLATION: Position {trade['Position ID']} on {trade['Instrument']} "
                f"risks ${risk_dollars:,.2f} ({risk_percent:.2f}% of equity) which is ≥100% of account balance. "
                f"Trade details: {trade['Side']} {trade['Lots']} lots at {trade['Open Price']}, "
                f"Stop Loss at {trade['Stop Loss']}. "
                f"Stop Loss distance: {abs(trade['Open Price'] - trade['Stop Loss']):.5f}. "
                f"With account equity of ${account_equity:,.2f}, this single trade risks the entire account. "
                f"Rule: No single trade may risk ≥100% of account equity."
            )
            
            violations.append({
                'Position_ID': trade['Position ID'],
                'Instrument': trade['Instrument'],
                'Side': trade['Side'],
                'Lots': trade['Lots'],
                'Open_Price': trade['Open Price'],
                'Stop_Loss': trade['Stop Loss'],
                'Open_Time': trade['Open Time'],
                'Risk_Dollars': risk_dollars,
                'Risk_Percent': risk_percent,
                'Account_Equity': account_equity,
                'Violation_Reason': reason
            })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 12,
        'rule_name': 'All-or-Nothing Trading',
        'status': status,
        'total_trades': len(df),
        'trades_with_sl': len(df_with_sl),
        'trades_without_sl': len(df) - len(df_with_sl),
        'violations_found': len(violations),
        'violations': violations,
        'account_equity': account_equity
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
                'Trades with SL': result['trades_with_sl']
            }
        )
        return
    
    print(f"Account Equity: ${result['account_equity']:,.2f}")
    print(f"Total trades: {result['total_trades']}")
    print(f"Trades with Stop Loss: {result['trades_with_sl']}")
    print(f"Trades without Stop Loss: {result['trades_without_sl']}")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} trade(s) risking ≥ 100% of account equity"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Position ID: {violation['Position_ID']}")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Side: {violation['Side']}")
            print(f"  Lots: {violation['Lots']}")
            print(f"  Open Price: {violation['Open_Price']}")
            print(f"  Stop Loss: {violation['Stop_Loss']}")
            print(f"  Open Time: {violation['Open_Time']}")
            print(f"  Risk Amount: ${violation['Risk_Dollars']:,.2f}")
            print(f"  Risk Percentage: {violation['Risk_Percent']:.2f}% ❌")
            print(f"  Account Equity: ${violation['Account_Equity']:,.2f}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No all-or-nothing trading detected. All trades risk less than 100% of equity."
        )


def export_results(result: dict, output_prefix: str = "Rule_12"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Trades with SL': result.get('trades_with_sl', 0),
        'Violations Found': result.get('violations_found', 0),
        'Account Equity': result.get('account_equity', 0)
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
    if len(sys.argv) >= 3:
        csv_file = sys.argv[1]
        account_equity = float(sys.argv[2])
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        account_equity = 100000  # Default
        print(f"⚠️  No account equity specified. Using default: ${account_equity:,.2f}")
        print("Usage: python Rule_12.py <csv_file> <account_equity>")
        print("Example: python Rule_12.py Trades121.csv 100000\n")
    
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
        
        # Check for all-or-nothing violations
        result = check_all_or_nothing(df, account_equity)
        
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
