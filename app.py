"""
Trading Rule Validation Dashboard
Streamlit-based web application for validating trading data against firm rules
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from io import BytesIO
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add rules directory to path
sys.path.append(str(Path(__file__).parent / "rules"))

# Import configuration and utilities
from rules import config
import dashboard_utils as utils
import rule_executor

# Page configuration
st.set_page_config(
    page_title="Trading Rule Validator",
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
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'validated_data' not in st.session_state:
    st.session_state.validated_data = {}
if 'rule_results' not in st.session_state:
    st.session_state.rule_results = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

def main():
    """Main application function"""
    
    # Header
    st.markdown('<div class="main-header">📊 Trading Rule Validation Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Validate your trading data against firm compliance rules</div>', unsafe_allow_html=True)
    
    # Sidebar
    create_sidebar()
    
    # Main content area
    if st.session_state.get('account_type') and st.session_state.get('account_size'):
        show_configuration_info()
        
        if st.session_state.uploaded_files:
            show_uploaded_files()
            
            if st.button("🚀 Run Validation", type="primary", use_container_width=True):
                run_validation()
            
            if st.session_state.analysis_complete and st.session_state.rule_results:
                show_results()
    else:
        show_welcome_message()

def create_sidebar():
    """Create sidebar with user inputs"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Account Type Selection
        st.subheader("1️⃣ Account Type")
        account_types = list(config.ACCOUNT_TYPES.keys())
        account_type = st.selectbox(
            "Select your account type:",
            account_types,
            key='account_type',
            help="Choose the type of account being validated"
        )
        
        # Account Size Selection
        st.subheader("2️⃣ Account Size")
        account_size = st.selectbox(
            "Select account equity:",
            config.ACCOUNT_SIZES,
            format_func=lambda x: f"${x:,}",
            key='account_size',
            help="Select your account equity amount"
        )
        
        # Add-on Selection
        st.subheader("3️⃣ Add-ons")
        config_data = config.ACCOUNT_TYPES[account_type]
        news_addon_allowed = config_data['news_addon_allowed']
        weekend_addon_allowed = config_data['weekend_addon_allowed']
        
        if news_addon_allowed or weekend_addon_allowed:
            if news_addon_allowed:
                news_addon_enabled = st.checkbox(
                    "Enable News Trading Add-on",
                    key='news_addon_enabled',
                    help="When enabled, Rule 18 (News Trading Restriction) is skipped"
                )
            else:
                st.session_state.news_addon_enabled = False
            
            if weekend_addon_allowed:
                weekend_addon_enabled = st.checkbox(
                    "Enable Weekend Holding Add-on",
                    key='weekend_addon_enabled',
                    help="When enabled, Rule 19 (Weekend Trading and Holding) is skipped"
                )
            else:
                st.session_state.weekend_addon_enabled = False
        else:
            st.info("ℹ️ Add-ons not available for this account type")
            st.session_state.news_addon_enabled = False
            st.session_state.weekend_addon_enabled = False
        
        st.divider()
        
        # File Upload
        st.subheader("4️⃣ Upload Trading Data")
        uploaded_files = st.file_uploader(
            "Upload CSV file(s):",
            type=['csv'],
            accept_multiple_files=True,
            help="Upload one or more CSV files with your trading history"
        )
        
        if uploaded_files:
            st.session_state.uploaded_files = {}
            for file in uploaded_files:
                # Let user assign phase to each file
                phase = st.selectbox(
                    f"Phase for {file.name}:",
                    ["Single Phase", "Phase 1", "Phase 2", "Funded Phase"],
                    key=f"phase_{file.name}"
                )
                st.session_state.uploaded_files[file.name] = {
                    'file': file,
                    'phase': phase
                }
        
        st.divider()
        
        # Info section
        with st.expander("ℹ️ Help & Information"):
            st.markdown("""
            **CSV Requirements:**
            - Required columns: Open Time, Close Time, Position ID, Side, Instrument, Lots, Open Price, Close Price
            - Optional: Stop Loss, Take Profit, PnL, etc.
            - At least 95% of rows must be valid
            
            **Account Types:**
            - **2-Step Phase 1/2**: 1:100 leverage, add-ons available
            - **Funded Phase**: 1:50 leverage, add-ons available
            - **Direct Funding**: 1:30 leverage, add-ons available
            
            **Rules Tested:**
            - Rule 1: Hedging Ban
            - Rule 3: Strategy Consistency
            - Rule 4: Prohibited EAs
            - Rule 12: All-or-Nothing Trading
            - Rule 13: Maximum Margin Usage
            - Rule 14: Gambling Definition
            - Rule 15: One-Sided Bets
            - Rule 16: Abuse of Simulated Environment
            - Rule 17: Max 2% Risk per Trade Idea
            - Rule 18: News Trading Restriction
            - Rule 19: Weekend Trading
            - Rule 23: Minimum Trading Days
            """)

