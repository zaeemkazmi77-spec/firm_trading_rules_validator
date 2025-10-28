"""
Test All Rules - Comprehensive Testing Script

This script runs all trading rules against the provided CSV file
and generates a comprehensive summary report showing which rules were
PASSED, VIOLATED, or NOT_TESTABLE.
"""

import subprocess
import sys
import pandas as pd
from datetime import datetime
import re
import os

# Set UTF-8 encoding for console output (Windows compatibility)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

def run_rule(rule_script, *args):
    """
    Run a rule script and capture output
    
    Args:
        rule_script: Name of the rule script
        *args: Additional arguments for the script
        
    Returns:
        Tuple of (return_code, output)
    """
    cmd = [sys.executable, f"rules/{rule_script}"] + list(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "ERROR: Script timed out after 30 seconds"
    except Exception as e:
        return -1, f"ERROR: {str(e)}"


def parse_rule_status(output):
    """
    Parse the output to determine if rule was PASSED, VIOLATED, or NOT_TESTABLE
    
    Args:
        output: Script output text
        
    Returns:
        Tuple of (status, violations_count)
    """
    # Look for status indicators in output (text only, not emoji)
    if "VIOLATED" in output and "Status:" in output:
        # Extract violations count
        match = re.search(r'Violations found: (\d+)', output)
        violations = int(match.group(1)) if match else 1  # Default to 1 if found violation text
        return "VIOLATED", violations
    elif "PASSED" in output and "Status:" in output:
        return "PASSED", 0
    elif "NOT_TESTABLE" in output or "NOT TESTABLE" in output:
        return "NOT_TESTABLE", 0
    elif "ERROR" in output or "Traceback" in output:
        return "ERROR", 0
    else:
        return "UNKNOWN", 0


def main():
    """Main test execution"""
    print("=" * 80)
    print("TRADING RULES VALIDATION - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Configuration
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "Trades121.csv"
    account_equity = 100000
    account_type = "Funded Phase"
    addon_enabled = "false"
    
    print(f"Configuration:")
    print(f"  CSV File: {csv_file}")
    print(f"  Account Equity: ${account_equity:,.2f}")
    print(f"  Account Type: {account_type}")
    print(f"  Add-on Enabled: {addon_enabled}")
    print("\n" + "=" * 80 + "\n")
    
    # Test all rules
    test_results = []
    
    # Rule 1: Hedging Ban
    print("Testing Rule 1: Hedging Ban...")
    returncode, output = run_rule("Rule_1.py", csv_file)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 1,
        'Name': 'Hedging Ban',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 3: Strategy Consistency
    print("Testing Rule 3: Strategy Consistency...")
    returncode, output = run_rule("Rule_3.py", csv_file)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 3,
        'Name': 'Strategy Consistency',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 4: Prohibited EAs
    print("Testing Rule 4: Prohibited Third-Party Strategies (EAs)...")
    returncode, output = run_rule("Rule_4.py", csv_file)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 4,
        'Name': 'Prohibited EAs',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 12: All-or-Nothing Trading
    print("Testing Rule 12: All-or-Nothing Trading...")
    returncode, output = run_rule("Rule_12.py", csv_file, str(account_equity))
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 12,
        'Name': 'All-or-Nothing Trading',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 13: Maximum Margin Usage
    print("Testing Rule 13: Maximum Margin Usage (80%)...")
    returncode, output = run_rule("Rule_13.py", csv_file, str(account_equity), account_type)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 13,
        'Name': 'Maximum Margin Usage',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 14: Gambling Definition
    print("Testing Rule 14: Gambling Definition...")
    returncode, output = run_rule("Rule_14.py", csv_file)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 14,
        'Name': 'Gambling Definition',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 15: One-Sided Bets
    print("Testing Rule 15: One-Sided Bets...")
    returncode, output = run_rule("Rule_15.py", csv_file)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 15,
        'Name': 'One-Sided Bets',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 16: Abuse of Simulated Environment
    print("Testing Rule 16: Abuse of Simulated Environment...")
    returncode, output = run_rule("Rule_16.py", csv_file, str(account_equity))
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 16,
        'Name': 'Abuse of Simulated Environment',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 17: Max 2% Risk per Trade Idea
    print("Testing Rule 17: Max 2% Risk per Trade Idea...")
    returncode, output = run_rule("Rule_17.py", csv_file, str(account_equity), "Direct Funding")
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 17,
        'Name': 'Max 2% Risk per Trade Idea',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 18: News Trading Restriction
    print("Testing Rule 18: News Trading Restriction...")
    returncode, output = run_rule("Rule_18.py", csv_file, addon_enabled)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 18,
        'Name': 'News Trading Restriction',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 19: Weekend Trading and Holding
    print("Testing Rule 19: Weekend Trading and Holding...")
    returncode, output = run_rule("Rule_19.py", csv_file, addon_enabled)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 19,
        'Name': 'Weekend Trading and Holding',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Rule 23: Minimum Trading Days
    print("Testing Rule 23: Minimum Trading Days...")
    returncode, output = run_rule("Rule_23.py", csv_file, account_type)
    status, violations = parse_rule_status(output)
    test_results.append({
        'Rule': 23,
        'Name': 'Minimum Trading Days',
        'Status': status,
        'Violations': violations,
        'Script_Exit': 'OK' if returncode == 0 else 'ERROR'
    })
    status_icon = '✅' if status == 'PASSED' else '❌' if status == 'VIOLATED' else '⚠️'
    print(f"  Status: {status_icon} {status} ({violations} violations)\n")
    
    # Generate summary
    print("=" * 80)
    print("RULES COMPLIANCE SUMMARY")
    print("=" * 80)
    
    df_results = pd.DataFrame(test_results)
    print(df_results.to_string(index=False))
    
    # Count results
    total_tests = len(test_results)
    passed_rules = len([r for r in test_results if r['Status'] == 'PASSED'])
    violated_rules = len([r for r in test_results if r['Status'] == 'VIOLATED'])
    not_testable = len([r for r in test_results if r['Status'] == 'NOT_TESTABLE'])
    errors = len([r for r in test_results if r['Status'] == 'ERROR'])
    
    total_violations = sum([r['Violations'] for r in test_results])
    
    print("\n" + "=" * 80)
    print(f"Total Rules Tested: {total_tests}")
    print(f"✅ PASSED: {passed_rules}")
    print(f"❌ VIOLATED: {violated_rules} (Total violations: {total_violations})")
    print(f"⚠️  NOT TESTABLE: {not_testable}")
    if errors > 0:
        print(f"🔴 ERRORS: {errors}")
    print("=" * 80)
    
    # Show violated rules details
    if violated_rules > 0:
        print("\n⚠️  RULES VIOLATIONS DETECTED:")
        print("-" * 80)
        for r in test_results:
            if r['Status'] == 'VIOLATED':
                print(f"  Rule {r['Rule']}: {r['Name']} - {r['Violations']} violation(s)")
                # Check if violation CSV exists
                csv_file = f"Rule_{r['Rule']}_violations.csv"
                if os.path.exists(csv_file):
                    print(f"    📄 Details: {csv_file}")
        print("-" * 80)
    
    # Overall compliance status
    print("\n" + "=" * 80)
    if violated_rules == 0 and errors == 0:
        print("✅ COMPLIANCE STATUS: PASSED - All rules complied!")
    else:
        print("❌ COMPLIANCE STATUS: FAILED - Violations detected!")
    print("=" * 80)
    
    # Export summary
    df_results.to_csv("test_all_rules_summary.csv", index=False)
    print(f"\n📊 Summary exported to: test_all_rules_summary.csv")
    
    print(f"\n🕐 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if (violated_rules == 0 and errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
