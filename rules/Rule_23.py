"""
Rule 23: Minimum Trading Days

• 2-Step Challenge Phases 1 & 2: No minimum → Always Pass.
• 2-Step Challenge Funded Stage: At least 4 active trading days required.
  - Fewer than 4 → Violation.
• Direct Funding: At least 7 active trading days required.
  - Fewer than 7 → Violation.
"""

import pandas as pd
import sys
import config
import utils

def check_minimum_trading_days(df: pd.DataFrame, account_type: str = "Funded Phase") -> dict:
    """
    Check for minimum trading days requirement
    
    Args:
        df: DataFrame with trade data
        account_type: Type of account
        
    Returns:
        Dictionary with rule results
    """
    # Get minimum required days for this account type
    min_required_days = config.ACCOUNT_TYPES[account_type]['min_trading_days']
    
    # Count distinct trading days
    distinct_days = utils.get_distinct_trading_days(df)
    
    # Get the list of trading dates
    trading_dates = sorted(df['Open Time'].dt.date.unique())
    
    # Check for violation
    violation_reason = None
    if min_required_days == 0:
        # No minimum required (Phase 1 or 2)
        status = config.STATUS_PASSED
        message = f"No minimum trading days required for {account_type}. Always passes."
    elif distinct_days < min_required_days:
        status = config.STATUS_VIOLATED
        message = f"Only {distinct_days} trading day(s) found. Minimum required: {min_required_days}"
        
        violation_reason = (
            f"MINIMUM TRADING DAYS VIOLATION: The account has {distinct_days} distinct trading day(s) "
            f"({', '.join(str(d) for d in trading_dates)}), which is {min_required_days - distinct_days} day(s) "
            f"short of the minimum {min_required_days} trading days required for {account_type} accounts. "
            f"[Rule 23: Funded Phase requires ≥4 days, Direct Funding requires ≥7 days]"
        )
    else:
        status = config.STATUS_PASSED
        message = f"Requirement met: {distinct_days} trading days (minimum: {min_required_days})"
    
    return {
        'rule_number': 23,
        'rule_name': 'Minimum Trading Days',
        'status': status,
        'total_trades': len(df),
        'distinct_trading_days': distinct_days,
        'min_required_days': min_required_days,
        'account_type': account_type,
        'trading_dates': [str(d) for d in trading_dates],
        'message': message,
        'violation_reason': violation_reason
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    print(f"Account Type: {result['account_type']}")
    print(f"Total trades: {result['total_trades']}")
    print(f"Distinct trading days: {result['distinct_trading_days']}")
    print(f"Minimum required: {result['min_required_days']}")
    print(f"\nTrading dates: {', '.join(result['trading_dates'])}\n")
    
    if result['status'] == config.STATUS_VIOLATED:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            result['message'],
            {
                'Trading Days Found': result['distinct_trading_days'],
                'Minimum Required': result['min_required_days'],
                'Shortfall': result['min_required_days'] - result['distinct_trading_days']
            }
        )
        print("\n📋 VIOLATION REASON:")
        print(f"   {result['violation_reason']}\n")
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            result['message']
        )


def export_results(result: dict, output_prefix: str = "Rule_23"):
    """Export results to CSV"""
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Account Type': result['account_type'],
        'Total Trades': result['total_trades'],
        'Distinct Trading Days': result['distinct_trading_days'],
        'Min Required Days': result['min_required_days'],
        'Trading Dates': ', '.join(result['trading_dates'])
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")


def main():
    """Main execution function"""
    if len(sys.argv) >= 3:
        csv_file = sys.argv[1]
        account_type = sys.argv[2]
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        account_type = "Funded Phase"  # Default
        print(f"⚠️  Using default account type: {account_type}")
        print("Usage: python Rule_23.py <csv_file> <account_type>")
        print('Example: python Rule_23.py Trades121.csv "Funded Phase"\n')
        print(f"Available account types:")
        for at in config.ACCOUNT_TYPES.keys():
            print(f"  - {at}")
        print()
    
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
        
        result = check_minimum_trading_days(df, account_type)
        print_results(result)
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
