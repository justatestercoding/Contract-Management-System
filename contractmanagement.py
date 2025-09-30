import streamlit as st
import pandas as pd
import numpy as np
import base64
import os
import pytz
import ast
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Union, Tuple
import dateutil.parser as du_parser
from dateutil.relativedelta import relativedelta
from plotly.subplots import make_subplots
from decimal import Decimal, getcontext
from math import ceil


# Page configuration
st.set_page_config(
    page_title="Contract Management",
    page_icon="cms.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Conversion of image to base64
def get_base64_of_bin_file(bin_file):
    try:
        if os.path.exists(bin_file):
            with open(bin_file, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()
        else:
            st.warning(f"Image file {bin_file} not found. Using placeholder.")
            return ""
    except Exception as e:
        st.warning(f"Error loading image {bin_file}: {str(e)}")
        return ""

# Get current time in IST
def get_current_time():
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    return (current_time.strftime("%A, %B %d, %Y<br>%I:%M %p IST"))

# Indian number format functions
def format_indian_currency(num):
    # for defining lakhs, crores
    if pd.isna(num) or num == 0:
        return "₹ 0"

    is_negative = num < 0
    num = abs(num)

    s = f"{num:.4f}"
    integer_part, decimal_part = s.split('.')
    decimal_part = decimal_part.rstrip('0').rstrip('.')
    if len(integer_part) <= 3:
        formatted_integer = integer_part
    else:
        # Last 3 digits
        last_three = integer_part[-3:]
        other_digits = integer_part[:-3]

        # Add commas every 2 digits for the remaining part
        formatted_other = ""
        for i in range(len(other_digits) - 1, -1, -1):
            if (len(other_digits) - i) % 2 == 1 and len(other_digits) - i > 1:
                formatted_other = "," + formatted_other
            formatted_other = other_digits[i] + formatted_other

        formatted_integer = formatted_other + "," + last_three

    result = formatted_integer
    if decimal_part and decimal_part != "00":
        result += "." + decimal_part

    result = "₹ " + result
    if is_negative:
        result = "-" + result

    return result

def format_indian_number(num):
    if pd.isna(num) or num == 0:
        return "0"

    is_negative = num < 0
    num = abs(num)
    s = str(int(num))

    if len(s) <= 3:
        formatted = s
    else:
        # Last 3 digits
        last_three = s[-3:]
        other_digits = s[:-3]

        # Add commas every 2 digits for the remaining part
        formatted_other = ""
        for i in range(len(other_digits) - 1, -1, -1):
            if (len(other_digits) - i) % 2 == 1 and len(other_digits) - i > 1:
                formatted_other = "," + formatted_other
            formatted_other = other_digits[i] + formatted_other

        formatted = formatted_other + "," + last_three
    if is_negative:
        formatted = "-" + formatted


    return formatted

def amount_in_lakhs_crores(amount):
    if pd.isna(amount) or amount == 0:
        return ""

    abs_amount = abs(amount)
    if abs_amount >= 10000000:  # 1 crore
        val = amount / 10000000
        return f"{val:.2f} Crores"
    elif abs_amount >= 100000:  # 1 lakh
        val = amount / 100000
        return f"{val:.2f} Lakhs"
    else:
        return ""

def format_date_indian(date_obj):
    if pd.isna(date_obj):
        return ""
    if isinstance(date_obj, str):
        try:
            date_obj = pd.to_datetime(date_obj)
        except:
            return date_obj
    return date_obj.strftime("%d/%m/%Y")

# PERCENTAGE-BASED CALCULATION FUNCTIONS
def format_percentage(percentage):
    if pd.isna(percentage):
        return "0.00%"
    return f"{percentage:.2f}%"

getcontext().prec = 50

# Date Parsing
def _parse_any_date_streamlit(x: "Union[date, datetime, str]", *, dayfirst=True, yearfirst=False) -> date:
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    if isinstance(x, datetime):
        return x.date()
    if not isinstance(x, str):
        raise TypeError("Expected date, datetime, or str")

    s = x.strip()

    # Hard-coded compact digits like 01042025 (DDMMYYYY), 20250401 (YYYYMMDD)
    if len(s) == 8 and s.isdigit():
        try:
            # Prefer DMY for India; if invalid, try YMD
            return datetime.strptime(s, "%d%m%Y").date()
        except ValueError:
            try:
                return datetime.strptime(s, "%Y%m%d").date()
            except ValueError:
                pass

    # Preferred DMY parse for India
    try:
        return du_parser.parse(s, dayfirst=dayfirst, yearfirst=yearfirst).date()
    except Exception:
        pass

    # ISO-first fallback (YYYY-MM-DD or similar)
    try:
        return du_parser.parse(s, yearfirst=True, dayfirst=False).date()
    except Exception:
        pass

    # US MDY fallback
    try:
        return du_parser.parse(s, dayfirst=False, yearfirst=False).date()
    except Exception:
        pass

    # Final explicit formats sweep for stubborn inputs
    fmts = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        "%d %b %Y", "%d %B %Y",
        "%b %d, %Y", "%B %d, %Y",
        "%d-%m-%y", "%d/%m/%y", "%y-%m-%d",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue

    # Last resort: let dateutil guess with defaults
    try:
        return du_parser.parse(s).date()
    except Exception as e:
        raise ValueError(f"Unrecognized date format: {x}") from e


def get_fy_from_date(input_date):
    if input_date is None:
        return
    
    try:
        if isinstance(input_date, str):
            # Try to parse string date in various formats
            try:
                date_obj = datetime.strptime(input_date.strip(), "%d/%m/%Y").date()
            except ValueError:
                try:
                    date_obj = datetime.strptime(input_date.strip(), "%d-%m-%Y").date()
                except ValueError:
                    try:
                        date_obj = du_parser.parse(input_date).date()
                    except:
                        return
        elif isinstance(input_date, datetime):
            date_obj = input_date.date()
        elif isinstance(input_date, date):
            date_obj = input_date
        else:
            return
        
        if date_obj.month >= 4:  # April onwards
            return f"FY{date_obj.year}-{date_obj.year + 1}"
        else:  # January to March
            return f"FY{date_obj.year - 1}-{date_obj.year}"
            
    except Exception:
        return

def add_financial_year_columns(df):
    if df.empty:
        return df
    
    df_copy = df.copy()
    
    # Check for Contract Date column and add "FY Contract"
    if 'Contract Date' in df_copy.columns:
        df_copy['FY Contract'] = df_copy['Contract Date'].apply(get_fy_from_date)
    
    # Check for Date of Invoice column and add "Invoice FY"
    if 'Date of Invoice' in df_copy.columns:
        df_copy['Invoice FY'] = df_copy['Date of Invoice'].apply(get_fy_from_date)
    
    # Check for Release Order Date column and add "RO FY"
    if 'Release Order Date' in df_copy.columns:
        df_copy['RO FY'] = df_copy['Release Order Date'].apply(get_fy_from_date)
    
    return df_copy


def generate_warranty_milestones(period, duration_months, percentage, amount):
    period_to_n = {"Monthly": 12, "Quarterly": 4, "Half Yearly": 2, "Annually": 1}
    periods_per_year = period_to_n.get(period, 1)
    total_years = duration_months / 12
    total_periods = int(periods_per_year * total_years)
                        
    if total_periods <= 0:
        return []
                        
    amount_per_period = amount / total_periods
    percentage_per_period = percentage / total_periods
                        
    milestones = []
    
    if period == "Monthly":
        for month in range(1, total_periods + 1):
            year = ((month - 1) // 12) + 1
            month_in_year = ((month - 1) % 12) + 1
            label = f"Warranty Month {month} (Year {year}, M{month_in_year}) ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
                                
    elif period == "Quarterly":
        for quarter in range(1, total_periods + 1):
            year = ((quarter - 1) // 4) + 1
            q_in_year = ((quarter - 1) % 4) + 1
            label = f"Warranty Q{q_in_year} Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
                                
    elif period == "Half Yearly":
        for half in range(1, total_periods + 1):
            year = ((half - 1) // 2) + 1
            h_in_year = ((half - 1) % 2) + 1
            label = f"Warranty H{h_in_year} Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
                                
    else:  # Annually
        for year in range(1, total_periods + 1):
            label = f"Warranty Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))

    return milestones


def generate_amc_milestones(period, duration_months, percentage, total_amount):
    period_to_n = {"Monthly": 12, "Quarterly": 4, "Half Yearly": 2, "Annually": 1}
    periods_per_year = period_to_n.get(period, 1)
    total_years = duration_months / 12
    total_periods = int(periods_per_year * total_years)

    if total_periods <= 0:
        return []
                        
    amount_per_period = total_amount / total_periods
    percentage_per_period = percentage / total_periods
    milestones = []
    
    if period == "Monthly":
        for month in range(1, total_periods + 1):
            year = ((month - 1) // 12) + 1
            month_in_year = ((month - 1) % 12) + 1
            label = f"AMC Month {month} (Year {year}, M{month_in_year}) ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
        
    elif period == "Quarterly":
        for quarter in range(1, total_periods + 1):
            year = ((quarter - 1) // 4) + 1
            q_in_year = ((quarter - 1) % 4) + 1
            label = f"AMC Q{q_in_year} Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
        
    elif period == "Half Yearly":
        for half in range(1, total_periods + 1):
            year = ((half - 1) // 2) + 1
            h_in_year = ((half - 1) % 2) + 1
            label = f"AMC H{h_in_year} Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
        
    else:  # Annually
        for year in range(1, total_periods + 1):
            label = f"AMC Year {year} ({percentage_per_period:.2f}%)"
            milestones.append((label, amount_per_period))
                        
    return milestones


def calculate_days(ro_date_str, receive_date_str):
    if not ro_date_str or not receive_date_str:
        return None
    try:
        ro_date = datetime.strptime(ro_date_str, "%d/%m/%Y")
        receive_date = datetime.strptime(receive_date_str, "%d/%m/%Y")
        delta = (ro_date - receive_date).days
        return delta if delta >= 0 else None
    except:
        return None
    
def style_alternate_rows(df):
    def style_with_conditions(row):
        # Base alternating colors
        if row.name % 2 == 0:
            base_style = 'background-color: #ffffff; color: #374151; text-align: left;'
        else:
            base_style = 'background-color: #f3f4f6; color: #374151; text-align: left;'
        
        # Apply base style to all columns
        styles = [base_style] * len(row)
        
        # Check for days-related columns and apply conditional coloring
        for col_idx, col_name in enumerate(df.columns):
            # Look for columns that might contain day values
            if any(keyword in col_name.lower() for keyword in ['days', 'daysbetween', 'overdue']):
                try:
                    days_value = row.iloc[col_idx]
                    if pd.notna(days_value) and isinstance(days_value, (int, float)):
                        if days_value > 30:
                            # Red background for > 30 days
                            styles[col_idx] = 'background-color: #fee2e2; color: #dc2626; text-align: left; font-weight: bold;'
                        elif days_value > 20:
                            # Yellow background for > 20 days
                            styles[col_idx] = 'background-color: #fef3c7; color: #d97706; text-align: left; font-weight: bold;'
                        # else keep base style for <= 20 days
                except (ValueError, TypeError):
                    # If conversion fails, keep base style
                    pass
        
        return styles
    
    return df.style.apply(style_with_conditions, axis=1)


# CSS styling
st.markdown("""
<style>
    /* HIDE ALL Streamlit elements */
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    [data-testid="stToolbar"] {
        visibility: hidden !important;
        height: 0% !important;
        position: fixed !important;
    }
    
    [data-testid="stStatusWidget"] {
        visibility: hidden !important;
        height: 0% !important;
        position: fixed !important;
    }
    
    header {
        visibility: hidden !important;
        height: 0% !important;
    }
    
    footer {
        visibility: hidden !important;
        height: 0% !important;
    }
    
    #MainMenu {
        visibility: hidden !important;
        height: 0% !important;
    }
    
    .stDeployButton {
        display: none !important;
    }
    
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* Remove top padding completely */
    .main > div {
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: none !important;
    }
    
    /* Advanced padding removal */
    #root > div:nth-child(1) > div > div > div > div > section > div {
        padding-top: 0rem !important;
    }
    
    section.main > div {
        padding-top: 0px !important;
    }
    
    .stApp {
        margin-top: 0px !important;
        padding-top: 0px !important;
    }
            
    /* Global font family */
    * {
        font-family: 'Open Sans', sans-serif !important;
    }
    
    /* first header: UIDAI Officials */
    .uidai-official-header {
        background: white;
        color: #1e3a8a;
        padding: 1rem 2rem;
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-bottom: 1px solid #e2e8f0;
    }
    
    .uidai-left-section {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .aadhaar-logo-img {
        height:35px;
        width: auto;
    }
    .uidai-logo-img {
        height: 40px;
        width: auto;
    }
    .uidai-header {
        background: linear-gradient(to right, #061A5C, #1AAAD6);
        color: white;
        padding: 1rem 2rem;
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    
    .uidai-logo-section {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .uidai-title {
        margin: 0;
        text-align: center;
        flex-grow: 1;
    }
    
    .uidai-title h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    
    .header-time {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.9);
        font-weight: 400;
        text-align: right;
        min-width: 250px;
    }
    
    /* Tab styling*/
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #006a9c;
        padding: 0;
        margin: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 24px;
        background: #006a9c;
        border: none;
        border-radius: 0;
        color: white;
        font-weight: 600;
        font-size: 1.5rem;
        margin: 0;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255,255,255,0.1);
        color: white;
    }
    
    .stTabs [aria-selected="true"] {
        background: #14578c;
        color: white;
        border-bottom: 4px solid #fbbf24;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding: 2rem;
        background: #f8fafc;
        min-height: auto;
    }
    
    /* Card styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #334155;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    .metric-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 400;
        margin-top: 0.2rem;
        font-style: italic;
    }
    
    /* Form styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border: 2px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.75rem;
        font-size: 0.95rem;
        transition: border-color 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: #e80831;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: #e80831;
        transform: translateY(-1px);
    }
    
    .stSuccess {
        background: #dcfce7;
        border: 1px solid #bbf7d0;
        color: #166534;
        border-radius: 6px;
        border-left: 4px solid #22c55e;
    }
    
    .stError {
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #991b1b;
        border-radius: 6px;
        border-left: 4px solid #ef4444;
    }
    
    /* Section headers */
    h1, h2, h3 {
        color: #1e3a8a;
        font-weight: 600;
    }
    
    .dataframe {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        hide_index: 
    }
    /* Dataframe outer container */
    div[data-testid="stDataFrame"] > div {
            border-radius: 4px !important;
            border: 1px solid #cbd5e1 !important; /* subtle border */
    }
    div[data-testid="stDataFrame"] table {
            border-radius: 0 !important;
    }
           
</style>
""", unsafe_allow_html=True)

# Custom metric cards
def create_metric_card(title, value, subtitle=""):
    subtitle_html = f'<div class="metric-subtitle">{subtitle}</div>' if subtitle else ""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value">{value}</div>
        {subtitle_html}
    </div>
    """

# Initialize -- Begins here.
if "work_orders" not in st.session_state:
    st.session_state["work_orders"] = []

if "invoices" not in st.session_state:
    st.session_state["invoices"] = []

uidai_logo_base64 = get_base64_of_bin_file('uidai_english_logo.png')
aadhaar_logo_base64 = get_base64_of_bin_file('uidai-logo.png')
if uidai_logo_base64 or aadhaar_logo_base64:
    st.markdown(f"""
    <div class="uidai-official-header">
        <div class="uidai-left-section">
            {f'<img src="data:image/png;base64,{uidai_logo_base64}" class="uidai-logo-img" alt="UIDAI Logo">' if uidai_logo_base64 else '<div style="width:70px;height:70px;background:#e2e8f0;border-radius:4px;"></div>'}
        </div>
        <div>
            {f'<img src="data:image/png;base64,{aadhaar_logo_base64}" class="aadhaar-logo-img" alt="Aadhaar Logo">' if aadhaar_logo_base64 else '<div style="width:60px;height:60px;background:#e2e8f0;border-radius:4px;"></div>'}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Header - A Logo, U Logo, Time, CMS
current_time = get_current_time()

st.markdown(f"""
<div class="uidai-header">
    <div class="uidai-logo-section">
        <div class="uidai-title">
            <h1>CONTRACT MANAGEMENT SYSTEM</h1>
        </div>
    </div>
    <div class="header-time">
        <div>Date & Time</div>
        <div style="font-weight: 600;">{current_time}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# Tabs
tabs = st.tabs([
    "Dashboard",
    "New Work Order",
    "New Invoice", 
    "Manage",
    "Payment Schedule",
    "Analytics & Reports",
    "Search",
    "About"
])


# --------- DASHBOARD ---------
with tabs[0]:
    
    # Initialize data collections
    work_orders = st.session_state.get('work_orders', [])
    invoices = st.session_state.get('invoices', [])
    
    if not work_orders and not invoices:
        st.markdown(f"""
            <div style="text-align: center; padding: 3rem; background: white; border-radius: 8px;">
                <h2 style="color: #1e3a8a;">Welcome to your Contract Management Dashboard!</h2>
                <p style="font-size: 1.1rem; color: #64748b;">Create your first work order to get started.</p>
            </div>
            """, unsafe_allow_html=True)
        
    else:        
        # Calculate KPIs
        total_contracts = len(work_orders)
        total_invoices = len(invoices)
        
        total_contract_value = sum(wo.get('Total Contract Value (with GST)', 0) for wo in work_orders)
        total_workorder_value = sum(wo.get('Work-Order Value (with GST)', 0) for wo in work_orders)
        total_invoice_value = sum(inv.get('Payable (With GST)', 0) for inv in invoices)
        total_pending_value = total_workorder_value - total_invoice_value
        
        # Payment status metrics
        paid_invoices = len([inv for inv in invoices if inv.get('Payment_Status') == 'Paid'])
        pending_invoices = len([inv for inv in invoices if inv.get('Payment_Status') == 'Pending'])
        
        # Display KPI Cards
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="📋 Total Contracts",
                value=f"{total_contracts:,}",
                help="Number of active work orders"
            )
            
        with col2:
            st.metric(
                label="💰 Contract Value",
                value=f"₹{total_contract_value:,.0f}",
                help="Total contract value including GST"
            )
            
        with col3:
            st.metric(
                label="🧾 Total Invoices", 
                value=f"{total_invoices:,}",
                help="Number of invoices generated"
            )
            
        with col4:
            st.metric(
                label="💸 Invoiced Amount",
                value=f"₹{total_invoice_value:,.0f}",
                help="Total invoiced amount with GST"
            )
            
        with col5:
            payment_rate = (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0
            st.metric(
                label="✅ Payment Rate",
                value=f"{payment_rate:.1f}%",
                delta=f"{paid_invoices}/{total_invoices}",
                help="Percentage of paid invoices"
            )
        
        st.markdown("---")
        
        # ================== WORK ORDERS OVERVIEW ==================
        if work_orders:
            st.markdown("### Work Orders Overview")
            
            # Professional Control Panel for Work Orders
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                wo_view_mode = st.selectbox(
                    "📋 Work Orders View",
                    options=["Executive Summary", "Detailed Analysis", "Category Breakdown"],
                    help="Choose the level of detail for work orders display"
                )
            
            with col2:
                # Category filtering
                all_wo_categories = []
                for wo in work_orders:
                    for item in wo.get('Items', []):
                        cat = item.get('Category', 'Others')
                        if cat not in all_wo_categories:
                            all_wo_categories.append(cat)
                
                if len(all_wo_categories) > 1:
                    selected_wo_categories = st.multiselect(
                        "🏷️ Filter Categories",
                        options=all_wo_categories,
                        default=all_wo_categories,
                        help="Select categories to display"
                    )
                else:
                    selected_wo_categories = all_wo_categories
            
            with col3:
                wo_sort_options = ["Contract Date", "Contract Value", "Work Order Value", "Item(s) Count"]
                wo_sort_by = st.selectbox(
                    "🔄 Sort By",
                    options=wo_sort_options,
                    help="Sort work orders by selected criteria"
                )
            
            # Filter and Sort Work Orders
            filtered_work_orders = []
            for wo in work_orders:
                wo_categories = [item.get('Category', 'Others') for item in wo.get('Items', [])]
                if any(cat in selected_wo_categories for cat in wo_categories):
                    filtered_work_orders.append(wo)
            
            # Sort work orders
            if wo_sort_by == "Contract Date":
                try:
                    filtered_work_orders = sorted(filtered_work_orders, 
                        key=lambda x: datetime.strptime(x.get('Contract Date', '01/01/2025'), "%d/%m/%Y"), 
                        reverse=True)
                except:
                    pass
            elif wo_sort_by == "Contract Value":
                filtered_work_orders = sorted(filtered_work_orders, 
                    key=lambda x: x.get('Total Contract Value (with GST)', 0), reverse=True)
            elif wo_sort_by == "Work Order Value":
                filtered_work_orders = sorted(filtered_work_orders, 
                    key=lambda x: x.get('Work-Order Value (with GST)', 0), reverse=True)
            elif wo_sort_by == "Item(s) Count":
                filtered_work_orders = sorted(filtered_work_orders, 
                    key=lambda x: x.get('Item(s) Count', 0), reverse=True)
            
            st.markdown("---")
            
            # Display Work Orders based on view mode
            if wo_view_mode == "Executive Summary":
                # Clean Executive Summary Table
                wo_summary_data = []
                for wo in filtered_work_orders:
                    wo_summary_data.append({
                        "Contract": wo.get('Contract Number', 'N/A'),
                        "Vendor": wo.get('Vendor', 'N/A'),
                        "Location": wo.get('Location', 'N/A'),
                        "Date": wo.get('Contract Date', 'N/A'),
                        "Items": wo.get('Item(s) Count', 0),
                        "Contract Value": f"₹{wo.get('Total Contract Value (with GST)', 0):,.0f}",
                        "WO Value": f"₹{wo.get('Work-Order Value (with GST)', 0):,.0f}",
                        "WO %": f"{wo.get('% Work-Order', 0):.1f}%"
                    })
                
                if wo_summary_data:
                    wo_summary_df = pd.DataFrame(wo_summary_data)
                    st.dataframe(
                        style_alternate_rows(wo_summary_df),
                        use_container_width=True,
                        hide_index=True,
                        height=min(400, len(wo_summary_data) * 35 + 50)
                    )
            
            elif wo_view_mode == "Detailed Analysis":
                # Comprehensive Analysis with Items
                for i, wo in enumerate(filtered_work_orders[:5]):  # Show top 5 for performance
                    with st.expander(
                        f"📋 {wo.get('Contract Number', 'Unknown')} - {wo.get('Vendor', 'Unknown')} (₹{wo.get('Work-Order Value (with GST)', 0):,.0f})",
                        expanded=(i == 0)
                    ):
                        # Work Order Summary
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Contract Value", f"₹{wo.get('Total Contract Value (with GST)', 0):,.0f}")
                        with col2:
                            st.metric("WO Value", f"₹{wo.get('Work-Order Value (with GST)', 0):,.0f}")
                        with col3:
                            st.metric("WO Percentage", f"{wo.get('% Work-Order', 0):.1f}%")
                        with col4:
                            st.metric("Item(s) Count", wo.get('Item(s) Count', 0))
                        
                        # Items Summary
                        items = wo.get('Items', [])
                        if items:
                            items_summary = []
                            for item in items:
                                items_summary.append({
                                    "Item": item.get('Item Name', 'N/A'),
                                    "Category": item.get('Category', 'N/A'),
                                    "Qty": item.get('Qty', 0),
                                    "Value": f"₹{item.get('₹ with GST', 0):,.0f}"
                                })
                            
                            items_df = pd.DataFrame(items_summary)
                            items_df_fy = add_financial_year_columns(items_df)
                            st.dataframe(style_alternate_rows(items_df_fy), use_container_width=True, hide_index=True)
                
                if len(filtered_work_orders) > 5:
                    st.info(f"Showing top 5 work orders. Total: {len(filtered_work_orders)} work orders available.")
            
            else:  # Category Breakdown
                # Category Analysis
                category_summary = {}
                for wo in filtered_work_orders:
                    for item in wo.get('Items', []):
                        category = item.get('Category', 'Others')
                        if category not in category_summary:
                            category_summary[category] = {
                                'count': 0,
                                'total_value': 0,
                                'contracts': set()
                            }
                        category_summary[category]['count'] += 1
                        category_summary[category]['total_value'] += item.get('₹ with GST', 0)
                        category_summary[category]['contracts'].add(wo.get('Contract Number', 'Unknown'))
                
                # Display category cards
                for category, data in category_summary.items():
                    with st.expander(
                        f"📦 {category} ({data['count']} items | ₹{data['total_value']:,.0f} | {len(data['contracts'])} contracts)",
                        expanded=True
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Items", data['count'])
                        with col2:
                            st.metric("Total Value", f"₹{data['total_value']:,.0f}")
                        with col3:
                            st.metric("Contracts", len(data['contracts']))
            
            # Work Orders Footer Summary
            if filtered_work_orders:
                filtered_wo_value = sum(wo.get('Work-Order Value (with GST)', 0) for wo in filtered_work_orders)
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Showing:** {len(filtered_work_orders)} of {len(work_orders)} work orders")
                with col2:
                    st.info(f"**Filtered Value:** ₹{filtered_wo_value:,.2f}")
        
        # ================== INVOICES OVERVIEW ==================
        if invoices:
            st.markdown("---")
            st.markdown("### Invoices Overview")
            
            # Professional Control Panel for Invoices
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                inv_view_mode = st.selectbox(
                    "🧾 Invoices View",
                    options=["Executive Summary", "Payment Analysis", "Status Breakdown"],
                    help="Choose the level of detail for invoices display"
                )
            
            with col2:
                # Payment status filtering
                payment_statuses = list(set([inv.get('Payment_Status', 'Pending') for inv in invoices]))
                selected_statuses = st.multiselect(
                    "💳 Payment Status",
                    options=payment_statuses,
                    default=payment_statuses,
                    help="Filter by payment status"
                )
            
            with col3:
                inv_sort_options = ["Invoice Date", "Invoice Value", "Payable Amount", "Contract Number"]
                inv_sort_by = st.selectbox(
                    "🔄 Sort By",
                    options=inv_sort_options,
                    help="Sort invoices by selected criteria"
                )
            
            # Filter and Sort Invoices
            filtered_invoices = [inv for inv in invoices if inv.get('Payment_Status', 'Pending') in selected_statuses]
            
            # Sort invoices
            if inv_sort_by == "Invoice Date":
                try:
                    filtered_invoices = sorted(filtered_invoices, 
                        key=lambda x: datetime.strptime(x.get('Date of Invoice', '01/01/2025'), "%d/%m/%Y"), 
                        reverse=True)
                except:
                    pass
            elif inv_sort_by == "Invoice Value":
                filtered_invoices = sorted(filtered_invoices, 
                    key=lambda x: x.get('Invoice Value', 0), reverse=True)
            elif inv_sort_by == "Payable Amount":
                filtered_invoices = sorted(filtered_invoices, 
                    key=lambda x: x.get('Payable Amount', 0), reverse=True)
            elif inv_sort_by == "Contract Number":
                filtered_invoices = sorted(filtered_invoices, 
                    key=lambda x: x.get('Contract Number', ''))
            
            st.markdown("---")
            
            # Display Invoices based on view mode
            if inv_view_mode == "Executive Summary":
                # Clean Executive Summary Table
                inv_summary_data = []
                for inv in filtered_invoices:
                    inv_summary_data.append({
                        "Invoice #": inv.get('Invoice Number', 'N/A'),
                        "Date": inv.get('Date of Invoice', 'N/A'),
                        "Contract": inv.get('Contract Number', 'N/A'),
                        "Item": inv.get('Item Name', 'N/A'),
                        "Category": inv.get('Category', 'N/A'),
                        "Invoice Value": f"₹{inv.get('Invoice Value', 0):,.0f}",
                        "Payable": f"₹{inv.get('Payable Amount', 0):,.0f}",
                        "Status": inv.get('Payment_Status', 'Pending')
                    })
                
                if inv_summary_data:
                    inv_summary_df = pd.DataFrame(inv_summary_data)
                    inv_summary_df_fy = add_financial_year_columns(inv_summary_df)
                    st.dataframe(
                        style_alternate_rows(inv_summary_df_fy),
                        use_container_width=True,
                        hide_index=True,
                        height=min(400, len(inv_summary_data) * 35 + 50)
                    )
            
            elif inv_view_mode == "Payment Analysis":
                # Payment Analysis with Financial Metrics
                payment_analysis = {}
                for inv in filtered_invoices:
                    status = inv.get('Payment_Status', 'Pending')
                    if status not in payment_analysis:
                        payment_analysis[status] = {
                            'count': 0,
                            'total_invoice_value': 0,
                            'total_payable': 0,
                            'total_ro_amount': 0
                        }
                    payment_analysis[status]['count'] += 1
                    payment_analysis[status]['total_invoice_value'] += inv.get('Invoice Value', 0)
                    payment_analysis[status]['total_payable'] += inv.get('Payable Amount', 0)
                    payment_analysis[status]['total_ro_amount'] += inv.get('Release Order Amount', 0)
                
                # Display payment status cards
                for status, data in payment_analysis.items():
                    status_color = "#22c55e" if status == "Paid" else "#f59e0b" if status == "Pending" else "#ef4444"
                    
                    with st.container():
                        st.markdown(f"""
                        <div style="background: {status_color}15; border-left: 4px solid {status_color}; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                        <strong>{status} Invoices ({data['count']})</strong>
                        </div>""", unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Invoice Value", f"₹{data['total_invoice_value']:,.0f}")
                        with col2:
                            st.metric("Payable Amount", f"₹{data['total_payable']:,.0f}")
                        with col3:
                            st.metric("RO Amount", f"₹{data['total_ro_amount']:,.0f}")
            
            else:  # Status Breakdown
                # Detailed status breakdown with individual invoices
                status_groups = {}
                for inv in filtered_invoices:
                    status = inv.get('Payment_Status', 'Pending')
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(inv)
                
                for status, invs in status_groups.items():
                    status_color = "#22c55e" if status == "Paid" else "#f59e0b" if status == "Pending" else "#ef4444"
                    total_value = sum(inv.get('Payable Amount', 0) for inv in invs)
                    
                    with st.expander(
                        f"💳 {status} ({len(invs)} invoices | ₹{total_value:,.0f})",
                        expanded=(status == "Pending")
                    ):
                        status_data = []
                        for inv in invs:
                            status_data.append({
                                "Invoice": inv.get('Invoice Number', 'N/A'),
                                "Contract": inv.get('Contract Number', 'N/A'),
                                "Item": inv.get('Item Name', 'N/A')[:20] + "..." if len(inv.get('Item Name', '')) > 20 else inv.get('Item Name', 'N/A'),
                                "Payable": f"₹{inv.get('Payable Amount', 0):,.0f}",
                                "RO Date": inv.get('Date of RELEASE ORDER', 'N/A')
                            })
                        
                        if status_data:
                            status_df = pd.DataFrame(status_data)
                            status_df_fy = add_financial_year_columns(status_df)
                            st.dataframe(style_alternate_rows(status_df_fy), use_container_width=True, hide_index=True)
            
            # Invoices Footer Summary
            if filtered_invoices:
                filtered_inv_value = sum(inv.get('Payable Amount', 0) for inv in filtered_invoices)
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Showing:** {len(filtered_invoices)} of {len(invoices)} invoices")
                with col2:
                    st.info(f"**Filtered Value:** ₹{filtered_inv_value:,.2f}")
    

# --------- NEW WORK ORDER TAB ---------
with tabs[1]:
    st.markdown("#### Create New Work Order")

    wo_uploaded_proof = st.file_uploader(
        "Upload **Proof** of Contract",
        type=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
        key="wo_uploaded_proof"
    )

    if 'work_orders' not in st.session_state:
        st.session_state['work_orders'] = []

    # Duplicate functions
    def is_duplicate_cn(cn: str) -> bool:
        if not cn:
            return False
        return cn in {wo.get('Contract Number', '') for wo in st.session_state['work_orders']}
    def is_duplicate_subcn(subcn: str) -> bool:
        if not subcn:
            return False
        return subcn in {wo.get('Sub-Contract Number', '') for wo in st.session_state['work_orders']}
    
    def is_duplicate_wonum(wonum: str) -> bool:
        if not wonum:
            return False
        return wonum in {wo.get('Work-Order Number', '') for wo in st.session_state['work_orders']}
    
    def contract_exists_full(cn: str, subcn: str, wonum: str, item_name: str, item_location: str, item_category: str) -> bool:
        cn = (cn or "").strip()
        subcn = (subcn or "").strip()
        wonum = (wonum or "").strip()
        item_name = (item_name or "").strip()
        item_location = (item_location or "").strip()
        item_category = (item_category or "").strip()
        if not (cn and subcn and wonum and item_name and item_location and item_category):
            return False
        
        for wo in st.session_state.get('work_orders', []):
            if cn == (wo.get("Contract Number","") or "").strip() and subcn == (wo.get("Sub-Contract Number","") or "").strip() and wonum == (wo.get("Work-Order Number","") or "").strip():
                for it in wo.get("Items", []):
                    if (item_name == (it.get("Item Name","") or "").strip()
                        and item_location == (it.get("Item Location","") or "").strip()
                        and item_category == (it.get("Category","") or "").strip()):
                        return True
        return False    
    

    def clear_all_inputs():
        keys = list(st.session_state.keys())
        for k in keys:
            if k.startswith("wo_"):
                del st.session_state[k]
        for k in list(st.session_state.keys()):
            if k.startswith("wo_sl_no_") or k.startswith("wo_name_") or k.startswith("wo_qty_") or k.startswith("wo_value_"):
                del st.session_state[k]
        # Also reset category locking trackers
        for k in ["wo_prev_cn", "wo_prev_subcn", "wo_prev_wonum"]:
            if k in st.session_state:
                del st.session_state[k]

    # Row 1
    r1c1, r1c2, r1c3, r1c4  = st.columns([2.5, 0.5, 1.5, 1.5])
    contract_number = r1c1.text_input("Contract Number", key="wo_contract_number")
    cn_value = contract_number.strip()
    cn_dup = is_duplicate_cn(cn_value)
    if cn_value:
        if cn_dup:
            r1c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#fee2e2;border:1px solid #fecaca;color:#991b1b;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#ef4444;"></span> Exists
            </div>""", unsafe_allow_html=True)
        else:
            r1c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#ecfdf5;border:1px solid #bbf7d0;color:#065f46;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#22c55e;"></span> Available
            </div>""", unsafe_allow_html=True)
    
    vendor = r1c3.text_input("Vendor", key="wo_vendor")
    location = r1c4.text_input("Location", key="wo_location")

    # Row 2
    r2c1, r2c2, r2c3 = st.columns([1.5, 1.5, 3])
    contract_value = r2c1.number_input("Contract Value ₹ (Basic)", min_value=0.0, step=1.0000, format="%.4f", key="wo_contract_value")
    gst_value = r2c2.number_input("GST (%)", min_value=0.0, max_value=100.0, value=5.0, step=1.00, format="%.2f", key="wo_gst_custom")
    contract_date = r2c3.date_input("Contract Date", value=datetime.today(), format="DD/MM/YYYY", key="wo_contract_date")

    # Row 3
    r3c1, r3c2, r3c3, r3c4 = st.columns([2.5, 0.5, 1.5, 1.5])
    workorder_number = r3c1.text_input("Work-Order Number", key="wo_workorder_number")
    wonum_value = workorder_number.strip()
    wonum_dup = is_duplicate_wonum(wonum_value)

    if wonum_value:
        if wonum_dup:
            r3c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#fee2e2;border:1px solid #fecaca;color:#991b1b;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#ef4444;"></span> Exists
            </div>""", unsafe_allow_html=True)
        else:
            r3c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#ecfdf5;border:1px solid #bbf7d0;color:#065f46;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#22c55e;"></span> Available
            </div>""", unsafe_allow_html=True)

    workorder_pct = r3c3.number_input("% Work-Order", min_value=0.0, max_value=100.00, step=1.00, format="%.2f", key="wo_workorder_pct")
    workorder_value = r3c4.number_input("Work-Order Value ₹ (Basic)", value=contract_value * (workorder_pct/100), min_value=0.0, step=1.0000, format="%.4f", key="wo_workorder_value")
    total_workorder_withgst = workorder_value * (1 + (gst_value/100))
    if workorder_value > contract_value:
        r3c4.caption(f"⚠️ Exceeds Contract Value: **{format_indian_currency(contract_value)}**")
    else: 
        r3c4.caption(f"Workorder Value (with GST): **{format_indian_currency(total_workorder_withgst)}**")
    
    # Row 4
    r4c1, r4c2, r4c3 = st.columns([2.5, 0.5, 3])
    subcontract_number = r4c1.text_input("Sub-Contract Number", key="wo_subcontract_number")
    subcn_value = subcontract_number.strip()
    subcn_dup = is_duplicate_subcn(subcn_value)
    if subcn_value:
        if subcn_dup:
            r4c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#fee2e2;border:1px solid #fecaca;color:#991b1b;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#ef4444;"></span> Exists
            </div>""", unsafe_allow_html=True)
        else:
            r4c2.markdown("""<div style="margin-top:1.9rem;padding:6px 10px;border-radius:999px;
                display:inline-flex;align-items:center;gap:8px;font-size:0.85rem;
                background:#ecfdf5;border:1px solid #bbf7d0;color:#065f46;box-shadow:0 1px 0 rgba(0,0,0,0.02);">
                <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#22c55e;"></span> Available
            </div>""", unsafe_allow_html=True)

    if "wo_prev_cn" not in st.session_state:
        st.session_state["wo_prev_cn"] = cn_value

    if "wo_prev_subcn" not in st.session_state:
        st.session_state["wo_prev_subcn"] = subcn_value
    
    if "wo_prev_wonum" not in st.session_state:
        st.session_state["wo_prev_wonum"] = wonum_value


    items_count = r4c3.number_input("Item(s) Count", min_value=1, value=1, step=1, key="wo_items_count")    
    
    # Row 5
    r5c1, r5c2 = st.columns(2)
    total_contract_with_gst = contract_value * (1 + (gst_value/100))
    r5c1.success(f"Total Contract Value (with GST): **{format_indian_currency(total_contract_with_gst)}**")
    
    # Validation (unchanged)
    missing_fields = []    
    if not cn_value: 
        missing_fields.append("Contract Number")
    if not location.strip():
        missing_fields.append("Location")
    if not vendor.strip(): 
        missing_fields.append("Vendor")
    if contract_value <= 0:
        missing_fields.append("Contract Value (₹)")
    if not subcontract_number.strip():
        missing_fields.append("Sub-Contract Number")
    if gst_value is None or gst_value < 0:
        missing_fields.append("GST")

    if not wo_uploaded_proof and missing_fields:
        r5c2.warning("Please upload the proof and fill all mandatory fields: " + ", ".join(missing_fields))
    elif not wo_uploaded_proof:
        r5c2.warning("Please upload the proof")
    elif missing_fields:
        r5c2.warning("Please fill all mandatory fields: " + ", ".join(missing_fields))
    
    
    st.markdown("#### Item Details")
    items_data = []
    calculated_total_value = 0.0
    item_validities = []
    any_full_exists = False

    for idx in range(1, items_count + 1):
        c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
        item_serial_no = c_a.text_input("Sl.", value=str(idx), disabled=True, key=f"item_sl_no_{idx}")
        item_name = c_b.text_input("Item Name", key=f"item_name_{idx}")
        item_location = c_c.text_input("Location", key=f"item_location_{idx}")

        category_options = ["Hardware", "Hardware (+ AMC)", "AMC", "Software", "Staff Cost", "Solution and Support", "Telecom", "Others",]
        category_disabled = not (cn_value and subcn_value and wonum_value)
        category = c_d.selectbox(
            "Category",
            category_options,
            placeholder="Select Category",
            key=f"item_category_{idx}",
            disabled=category_disabled,
        )

        item_qty = c_e.number_input("Qty", min_value=1, step=1, key=f"item_qty_{idx}")

        if category == "Staff Cost":
            item_val = c_f.number_input("Man per Month (₹)", min_value=0.0, step=1.0000, format="%.4f", key=f"item_value_{idx}")
        else:
            item_val = c_f.number_input("Value per Item (₹)", min_value=0.0, step=1.0000, format="%.4f", key=f"item_value_{idx}")

        item_val_qty = item_qty * item_val
        item_val_withtax = item_qty * item_val * (1 + (gst_value/100))
        
        if category == "Staff Cost":
            item_val_tax = c_g.number_input("Total Man per Month ₹ (with Tax)", value=item_val_withtax, step=1.0000, format="%.4f", key=f"item_val_withtax_{idx}")
        else:
            item_val_tax = c_g.number_input("Item Total ₹ (with Tax)", value=item_val_withtax, format="%.4f", key=f"item_val_withtax_{idx}")       

        item_remark = c_h.text_input("Remark", key=f"item_remark_{idx}")

        item_row = {
            "Item Sl. No.": idx,
            "Item Name": item_name,
            "Item Location": item_location,
            "Category": category,
            "Qty": item_qty,
            "Value per Item": float(item_val),
            "₹ without GST": float(item_val_qty),
            "GST": float(gst_value),
            "₹ with GST": float(item_val_tax),
            "Remark": item_remark,
        }
        
        if category == "Hardware":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            
            item_warranty_duration = c_d.number_input("Warranty Duration (Months)", min_value=1, value=36, step=1, key=f"item_warranty_duration_{idx}")
            item_warranty_years = (item_warranty_duration / 12)
            c_d.caption(f"{item_warranty_years:.2f} Years")
            item_warranty_pct = c_e.number_input("% Warranty", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key=f"item_warranty_pct_{idx}")
            item_rate_warranty = c_f.number_input("Rate per Item incl. Warranty", value=float(item_val * (1 + (item_warranty_pct/100))), format="%.4f", step=0.10, key=f"item_rate_warranty_{idx}")
            item_warranty_val_withtax = c_g.number_input("Total Value ₹ (with Tax)", value=float(item_rate_warranty * item_qty * (1 + (gst_value/100))), format="%.4f", key=f"item_warranty_val_withtax_{idx}") 
            add_remark = c_h.text_input("Addnl. Remark", key=f"add_remark_{idx}")

            item_row.update({ 
                "Warranty Duration (Months)": item_warranty_duration,
                "Warranty Duration (Years)": item_warranty_years,
                "% Warranty": item_warranty_pct,
                "Rate incl. Warranty": item_rate_warranty,
                "Warranty Total ₹ with GST": item_warranty_val_withtax,
                "Additional Remark": add_remark
            })

            to_add = float(item_warranty_val_withtax)

        elif category == "AMC":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            
            item_amc_duration = c_d.number_input("AMC Duration (Months)", min_value=1, value=48, step=1, key=f"item_amc_duration_{idx}")
            item_amc_years = (item_amc_duration / 12)
            c_d.caption(f"{item_amc_years:.2f} Years")
            item_amc_pct = c_e.number_input("% AMC", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key=f"item_amc_pct_{idx}")
            item_rate_amc = c_f.number_input("Rate per Item incl. AMC", value=float(item_val * (1 + (item_amc_pct/100))), format="%.4f", step=0.10, key=f"item_rate_amc_{idx}")
            item_amc_val_withtax = c_g.number_input("Item Total Value ₹ (with Tax)", value=float(item_rate_amc * item_qty * (1 + (gst_value/100))), format="%.4f", key=f"item_value_withtax_{idx}") 
            add_remark = c_h.text_input("Addnl. Remark", key=f"add_remark_{idx}")
            item_row.update({
                "AMC Duration (Months)": item_amc_duration,
                "AMC Duration (Years)": item_amc_years,
                "% AMC": item_amc_pct,
                "Rate incl. AMC": item_rate_amc,
                "AMC Total ₹ with GST": item_amc_val_withtax,
                "Additional Remark": add_remark
            })

            to_add = float(item_amc_val_withtax)

        elif category == "Telecom":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            subvendor = c_d.text_input("Sub-Vendor Name", key=f"item_subvendor_{idx}")         
            telecom_link = c_e.text_input("Link/Location", key=f"item_telecom_link_{idx}")
            telecom_type = c_f.text_input("Type", key=f"item_telecom_type_{idx}")
            telecom_capacity = c_g.text_input("Capacity", key=f"item_capacity_{idx}")
            add_remark = c_h.text_input("Addnl. Remark", key=f"add_remark_{idx}")
            item_row.update({
                "Telecom Link/Location": telecom_link,
                "Telecom Type": telecom_type,
                "Telecom Capacity": telecom_capacity,
                "Additional Remark": add_remark
            })
            
            to_add = float(item_val_tax)

        elif category == "Solution and Support":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            item_support_pct = c_c.number_input("% Support", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key=f"item_support_pct_{idx}")
            item_support_duration = c_d.number_input("Support Duration (Months)", min_value=1, value=48, step=1, key=f"item_support_duration_{idx}")
            item_support_years = (item_support_duration / 12)
            c_d.caption(f"{item_support_years:.2f} Years")

            item_support_period = c_e.selectbox(
                "Support Period",
                options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                index=0,
                key=f"item_support_period_{idx}"
            )
            if item_support_period == "Annually":
                c_e.caption(f"{item_support_years:.2f} Years")
            elif item_support_period == "Half Yearly":
                c_e.caption(f"{(item_support_years * 2):.2f} Half Years")
            elif item_support_period == "Quarterly":
                c_e.caption(f"{(item_support_years * 4):.2f} Quarters")
            elif item_support_period == "Monthly":
                c_e.caption(f"{item_support_duration:.2f} Months")


            item_support_start_date = c_f.date_input("Period Start Date", value=datetime.today(), format="DD/MM/YYYY", key=f"item_support_start_{idx}")
            item_rate_support = c_g.number_input("Rate per Item incl. Support", value=float(item_val * (1 + (item_support_pct/100))), format="%.4f", step=0.10, key=f"item_rate_support_{idx}")            
            item_support_val_withtax = c_h.number_input("Total Value ₹(with Tax)", value=float(item_rate_support * item_qty * (1 + (gst_value/100))), format="%.4f", key=f"item_value_withtax_{idx}") 

            item_row.update({
                "Support Duration (Months)":item_support_duration, 
                "Support Duration (Years)": item_support_years,
                "Support Period": item_support_period,
                "% Support": item_support_pct,
                "Rate incl. Support": item_rate_support,
                "Support Total ₹ with GST": item_support_val_withtax,
                "Period Start Date": item_support_start_date.strftime("%d/%m/%Y")
            })

            to_add =float(item_support_val_withtax)

        elif category == "Staff Cost":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            item_staff_period = None
            item_staff_from = None
            item_staff_to = None
            item_staff_start_date = None
            item_staff_duration = 0
            item_staff_years = 0.0

            mode = c_c.radio(
                "Duration",
                options=["Period", "From : To"],
                index=0,
                key=f"item_staff_mode_{idx}",
                horizontal=True,
            )
            
            if mode == "From : To":
                item_staff_from = c_d.date_input(
                    "From",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"item_staff_from_{idx}",
                    )
                item_staff_to = c_e.date_input(
                    "To",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"item_staff_to_{idx}",
                )
                
                if item_staff_to < item_staff_from:
                    c_d.caption("0.00 Years")
                    item_staff_duration = 0
                    item_staff_years = 0.0
                else:
                    start_y, start_m, start_d = item_staff_from.year, item_staff_from.month, item_staff_from.day
                    end_y, end_m, end_d = item_staff_to.year, item_staff_to.month, item_staff_to.day
                    months = (end_y - start_y) * 12 + (end_m - start_m)
                    if end_d >= start_d:
                        months += 1
                        months = max(months, 1)
                
                    item_staff_duration = months
                    item_staff_years = months / 12.0  
                c_d.caption(f"{(item_staff_years or 0.0):.2f} Years") 
            
            elif mode == "Period":
                item_staff_duration = c_d.number_input(
                    "Staff Duration (Months)",
                    min_value=12,
                    step=1,
                    key=f"item_staff_duration_{idx}",
                )
                item_staff_years = item_staff_duration / 12.0
                c_d.caption(f"{item_staff_years:.2f} Years")

                item_staff_period = c_e.selectbox(
                    "Staff Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key=f"item_staff_period_{idx}"
                    )
                if item_staff_period == "Annually":
                    c_e.caption(f"{item_staff_years:.2f} Years")
                elif item_staff_period == "Half Yearly":
                    c_e.caption(f"{(item_staff_duration / 6):.2f} Half Years")
                elif item_staff_period == "Quarterly":
                    c_e.caption(f"{(item_staff_duration / 3):.2f} Quarters")
                elif item_staff_period == "Monthly":
                    c_e.caption(f"{item_staff_duration:.2f} Months")                
        
            item_staff_start_date = c_f.date_input(
                "Staff Start Date",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"item_staff_start_{idx}",
            )
            
            add_remark = c_h.text_input("Addnl. Remark", key=f"add_remark_{idx}")

            item_row.update({
                "Staff Duration (Months)": item_staff_duration,
                "Staff Duration (Years)": item_staff_years,
                "Staff Period": item_staff_period,
                "Staff From": item_staff_from.strftime("%d/%m/%Y") if item_staff_from else "",
                "Staff To": item_staff_to.strftime("%d/%m/%Y") if item_staff_to else "",
                "Staff Start Date": item_staff_start_date.strftime("%d/%m/%Y"),
                "Additional Remark": add_remark,
            })
            
            to_add = float(item_val_tax)

        elif category == "Hardware (+ AMC)":
            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            item_warranty_duration = c_d.number_input("Warranty Duration (Months)", min_value=1, value=36, step=1, key=f"item_warranty_duration_{idx}")
            item_warranty_years = (item_warranty_duration / 12)
            c_d.caption(f"{item_warranty_years:.2f} Years")
            item_warranty_pct = c_e.number_input("% Warranty", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key=f"item_warranty_pct_{idx}")
            item_rate_warranty = c_f.number_input("Rate per Item incl. Warranty", value=float(item_val * (1 + (item_warranty_pct/100))), format="%.4f", step=0.10, key=f"item_rate_warranty_{idx}")
            item_warranty_val_withtax = c_g.number_input("Item Total Value ₹ (with Tax)", value=float(item_rate_warranty * item_qty * (1 + (gst_value/100))), format="%.4f", key=f"item_warranty_val_withtax_{idx}") 

            c_a, c_b, c_c, c_d, c_e, c_f, c_g, c_h = st.columns([0.3, 0.7, 0.65, 1, 0.8, 1, 1, 0.8])
            item_amc_duration = c_d.number_input("AMC Duration (Months)", min_value=1, value=48, step=1, key=f"item_amc_duration_{idx}")
            item_amc_years = (item_amc_duration / 12)
            c_d.caption(f"{item_amc_years:.2f} Years")
            item_amc_pct = c_e.number_input("% AMC", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key=f"item_amc_pct_{idx}")
            item_rate_amc = item_val * (1 + (item_amc_pct/100))
            item_rate_amc_pct = c_f.number_input("Rate per Item incl. AMC", value=item_rate_amc, format="%.4f", step=0.10, key=f"item_rate_amc_{idx}")            
            item_amc_val_withtax = item_rate_amc_pct * item_qty * (1 + (gst_value/100))
            item_total_amc_with = c_g.number_input("Total Value ₹ (with Tax)", value=item_amc_val_withtax, format="%.4f", key=f"item_value_withtax_{idx}") 
            add_remark = c_h.text_input("Addnl. Remark", key=f"add_remark_{idx}")

            item_row.update({
                "Warranty Duration (Months)": item_warranty_duration,
                "Warranty Duration (Years)": item_warranty_years,
                "% Warranty": item_warranty_pct,
                "Rate incl. Warranty": item_rate_warranty,
                "Warranty Total ₹ with GST": item_warranty_val_withtax,

                "AMC Duration (Months)": item_amc_duration,
                "AMC Duration (Years)": item_amc_years,
                "% AMC": item_amc_pct,
                "Rate incl. AMC": item_rate_amc,
                "AMC Total ₹ with GST": item_amc_val_withtax,

                "Additional Remark": add_remark
            })    
            to_add = float(item_total_amc_with) + float(item_warranty_val_withtax)
        
        else: 
            to_add = float(item_val_tax)
        
        calculated_total_value += float(to_add)
                
        effective_category = (category or "").strip()
        exists_item_full = contract_exists_full(cn_value, subcn_value, wonum_value, item_name, item_location, effective_category)
        any_full_exists = any_full_exists or exists_item_full

        if effective_category:
            c_a.caption(
                """<div style="margin-top:0.2rem;padding:4px 8px;border-radius:999px;display:inline-flex;align-items:center;gap:6px;font-size:0.75rem;{bg}{bd}{fg}"><span style="display:inline-block;width:6px;height:6px;border-radius:999px;{dot}"></span> {txt}</div>""".format(
                    bg="background:#fee2e2;" if exists_item_full else "background:#ecfdf5;",
                    bd="border:1px solid #fecaca;" if exists_item_full else "border:1px solid #bbf7d0;",
                    fg="color:#991b1b;" if exists_item_full else "color:#065f46;",
                    dot="background:#ef4444;" if exists_item_full else "background:#22c55e;",
                    txt="Exists" if exists_item_full else "Available",
                ),
                unsafe_allow_html=True,
            )

        ok = bool(item_name.strip()) and item_qty >= 1 and item_val > 0
        item_validities.append(ok)
        items_data.append(item_row)
        

    if not (all(item_validities) and len(items_data) >= 1):
        st.warning("Ensure each item has a name, quantity ≥ 1, and value per item > 0.")

    if abs(calculated_total_value - float(total_workorder_withgst)) > 0.01:
        st.warning(
            f"Value Mismatch: Total Value {format_indian_currency(calculated_total_value)} "
            f"vs Work Order value {format_indian_currency(total_workorder_withgst)}"
        )
    else:
        st.success("Value Verified: Items total matches the contract value.")
    
    if any_full_exists:
        st.warning("Submission disabled. Duplicate detected: Same Contract Number Sub-Contract Number, Work-Order Number, Item Name and Item Category already exist.")

    is_valid = (cn_value) and (not missing_fields) and all(item_validities) and (wo_uploaded_proof) and (not any_full_exists)

    

    a1, a2 = st.columns([2.5, 1.5])
    with a1:
        create_clicked = st.button("Create Work Order", key="create_wo", disabled=not is_valid, use_container_width=True)
    with a2:
        clear_clicked = st.button("Clear All", key="clear_wo", use_container_width=True)

    if clear_clicked:
        clear_all_inputs()
        st.rerun()

    if create_clicked and is_valid:
        work_order_summary = {
            "Contract Number": cn_value,
            "Sub-Contract Number": subcn_value,
            "Work-Order Number": wonum_value,
            "% Work-Order": float(workorder_pct),
            "Work-Order Value (Basic)": float(workorder_value),
            "Work-Order Value (with GST)": float(total_workorder_withgst),
            "Vendor": vendor.strip(),
            "Location": location.strip(),
            "Contract Date": contract_date.strftime("%d/%m/%Y"),
            "GST (%)": float(gst_value),
            "Contract Value": float(contract_value),
            "Total Contract Value (with GST)": float(total_contract_with_gst),
            "Item(s) Count": int(items_count),
            "Items": items_data,
            "Proof Filename": getattr(wo_uploaded_proof, "name", None),
            "Created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        st.session_state['work_orders'].append(work_order_summary)
        st.success(f"✅ Contract '{cn_value}' | Work Order '{wonum_value}' | Sub-Contract '{subcn_value}' created successfully!")
        st.rerun()

    # DISPLAY EXISTING WORK ORDERS
    if st.session_state.get('work_orders'):
        st.markdown("---")
        st.markdown("#### Existing Work Orders")

        wo_detailed_rows = []
        current_date = datetime.now()

        #contract-level columns
        
        base_cols = [
            "Contract Number", "Vendor Name", "Location", "Contract Date", "Contract Value", "GST", "Total Contract Value (with GST)",
            "Work-Order Number", "% Work-Order", "Work-Order Value (Basic)", "Work-Order Value (with GST)",
            "Sub-Contract Number", "Item(s) Count", "Item Sl. No.", "Item Name", "Category", "Qty", "Value per Item",
            "₹ without GST", "₹ with GST", "Ageing", "Remark"
        ]
        
        # category-specific columns
        extra_cols = [
            "Warranty Duration (Months)", "Warranty Duration (Years)", "% Warranty", "Rate incl. Warranty", "Warranty Total with GST",
            "AMC Duration (Months)", "AMC Duration (Years)", "% AMC", "Rate incl. AMC", "AMC Total with GST",
            "Telecom Link/Location", "Telecom Type", "Telecom Capacity",
            "% Support", "Support Duration (Months)", "Support Duration (Years)", "Support Period", "Rate incl. Support", "Support Total ₹ with GST",
            "Staff Duration (Months)", "Staff Duration (Years)", "Staff Period", "Staff From", "Staff To", "Staff Start Date",
            "Additional Remark"
        ]
       
        all_columns = base_cols + extra_cols

        for wo in st.session_state['work_orders']:
            try:
                contract_date_dt = datetime.strptime(wo.get("Contract Date", "01/01/2025"), "%d/%m/%Y")
                age_delta = current_date - contract_date_dt
                total_days = age_delta.days
                years = total_days // 365
                remaining_days = total_days % 365
                ageing = f"{years} year{'s' if years != 1 else ''}, {remaining_days} day{'s' if remaining_days != 1 else ''}" if years > 0 else f"{remaining_days} day{'s' if remaining_days != 1 else ''}"
            except:
                ageing = "N/A"

            items = wo.get("Items", [])
            if items:
                for i, item in enumerate(items):
                    row = {col: "" for col in all_columns}
                    if i == 0:
                        row.update({
                            "Contract Number": wo.get("Contract Number", ""),
                            "Sub-Contract Number": wo.get("Sub-Contract Number", ""),
                            "Vendor Name": wo.get("Vendor", ""),
                            "Location": wo.get("Location", ""),
                            "Contract Date": wo.get("Contract Date", ""),
                            "Contract Value": format_indian_currency(wo.get("Contract Value", 0.0)),
                            "GST": f"{wo.get('GST (%)', 0.0):.2f}%",
                            "Total Contract Value (with GST)": format_indian_currency(wo.get("Total Contract Value (with GST)", 0.0)),
                            "Work-Order Number": wo.get("Work-Order Number", ""),
                            "% Work-Order": f"{wo.get('% Work-Order', 0.0):.2f}%",
                            "Work-Order Value (Basic)": format_indian_currency(wo.get("Work-Order Value (Basic)", 0.0)),
                            "Work-Order Value (with GST)": format_indian_currency(wo.get("Work-Order Value (with GST)", 0.0)),
                            "Item(s) Count": wo.get("Item(s) Count", 0),
                            "Ageing": ageing,
                        })
                        
                    row.update({
                        "Item Sl. No.": item.get("Item Sl. No.", ""),
                        "Item Name": item.get("Item Name", ""),
                        "Item Location": item.get("Item Location", ""),
                        "Category": item.get("Category", ""),
                        "Qty": item.get("Qty", 0),
                        "Value per Item": format_indian_currency(item.get("Value per Item", 0)),
                        "₹ without GST": format_indian_currency(item.get("₹ without GST", 0)),
                        "₹ with GST": format_indian_currency(item.get("₹ with GST", 0)),
                        "Remark": item.get("Remark", ""),
                    })
                    
                    # Category extras if present
                    for ec in extra_cols:
                        if ec in item:
                            if "Rate" in ec or "Total" in ec or "₹" in ec:
                                row[ec] = format_indian_currency(item.get(ec, 0.0))
                            else:
                                row[ec] = item.get(ec, "")
                    wo_detailed_rows.append(row)

            else:
                row = {col: "" for col in all_columns}
                row.update({
                    "Contract Number": wo.get("Contract Number", ""),
                    "Sub-Contract Number": wo.get("Sub-Contract Number", ""),
                    "Vendor Name": wo.get("Vendor", ""),
                    "Location": wo.get("Location", ""),
                    "Contract Date": wo.get("Contract Date", ""),
                    "Contract Value": format_indian_currency(wo.get("Contract Value", 0.0)),
                    "Total Contract Value (with GST)": format_indian_currency(wo.get("Total Contract Value (with GST)", 0.0)),
                    "Work-Order Number": wo.get("Work-Order Number", ""),
                    "% Work-Order": f"{wo.get('% Work-Order', 0.0):.2f}%",
                    "Work-Order Value (Basic)": format_indian_currency(wo.get("Work-Order Value (Basic)", 0.0)),
                    "Work-Order Value (with GST)": format_indian_currency(wo.get("Work-Order Value (with GST)", 0.0)),
                    "Item(s) Count": wo.get("Item(s) Count", 0),
                    "Item Sl. No.": "",
                    "Item Name": "",
                    "Item Location": "",
                    "Category": "",
                    "Qty": 0,
                    "Value per Item": "",
                    "₹ without GST": "",
                    "GST": f"{gst_value:.2f}%",
                    "₹ with GST": "",
                    "Ageing": ageing
                })
                wo_detailed_rows.append(row)

        if wo_detailed_rows:
            df_wo_detailed = pd.DataFrame(wo_detailed_rows)[all_columns]
            df_wo_detailed_with_fy = add_financial_year_columns(df_wo_detailed)
            st.dataframe(style_alternate_rows(df_wo_detailed_with_fy), use_container_width=True, hide_index=True)

            unique_contracts = len(st.session_state['work_orders'])
            total_contract_value_sum = sum([wo.get("Contract Value", 0) for wo in st.session_state['work_orders']])
            total_value_with_gst_sum = sum([wo.get("Contract Value", 0) * (1 + wo.get("GST (%)", 0) / 100) for wo in st.session_state['work_orders']])
            total_items = sum([wo.get("Item(s) Count", 0) for wo in st.session_state['work_orders']])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Work Orders", unique_contracts)
            with col2:
                st.metric("Total Contract Value", format_indian_currency(total_contract_value_sum))
            with col3:
                st.metric("Total Value with GST", format_indian_currency(total_value_with_gst_sum))
            with col4:
                st.metric("Total Items", int(total_items))


# --------- NEW INVOICE ---------
with tabs[2]:
    st.markdown("#### Add Invoice(s)")
    if not st.session_state.get('work_orders'):
        st.warning("⚠️ **No Work Orders Available.** Please create a work order first. Invoices can only be created for items that exist in work orders.")

    invoice_uploaded_proof = st.file_uploader(
        "Upload **Proof** of Invoice",
        type=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
        key="invoice_uploaded_proof"
    )

    # Row 1
    r1col1, r1col2, r1col3 = st.columns(3)
    invoice_no = r1col1.text_input("Invoice Number", key="main_invoice_no")
    invoice_date = r1col2.date_input("Date of Invoice", value=date.today(), format="DD/MM/YYYY", key="main_invoice_date")
    invoice_location = r1col3.text_input("Invoice Location", key="invoice_location")

    # Row 2
    r2col1, r2col2, r2col3, r2col4 = st.columns([3, 1.5, 1.5, 3])
    all_contract_numbers = [wo.get("Contract Number", "") for wo in st.session_state["work_orders"]]
    contract_numbers = list(dict.fromkeys(all_contract_numbers))
    contract_no = r2col1.selectbox("Contract Number", options=contract_numbers, key="main_contract_no")
    selected_contract = next((wo for wo in st.session_state["work_orders"] if wo.get("Contract Number") == contract_no), None)
    

    vendor = r2col2.text_input("Vendor", value=selected_contract.get('Vendor', '') if selected_contract else '', key="wo_vendor_display", disabled=True)
    locate = r2col3.text_input("Contract Location", value=selected_contract.get('Location', '') if selected_contract else '', key="wo_location_display", disabled=True)
    contract_date_display = r2col4.text_input("Contract Date", value=selected_contract.get('Contract Date', '') if selected_contract else '', key="wo_contract_date_display", disabled=True)

    # Row 3
    r3col1, r3col2, r3col3, r3col4 = st.columns([3, 1.5, 1.5, 3])
    wo_numbers = [
        wo.get("Work-Order Number", "")
        for wo in st.session_state['work_orders']
        if wo.get('Contract Number') == contract_no
    ]
    
    selected_wonum = r3col1.selectbox("Work-Order Number", options=[""] + wo_numbers, key="main_workorder_no")

    wo_entry = next((
        wo for wo in st.session_state['work_orders']
        if wo.get('Contract Number') == contract_no and wo.get('Work-Order Number') == selected_wonum
    ), None) if (contract_no and selected_wonum) else None

    pct_wo = float(wo_entry.get("% Work-Order", 0.0) if wo_entry else 0.0)
    val_wo_basic = float(wo_entry.get("Work-Order Value (Basic)", 0.0) if wo_entry else 0.0)
    val_wo_gst = float(wo_entry.get("Work-Order Value (with GST)", 0.0) if wo_entry else 0.0)

    r3col2.text_input("% Work-Order", value=f"{pct_wo:.2f}%", key="wo_pct_display")
    r3col3.text_input("Work-Order Value Basic (₹)", value=val_wo_basic, key="wo_val_basic_display")
    r3col3.caption(f"With GST: {format_indian_currency(val_wo_gst)}")
    
    admissible_amount = r3col4.number_input("Admissible Amount (₹)", min_value=1.00, step=1.0, format="%.4f", key="main_admissible_amount")
    admissible = float(admissible_amount or 0.0)    

    # Row 4:
    r4col1, r4col2, r4col3 = st.columns(3)
    subcontract_numbers = [
        wo.get("Sub-Contract Number", "")
        for wo in st.session_state["work_orders"]
        if wo.get("Contract Number") == contract_no and wo.get("Work-Order Number") == selected_wonum
    ] if (contract_no and selected_wonum) else []
    subcontract_no = r4col1.selectbox("Sub-Contract Number", options=[""] + subcontract_numbers, key="main_subcontract_no")

    actual_contract_value = float(selected_contract.get('Contract Value', 0.0) if selected_contract else 0.0)
    actual_contract_value_gst = float(selected_contract.get('Total Contract Value (with GST)', 0.0) if selected_contract else 0.0)

    contract_value = r4col2.text_input("Total Contract Value (₹)", value=float(actual_contract_value), key="wo_contract_value_display")
    r4col2.caption(f"With GST: {format_indian_currency(float(actual_contract_value_gst))}")
    invoice_value = r4col3.number_input("Invoice Value (₹)", min_value=0.0, step=1.0000, format="%.4f", key="main_invoice_value")

    available_items = []
    if contract_no and selected_wonum and subcontract_no:
        wo_items_entry = next((
            wo for wo in st.session_state['work_orders']
            if wo.get('Contract Number') == contract_no
            and wo.get('Work-Order Number') == selected_wonum
            and wo.get('Sub-Contract Number') == subcontract_no
        ), None)
        available_items = wo_items_entry.get('Items', []) if wo_items_entry else []
    

    # Row 5: quantity, value per item, GST
    r5col1, r5col2, r5col3, r5col4 = st.columns([3, 1.5, 1.5, 3])
    item_names = [item.get('Item Name', '') for item in available_items]
    item_name = r5col1.selectbox("Item Name", options=[""] + item_names, key="main_item_name")

    selected_item = next((it for it in available_items if it.get('Item Name','') == item_name), None) if item_name else None
    derived_category = (selected_item or {}).get('Category', '')
    derived_item_location = (selected_item or {}).get('Item Location', '')
    r5col2.text_input("Category", value=derived_category, key="wo_category_display", disabled=True)
    r5col3.text_input("Item Location", value=derived_item_location, key="wo_item_location_display", disabled=True)

    tax = r5col4.number_input("Invoice GST (%)", min_value=0.00, max_value=100.00, step=5.00, key="main_tax")
    
    admissible_gst = admissible * (1 + (tax/100))
    if admissible > actual_contract_value:
        r3col4.caption(f"⚠️ Exceeds Contract Value {format_indian_currency(actual_contract_value)}")
    elif admissible > val_wo_basic:
        r3col4.caption(f"⚠️ Exceeds Work-Order Value {format_indian_currency(val_wo_basic)}")
    else:
        r3col4.caption(f"With GST: {format_indian_currency(float(admissible_gst))}")

    # Row 6
    r6col1, r6col2, r6col3 = st.columns(3)
    derived_max_qty = int((selected_item or {}).get('Qty', 0) or 0)
    derived_unit_value = float((selected_item or {}).get('Value per Item', 0.0) or 0.0)

    if selected_item and derived_max_qty > 0:
        quantity = r6col1.selectbox("Quantity", options=list(range(1, derived_max_qty + 1)), key="main_quantity")
    else:
        quantity = r6col1.number_input("Quantity", min_value=1, value=1, disabled=True, key="main_quantity")
        if not selected_item:
            r6col1.caption("Select an item to enable quantity selection")
            
    r6col2.number_input("Item Value (₹)", value=float(derived_unit_value * quantity), format="%.4f", key="wo_item_value_displayed")
    r6col2.caption(f"Value per Item: {format_indian_currency(derived_unit_value)}")
       
    if invoice_value > 0 and actual_contract_value > 0 and admissible > 0:
            if invoice_value > actual_contract_value:
                r6col3.error(f"⚠️ Invoice Value Exceeds **Contract Value** ")
            elif invoice_value > admissible:
                r6col3.warning(f"⚠️ Invoice Value Exceeds **Admissible Value**")
            else: 
                r6col3.markdown(f"Total Invoice Value (with GST): **{format_indian_currency(invoice_value * (1 + tax/100))}**")
    
    # actual values for processing
    actual_vendor = selected_contract.get('Vendor', '') if selected_contract else ''
    actual_location = selected_contract.get('Location', '') if selected_contract else ''
    actual_category = derived_category or (selected_contract.get('Category', '') if selected_contract else '')
    actual_contract_value_num = actual_contract_value


    # PROCESS TRACKING - Only show when category is selected
    category_info = {
        "Hardware": {"color": "#9333ea", "has_warranty": True},
        "Hardware (+ AMC)": {"color": "#f6ff00", "has_amc_warranty": True},
        "AMC": {"color": "#9aea61", "has_amc": True},
        "Solution and Support": {"color": "#f59e0b", "has_solution": True},
        "Software": {"color": "#3b5af6", "has_software": True},
        "Telecom": {"color": "#63f1ef", "has_telecom": True},
        "Staff Cost": {"color": "#e11d48", "has_staffcost": True},
        "Others": {"color": "#636262", "has_others": True}
    }
    
    info = category_info.get(actual_category, category_info["Others"])
    has_amc = info.get("has_amc", False)
    has_warranty = info.get("has_warranty", False)
    has_amc_warranty = info.get("has_amc_warranty", False)
    has_software = info.get("has_software", False)
    has_staffcost = info.get("has_staffcost", False)
    has_telecom = info.get("has_telecom", False)
    has_solution = info.get("has_solution", False)
    has_others = info.get("has_others", False)

    if actual_category:
        st.markdown("---")
        st.markdown("#### Process Tracking")

        st.markdown(f"""
        <div style="background: {info['color']}15; border-left: 4px solid {info['color']}; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
        <strong>{actual_category} Category Selected</strong><br>
        </div>""", unsafe_allow_html=True)        


        # Warranty
        if has_warranty:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Payment Milestones")
                
            with col2:
                st.markdown("###### Warranty Payment Distribution")

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                delivery_percentage = st.number_input(
                    "Delivery (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=40.0,
                    step=1.0,
                    format="%.1f",
                    key="delivery_percentage",
                )
                delivery_amount = (admissible * delivery_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(delivery_amount)}")
            
            with col2:
                uat_submission_percentage = st.number_input(
                    "Power ON / UAT Submission % ",
                    min_value=0.0,
                    max_value=100.0,
                    value=20.0,
                    step=1.0,
                    format="%.1f",
                    key="uat_submission_percentage",
                )
                uat_submission_amount = (admissible * uat_submission_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(uat_submission_amount)}")
            
            with col3:
                uat_percentage = st.number_input(
                    "UAT Completion (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=25.0,
                    step=1.0,
                    format="%.1f",
                    key="uat_percentage",
                )
                uat_amount = (admissible * uat_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(uat_amount)}")
            
            with col4:
                warranty_percentage = st.number_input(
                    "Warranty (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=15.0,
                    step=1.0,
                    format="%.1f",
                    key="warranty_percentage",
                )
                warranty_amount = (admissible * warranty_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(warranty_amount)}")

            
            with col5:
                default_warranty_m = int((selected_item or {}).get('Warranty Duration (Months)', 12) or 12)
                warranty_duration = st.number_input(
                    "Warranty Duration (Months)",
                    min_value=1, value=default_warranty_m, step=1, key="warranty_duration"
                )
                warranty_years = (warranty_duration / 12)
                st.caption(f"{warranty_years:.2f} Years")                
                

            with col6:
                warranty_period = st.selectbox(
                    "Warranty Claiming Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key=f"warranty_period"
                )

            with col1:
            # Validate total percentage
                total_milestone_percentage = delivery_percentage + uat_submission_percentage + uat_percentage + warranty_percentage
                if abs(total_milestone_percentage - 100.0) > 0.1:
                    st.warning(f"⚠️ **Total Milestone Percentage** = {total_milestone_percentage:.1f}% (Should be 100%)")
                else:
                    st.markdown(f"**Total Milestone** = {total_milestone_percentage:.2f}%")
        
        # AMC Category
        elif has_amc:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                amc_percentage = st.number_input(
                    "AMC (%)",
                    min_value=0.0, max_value=100.0, value=40.0, step=1.0, format="%.1f",
                    key="amc_percentage",
                )
                st.caption(f"Amount:{admissible * (amc_percentage/100)} | With GST:{(admissible * (amc_percentage/100) * (1 + (tax/100)))}")

            with col2:
                default_amc_m = int((selected_item or {}).get('AMC Duration (Months)', 12) or 12)
                amc_duration = st.number_input(
                    "AMC Duration (Months)", min_value=1, value=default_amc_m, step=1, key="amc_duration"
                )
                st.caption(f"{(amc_duration / 12):.2f} Years")
            
            with col3:
                amc_period = st.selectbox(
                    "AMC Claiming Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key=f"amc_period"
                )
                if amc_period == "Annually":
                    st.caption(f"Amount per Year: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 12) if admissible > 0 else 0)}")
                elif amc_period == "Half Yearly":
                    st.caption(f"Amount per Half Year: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 6) if admissible > 0 else 0)}")
                elif amc_period == "Quarterly":
                    st.caption(f"Amount per Quarter: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 3) if admissible > 0 else 0)}")
                elif amc_period == "Monthly":
                    st.caption(f"Amount per Month: {format_indian_currency((admissible * amc_percentage/100) / amc_duration if admissible > 0 else 0)}")

            with col4:
                amc_start_date = st.date_input(
                        "AMC Start Date",
                        value=date.today(),
                        format="DD/MM/YYYY",
                        key="amc_start_date",
                    )

            with col5:
                def build_starting_options(period: str, start_d: date, months: int):
                    months = max(1, int(months))
                    out = []
                    if period == "Annually":
                        years = ceil(months / 12)
                        for i in range(years):
                            out.append(f"Year {i+1} ({start_d.year + i})")
                    elif period == "Half Yearly":
                        halfs = ceil(months / 6)
                        for i in range(halfs):
                            out.append(f"H{i+1} {start_d.year + (i//2)}")
                    elif period == "Quarterly":
                        quarters = ceil(months / 3)
                        for i in range(quarters):
                            out.append(f"Q{i+1}")
                            
                    else:
                        for i in range(months):
                            out.append(f"Month {i+1}")
                    return out

                starting_options = build_starting_options(amc_period, amc_start_date, int(amc_duration))
                if not starting_options:
                    starting_options = ["Start"]
                starting_label = st.selectbox(
                    f"Select Starting {amc_period.split()[0]}",
                    options=starting_options,
                    index=0,
                    key="amc_starting_label",
                )
                st.caption(f"Payments will be made {amc_period} starting from {starting_label}") 

        # Warranty + AMC
        elif has_amc_warranty:
            col1, col2, col3 = st.columns([2, 2, 4])
            with col1:
                st.markdown("###### Payment Milestones")
                
            with col2:
                st.markdown("###### Warranty Payment Distribution")
            
            with col3:
                st.markdown("###### AMC Payment Distribution")

            pm1, wp2, ap3, ap4 = st.columns([2, 2, 2, 2])
            
            with pm1:
                delivery_percentage = st.number_input(
                    "Delivery (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=40.0,
                    step=1.0,
                    format="%.1f",
                    key="delivery_percentage",
                )
                delivery_amount = (admissible * delivery_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(delivery_amount)}")
            
                uat_submission_percentage = st.number_input(
                    "Power ON / UAT Submission % ",
                    min_value=0.0,
                    max_value=100.0,
                    value=20.0,
                    step=1.0,
                    format="%.1f",
                    key="uat_submission_percentage",
                )
                uat_submission_amount = (admissible * uat_submission_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(uat_submission_amount)}")
            
                uat_percentage = st.number_input(
                    "UAT Completion (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=25.0,
                    step=1.0,
                    format="%.1f",
                    key="uat_percentage",
                )
                uat_amount = (admissible * uat_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(uat_amount)}")
            
            with wp2:
                warranty_percentage = st.number_input(
                    "Warranty (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=15.0,
                    step=1.0,
                    format="%.1f",
                    key="warranty_percentage",
                )
                warranty_amount = (admissible * warranty_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(warranty_amount)}")

            
                default_warranty_m = int((selected_item or {}).get('Warranty Duration (Months)', 12) or 12)
                warranty_duration = st.number_input(
                    "Warranty Duration (Months)",
                    min_value=1, value=default_warranty_m, step=1, key="warranty_duration"
                )
                warranty_years = (warranty_duration / 12)
                st.caption(f"{warranty_years:.2f} Years")                
                

                warranty_period = st.selectbox(
                    "Warranty Claiming Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key=f"warranty_period"
                )

            with ap3:
                amc_percentage = st.number_input(
                    "AMC (%)",
                    min_value=0.0, max_value=100.0, value=40.0, step=1.0, format="%.1f",
                    key="amc_percentage",
                )
                amc_amount = admissible * (amc_percentage/100)
                st.caption(f"Amount:{amc_amount} | With GST:{( amc_amount * (1 + (tax/100)))}")


                default_amc_m = int((selected_item or {}).get('AMC Duration (Months)', 12) or 12)
                amc_duration = st.number_input(
                    "AMC Duration (Months)", min_value=1, value=default_amc_m, step=1, key="amc_duration"
                )
                st.caption(f"{(amc_duration / 12):.2f} Years")

                amc_period = st.selectbox(
                    "AMC Claiming Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key=f"amc_period"
                )
                if amc_period == "Annually":
                    st.caption(f"Amount per Year: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 12) if admissible > 0 else 0)}")
                elif amc_period == "Half Yearly":
                    st.caption(f"Amount per Half Year: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 6) if admissible > 0 else 0)}")
                elif amc_period == "Quarterly":
                    st.caption(f"Amount per Quarter: {format_indian_currency((admissible * amc_percentage/100) / (amc_duration / 3) if admissible > 0 else 0)}")
                elif amc_period == "Monthly":
                    st.caption(f"Amount per Month: {format_indian_currency((admissible * amc_percentage/100) / amc_duration if admissible > 0 else 0)}") 

            with ap4:
                amc_start_date = st.date_input(
                        "AMC Start Date",
                        value=date.today(),
                        format="DD/MM/YYYY",
                        key="amc_start_date",
                )
                st.caption("")
                st.caption("")

                def build_starting_options(period: str, start_d: date, months: int):
                    months = max(1, int(months))
                    out = []
                    if period == "Annually":
                        years = ceil(months / 12)
                        for i in range(years):
                            out.append(f"Year {i+1} ({start_d.year + i})")
                    elif period == "Half Yearly":
                        halfs = ceil(months / 6)
                        for i in range(halfs):
                            out.append(f"H{i+1} {start_d.year + (i//2)}")
                    elif period == "Quarterly":
                        quarters = ceil(months / 3)
                        for i in range(quarters):
                            out.append(f"Q{i+1}")
                            
                    else:
                        for i in range(months):
                            out.append(f"Month {i+1}")
                    return out

                starting_options = build_starting_options(amc_period, amc_start_date, int(amc_duration))
                if not starting_options:
                    starting_options = ["Start"]
                starting_label = st.selectbox(
                    f"Select Starting {amc_period.split()[0]}",
                    options=starting_options,
                    index=0,
                    key="amc_starting_label",
                )
                st.caption(f"Payments will be made {amc_period} starting from {starting_label}") 
                
        # Software Category
        elif has_software:    
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Payment Milestones")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                delivery_percentage = st.number_input(
                    "Delivery (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=70.0,
                    step=1.0,
                    format="%.2f",
                    key="main_delivery_percentage",
                )
                delivery_amount = (admissible * delivery_percentage / 100) if admissible > 0 else 0
                st.caption(f"Amount: {format_indian_currency(delivery_amount)}")
            
            with col2:
                software_duration = st.number_input("Software Duration (Months)", min_value=1, step=1, value=12, key="main_software_duration")

                software_years = float(software_duration / 12)
                st.caption(f"{software_years:.2f} Years")

            with col3:
                software_support_percentage = st.number_input(
                    "Support Percentage (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=30.0,
                    format="%.2f",
                    step=1.00,
                    key="main_software_support_percentage",
                )

                software_support_amount = ((admissible * software_support_percentage) / 100) if admissible > 0 else 0 
                yearly_support_percentage = (software_support_percentage / software_years) if software_duration > 0 else 0
                yearly_support_amount = (software_support_amount / software_years) if software_duration > 0 else 0
                st.caption(f"**Total** = {format_indian_currency(software_support_amount)}")

            col1, col2 = st.columns([3.5, 2.33])
            with col1:
                total_percentage = delivery_percentage + software_support_percentage
                if abs(total_percentage - 100.0) > 0.1:
                    st.warning(f"⚠️ **Total Milestone Percentage** = {total_percentage:.1f}% (Should be 100%)")
                else:
                    st.markdown(f"**Total Milestone** = {total_percentage:.2f}%")
        
        elif has_solution:
            st.markdown("###### Payment Milestones")
            col1, col2 = st.columns(2)
            with col1:
                if "sol_custom_count" not in st.session_state:
                    st.session_state["sol_custom_count"] = 2
                sol_count = st.number_input(
                    "Number of Milestones",
                    min_value=1, max_value=10, step=1,
                    value=st.session_state["sol_custom_count"],
                    key="main_sol_custom_count",
                )
                st.session_state["sol_custom_count"] = int(sol_count)

            total_percentage = 0.0
            sol_rows = []

            for i in range(1, int(sol_count) + 1):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    pct_key = f"main_custom_percentage_{i}"
                    pct = st.number_input(
                        f"({i}) Support %",
                        min_value=0.0, max_value=100.0, step=1.0, format="%.2f",
                        key=pct_key,
                        value=st.session_state.get(pct_key, 0.0),
                    )
                    row_amount = (admissible or 0.0) * (pct / 100.0)
                    st.caption(f"Amount: {format_indian_currency(row_amount)}")
                    total_percentage += pct

                with col2:
                    start_key = f"main_solution_support_start_{i}"
                    sol_sup_start = st.date_input(
                        "Support Start Date",
                        value=date.today(),
                        format="DD/MM/YYYY",
                        key=start_key,
                    )
                
                with col3:
                    sol_period_key = f"main_solution_support_period_{i}"
                    sol_sup_period = st.selectbox(
                        "Support Period",
                        options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                        index=0,
                        key=sol_period_key,
                    )
                with col4:
                    sol_duration_key = f"main_solution_support_duration_{i}"
                    sol_sup_duration = st.number_input(
                        "Support Duration (Months)",
                        min_value=1, value=12, step=1,
                        key=sol_duration_key,
                    )
                    sol_sup_years = (sol_sup_duration / 12)
                    st.caption(f"{sol_sup_years:.2f} Years")
                
                sol_rows.append({
                    "idx": i,
                    "percentage": pct,
                    "amount": row_amount,
                    "period": sol_sup_period,
                    "start_date": sol_sup_start,
                    "duration": sol_sup_duration,
                })

            # Validation 
            col1, col2 = st.columns([3.5, 2.33])
            with col1:
                if abs(total_percentage - 100.0) > 0.1:
                    st.warning(f"⚠️**Total Milestone Percentage** = {total_percentage:.1f}% (Should be 100%)")
                else:
                    st.markdown(f"**Total Milestone** = {total_percentage:.2f}%")

            st.session_state["sol_custom_total"] = total_percentage
            st.session_state["sol_support_rows"] = sol_rows
            

        elif has_staffcost:
            st.markdown("##### Milestones")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                staff_duration = st.number_input(
                    "Staff Duration (Months)",
                    min_value=1, value=12, step=1,
                    key="main_staff_duration",
                )
                try:
                    staff_duration = int(staff_duration)
                except (TypeError, ValueError):
                    staff_duration = 12
                if staff_duration < 1:
                    staff_duration = 1
                staff_duration_years = max(1, int(round(staff_duration / 12.0)))
                
            with col2:
                staff_start = st.date_input(
                    "Staff Date",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key="main_staff_start_date",
                )
                
            with col3:
                staff_period = st.selectbox(
                    "Staff Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key="main_staff_period",
                )
            
            period_to_n = {"Monthly": 12, "Quarterly": 4, "Half Yearly": 2, "Annually": 1}
            installs_per_year = int(period_to_n.get(staff_period, 4))
            total_installs = int(installs_per_year * staff_duration_years)
            per_install_amount = (float(admissible or 0.0) / total_installs) if total_installs > 0 else 0.0
            total_install_amount = per_install_amount * total_installs
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.caption(f"Installments/year: {installs_per_year}")
            with c2:
                st.caption(f"Total installments: {total_installs}")
            with c3:
                st.caption(f"Per installment: {format_indian_currency(per_install_amount)}")
            with c4:
                st.caption(f"Total Amount: {format_indian_currency(total_install_amount)}")

            def generate_installment_labels(period: str, years: int):
                period = period or "Quarterly"
                try:
                    years = int(years)
                except (TypeError, ValueError):
                    years = 1
                if years < 1:
                    years = 1
                    
                if period == "Monthly":
                    return [f"Month {i}" for i in range(1, 12 * years + 1)]
                elif period == "Quarterly":
                    labels = []
                    for y in range(1, years + 1):
                        for q in ["Q1", "Q2", "Q3", "Q4"]:
                            labels.append(f"{q} Year {y}")
                    return labels
                elif period == "Half Yearly":
                    return [f"H1 Year {y}" for y in range(1, years + 1)] + \
                        [f"H2 Year {y}" for y in range(1, years + 1)]
                else:
                    return [f"Year {y}" for y in range(1, years + 1)]
                
            staff_installment_labels = generate_installment_labels(staff_period, staff_duration_years)
            st.session_state["main_staff_installments_per_year"] = installs_per_year
            st.session_state["main_staff_total_installments"] = total_installs
            st.session_state["main_staff_amount_per_installment"] = float(per_install_amount)
            st.session_state["main_staff_installment_labels"] = staff_installment_labels
    
        # Telecom
        elif has_telecom:
            st.markdown("##### Billing Milestones")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                telecom_duration = st.number_input(
                    "Telecom Duration (Months)",
                    min_value=1, max_value=120, value=12, step=1,
                    key="main_telecom_duration",
                )
                try:
                    telecom_duration = int(telecom_duration)
                except (TypeError, ValueError):
                    telecom_duration = 12
                if telecom_duration < 1:
                    telecom_duration = 1

                telecom_years = max(1, int(round(telecom_duration / 12.0)))
                
            with col2:
                tel_start = st.date_input(
                    "Billing Start Date",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key="main_telecom_billing_start",
                )
            with col3:
                tel_period = st.selectbox(
                    "Billing Period",
                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                    index=0,
                    key="main_telecom_billing_period",
                )
            
            period_to_n = {"Monthly": 12, "Quarterly": 4, "Half Yearly": 2, "Annually": 1}
            tel_installs_per_year = int(period_to_n.get(tel_period, 4))
            tel_total_installs = int(tel_installs_per_year * telecom_years)
            tel_per_install_amount = (float(admissible or 0.0) / tel_total_installs) if tel_total_installs > 0 else 0.0
            tel_total_install_amount = tel_total_installs * tel_per_install_amount

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.caption(f"Installments/year: {tel_installs_per_year}")
            with c2:
                st.caption(f"Total installments: {tel_total_installs}")
            with c3:
                st.caption(f"Per installment: {format_indian_currency(tel_per_install_amount)}")
                
            st.markdown(f"**Total Amount: {format_indian_currency(tel_total_install_amount)}**")

            def generate_tel_labels(period: str, years: int):
                period = period or "Quarterly"
                try:
                    years = int(years)
                except (TypeError, ValueError):
                    years = 1
                if years < 1:
                    years = 1
                    
                if period == "Monthly":
                    return [f"Month {i}" for i in range(1, 12 * years + 1)]
                if period == "Quarterly":
                    labels = []
                    for y in range(1, years + 1):
                        for q in ["Q1", "Q2", "Q3", "Q4"]:
                            labels.append(f"{q} Year {y}")
                    return labels
                if period == "Half Yearly":
                    return [f"H1 Year {y}" for y in range(1, years + 1)] + \
                        [f"H2 Year {y}" for y in range(1, years + 1)]
                return [f"Year {y}" for y in range(1, years + 1)]
            
            tel_installment_labels = generate_tel_labels(tel_period, telecom_years)
            st.session_state["main_telecom_installs_per_year"] = tel_installs_per_year
            st.session_state["main_telecom_total_installs"] = tel_total_installs
            st.session_state["main_telecom_per_install_amount"] = float(tel_per_install_amount)
            st.session_state["main_telecom_installment_labels"] = tel_installment_labels   

        # Others
        elif has_others:
            st.markdown("##### Custom Milestones")
            if "others_custom_count" not in st.session_state:
                st.session_state.others_custom_count = 1
            MAX_CUSTOM = 10
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.others_custom_count = int(st.number_input(
                "Number of Custom Milestones",
                min_value=1, max_value=MAX_CUSTOM, step=1,
                value=st.session_state.others_custom_count,
                key="main_others_custom_count"
                ))

            total_custom_percentage = 0.0

            for i in range(1, st.session_state.others_custom_count + 1):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    key_percentage = f"main_others_custompercentage_{i}"
                    percentage = st.number_input(
                        f"Custom Milestone {i} (%)",
                        min_value=0.0, max_value=100.0, step=1.0, format="%.2f",
                        key=key_percentage,
                        value=st.session_state.get(key_percentage, 0.0),
                    )
                    amount = (admissible or 0.0) * (percentage / 100.0)
                    st.caption(f"Amount: {format_indian_currency(amount)}")

                with col2:
                    key_remark = f"main_others_customremark_{i}"
                    remark = st.text_input(f"Remark {i}", key=key_remark, value=st.session_state.get(key_remark, ""))              

                total_custom_percentage += percentage

            # Validation 
            st.markdown(f"**Total Custom Percentage:** {total_custom_percentage:.2f}%")
            if abs(total_custom_percentage - 100.0) > 0.1:
                st.warning("Total Custom Percentage should be 100%. Please adjust.")

    else:
        st.info("**Process Tracking will appear here once you select a contract.**")
    

    # Milestone Invoiced submission details 
    if actual_category:
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            submission_date = st.date_input("Date of Invoice SUBMISSION", value=date.today(), format="DD/MM/YYYY", key="main_submission_date")
        
        with col2:
            receive_date = st.date_input("Date of Invoice RECEIVED at TMD", value=date.today(), format="DD/MM/YYYY", key="main_receive_date")
        
        with col3:       
            artifact_date = st.date_input("Complete ARTIFACTS Receiving Date", value=date.today(), format="DD/MM/YYYY", key="main_artifact_date")        
        
        with col4:
            # milestone selection dropdown
            if admissible > 0:
                milestone_options = []
                milestone_amounts = {}

                def add_opt(label: str, amount: float):
                    milestone_options.append(label)
                    milestone_amounts[label] = float(amount or 0.0)

                if has_warranty:
                    add_opt(f"Delivery ({delivery_percentage:.2f}%)", delivery_amount)
                    add_opt(f"Submission for UAT ({uat_submission_percentage:.2f}%)", uat_submission_amount)
                    add_opt(f"UAT Completion ({uat_percentage:.2f}%)", uat_amount)
                    

                    warranty_milestones = generate_warranty_milestones(
                        warranty_period, 
                        warranty_duration, 
                        warranty_percentage,
                        warranty_amount
                    )
                    
                    for milestone_label, milestone_amount in warranty_milestones:
                        add_opt(milestone_label, milestone_amount)

                elif has_amc:                    
                    amc_period = st.session_state.get("amc_period", "Quarterly")
                    amc_duration = st.session_state.get("amc_duration", 12)
                    amc_percentage = st.session_state.get("amc_percentage", 100.0)
                    total_amc_amount = (admissible * amc_percentage / 100) if admissible > 0 else 0

                    amc_milestones = generate_amc_milestones(
                        amc_period,
                        amc_duration,
                        amc_percentage,
                        total_amc_amount,                              
                    )
    
                    for milestone_label, milestone_amount in amc_milestones:
                        add_opt(milestone_label, milestone_amount)

                elif has_amc_warranty:
                    add_opt(f"Delivery ({delivery_percentage:.2f}%)", delivery_amount)
                    add_opt(f"Power ON UAT Submission ({uat_submission_percentage:.2f}%)", uat_submission_amount)
                    add_opt(f"UAT Completion ({uat_percentage:.2f}%)", uat_amount)
    
                    warranty_milestones = generate_warranty_milestones(warranty_period, warranty_duration, warranty_percentage, warranty_amount)
                    for milestone_label, milestone_amount in warranty_milestones:
                        add_opt(milestone_label, milestone_amount)

                    amc_period = st.session_state.get("amc_period", "Quarterly")
                    amc_duration = st.session_state.get("amc_duration", 12)
                    amc_percentage = st.session_state.get("amc_percentage", 100.0)
    
                    amc_milestones = generate_amc_milestones(amc_period, amc_duration, amc_percentage, amc_amount)
                    for milestone_label, milestone_amount in amc_milestones:
                        add_opt(milestone_label, milestone_amount)

    
                elif has_software:
                    if software_years == 1:
                        add_opt(f"Downpayment ({total_percentage:.2f}%)", (delivery_amount + software_support_amount))
                    else:
                        first_percentage = (delivery_percentage + yearly_support_percentage)
                        first_amount = (delivery_amount + yearly_support_amount)
                                                
                        add_opt(f"Delivery + Support Year 1 ({first_percentage:.2f}%)", first_amount)
                        for year in range(2, int(software_years) + 1):
                            add_opt(f"Support Year {year} ({yearly_support_percentage:.2f}%)", yearly_support_amount)

                elif has_solution:
                    def generate_solution_milestones(sol_rows):
                        milestones = []
            
                        for row in sol_rows:
                            try:
                                idx = row.get("idx", 1)
                                percentage = float(row.get("percentage", 0.0))
                                amount = float(row.get("amount", 0.0))
                                period = row.get("period", "Annually")
                                duration = int(row.get("duration", 12))
                                start_date = row.get("start_date")
                                period_to_n = {"Monthly": 12, "Quarterly": 4, "Half Yearly": 2, "Annually": 1}
                                periods_per_year = period_to_n.get(period, 1)
                                total_years = duration / 12
                                total_periods = int(periods_per_year * total_years)
                            
                                if total_periods <= 1:
                                    start_txt = start_date.strftime("%d-%m-%Y") if start_date else ""
                                    lbl = f"Support {idx} ({percentage:.2f}%) — {period}"
                                    if start_txt:
                                        lbl += f" (Start: {start_txt})"
                                    milestones.append((lbl, amount))
                                else:
                                    amount_per_period = amount / total_periods
                                    percentage_per_period = percentage / total_periods
                        
                                    if period == "Monthly":
                                        for month in range(1, total_periods + 1):
                                            year = ((month - 1) // 12) + 1
                                            month_in_year = ((month - 1) % 12) + 1
                                            lbl = f"Support {idx} Month {month} (Year {year}, M{month_in_year}) ({percentage_per_period:.2f}%)"
                                            milestones.append((lbl, amount_per_period))
                        
                                    elif period == "Quarterly":
                                        for quarter in range(1, total_periods + 1):
                                            year = ((quarter - 1) // 4) + 1
                                            q_in_year = ((quarter - 1) % 4) + 1
                                            lbl = f"Support {idx} Q{q_in_year} Year {year} ({percentage_per_period:.2f}%)"
                                            milestones.append((lbl, amount_per_period))
                        
                                    elif period == "Half Yearly":
                                        for half in range(1, total_periods + 1):
                                            half_index = half - 1 
                                            year = (half_index // 2) + 1 
                                            h_in_year = (half_index % 2) + 1
                                            lbl = f"Support {idx} H{h_in_year} Year {year} ({percentage_per_period:.2f}%)"
                                            milestones.append((lbl, amount_per_period))
                        
                                    else:  # Annually
                                        for year in range(1, total_periods + 1):
                                            lbl = f"Support {idx} Year {year} ({percentage_per_period:.2f}%)"
                                            milestones.append((lbl, amount_per_period))

                            except (TypeError, ValueError, KeyError):
                                lbl = f"Support {row.get('idx', 1)} ({row.get('percentage', 0.0):.2f}%)"
                                milestones.append((lbl, row.get("amount", 0.0)))     

                        return milestones
                    try:
                        rows = st.session_state.get("sol_support_rows", [])
            
                        solution_milestones = generate_solution_milestones(rows)
                        for milestone_label, milestone_amount in solution_milestones:
                            add_opt(milestone_label, milestone_amount)
                
                    except Exception:
                        rows = st.session_state.get("sol_support_rows", [])
                        for r in rows:
                            start_txt = r["start_date"].strftime("%d-%m-%Y") if r.get("start_date") else ""
                            lbl = f"Support {r['idx']} ({r['percentage']:.2f}%) — {r['period']}"
                            if start_txt:
                                lbl += f" (Start: {start_txt})"
                            add_opt(lbl, r["amount"])                    

                elif has_staffcost:
                    labels = st.session_state.get("main_staff_installment_labels", [])
                    per_install = float(st.session_state.get("main_staff_amount_per_installment", 0.0))
                    for lbl in labels:
                        add_opt(lbl, per_install)

                elif has_telecom:
                    labels = st.session_state.get("main_telecom_installment_labels", [])
                    per_install = float(st.session_state.get("main_telecom_per_install_amount", 0.0))
                    for lbl in labels:
                        add_opt(lbl, per_install)

                elif has_others:
                    others_custom_count = st.session_state.get("others_custom_count", 1)
                    for i in range(1, others_custom_count + 1):
                        perc_key = f"main_others_custompercentage_{i}"
                        percentage = float(st.session_state.get(perc_key, 0.0))
                        remark = st.session_state.get(f"main_others_customremark_{i}", "")
                        lbl = f"Custom Milestone {i}: {percentage:.2f}%"
                        if remark.strip():
                            lbl += f" ({remark.strip()})"
                        amt = (admissible or 0.0) * (percentage / 100.0)
                        add_opt(lbl, amt)
                

                claimed_milestones = st.multiselect(
                    "Claimed Milestones",
                    options=milestone_options,
                    key="selected_milestones",
                    help="Select one or more milestones for this release order"
                )

                selected_labels = claimed_milestones or []
                plan_amount = float(sum(milestone_amounts.get(lbl, 0.0) for lbl in selected_labels))

                if not selected_labels:
                    milestone_type = ""
                elif len(selected_labels) == 1:
                    milestone_type = selected_labels[0]
                else:
                    milestone_type = f"{len(selected_labels)} Milestones"
                
            else:
                milestone_type = ""
                planned_amount = 0.0


        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            if has_telecom:
                claimed_amount = st.number_input(
                    "Claimed Value (₹)",
                    step=1.0000, 
                    format="%.4f",
                    key="main_claimed_telecom"
                )
                if claimed_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(claimed_amount * (1 + tax/100))}**")

            else:
                planned_amount = st.number_input("PQP/ Planned Claim (₹)", step=1.00, format="%.4f", key="planned_claim")
                if planned_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(planned_amount * (1 + tax/100))}**")
        
        with col2:            
            if has_telecom:
                liquidity_percentage = st.number_input(
                "Liquidity Damage (%)", 
                min_value=0.0,
                max_value=100.0,
                step=0.0000000001, 
                format="%.10f",
                key="main_liquidity_pct_telecom"
            )
                
            else:
                claimed_amount = st.number_input(
                    "Claimed Value (₹)",
                    step=1.0000, 
                    format="%.4f",
                    key="main_claimed"
                )
                if claimed_amount > planned_amount:
                    st.caption(f"⚠️ Exceeds **PQP {format_indian_currency(planned_amount)}**")
                elif claimed_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(claimed_amount * (1 + tax/100))}**")
        
        with col3:
            if has_telecom:
                if liquidity_percentage > 0:
                    liquidity_amount = st.number_input(
                    "LD Amount (₹)",
                    format="%.12f",  
                    key="main_liquidity_amount_telecom"
                    )
                    st.caption(f"With GST: **{format_indian_currency(liquidity_amount * (1 + tax/100))}**")

            else:
                liquidity_percentage = st.number_input(
                    "Liquidity Damage (%)", 
                    min_value=0.0, max_value=100.0,
                    step=0.0000000001, format="%.10f",
                    key="main_liquidity_pct"
                )
                cap1, cap2 = st.columns([1, 1], vertical_alignment="center")
                with cap1:
                    apply_on_pqp = st.checkbox("PQP", key="ld_apply_pqp", help="Apply LD on PQP amount.")
                with cap2:
                    apply_on_claimed = st.checkbox("Claim", key="ld_apply_claimed", help="Apply LD on Claimed amount.")

                prev_pqp = st.session_state.get("_prev_ld_apply_pqp", False)
                prev_claim = st.session_state.get("_prev_ld_apply_claimed", False)
                if apply_on_pqp and apply_on_claimed:
                    if apply_on_pqp != prev_pqp:
                        st.session_state["ld_apply_claimed"] = False
                        apply_on_claimed = False
                    else:
                        st.session_state["ld_apply_pqp"] = False
                        apply_on_pqp = False
                st.session_state["_prev_ld_apply_pqp"] = apply_on_pqp
                st.session_state["_prev_ld_apply_claimed"] = apply_on_claimed

        if not has_telecom:
            with col4:
                if liquidity_percentage > 0:
                    liquidity_amount = st.number_input(
                    "LD Amount (₹)",
                    format="%.12f",  
                    key="main_liquidity_amount"
                    )  
        
        col1, col2, col3, col4 = st.columns(4)  
        with col1:
            if has_telecom and liquidity_percentage > 0:
                payable_amount = st.number_input(
                "Payable Amount", 
                value=float(claimed_amount - liquidity_amount), 
                format="%.10f", 
                key="main_payable"
                )
                if payable_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(payable_amount * (1 + tax/100))}**")
                
            elif not has_telecom and apply_on_claimed and liquidity_percentage > 0:
                payable_claimed = claimed_amount - liquidity_amount
                payable_amount = st.number_input(
                "Payable Amount", 
                value=payable_claimed, 
                format="%.10f", 
                key="main_payable"
                )
                if payable_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                elif payable_amount > planned_amount and payable_amount < admissible:
                    st.caption(f"⚠️ Exceeds **PQP {format_indian_currency(planned_amount)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(payable_amount * (1 + tax/100))}**")

            elif not has_telecom and apply_on_pqp and liquidity_percentage > 0:
                payable_pqp = planned_amount - liquidity_amount
                payable_amount = st.number_input(
                "Payable Amount", 
                value=payable_pqp, 
                format="%.10f", 
                key="main_payable"
                )
                if payable_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                elif payable_amount > planned_amount and payable_amount < admissible:
                    st.caption(f"⚠️ Exceeds **PQP {format_indian_currency(planned_amount)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(payable_amount * (1 + tax/100))}**")
            
            else:
                payable_amount = st.number_input(
                    "Payable Amount", 
                    value=0.0, step=1.0, format="%.10f",
                    key="main_payable_default"
                )
                if payable_amount > admissible:
                    st.caption(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
                elif not has_telecom and payable_amount > planned_amount and payable_amount < admissible:
                    st.caption(f"⚠️ Exceeds **PQP {format_indian_currency(planned_amount)}**")
                else:
                    st.caption(f"With GST: **{format_indian_currency(payable_amount * (1 + tax/100))}**")

        with col2:
            ro_number = st.text_input("Release Order Number", value="", key="main_ro_number")               

        with col3:
            ro_amount = st.number_input(
                "Release Order Amount", 
                format="%.10f", 
                step=1.00,
                key="main_ro_amount"
            )
            if ro_amount > payable_amount and ro_amount < admissible:
                st.caption("⚠️ Cannot exceed Payable Amount")
            elif not has_telecom and ro_amount < admissible and ro_amount > planned_amount:
                st.caption(f"⚠️ Exceeds **PQP {format_indian_currency(planned_amount)}**")
            elif not has_telecom and ro_amount < planned_amount and ro_amount > payable_amount:
                st.caption("⚠️ Cannot exceed Payable Amount")
            elif ro_amount > admissible:
                st.error(f"⚠️ Exceeds **Admissible {format_indian_currency(admissible)}**")
            else:
                st.caption(f"With GST: **{format_indian_currency(ro_amount * (1 + tax/100))}**")   
            
        with col4:
            ro_date = st.date_input("Date of RELEASE ORDER", value=None, format="DD/MM/YYYY", key="main_ro_date")
        
        rdcol1, rdcol2, rdcol3, rdcol4 = st.columns(4)
        with rdcol3:
            damage_reason = ""
            if liquidity_percentage > 0:
                damage_reason = st.text_input("**Reason** for Liquidity Damage", key="main_damage_reason")
        with rdcol4:
            days_reason = ""
            noOfDays = calculate_days(ro_date.strftime("%d/%m/%Y") if ro_date else None, receive_date.strftime("%d/%m/%Y"))
            if noOfDays is not None:
                if noOfDays > 30:
                    days_reason = st.text_input("**Reason** for Delay", key="main_days_reason")
        
        # Validation and form submission
        col1, col2 = st.columns([2.5, 1.5])
        with col1:
            invoice_uploaded_proof = st.session_state.get('invoice_uploaded_proof', None)
            invoice_no = st.session_state.get('main_invoice_no', '')
            invoice_date = st.session_state.get('main_invoice_date', None)
            invoice_location = st.session_state.get('invoice_location', '')
            contract_no = st.session_state.get('main_contract_no', '')
            work_order_no = st.session_state.get('main_workorder_no', '')
            sub_contract_no = st.session_state.get('main_subcontract_no', '')
            invoice_value = st.session_state.get('main_invoice_value', 0.0)
            item_name = st.session_state.get('main_item_name', '')
            quantity = st.session_state.get('main_quantity', 0.0)
            gst = st.session_state.get('main_gst', 0.0)
            claimed_milestones = st.session_state.get('selected_milestones', [])
    
            # Conditional fields
            planned_amount = st.session_state.get('planned_claim', 0.0) if not has_telecom else 0.0
            ro_amount = st.session_state.get('main_ro_amount', 0.0)
            liquidity_percentage = st.session_state.get('main_liquidity_pct', 0.0)
            liquidity_amount = st.session_state.get('main_liquidity_amount', 0.0)
            damage_reason = st.session_state.get('main_damage_reason', '') if liquidity_percentage > 0 else ''
            days_reason = st.session_state.get('main_days_reason', '') if noOfDays and noOfDays > 30 else ''
    
            basic_validation = bool(
                invoice_uploaded_proof and invoice_no and invoice_date and invoice_location and
                contract_no and work_order_no and sub_contract_no and
                invoice_value > 0 and admissible_amount > 0 and
                item_name and quantity > 0 and gst >= 0 and claimed_milestones
            )    
            telecom_validation = True
            if not has_telecom:
                telecom_validation = bool(planned_amount > 0)
            
            # Payment amount validation
            payment_validation = bool(claimed_amount > 0 and payable_amount > 0)
    
            ld_validation = True
            if liquidity_percentage > 0:
                ld_validation = bool(liquidity_amount > 0)

            delay_validation = True
            if noOfDays and noOfDays > 30:
                delay_validation = bool(days_reason)
                
            amount_validation = True
            amount_errors = []
        
            if payable_amount > admissible:
                amount_validation = False
                amount_errors.append(f"Payable Amount ({format_indian_currency(payable_amount)}) exceeds Admissible Amount ({format_indian_currency(admissible)})")
    
            if ro_amount > admissible:
                amount_validation = False
                amount_errors.append(f"Release Order Amount ({format_indian_currency(ro_amount)}) exceeds Admissible Amount ({format_indian_currency(admissible)})")
    
            duplicate_validation = True
            if invoice_no:
                existing_invoices = [inv['Invoice Number'] for inv in st.session_state.get("invoices", [])]
                duplicate_validation = invoice_no not in existing_invoices
    
            form_ready = bool(
                basic_validation and telecom_validation and payment_validation and ld_validation and
                delay_validation and amount_validation and duplicate_validation)
    

            if not invoice_uploaded_proof:
                st.error("⚠️ **Upload Proof of Invoice** is required")
            elif not invoice_no:
                st.error("⚠️ **Invoice Number** is required")
            elif not duplicate_validation:
                st.error("⚠️ **Invoice Number already exists** - please use a unique number")
            elif not invoice_date:
                st.error("⚠️ **Date of Invoice** is required")
            elif not contract_no:
                st.error("⚠️ **Contract Number** is required")
            elif not work_order_no:
                st.error("⚠️ **Work-Order Number** is required")
            elif not sub_contract_no:
                st.error("⚠️ **Sub-Contract Number** is required")
            elif invoice_value <= 0:
                st.error("⚠️ **Invoice Value** must be greater than 0")
            elif not item_name:
                st.error("⚠️ **Item Name** is required")
            elif quantity <= 0:
                st.error("⚠️ **Quantity** must be greater than 0")
            elif gst < 0:
                st.error("⚠️ **GST** cannot be negative")
            elif not claimed_milestones:
                st.error("⚠️ **Claimed Milestone** selection is required")
            elif not has_telecom and planned_amount <= 0:
                st.error("⚠️ **PQP/Planned Claim** is required for non-telecom categories")
            elif claimed_amount <= 0:
                st.error("⚠️ **Claimed Value** must be greater than 0")
            elif liquidity_percentage > 0 and liquidity_amount <= 0:
                st.error("⚠️ **LD Amount** is required when Liquidity Damage % > 0")
            elif noOfDays and noOfDays > 30 and not days_reason:
                st.error("⚠️ **Reason for Delay** is required when delay > 30 days")
            elif not amount_validation:
                for error in amount_errors:
                    st.error(f"⚠️ **Critical:** {error}")
          
            submitted = st.button(
                "Create Invoice", 
                type="primary", 
                use_container_width=True, 
                disabled=not form_ready
            )
            
        with col2:
            clear_all = st.button("Clear All", use_container_width=True)

        if submitted and form_ready:
            def create_solution_fields():
                fields = {}
                sol_rows = st.session_state.get('sol_support_rows', [])
                
                for i, row in enumerate(sol_rows, 1):
                    fields[f"({i}) Sol Support %"] = row.get('percentage', 0.0)
                    fields[f"({i}) Sol Support Amount"] = row.get('amount', 0.0)
                    fields[f"({i}) Sol Support Start Date"] = row.get('start_date', '').strftime("%d/%m/%Y") if row.get('start_date') else ''
                    fields[f"Sol Support Period"] = row.get('period', '')
                    fields[f"Sol Support Duration (Months)"] = row.get('duration', 0)
                    fields[f"Support Duration (Years)"] = row.get('duration', 0) / 12 if row.get('duration', 0) > 0 else 0.0
                return fields

            def create_custom_milestone_fields():
                fields = {}
                custom_count = st.session_state.get('others_custom_count', 0)
                for i in range(1, custom_count + 1):
                    percentage = st.session_state.get(f'main_others_custompercentage_{i}', 0.0)
                    remark = st.session_state.get(f'main_others_customremark_{i}', '')
                    fields[f"Custom Milestone ({i}) %"] = percentage
                    fields[f"Custom Milestone ({i}) Amount"] = (admissible_amount * percentage / 100) if percentage > 0 else 0.0
                    fields[f"Custom Milestone Remark ({i})"] = remark
                return fields

            def get_ld_application_type():
                if has_telecom:
                    return "Claimed"
                elif st.session_state.get('ld_apply_pqp', False):
                    return "PQP"
                
                elif st.session_state.get('ld_apply_claimed', False):
                    return "Claimed"
                else:
                    return ""

            milestone_data = {
                "Delivery_Percentage": delivery_percentage if 'delivery_percentage' in locals() else 0.0,
                "Delivery_Amount": delivery_amount if 'delivery_amount' in locals() else 0.0,
                "UAT_Submission_Percentage": uat_submission_percentage if 'uat_submission_percentage' in locals() else 0.0,
                "UAT_Submission_Amount": uat_submission_amount if 'uat_submission_amount' in locals() else 0.0,
                "UAT_Percentage": uat_percentage if 'uat_percentage' in locals() else 0.0,
                "UAT_Amount": uat_amount if 'uat_amount' in locals() else 0.0,
                "Warranty_Percentage": warranty_percentage if 'warranty_percentage' in locals() else 0.0,
                "Warranty_Amount": warranty_amount if 'warranty_amount' in locals() else 0.0,
                "Total_Milestone_Percentage": total_milestone_percentage if 'total_milestone_percentage' in locals() else (total_percentage if 'total_percentage' in locals() else 0.0),
                "Selected_Milestone_Type": milestone_type if 'milestone_type' in locals() else "",
                "Selected_Milestones_List": selected_labels if 'selected_labels' in locals() else st.session_state.get('selected_milestones', []),
                "Planned_Claim": planned_amount,
                "Current_Milestone_Claim": claimed_amount,
                "Release_Order_Milestone": milestone_type if (ro_date and 'milestone_type' in locals()) else None
            }

            new_invoice = {
                # Basic Invoice Information
                "Upload_Proof": invoice_uploaded_proof.name if invoice_uploaded_proof else None,
                "Invoice Number": invoice_no,
                "Date of Invoice": invoice_date.strftime("%d/%m/%Y"),
                "Invoice Location": invoice_location,
                
                # Contract Information
                "Contract Number": contract_no,
                "Vendor": actual_vendor,
                "Contract Date": selected_contract.get('Contract Date', '') if selected_contract else '',
        
                # Work Order Information  
                "Work-Order Number": work_order_no,
                "Admissible Amount": admissible_amount,
                "Sub-Contract Number": sub_contract_no,
                "Total Contract Value": actual_contract_value,
                "Total Contract Value (With GST)": actual_contract_value_gst,
        
                # Invoice Details
                "Invoice Value": invoice_value,
                "Invoice GST": tax,
        
                # Item Information
                "Item Name": item_name,
                "Category": actual_category,
                "Item Location": derived_item_location,
                "Quantity": quantity,
                "Item Value": derived_unit_value * quantity,
                "Value per Item": derived_unit_value,
        
                # Warranty Category Fields
                "Delivery (%)": st.session_state.get('delivery_percentage', 0.0) if (has_warranty or has_amc_warranty) else 0.0,
                "Delivery Amount": (admissible_amount * st.session_state.get('delivery_percentage', 0.0) / 100) if (has_warranty or has_amc_warranty) else 0.0,
                "Total Milestone %": st.session_state.get('total_milestone_percentage', 0.0) if (has_warranty or has_amc_warranty) else 0.0,
                "Power ON / UAT Submission (%)": st.session_state.get('uat_submission_percentage', 0.0) if (has_warranty or has_amc_warranty) else 0.0,
                "Power On Amount": (admissible_amount * st.session_state.get('uat_submission_percentage', 0.0) / 100) if (has_warranty or has_amc_warranty) else 0.0,
                "UAT Completion (%)": st.session_state.get('uat_percentage', 0.0) if (has_warranty or has_amc_warranty) else 0.0,
                "Completion Amount": (admissible_amount * st.session_state.get('uat_percentage', 0.0) / 100) if (has_warranty or has_amc_warranty) else 0.0,
                "Warranty (%)": st.session_state.get('warranty_percentage', 0.0) if (has_warranty or has_amc_warranty) else 0.0,
                "Warranty Amount": (admissible_amount * st.session_state.get('warranty_percentage', 0.0) / 100) if (has_warranty or has_amc_warranty) else 0.0,
                "Warranty Duration (Months)": st.session_state.get('warranty_duration', 0) if (has_warranty or has_amc_warranty) else 0,
                "Warranty Duration (Years)": (st.session_state.get('warranty_duration', 0) / 12) if (has_warranty or has_amc_warranty) else 0.0,
                "Warranty Claiming Period": st.session_state.get('warranty_period', '') if (has_warranty or has_amc_warranty) else '',
        
        # AMC Category Fields (for has_amc OR has_amc_warranty)
        "AMC (%)": st.session_state.get('amc_percentage', 0.0) if (has_amc or has_amc_warranty) else 0.0,
        "AMC Amount": (admissible_amount * st.session_state.get('amc_percentage', 0.0) / 100) if (has_amc or has_amc_warranty) else 0.0,
        "AMC Duration (Months)": st.session_state.get('amc_duration', 0) if (has_amc or has_amc_warranty) else 0,
        "AMC Duration (Years)": (st.session_state.get('amc_duration', 0) / 12) if (has_amc or has_amc_warranty) else 0.0,
        "AMC Claiming Period": st.session_state.get('amc_period', '') if (has_amc or has_amc_warranty) else '',
        "AMC Start Date": st.session_state.get('amc_start_date', '').strftime("%d/%m/%Y") if ((has_amc or has_amc_warranty) and st.session_state.get('amc_start_date')) else '',
        "Select Starting": st.session_state.get('amc_starting_label', '') if (has_amc or has_amc_warranty) else '',
        
        # Staff Cost Category Fields
        "Staff Duration (Months)": st.session_state.get('main_staff_duration', 0) if has_staffcost else 0,
        "Staff Duration (Years)": (st.session_state.get('main_staff_duration', 0) / 12) if has_staffcost else 0.0,
        "Staff Date": st.session_state.get('main_staff_start_date', '').strftime("%d/%m/%Y") if (has_staffcost and st.session_state.get('main_staff_start_date')) else '',
        "Staff Period": st.session_state.get('main_staff_period', '') if has_staffcost else '',
        
        # Software Category Fields  
        "Delivery (%) - Software": st.session_state.get('main_delivery_percentage', 0.0) if has_software else 0.0,
        "Delivery Amount - Software": (admissible_amount * st.session_state.get('main_delivery_percentage', 0.0) / 100) if has_software else 0.0,
        "Software Duration (Months)": st.session_state.get('main_software_duration', 0) if has_software else 0,
        "Software Duration (Years)": (st.session_state.get('main_software_duration', 0) / 12) if has_software else 0.0,
        "Software support Percentage (%)": st.session_state.get('main_software_support_percentage', 0.0) if has_software else 0.0,
        "Software support Amount": (admissible_amount * st.session_state.get('main_software_support_percentage', 0.0) / 100) if has_software else 0.0,
        
        # Solution Category Fields
        "Number of Milestones": st.session_state.get('sol_custom_count', 0) if has_solution else 0,
        **(create_solution_fields() if has_solution else {}),
        
        # Telecom Category Fields
        "Telecom Duration (Months)": st.session_state.get('main_telecom_duration', 0) if has_telecom else 0,
        "Telecom Duration (Years)": (st.session_state.get('main_telecom_duration', 0) / 12) if has_telecom else 0.0,
        "Billing Start Date": st.session_state.get('main_telecom_billing_start', '').strftime("%d/%m/%Y") if (has_telecom and st.session_state.get('main_telecom_billing_start')) else '',
        "Billing Period": st.session_state.get('main_telecom_billing_period', '') if has_telecom else '',
        
        # Others/Custom Milestones
        "Number of Custom Milestones": st.session_state.get('others_custom_count', 0) if has_others else 0,
        **(create_custom_milestone_fields() if has_others else {}),
        
        # Process Tracking Dates
        "Date of Invoice SUBMISSION": submission_date.strftime("%d/%m/%Y"),
        "Date of Invoice RECEIVED at TMD": receive_date.strftime("%d/%m/%Y"),
        "Complete ARTIFACTS Receiving Date": artifact_date.strftime("%d/%m/%Y"),
        
        # Claimed Milestones
        "Claimed Milestones": st.session_state.get('selected_milestones', []),
        
        # Financial Information - PQP
        "PQP/ Planned Claim": planned_amount,
        "PQP (With GST)": planned_amount * (1 + tax/100),
        
        # Financial Information - Claimed
        "Claimed Value": claimed_amount,
        "Claimed Value (With GST)": claimed_amount * (1 + tax/100),
        
        # Liquidity Damage Information
        "Liquidity Damage (%)": liquidity_percentage,
        "LD Amount": liquidity_amount,
        "LD Applied on": get_ld_application_type(),
        
        # Payable Information
        "Payable Amount": payable_amount,
        "Payable (With GST)": payable_amount * (1 + tax/100),
        
        # Release Order Information
        "Release Order Number": ro_number,
        "Release Order Amount": ro_amount,
        "RO Amount (With GST)": ro_amount * (1 + tax/100),
        "Date of RELEASE ORDER": ro_date.strftime("%d/%m/%Y") if ro_date else None,
        
        # Reason Fields
        "Reason for Liquidity Damage": damage_reason if liquidity_percentage > 0 else '',
        "Reason for Delay": days_reason if (noOfDays and noOfDays > 30) else '',
        
        # Calculated Fields (the 3 missing ones we identified)
        "Days_Between_RO_Receive": noOfDays,
        "Payment_Status": "Paid" if (ro_date and ro_amount > 0) else "Pending",
        
        # Legacy fields from your existing structure
        "Location": actual_location,
        "GST (%)": tax,
        "LD (%)": liquidity_percentage,
        "Liquidity Damages": liquidity_amount,
        "Payable Amount": payable_amount,
        "Days": noOfDays,
        "Days_Reason": days_reason,
        "Damage_Reason": damage_reason,
        
        # Metadata
        "Created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Last Modified": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            if "invoices" not in st.session_state:
                st.session_state["invoices"] = []
    
            st.session_state["invoices"].append(new_invoice)
            st.session_state["last_updated"] = datetime.now()
    
            # Success message with AMC Warranty handling
            success_msg = f"✅ {actual_category} invoice '{invoice_no}' created successfully!"
            success_msg += f"\n🔗 **Linked to Contract:** {work_order_no}--{sub_contract_no}"
            success_msg += f"\n🎯 **Milestone Tracking:** {milestone_data.get('Total_Milestone_Percentage', 0.0):.1f}% milestone structure"
    
            if ro_date and milestone_data.get('Selected_Milestone_Type'):
                success_msg += f"\n💰 **Release Order:** {ro_number} issued for {milestone_data.get('Selected_Milestone_Type')} milestone"
    
            st.success(success_msg)
            st.success(f"📊 **Summary:** Invoice Value: {format_indian_currency(invoice_value)} | Eligible: {format_indian_currency(admissible_amount)} | Payable: {format_indian_currency(payable_amount)}")
            st.success(f"📋 **Data Captured:** {len(new_invoice)} comprehensive fields including **Hardware AMC** category support!")
            st.rerun()
            
        elif clear_all:
            keys_to_clear = [
                'main_invoice_no', 'main_contract_no', 'main_item_name', 'main_quantity',
                'main_invoice_value', 'main_tax', 'main_invoice_date', 'main_submission_date',
                'main_receive_date', 'main_ro_date', 'main_claimed', 'main_claimed_telecom',
                'main_liquidity_pct', 'main_liquidity_pct_telecom', 'main_liquidity_amount',
                'main_liquidity_amount_telecom', 'main_damage_reason', 'duration_years', 
                'starting_quarter_year', 'delivery_percentage', 'uat_submission_percentage', 
                'uat_percentage', 'warranty_percentage', 'warranty_years', 'warranty_duration',
                'warranty_period', 'amc_percentage', 'amc_duration', 'amc_period', 
                'amc_start_date', 'amc_starting_label', 'main_ro_number', 'planned_claim', 
                'selected_milestones', 'invoice_uploaded_proof', 'invoice_location',
                'main_workorder_no', 'main_subcontract_no', 'main_admissible_amount',
                'main_artifact_date', 'main_payable', 'main_payable_default', 'main_payable',
                'main_ro_amount', 'main_days_reason', 'ld_apply_pqp', 'ld_apply_claimed',
                '_prev_ld_apply_pqp', '_prev_ld_apply_claimed',
        
                'main_delivery_percentage', 'main_software_duration', 'main_software_support_percentage',
        
                'sol_custom_count', 'sol_support_rows',
        
                'main_staff_duration', 'main_staff_period', 'main_staff_start_date',
        
                'main_telecom_duration', 'main_telecom_billing_period', 'main_telecom_billing_start',
        
                'others_custom_count'
            ]
            if st.session_state.get('others_custom_count', 0) > 0:
                for i in range(1, st.session_state.get('others_custom_count', 0) + 1):
                    keys_to_clear.extend([
                        f'main_others_custompercentage_{i}',
                        f'main_others_customremark_{i}'
                    ])   
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]    
                        
                st.success("🗑️ All fields cleared! Starting fresh.")
                st.rerun()


# --------- MANAGEMENT ---------
with tabs[3]:
    st.markdown("#### Manage Work Orders & Invoices")
    
    # Radio button selection
    manage_type = st.radio(
        "",
        options=["📋 Work Orders", "🧾 Invoices"],
        horizontal=True,
        key="manage_type_selection"
    )
    
    if manage_type == "📋 Work Orders":
        st.markdown("### Work Orders Management")
        
        if not st.session_state.get('work_orders'):
            st.info("No work orders available to manage. Create work orders first.")
        else:
            st.markdown("#### Select Work Order to Manage")
            
            all_contracts = [wo.get("Contract Number", "") for wo in st.session_state["work_orders"] if wo.get("Contract Number", "")]
            contract_numbers = list(dict.fromkeys(all_contracts)) 
            contract_numbers.sort()
            
            # Row 1: Three separate dropdowns
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1.5])
            
            with col1:
                selected_contract = st.selectbox(
                    "Contract Number",
                    options=[""]+contract_numbers,
                    key="manage_contract_select",
                    placeholder="Select Contract Number"
                )

            if selected_contract:
                filtered_wos_by_contract = [wo for wo in st.session_state['work_orders'] if wo.get('Contract Number') == selected_contract]
                workorder_numbers = list(set([wo.get('Work-Order Number', '') for wo in filtered_wos_by_contract if wo.get('Work-Order Number', '')]))
                workorder_numbers.sort()
            else:
                workorder_numbers = []
            
            with col2:
                selected_workorder = st.selectbox(
                    "Work-Order Number",
                    options=[""] + workorder_numbers,
                    key="manage_workorder_select",
                    placeholder="Select Work-Order Number",
                    disabled=not selected_contract
                )
            
            if selected_contract and selected_workorder:
                filtered_wos_by_wo = [wo for wo in filtered_wos_by_contract if wo.get('Work-Order Number') == selected_workorder]
                subcontract_numbers = list(set([wo.get('Sub-Contract Number', '') for wo in filtered_wos_by_wo if wo.get('Sub-Contract Number', '')]))
                subcontract_numbers.sort()
            else:
                subcontract_numbers = []
            
            with col3:
                selected_subcontract = st.selectbox(
                    "Sub-Contract Number",
                    options=[""] + subcontract_numbers,
                    key="manage_subcontract_select",
                    placeholder="Select Sub-Contract Number",
                    disabled=not (selected_contract and selected_workorder)
                )
            
            with col4:
                action = st.selectbox(
                    "Actions",
                    options=["View", "Edit Details", "Add Item", "Delete Item", "Delete Work-Order"],
                    key="wo_action",
                    disabled=not (selected_contract and selected_workorder and selected_subcontract)
                )
            
            selected_wo = None
            selected_wo_index = None
            
            if selected_contract and selected_workorder and selected_subcontract:
                for i, wo in enumerate(st.session_state['work_orders']):
                    wo_contract = str(wo.get("Contract Number", "")).strip()
                    wo_workorder = str(wo.get("Work-Order Number", "")).strip() 
                    wo_subcontract = str(wo.get("Sub-Contract Number", "")).strip()
        
                    selected_contract_str = str(selected_contract).strip()
                    selected_workorder_str = str(selected_workorder).strip()
                    selected_subcontract_str = str(selected_subcontract).strip()

                    if (wo_contract == selected_contract_str and 
                        wo_workorder == selected_workorder_str and 
                        wo_subcontract == selected_subcontract_str):
                        selected_wo = wo
                        selected_wo_index = i
                        break
                
                if not selected_wo:
                        st.error("NOT FOUND. NO SUCH ENTRY EXISTS.")
                else:
                    if action == "View":
                        st.markdown("---")
                        st.markdown("#### Work Order Details")
                        
                        # Display all required information as specified
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text_input("Contract Number", value=selected_wo.get('Contract Number', ''), disabled=True, key="view_contract_num")
                            st.text_input("Vendor", value=selected_wo.get('Vendor', ''), disabled=True, key="view_vendor")
                            st.text_input("Location", value=selected_wo.get('Location', ''), disabled=True, key="view_location")
                            st.number_input("Contract Value ₹ (Basic)", value=selected_wo.get('Contract Value', 0.0), disabled=True, key="view_contract_val")
                        
                        with col2:
                            st.number_input("GST (%)", value=selected_wo.get('GST (%)', 0.0), disabled=True, key="view_gst")
                            total_contract_gst = selected_wo.get('Total Contract Value (with GST)', 0.0)
                            st.number_input("Total Contract Value (with GST) ₹", value=total_contract_gst, disabled=True, key="view_total_contract")
                            st.text_input("Contract Date", value=selected_wo.get('Contract Date', ''), disabled=True, key="view_contract_date")
                            st.text_input("Work-Order Number", value=selected_wo.get('Work-Order Number', ''), disabled=True, key="view_wo_num")
                        
                        with col3:
                            st.number_input("% Work-Order", value=selected_wo.get('% Work-Order', 0.0), disabled=True, key="view_wo_pct")
                            st.number_input("Work-Order Value ₹ (Basic)", value=selected_wo.get('Work-Order Value (Basic)', 0.0), disabled=True, key="view_wo_basic")
                            st.number_input("Work-Order Value (with GST) ₹", value=selected_wo.get('Work-Order Value (with GST)', 0.0), disabled=True, key="view_wo_gst")
                            st.text_input("Sub-Contract Number", value=selected_wo.get('Sub-Contract Number', ''), disabled=True, key="view_subcontract")
                        
                        # Items count and details
                        items_count = selected_wo.get('Item(s) Count', 0)
                        st.number_input("Item(s) Count", value=items_count, disabled=True, key="view_items_count")
                        
                        # Display all item details
                        st.markdown("#### Item Details")
                        items = selected_wo.get('Items', [])
                        if items:
                            # Create comprehensive dataframe with all item details
                            items_display_data = []
                            for item in items:
                                item_row = {
                                    "Sl. No.": item.get("Item Sl. No.", ""),
                                    "Item Name": item.get("Item Name", ""),
                                    "Item Location": item.get("Item Location", ""),
                                    "Category": item.get("Category", ""),
                                    "Qty": item.get("Qty", 0),
                                    "Value per Item ₹": format_indian_currency(item.get("Value per Item", 0)),
                                    "₹ without GST": format_indian_currency(item.get("₹ without GST", 0)),
                                    "₹ with GST": format_indian_currency(item.get("₹ with GST", 0)),
                                    "Remark": item.get("Remark", "")
                                }
                                
                                # Add category-specific details
                                category = item.get("Category", "")
                                
                                if category == "Hardware":
                                    item_row.update({
                                        "Warranty Duration (Months)": item.get("Warranty Duration (Months)", ""),
                                        "Warranty Duration (Years)": f"{item.get('Warranty Duration (Years)', 0.0):.2f}",
                                        "% Warranty": f"{item.get('% Warranty', 0.0):.2f}%",
                                        "Rate incl. Warranty": format_indian_currency(item.get("Rate incl. Warranty", 0)),
                                        "Warranty Total ₹ with GST": format_indian_currency(item.get("Warranty Total ₹ with GST", 0))
                                    })
                                
                                elif category == "AMC":
                                    item_row.update({
                                        "AMC Duration (Months)": item.get("AMC Duration (Months)", ""),
                                        "AMC Duration (Years)": f"{item.get('AMC Duration (Years)', 0.0):.2f}",
                                        "% AMC": f"{item.get('% AMC', 0.0):.2f}%",
                                        "Rate incl. AMC": format_indian_currency(item.get("Rate incl. AMC", 0)),
                                        "AMC Total ₹ with GST": format_indian_currency(item.get("AMC Total ₹ with GST", 0))
                                    })
                                
                                elif category == "Hardware (+ AMC)":
                                    item_row.update({
                                        "Warranty Duration (Months)": item.get("Warranty Duration (Months)", ""),
                                        "Warranty Duration (Years)": f"{item.get('Warranty Duration (Years)', 0.0):.2f}",
                                        "% Warranty": f"{item.get('% Warranty', 0.0):.2f}%",
                                        "Rate incl. Warranty": format_indian_currency(item.get("Rate incl. Warranty", 0)),
                                        "Warranty Total ₹ with GST": format_indian_currency(item.get("Warranty Total ₹ with GST", 0)),
                                        "AMC Duration (Months)": item.get("AMC Duration (Months)", ""),
                                        "AMC Duration (Years)": f"{item.get('AMC Duration (Years)', 0.0):.2f}",
                                        "% AMC": f"{item.get('% AMC', 0.0):.2f}%",
                                        "Rate incl. AMC": format_indian_currency(item.get("Rate incl. AMC", 0)),
                                        "AMC Total ₹ with GST": format_indian_currency(item.get("AMC Total ₹ with GST", 0))
                                    })
                                
                                elif category == "Solution and Support":
                                    item_row.update({
                                        "Support Duration (Months)": item.get("Support Duration (Months)", ""),
                                        "Support Duration (Years)": f"{item.get('Support Duration (Years)', 0.0):.2f}",
                                        "Support Period": item.get("Support Period", ""),
                                        "% Support": f"{item.get('% Support', 0.0):.2f}%",
                                        "Rate incl. Support": format_indian_currency(item.get("Rate incl. Support", 0)),
                                        "Support Total ₹ with GST": format_indian_currency(item.get("Support Total ₹ with GST", 0)),
                                        "Period Start Date": item.get("Period Start Date", "")
                                    })
                                
                                elif category == "Staff Cost":
                                    item_row.update({
                                        "Staff Duration (Months)": item.get("Staff Duration (Months)", ""),
                                        "Staff Duration (Years)": f"{item.get('Staff Duration (Years)', 0.0):.2f}",
                                        "Staff Period": item.get("Staff Period", ""),
                                        "Staff From": item.get("Staff From", ""),
                                        "Staff To": item.get("Staff To", ""),
                                        "Staff Start Date": item.get("Staff Start Date", "")
                                    })
                                
                                elif category == "Telecom":
                                    item_row.update({
                                        "Sub-Vendor Name": item.get("Sub-Vendor Name", ""),
                                        "Telecom Link/Location": item.get("Telecom Link/Location", ""),
                                        "Telecom Type": item.get("Telecom Type", ""),
                                        "Telecom Capacity": item.get("Telecom Capacity", "")
                                    })
                                
                                # Add additional remarks if present
                                if item.get("Additional Remark"):
                                    item_row["Additional Remark"] = item.get("Additional Remark", "")
                                
                                items_display_data.append(item_row)
                            
                            # Display as dataframe
                            items_df = pd.DataFrame(items_display_data)
                            items_df_fy = add_financial_year_columns(items_df)
                            st.dataframe(style_alternate_rows(items_df_fy), use_container_width=True, hide_index=True)
                        else:
                            st.info("No items found in this work order.")
                    
                    elif action == "Edit Details":
                        st.markdown("---")
                        st.markdown("#### Edit Work Order Details")
                        
                        with st.form("edit_wo_form"):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                edit_vendor = st.text_input("Vendor", value=selected_wo.get('Vendor', ''))
                                edit_location = st.text_input("Location", value=selected_wo.get('Location', ''))
                            
                            with col2:
                                edit_contract_value = st.number_input(
                                    "Contract Value ₹ (Basic)", 
                                    value=float(selected_wo.get('Contract Value', 0.0)),
                                    min_value=0.0,
                                    step=1.0000,
                                    format="%.4f"
                                )
                                edit_gst = st.number_input(
                                    "GST (%)", 
                                    value=float(selected_wo.get('GST (%)', 0.0)),
                                    min_value=0.0,
                                    max_value=100.0,
                                    step=1.00,
                                    format="%.2f"
                                )
                            
                            with col3:
                                edit_wo_pct = st.number_input(
                                    "% Work-Order", 
                                    value=float(selected_wo.get('% Work-Order', 0.0)),
                                    min_value=0.0,
                                    max_value=100.0,
                                    step=1.00,
                                    format="%.2f"
                                )
                                
                                edit_wo_value = edit_contract_value * (edit_wo_pct/100)
                                st.number_input(
                                    "Work-Order Value ₹ (Basic)", 
                                    value=edit_wo_value,
                                    disabled=True,
                                    format="%.4f"
                                )
                            
                            submit_edit = st.form_submit_button("Update Work Order Details")
                            
                            if submit_edit:
                                # Update work order details
                                st.session_state['work_orders'][selected_wo_index].update({
                                    'Vendor': edit_vendor,
                                    'Location': edit_location,
                                    'Contract Value': edit_contract_value,
                                    'GST (%)': edit_gst,
                                    '% Work-Order': edit_wo_pct,
                                    'Work-Order Value (Basic)': edit_wo_value,
                                    'Work-Order Value (with GST)': edit_wo_value * (1 + edit_gst/100),
                                    'Total Contract Value (with GST)': edit_contract_value * (1 + edit_gst/100)
                                })
                                st.success("Work order details updated successfully!")
                                st.rerun()
                    
                    elif action == "Add Item":
                        st.markdown("---")
                        st.markdown("#### Add New Item to Work Order")
                        
                        # Get the next serial number
                        existing_items = selected_wo.get('Items', [])
                        next_sl_no = len(existing_items) + 1
                        
                        st.info(f"Current Item(s) Count: **{len(existing_items)}**")
                        
                            # Basic item information
                        col1, col2, col3, col4 = st.columns([0.3, 0.7, 0.65, 1])
                            
                            # Display the serial number (disabled)
                        with col1:
                            st.text_input("Sl. No.", value=str(next_sl_no), disabled=True, key="add_item_sl_no")
                            
                        with col2:
                            new_item_name = st.text_input("Item Name", key="add_item_name")
                            
                        with col3:
                            new_item_location = st.text_input("Item Location", key="add_item_location")
                            
                        with col4:
                            category_options = ["Hardware", "Hardware (+ AMC)", "AMC", "Software", "Staff Cost", "Solution and Support", "Telecom", "Others"]
                            new_category = st.selectbox("Category", category_options, key="add_item_category", placeholder="Select Category")
                            
                            # Quantity and value information
                        col1, col2, col3, col4 = st.columns([0.8, 1, 1, 0.8])
                            
                        with col1:
                            new_qty = st.number_input("Qty", min_value=1, step=1, value=1, key="add_item_qty")
                            
                        with col2:
                            if new_category == "Staff Cost":
                                new_value_per_item = st.number_input("Man per Month (₹)", min_value=0.0, step=1.0000, format="%.4f", key="add_item_value")
                            else:
                                new_value_per_item = st.number_input("Value per Item (₹)", min_value=0.0, step=1.0000, format="%.4f", key="add_item_value")
                            
                        # Calculate GST using the work order's GST rate
                        current_gst = selected_wo.get('GST (%)', 0.0)
                        item_total_without_gst = new_qty * new_value_per_item
                        item_total_with_gst = item_total_without_gst * (1 + current_gst/100)
                            
                        with col3:
                            if new_category == "Staff Cost":
                                st.number_input("Total Man per Month ₹ (with Tax)", value=item_total_with_gst, disabled=True, format="%.4f", key="add_item_total_gst")
                            else:
                                st.number_input("Item Total ₹ (with Tax)", value=item_total_with_gst, disabled=True, format="%.4f", key="add_item_total_gst")
                            
                        with col4:
                            new_remark = st.text_input("Remark", key="add_item_remark")
                            
                        # Category-specific fields
                        category_fields = {}
                            
                        if new_category == "Hardware":
                            st.markdown("##### Hardware Specific Fields")
                            hcol1, hcol2, hcol3, hcol4 = st.columns([1, 0.8, 1, 0.8])
                            with hcol1:
                                warranty_duration = st.number_input("Warranty Duration (Months)", min_value=1, value=36, step=1, key="add_warranty_dur")
                                warranty_years = warranty_duration / 12
                                st.caption(f"{warranty_years:.2f} Years")
                            with hcol2:
                                warranty_pct = st.number_input("% Warranty", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key="add_warranty_pct")
                            with hcol3:
                                rate_warranty = new_value_per_item * (1 + warranty_pct/100)
                                st.number_input("Rate incl. Warranty", value=rate_warranty, disabled=True, format="%.4f", key="add_rate_warranty")
                            with hcol4:
                                warranty_total = rate_warranty * new_qty * (1 + current_gst/100)
                                st.number_input("Total Value ₹ (with Tax)", value=warranty_total, disabled=True, format="%.4f", key="add_warranty_total")
                                
                            add_remark = st.text_input("Additional Remark", key="add_hardware_remark")
                                
                            category_fields.update({
                                    'Warranty Duration (Months)': warranty_duration,
                                    'Warranty Duration (Years)': warranty_years,
                                    '% Warranty': warranty_pct,
                                    'Rate incl. Warranty': rate_warranty,
                                    'Warranty Total ₹ with GST': warranty_total,
                                    'Additional Remark': add_remark
                            })
                            
                        elif new_category == "AMC":
                            st.markdown("##### AMC Specific Fields")
                            acol1, acol2, acol3, acol4 = st.columns([1, 0.8, 1, 0.8])
                            with acol1:
                                amc_duration = st.number_input("AMC Duration (Months)", min_value=1, value=48, step=1, key="add_amc_dur")
                                amc_years = amc_duration / 12
                                st.caption(f"{amc_years:.2f} Years")
                            with acol2:
                                amc_pct = st.number_input("% AMC", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key="add_amc_pct")
                            with acol3:
                                rate_amc = new_value_per_item * (1 + amc_pct/100)
                                st.number_input("Rate incl. AMC", value=rate_amc, disabled=True, format="%.4f", key="add_rate_amc")
                            with acol4:
                                amc_total = rate_amc * new_qty * (1 + current_gst/100)
                                st.number_input("Item Total Value ₹ (with Tax)", value=amc_total, disabled=True, format="%.4f", key="add_amc_total")
                                
                            add_remark = st.text_input("Additional Remark", key="add_amc_remark")
                                
                            category_fields.update({
                                    'AMC Duration (Months)': amc_duration,
                                    'AMC Duration (Years)': amc_years,
                                    '% AMC': amc_pct,
                                    'Rate incl. AMC': rate_amc,
                                    'AMC Total ₹ with GST': amc_total,
                                    'Additional Remark': add_remark
                            })
                            
                        elif new_category == "Hardware (+ AMC)":
                            st.markdown("##### Hardware (+ AMC) Specific Fields")

                            st.markdown("###### Warranty Information")
                            hcol1, hcol2, hcol3, hcol4 = st.columns([1, 0.8, 1, 1])
                            with hcol1:
                                warranty_duration = st.number_input("Warranty Duration (Months)", min_value=1, value=36, step=1, key="add_hw_amc_warranty_dur")
                                warranty_years = warranty_duration / 12
                                st.caption(f"{warranty_years:.2f} Years")
                            with hcol2:
                                warranty_pct = st.number_input("% Warranty", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key="add_hw_amc_warranty_pct")
                            with hcol3:
                                rate_warranty = new_value_per_item * (1 + warranty_pct/100)
                                st.number_input("Rate incl. Warranty", value=rate_warranty, disabled=True, format="%.4f", key="add_hw_amc_rate_warranty")
                            with hcol4:
                                warranty_total = rate_warranty * new_qty * (1 + current_gst/100)
                                st.number_input("Item Total Value ₹ (with Tax)", value=warranty_total, disabled=True, format="%.4f", key="add_hw_amc_warranty_total")
                                
                            # AMC
                            st.markdown("###### AMC Information")
                            acol1, acol2, acol3, acol4 = st.columns([1, 0.8, 1, 1])
                            with acol1:
                                amc_duration = st.number_input("AMC Duration (Months)", min_value=1, value=48, step=1, key="add_hw_amc_amc_dur")
                                amc_years = amc_duration / 12
                                st.caption(f"{amc_years:.2f} Years")
                            with acol2:
                                amc_pct = st.number_input("% AMC", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key="add_hw_amc_amc_pct")
                            with acol3:
                                rate_amc = new_value_per_item * (1 + amc_pct/100)
                                st.number_input("Rate incl. AMC", value=rate_amc, disabled=True, format="%.4f", key="add_hw_amc_rate_amc")
                            with acol4:
                                amc_total = rate_amc * new_qty * (1 + current_gst/100)
                                st.number_input("Total Value ₹ (with Tax)", value=amc_total, disabled=True, format="%.4f", key="add_hw_amc_amc_total")
                                
                            add_remark = st.text_input("Additional Remark", key="add_hw_amc_remark")
                                
                            category_fields.update({
                                    'Warranty Duration (Months)': warranty_duration,
                                    'Warranty Duration (Years)': warranty_years,
                                    '% Warranty': warranty_pct,
                                    'Rate incl. Warranty': rate_warranty,
                                    'Warranty Total ₹ with GST': warranty_total,
                                    'AMC Duration (Months)': amc_duration,
                                    'AMC Duration (Years)': amc_years,
                                    '% AMC': amc_pct,
                                    'Rate incl. AMC': rate_amc,
                                    'AMC Total ₹ with GST': amc_total,
                                    'Additional Remark': add_remark
                            })
                            
                        elif new_category == "Solution and Support":
                            st.markdown("##### Solution and Support Specific Fields")
                            scol1, scol2, scol3 = st.columns(3)
                            with scol1:
                                support_pct = st.number_input("% Support", min_value=0.0, step=5.0, max_value=100.0, format="%.2f", key="add_support_pct")
                            with scol2:
                                support_duration = st.number_input("Support Duration (Months)", min_value=1, value=48, step=1, key="add_support_dur")
                                support_years = support_duration / 12
                                st.caption(f"{support_years:.2f} Years")
                            with scol3:
                                support_period = st.selectbox(
                                    "Support Period",
                                    options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                                    index=0,
                                    key="add_support_period"
                                )
                                if support_period == "Annually":
                                    st.caption(f"{support_years:.2f} Years")
                                elif support_period == "Half Yearly":
                                    st.caption(f"{(support_years * 2):.2f} Half Years")
                                elif support_period == "Quarterly":
                                    st.caption(f"{(support_years * 4):.2f} Quarters")
                                elif support_period == "Monthly":
                                    st.caption(f"{support_duration:.2f} Months")
                                
                            scol1, scol2 = st.columns(2)
                            with scol1:
                                support_start_date = st.date_input("Period Start Date", value=datetime.today(), format="DD/MM/YYYY", key="add_support_start")
                            with scol2:
                                rate_support = new_value_per_item * (1 + support_pct/100)
                                st.number_input("Rate incl. Support", value=rate_support, disabled=True, format="%.4f", key="add_rate_support")
                                support_total = rate_support * new_qty * (1 + current_gst/100)
                                st.number_input("Total Value ₹(with Tax)", value=support_total, disabled=True, format="%.4f", key="add_support_total")
                                
                            category_fields.update({
                                    'Support Duration (Months)': support_duration,
                                    'Support Duration (Years)': support_years,
                                    'Support Period': support_period,
                                    '% Support': support_pct,
                                    'Rate incl. Support': rate_support,
                                    'Support Total ₹ with GST': support_total,
                                    'Period Start Date': support_start_date.strftime("%d/%m/%Y")
                            })
                            
                        elif new_category == "Staff Cost":
                            st.markdown("##### Staff Cost Specific Fields")
                            stcol1, stcol2, stcol3 = st.columns(3)
                                
                            with stcol1:
                                mode = st.radio(
                                        "Duration",
                                        options=["Period", "From : To"],
                                        index=0,
                                        key="add_staff_mode",
                                        horizontal=True,
                                )
                                
                            if mode == "From : To":
                                with stcol2:
                                    staff_from = st.date_input("From", value=date.today(), format="DD/MM/YYYY", key="add_staff_from")
                                with stcol3:
                                    staff_to = st.date_input("To", value=date.today(), format="DD/MM/YYYY", key="add_staff_to")
                                    
                                if staff_to < staff_from:
                                    staff_duration = 0
                                    staff_years = 0.0
                                    stcol2.caption("0.00 Years")
                                else:
                                    start_y, start_m, start_d = staff_from.year, staff_from.month, staff_from.day
                                    end_y, end_m, end_d = staff_to.year, staff_to.month, staff_to.day
                                    months = (end_y - start_y) * 12 + (end_m - start_m)
                                    if end_d >= start_d:
                                        months += 1
                                    months = max(months, 1)
                                    staff_duration = months
                                    staff_years = months / 12.0
                                    stcol2.caption(f"{staff_years:.2f} Years")
                                    
                                category_fields.update({
                                    'Staff From': staff_from.strftime("%d/%m/%Y"),
                                    'Staff To': staff_to.strftime("%d/%m/%Y"),
                                    'Staff Duration (Months)': staff_duration,
                                    'Staff Duration (Years)': staff_years,
                                    'Staff Period': None
                                })
                                
                            else:  # Period mode
                                with stcol2:
                                    staff_duration = st.number_input("Staff Duration (Months)", min_value=12, step=1, key="add_staff_dur")
                                    staff_years = staff_duration / 12.0
                                    st.caption(f"{staff_years:.2f} Years")
                                with stcol3:
                                    staff_period = st.selectbox(
                                            "Staff Period",
                                            options=["Annually", "Half Yearly", "Quarterly", "Monthly"],
                                            index=0,
                                            key="add_staff_period"
                                    )

                                    if staff_period == "Annually":
                                        st.caption(f"{staff_years:.2f} Years")
                                    elif staff_period == "Half Yearly":
                                        st.caption(f"{(staff_duration / 6):.2f} Half Years")
                                    elif staff_period == "Quarterly":
                                        st.caption(f"{(staff_duration / 3):.2f} Quarters")
                                    elif staff_period == "Monthly":
                                        st.caption(f"{staff_duration:.2f} Months")
                                    
                                category_fields.update({
                                        'Staff Duration (Months)': staff_duration,
                                        'Staff Duration (Years)': staff_years,
                                        'Staff Period': staff_period,
                                        'Staff From': "",
                                        'Staff To': ""
                                })
                                
                            staff_start_date = st.date_input("Staff Start Date", value=date.today(), format="DD/MM/YYYY", key="add_staff_start")
                            add_remark = st.text_input("Additional Remark", key="add_staff_remark")
                                
                            category_fields.update({
                                    'Staff Start Date': staff_start_date.strftime("%d/%m/%Y"),
                                    'Additional Remark': add_remark
                            })
                            
                        elif new_category == "Telecom":
                            st.markdown("##### Telecom Specific Fields")
                            tcol1, tcol2, tcol3, tcol4 = st.columns(4)
                            with tcol1:
                                subvendor = st.text_input("Sub-Vendor Name", key="add_subvendor")
                            with tcol2:
                                telecom_link = st.text_input("Link/Location", key="add_telecom_link")
                            with tcol3:
                                telecom_type = st.text_input("Type", key="add_telecom_type")
                            with tcol4:
                                telecom_capacity = st.text_input("Capacity", key="add_telecom_capacity")
                                
                            add_remark = st.text_input("Additional Remark", key="add_telecom_remark")
                                
                            category_fields.update({
                                    'Sub-Vendor Name': subvendor,
                                    'Telecom Link/Location': telecom_link,
                                    'Telecom Type': telecom_type,
                                    'Telecom Capacity': telecom_capacity,
                                    'Additional Remark': add_remark
                            })
                            
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Add Item", type="primary", key="submit_new_item", use_container_width=True):
                                if new_item_name and new_qty > 0 and new_value_per_item > 0:
                                    # Check for duplicates using existing function
                                    if contract_exists_full(selected_contract, selected_subcontract, selected_workorder, new_item_location, new_category):
                                        st.error("Item with same name, location, and category already exists!")
                                    else:
                                        # Create new item with proper structure
                                        new_item = {
                                            "Item Sl. No.": next_sl_no,
                                            "Item Name": new_item_name,
                                            "Item Location": new_item_location,
                                            "Category": new_category,
                                            "Qty": new_qty,
                                            "Value per Item": new_value_per_item,
                                            "₹ without GST": item_total_without_gst,
                                            "GST": current_gst,
                                            "₹ with GST": item_total_with_gst,
                                            "Remark": new_remark,
                                            **category_fields
                                        }
                                        if 'Items' not in st.session_state['work_orders'][selected_wo_index]:
                                            st.session_state['work_orders'][selected_wo_index]['Items'] = []
                                        st.session_state['work_orders'][selected_wo_index]['Items'].append(new_item)
                    
                                        new_count = len(st.session_state['work_orders'][selected_wo_index]['Items'])
                                        st.session_state['work_orders'][selected_wo_index]['Item(s) Count'] = new_count
                    
                                        st.success(f"✅ Item '{new_item_name}' added successfully! New Item(s) Count: {new_count}")
                                        st.rerun()
                                else:
                                    st.error("Please fill all required fields (Item Name, Qty > 0, Value per Item > 0)")
                        
                        with col2:
                            if st.button("Clear Form", key="clear_add_item_form", use_container_width=True):
                                keys_to_remove = [k for k in st.session_state.keys() if k.startswith("add_")]
                                for key in keys_to_remove:
                                    del st.session_state[key]
                                    st.rerun()    
                    
                    elif action == "Delete Item":
                        st.markdown("---")
                        st.markdown("#### Delete Item from Work Order")
                        
                        items = selected_wo.get('Items', [])
                        if not items:
                            st.info("No items to delete in this work order.")
                        else:
                            item_options = []
                            for i, item in enumerate(items):
                                item_display = f"Sl.{item.get('Item Sl. No.', '')} | {item.get('Item Name', '')} | {item.get('Category', '')} | {item.get('Item Location', '')} | Qty: {item.get('Qty', 0)}"
                                item_options.append((item_display, i))
                            
                            selected_item_display = st.selectbox(
                                "Select Item to Delete",
                                options=[opt[0] for opt in item_options],
                                key="delete_item_selector"
                            )
                            
                            selected_item_index = next((i for display, i in item_options if display == selected_item_display), None)
                            
                            if selected_item_index is not None:
                                selected_item = items[selected_item_index]
                                
                                # Show item details for confirmation
                                st.markdown("##### Item Details to Delete:")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.text(f"Sl. No.: {selected_item.get('Item Sl. No.', '')}")
                                    st.text(f"Name: {selected_item.get('Item Name', '')}")
                                    st.text(f"Category: {selected_item.get('Category', '')}")
                                with col2:
                                    st.text(f"Location: {selected_item.get('Item Location', '')}")
                                    st.text(f"Quantity: {selected_item.get('Qty', 0)}")
                                    st.text(f"Value per Item: ₹{selected_item.get('Value per Item', 0):,.2f}")
                                with col3:
                                    st.text(f"Total Value: ₹{selected_item.get('₹ with GST', 0):,.2f}")
                                    st.text(f"Remark: {selected_item.get('Remark', 'N/A')}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("🗑️ Confirm Delete Item", type="primary", key="confirm_delete_item"):
                                        # Remove item from work order
                                        st.session_state['work_orders'][selected_wo_index]['Items'].pop(selected_item_index)
                                        
                                        # Update serial numbers for remaining items
                                        for i, item in enumerate(st.session_state['work_orders'][selected_wo_index]['Items']):
                                            item['Item Sl. No.'] = i + 1
                                        
                                        # Update item count
                                        new_count = len(st.session_state['work_orders'][selected_wo_index]['Items'])
                                        st.session_state['work_orders'][selected_wo_index]['Item(s) Count'] = new_count
                                        
                                        st.success(f"✅ Item deleted successfully! Updated Item(s) Count: {new_count}")
                                        st.rerun()
                                
                                with col2:
                                    st.button("Cancel", key="cancel_delete_item")
                    
                    elif action == "Delete Work-Order":
                        st.markdown("---")
                        st.markdown("#### Delete Entire Work-Order")
                        st.warning("⚠️ This action will permanently delete the entire work-order and all its items!")
                        
                        # Show work order summary for confirmation
                        st.markdown("##### Work-Order to Delete:")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"Contract: {selected_wo.get('Contract Number', '')}")
                            st.text(f"Work-Order: {selected_wo.get('Work-Order Number', '')}")
                            st.text(f"Sub-Contract: {selected_wo.get('Sub-Contract Number', '')}")
                        with col2:
                            st.text(f"Vendor: {selected_wo.get('Vendor', '')}")
                            st.text(f"Location: {selected_wo.get('Location', '')}")
                            st.text(f"Item(s) Count: {selected_wo.get('Item(s) Count', 0)}")
                        with col3:
                            st.text(f"Contract Value: ₹{selected_wo.get('Contract Value', 0):,.2f}")
                            st.text(f"Work-Order Value: ₹{selected_wo.get('Work-Order Value (with GST)', 0):,.2f}")
                        
                        st.text_input(
                            "Type 'DELETE' to confirm deletion:",
                            key="delete_wo_confirmation",
                            placeholder="Type DELETE here..."
                        )
                        
                        confirmation_text = st.session_state.get("delete_wo_confirmation", "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                                "🗑️ Permanently Delete Work-Order", 
                                type="primary",
                                disabled=(confirmation_text.upper() != "DELETE"),
                                key="confirm_delete_wo"
                            ):
                                # Check if there are any invoices linked to this work order
                                linked_invoices = []
                                if 'invoices' in st.session_state:
                                    for invoice in st.session_state['invoices']:
                                        if (invoice.get('Contract Number') == selected_wo.get('Contract Number') and
                                            invoice.get('Work-Order Number') == selected_wo.get('Work-Order Number') and
                                            invoice.get('Sub-Contract Number') == selected_wo.get('Sub-Contract Number')):
                                            linked_invoices.append(invoice.get('Invoice Number', ''))
                                
                                if linked_invoices:
                                    st.error(f"Cannot delete work-order! The following invoices are linked to it: {', '.join(linked_invoices)}")
                                else:
                                    # Delete work order
                                    st.session_state['work_orders'].pop(selected_wo_index)
                                    st.success("✅ Work-order deleted successfully!")
                                    st.rerun()
                        
                        with col2:
                            st.button("Cancel", key="cancel_delete_wo")

    # manage_type == "🧾 Invoices"
    else:  
        st.markdown("### Invoices Management")
        
        if not st.session_state.get('invoices'):
            st.info("No invoices available to manage. Create invoices first.")
        else:
            st.markdown("#### Select Invoice to Manage")  
            all_inv_contracts = [inv.get("Contract Number", "") for inv in st.session_state["invoices"] if inv.get("Contract Number", "")]
            contract_numbers = list(dict.fromkeys(all_inv_contracts))      
            contract_numbers.sort()
        
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1.5])
        
            with col1:
                selected_inv_contract = st.selectbox(
                    "Contract Number",
                    options=contract_numbers,
                    key="manage_inv_contract_select",
                    placeholder="Select Contract Number"
                )
        
                if selected_inv_contract:
                    filtered_invs_by_contract = [inv for inv in st.session_state['invoices'] if inv.get('Contract Number') == selected_inv_contract]
                    workorder_numbers = list(set([inv.get('Work-Order Number', '') for inv in filtered_invs_by_contract if inv.get('Work-Order Number', '')]))
                    workorder_numbers.sort()
                else:
                    workorder_numbers = []
        
            with col2:
                selected_inv_workorder = st.selectbox(
                    "Work-Order Number",
                    options=workorder_numbers,
                    key="manage_inv_workorder_select",
                    placeholder="Select Work-Order Number",
                    disabled=not selected_inv_contract
                )
        
       
                if selected_inv_contract and selected_inv_workorder:
                    filtered_invs_by_wo = [inv for inv in filtered_invs_by_contract if inv.get('Work-Order Number') == selected_inv_workorder]
                    subcontract_numbers = list(set([inv.get('Sub-Contract Number', '') for inv in filtered_invs_by_wo if inv.get('Sub-Contract Number', '')]))
                    subcontract_numbers.sort()
                else:
                    subcontract_numbers = []
        
            with col3:
                selected_inv_subcontract = st.selectbox(
                "Sub-Contract Number",
                options=[""] + subcontract_numbers,
                key="manage_inv_subcontract_select",
                placeholder="Select Sub-Contract Number",
                disabled=not (selected_inv_contract and selected_inv_workorder)
                )
        
       
                if selected_inv_contract and selected_inv_workorder and selected_inv_subcontract:
                    filtered_invs_by_sub = [inv for inv in filtered_invs_by_wo if inv.get('Sub-Contract Number') == selected_inv_subcontract]
                    item_names = list(set([inv.get('Item Name', '') for inv in filtered_invs_by_sub if inv.get('Item Name', '')]))
                    item_names.sort()
                else:
                    item_names = []
        
            with col4:
                selected_inv_item = st.selectbox(
                "Item Name",
                options=[""] + item_names,
                key="manage_inv_item_select",
                placeholder="Select Item Name",
                disabled=not (selected_inv_contract and selected_inv_workorder and selected_inv_subcontract)
                )
        
            with col5:
                invoice_action = st.selectbox(
                    "Actions",
                    options=["View", "Edit Details", "Update Payment", "Delete Invoice"],
                    key="invoice_action",
                    disabled=not (selected_inv_contract and selected_inv_workorder and selected_inv_subcontract and selected_inv_item)
                )
        
            selected_invoice = None
            selected_invoice_index = None
        
            if selected_inv_contract and selected_inv_workorder and selected_inv_subcontract and selected_inv_item:
                for i, inv in enumerate(st.session_state['invoices']):
                    if (inv.get('Contract Number') == selected_inv_contract and 
                        inv.get('Work-Order Number') == selected_inv_workorder and 
                        inv.get('Sub-Contract Number') == selected_inv_subcontract and
                        inv.get('Item Name') == selected_inv_item):
                        selected_invoice = inv
                        selected_invoice_index = i
                        break
            
            if not selected_invoice:
                st.error("NOT FOUND. NO SUCH ENTRY EXISTS.")
            else:
                    if invoice_action == "View":
                        st.markdown("---")
                        st.markdown("#### Invoice Details")
                    
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text_input("Invoice Number", value=selected_invoice.get('Invoice Number', ''), disabled=True, key="view_inv_num")
                            st.text_input("Date of Invoice", value=selected_invoice.get('Date of Invoice', ''), disabled=True, key="view_inv_date")
                            st.text_input("Invoice Location", value=selected_invoice.get('Invoice Location', ''), disabled=True, key="view_inv_loc")
                    
                        with col2:
                            st.text_input("Contract Number", value=selected_invoice.get('Contract Number', ''), disabled=True, key="view_inv_contract")
                            st.text_input("Work Order Number", value=selected_invoice.get('Work-Order Number', ''), disabled=True, key="view_inv_wo")
                            st.text_input("Sub-Contract Number", value=selected_invoice.get('Sub-Contract Number', ''), disabled=True, key="view_inv_sub")
                    
                        with col3:
                            st.number_input("Invoice Value", value=selected_invoice.get('Invoice Value', 0.0), disabled=True, key="view_inv_val")
                            st.number_input("Invoice GST (%)", value=selected_invoice.get('Invoice GST', 0.0), disabled=True, key="view_inv_gst")
                            st.text_input("Payment Status", value=selected_invoice.get('PaymentStatus', 'Pending'), disabled=True, key="view_inv_status")
                
                        st.markdown("#### Item Information")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.text_input("Item Name", value=selected_invoice.get('Item Name', ''), disabled=True, key="view_item_name")
                            st.text_input("Category", value=selected_invoice.get('Category', ''), disabled=True, key="view_item_cat")
                    
                        with col2:
                            st.text_input("Item Location", value=selected_invoice.get('Item Location', ''), disabled=True, key="view_item_loc")
                            st.number_input("Quantity", value=selected_invoice.get('Quantity', 0), disabled=True, key="view_item_qty")
                    
                        with col3:
                            st.number_input("Value per Item", value=selected_invoice.get('Value per Item', 0.0), disabled=True, key="view_item_val")
                            st.number_input("Item Value", value=selected_invoice.get('Item Value', 0.0), disabled=True, key="view_total_val")
                    
                        with col4:
                            st.number_input("Admissible Amount", value=selected_invoice.get('Admissible Amount', 0.0), disabled=True, key="view_adm_amt")
                            st.number_input("Payable Amount", value=selected_invoice.get('Payable Amount', 0.0), disabled=True, key="view_pay_amt")
                    
                
                    elif invoice_action == "Edit Details":
                        st.markdown("---")
                        st.markdown("#### Edit Invoice Details")
                    
                        with st.form("edit_invoice_form"):
                            st.markdown("##### Basic Information")
                            col1, col2, col3 = st.columns(3)
                        
                            with col1:
                                edit_invoice_location = st.text_input("Invoice Location", value=selected_invoice.get('Invoice Location', ''))
                                edit_invoice_value = st.number_input(
                                    "Invoice Value ₹", 
                                    value=float(selected_invoice.get('Invoice Value', 0.0)),
                                    min_value=0.0,
                                    step=1.0000,
                                    format="%.4f"
                                )
                        
                            with col2:
                                edit_invoice_gst = st.number_input(
                                "Invoice GST (%)", 
                                value=float(selected_invoice.get('Invoice GST', 0.0)),
                                min_value=0.0,
                                max_value=100.0,
                                step=0.01,
                                format="%.2f"
                                )
                                edit_admissible = st.number_input(
                                "Admissible Amount ₹", 
                                value=float(selected_invoice.get('Admissible Amount', 0.0)),
                                min_value=0.0,
                                step=1.0000,
                                format="%.4f"
                            )
                        
                            with col3:
                                available_quantities = []
                                for wo in st.session_state.get('work_orders', []):
                                    if (wo.get('Contract Number') == selected_inv_contract and 
                                        wo.get('Work-Order Number') == selected_inv_workorder and 
                                        wo.get('Sub-Contract Number') == selected_inv_subcontract):
                                        for item in wo.get('Items', []):
                                            if item.get('Item Name') == selected_inv_item:
                                                max_qty = item.get('Qty', 1)
                                                available_quantities = list(range(1, max_qty + 1))
                                                break
                            
                                if not available_quantities:
                                    available_quantities = [1]
                            
                                current_qty = selected_invoice.get('Quantity', 1)
                                if current_qty not in available_quantities:
                                        available_quantities.append(current_qty)
                                        available_quantities.sort()
                            
                                edit_quantity = st.selectbox(
                                "Quantity", 
                                options=available_quantities,
                                index=available_quantities.index(current_qty) if current_qty in available_quantities else 0
                                )
                        
                            submit_edit_invoice = st.form_submit_button("Update Invoice Details")
                        
                            if submit_edit_invoice:
                            # Update invoice details (excluding process tracking and financial information)
                                st.session_state['invoices'][selected_invoice_index].update({
                                'Invoice Location': edit_invoice_location,
                                'Invoice Value': edit_invoice_value,
                                'Invoice GST': edit_invoice_gst,
                                'Admissible Amount': edit_admissible,
                                'Quantity': edit_quantity,
                                })
                                st.success("Invoice details updated successfully!")
                                st.rerun()

                
                    elif invoice_action == "Update Payment":
                        st.markdown("---")
                        cupp1, cupp2 = st.columns(2)
                        cupp1.markdown("##### Update Payment Details")
                        current_status = selected_invoice.get('PaymentStatus', 'Pending')
                        cupp1.info(f"Current Payment Status: **{current_status}**")  
                        # Show info about claimed milestones that are pending
                        claimed_milestones_list = selected_invoice.get('Claimed Milestones', [])
                        if isinstance(claimed_milestones_list, str):
                            try:
                               claimed_milestones_list = ast.literal_eval(claimed_milestones_list)
                            except:
                                claimed_milestones_list = [claimed_milestones_list] if claimed_milestones_list else []    
                        
                        cupp2.markdown("##### Claimed Milestones Information")
                        
                        if claimed_milestones_list:
                            cupp2.success(f"**{len(claimed_milestones_list)} Milestone(s) Claimed:** {', '.join(claimed_milestones_list)}")
                            milestone_type = selected_invoice.get('Selected Milestone Type', '')
                            if milestone_type:
                                cupp2.info(f"**Milestone Type:** {milestone_type}")      

                        else:
                            cupp2.warning("⚠️ No milestones claimed for this invoice. Payment updates require milestone selection.")
    
                        milestone_options = []
                        milestone_data = {}
    
                        for milestone in claimed_milestones_list:
                            milestone_key = f"milestone_{milestone.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct')}"
        
                            existing_ro_num = selected_invoice.get(f'{milestone_key}_RO_Number', '')
                            existing_ro_date = selected_invoice.get(f'{milestone_key}_RO_Date', '')
        
                            status = "✅ Processed" if existing_ro_num else "⏳ Pending"
                            option_display = f"{milestone} - {status}"
                            milestone_options.append((option_display, milestone))
        
                            milestone_data[milestone] = {
                                'key': milestone_key,
                                'ro_number': existing_ro_num,
                                'ro_date': existing_ro_date,
                                'status': status
                            }

                        st.markdown("##### Process Tracking Dates")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        selected_milestone_display = col1.selectbox(
                            "**Select Milestone to Update**",
                            options=[opt[0] for opt in milestone_options],
                            key="update_milestone_select",
                            help="Select a milestone to update its payment details"
                        )
                    
                        selected_milestone = next((milestone for display, milestone in milestone_options if display == selected_milestone_display), None)
                        if selected_milestone:
                            milestone_key = milestone_data[selected_milestone]['key']
        
                            current_submission_date = selected_invoice.get(f'{milestone_key}_Submission_Date', selected_invoice.get('Date of Invoice SUBMISSION', ''))
                            current_received_date = selected_invoice.get(f'{milestone_key}_Received_Date', selected_invoice.get('Date of Invoice RECEIVED at TMD', ''))
                            current_artifacts_date = selected_invoice.get(f'{milestone_key}_Artifacts_Date', selected_invoice.get('Complete ARTIFACTS Receiving Date', ''))
                            current_pqp = selected_invoice.get(f'{milestone_key}_PQP', selected_invoice.get('PQP/ Planned Claim (₹)', 0.0))
                            current_pqp_gst = selected_invoice.get(f'{milestone_key}_PQP_GST', selected_invoice.get('PQP (With GST)', 0.0))
                            current_claimed = selected_invoice.get(f'{milestone_key}_Claimed', selected_invoice.get('Claimed Value (₹)', 0.0))
                            current_claimed_gst = selected_invoice.get(f'{milestone_key}_Claimed_GST', selected_invoice.get('Claimed Value (₹) (With GST)', 0.0))
                            current_ld_pct = selected_invoice.get(f'{milestone_key}_LD_Pct', selected_invoice.get('Liquidity Damage (%)', 0.0))
                            current_ld_applied = selected_invoice.get(f'{milestone_key}_LD_Applied', selected_invoice.get('LD Applied On', ''))
                            current_ld_amount = selected_invoice.get(f'{milestone_key}_LD_Amount', selected_invoice.get('LD Amount (₹)', 0.0))
                            current_payable = selected_invoice.get(f'{milestone_key}_Payable', selected_invoice.get('Payable Amount', 0.0))
                            current_payable_gst = selected_invoice.get(f'{milestone_key}_Payable_GST', selected_invoice.get('Payable Amount (With GST)', 0.0))
                            current_ro_number = selected_invoice.get(f'{milestone_key}_RO_Number', selected_invoice.get('Release Order Number', ''))
                            current_ro_amount = selected_invoice.get(f'{milestone_key}_RO_Amount', selected_invoice.get('Release Order Amount', 0.0))
                            current_ro_amount_gst = selected_invoice.get(f'{milestone_key}_RO_Amount_GST', selected_invoice.get('Release Order Amount (With GST)', 0.0))
                            current_ro_date = selected_invoice.get(f'{milestone_key}_RO_Date', selected_invoice.get('Date of RELEASE ORDER', ''))
        
        
                            with col2:
                                try:
                                    submission_date_obj = datetime.strptime(current_submission_date, "%d/%m/%Y").date() if current_submission_date else date.today()
                                except:
                                    submission_date_obj = date.today()
            
                                submission_date = st.date_input(
                                    "Date of Invoice SUBMISSION",
                                    value=submission_date_obj,
                                    format="DD/MM/YYYY",
                                    key=f"milestone_submission_{milestone_key}"
                                )
        
                            with col3:
                                try:
                                    received_date_obj = datetime.strptime(current_received_date, "%d/%m/%Y").date() if current_received_date else date.today()
                                except:
                                    received_date_obj = date.today()
            
                                received_date = st.date_input(
                                    "Date of Invoice RECEIVED at TMD",
                                    value=received_date_obj,
                                    format="DD/MM/YYYY",
                                    key=f"milestone_received_{milestone_key}"
                                )
        
                            with col4:
                                try:
                                        artifacts_date_obj = datetime.strptime(current_artifacts_date, "%d/%m/%Y").date() if current_artifacts_date else date.today()
                                except:
                                        artifacts_date_obj = date.today()
            
                                artifacts_date = st.date_input(
                                        "Complete ARTIFACTS Receiving Date",
                                        value=artifacts_date_obj,
                                        format="DD/MM/YYYY",
                                        key=f"milestone_artifacts_{milestone_key}"
                                )
        
        
                            st.markdown("##### Financial Information")
                            col1, col2, col3, col4, col5 = st.columns(5)
        
                            with col1:
                                    pqp_planned = st.number_input(
                                        "PQP/ Planned Claim (₹)",
                                        value=float(current_pqp),
                                        min_value=0.0,
                                        step=1.0000,
                                        format="%.4f",
                                        key=f"milestone_pqp_{milestone_key}"
                                        )
            
                                    invoice_gst = selected_invoice.get('Invoice GST', 0.0)
                                    pqp_with_gst = pqp_planned * (1 + invoice_gst/100)
                                    st.caption(f"PQP (With GST): {format_indian_currency(pqp_with_gst)}")
        
                            with col2:
                                    claimed_value = st.number_input(
                                        "Claimed Value (₹)",
                                        value=float(current_claimed),
                                        min_value=0.0, step=1.0000, format="%.4f",
                                        key=f"milestone_claimed_{milestone_key}"
                                    )
                                    claimed_with_gst = claimed_value * (1 + invoice_gst/100)
                                    if claimed_value > pqp_planned and pqp_planned > 0:
                                        st.caption(f"⚠️ Claimed Value exceeds PQP: {format_indian_currency(pqp_planned)}")
                                    else: 
                                        st.caption(f"Claimed (With GST): {format_indian_currency(claimed_with_gst)}")
        
                            with col3:
                                    ld_percentage = st.number_input(
                                        "Liquidity Damage (%)",
                                        value=float(current_ld_pct),
                                        min_value=0.0, max_value=100.0, step=0.0001,
                                        format="%.12f",
                                        key=f"milestone_ld_pct_{milestone_key}"
                                    )
            
                                    ld_applied_options = ["PQP", "Claimed"]
                                    current_ld_index = 0
                                    if current_ld_applied in ld_applied_options:
                                        current_ld_index = ld_applied_options.index(current_ld_applied)
            
                                    ld_applied_on = st.selectbox(
                                        "LD Applied On",
                                        options=ld_applied_options,
                                        index=current_ld_index,
                                        key=f"milestone_ld_applied_{milestone_key}"
                                    )
        
                            with col4:
                                    if ld_percentage > 0:
                                        if ld_applied_on == "PQP":
                                            auto_ld_amount = pqp_planned * (ld_percentage / 100)
                                        else:
                                            auto_ld_amount = claimed_value * (ld_percentage / 100)
                                    else:
                                        auto_ld_amount = 0.0
            
                                    ld_amount = st.number_input(
                                        "LD Amount (₹)",
                                        value=auto_ld_amount,
                                        min_value=0.0,
                                        step=0.000000000001,
                                        format="%.12f",
                                        key=f"milestone_ld_amount_{milestone_key}"
                                    )
                                    
                                    ld_reason = ""
                                    if ld_percentage > 0 or ld_amount > 0:
                                        ld_reason = st.text_input("**Reason** for Liquidity Damage", key=f"milestone_ld_reason_{milestone_key}")
                                        
        
                            with col5:
                                if ld_applied_on == "PQP":
                                        auto_payable = pqp_planned - ld_amount
                                else:  # Claimed
                                        auto_payable = claimed_value - ld_amount
                                    
                                payable_amount = st.number_input(
                                    "Payable Amount",
                                    value=max(0.0, auto_payable),
                                    min_value=0.0,
                                    step=1.0000,
                                    format="%.4f",
                                    key=f"milestone_payable_{milestone_key}"
                                )
            
                                payable_with_gst = payable_amount * (1 + invoice_gst/100)
                                st.caption(f"Payable (With GST): {format_indian_currency(payable_with_gst)}")
        
                                admissible_amount = selected_invoice.get('Admissible Amount', 0.0)
                                if payable_amount > admissible_amount:
                                    st.caption(f"⚠️ Exceeds Admissible Amount: {format_indian_currency(admissible_amount)}")
                                
        
        
                            st.markdown("##### Release Order Information")
                            col1, col2, col3, col4, col5 = st.columns(5)
        
                            with col1:
                                    ro_number = st.text_input(
                                        "Release Order Number",
                                        value=current_ro_number,
                                        key=f"milestone_ro_number_{milestone_key}"
                                    )
        
                            with col2:
                                    ro_amount = st.number_input(
                                        "Release Order Amount",
                                        value=float(current_ro_amount) if current_ro_amount else payable_amount,
                                        min_value=0.0,
                                        step=1.0000,
                                        format="%.4f",
                                        key=f"milestone_ro_amount_{milestone_key}"
                                    )
            
          
                                    ro_amount_with_gst = ro_amount * (1 + invoice_gst/100)
                                    st.caption(f"RO Amount (With GST): {format_indian_currency(ro_amount_with_gst)}")
        
                            with col3:
                                    try:
                                        ro_date_obj = datetime.strptime(current_ro_date, "%d/%m/%Y").date() if current_ro_date else None
                                    except:
                                        ro_date_obj = None
            
                                    ro_date = st.date_input(
                                        "Date of RELEASE ORDER",
                                        value=ro_date_obj,
                                        format="DD/MM/YYYY",
                                        key=f"milestone_ro_date_{milestone_key}"
                                    )

                            with col4:
                                ro_days_reason = ""
                                ro_noOfDays = calculate_days(ro_date.strftime("%d/%m/%Y") if ro_date else None, receive_date.strftime("%d/%m/%Y"))
                                if ro_noOfDays is not None:
                                    if ro_noOfDays > 30:
                                        ro_days_reason = st.text_input("**Reason** for Delay", key=f"milestone_ro_delay_reason_{milestone_key}")
                                
        
                            col1, col2 = st.columns([2.5, 1.5])
        
                            with col1:
                                    if st.button(f"Update {selected_milestone} Details", type="primary", key=f"update_milestone_{milestone_key}"):
                                        if not ro_number:
                                            st.error("Release Order Number is required!")
                                        elif ro_amount <= 0:
                                                st.error("Release Order Amount must be greater than 0!")
                                        elif ro_amount > payable_amount:
                                            st.error("Release Order Amount cannot exceed Payable Amount!")
                                        elif not ro_date:
                                            st.error("Release Order Date is required!")
                                        else:
                                            try:
                                                days_between = (ro_date - received_date).days
                                            except:     
                                                days_between = 0
                    
                    
                                            milestone_updates = {
                                                f'{milestone_key}_Submission_Date': submission_date.strftime("%d/%m/%Y"),
                                                f'{milestone_key}_Received_Date': received_date.strftime("%d/%m/%Y"),
                                                f'{milestone_key}_Artifacts_Date': artifacts_date.strftime("%d/%m/%Y"),
                                                f'{milestone_key}_PQP': pqp_planned,
                                                f'{milestone_key}_PQP_GST': pqp_with_gst,
                                                f'{milestone_key}_Claimed': claimed_value,
                                                f'{milestone_key}_Claimed_GST': claimed_with_gst,
                                                f'{milestone_key}_LD_Pct': ld_percentage,
                                                f'{milestone_key}_LD_Applied': ld_applied_on,
                                                f'{milestone_key}_LD_Amount': ld_amount,
                                                f'{milestone_key}_LD_Reason': ld_reason,
                                                f'{milestone_key}_Payable': payable_amount,
                                                f'{milestone_key}_Payable_GST': payable_with_gst,
                                                f'{milestone_key}_RO_Number': ro_number,
                                                f'{milestone_key}_RO_Amount': ro_amount,
                                                f'{milestone_key}_RO_Amount_GST': ro_amount_with_gst,
                                                f'{milestone_key}_RO_Date': ro_date.strftime("%d/%m/%Y"),
                                                f'{milestone_key}_Days_Between': days_between,
                                                f'{milestone_key}_RO_Delay_Reason': ro_days_reason,
                                                f'{milestone_key}_Status': 'Processed',
                                                
                                            }
                    
                                            st.session_state['invoices'][selected_invoice_index].update(milestone_updates)
                                            all_processed = True
                                            for milestone in claimed_milestones_list:
                                                m_key = f"milestone_{milestone.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct')}"
                                                if not st.session_state['invoices'][selected_invoice_index].get(f'{m_key}_RO_Number'):
                                                    all_processed = False
                                                    break
                    
                                            if all_processed:
                                                st.session_state['invoices'][selected_invoice_index]['PaymentStatus'] = 'Processed'
                                            else:
                                                st.session_state['invoices'][selected_invoice_index]['PaymentStatus'] = 'Partially Processed'
                    
                                            st.success(f"✅ {selected_milestone} payment details updated successfully!")
                                            st.success(f"Release Order {ro_number} issued for {format_indian_currency(ro_amount)}")
                    
                                            if days_between > 30:
                                                st.warning(f"⚠️ Payment delayed by {days_between} days (> 30 days)")
                            
                                            st.rerun()
        
                            with col2:
                                if st.button("Clear Milestone Data", key=f"clear_milestone_{milestone_key}"):
                                    keys_to_clear = [k for k in st.session_state['invoices'][selected_invoice_index].keys() if k.startswith(milestone_key)]
                                    for key in keys_to_clear:
                                        del st.session_state['invoices'][selected_invoice_index][key]
                
                                    st.success(f"✅ {selected_milestone} data cleared!")
                                    st.rerun()


                    elif invoice_action == "Delete Invoice":
                        st.markdown("---")
                        st.markdown("#### Delete Invoice")
                        st.warning("⚠️ This action will permanently delete the invoice!")
                    
                        st.markdown("##### Invoice to Delete:")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"Invoice Number: {selected_invoice.get('Invoice Number', '')}")
                            st.text(f"Contract: {selected_invoice.get('Contract Number', '')}")
                    
                        with col2:
                            st.text(f"Work Order: {selected_invoice.get('Work-Order Number', '')}")
                            st.text(f"Item: {selected_invoice.get('Item Name', '')}")
                    
                        with col3:
                            st.text(f"Invoice Value: ₹{selected_invoice.get('Invoice Value', 0):,.2f}")
                            st.text(f"Status: {selected_invoice.get('PaymentStatus', 'Pending')}")
                    
                        st.text_input(
                            "Type 'DELETE' to confirm deletion:",
                            key="delete_invoice_confirmation",
                            placeholder="Type DELETE here..."
                        )
                    
                        invoice_confirmation_text = st.session_state.get("delete_invoice_confirmation", "")
                    
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                            "🗑️ Permanently Delete Invoice", type="primary",
                            disabled=(invoice_confirmation_text.upper() != "DELETE"), key="confirm_delete_invoice"
                            ):
                            # Delete invoice
                                st.session_state['invoices'].pop(selected_invoice_index)
                                st.success("✅ Invoice deleted successfully!")
                                st.rerun()
                    
                        with col2:
                            st.button("Cancel", key="cancel_delete_invoice")


