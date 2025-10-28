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
        addon_allowed = config.ACCOUNT_TYPES[account_type]['addon_allowed']
        
        if addon_allowed:
            addon_enabled = st.checkbox(
                "Enable News Trading & Weekend Holding Add-on",
                key='addon_enabled',
                help="When enabled, Rules 18 (News Trading) and 19 (Weekend Holding) are skipped"
            )
        else:
            st.info("ℹ️ Add-on not available for this account type")
            st.session_state.addon_enabled = False
        
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
            - **2-Step Phase 1/2**: 1:100 leverage, no add-on
            - **Funded Phase**: 1:50 leverage, add-on optional
            - **Direct Funding**: 1:30 leverage, add-on optional
            
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
    addon_enabled = st.session_state.get('addon_enabled', False)
    
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
                st.metric("Add-on Status", "Enabled" if addon_enabled else "Disabled")
            
            st.info(f"ℹ️ Minimum Trading Days Required: {config_data['min_trading_days']}")
            
            # Show which rules will be active/skipped
            st.markdown("**Active Rules:**")
            rules_status = []
            all_rules = [1, 3, 4, 12, 13, 14, 15, 16, 17, 18, 19, 23]
            
            for rule_num in all_rules:
                if addon_enabled and rule_num in [18, 19]:
                    rules_status.append(f"Rule {rule_num}: ⏭️ Skipped (Add-on enabled)")
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
        addon_enabled = st.session_state.get('addon_enabled', False)
        
        # Determine active rules
        active_rules = utils.determine_active_rules(account_type, addon_enabled)
        
        # Execute rules
        with st.spinner("🔍 Running rule validation..."):
            results = rule_executor.execute_all_rules(
                phases,
                account_type,
                account_size,
                addon_enabled,
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
    """Export results to CSV"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create summary DataFrame
        summary_data = []
        for result in results:
            summary_data.append({
                'Rule Number': result.get('rule_number'),
                'Rule Name': result.get('rule_name'),
                'Status': result.get('status'),
                'Message': result.get('message', ''),
                'Violations Found': result.get('violations_found', result.get('pattern_groups_found', 0))
            })
        
        df_summary = pd.DataFrame(summary_data)
        
        # Convert to CSV
        csv = df_summary.to_csv(index=False)
        
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"rule_results_{timestamp}.csv",
            mime="text/csv"
        )
        
        st.success("✅ CSV export ready!")
        
    except Exception as e:
        st.error(f"Error exporting to CSV: {str(e)}")


def export_to_pdf(results: List[Dict]):
    """Export results to PDF"""
    try:
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        
        # Title
        account_type = st.session_state.get('account_type', 'Unknown')
        account_size = st.session_state.get('account_size', 0)
        pdf.cell(0, 10, f'Trading Rule Validation Report', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Account: {account_type} - ${account_size:,}', 0, 1, 'C')
        pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        pdf.ln(10)
        
        # Summary
        overall_status, counts = utils.calculate_overall_status(results)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'Overall Status: {overall_status}', 0, 1)
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
            rule_name = result.get('rule_name')
            status = result.get('status')
            
            pdf.cell(0, 8, f'Rule {rule_num}: {rule_name} - {status}', 0, 1)
        
        # Generate PDF
        pdf_output = pdf.output(dest='S').encode('latin-1')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="Download PDF",
            data=pdf_output,
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