def show_configuration_info():
    """Display current configuration"""
    account_type = st.session_state.get('account_type')
    account_size = st.session_state.get('account_size')
    news_addon_enabled = st.session_state.get('news_addon_enabled', False)
    weekend_addon_enabled = st.session_state.get('weekend_addon_enabled', False)
    
    if account_type and account_size:
        config_data = config.ACCOUNT_TYPES[account_type]
        
        with st.expander("📋 Current Configuration", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Account Type", account_type)
            with col2:
                st.metric("Account Size", f"${account_size:,}")
            with col3:
                st.metric("Leverage", f"1:{config_data['leverage']}")
            with col4:
                news_status = "✅" if news_addon_enabled else "❌"
                weekend_status = "✅" if weekend_addon_enabled else "❌"
                st.metric("Add-ons", f"News: {news_status} | Weekend: {weekend_status}")
            
            st.info(f"ℹ️ Minimum Trading Days Required: {config_data['min_trading_days']}")
            
            # Show which rules will be active/skipped
            st.markdown("**Active Rules:**")
            rules_status = []
            all_rules = [1, 3, 4, 12, 13, 14, 15, 16, 17, 18, 19, 23]
            
            for rule_num in all_rules:
                if news_addon_enabled and rule_num == 18:
                    rules_status.append(f"Rule {rule_num}: ⏭️ Skipped (News Trading Add-on enabled)")
                elif weekend_addon_enabled and rule_num == 19:
                    rules_status.append(f"Rule {rule_num}: ⏭️ Skipped (Weekend Holding Add-on enabled)")
                elif rule_num == 17 and account_type != "Direct Funding":
                    rules_status.append(f"Rule {rule_num}: ⏭️ Skipped (Direct Funding only)")
                else:
                    rules_status.append(f"Rule {rule_num}: ✅ Active")
            
            st.text("\n".join(rules_status))

def show_uploaded_files():
    """Display uploaded files information"""
    st.subheader("📁 Uploaded Files")
    
    files_info = []
    for filename, file_data in st.session_state.uploaded_files.items():
        files_info.append({
            'Filename': filename,
            'Phase': file_data['phase'],
            'Size': f"{file_data['file'].size / 1024:.2f} KB"
        })
    
    if files_info:
        df_files = pd.DataFrame(files_info)
        st.dataframe(df_files, use_container_width=True, hide_index=True)

def show_welcome_message():
    """Show welcome message when no configuration is set"""
    st.info("👈 Please configure your account settings in the sidebar to begin")
    
    st.markdown("""
    ### Welcome to the Trading Rule Validation Dashboard
    
    This application helps you validate your trading data against firm compliance rules.
    
    **Getting Started:**
    1. Select your account type from the sidebar
    2. Choose your account size
    3. Enable add-ons if applicable
    4. Upload your trading CSV file(s)
    5. Click "Run Validation" to analyze your trades
    
    **What You'll Get:**
    - Complete rule validation results
    - Detailed violation reports (if any)
    - Exportable CSV and PDF reports
    - Visual analytics of your trading patterns
    """)

def run_validation():
    """Run validation on uploaded files"""
    try:
        # Validate and load CSV files
        with st.spinner("📄 Validating CSV files..."):
            phases = {}
            all_valid = True
            
            for filename, file_data in st.session_state.uploaded_files.items():
                file_obj = file_data['file']
                phase = file_data['phase']
                
                # Reset file pointer
                file_obj.seek(0)
                
                # Read CSV
                df = pd.read_csv(file_obj)
                
                # Validate
                is_valid, df_clean, errors = utils.validate_csv_file(df, filename)
                
                if not is_valid:
                    st.error(f"❌ Validation failed for {filename}:")
                    for error in errors:
                        st.error(f"  • {error}")
                    all_valid = False
                else:
                    if errors:  # Show warnings
                        with st.expander(f"⚠️ Warnings for {filename}"):
                            for error in errors:
                                st.warning(error)
                    
                    # Store validated data
                    if phase in phases:
                        phases[phase] = pd.concat([phases[phase], df_clean], ignore_index=True)
                    else:
                        phases[phase] = df_clean
                    
                    st.success(f"✅ {filename} validated: {len(df_clean)} trades")
            
            if not all_valid:
                st.error("Please fix the validation errors and try again.")
                return
        
        # Store validated data in session state
        st.session_state.validated_data = phases
        
        # Debug: Show what data we have
        with st.expander("🔍 Debug: Validated Data Info"):
            st.write(f"Number of phases: {len(phases)}")
            for phase_name, phase_df in phases.items():
                st.write(f"Phase '{phase_name}': {len(phase_df)} trades")
                st.write(f"Columns: {list(phase_df.columns)}")
                st.dataframe(phase_df.head(2))
        
        # Get configuration
        account_type = st.session_state.get('account_type')
        account_size = st.session_state.get('account_size')
        news_addon_enabled = st.session_state.get('news_addon_enabled', False)
        weekend_addon_enabled = st.session_state.get('weekend_addon_enabled', False)
        
        # Determine active rules
        active_rules = utils.determine_active_rules(account_type, news_addon_enabled, weekend_addon_enabled)
        
        # Execute rules
        with st.spinner("🔍 Running rule validation..."):
            results = rule_executor.execute_all_rules(
                phases,
                account_type,
                account_size,
                news_addon_enabled,
                weekend_addon_enabled,
                active_rules
            )
        
        # Store results
        st.session_state.rule_results = results
        st.session_state.analysis_complete = True
        
        st.success("✅ Validation complete!")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Error during validation: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def show_results():
    """Display validation results"""
    results = st.session_state.rule_results
    
    if not results:
        st.warning("No results to display")
        return
    
    st.header("📊 Validation Results")
    
    # Calculate overall status
    overall_status, counts = utils.calculate_overall_status(results)
    
    # Display summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_trades = sum(len(df) for df in st.session_state.validated_data.values())
        st.metric("Total Trades", total_trades)
    
    with col2:
        st.metric("Rules Tested", counts['total'])
    
    with col3:
        st.metric("✅ Passed", counts['passed'])
    
    with col4:
        st.metric("❌ Violated", counts['violated'])
    
    with col5:
        st.metric("⚠️ Not Testable", counts['not_testable'])
    
    # Overall status
    if overall_status == "PASSED":
        st.success(f"### 🎉 Overall Status: {overall_status}")
    elif overall_status == "FAILED":
        st.error(f"### ❌ Overall Status: {overall_status}")
    else:
        st.warning(f"### ⚠️ Overall Status: {overall_status}")
    
    st.divider()
    
    # Results table
    show_results_table(results)
    
    # Violation details
    show_violation_details(results)
    
    # Text summary
    show_text_summary(results)
    
    # Export options
    show_export_options(results)


def show_results_table(results: List[Dict]):
    """Display results in a table"""
    st.subheader("📋 Rule Summary")
    
    rule_descriptions = utils.get_rule_descriptions()
    
    table_data = []
    for result in results:
        rule_num = result.get('rule_number')
        rule_info = rule_descriptions.get(rule_num, {})
        
        table_data.append({
            'Rule': f"Rule {rule_num}",
            'Name': result.get('rule_name', rule_info.get('name', 'Unknown')),
            'Status': result.get('status', 'Unknown'),
            'Description': rule_info.get('description', ''),
            'Affected Trades': result.get('violations_found', result.get('pattern_groups_found', 0))
        })
    
    df_results = pd.DataFrame(table_data)
    
    # Style the dataframe
    def highlight_status(val):
        if 'PASSED' in val:
            return 'background-color: #d4edda; color: #155724'
        elif 'VIOLATED' in val:
            return 'background-color: #f8d7da; color: #721c24'
        else:
            return 'background-color: #fff3cd; color: #856404'
    
    styled_df = df_results.style.applymap(highlight_status, subset=['Status'])
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def show_violation_details(results: List[Dict]):
    """Show detailed information for each violated rule"""
    violated_rules = [r for r in results if r.get('status') == config.STATUS_VIOLATED]
    
    if not violated_rules:
        st.success("✅ No violations detected!")
        return
    
    st.subheader("🔍 Violation Details")
    
    for result in violated_rules:
        rule_num = result.get('rule_number')
        rule_name = result.get('rule_name')
        
        with st.expander(f"❌ Rule {rule_num}: {rule_name}", expanded=True):
            st.markdown(f"**Status:** {result.get('status')}")
            
            # Show violation reason
            if 'violation_reason' in result:
                st.markdown("**Violation Reason:**")
                st.info(result['violation_reason'])
            
            # Show violations details
            if 'violations' in result and result['violations']:
                st.markdown(f"**Total Violations:** {len(result['violations'])}")
                
                # Create DataFrame of violations
                violations_df = pd.DataFrame(result['violations'])
                st.dataframe(violations_df, use_container_width=True)


def show_text_summary(results: List[Dict]):
    """Show plain text summary of violations"""
    st.subheader("📝 Violation Summary Text")
    
    summary_text = utils.create_violation_summary_text(results)
    st.text_area("Summary", summary_text, height=300)


def show_export_options(results: List[Dict]):
    """Show export buttons"""
    st.subheader("💾 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export to CSV", use_container_width=True):
            export_to_csv(results)
    
    with col2:
        if st.button("📄 Export to PDF", use_container_width=True):
            export_to_pdf(results)


def export_to_csv(results: List[Dict]):
    """Export results to CSV with detailed violation information (parity with PDF)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # --- 1) Match PDF status mapping
        def status_to_text(status: str) -> str:
            s = str(status or "")
            if "PASSED" in s or "✅" in s:
                return "[PASSED]"
            if "VIOLATED" in s or "❌" in s:
                return "[VIOLATED]"
            if "NOT TESTABLE" in s or "⚠" in s:
                return "[NOT TESTABLE]"
            return s

        # --- 2) Summary CSV (one row per rule)
        summary_rows = []
        for r in results:
            summary_rows.append({
                "Rule Number": r.get("rule_number"),
                "Rule Name": r.get("rule_name"),
                "Status": status_to_text(r.get("status", "")),
                "Message": r.get("message", ""),
                "Total Violations": len(r.get("violations", [])) if r.get("violations") else 0,
                "Violation Reason": r.get("violation_reason", ""),
            })
        df_summary = pd.DataFrame(summary_rows)
        df_summary = df_summary.fillna("")  # clean NaN

        # --- 3) Detailed violations CSV (one row per affected trade/violation)
        violations_rows = []
        for r in results:
            if status_to_text(r.get("status", "")) != "[VIOLATED]":
                continue

            rule_num = r.get("rule_number")
            rule_name = r.get("rule_name")
            violations_list = r.get("violations", []) or []

            for idx, v in enumerate(violations_list, 1):
                base = {
                    "Rule Number": rule_num,
                    "Rule Name": rule_name,
                    "Rule Status": "[VIOLATED]",
                    "Violation #": idx,
                }

                if isinstance(v, dict):
                    # normalize core fields first (for consistent order)
                    row = {
                        **base,
                        "Position ID": v.get("Position ID") or v.get("Position_ID", ""),
                        "Instrument": v.get("Instrument", ""),
                        "Side": v.get("Side", ""),
                        "Lots": v.get("Lots", ""),
                        "Open Time": v.get("Open Time", ""),
                        "Close Time": v.get("Close Time", ""),
                        "Open Price": v.get("Open Price", ""),
                        "Close Price": v.get("Close Price", ""),
                        "Stop Loss": v.get("Stop Loss", ""),
                        "Take Profit": v.get("Take Profit", ""),
                        "PnL": v.get("PnL", ""),
                        "Violation Reason (row)": v.get("Violation_Reason") or v.get("violation_reason", ""),
                    }
                    # append any extra keys deterministically, coercing to string
                    extra_keys = [k for k in v.keys() if k not in row and k not in ("Position_ID",)]
                    for k in sorted(extra_keys):
                        row[k] = "" if v[k] is None else str(v[k])
                    violations_rows.append(row)
                else:
                    # string violation payload
                    violations_rows.append({
                        **base,
                        "Violation Details": "" if v is None else str(v),
                    })

        # Prepare downloads
        csv_summary = df_summary.to_csv(index=False)

        # Only create & offer the detailed CSV if there are any rows
        if violations_rows:
            # Ensure deterministic column order: base + common core fields first
            core_order = [
                "Rule Number", "Rule Name", "Rule Status", "Violation #",
                "Position ID", "Instrument", "Side", "Lots",
                "Open Time", "Close Time", "Open Price", "Close Price",
                "Stop Loss", "Take Profit", "PnL",
                "Violation Reason (row)", "Violation Details",
            ]
            df_viol = pd.DataFrame(violations_rows).fillna("")
            # Add any missing core columns
            for col in core_order:
                if col not in df_viol.columns:
                    df_viol[col] = ""
            # Put core first, extras after (sorted)
            extras = [c for c in df_viol.columns if c not in core_order]
            df_viol = df_viol[core_order + sorted(extras)]
            csv_violations = df_viol.to_csv(index=False)

            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📊 Download Summary CSV",
                    data=csv_summary,
                    file_name=f"rule_summary_{timestamp}.csv",
                    mime="text/csv",
                    help="Download rule summary with overall results"
                )
            with c2:
                st.download_button(
                    label="🔍 Download Detailed Violations CSV",
                    data=csv_violations,
                    file_name=f"violations_detailed_{timestamp}.csv",
                    mime="text/csv",
                    help="Download detailed violation information for each affected trade"
                )
            st.success(f"✅ CSV exports ready! Summary + {len(df_viol)} violation rows")
        else:
            st.download_button(
                label="📊 Download Summary CSV",
                data=csv_summary,
                file_name=f"rule_summary_{timestamp}.csv",
                mime="text/csv",
                help="Download rule summary with overall results"
            )
            st.success("✅ Summary CSV export ready! No violations to export.")

    except Exception as e:
        st.error(f"Error exporting to CSV: {str(e)}")


def export_to_pdf(results: List[Dict]):
    """Export results to PDF"""
    try:
        from fpdf import FPDF
        
        # Helper function to sanitize text for PDF (Latin-1 encoding)
        def sanitize_for_pdf(text: str) -> str:
            """Replace Unicode characters with ASCII-safe equivalents for PDF"""
            if not text:
                return ""
            
            # Replace common Unicode symbols with ASCII-safe versions
            replacements = {
                "≥": ">=",
                "≤": "<=",
                "×": "x",
                "–": "-",
                "—": "-",
                """: '"',
                """: '"',
                "'": "'",
                "'": "'",
                "•": "-",
                "→": "->",
                "←": "<-",
                "↔": "<->",
                "✔": "OK",
                "✅": "[PASSED]",
                "❌": "[VIOLATED]",
                "⚠": "[WARN]",
                "⚠️": "[WARN]",
                "⏭": "[SKIP]",
                "⏭️": "[SKIP]",
                "℃": "C",
                "°": " deg",
                "±": "+/-",
            }
            
            for k, v in replacements.items():
                text = text.replace(k, v)
            
            # Strip remaining non-Latin-1 characters
            try:
                return text.encode("latin-1", "ignore").decode("latin-1")
            except:
                return text
        
        # Safe multi_cell helper to prevent horizontal space errors
        def safe_multicell(pdf, text: str, line_height: float = 4.0):
            """Safely write multi-line text with proper width and position handling"""
            # Ensure text is a string
            text = "" if text is None else str(text)
            
            # Sanitize text
            text = sanitize_for_pdf(text)
            
            # Insert spaces in very long unbreakable tokens so fpdf can wrap
            def break_long_tokens(s: str, maxlen: int = 60) -> str:
                out = []
                for tok in s.split(" "):
                    if len(tok) > maxlen:
                        out.extend(tok[i:i+maxlen] for i in range(0, len(tok), maxlen))
                    else:
                        out.append(tok)
                return " ".join(out)
            
            text = break_long_tokens(text)
            
            # Reset X and give multi_cell an explicit width
            content_width = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, line_height, text)
        
        # Helper function to convert emoji status to text
        def status_to_text(status: str) -> str:
            """Convert emoji status to PDF-friendly text"""
            if "PASSED" in status or "✅" in status:
                return "[PASSED]"
            elif "VIOLATED" in status or "❌" in status:
                return "[VIOLATED]"
            elif "NOT TESTABLE" in status or "⚠" in status:
                return "[NOT TESTABLE]"
            return sanitize_for_pdf(status.replace("✅", "[PASSED]").replace("❌", "[VIOLATED]").replace("⚠️", "[NOT TESTABLE]"))
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        
        # Title
        account_type = st.session_state.get('account_type', 'Unknown')
        account_size = st.session_state.get('account_size', 0)
        pdf.cell(0, 10, 'Trading Rule Validation Report', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Account: {account_type} - ${account_size:,}', 0, 1, 'C')
        pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        pdf.ln(10)
        
        # Summary
        overall_status, counts = utils.calculate_overall_status(results)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'Overall Status: {status_to_text(overall_status)}', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 8, f'Total Rules Tested: {counts["total"]}', 0, 1)
        pdf.cell(0, 8, f'Passed: {counts["passed"]} | Violated: {counts["violated"]} | Not Testable: {counts["not_testable"]}', 0, 1)
        pdf.ln(10)
        
        # Rule results
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Rule Results', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        for result in results:
            rule_num = result.get('rule_number')
            rule_name = sanitize_for_pdf(result.get('rule_name', f'Rule {rule_num}'))
            status = status_to_text(result.get('status', ''))
            message = sanitize_for_pdf(result.get('message', ''))
            
            # Rule header
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, f'Rule {rule_num}: {rule_name} - {status}', 0, 1)
            
            # Rule message/description
            if message:
                pdf.set_font('Arial', '', 9)
                # Handle long messages - split into multiple lines if needed
                message_clean = message.replace('\n', ' ')[:200]  # Limit length
                safe_multicell(pdf, f'  {message_clean}', line_height=6)
            
            pdf.ln(2)
        
        # Add violations summary if any
        violations = [r for r in results if "VIOLATED" in r.get('status', '')]
        if violations:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'VIOLATION DETAILS', 0, 1, 'C')
            pdf.ln(5)
            
            for result in violations:
                rule_num = result.get('rule_number')
                rule_name = sanitize_for_pdf(result.get('rule_name', f'Rule {rule_num}'))
                
                # Rule header with box
                pdf.set_fill_color(255, 230, 230)  # Light red background
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 8, f'Rule {rule_num}: {rule_name} - [VIOLATED]', 0, 1, 'L', True)
                pdf.ln(2)
                
                # Violation reason
                if 'violation_reason' in result:
                    # Check if we need a new page
                    if pdf.get_y() > 250:
                        pdf.add_page()
                    
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, 'Violation Reason:', 0, 1)
                    pdf.set_font('Arial', '', 9)
                    reason_text = result['violation_reason'].replace('\n', ' ')[:300]
                    safe_multicell(pdf, reason_text, line_height=5)
                    pdf.ln(2)
                
                # Violation details/trades
                violations_list = result.get('violations', [])
                if violations_list:
                    # Check if we need a new page
                    if pdf.get_y() > 240:
                        pdf.add_page()
                    
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, f'Total Violations: {len(violations_list)}', 0, 1)
                    pdf.ln(2)
                    
                    # Show detailed violations
                    pdf.set_font('Arial', 'B', 9)
                    pdf.cell(0, 5, 'Affected Trades:', 0, 1)
                    pdf.set_font('Arial', '', 8)
                    
                    # Display first 20 violations
                    for idx, violation in enumerate(violations_list[:20], 1):
                        # Check if we need a new page before each violation
                        if pdf.get_y() > 270:
                            pdf.add_page()
                            pdf.set_font('Arial', '', 8)  # Reset font after page break
                        
                        if isinstance(violation, dict):
                            # Build violation entry text
                            violation_text = f"{idx}. "
                            
                            # Add Position ID if available
                            if 'Position ID' in violation:
                                violation_text += f"Position {sanitize_for_pdf(str(violation['Position ID']))} - "
                            elif 'Position_ID' in violation:
                                violation_text += f"Position {sanitize_for_pdf(str(violation['Position_ID']))} - "
                            
                            # Add Instrument if available
                            if 'Instrument' in violation:
                                violation_text += f"{sanitize_for_pdf(str(violation['Instrument']))} "
                            
                            # Add Side if available
                            if 'Side' in violation:
                                violation_text += f"({sanitize_for_pdf(str(violation['Side']))}) "
                            
                            # Add Open/Close times if available
                            if 'Open Time' in violation:
                                violation_text += f"Open: {sanitize_for_pdf(str(violation['Open Time']))} "
                            if 'Close Time' in violation:
                                violation_text += f"Close: {sanitize_for_pdf(str(violation['Close Time']))} "
                            
                            # Add violation reason if available
                            if 'Violation_Reason' in violation:
                                violation_text += f"| {sanitize_for_pdf(str(violation['Violation_Reason']))}"
                            elif 'violation_reason' in violation:
                                violation_text += f"| {sanitize_for_pdf(str(violation['violation_reason']))}"
                            
                            # Truncate if too long
                            if len(violation_text) > 180:
                                violation_text = violation_text[:177] + "..."
                            
                            # Use safe_multicell instead of multi_cell
                            safe_multicell(pdf, violation_text, line_height=4)
                        else:
                            # Handle string violations
                            violation_text = str(violation)[:180]
                            safe_multicell(pdf, f"{idx}. {violation_text}", line_height=4)
                    
                    if len(violations_list) > 20:
                        if pdf.get_y() > 270:
                            pdf.add_page()
                        pdf.set_font('Arial', 'I', 9)
                        pdf.cell(0, 5, f'... and {len(violations_list) - 20} more violations', 0, 1)
                
                pdf.ln(5)
                
                # Add page break if needed
                if pdf.get_y() > 250:
                    pdf.add_page()
        
        # Generate PDF bytes safely for Streamlit
        out = pdf.output(dest='S')  # can be str, bytes, or bytearray depending on fpdf version
        if isinstance(out, (bytes, bytearray)):
            pdf_bytes = bytes(out)           # normalize bytearray -> bytes
        else:
            pdf_bytes = out.encode('latin-1')  # fpdf/pyfpdf returns str -> encode to bytes
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"rule_report_{timestamp}.pdf",
            mime="application/pdf"
        )
        
        st.success("✅ PDF export ready!")
        
    except Exception as e:
        st.error(f"Error exporting to PDF: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main()
