"""
Rule 4: Prohibited Third-Party Strategies (EAs)

Use of prebuilt, purchased, or automated trading systems is forbidden in all phases.

A violation occurs if:
• at least 10 trades have identical patterns:
  - Stop-Loss distance difference ≤ 0.00001
  - Take-Profit distance difference ≤ 0.00001
  - Holding duration difference ≤ 1 second
  - Lot size difference ≤ 0.0001
• and these trades occur across 3 or more distinct days

The pattern may occur on a single symbol; multiple symbols are not required.
"""

import pandas as pd
import sys
import numpy as np
from itertools import combinations
import config
import utils

def check_ea_violation(df: pd.DataFrame) -> dict:
    """
    Check for automated trading patterns (EA usage)
    
    Args:
        df: DataFrame with trade data
        
    Returns:
        Dictionary with rule results
    """
    # Filter trades that have both SL and TP (needed for pattern detection)
    df_with_sl_tp = df[df['Stop Loss'].notna() & df['Take Profit'].notna()].copy()
    
    if len(df_with_sl_tp) < config.EA_DETECTION_MIN_TRADES:
        return {
            'rule_number': 4,
            'rule_name': 'Prohibited Third-Party Strategies (EAs)',
            'status': config.STATUS_NOT_TESTABLE,
            'message': f'Only {len(df_with_sl_tp)} trades have both SL and TP (minimum required: {config.EA_DETECTION_MIN_TRADES})',
            'total_trades': len(df),
            'trades_with_sl_tp': len(df_with_sl_tp)
        }
    
    # Calculate SL and TP distances for each trade
    df_with_sl_tp['SL_Distance'] = df_with_sl_tp.apply(
        lambda row: utils.calculate_sl_distance(row['Open Price'], row['Stop Loss'], row['Side']),
        axis=1
    )
    
    df_with_sl_tp['TP_Distance'] = df_with_sl_tp.apply(
        lambda row: utils.calculate_tp_distance(row['Open Price'], row['Take Profit'], row['Side']),
        axis=1
    )
    
    # Find pattern groups
    pattern_groups = find_pattern_groups(df_with_sl_tp)
    
    # Check each group for violations
    violations = []
    for group in pattern_groups:
        if len(group) >= config.EA_DETECTION_MIN_TRADES:
            # Check if trades span at least 3 distinct days
            trade_dates = df_with_sl_tp.loc[group, 'Open Time'].dt.date.unique()
            if len(trade_dates) >= config.EA_DETECTION_MIN_DAYS:
                # Get trade details for violation reason
                group_trades = df_with_sl_tp.loc[group]
                first_trade = group_trades.iloc[0]
                
                # Build detailed positions string (show first few)
                positions_detail = []
                for idx, (_, t) in enumerate(group_trades.head(5).iterrows()):
                    positions_detail.append(
                        f"Position {t['Position ID']} ({t['Instrument']}, {t['Lots']} lots, "
                        f"duration: {utils.format_duration(t['Duration_Seconds'])})"
                    )
                
                more_trades = len(group_trades) - 5 if len(group_trades) > 5 else 0
                
                violation_reason = (
                    f"PROHIBITED EA VIOLATION: Detected {len(group)} trade(s) with identical automated pattern "
                    f"(SL distance: {first_trade['SL_Distance']:.5f}, TP distance: {first_trade['TP_Distance']:.5f}, "
                    f"duration: {utils.format_duration(first_trade['Duration_Seconds'])}, lots: {first_trade['Lots']}) "
                    f"across {len(trade_dates)} distinct trading day(s) ({', '.join([str(d) for d in sorted(trade_dates)])}). "
                    f"This exceeds the threshold of {config.EA_DETECTION_MIN_TRADES} identical trades across "
                    f"{config.EA_DETECTION_MIN_DAYS} days, indicating use of automated/prohibited trading systems. "
                    f"Example trades: {'; '.join(positions_detail)}"
                    f"{f' and {more_trades} more' if more_trades > 0 else ''}. "
                    f"[Rule 4: ≥{config.EA_DETECTION_MIN_TRADES} identical trades across ≥{config.EA_DETECTION_MIN_DAYS} days = EA violation]"
                )
                
                violations.append({
                    'trade_indices': group,
                    'pattern_size': len(group),
                    'distinct_days': len(trade_dates),
                    'dates': sorted([str(d) for d in trade_dates]),
                    'violation_reason': violation_reason
                })
    
    # Prepare results
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 4,
        'rule_name': 'Prohibited Third-Party Strategies (EAs)',
        'status': status,
        'total_trades': len(df),
        'trades_analyzed': len(df_with_sl_tp),
        'pattern_groups_found': len(violations),
        'violations': violations,
        'df': df_with_sl_tp
    }


