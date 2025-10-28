"""
Trading Rule Validation Dashboard
A comprehensive Streamlit web application for validating trading data against fixed rules
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import io
import re
from pathlib import Path
import pytz
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Add rules directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rules'))
import config
from utils import load_csv, validate_csv_quality

# Get Python executable path
PYTHON_EXECUTABLE = sys.executable

# Page configuration
st.set_page_config(
    page_title="Trading Rule Validation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .status-passed {
        color: #28a745;
        font-weight: bold;
    }
    .status-violated {
        color: #dc3545;
        font-weight: bold;
    }
    .status-not-testable {
        color: #ffc107;
        font-weight: bold;
    }
    .status-skipped {
        color: #6c757d;
        font-weight: bold;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = {}
if 'rule_results' not in st.session_state:
    st.session_state.rule_results = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'phase_mapping' not in st.session_state:
    st.session_state.phase_mapping = {}  # Maps file_key to phase label
if 'session_logs' not in st.session_state:
    st.session_state.session_logs = []  # Logging for errors and warnings
if 'display_timezone' not in st.session_state:
    st.session_state.display_timezone = 'UTC'  # Default display timezone


def convert_to_display_timezone(dt, timezone='UTC'):
    """Convert UTC datetime to display timezone"""
    if pd.isna(dt):
        return dt
    
    if timezone == 'Europe/Zurich':
        zurich_tz = pytz.timezone('Europe/Zurich')
        if hasattr(dt, 'tz_convert'):
            return dt.tz_convert(zurich_tz)
        elif hasattr(dt, 'tz_localize'):
            return dt.tz_localize('UTC').tz_convert(zurich_tz)
    return dt


def log_message(rule_number: Optional[int], file_name: str, message: str, level: str = "INFO"):
    """Add a log entry to session logs"""
    log_entry = {
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Level': level,
        'Rule': f"Rule {rule_number}" if rule_number else "System",
        'File': file_name,
        'Message': message
    }
    st.session_state.session_logs.append(log_entry)



def validate_uploaded_csv(uploaded_file, file_key: str) -> Tuple[bool, Optional[pd.DataFrame], List[str]]:
    """
    Validate an uploaded CSV file
    
    Returns:
        Tuple of (is_valid, dataframe, error_messages)
    """
    errors = []
    
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_{file_key}_{uploaded_file.name}"
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Load and validate CSV
        df = load_csv(temp_path)
        
        # Validate data quality
        is_valid, quality_errors = validate_csv_quality(df, min_valid_percent=95.0)
        
        if not is_valid:
            errors.extend(quality_errors)
            for error in quality_errors:
                log_message(None, uploaded_file.name, error, "ERROR")
            os.remove(temp_path)
            return False, None, errors
        
        # Store the temp path for later use
        st.session_state.uploaded_files[file_key] = {
            'dataframe': df,
            'temp_path': temp_path,
            'original_name': uploaded_file.name,
            'trades_count': len(df),
            'date_range': f"{df['Open Time'].min().strftime('%Y-%m-%d')} to {df['Close Time'].max().strftime('%Y-%m-%d')}"
        }
        
        log_message(None, uploaded_file.name, f"File validated successfully: {len(df)} trades", "INFO")
        return True, df, []
        
    except Exception as e:
        errors.append(f"Error processing file: {str(e)}")
        log_message(None, uploaded_file.name, f"Error processing file: {str(e)}", "ERROR")
        return False, None, errors


def get_rule_info() -> Dict:
    """
    Get information about all available rules
    """
    return {
        1: {"name": "Hedging Ban", "description": "No simultaneous Long/Short positions on same instrument"},
        3: {"name": "Strategy Consistency", "description": "Consistent trading behavior between phases"},
        4: {"name": "Prohibited EAs", "description": "No automated trading systems allowed"},
        12: {"name": "All-or-Nothing Trading", "description": "Single trade/idea cannot risk entire account"},
        13: {"name": "Maximum Margin Usage", "description": "Margin usage must stay below 80%"},
        14: {"name": "Gambling Definition", "description": "Max 50% of trades can be under 60 seconds"},
        15: {"name": "One-Sided Bets", "description": "Max 2 trades same direction per symbol"},
        16: {"name": "Abuse of Simulated Environment", "description": "Volume and SL requirements"},
        17: {"name": "Max 2% Risk per Trade", "description": "Direct Funding: max 2% risk per idea"},
        18: {"name": "News Trading Restriction", "description": "No trading ±5 min around news releases"},
        19: {"name": "Weekend Trading Ban", "description": "No trading Fri 22:00 - Sun 22:00 UTC"},
        23: {"name": "Minimum Trading Days", "description": "Minimum active trading days requirement"}
    }


def parse_rule_status(output: str, exit_code: int = 0) -> Tuple[str, int, Dict]:
    """
    Robustly parse rule execution output to extract status and details.
    Accepts many variants and is case-insensitive.
    
    Args:
        output: Rule script stdout/stderr output
        exit_code: Process exit code
        
    Returns:
        Tuple of (status, violation_count, details_dict)
    """
    import json
    
    details = {}
    violation_count = 0
    text = (output or "").strip()
    low = text.lower()

    # Try JSON first (if a rule prints a JSON object with status/violations)
    json_obj = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                json_obj = json.loads(line)
                break
            except Exception:
                pass
    
    if json_obj:
        status = str(json_obj.get("status", "")).upper().replace(" ", "_")
        violation_count = int(json_obj.get("violation_count", json_obj.get("violations", 0)) or 0)
        # Merge the rest as details
        for k, v in json_obj.items():
            if k not in {"status", "violation_count", "violations"}:
                details[str(k)] = str(v)
        if status in {"PASSED", "VIOLATED", "NOT_TESTABLE", "SKIPPED"}:
            return status, violation_count, details

    # Normalize ANSI codes and emojis away for matching
    ansi_stripped = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text)  # remove ANSI
    low = ansi_stripped.lower()

    # Broad matching (case-insensitive, with synonyms)
    def has(*needles):
        return any(n.lower() in low for n in needles)

    # Violated
    if has("❌", "violated", "violation"):
        status = "VIOLATED"
        # Try to extract a number
        m = re.search(r'(\d+)\s+violation', low, re.IGNORECASE)
        if m:
            violation_count = int(m.group(1))

    # Skipped
    elif has("⏭", "skipped", "not applicable", "n/a"):
        status = "SKIPPED"

    # Not testable
    elif has("not testable", "missing data", "insufficient data", "requires two csv", "requires both phase"):
        status = "NOT_TESTABLE"

    # Passed
    elif has("✅", "passed", "no violation", "no violations", "ok", "pass"):
        status = "PASSED"

    else:
        # If the process succeeded (exit_code==0) and nothing looks like an error,
        # treat as PASSED to avoid "ERROR" noise—adjust if you prefer stricter behavior.
        if exit_code == 0 and not has("error", "traceback", "exception", "failed", "failure"):
            status = "PASSED"
        else:
            status = "ERROR"

    # Extract k:v details
    for line in ansi_stripped.splitlines():
        if ":" in line and not line.strip().startswith("="):
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                details[k] = v

    return status, violation_count, details


def run_single_rule(rule_number: int, csv_file: str, account_type: str, 
                    equity: float, addon_enabled: bool) -> Dict:
    """
    Run a single rule script and return results
    """
    rule_script = f"rules/Rule_{rule_number}.py"
    
    if not os.path.exists(rule_script):
        return {
            'rule_number': rule_number,
            'status': 'ERROR',
            'violation_count': 0,
            'message': f'Rule script not found: {rule_script}',
            'details': {},
            'output': ''
        }
    
    try:
        # Prepare command based on rule requirements
        if rule_number == 3:
            # Rule 3 needs two CSV files - skip for single file
            return {
                'rule_number': rule_number,
                'status': 'NOT_TESTABLE',
                'violation_count': 0,
                'message': 'Rule 3 requires two CSV files for phase comparison',
                'details': {},
                'output': ''
            }
        elif rule_number in [18, 19]:
            # Skip news/weekend rules if addon is enabled
            if addon_enabled:
                return {
                    'rule_number': rule_number,
                    'status': 'SKIPPED',
                    'violation_count': 0,
                    'message': 'Rule skipped - Add-on enabled',
                    'details': {},
                    'output': f'⏭️ SKIPPED: Add-on "News Trading and Weekend Holding" is enabled. Rule {rule_number} does not apply.'
                }
            cmd = [PYTHON_EXECUTABLE, rule_script, csv_file, 'false']  # addon_enabled is always false here
        elif rule_number in [13, 17]:
            # Rules that need equity and account type
            cmd = [PYTHON_EXECUTABLE, rule_script, csv_file, str(equity), account_type]
        elif rule_number == 23:
            # Rule 23 needs account type only
            cmd = [PYTHON_EXECUTABLE, rule_script, csv_file, account_type]
        elif rule_number in [1, 14, 15]:
            # Rules that need only CSV file (no equity parameter)
            cmd = [PYTHON_EXECUTABLE, rule_script, csv_file]
        else:
            # Standard rules that need CSV and equity (4, 12, 16)
            cmd = [PYTHON_EXECUTABLE, rule_script, csv_file, str(equity)]
        
        # Execute rule
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding='utf-8'
        )
        
        output = result.stdout if result.stdout else result.stderr
        
        # Parse status with exit code
        status, violation_count, details = parse_rule_status(output, result.returncode)
        
        return {
            'rule_number': rule_number,
            'status': status,
            'violation_count': violation_count,
            'message': output.split('\n')[0] if output else 'No output',
            'details': details,
            'output': output,
            'exit_code': result.returncode
        }
        
    except Exception as e:
        return {
            'rule_number': rule_number,
            'status': 'ERROR',
            'violation_count': 0,
            'message': f'Error running rule: {str(e)}',
            'details': {},
            'output': str(e),
            'exit_code': -1
        }


def run_rule_3(phase1_file: str, phase2_file: str, equity: float) -> Dict:
    """
    Run Rule 3 (Strategy Consistency) with two phase files
    """
    rule_script = "rules/Rule_3.py"
    
    try:
        cmd = [PYTHON_EXECUTABLE, rule_script, phase1_file, phase2_file, str(equity), str(equity)]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            encoding='utf-8'
        )
        
        output = result.stdout if result.stdout else result.stderr
        status, violation_count, details = parse_rule_status(output, result.returncode)
        
        return {
            'rule_number': 3,
            'status': status,
            'violation_count': violation_count,
            'message': output.split('\n')[0] if output else 'No output',
            'details': details,
            'output': output,
            'exit_code': result.returncode
        }
        
    except Exception as e:
        return {
            'rule_number': 3,
            'status': 'ERROR',
            'violation_count': 0,
            'message': f'Error running Rule 3: {str(e)}',
            'details': {},
            'output': str(e),
            'exit_code': -1
        }



def run_all_rules(account_type: str, equity: float, addon_enabled: bool) -> List[Dict]:
    """
    Run all rules on uploaded files with proper phase mapping
    """
    results = []
    rule_info = get_rule_info()
    
    # Get the first uploaded file (or handle multiple files)
    if not st.session_state.uploaded_files:
        st.error("No files uploaded")
        return results
    
    # Get phase-mapped files
    phase1_file = None
    phase2_file = None
    primary_file = None
    
    for file_key, file_info in st.session_state.uploaded_files.items():
        phase = st.session_state.phase_mapping.get(file_key, "Unassigned")
        if phase == "Phase 1":
            phase1_file = file_info['temp_path']
        elif phase == "Phase 2":
            phase2_file = file_info['temp_path']
        
        # Use first assigned file as primary
        if primary_file is None and phase != "Unassigned":
            primary_file = file_info['temp_path']
    
    # If no phase assigned, use first file
    if primary_file is None:
        first_file_key = list(st.session_state.uploaded_files.keys())[0]
        primary_file = st.session_state.uploaded_files[first_file_key]['temp_path']
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_rules = len(rule_info)
    
    for idx, rule_number in enumerate(rule_info.keys()):
        status_text.text(f"Running Rule {rule_number}: {rule_info[rule_number]['name']}...")
        
        # Special handling for Rule 3
        if rule_number == 3:
            if phase1_file and phase2_file:
                result = run_rule_3(phase1_file, phase2_file, equity)
                log_message(3, "Phase1 & Phase2", "Rule 3 executed with both phase files", "INFO")
            else:
                result = {
                    'rule_number': 3,
                    'status': 'NOT_TESTABLE',
                    'violation_count': 0,
                    'message': 'Rule 3 requires both Phase 1 and Phase 2 files to be assigned',
                    'details': {},
                    'output': '⚠️ NOT TESTABLE: Please assign Phase 1 and Phase 2 labels to your uploaded files.'
                }
                log_message(3, "N/A", "Rule 3 not testable - missing phase assignments", "WARNING")
        else:
            result = run_single_rule(rule_number, primary_file, account_type, equity, addon_enabled)
            if result['status'] == 'ERROR':
                log_message(rule_number, primary_file, result['message'], "ERROR")
            elif result['status'] == 'NOT_TESTABLE':
                log_message(rule_number, primary_file, result['message'], "WARNING")
        
        result['rule_name'] = rule_info[rule_number]['name']
        result['rule_description'] = rule_info[rule_number]['description']
        results.append(result)
        
        progress_bar.progress((idx + 1) / total_rules)
    
    status_text.text("Analysis complete! ✅")
    progress_bar.empty()
    
    return results


def get_affected_trades(rule_number: int) -> int:
    """
    Get count of affected trades from violation CSV file
    
    Returns:
        Count of unique Position IDs affected by violations
    """
    violation_csv = f"rules/Rule_{rule_number}_violations.csv"
    if os.path.exists(violation_csv):
        try:
            viol_df = pd.read_csv(violation_csv)
            if 'Position ID' in viol_df.columns:
                return viol_df['Position ID'].nunique()
            elif len(viol_df) > 0:
                # If no Position ID column, return row count as estimate
                return len(viol_df)
        except Exception:
            pass
    return 0


def display_results_table(results: List[Dict]):
    """
    Display results in a formatted table
    """
    st.markdown('<div class="sub-header">📋 Rule Validation Summary</div>', unsafe_allow_html=True)
    
    # Prepare data for display
    display_data = []
    for result in results:
        status_emoji = {
            'PASSED': '🟢',
            'VIOLATED': '🔴',
            'NOT_TESTABLE': '🟡',
            'SKIPPED': '⏭️',
            'ERROR': '⚫'
        }.get(result['status'], '⚫')
        
        # Get affected trades count for violated rules
        affected_trades = 0
        if result['status'] == 'VIOLATED':
            affected_trades = get_affected_trades(result['rule_number'])
        
        display_data.append({
            'Rule': f"Rule {result['rule_number']}",
            'Name': result['rule_name'],
            'Status': f"{status_emoji} {result['status']}",
            'Violations': result['violation_count'] if result['status'] == 'VIOLATED' else '-',
            'Affected Trades': affected_trades if result['status'] == 'VIOLATED' else '-',
            'Exit Code': result.get('exit_code', 0),
            'Description': result['rule_description']
        })
    
    df = pd.DataFrame(display_data)
    
    # Display with custom styling
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Rule': st.column_config.TextColumn('Rule', width='small'),
            'Name': st.column_config.TextColumn('Rule Name', width='medium'),
            'Status': st.column_config.TextColumn('Status', width='medium'),
            'Violations': st.column_config.NumberColumn('Violations', width='small'),
            'Affected Trades': st.column_config.NumberColumn('Affected Trades', width='small'),
            'Exit Code': st.column_config.NumberColumn('Exit', width='small'),
            'Description': st.column_config.TextColumn('Description', width='large')
        }
    )
    
    # Summary statistics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    passed_count = sum(1 for r in results if r['status'] == 'PASSED')
    violated_count = sum(1 for r in results if r['status'] == 'VIOLATED')
    not_testable_count = sum(1 for r in results if r['status'] == 'NOT_TESTABLE')
    skipped_count = sum(1 for r in results if r['status'] == 'SKIPPED')
    total_violations = sum(r['violation_count'] for r in results)
    
    col1.metric("✅ Passed", passed_count)
    col2.metric("❌ Violated", violated_count)
    col3.metric("⚠️ Not Testable", not_testable_count)
    col4.metric("⏭️ Skipped", skipped_count)
    col5.metric("Total Violations", total_violations)
    
    # Plain text violation summary
    violated_rules = [r for r in results if r['status'] == 'VIOLATED']
    if violated_rules:
        st.markdown("---")
        st.markdown('<div class="sub-header">📝 Violation Summary</div>', unsafe_allow_html=True)
        
        summary_text = []
        for result in violated_rules:
            rule_num = result['rule_number']
            rule_name = result['rule_name']
            
            # Try to read violation CSV and generate narrative
            violation_csv = f"rules/Rule_{rule_num}_violations.csv"
            if os.path.exists(violation_csv):
                try:
                    viol_df = pd.read_csv(violation_csv)
                    if len(viol_df) > 0:
                        # Get first few violations as examples
                        for idx, row in viol_df.head(3).iterrows():
                            position_id = row.get('Position ID', 'Unknown')
                            instrument = row.get('Instrument', 'Unknown')
                            
                            # Convert times to selected timezone
                            if 'Open Time' in row:
                                try:
                                    open_time = pd.to_datetime(row['Open Time'])
                                    if st.session_state.display_timezone == 'Europe/Zurich':
                                        open_time = convert_to_display_timezone(open_time, 'Europe/Zurich')
                                    time_str = open_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                                except:
                                    time_str = str(row['Open Time'])
                            else:
                                time_str = "Unknown time"
                            
                            # Get violation reason if available
                            reason = row.get('Violation_Reason', 'Violation detected')
                            
                            summary_text.append(
                                f"**Rule {rule_num} ({rule_name})**: On {time_str}, violation detected on {instrument} "
                                f"(Position {position_id}). {reason}"
                            )
                        
                        if len(viol_df) > 3:
                            summary_text.append(f"*...and {len(viol_df) - 3} more violations for Rule {rule_num}*")
                except Exception as e:
                    summary_text.append(f"**Rule {rule_num} ({rule_name})**: {result['violation_count']} violations detected. See details below.")
            else:
                summary_text.append(f"**Rule {rule_num} ({rule_name})**: {result['violation_count']} violations detected.")
        
        if summary_text:
            st.markdown("\n\n".join(summary_text))



def display_violation_details(results: List[Dict]):
    """
    Display detailed violation information
    """
    violated_rules = [r for r in results if r['status'] == 'VIOLATED']
    
    if not violated_rules:
        st.success("🎉 No violations detected! All rules passed successfully.")
        return
    
    st.markdown('<div class="sub-header">⚠️ Violation Details</div>', unsafe_allow_html=True)
    
    for result in violated_rules:
        with st.expander(f"🔴 Rule {result['rule_number']}: {result['rule_name']} ({result['violation_count']} violations)"):
            st.markdown(f"**Description:** {result['rule_description']}")
            st.markdown(f"**Violation Count:** {result['violation_count']}")
            
            # Display output in a code block
            if result['output']:
                st.code(result['output'], language='text')
            
            # Check if violation CSV exists
            violation_csv = f"rules/Rule_{result['rule_number']}_violations.csv"
            if os.path.exists(violation_csv):
                try:
                    viol_df = pd.read_csv(violation_csv)
                    st.markdown("**Affected Trades:**")
                    
                    # Use AgGrid for better table display
                    gb = GridOptionsBuilder.from_dataframe(viol_df)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
                    grid_options = gb.build()
                    
                    AgGrid(
                        viol_df,
                        gridOptions=grid_options,
                        enable_enterprise_modules=False,
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        height=min(400, 50 + len(viol_df) * 35),
                        fit_columns_on_grid_load=True
                    )
                except Exception as e:
                    st.warning(f"Could not load violation details: {str(e)}")
                    # Fallback to regular dataframe
                    try:
                        viol_df = pd.read_csv(violation_csv)
                        st.dataframe(viol_df, use_container_width=True)
                    except:
                        pass


def export_results_csv(results: List[Dict]) -> bytes:
    """
    Export results to CSV format
    """
    export_data = []
    for result in results:
        export_data.append({
            'Rule_Number': result['rule_number'],
            'Rule_Name': result['rule_name'],
            'Status': result['status'],
            'Violation_Count': result['violation_count'],
            'Description': result['rule_description'],
            'Message': result['message']
        })
    
    df = pd.DataFrame(export_data)
    return df.to_csv(index=False).encode('utf-8')


def export_results_pdf(results: List[Dict], account_type: str, equity: float) -> bytes:
    """
    Export results to PDF format (using fpdf2)
    """
    try:
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Trading Rule Validation Report', 0, 1, 'C')
        pdf.ln(5)
        
        # Account info
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Account Type: {account_type}', 0, 1)
        pdf.cell(0, 10, f'Account Size: ${equity:,.0f}', 0, 1)
        pdf.cell(0, 10, f'Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
        pdf.ln(5)
        
        # Summary
        passed_count = sum(1 for r in results if r['status'] == 'PASSED')
        violated_count = sum(1 for r in results if r['status'] == 'VIOLATED')
        total_violations = sum(r['violation_count'] for r in results)
        
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Summary', 0, 1)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Passed: {passed_count}', 0, 1)
        pdf.cell(0, 10, f'Violated: {violated_count}', 0, 1)
        pdf.cell(0, 10, f'Total Violations: {total_violations}', 0, 1)
        pdf.ln(5)
        
        # Detailed results
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Detailed Results', 0, 1)
        
        for result in results:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f"Rule {result['rule_number']}: {result['rule_name']}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, f"Status: {result['status']}")
            pdf.multi_cell(0, 5, f"Description: {result['rule_description']}")
            if result['status'] == 'VIOLATED':
                pdf.multi_cell(0, 5, f"Violations: {result['violation_count']}")
            pdf.ln(3)
        
        # Violation Narrative section
        violated_rules = [r for r in results if r['status'] == 'VIOLATED']
        if violated_rules:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Violation Narrative', 0, 1)
            pdf.ln(3)
            
            for result in violated_rules:
                rule_num = result['rule_number']
                rule_name = result['rule_name']
                
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 8, f"Rule {rule_num}: {rule_name}", 0, 1)
                
                # Try to read violation CSV
                violation_csv = f"rules/Rule_{rule_num}_violations.csv"
                if os.path.exists(violation_csv):
                    try:
                        viol_df = pd.read_csv(violation_csv)
                        pdf.set_font('Arial', '', 10)
                        
                        # Add first few violations as narrative
                        for idx, row in viol_df.head(5).iterrows():
                            position_id = row.get('Position ID', 'Unknown')
                            instrument = row.get('Instrument', 'Unknown')
                            
                            # Convert time to Zurich timezone
                            if 'Open Time' in row:
                                try:
                                    open_time = pd.to_datetime(row['Open Time'])
                                    zurich_tz = pytz.timezone('Europe/Zurich')
                                    if open_time.tzinfo is None:
                                        open_time = open_time.tz_localize('UTC')
                                    open_time = open_time.tz_convert(zurich_tz)
                                    time_str = open_time.strftime('%Y-%m-%d %H:%M %Z')
                                except:
                                    time_str = str(row['Open Time'])
                            else:
                                time_str = "Unknown time"
                            
                            reason = row.get('Violation_Reason', 'Violation detected')
                            narrative = f"- On {time_str}, {instrument} (Position {position_id}): {reason[:100]}"
                            pdf.multi_cell(0, 5, narrative.encode('latin-1', 'replace').decode('latin-1'))
                        
                        if len(viol_df) > 5:
                            pdf.multi_cell(0, 5, f"...and {len(viol_df) - 5} more violations")
                    except Exception as e:
                        pdf.multi_cell(0, 5, f"Error reading violation details: {str(e)}")
                else:
                    pdf.set_font('Arial', '', 10)
                    pdf.multi_cell(0, 5, f"{result['violation_count']} violations detected.")
                
                pdf.ln(3)
        
        return bytes(pdf.output())
        
    except ImportError:
        st.error("fpdf2 library not installed. Install with: pip install fpdf2")
        return None
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


# ============================================================================
# MAIN APP LAYOUT
# ============================================================================

def main():
    # Header
    st.markdown('<div class="main-header">📊 Trading Rule Validation Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Account Type Selection
        account_type = st.selectbox(
            "Account Type",
            options=list(config.ACCOUNT_TYPES.keys()),
            help="Select your account type"
        )
        
        # Account Size Selection
        equity = st.selectbox(
            "Account Size ($)",
            options=config.ACCOUNT_SIZES,
            format_func=lambda x: f"${x:,}",
            help="Select your account size"
        )
        
        # Add-on toggle
        account_config = config.ACCOUNT_TYPES[account_type]
        addon_enabled = False
        
        if account_config['addon_allowed']:
            addon_enabled = st.checkbox(
                "Enable Add-on: News Trading and Weekend Holding",
                value=False,
                help="If enabled, Rules 18 and 19 will be skipped"
            )
        else:
            st.info("ℹ️ Add-on not available for this account type")
        
        st.markdown("---")
        
        # News calendar configuration (for Rule 18)
        st.subheader("📰 News Calendar (Rule 18)")
        use_local_calendar = st.checkbox(
            "Use local calendar file (CSV)",
            value=False,
            help="Upload a local news calendar CSV instead of fetching from ForexFactory"
        )
        
        calendar_file = None
        if use_local_calendar:
            calendar_file = st.file_uploader(
                "Upload News Calendar CSV",
                type=['csv'],
                help="CSV with columns: Date, Time, Currency, Event, Impact"
            )
            if calendar_file:
                st.success("✅ Calendar file uploaded")
        else:
            st.info("📡 Will fetch live news data from ForexFactory.com")
        
        st.markdown("---")
        
        # Timezone display preference
        st.subheader("🌐 Display Settings")
        display_timezone = st.selectbox(
            "Timezone for time display",
            options=['UTC', 'Europe/Zurich'],
            help="Select timezone for displaying trade times"
        )
        st.session_state.display_timezone = display_timezone
        
        # Global tolerances info
        with st.expander("📏 Global Tolerances"):
            st.markdown("""
            **System Tolerances:**
            - Time: ±1 second
            - Price: ±0.00001
            - Lot size: ±0.0001
            - Overlap threshold: ≥1 second
            
            These tolerances are applied across all rule validations.
            """)
        
        st.markdown("---")
        
        # Display account configuration
        st.subheader("📋 Account Configuration")
        st.write(f"**Leverage:** 1:{account_config['leverage']}")
        st.write(f"**Contract Size:** {account_config['contract_size'].title()}")
        st.write(f"**Min Trading Days:** {account_config['min_trading_days']}")
        
        st.markdown("---")
        
        # Help section
        with st.expander("❓ Help & Information"):
            st.markdown("""
            **How to use:**
            1. Select your account type and size
            2. Upload your trading CSV file(s)
            3. Click 'Analyze Trades' to run validation
            4. Review results and export if needed
            
            **Required CSV columns:**
            - Open Time, Close Time
            - Position ID, Side, Instrument
            - Lots, Open Price, Close Price
            """)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📁 Upload & Validate", "📊 Results", "📥 Export"])
    
    with tab1:
        st.header("📁 Upload Trading Data")
        
        st.markdown("""
        <div class="info-box">
        Upload one or more CSV files containing your trading history. 
        Each file should represent a trading phase (e.g., Phase 1, Phase 2, Funded Phase).
        </div>
        """, unsafe_allow_html=True)
        
        # Sample data button
        col_upload, col_sample = st.columns([3, 1])
        with col_sample:
            if st.button("📂 Load Sample Data", help="Load example CSV file for demo"):
                # Check if sample file exists
                sample_file = "Trades121.csv"
                if os.path.exists(sample_file):
                    try:
                        with open(sample_file, 'rb') as f:
                            file_content = f.read()
                        
                        # Create a BytesIO object to mimic uploaded file
                        from io import BytesIO
                        sample_buffer = BytesIO(file_content)
                        sample_buffer.name = sample_file
                        
                        file_key = "sample_0"
                        with st.spinner(f"Loading sample data..."):
                            # Simulate upload validation
                            temp_path = f"temp_{file_key}_{sample_file}"
                            with open(temp_path, 'wb') as f:
                                f.write(file_content)
                            
                            df = load_csv(temp_path)
                            is_valid, quality_errors = validate_csv_quality(df, min_valid_percent=95.0)
                            
                            if is_valid:
                                st.session_state.uploaded_files[file_key] = {
                                    'dataframe': df,
                                    'temp_path': temp_path,
                                    'original_name': sample_file,
                                    'trades_count': len(df),
                                    'date_range': f"{df['Open Time'].min().strftime('%Y-%m-%d')} to {df['Close Time'].max().strftime('%Y-%m-%d')}"
                                }
                                log_message(None, sample_file, "Sample data loaded successfully", "INFO")
                                st.success("✅ Sample data loaded!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error loading sample data: {str(e)}")
                else:
                    st.warning("Sample file not found. Please upload your own CSV files.")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose CSV file(s)",
            type=['csv'],
            accept_multiple_files=True,
            help="Upload your trading history CSV files"
        )
        
        if uploaded_files:
            st.subheader("📋 Uploaded Files")
            
            for idx, uploaded_file in enumerate(uploaded_files):
                file_key = f"file_{idx}"
                
                with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                    if file_key not in st.session_state.uploaded_files:
                        with st.spinner(f"Validating {uploaded_file.name}..."):
                            is_valid, df, errors = validate_uploaded_csv(uploaded_file, file_key)
                            
                            if is_valid:
                                st.success(f"✅ File validated successfully!")
                                file_info = st.session_state.uploaded_files[file_key]
                                
                                col1, col2 = st.columns(2)
                                col1.metric("Total Trades", file_info['trades_count'])
                                col2.metric("Date Range", file_info['date_range'])
                                
                                # Show preview
                                st.markdown("**Data Preview:**")
                                st.dataframe(df.head(10), use_container_width=True)
                                
                            else:
                                st.error("❌ Validation failed!")
                                for error in errors:
                                    st.error(f"• {error}")
                    else:
                        file_info = st.session_state.uploaded_files[file_key]
                        st.success(f"✅ File already validated")
                        
                        col1, col2 = st.columns(2)
                        col1.metric("Total Trades", file_info['trades_count'])
                        col2.metric("Date Range", file_info['date_range'])
                        
                        # Phase assignment
                        st.markdown("**Assign Phase:**")
                        phase_label = st.selectbox(
                            "Select phase for this file",
                            options=["Phase 1", "Phase 2", "Funded Phase", "Direct Funding", "Unassigned"],
                            key=f"phase_{file_key}",
                            index=4 if file_key not in st.session_state.phase_mapping else 
                                  ["Phase 1", "Phase 2", "Funded Phase", "Direct Funding", "Unassigned"].index(st.session_state.phase_mapping.get(file_key, "Unassigned"))
                        )
                        
                        if phase_label != "Unassigned":
                            st.session_state.phase_mapping[file_key] = phase_label
                            st.info(f"📍 This file is assigned to: **{phase_label}**")
                        elif file_key in st.session_state.phase_mapping:
                            del st.session_state.phase_mapping[file_key]
            
            st.markdown("---")
            
            # Analyze button
            if st.button("🚀 Analyze Trades", type="primary", use_container_width=True):
                with st.spinner("Running rule validation..."):
                    results = run_all_rules(account_type, equity, addon_enabled)
                    st.session_state.rule_results = results
                    st.session_state.analysis_complete = True
                    st.success("✅ Analysis complete! Check the 'Results' tab.")
                    st.balloons()
    
    with tab2:
        st.header("📊 Validation Results")
        
        if st.session_state.analysis_complete and st.session_state.rule_results:
            results = st.session_state.rule_results
            
            # Display results table
            display_results_table(results)
            
            st.markdown("---")
            
            # Display violation details
            display_violation_details(results)
            
            # Display logs
            if st.session_state.session_logs:
                st.markdown("---")
                with st.expander("📋 Session Logs", expanded=False):
                    logs_df = pd.DataFrame(st.session_state.session_logs)
                    st.dataframe(logs_df, use_container_width=True, hide_index=True)
                    
                    # Download logs button
                    logs_csv = logs_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download Logs (CSV)",
                        data=logs_csv,
                        file_name=f"session_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
        else:
            st.info("👈 Upload files and click 'Analyze Trades' to see results here.")
    
    with tab3:
        st.header("📥 Export Results")
        
        if st.session_state.analysis_complete and st.session_state.rule_results:
            results = st.session_state.rule_results
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📄 CSV Export")
                csv_data = export_results_csv(results)
                st.download_button(
                    label="⬇️ Download CSV Report",
                    data=csv_data,
                    file_name=f"rule_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                st.subheader("📑 PDF Export")
                if st.button("📄 Generate PDF Report", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        pdf_data = export_results_pdf(results, account_type, equity)
                        if pdf_data:
                            st.download_button(
                                label="⬇️ Download PDF Report",
                                data=pdf_data,
                                file_name=f"rule_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
        else:
            st.info("👈 Run analysis first to enable export options.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        Trading Rule Validation Dashboard v1.0 | Built with Streamlit
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