# --------- PAYMENT SCHEDULE ---------
with tabs[4]:
    st.markdown("#### Payment Schedule & Milestone Tracking")
    
    if not st.session_state.get('invoices'):
        st.info("No invoices available. Create invoices first to see payment schedules.")
    else:
        # Tab selection for different schedule views
        schedule_type = st.radio(
            "Schedule View:",
            options=["📅 Upcoming Payments", "⏰ Overdue Payments", "✅ Completed Payments", "📊 Payment Calendar"],
            horizontal=True
        )
        
        invoices = st.session_state['invoices']
        current_date = datetime.now().date()
        
        if schedule_type == "📅 Upcoming Payments":
            st.markdown("### Upcoming Payment Schedule")
            
            upcoming_payments = []
            for invoice in invoices:
                if invoice.get('Payment_Status', 'Pending') == 'Pending':
                    category = invoice.get('Category', '')
                    
                    # Extract payment milestones based on category
                    if category in ['Hardware', 'Hardware (+ AMC)']:
                        # Warranty milestones
                        warranty_period = invoice.get('Warranty Claiming Period', 'Annually')
                        warranty_duration = invoice.get('Warranty Duration (Months)', 36)
                        warranty_amount = invoice.get('Warranty Amount', 0)
                        
                        if warranty_amount > 0:
                            warranty_milestones = generate_warranty_milestones(
                                warranty_period, warranty_duration, 
                                invoice.get('Warranty (%)', 0), warranty_amount
                            )
                            for milestone, amount in warranty_milestones:
                                upcoming_payments.append({
                                    'Invoice': invoice.get('Invoice Number', ''),
                                    'Contract': invoice.get('Contract Number', ''),
                                    'Milestone': milestone,
                                    'Amount': amount,
                                    'Due Date': 'TBD',  # You can calculate based on contract dates
                                    'Category': category,
                                    'Status': 'Pending'
                                })
                    
                    elif category in ['AMC', 'Hardware (+ AMC)']:
                        # AMC milestones
                        amc_period = invoice.get('AMC Claiming Period', 'Quarterly')
                        amc_duration = invoice.get('AMC Duration (Months)', 48)
                        amc_amount = invoice.get('AMC Amount', 0)
                        
                        if amc_amount > 0:
                            amc_milestones = generate_amc_milestones(
                                amc_period, amc_duration, 
                                invoice.get('AMC (%)', 0), amc_amount
                            )
                            for milestone, amount in amc_milestones:
                                upcoming_payments.append({
                                    'Invoice': invoice.get('Invoice Number', ''),
                                    'Contract': invoice.get('Contract Number', ''),
                                    'Milestone': milestone,
                                    'Amount': amount,
                                    'Due Date': 'TBD',
                                    'Category': category,
                                    'Status': 'Pending'
                                })
            
            if upcoming_payments:
                upcoming_df = pd.DataFrame(upcoming_payments)
                upcoming_df['Amount'] = upcoming_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(style_alternate_rows(upcoming_df), use_container_width=True, hide_index=True)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Upcoming Payments", len(upcoming_payments))
                with col2:
                    try:
                        total_upcoming = 0.0
                        for p in upcoming_payments:
                            amount_str = ""
                            if 'Amount' in p:
                                amount_str = str(p['Amount'])
                            elif 'Payable Amount' in p:
                                amount_str = str(p['Payable Amount'])
                            elif 'Invoice Value' in p:
                                amount_str = str(p['Invoice Value'])
                            elif 'Release Order Amount' in p:
                                amount_str = str(p['Release Order Amount'])
                            else:
                                continue
                            if amount_str:
                                clean_amount = amount_str.replace('₹', '').replace(',', '').strip()
                                if clean_amount:
                                    try:
                                        total_upcoming += float(clean_amount)
                                    except ValueError:
                                        continue

                    except Exception as e:
                        st.error(f"Error calculating upcoming payments: {str(e)}")
                        total_upcoming = 0.0
                        
                    st.metric("Total Amount", f"₹{total_upcoming:,.2f}")
                    with col3:
                        unique_contracts = len(set([p['Contract'] for p in upcoming_payments]))
                        st.metric("Contracts", unique_contracts)
            else:
                st.info("No upcoming payments found.")
        
        elif schedule_type == "⏰ Overdue Payments":
            st.markdown("### Overdue Payments")
            
            overdue_payments = []
            for invoice in invoices:
                ro_date = invoice.get('Date of RELEASE ORDER', '')
                if ro_date and invoice.get('Payment_Status', 'Pending') == 'Pending':
                    try:
                        ro_date_obj = datetime.strptime(ro_date, "%d/%m/%Y").date()
                        days_overdue = (current_date - ro_date_obj).days
                        
                        if days_overdue > 30:  # Consider overdue after 30 days
                            overdue_payments.append({
                                'Invoice': invoice.get('Invoice Number', ''),
                                'Contract': invoice.get('Contract Number', ''),
                                'RO Date': ro_date,
                                'Days Overdue': days_overdue,
                                'RO Amount': f"₹{invoice.get('Release Order Amount', 0):,.2f}",
                                'Category': invoice.get('Category', ''),
                                'Vendor': invoice.get('Vendor', '')
                            })
                    except:
                        pass
            
            if overdue_payments:
                overdue_df = pd.DataFrame(overdue_payments)
                st.dataframe(style_alternate_rows(overdue_df), use_container_width=True, hide_index=True)
                
                # Alert for critical overdue
                critical_overdue = [p for p in overdue_payments if p['Days Overdue'] > 90]
                if critical_overdue:
                    st.error(f"🚨 {len(critical_overdue)} payments are critically overdue (>90 days)")
            else:
                st.success("✅ No overdue payments found.")
        
        elif schedule_type == "✅ Completed Payments":
            st.markdown("### Completed Payments")
            
            completed_payments = []
            for invoice in invoices:
                if invoice.get('Payment_Status', 'Pending') == 'Paid':
                    completed_payments.append({
                        'Invoice': invoice.get('Invoice Number', ''),
                        'Contract': invoice.get('Contract Number', ''),
                        'RO Number': invoice.get('Release Order Number', ''),
                        'RO Date': invoice.get('Date of RELEASE ORDER', ''),
                        'Amount Paid': f"₹{invoice.get('Release Order Amount', 0):,.2f}",
                        'Category': invoice.get('Category', ''),
                        'Vendor': invoice.get('Vendor', '')
                    })
            
            if completed_payments:
                completed_df = pd.DataFrame(completed_payments)
                completed_df_fy = add_financial_year_columns(completed_df)
                st.dataframe(style_alternate_rows(completed_df_fy), use_container_width=True, hide_index=True)
                
                total_paid = sum([invoice.get('Release Order Amount', 0) for invoice in invoices if invoice.get('Payment_Status') == 'Paid'])
                st.success(f"💰 Total Payments Completed: ₹{total_paid:,.2f}")
            else:
                st.info("No completed payments found.")
        
        else:  # Payment Calendar
            st.markdown("### Payment Calendar View")
            
            # Monthly payment summary
            monthly_payments = {}
            for invoice in invoices:
                ro_date = invoice.get('Date of RELEASE ORDER', '')
                if ro_date:
                    try:
                        ro_date_obj = datetime.strptime(ro_date, "%d/%m/%Y").date()
                        month_key = ro_date_obj.strftime("%Y-%m")
                        
                        if month_key not in monthly_payments:
                            monthly_payments[month_key] = {'count': 0, 'amount': 0}
                        
                        monthly_payments[month_key]['count'] += 1
                        monthly_payments[month_key]['amount'] += invoice.get('Release Order Amount', 0)
                    except:
                        pass
            
            if monthly_payments:
                calendar_data = []
                for month, data in sorted(monthly_payments.items()):
                    calendar_data.append({
                        'Month': datetime.strptime(month, "%Y-%m").strftime("%B %Y"),
                        'Payments Count': data['count'],
                        'Total Amount': f"₹{data['amount']:,.2f}"
                    })
                
                calendar_df = pd.DataFrame(calendar_data)
                st.dataframe(style_alternate_rows(calendar_df), use_container_width=True, hide_index=True)
            else:
                st.info("No payment calendar data available.")


