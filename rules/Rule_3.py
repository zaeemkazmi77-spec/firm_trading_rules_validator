"""
Rule 3: Strategy Consistency

Trading behavior must remain consistent between Evaluation and Funded phases.

Metrics compared:
1. Median trade duration (seconds)
2. Average trades per day
3. Median risk per trade (% of account)

If at least 2 of 3 metrics differ by ≥ 200% between phases → Violation.
If any phase has fewer than 20 trades → Not testable.
"""

import pandas as pd
import sys
import numpy as np
import config
import utils

def check_strategy_consistency(df_phase1: pd.DataFrame, df_phase2: pd.DataFrame, 
                               equity_phase1: float, equity_phase2: float) -> dict:
    """
    Check for strategy consistency between two phases
    
    Args:
        df_phase1: DataFrame with phase 1 trade data
        df_phase2: DataFrame with phase 2 trade data
        equity_phase1: Account equity for phase 1
        equity_phase2: Account equity for phase 2
        
    Returns:
        Dictionary with rule results
    """
    # Check if we have enough trades
    if len(df_phase1) < config.STRATEGY_CONSISTENCY_MIN_TRADES:
        return {
            'rule_number': 3,
            'rule_name': 'Strategy Consistency',
            'status': config.STATUS_NOT_TESTABLE,
            'message': f'Phase 1 has only {len(df_phase1)} trades (minimum required: {config.STRATEGY_CONSISTENCY_MIN_TRADES})',
            'phase1_trades': len(df_phase1),
            'phase2_trades': len(df_phase2)
        }
    
    if len(df_phase2) < config.STRATEGY_CONSISTENCY_MIN_TRADES:
        return {
            'rule_number': 3,
            'rule_name': 'Strategy Consistency',
            'status': config.STATUS_NOT_TESTABLE,
            'message': f'Phase 2 has only {len(df_phase2)} trades (minimum required: {config.STRATEGY_CONSISTENCY_MIN_TRADES})',
            'phase1_trades': len(df_phase1),
            'phase2_trades': len(df_phase2)
        }
    
    # Calculate metrics for Phase 1
    phase1_metrics = calculate_phase_metrics(df_phase1, equity_phase1)
    
    # Calculate metrics for Phase 2
    phase2_metrics = calculate_phase_metrics(df_phase2, equity_phase2)
    
    # Compare metrics
    differences = compare_metrics(phase1_metrics, phase2_metrics)
    
    # Count how many metrics differ by ≥ 200%
    metrics_exceeded = sum([
        differences['duration_exceeds'],
        differences['trades_per_day_exceeds'],
        differences['risk_exceeds']
    ])
    
    # Build violation reason if needed
    violation_reason = None
    if metrics_exceeded >= 2:
        exceeded_metrics = []
        if differences['duration_exceeds']:
            exceeded_metrics.append(
                f"Median Duration (Phase 1: {utils.format_duration(phase1_metrics['median_duration_seconds'])}, "
                f"Phase 2: {utils.format_duration(phase2_metrics['median_duration_seconds'])}, "
                f"Ratio: {differences['duration_ratio']:.2f}x)"
            )
        if differences['trades_per_day_exceeds']:
            exceeded_metrics.append(
                f"Trades per Day (Phase 1: {phase1_metrics['trades_per_day']:.2f}, "
                f"Phase 2: {phase2_metrics['trades_per_day']:.2f}, "
                f"Ratio: {differences['trades_per_day_ratio']:.2f}x)"
            )
        if differences['risk_exceeds']:
            exceeded_metrics.append(
                f"Median Risk (Phase 1: {phase1_metrics['median_risk_percent']:.2f}%, "
                f"Phase 2: {phase2_metrics['median_risk_percent']:.2f}%, "
                f"Ratio: {differences['risk_ratio']:.2f}x)"
            )
        
        violation_reason = (
            f"STRATEGY CONSISTENCY VIOLATION: {metrics_exceeded} out of 3 key trading metrics differ by "
            f"≥200% (ratio ≥{config.STRATEGY_CONSISTENCY_THRESHOLD:.1f}x) between Phase 1 ({len(df_phase1)} trades) "
            f"and Phase 2 ({len(df_phase2)} trades). Metrics exceeding threshold: {'; '.join(exceeded_metrics)}. "
            f"This indicates inconsistent trading behavior between evaluation and funded phases. "
            f"[Rule 3: At least 2 of 3 metrics must differ by ≥200% for violation]"
        )
    
    # Determine status
    status = config.STATUS_VIOLATED if metrics_exceeded >= 2 else config.STATUS_PASSED
    
    return {
        'rule_number': 3,
        'rule_name': 'Strategy Consistency',
        'status': status,
        'phase1_trades': len(df_phase1),
        'phase2_trades': len(df_phase2),
        'phase1_metrics': phase1_metrics,
        'phase2_metrics': phase2_metrics,
        'differences': differences,
        'metrics_exceeded_threshold': metrics_exceeded,
        'message': f'{metrics_exceeded} out of 3 metrics differ by ≥ 200%',
        'violation_reason': violation_reason
    }