def find_pattern_groups(df: pd.DataFrame) -> list:
    """
    Find groups of trades with identical patterns
    
    Args:
        df: DataFrame with trade data including SL_Distance and TP_Distance
        
    Returns:
        List of groups (each group is a list of indices)
    """
    pattern_groups = []
    used_indices = set()
    
    # For each trade, find all similar trades
    for idx in df.index:
        if idx in used_indices:
            continue
        
        trade = df.loc[idx]
        similar_trades = [idx]
        
        # Compare with all other trades
        for other_idx in df.index:
            if other_idx == idx or other_idx in used_indices:
                continue
            
            other_trade = df.loc[other_idx]
            
            # Check if patterns match within tolerances
            if is_pattern_match(trade, other_trade):
                similar_trades.append(other_idx)
                used_indices.add(other_idx)
        
        if len(similar_trades) >= config.EA_DETECTION_MIN_TRADES:
            pattern_groups.append(similar_trades)
            used_indices.update(similar_trades)
    
    return pattern_groups


def is_pattern_match(trade1: pd.Series, trade2: pd.Series) -> bool:
    """
    Check if two trades have matching patterns within tolerances
    
    Args:
        trade1: First trade
        trade2: Second trade
        
    Returns:
        True if patterns match
    """
    # Check SL distance
    sl_diff = abs(trade1['SL_Distance'] - trade2['SL_Distance'])
    if sl_diff > config.TOLERANCES['price']:
        return False
    
    # Check TP distance
    tp_diff = abs(trade1['TP_Distance'] - trade2['TP_Distance'])
    if tp_diff > config.TOLERANCES['price']:
        return False
    
    # Check duration
    duration_diff = abs(trade1['Duration_Seconds'] - trade2['Duration_Seconds'])
    if duration_diff > config.TOLERANCES['time']:
        return False
    
    # Check lot size
    lot_diff = abs(trade1['Lots'] - trade2['Lots'])
    if lot_diff > config.TOLERANCES['lots']:
        return False
    
    return True


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    if result['status'] == config.STATUS_NOT_TESTABLE:
        utils.print_rule_result(
            config.STATUS_NOT_TESTABLE,
            result['message'],
            {
                'Total Trades': result['total_trades'],
                'Trades with SL & TP': result['trades_with_sl_tp'],
                'Minimum Required': config.EA_DETECTION_MIN_TRADES
            }
        )
        return
    
    print(f"Total trades analyzed: {result['total_trades']}")
    print(f"Trades with SL & TP: {result['trades_analyzed']}")
    print(f"Pattern groups found: {result['pattern_groups_found']}\n")
    
    if result['pattern_groups_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['pattern_groups_found']} suspicious pattern group(s) indicating potential EA usage"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        df = result['df']
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nPattern Group #{idx}:")
            print(f"  - Number of matching trades: {violation['pattern_size']}")
            print(f"  - Distinct trading days: {violation['distinct_days']}")
            print(f"  - Dates: {', '.join(violation['dates'])}")
            
            print(f"\n  📋 VIOLATION REASON:")
            print(f"     {violation['violation_reason']}")
            
            # Show sample of matching trades
            sample_indices = violation['trade_indices'][:5]  # Show first 5
            print(f"\n  Sample trades from this pattern:")
            for trade_idx in sample_indices:
                trade = df.loc[trade_idx]
                print(f"    Position {trade['Position ID']}: {trade['Instrument']} {trade['Side']}, "
                      f"Lots: {trade['Lots']:.4f}, Duration: {utils.format_duration(trade['Duration_Seconds'])}, "
                      f"SL Dist: {trade['SL_Distance']:.5f}, TP Dist: {trade['TP_Distance']:.5f}")
            
            if len(violation['trade_indices']) > 5:
                print(f"    ... and {len(violation['trade_indices']) - 5} more")
            
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No automated trading patterns detected. No EA usage indicators found."
        )


def export_results(result: dict, output_prefix: str = "Rule_4"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'Trades Analyzed': result.get('trades_analyzed', 0),
        'Pattern Groups Found': result.get('pattern_groups_found', 0)
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")
    
    # Export violations if any
    if result.get('violations'):
        violation_details = []
        df = result['df']
        
        for group_idx, violation in enumerate(result['violations'], 1):
            for trade_idx in violation['trade_indices']:
                trade = df.loc[trade_idx]
                violation_details.append({
                    'Pattern_Group': group_idx,
                    'Position_ID': trade['Position ID'],
                    'Instrument': trade['Instrument'],
                    'Side': trade['Side'],
                    'Lots': trade['Lots'],
                    'Open_Time': trade['Open Time'],
                    'Duration_Seconds': trade['Duration_Seconds'],
                    'SL_Distance': trade['SL_Distance'],
                    'TP_Distance': trade['TP_Distance']
                })
        
        violations_df = pd.DataFrame(violation_details)
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
        
        # Check for EA violations
        result = check_ea_violation(df)
        
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
