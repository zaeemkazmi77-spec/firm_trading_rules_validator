"""
Rule 17: Max 2% Risk per Trade Idea (Direct Funding only)

Applies only to Direct Funding accounts.
A trade idea is defined as multiple trades on the same symbol and direction (Long or 
Short) where the time gap between openings is ≤ 5 minutes (≤ 60 seconds for XAUUSD).
Total risk of all trades in the idea = (entry-to-Stop-Loss distance × position size × value per point).
If risk > 2.05% of equity at first entry → Violation.
If ≤ 2% → No violation.
"""

import pandas as pd
import sys
import numpy as np
import config
import utils

def check_max_risk_per_idea(df: pd.DataFrame, account_equity: float, account_type: str = "Direct Funding") -> dict:
    """
    Check for max 2% risk per trade idea violation
    
    Args:
        df: DataFrame with trade data
        account_equity: Account equity
        account_type: Type of account
        
    Returns:
        Dictionary with rule results
    """
    # This rule only applies to Direct Funding accounts
    if account_type != "Direct Funding":
        return {
            'rule_number': 17,
            'rule_name': 'Max 2% Risk per Trade Idea',
            'status': config.STATUS_NOT_TESTABLE,
            'message': f'This rule only applies to Direct Funding accounts. Current type: {account_type}',
            'total_trades': len(df)
        }
    
    # Filter trades with Stop Loss
    df_with_sl = df[df['Stop Loss'].notna()].copy()
    
    if len(df_with_sl) == 0:
        return {
            'rule_number': 17,
            'rule_name': 'Max 2% Risk per Trade Idea',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'No trades have Stop Loss values. Cannot calculate risk.',
            'total_trades': len(df),
            'trades_with_sl': 0
        }
    
    # Group trades into ideas
    trade_ideas = group_trades_into_ideas(df_with_sl)
    
    # Check risk for each idea
    violations = []
    
    for idea_id, idea_trades in trade_ideas.items():
        # Get first trade in the idea (earliest open time)
        first_trade = idea_trades.iloc[0]
        
        # Calculate total risk for the idea
        total_risk_dollars = 0
        
        for _, trade in idea_trades.iterrows():
            risk_dollars, _ = utils.calculate_trade_risk(
                trade['Open Price'],
                trade['Stop Loss'],
                trade['Lots'],
                trade['Instrument'],
                account_equity
            )
            
            if pd.notna(risk_dollars):
                total_risk_dollars += risk_dollars
        
        # Calculate risk as percentage of equity
        total_risk_percent = (total_risk_dollars / account_equity) * 100 if account_equity > 0 else 0
        
        # Check for violation
        if total_risk_percent > config.MAX_RISK_PERCENT_DIRECT:
            # Build detailed trades string
            trades_detail = []
            for _, trade in idea_trades.iterrows():
                risk_dollars, risk_percent = utils.calculate_trade_risk(
                    trade['Open Price'],
                    trade['Stop Loss'],
                    trade['Lots'],
                    trade['Instrument'],
                    account_equity
                )
                trades_detail.append(
                    f"Position {trade['Position ID']} ({trade['Lots']} lots at {trade['Open Price']}, "
                    f"SL: {trade['Stop Loss']}, risk: ${risk_dollars:,.2f} / {risk_percent:.2f}%)"
                )
            
            violation_reason = (
                f"MAX RISK PER IDEA VIOLATION: Trade idea on {first_trade['Instrument']} {first_trade['Side']} "
                f"starting at {first_trade['Open Time'].strftime('%Y-%m-%d %H:%M:%S')} consists of {len(idea_trades)} "
                f"trade(s) with combined risk of ${total_risk_dollars:,.2f} ({total_risk_percent:.2f}% of equity), "
                f"which exceeds the maximum allowed {config.MAX_RISK_PERCENT_DIRECT:.2f}% risk per idea for Direct Funding accounts. "
                f"Trades in this idea: {'; '.join(trades_detail)}. "
                f"[Rule 17: Max {config.MAX_RISK_PERCENT_DIRECT}% risk per trade idea for Direct Funding]"
            )
            
            violations.append({
                'Idea_ID': idea_id,
                'Instrument': first_trade['Instrument'],
                'Direction': first_trade['Side'],
                'Trade_Count': len(idea_trades),
                'First_Entry_Time': first_trade['Open Time'],
                'Total_Risk_Dollars': total_risk_dollars,
                'Total_Risk_Percent': total_risk_percent,
                'Account_Equity': account_equity,
                'Position_IDs': list(idea_trades['Position ID']),
                'Trades': idea_trades[['Position ID', 'Open Time', 'Lots', 'Open Price', 'Stop Loss']].to_dict('records'),
                'Violation_Reason': violation_reason
            })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 17,
        'rule_name': 'Max 2% Risk per Trade Idea',
        'status': status,
        'total_trades': len(df),
        'trades_with_sl': len(df_with_sl),
        'trade_ideas_found': len(trade_ideas),
        'violations_found': len(violations),
        'violations': violations,
        'account_equity': account_equity
    }