def calculate_phase_metrics(df: pd.DataFrame, equity: float) -> dict:
    """
    Calculate the three metrics for a phase
    
    Args:
        df: DataFrame with trade data
        equity: Account equity
        
    Returns:
        Dictionary with calculated metrics
    """
    # 1. Median trade duration (seconds)
    median_duration = df['Duration_Seconds'].median()
    
    # 2. Average trades per day
    distinct_days = utils.get_distinct_trading_days(df)
    trades_per_day = len(df) / distinct_days if distinct_days > 0 else 0
    
    # 3. Median risk per trade (% of equity)
    risks = []
    for _, trade in df.iterrows():
        if pd.notna(trade.get('Stop Loss')):
            _, risk_percent = utils.calculate_trade_risk(
                trade['Open Price'],
                trade['Stop Loss'],
                trade['Lots'],
                trade['Instrument'],
                equity
            )
            if pd.notna(risk_percent):
                risks.append(risk_percent)
    
    median_risk = np.median(risks) if risks else np.nan
    
    return {
        'median_duration_seconds': median_duration,
        'trades_per_day': trades_per_day,
        'median_risk_percent': median_risk,
        'distinct_trading_days': distinct_days,
        'trades_with_sl': len(risks)
    }


def compare_metrics(phase1: dict, phase2: dict) -> dict:
    """
    Compare metrics between two phases and determine if they exceed threshold
    
    Args:
        phase1: Metrics from phase 1
        phase2: Metrics from phase 2
        
    Returns:
        Dictionary with comparison results
    """
    def calculate_ratio(val1, val2):
        """Calculate the ratio (max/min)"""
        if val1 == 0 or val2 == 0 or pd.isna(val1) or pd.isna(val2):
            return np.nan
        return max(val1, val2) / min(val1, val2)
    
    # Calculate ratios
    duration_ratio = calculate_ratio(
        phase1['median_duration_seconds'],
        phase2['median_duration_seconds']
    )
    
    trades_per_day_ratio = calculate_ratio(
        phase1['trades_per_day'],
        phase2['trades_per_day']
    )
    
    risk_ratio = calculate_ratio(
        phase1['median_risk_percent'],
        phase2['median_risk_percent']
    )
    
    # Check if exceeds threshold (ratio >= 3.0 means >= 200% difference)
    threshold = config.STRATEGY_CONSISTENCY_THRESHOLD
    
    return {
        'duration_ratio': duration_ratio,
        'duration_exceeds': duration_ratio >= threshold if pd.notna(duration_ratio) else False,
        'trades_per_day_ratio': trades_per_day_ratio,
        'trades_per_day_exceeds': trades_per_day_ratio >= threshold if pd.notna(trades_per_day_ratio) else False,
        'risk_ratio': risk_ratio,
        'risk_exceeds': risk_ratio >= threshold if pd.notna(risk_ratio) else False
    }


