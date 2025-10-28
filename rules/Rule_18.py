"""
Rule 18: News Trading Restriction

Trading within 5 minutes (300 seconds) before or after a relevant economic news 
release is forbidden.
Applies to manual and automatic executions (including SL/TP).
If Add-on = OFF and trade falls in this window → Violation.
If Add-on = ON → No violation.
"""

import pandas as pd
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import config
import utils

def check_news_trading(df: pd.DataFrame, addon_enabled: bool = False) -> dict:
    """
    Check for news trading violations
    
    Args:
        df: DataFrame with trade data
        addon_enabled: Whether news trading add-on is enabled
        
    Returns:
        Dictionary with rule results
    """
    # If add-on is enabled, skip this rule
    if addon_enabled:
        return {
            'rule_number': 18,
            'rule_name': 'News Trading Restriction',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'News Trading Add-on is enabled. This rule is skipped.',
            'total_trades': len(df),
            'addon_enabled': True
        }
    
    # Get date range from trades
    min_date = df['Open Time'].min().date()
    max_date = df['Close Time'].max().date()
    
    print(f"Fetching news events from {min_date} to {max_date}...")
    
    # Fetch news events from ForexFactory
    news_events = fetch_forex_factory_news(min_date, max_date)
    
    if not news_events:
        return {
            'rule_number': 18,
            'rule_name': 'News Trading Restriction',
            'status': config.STATUS_NOT_TESTABLE,
            'message': 'Unable to fetch news data from ForexFactory. Cannot test this rule.',
            'total_trades': len(df),
            'addon_enabled': False
        }
    
    print(f"Found {len(news_events)} news events")
    
    # Check each trade for news trading violations
    violations = []
    
    for _, trade in df.iterrows():
        # Get relevant currencies for this instrument
        base_curr, quote_curr = utils.get_instrument_currency_pairs(trade['Instrument'])
        relevant_currencies = [base_curr, quote_curr] if base_curr else []
        
        # Check if trade opens or closes near a news event
        for event in news_events:
            # Check if currency is relevant
            if event['currency'] not in relevant_currencies:
                continue
            
            # Check open time
            time_diff_open = abs((trade['Open Time'] - event['time']).total_seconds())
            if time_diff_open <= config.NEWS_BUFFER_SECONDS:
                violation_reason = (
                    f"NEWS TRADING VIOLATION: Position {trade['Position ID']} ({trade['Instrument']}) "
                    f"was OPENED at {trade['Open Time'].strftime('%Y-%m-%d %H:%M:%S')} UTC, "
                    f"which is {int(time_diff_open)} seconds {'before' if trade['Open Time'] < event['time'] else 'after'} "
                    f"the news event '{event['title']}' ({event['currency']}) scheduled at "
                    f"{event['time'].strftime('%Y-%m-%d %H:%M:%S')} UTC. "
                    f"This is within the prohibited ±{config.NEWS_BUFFER_SECONDS // 60} minute buffer around news releases. "
                    f"[Rule 18: No trading ±5 minutes from relevant news events]"
                )
                
                violations.append({
                    'Position_ID': trade['Position ID'],
                    'Instrument': trade['Instrument'],
                    'Event_Type': 'OPEN',
                    'Trade_Time': trade['Open Time'],
                    'News_Event': event['title'],
                    'News_Currency': event['currency'],
                    'News_Time': event['time'],
                    'Time_Difference_Seconds': time_diff_open,
                    'Violation_Reason': violation_reason
                })
            
            # Check close time
            time_diff_close = abs((trade['Close Time'] - event['time']).total_seconds())
            if time_diff_close <= config.NEWS_BUFFER_SECONDS:
                violation_reason = (
                    f"NEWS TRADING VIOLATION: Position {trade['Position ID']} ({trade['Instrument']}) "
                    f"was CLOSED at {trade['Close Time'].strftime('%Y-%m-%d %H:%M:%S')} UTC, "
                    f"which is {int(time_diff_close)} seconds {'before' if trade['Close Time'] < event['time'] else 'after'} "
                    f"the news event '{event['title']}' ({event['currency']}) scheduled at "
                    f"{event['time'].strftime('%Y-%m-%d %H:%M:%S')} UTC. "
                    f"This is within the prohibited ±{config.NEWS_BUFFER_SECONDS // 60} minute buffer around news releases. "
                    f"[Rule 18: No trading ±5 minutes from relevant news events]"
                )
                
                violations.append({
                    'Position_ID': trade['Position ID'],
                    'Instrument': trade['Instrument'],
                    'Event_Type': 'CLOSE',
                    'Trade_Time': trade['Close Time'],
                    'News_Event': event['title'],
                    'News_Currency': event['currency'],
                    'News_Time': event['time'],
                    'Time_Difference_Seconds': time_diff_close,
                    'Violation_Reason': violation_reason
                })
    
    # Determine status
    status = config.STATUS_VIOLATED if violations else config.STATUS_PASSED
    
    return {
        'rule_number': 18,
        'rule_name': 'News Trading Restriction',
        'status': status,
        'total_trades': len(df),
        'news_events_found': len(news_events),
        'violations_found': len(violations),
        'violations': violations,
        'addon_enabled': False
    }


