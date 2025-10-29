"""
Rule Executor Module
Coordinates execution of all trading rules
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Any
import streamlit as st

# Import rule modules
sys.path.append(str(Path(__file__).parent / "rules"))

from rules import config
from rules import Rule_1, Rule_3, Rule_4, Rule_12, Rule_13, Rule_14, Rule_15, Rule_16, Rule_17, Rule_18, Rule_19, Rule_23


def execute_all_rules(
    phases: Dict[str, pd.DataFrame],
    account_type: str,
    account_size: float,
    news_addon_enabled: bool,
    weekend_addon_enabled: bool,
    active_rules: List[int]
) -> List[Dict[str, Any]]:
    """
    Execute all active rules and collect results
    
    Args:
        phases: Dictionary mapping phase names to DataFrames
        account_type: Selected account type
        account_size: Account equity
        news_addon_enabled: Whether News Trading add-on is enabled
        weekend_addon_enabled: Whether Weekend Holding add-on is enabled
        active_rules: List of rule numbers to execute
        
    Returns:
        List of rule results
    """
    results = []
    
    # Get main DataFrame (merge all phases for single-phase rules)
    if len(phases) == 1:
        main_df = list(phases.values())[0]
    else:
        # Merge all phases
        main_df = pd.concat(phases.values(), ignore_index=True)
    
    # Progress tracking
    total_rules = len(active_rules)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, rule_num in enumerate(active_rules):
        status_text.text(f"Testing Rule {rule_num} of {max(active_rules)}...")
        
        try:
            if rule_num == 1:
                result = execute_rule_1(main_df)
            elif rule_num == 3:
                result = execute_rule_3(phases, account_size)
            elif rule_num == 4:
                result = execute_rule_4(main_df)
            elif rule_num == 12:
                result = execute_rule_12(main_df, account_size, account_type)
            elif rule_num == 13:
                result = execute_rule_13(main_df, account_size, account_type)
            elif rule_num == 14:
                result = execute_rule_14(main_df)
            elif rule_num == 15:
                result = execute_rule_15(main_df, account_size)
            elif rule_num == 16:
                result = execute_rule_16(main_df, account_size)
            elif rule_num == 17:
                result = execute_rule_17(main_df, account_size, account_type)
            elif rule_num == 18:
                result = execute_rule_18(main_df, news_addon_enabled)
            elif rule_num == 19:
                result = execute_rule_19(main_df, weekend_addon_enabled, account_size)
            elif rule_num == 23:
                result = execute_rule_23(main_df, account_type)
            else:
                result = {
                    'rule_number': rule_num,
                    'rule_name': f'Rule {rule_num}',
                    'status': config.STATUS_NOT_TESTABLE,
                    'message': 'Rule not implemented'
                }
            
            results.append(result)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"❌ Error executing Rule {rule_num}: {str(e)}")
            with st.expander("Show Error Details"):
                st.code(error_details)
            results.append({
                'rule_number': rule_num,
                'rule_name': f'Rule {rule_num}',
                'status': config.STATUS_NOT_TESTABLE,
                'message': f'Error: {str(e)}',
                'error_details': error_details
            })
        
        # Update progress
        progress_bar.progress((idx + 1) / total_rules)
    
    status_text.text("✅ All rules tested!")
    progress_bar.empty()
    status_text.empty()
    
    return results


def execute_rule_1(df: pd.DataFrame) -> Dict[str, Any]:
    """Execute Rule 1: Hedging Ban"""
    return Rule_1.check_hedging_violation(df)


def execute_rule_3(phases: Dict[str, pd.DataFrame], account_size: float) -> Dict[str, Any]:
    """Execute Rule 3: Strategy Consistency"""
    # Need at least 2 phases
    phase_list = list(phases.keys())
    
    if len(phases) < 2:
        return {
            'rule_number': 3,
            'rule_name': 'Strategy Consistency',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'Need at least 2 phases to test consistency',
            'phase1_trades': len(list(phases.values())[0]) if phases else 0,
            'phase2_trades': 0
        }
    
    # Get phase 1 and phase 2 data
    # Try to intelligently match phases
    if "Phase 1" in phases and "Phase 2" in phases:
        df_phase1 = phases["Phase 1"]
        df_phase2 = phases["Phase 2"]
    elif "Phase 1" in phases and "Funded Phase" in phases:
        df_phase1 = phases["Phase 1"]
        df_phase2 = phases["Funded Phase"]
    elif "Phase 2" in phases and "Funded Phase" in phases:
        df_phase1 = phases["Phase 2"]
        df_phase2 = phases["Funded Phase"]
    else:
        # Use first two phases
        df_phase1 = phases[phase_list[0]]
        df_phase2 = phases[phase_list[1]]
    
    return Rule_3.check_strategy_consistency(df_phase1, df_phase2, account_size, account_size)


def execute_rule_4(df: pd.DataFrame) -> Dict[str, Any]:
    """Execute Rule 4: Prohibited EAs"""
    return Rule_4.check_ea_violation(df)


def execute_rule_12(df: pd.DataFrame, account_size: float, account_type: str) -> Dict[str, Any]:
    """Execute Rule 12: All-or-Nothing Trading"""
    return Rule_12.check_all_or_nothing(df, account_size, account_type)


def execute_rule_13(df: pd.DataFrame, account_size: float, account_type: str) -> Dict[str, Any]:
    """Execute Rule 13: Maximum Margin Usage"""
    account_config = config.ACCOUNT_TYPES[account_type]
    leverage = account_config['leverage']
    return Rule_13.check_margin_usage(df, account_size, account_type)


def execute_rule_14(df: pd.DataFrame) -> Dict[str, Any]:
    """Execute Rule 14: Gambling Definition"""
    return Rule_14.check_gambling(df)


def execute_rule_15(df: pd.DataFrame, account_size: float) -> Dict[str, Any]:
    """Execute Rule 15: One-Sided Bets"""
    return Rule_15.check_one_sided_bets(df)


def execute_rule_16(df: pd.DataFrame, account_size: float) -> Dict[str, Any]:
    """Execute Rule 16: Abuse of Simulated Environment"""
    return Rule_16.check_abuse_of_sim_environment(df, account_size)


def execute_rule_17(df: pd.DataFrame, account_size: float, account_type: str) -> Dict[str, Any]:
    """Execute Rule 17: Max 2% Risk per Trade Idea"""
    if account_type != "Direct Funding":
        return {
            'rule_number': 17,
            'rule_name': 'Max 2% Risk per Trade Idea',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'Only applicable to Direct Funding accounts'
        }
    return Rule_17.check_max_risk_per_idea(df, account_size, account_type)


def execute_rule_18(df: pd.DataFrame, addon_enabled: bool) -> Dict[str, Any]:
    """Execute Rule 18: News Trading Restriction"""
    if addon_enabled:
        return {
            'rule_number': 18,
            'rule_name': 'News Trading Restriction',
            'status': config.STATUS_PASSED,
            'message': 'Skipped - Add-on enabled'
        }
    return Rule_18.check_news_trading(df, addon_enabled)


def execute_rule_19(df: pd.DataFrame, addon_enabled: bool, account_size: float) -> Dict[str, Any]:
    """Execute Rule 19: Weekend Trading"""
    if addon_enabled:
        return {
            'rule_number': 19,
            'rule_name': 'Weekend Trading and Holding',
            'status': config.STATUS_PASSED,
            'message': 'Skipped - Add-on enabled'
        }
    return Rule_19.check_weekend_trading(df, addon_enabled)


def execute_rule_23(df: pd.DataFrame, account_type: str) -> Dict[str, Any]:
    """Execute Rule 23: Minimum Trading Days"""
    return Rule_23.check_minimum_trading_days(df, account_type)