def print_results(result: dict):
    """Print formatted results"""
    utils.print_rule_header(result['rule_number'], result['rule_name'])
    
    if result['status'] == config.STATUS_NOT_TESTABLE:
        utils.print_rule_result(
            config.STATUS_NOT_TESTABLE,
            result['message'],
            {
                'Phase 1 Trades': result['phase1_trades'],
                'Phase 2 Trades': result['phase2_trades'],
                'Minimum Required': config.STRATEGY_CONSISTENCY_MIN_TRADES
            }
        )
        return
    
    # Print metrics comparison
    print("PHASE 1 METRICS:")
    print(f"  - Trades: {result['phase1_trades']}")
    print(f"  - Trading Days: {result['phase1_metrics']['distinct_trading_days']}")
    print(f"  - Median Duration: {utils.format_duration(result['phase1_metrics']['median_duration_seconds'])}")
    print(f"  - Trades per Day: {result['phase1_metrics']['trades_per_day']:.2f}")
    print(f"  - Median Risk: {result['phase1_metrics']['median_risk_percent']:.2f}%" if pd.notna(result['phase1_metrics']['median_risk_percent']) else "  - Median Risk: N/A (no SL data)")
    
    print("\nPHASE 2 METRICS:")
    print(f"  - Trades: {result['phase2_trades']}")
    print(f"  - Trading Days: {result['phase2_metrics']['distinct_trading_days']}")
    print(f"  - Median Duration: {utils.format_duration(result['phase2_metrics']['median_duration_seconds'])}")
    print(f"  - Trades per Day: {result['phase2_metrics']['trades_per_day']:.2f}")
    print(f"  - Median Risk: {result['phase2_metrics']['median_risk_percent']:.2f}%" if pd.notna(result['phase2_metrics']['median_risk_percent']) else "  - Median Risk: N/A (no SL data)")
    
    print("\nMETRIC COMPARISONS:")
    diff = result['differences']
    print(f"  1. Duration Ratio: {diff['duration_ratio']:.2f}x {'❌ EXCEEDS' if diff['duration_exceeds'] else '✅ OK'}")
    print(f"  2. Trades/Day Ratio: {diff['trades_per_day_ratio']:.2f}x {'❌ EXCEEDS' if diff['trades_per_day_exceeds'] else '✅ OK'}")
    print(f"  3. Risk Ratio: {diff['risk_ratio']:.2f}x {'❌ EXCEEDS' if diff['risk_exceeds'] else '✅ OK'}" if pd.notna(diff['risk_ratio']) else "  3. Risk Ratio: N/A (insufficient SL data)")
    
    print(f"\nMetrics exceeding 200% threshold: {result['metrics_exceeded_threshold']} / 3")
    
    if result['status'] == config.STATUS_VIOLATED:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Strategy consistency violation detected. {result['metrics_exceeded_threshold']} metrics differ by ≥ 200%"
        )
        print("\n📋 VIOLATION REASON:")
        print(f"   {result['violation_reason']}\n")
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "Strategy is consistent between phases. Less than 2 metrics differ by ≥ 200%"
        )


def export_results(result: dict, output_prefix: str = "Rule_3"):
    """Export results to CSV"""
    # Export summary
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Message': result.get('message', ''),
        'Phase 1 Trades': result['phase1_trades'],
        'Phase 2 Trades': result['phase2_trades']
    }
    
    if result['status'] != config.STATUS_NOT_TESTABLE:
        summary['Metrics Exceeded Threshold'] = result['metrics_exceeded_threshold']
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f"{output_prefix}_summary.csv", index=False)
    print(f"\nSummary exported to: {output_prefix}_summary.csv")


def main():
    """Main execution function"""
    print("=" * 80)
    print("RULE 3: Strategy Consistency")
    print("=" * 80)
    print("\nNOTE: This rule requires TWO CSV files (one for each phase to compare)")
    print("Usage: python Rule_3.py <phase1.csv> <phase2.csv> <equity_phase1> <equity_phase2>")
    print("\nExample: python Rule_3.py phase1_trades.csv funded_trades.csv 100000 100000")
    print("=" * 80 + "\n")
    
    # Check command line arguments
    if len(sys.argv) >= 5:
        csv_file1 = sys.argv[1]
        csv_file2 = sys.argv[2]
        equity1 = float(sys.argv[3])
        equity2 = float(sys.argv[4])
    else:
        # Default: try to use the same file as both phases (for testing purposes)
        print("⚠️ WARNING: Not enough arguments provided.")
        print("For proper testing, this rule needs two separate phase files.\n")
        print("Running in TEST MODE with single file split in half...\n")
        
        csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
        
        # Load and split data
        df = utils.load_csv(csv_file)
        midpoint = len(df) // 2
        df_phase1 = df.iloc[:midpoint]
        df_phase2 = df.iloc[midpoint:]
        
        equity1 = 100000  # Default
        equity2 = 100000
        
        print(f"Loaded {len(df)} trades from: {csv_file}")
        print(f"Split into Phase 1 ({len(df_phase1)} trades) and Phase 2 ({len(df_phase2)} trades)\n")
        
        # Check for strategy consistency
        result = check_strategy_consistency(df_phase1, df_phase2, equity1, equity2)
        
        # Print results
        print_results(result)
        
        # Export results
        export_results(result)
        return
    
    try:
        # Load both CSV files
        print(f"Loading Phase 1 data from: {csv_file1}")
        df_phase1 = utils.load_csv(csv_file1)
        print(f"Successfully loaded {len(df_phase1)} trades from Phase 1\n")
        
        print(f"Loading Phase 2 data from: {csv_file2}")
        df_phase2 = utils.load_csv(csv_file2)
        print(f"Successfully loaded {len(df_phase2)} trades from Phase 2\n")
        
        # Check for strategy consistency
        result = check_strategy_consistency(df_phase1, df_phase2, equity1, equity2)
        
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