def fetch_forex_factory_news(start_date, end_date):
    """
    Fetch news events from ForexFactory
    Note: This is a simplified placeholder. In production, you would use web scraping
    or an API to fetch real news data.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of news events
    """
    # IMPORTANT: This is a placeholder implementation
    # In a real application, you would:
    # 1. Use ForexFactory's calendar page or API
    # 2. Parse HTML with BeautifulSoup
    # 3. Filter for high-impact news events
    
    print("⚠️  WARNING: Using mock news data. In production, integrate with ForexFactory API.")
    
    # Return empty list for now (no violations will be detected)
    # In production, this would return actual news events like:
    # [
    #     {'time': datetime(...), 'currency': 'USD', 'title': 'NFP', 'impact': 'high'},
    #     ...
    # ]
    
    return []


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
    print(f"News events found: {result['news_events_found']}")
    print(f"News buffer: ±{config.NEWS_BUFFER_SECONDS} seconds (5 minutes)")
    print(f"Violations found: {result['violations_found']}\n")
    
    if result['violations_found'] > 0:
        utils.print_rule_result(
            config.STATUS_VIOLATED,
            f"Found {result['violations_found']} trade(s) within ±5 minutes of news events"
        )
        
        print("VIOLATION DETAILS:")
        print("-" * 80)
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"\nViolation #{idx}:")
            print(f"  Position ID: {violation['Position_ID']}")
            print(f"  Instrument: {violation['Instrument']}")
            print(f"  Event Type: {violation['Event_Type']}")
            print(f"  Trade Time: {violation['Trade_Time']}")
            print(f"  News Event: {violation['News_Event']}")
            print(f"  News Currency: {violation['News_Currency']}")
            print(f"  News Time: {violation['News_Time']}")
            print(f"  Time Difference: {violation['Time_Difference_Seconds']:.0f} seconds ❌")
            print(f"\n  📋 REASON:")
            print(f"     {violation['Violation_Reason']}")
            print("-" * 80)
    else:
        utils.print_rule_result(
            config.STATUS_PASSED,
            "No news trading violations detected."
        )


def export_results(result: dict, output_prefix: str = "Rule_18"):
    """Export results to CSV"""
    summary = {
        'Rule': result['rule_number'],
        'Rule Name': result['rule_name'],
        'Status': result['status'],
        'Total Trades': result['total_trades'],
        'News Events Found': result.get('news_events_found', 0),
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
        print("Usage: python Rule_18.py <csv_file> <addon_enabled>")
        print("Example: python Rule_18.py Trades121.csv false\n")
    
    print(f"Loading data from: {csv_file}")
    print(f"News Trading Add-on: {'Enabled' if addon_enabled else 'Disabled'}\n")
    
    try:
        df = utils.load_csv(csv_file)
        print(f"Successfully loaded {len(df)} trades\n")
        
        is_valid, errors = utils.validate_csv_quality(df)
        if not is_valid:
            print("CSV Validation Failed:")
            for error in errors:
                print(f"  - {error}")
            return
        
        result = check_news_trading(df, addon_enabled)
        print_results(result)
        export_results(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