def group_trades_into_ideas(df: pd.DataFrame) -> dict:
    """
    Group trades into ideas based on symbol, direction, and time gap
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Dictionary of trade ideas {idea_id: DataFrame}
    """
    trade_ideas = {}
    idea_counter = 1
    
    # Sort by open time
    df_sorted = df.sort_values('Open Time').copy()
    
    # Group by instrument and direction
    for (instrument, direction), group in df_sorted.groupby(['Instrument', 'Side']):
        group_sorted = group.sort_values('Open Time')
        
        # Determine time gap threshold for this instrument
        if instrument.startswith('XAUUSD') or instrument == 'XAUUSD':
            time_gap_threshold = config.TRADE_IDEA_GAP_XAUUSD_SECONDS
        else:
            time_gap_threshold = config.TRADE_IDEA_GAP_SECONDS
        
        # Group trades with time gaps <= threshold
        current_idea = []
        
        for idx, trade in group_sorted.iterrows():
            if not current_idea:
                # Start new idea
                current_idea.append(trade)
            else:
                # Check time gap from last trade in current idea
                last_trade = current_idea[-1]
                time_gap = (trade['Open Time'] - last_trade['Open Time']).total_seconds()
                
                if time_gap <= time_gap_threshold:
                    # Add to current idea
                    current_idea.append(trade)
                else:
                    # Save current idea and start new one
                    if current_idea:
                        trade_ideas[f"Idea_{idea_counter}"] = pd.DataFrame(current_idea)
                        idea_counter += 1
                    current_idea = [trade]
        
        # Save last idea
        if current_idea:
            trade_ideas[f"Idea_{idea_counter}"] = pd.DataFrame(current_idea)
            idea_counter += 1
    
    return trade_ideas


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    if result['status'] == config.STATUS_NOT_TESTABLE:
        utils.print_rule_result(
            config.STATUS_NOT_TESTABLE,
            result['message'],
            {
                'Total Trades': result['total_trades']
            }
        )
        return
    
    print(f"Account Equity: ${result['account_equity']:,.2f}")
    print(f"Total trades: {result['total_trades']}")
    print(f"Trades with SL: {result['trades_with_sl']}")
    print(f"Trade ideas found: {result['trade_ideas_found']}")
    print(f"Maximum allowed risk per idea: {config.MAX_RISK_PERCENT_DIRECT:.2f}%")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} trade idea(s) with risk > 2.05%"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Idea ID: {violation['Idea_ID']}")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Direction: {violation['Direction']}")
            print(f"  Trades in Idea: {violation['Trade_Count']}")
            print(f"  First Entry: {violation['First_Entry_Time']}")
            print(f"  Total Risk: ${violation['Total_Risk_Dollars']:,.2f} ({violation['Total_Risk_Percent']:.2f}%) ❌")
            print(f"  Account Equity: ${violation['Account_Equity']:,.2f}")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print(f"\n  Trades in this idea:")
            for trade in violation['Trades']:
                print(f"    - Position {trade['Position ID']}: {trade['Lots']} lots at {trade['Open Price']}, "
                      f"SL: {trade['Stop Loss']}, Time: {trade['Open Time']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No violations detected. All trade ideas risk ≤ 2% of equity."
        )


def export_results(result: dict, output_prefix: str = "Rule_17"):
    """Export results to CSV"""
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Trades with SL': result.get('trades_with_sl', 0),
        'Trade Ideas Found': result.get('trade_ideas_found', 0),
        'Violations Found': result.get('violations_found', 0)
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    if result.get('violations'):
        violations_flat = []
        for v in result['violations']:
            violations_flat.append({
                'Idea_ID': v['Idea_ID'],
                'Instrument': v['Instrument'],
                'Direction': v['Direction'],
                'Trade_Count': v['Trade_Count'],
                'First_Entry_Time': v['First_Entry_Time'],
                'Total_Risk_Dollars': v['Total_Risk_Dollars'],
                'Total_Risk_Percent': v['Total_Risk_Percent'],
                'Position_IDs': ', '.join(str(pid) for pid in v['Position_IDs'])
            })
        
        violations_df = pd.DataFrame(violations_flat)
        violations_df.to_csv(f"{output_prefix}_violations.csv", index=False)
        print(f"Violations exported to: {output_prefix}_violations.csv")


def main():
    """Main execution function"""
    if len(sys.argv) >= 4:
        csv_file = sys.argv[1]
        account_equity = float(sys.argv[2])
        account_type = sys.argv[3]
    else:
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        account_equity = 100000
        account_type = "Direct Funding"
        print(f"⚠️  Using defaults - Equity: ${account_equity:,.2f}, Type: {account_type}")
        print('Usage: python Rule_17.py <csv_file> <account_equity> <account_type>')
        print('Example: python Rule_17.py Trades121.csv 100000 "Direct Funding"\n')
    
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
        
        result = check_max_risk_per_idea(df, account_equity, account_type)
        print_results(result)
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