# --------- ANALYTICS ---------
with tabs[5]:
    st.markdown("#### Financial Analytics & Insights")
    
    work_orders = st.session_state.get('work_orders', [])
    invoices = st.session_state.get('invoices', [])
    
    if not work_orders and not invoices:
        st.info("📊 No data available for analytics. Create work orders and invoices to see comprehensive insights.")
    else:
        # Analytics Navigation
        analytics_view = st.selectbox(
            "Select Analytics View:",
            options=[
                "📈 Financial Overview", 
                "📊 Category Analysis",
                "⏱️ Performance Metrics",
                "💰 Payment Analysis",
                "📅 Timeline Analysis",
                "🎯 Milestone Tracking"
            ]
        )
        
        if analytics_view == "📈 Financial Overview":
            st.markdown("### Financial Overview Dashboard")
            
            # Key Financial Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_contracts = len(work_orders)
            total_contract_value = sum([wo.get('Total Contract Value (with GST)', 0) for wo in work_orders])
            total_invoices = len(invoices)
            total_invoice_value = sum([inv.get('Invoice Value', 0) for inv in invoices])
            
            with col1:
                st.metric("Total Contracts", f"{total_contracts:,}")
            with col2:
                st.metric("Contract Value", f"₹{total_contract_value:,.0f}")
            with col3:
                st.metric("Total Invoices", f"{total_invoices:,}")
            with col4:
                st.metric("Invoice Value", f"₹{total_invoice_value:,.0f}")
            
            # Revenue vs Claims Analysis
            st.markdown("#### Revenue vs Claims Analysis")
            col1, col2 = st.columns(2)
            
            with col1:
                total_claimed = sum([inv.get('Claimed Value', 0) for inv in invoices])
                total_payable = sum([inv.get('Payable Amount', 0) for inv in invoices])
                total_ld = sum([inv.get('LD Amount', 0) for inv in invoices])
                
                revenue_data = {
                    'Metric': ['Total Claimed', 'Total Payable', 'LD Deductions', 'Net Revenue'],
                    'Amount': [total_claimed, total_payable, total_ld, total_payable - total_ld],
                    'Formatted': [f"₹{total_claimed:,.2f}", f"₹{total_payable:,.2f}", 
                                f"₹{total_ld:,.2f}", f"₹{(total_payable - total_ld):,.2f}"]
                }
                
                revenue_df = pd.DataFrame(revenue_data)
                st.dataframe(style_alternate_rows(revenue_df[['Metric', 'Formatted']]), hide_index=True, use_container_width=True)
            
            with col2:
                # Payment Status Distribution
                payment_status_counts = {}
                for inv in invoices:
                    status = inv.get('Payment_Status', 'Pending')
                    payment_status_counts[status] = payment_status_counts.get(status, 0) + 1
                
                if payment_status_counts:
                    status_data = {
                        'Status': list(payment_status_counts.keys()),
                        'Count': list(payment_status_counts.values())
                    }
                    status_df = pd.DataFrame(status_data)
                    status_df_fy = add_financial_year_columns(status_df)
                    st.dataframe(style_alternate_rows(status_df_fy), hide_index=True, use_container_width=True)
        
        elif analytics_view == "📊 Category Analysis":
            st.markdown("### Category-wise Analysis")
            
            # Category distribution from work orders
            category_analysis = {}
            
            for wo in work_orders:
                for item in wo.get('Items', []):
                    category = item.get('Category', 'Others')
                    if category not in category_analysis:
                        category_analysis[category] = {
                            'wo_count': 0,
                            'wo_value': 0,
                            'item_count': 0,
                            'inv_count': 0,
                            'inv_value': 0
                        }
                    
                    category_analysis[category]['wo_count'] += 1
                    category_analysis[category]['wo_value'] += item.get('₹ with GST', 0)
                    category_analysis[category]['item_count'] += item.get('Qty', 0)
            
            # Add invoice data
            for inv in invoices:
                category = inv.get('Category', 'Others')
                if category in category_analysis:
                    category_analysis[category]['inv_count'] += 1
                    category_analysis[category]['inv_value'] += inv.get('Payable Amount', 0)
            
            # Create category analysis table
            if category_analysis:
                category_data = []
                for category, data in category_analysis.items():
                    category_data.append({
                        'Category': category,
                        'WO Items': data['wo_count'],
                        'WO Value': f"₹{data['wo_value']:,.2f}",
                        'Total Items': data['item_count'],
                        'Invoices': data['inv_count'],
                        'Invoice Value': f"₹{data['inv_value']:,.2f}",
                        'Utilization %': f"{(data['inv_value'] / data['wo_value'] * 100):.1f}%" if data['wo_value'] > 0 else "0%"
                    })
                
                category_df = pd.DataFrame(category_data)
                category_df_fy = add_financial_year_columns(category_df)
                st.dataframe(style_alternate_rows(category_df_fy), hide_index=True, use_container_width=True)
                
                # Top categories by value
                st.markdown("#### Top Categories by Value")
                sorted_categories = sorted(category_analysis.items(), 
                                         key=lambda x: x[1]['wo_value'], reverse=True)[:5]
                
                for i, (category, data) in enumerate(sorted_categories, 1):
                    st.markdown(f"{i}. **{category}**: ₹{data['wo_value']:,.2f} ({data['wo_count']} items)")
        
        elif analytics_view == "⏱️ Performance Metrics":
            st.markdown("### Performance Metrics")
            
            # Calculate performance metrics
            if invoices:
                # Payment processing time analysis
                processing_times = []
                for inv in invoices:
                    submit_date = inv.get('Date of Invoice SUBMISSION', '')
                    ro_date = inv.get('Date of RELEASE ORDER', '')
                    
                    if submit_date and ro_date:
                        try:
                            submit_dt = datetime.strptime(submit_date, "%d/%m/%Y")
                            ro_dt = datetime.strptime(ro_date, "%d/%m/%Y")
                            days_diff = (ro_dt - submit_dt).days
                            processing_times.append(days_diff)
                        except:
                            pass
                
                if processing_times:
                    avg_processing = sum(processing_times) / len(processing_times)
                    min_processing = min(processing_times)
                    max_processing = max(processing_times)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Avg Processing Time", f"{avg_processing:.1f} days")
                    with col2:
                        st.metric("Fastest Processing", f"{min_processing} days")
                    with col3:
                        st.metric("Slowest Processing", f"{max_processing} days")
                
                # Efficiency metrics
                st.markdown("#### Efficiency Metrics")
                
                total_admissible = sum([inv.get('Admissible Amount', 0) for inv in invoices])
                total_claimed = sum([inv.get('Claimed Value', 0) for inv in invoices])
                total_payable = sum([inv.get('Payable Amount', 0) for inv in invoices])
                
                claim_efficiency = (total_claimed / total_admissible * 100) if total_admissible > 0 else 0
                approval_rate = (total_payable / total_claimed * 100) if total_claimed > 0 else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Claim Efficiency", f"{claim_efficiency:.1f}%", 
                             help="Percentage of admissible amount claimed")
                with col2:
                    st.metric("Approval Rate", f"{approval_rate:.1f}%",
                             help="Percentage of claimed amount approved")

    st.markdown("#### Reports & Data Export")
    
    if not st.session_state.get('work_orders') and not st.session_state.get('invoices'):
        st.info("No data available for reports. Create work orders and invoices first.")
    else:
        report_type = st.selectbox(
            "Select Report Type:",
            options=[
                "📋 Complete Work Orders Report",
                "🧾 Complete Invoices Report", 
                "💰 Financial Summary Report",
                "📊 Category Analysis Report",
                "⏱️ Payment Status Report",
                "📈 Performance Metrics Report",
                "🔍 Custom Filtered Report"
            ]
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            export_format = st.selectbox("Export Format:", ["CSV", "Excel"])
            
        with col1:
            if st.button("📥 Generate & Download Report", type="primary", use_container_width=True):
                if report_type == "📋 Complete Work Orders Report":
                    # Generate comprehensive work orders report
                    if st.session_state.get('work_orders'):
                        wo_report_data = []
                        for wo in st.session_state['work_orders']:
                            base_data = {
                                'Contract Number': wo.get('Contract Number', ''),
                                'Vendor': wo.get('Vendor', ''),
                                'Location': wo.get('Location', ''),
                                'Contract Date': wo.get('Contract Date', ''),
                                'Contract Value': wo.get('Contract Value', 0),
                                'GST (%)': wo.get('GST (%)', 0),
                                'Total Contract Value (with GST)': wo.get('Total Contract Value (with GST)', 0),
                                'Work-Order Number': wo.get('Work-Order Number', ''),
                                '% Work-Order': wo.get('% Work-Order', 0),
                                'Work-Order Value (with GST)': wo.get('Work-Order Value (with GST)', 0),
                                'Sub-Contract Number': wo.get('Sub-Contract Number', ''),
                                'Item(s) Count': wo.get('Item(s) Count', 0),
                                'Created Date': wo.get('Created', '')
                            }
                            
                            items = wo.get('Items', [])
                            if items:
                                for item in items:
                                    item_data = base_data.copy()
                                    item_data.update({
                                        'Item Name': item.get('Item Name', ''),
                                        'Category': item.get('Category', ''),
                                        'Item Location': item.get('Item Location', ''),
                                        'Quantity': item.get('Qty', 0),
                                        'Value per Item': item.get('Value per Item', 0),
                                        'Item Total (with GST)': item.get('₹ with GST', 0),
                                        'Remark': item.get('Remark', ''),
                                        
                                        # Category-specific fields
                                        'Warranty Duration (Months)': item.get('Warranty Duration (Months)', ''),
                                        'Warranty %': item.get('% Warranty', ''),
                                        'AMC Duration (Months)': item.get('AMC Duration (Months)', ''),
                                        'AMC %': item.get('% AMC', ''),
                                        'Support Duration (Months)': item.get('Support Duration (Months)', ''),
                                        'Staff Duration (Months)': item.get('Staff Duration (Months)', ''),
                                        'Additional Remark': item.get('Additional Remark', '')
                                    })
                                    wo_report_data.append(item_data)
                            else:
                                wo_report_data.append(base_data)
                        
                        # Create and download report
                        df_report = pd.DataFrame(wo_report_data)
                        df_report_fy = add_financial_year_columns(df_report)
                        
                        if export_format == "CSV":
                            csv_data = df_report_fy.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Work Orders CSV",
                                data=csv_data,
                                file_name=f"work_orders_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        else:
                            # Excel export (requires openpyxl)
                            from io import BytesIO
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df_report_fy.to_excel(writer, sheet_name='Work Orders', index=False)
                            
                            st.download_button(
                                label="📥 Download Work Orders Excel",
                                data=output.getvalue(),
                                file_name=f"work_orders_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        st.success(f"✅ Work Orders report generated with {len(wo_report_data)} rows!")
                        st.dataframe(style_alternate_rows(df_report_fy.head()), use_container_width=True)
                
                elif report_type == "🧾 Complete Invoices Report":
                    # Generate comprehensive invoices report
                    if st.session_state.get('invoices'):
                        invoices_report_data = []
                        for invoice in st.session_state['invoices']:
                            invoice_data = {
                                # Basic Information
                                'Invoice Number': invoice.get('Invoice Number', ''),
                                'Date of Invoice': invoice.get('Date of Invoice', ''),
                                'Invoice Location': invoice.get('Invoice Location', ''),
                                'Contract Number': invoice.get('Contract Number', ''),
                                'Work-Order Number': invoice.get('Work-Order Number', ''),
                                'Sub-Contract Number': invoice.get('Sub-Contract Number', ''),
                                'Vendor': invoice.get('Vendor', ''),
                                
                                # Financial Information
                                'Invoice Value': invoice.get('Invoice Value', 0),
                                'Invoice GST (%)': invoice.get('Invoice GST', 0),
                                'Admissible Amount': invoice.get('Admissible Amount', 0),
                                'PQP/Planned Claim': invoice.get('PQP/ Planned Claim', 0),
                                'Claimed Value': invoice.get('Claimed Value', 0),
                                'Liquidity Damage (%)': invoice.get('Liquidity Damage (%)', 0),
                                'LD Amount': invoice.get('LD Amount', 0),
                                'Payable Amount': invoice.get('Payable Amount', 0),
                                'Payable (With GST)': invoice.get('Payable (With GST)', 0),
                                
                                # Item Information
                                'Item Name': invoice.get('Item Name', ''),
                                'Category': invoice.get('Category', ''),
                                'Item Location': invoice.get('Item Location', ''),
                                'Quantity': invoice.get('Quantity', 0),
                                'Value per Item': invoice.get('Value per Item', 0),
                                
                                # Process Tracking
                                'Date of Submission': invoice.get('Date of Invoice SUBMISSION', ''),
                                'Date Received at TMD': invoice.get('Date of Invoice RECEIVED at TMD', ''),
                                'Artifacts Receiving Date': invoice.get('Complete ARTIFACTS Receiving Date', ''),
                                'Release Order Number': invoice.get('Release Order Number', ''),
                                'Release Order Amount': invoice.get('Release Order Amount', 0),
                                'Date of Release Order': invoice.get('Date of RELEASE ORDER', ''),
                                'Payment Status': invoice.get('Payment_Status', 'Pending'),
                                
                                # Category-specific fields
                                'Delivery (%)': invoice.get('Delivery (%)', 0),
                                'UAT Submission (%)': invoice.get('Power ON / UAT Submission (%)', 0),
                                'UAT Completion (%)': invoice.get('UAT Completion (%)', 0),
                                'Warranty (%)': invoice.get('Warranty (%)', 0),
                                'Warranty Duration (Months)': invoice.get('Warranty Duration (Months)', 0),
                                'Warranty Claiming Period': invoice.get('Warranty Claiming Period', ''),
                                'AMC (%)': invoice.get('AMC (%)', 0),
                                'AMC Duration (Months)': invoice.get('AMC Duration (Months)', 0),
                                'AMC Claiming Period': invoice.get('AMC Claiming Period', ''),
                                'AMC Start Date': invoice.get('AMC Start Date', ''),
                                
                                # Metadata
                                'Created Date': invoice.get('Created', ''),
                                'Days Between RO & Receive': invoice.get('Days_Between_RO_Receive', ''),
                                'Payment Remarks': invoice.get('Payment_Remarks', '')
                            }
                            invoices_report_data.append(invoice_data)
                        
                        # Create and download report
                        df_report = pd.DataFrame(invoices_report_data)
                        df_report_fy = add_financial_year_columns(df_report)
                        
                        if export_format == "CSV":
                            csv_data = df_report_fy.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Invoices CSV",
                                data=csv_data,
                                file_name=f"invoices_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        else:
                            from io import BytesIO
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df_report_fy.to_excel(writer, sheet_name='Invoices', index=False)
                            
                            st.download_button(
                                label="📥 Download Invoices Excel",
                                data=output.getvalue(),
                                file_name=f"invoices_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        st.success(f"✅ Invoices report generated with {len(invoices_report_data)} rows!")
                        st.dataframe(style_alternate_rows(df_report_fy.head()), use_container_width=True)
                
                elif report_type == "💰 Financial Summary Report":
                    # Generate financial summary report
                    financial_data = []
                    
                    # Work Orders Summary
                    if st.session_state.get('work_orders'):
                        for wo in st.session_state['work_orders']:
                            financial_data.append({
                                'Type': 'Work Order',
                                'Reference': wo.get('Work-Order Number', ''),
                                'Contract Number': wo.get('Contract Number', ''),
                                'Vendor': wo.get('Vendor', ''),
                                'Contract Value': wo.get('Contract Value', 0),
                                'GST (%)': wo.get('GST (%)', 0),
                                'Total Value (with GST)': wo.get('Total Contract Value (with GST)', 0),
                                'Work Order Value': wo.get('Work-Order Value (with GST)', 0),
                                'Item(s) Count': wo.get('Item(s) Count', 0),
                                'Date': wo.get('Contract Date', ''),
                                'Status': 'Active'
                            })
                    
                    # Invoices Summary
                    if st.session_state.get('invoices'):
                        for invoice in st.session_state['invoices']:
                            financial_data.append({
                                'Type': 'Invoice',
                                'Reference': invoice.get('Invoice Number', ''),
                                'Contract Number': invoice.get('Contract Number', ''),
                                'Vendor': invoice.get('Vendor', ''),
                                'Contract Value': invoice.get('Invoice Value', 0),
                                'GST (%)': invoice.get('Invoice GST', 0),
                                'Total Value (with GST)': invoice.get('Payable (With GST)', 0),
                                'Work Order Value': invoice.get('Admissible Amount', 0),
                                'Item(s) Count': 1,
                                'Date': invoice.get('Date of Invoice', ''),
                                'Status': invoice.get('Payment_Status', 'Pending')
                            })
                    
                    if financial_data:
                        df_financial = pd.DataFrame(financial_data)
                        
                        if export_format == "CSV":
                            csv_data = df_financial.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Financial Summary CSV",
                                data=csv_data,
                                file_name=f"financial_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        
                        st.success(f"✅ Financial summary generated with {len(financial_data)} entries!")
                        st.dataframe(style_alternate_rows(df_financial.head()), use_container_width=True)
                
                
        st.markdown("---")
        st.markdown("#### Quick Data Overview")
        
        # Show summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            wo_count = len(st.session_state.get('work_orders', []))
            st.metric("Work Orders", wo_count)
            
        with col2:
            inv_count = len(st.session_state.get('invoices', []))
            st.metric("Invoices", inv_count)
            
        with col3:
            total_contract_value = sum([wo.get('Total Contract Value (with GST)', 0) for wo in st.session_state.get('work_orders', [])])
            st.metric("Total Contract Value", f"₹{total_contract_value:,.0f}")
            
        with col4:
            total_payable = sum([inv.get('Payable Amount', 0) for inv in st.session_state.get('invoices', [])])
            st.metric("Total Payable", f"₹{total_payable:,.0f}")


# --------- SEARCH ---------
with tabs[6]:
    st.markdown("### Advanced Search & Filter")
    
    if not st.session_state.get("work_orders", []) and not st.session_state.get("invoices", []):
        st.info("No data available to search. Create work orders and invoices first.")
    else:
        # Search Type Selection
        search_type = st.radio("Search in:", options=["Work Orders", "Invoices", "All Data"], horizontal=True)
        
        st.markdown("---")
        
        # Enhanced Filter Section
        col1, col2, col3 = st.columns([2, 1.5, 1.5])
        
        with col1:
            search_query = st.text_input("Search Query", placeholder="Enter contract number, vendor, item name, etc.")
        
        with col2:
            # Location Filter - Dynamic options from data
            all_locations = set()
            if search_type in ["Work Orders", "All Data"]:
                for wo in st.session_state.get("work_orders", []):
                    location = wo.get("Location", "").strip()
                    if location:
                        all_locations.add(location)
                    # Also get item locations
                    for item in wo.get("Items", []):
                        item_location = item.get("Item Location", "").strip()
                        if item_location:
                            all_locations.add(item_location)
            
            if search_type in ["Invoices", "All Data"]:
                for inv in st.session_state.get("invoices", []):
                    location = inv.get("Invoice Location", "").strip()
                    if location:
                        all_locations.add(location)
            
            location_options = ["All Locations"] + sorted(list(all_locations))
            selected_location = st.selectbox("Filter by Location", options=location_options, key="search_location_filter")
        
        with col3:
            # Name Filter (Vendor/Item Name) - Dynamic options from data
            all_names = set()
            if search_type in ["Work Orders", "All Data"]:
                for wo in st.session_state.get("work_orders", []):
                    vendor = wo.get("Vendor", "").strip()
                    if vendor:
                        all_names.add(vendor)
                    # Also get item names
                    for item in wo.get("Items", []):
                        item_name = item.get("Item Name", "").strip()
                        if item_name:
                            all_names.add(item_name)
            
            if search_type in ["Invoices", "All Data"]:
                for inv in st.session_state.get("invoices", []):
                    vendor = inv.get("Vendor", "").strip()
                    if vendor:
                        all_names.add(vendor)
                    item_name = inv.get("Item Name", "").strip()
                    if item_name:
                        all_names.add(item_name)
            
            name_options = ["All Names"] + sorted(list(all_names))
            selected_name = st.selectbox("Filter by Name", options=name_options, key="search_name_filter")
        
        # Search Fields Selection
        search_fields = st.multiselect(
            "Search Fields", 
            options=["Contract Number", "Vendor", "Item Name", "Category", "Invoice Number", "Location", "Sub-Contract Number"],
            default=["Contract Number", "Vendor", "Item Name"],
            key="search_fields_selection"
        )
        
        # Category Filter
        categories = set()
        if search_type in ["Work Orders", "All Data"]:
            for wo in st.session_state.get("work_orders", []):
                for item in wo.get("Items", []):
                    categories.add(item.get("Category", "Others"))
        
        if categories:
            category_filter = st.multiselect(
                "Filter by Category", 
                options=list(categories), 
                default=list(categories),
                key="search_category_filter"
            )
        
        # Advanced Filters in Expander
        with st.expander("🔧 Advanced Filters"):
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            with filter_col1:
                # Date Range Filter
                date_filter = st.checkbox("Filter by Date Range")
                if date_filter:
                    start_date = st.date_input("Start Date", value=date.today() - timedelta(days=365))
                    end_date = st.date_input("End Date", value=date.today())
            
            with filter_col2:
                # Value Range Filter
                value_filter = st.checkbox("Filter by Value Range")
                if value_filter:
                    min_value = st.number_input("Min Value ₹", min_value=0, value=0)
                    max_value = st.number_input("Max Value ₹", min_value=0, value=1000000)
            
            with filter_col3:
                # Financial Year Filter
                fy_filter = st.checkbox("Filter by Financial Year")
                if fy_filter:
                    # Get all unique FY values from data
                    all_fys = set()
                    if search_type in ["Work Orders", "All Data"]:
                        for wo in st.session_state.get("work_orders", []):
                            contract_date = wo.get("Contract Date", "")
                            if contract_date:
                                fy = get_fy_from_date(contract_date)
                                if fy != "N/A":
                                    all_fys.add(fy)
                    
                    fy_options = ["All FY"] + sorted(list(all_fys), reverse=True)
                    selected_fy = st.selectbox("Select Financial Year", options=fy_options)
        
        # Search Button
        if st.button("🔍 Search", type="primary"):
            results = []
            
            # Search in Work Orders
            if search_type in ["Work Orders", "All Data"]:
                for wo in st.session_state.get("work_orders", []):
                    match_found = False
                    
                    # Apply search query filter
                    if not search_query:
                        match_found = True
                    else:
                        search_lower = search_query.lower()
                        if "Contract Number" in search_fields and search_lower in wo.get("Contract Number", "").lower():
                            match_found = True
                        elif "Vendor" in search_fields and search_lower in wo.get("Vendor", "").lower():
                            match_found = True
                        elif "Location" in search_fields and search_lower in wo.get("Location", "").lower():
                            match_found = True
                        elif "Sub-Contract Number" in search_fields and search_lower in wo.get("Sub-Contract Number", "").lower():
                            match_found = True
                        
                        # Search in items
                        if not match_found:
                            for item in wo.get("Items", []):
                                if "Item Name" in search_fields and search_lower in item.get("Item Name", "").lower():
                                    match_found = True
                                    break
                                elif "Category" in search_fields and search_lower in item.get("Category", "").lower():
                                    match_found = True
                                    break
                    
                    # Apply location filter
                    if match_found and selected_location != "All Locations":
                        location_match = False
                        if wo.get("Location", "") == selected_location:
                            location_match = True
                        # Check item locations too
                        if not location_match:
                            for item in wo.get("Items", []):
                                if item.get("Item Location", "") == selected_location:
                                    location_match = True
                                    break
                        if not location_match:
                            match_found = False
                    
                    # Apply name filter (Vendor/Item Name)
                    if match_found and selected_name != "All Names":
                        name_match = False
                        if wo.get("Vendor", "") == selected_name:
                            name_match = True
                        # Check item names too
                        if not name_match:
                            for item in wo.get("Items", []):
                                if item.get("Item Name", "") == selected_name:
                                    name_match = True
                                    break
                        if not name_match:
                            match_found = False
                    
                    # Apply category filter
                    if match_found and 'category_filter' in locals() and categories:
                        wo_categories = [item.get("Category", "Others") for item in wo.get("Items", [])]
                        if not any(cat in category_filter for cat in wo_categories):
                            match_found = False
                    
                    # Apply date filter
                    if match_found and 'date_filter' in locals() and date_filter:
                        try:
                            wo_date = datetime.strptime(wo.get("Contract Date", ""), "%d/%m/%Y").date()
                            if not (start_date <= wo_date <= end_date):
                                match_found = False
                        except:
                            match_found = False
                    
                    # Apply value filter
                    if match_found and 'value_filter' in locals() and value_filter:
                        wo_value = wo.get("Total Contract Value with GST", 0)
                        if not (min_value <= wo_value <= max_value):
                            match_found = False
                    
                    # Apply FY filter
                    if match_found and 'fy_filter' in locals() and fy_filter and selected_fy != "All FY":
                        wo_fy = get_fy_from_date(wo.get("Contract Date", ""))
                        if wo_fy != selected_fy:
                            match_found = False
                    
                    if match_found:
                        results.append({
                            "Type": "Work Order",
                            "Reference": wo.get("Work-Order Number", ""),
                            "Contract": wo.get("Contract Number", ""),
                            "Sub-Contract": wo.get("Sub-Contract Number", ""),
                            "Vendor": wo.get("Vendor", ""),
                            "Location": wo.get("Location", ""),
                            "Date": wo.get("Contract Date", ""),
                            "FY Contract": get_fy_from_date(wo.get("Contract Date", "")),
                            "Value": wo.get("Total Contract Value with GST", 0),
                            "Status": "Active",
                            "Items": wo.get("Item(s) Count", 0)
                        })
            
            # Search in Invoices
            if search_type in ["Invoices", "All Data"]:
                for inv in st.session_state.get("invoices", []):
                    match_found = False
                    
                    # Apply search query filter
                    if not search_query:
                        match_found = True
                    else:
                        search_lower = search_query.lower()
                        if "Contract Number" in search_fields and search_lower in inv.get("Contract Number", "").lower():
                            match_found = True
                        elif "Vendor" in search_fields and search_lower in inv.get("Vendor", "").lower():
                            match_found = True
                        elif "Invoice Number" in search_fields and search_lower in inv.get("Invoice Number", "").lower():
                            match_found = True
                        elif "Item Name" in search_fields and search_lower in inv.get("Item Name", "").lower():
                            match_found = True
                        elif "Category" in search_fields and search_lower in inv.get("Category", "").lower():
                            match_found = True
                        elif "Location" in search_fields and search_lower in inv.get("Invoice Location", "").lower():
                            match_found = True
                        elif "Sub-Contract Number" in search_fields and search_lower in inv.get("Sub-Contract Number", "").lower():
                            match_found = True
                    
                    # Apply location filter
                    if match_found and selected_location != "All Locations":
                        if inv.get("Invoice Location", "") != selected_location:
                            match_found = False
                    
                    # Apply name filter
                    if match_found and selected_name != "All Names":
                        if inv.get("Vendor", "") != selected_name and inv.get("Item Name", "") != selected_name:
                            match_found = False
                    
                    # Apply date filter
                    if match_found and 'date_filter' in locals() and date_filter:
                        try:
                            inv_date = datetime.strptime(inv.get("Date of Invoice", ""), "%d/%m/%Y").date()
                            if not (start_date <= inv_date <= end_date):
                                match_found = False
                        except:
                            match_found = False
                    
                    # Apply value filter
                    if match_found and 'value_filter' in locals() and value_filter:
                        inv_value = inv.get("Invoice Value", 0)
                        if not (min_value <= inv_value <= max_value):
                            match_found = False
                    
                    # Apply FY filter
                    if match_found and 'fy_filter' in locals() and fy_filter and selected_fy != "All FY":
                        inv_fy = get_fy_from_date(inv.get("Date of Invoice", ""))
                        if inv_fy != selected_fy:
                            match_found = False
                    
                    if match_found:
                        results.append({
                            "Type": "Invoice",
                            "Reference": inv.get("Invoice Number", ""),
                            "Contract": inv.get("Contract Number", ""),
                            "Sub-Contract": inv.get("Sub-Contract Number", ""),
                            "Vendor": inv.get("Vendor", ""),
                            "Location": inv.get("Invoice Location", ""),
                            "Date": inv.get("Date of Invoice", ""),
                            "Invoice FY": get_fy_from_date(inv.get("Date of Invoice", "")),
                            "Value": inv.get("Invoice Value", 0),
                            "Status": inv.get("PaymentStatus", "Pending"),
                            "Items": 1
                        })
            
            # Display Results
            if results:
                st.success(f"✅ Found {len(results)} matching results")
                results_df = pd.DataFrame(results)
                
                # Format currency values
                if "Value" in results_df.columns:
                    results_df["Value"] = results_df["Value"].apply(lambda x: format_indian_currency(x) if isinstance(x, (int, float)) else str(x))
                
                # Add Financial Year columns and apply styling
                results_df_with_fy = add_financial_year_columns(results_df)
                st.dataframe(
                    style_alternate_rows(results_df_with_fy), 
                    hide_index=True, 
                    use_container_width=True
                )
                
                # Summary Statistics
                st.markdown("### Search Results Summary")
                summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
                
                with summary_col1:
                    wo_count = len([r for r in results if r["Type"] == "Work Order"])
                    st.metric("Work Orders", wo_count)
                
                with summary_col2:
                    inv_count = len([r for r in results if r["Type"] == "Invoice"])
                    st.metric("Invoices", inv_count)
                
                with summary_col3:
                    total_value = sum([r["Value"] if isinstance(r["Value"], (int, float)) else 0 for r in results])
                    st.metric("Total Value", format_indian_currency(total_value))
                
                with summary_col4:
                    unique_vendors = len(set([r["Vendor"] for r in results if r["Vendor"]]))
                    st.metric("Unique Vendors", unique_vendors)
                
                # Download Results
                st.markdown("### Export Results")
                download_col1, download_col2 = st.columns(2)
                
                with download_col1:
                    if st.button("📥 Download Search Results (CSV)"):
                        csv_data = results_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv_data,
                            file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                with download_col2:
                    if st.button("📊 Download Search Results (Excel)"):
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            results_df.to_excel(writer, sheet_name='Search Results', index=False)
                        st.download_button(
                            label="📊 Download Excel",
                            data=output.getvalue(),
                            file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            else:
                st.warning("❌ No results found matching your search criteria.")
                st.info("💡 Try adjusting your search filters or query to find matching records.")


# --------- ABOUT ---------
with tabs[7]:  # About tab
    st.markdown("## About Contract Management System")
    
    # Main description section
    st.markdown("""
    ### **System Overview**
    
    The Contract Management System is a comprehensive digital solution designed to streamline and automate 
    the entire contract lifecycle management process. Built with modern web technologies, this system 
    provides government organizations with the tools needed to efficiently manage contracts, work orders, 
    invoices, and payment schedules in compliance with regulatory requirements.
    """)
    
    # Key features section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### **Key Features**
        
        **Contract Management**
        - Create and manage work orders with detailed item specifications
        - Multi-category item support (Hardware, AMC, Software, Telecom)
        - Staff cost tracking with flexible duration options
        - Telecom billing with customizable periods
        
        **Financial Operations**
        - Invoice management with milestone-based billing
        - Payment schedule generation and tracking
        - GST compliance and tax management
        
        **Analytics & Reporting**
        - Complete transaction history  
        - Real-time dashboard with key performance metrics
        - Category-wise distribution reports
        - Quarter-wise timeline overview  
        """)
    
    with col2:
        st.markdown("""
        ###
        **Advanced Functionality**
        - Reduced manual processing time 
        - Responsive design for all device types
        - Intuitive navigation with tabbed interface
        - Secure file upload and document management
        - Built-in validation & duplicate detection
                    
        **Supported Categories**
        - **Hardware:** Equipment procurement & management
        - **Hardware AMC:** Combined warranty & maintenance
        - **AMC:** Annual maintenance contracts
        - **Software:** License & implementation tracking
        - **Staff Cost:** Human resource allocation
        - **Solution & Support:** Technical services
        - **Telecom:** Communication infrastructure
        - **Others:** Custom category support
        """)
    
    st.markdown("---")
    
    
    # Usage statistics (if available)
    if st.session_state.get('work_orders'):
        st.markdown("---")
        st.markdown("### **Current System Statistics**")
        
        total_contracts = len(st.session_state['work_orders'])
        total_value = sum([wo.get('Contract Value', 0) for wo in st.session_state['work_orders']])
        total_items = sum([wo.get('Item(s) Count', 0) for wo in st.session_state['work_orders']])
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric("Active Contracts", total_contracts)
        
        with stat_col2:
            st.metric("Total Contract Value", format_indian_currency(total_value))
        
        with stat_col3:
            st.metric("Total Line Items", total_items)
        
        with stat_col4:
            invoices_count = len(st.session_state.get('invoices', []))
            st.metric("Invoices Processed", invoices_count)
    
    
    st.markdown("---")
    
    # FAQ Section
    st.markdown("#### **Frequently Asked Questions (FAQs)**")
    
    with st.expander("📋 How do I create a new work order?"):
        st.markdown("""
        1. Navigate to the **Work Order** tab
        2. Fill in all required contract details (Contract Number, Vendor, Location, etc.)
        3. Add items with their categories and values
        4. Upload proof documents
        5. Click **Create Work Order** to save
        """)
    
    with st.expander("💰 How are invoice milestones calculated?"):
        st.markdown("""
        Invoice milestones are automatically calculated based on:
        - **Category type** (Hardware, AMC, Software, etc.)
        - **Payment percentages** set during invoice creation
        - **Duration and period** specifications
        - **GST calculations** applied automatically
        """)
    
    with st.expander("🔍 Why am I getting duplicate detection warnings?"):
        st.markdown("""
        The system prevents duplicates by checking:
        - **Contract Number + Sub-Contract Number combination**
        - **Work Order Number + Item Name + Category**
        - Use different values or check existing entries in the dashboard
        """)
    
    with st.expander("📊 How do I export reports?"):
        st.markdown("""
        Reports can be exported from:
        - **Dashboard tab** - Overall analytics and summaries
        - **Work Order tab** - Detailed contract information
        - **Invoice tab** - Payment and milestone reports
        - Data is available in **Excel and CSV formats**
        """)
    
    with st.expander("⚠️ What do the status indicators mean?"):
        st.markdown("""
        - **🟢 Green**: Available/Valid entries
        - **🔴 Red**: Duplicates or validation errors
        - **🟡 Yellow**: Warnings or attention required
        - **✅ Success**: Operations completed successfully
        """)
    
    st.markdown("---")
    
    # Glossary Section
    st.markdown("#### **Glossary of Terms**")
    
    with st.expander("📖 Contract & Work Order Terms"):
        st.markdown("""
        **Contract Number**: Unique identifier for the main contract  
        **Sub-Contract Number**: Division or sub-section of main contract  
        **Work Order Number**: Specific order within a contract  
        **Contract Value**: Total monetary value of the contract  
        **Admissible Amount**: Maximum allowable payment amount  
        **GST**: Goods and Services Tax percentage  
        **LD**: Liquidity Damage for delays  
        """)
    
    with st.expander("📖 Category-Specific Terms"):
        st.markdown(""" 
        **AMC**: Annual Maintenance Contract for services  
        **Hardware AMC**: Combined hardware with maintenance  
        **Warranty**: Manufacturer's guarantee period  
        **UAT**: User Acceptance Testing phase  
        **PQP**: Pre-Qualified Proposal amount  
        **Release Order**: Authorization for payment release  
        """)
    
    with st.expander("📖 Payment & Milestone Terms"):
        st.markdown("""
        **Milestone**: Payment checkpoint in project lifecycle  
        **Delivery**: Equipment/service delivery milestone  
        **Power ON**: System activation milestone  
        **Support Period**: Duration of technical support  
        **Claiming Period**: Frequency of payment claims  
        **Payable Amount**: Final amount after deductions  
        """)
    
    st.markdown("---")
    
    # System information
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### **System Info**")
        st.warning("""
        **Version:** 2.0.0  
        **Last Updated:** September 2025        
        **Technology:** Python/Streamlit Web Application  
        **Database:** PostgreSQL  
        **Deployment:** Cloud-Ready Architecture  
        **Status:** ✅ Operational
        """)
  
    with col2:
        st.markdown("#### **Browser Compatibility**")
        st.info("""
        • **Chrome 90+** (Recommended)  
        • **Firefox 88+**  
        • **Safari 14+**  
        • **Chrome Mobile** (Android)  
        • **Safari Mobile** (iOS)   
        • **Responsive Design** for all screen sizes
        """)
    
    with col3:
        st.markdown("#### **Performance**")
        st.success("""
        **Uptime:** 99.9%  
        **Response Time:** <10s  
        **Data Processing:** Real-time  
        **Concurrent Users:** 10+  
        **Storage:** Scalable
        """)

    st.markdown("---")
    cs1, uf2 = st.columns(2)
    with cs1: # Contact & Support
        st.markdown("#### **Contact & Support**")
        st.markdown("""  
                **Email:** support@xyz.gov.in  
                **Phone:** +01-2345-6789  
                **Hours:** 9:00 AM - 6:00 PM (Mon-Fri)  
                **Response Time:** Within 24 hours
            """)
    
    with uf2: # Feedback Section
        st.markdown("##### 📝 **User Feedback**")
        feedback_type = st.selectbox("Feedback Type", ["General Feedback", "Bug Report", "Feature Request", "Technical Issue"])
        feedback_text = st.text_area("Your Feedback", placeholder="Your feedback will helps us fix bugs and issues, add new features, improve user experience and enhance overall performance.")
        
        if st.button("Submit Feedback", type="primary"):
            if feedback_text.strip():
                st.success("Thank you for your feedback! We'll review it and get back to you.")
                # In a real implementation, this would save to a database or send an email
            else:
                st.warning("Please enter your feedback before submitting.") 


# Footer
st.markdown(f"""
<div style="background: #1e3a8a; color: white; text-align: center; padding: 1rem; margin-top: 2rem;">
    <p style="margin: 0; font-size: 0.9rem;">© 2025 Contract Management System</p>
    <p style="margin: 0; font-size: 0.8rem; opacity: 0.8;">Developed for UIDAI</p>
</div>

""", unsafe_allow_html=True)
