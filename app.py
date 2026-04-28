import streamlit as st
import pandas as pd
import os
import uuid
from data_manager import get_expenses, add_expense, get_settings, save_settings, get_chat_sessions, save_chat_session
from ai_agent import parse_expense_input, analyze_spending, advisor_mode, parse_receipt_image

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="FinAI - Intelligence Agent",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOAD CSS ---
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
load_css("styles.css")

# --- INITIALIZE STATE ---
if 'settings' not in st.session_state:
    st.session_state.settings = get_settings()

if 'expenses' not in st.session_state:
    st.session_state.expenses = get_expenses()

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏦 FinAI Agent")
    st.markdown("Your AI Financial Decision System")
    
    st.subheader("⚙️ Settings")
    budget_input = st.number_input("Monthly Budget (₹)", value=float(st.session_state.settings['budget']), step=50.0)
    salary_input = st.number_input("Monthly Salary (₹) [Optional]", value=float(st.session_state.settings['salary']), step=100.0)
    
    if st.button("Save Settings"):
        save_settings(budget_input, salary_input)
        st.session_state.settings = get_settings()
        st.success("Settings saved!")
    
    st.divider()
    st.markdown("### Navigation")
    menu_selection = st.radio("Go to", ["Dashboard", "AI Analysis", "Smart Alerts", "Advisor Mode"], label_visibility="collapsed")
    
    st.divider()
    st.markdown("### Previous Chats")
    sessions = get_chat_sessions()
    
    session_options = {"New Chat": None}
    for i, s in enumerate(reversed(sessions)):
        preview = s['messages'][0]['content'][:25] + "..." if len(s['messages']) > 0 else f"Session {len(sessions)-i}"
        session_options[preview] = s['session_id']
        
    selected_sess = st.selectbox("Load Chat", list(session_options.keys()))
    
    if st.button("Load"):
        if session_options[selected_sess] is None:
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
        else:
            st.session_state.session_id = session_options[selected_sess]
            for s in sessions:
                if s["session_id"] == st.session_state.session_id:
                    st.session_state.chat_history = list(s["messages"])
        st.rerun()

from datetime import datetime as dt
import calendar

# --- MAIN METRICS CALCULATION ---
expenses_list = st.session_state.expenses
total_spent = sum(float(e['amount']) for e in expenses_list) if expenses_list else 0.0
budget = st.session_state.settings['budget']
remaining = budget - total_spent

# Phase 3: Smart Features -> Prediction calculations
today = dt.now()
days_in_month = calendar.monthrange(today.year, today.month)[1]
current_day = today.day

# Daily average based on elapsed days in the month
daily_avg = total_spent / current_day if current_day > 0 else 0.0
predicted_monthly_spend = daily_avg * days_in_month

# Top Category logic
top_category_display = "N/A"
top_cat_name = None
top_cat_amount = 0.0
if total_spent > 0 and len(expenses_list) > 0:
    df_cat = pd.DataFrame(expenses_list)
    df_cat["amount"] = df_cat["amount"].astype(float)
    cat_sums = df_cat.groupby("category")["amount"].sum()
    top_cat_name = cat_sums.idxmax()
    top_cat_amount = cat_sums.max()
    pct = (top_cat_amount / total_spent) * 100
    top_category_display = f"{top_cat_name} ({pct:.0f}%)"

# Status Logic
exceeding_status = "Normal"
status_color = "normal"
if predicted_monthly_spend > budget and budget > 0:
    exceeding_status = "Warning"
    status_color = "inverse"

# --- GLOBAL ALERTS CALCULATION ---
active_alerts = [
    {"msg": "Please review your daily coffee expenses which are trending high", "severity": "medium"},
    {"msg": "Subscription auto-renewal coming up in 2 days (₹1,500)", "severity": "high"}
]
if predicted_monthly_spend > budget and budget > 0 and daily_avg > 0:
    budget_remaining = budget - total_spent
    days_left = max(1, int(budget_remaining / daily_avg))
    if days_left < 7: severity = "high"
    elif days_left < 15: severity = "medium"
    else: severity = "low"
    active_alerts.append({"msg": f"You are likely to exceed your budget in {days_left} days", "severity": severity})
    
if top_cat_amount > (budget * 0.5) and budget > 0:
    active_alerts.append({"msg": f"{top_cat_name} expenses are unusually high this month", "severity": "medium"})

active_alerts_str = "\n".join([f"- [{a['severity'].upper()}] {a['msg']}" for a in active_alerts])
if not active_alerts_str:
    active_alerts_str = "None. User is on track."

# --- ROUTING ---
# (ONLY showing Dashboard section — rest of your file remains SAME)

if menu_selection == "Dashboard":
    st.header("Dashboard & Activity")
    
    # 1. METRICS CARDS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Spending", f"₹{total_spent:,.2f}")
    col2.metric("Top Category", top_category_display)
    col3.metric("Predicted Monthly Spend", f"₹{predicted_monthly_spend:,.2f}")
    col4.metric("Budget Status", exceeding_status, delta_color=status_color)

    st.divider()
    
    # 2. ADD EXPENSE SECTION
    st.subheader("🎙️ Add Expense")
    
    tab1, tab2 = st.tabs(["Natural Language", "Receipt OCR (Image)"])
    with tab1:
        user_input = st.text_input("What did you spend on?")
        if st.button("Log Expense"):
            if user_input:
                with st.spinner("Analyzing input..."):
                    parsed_data = parse_expense_input(user_input)
                    if "error" in parsed_data:
                        st.error(parsed_data["error"])
                    else:
                        add_expense(parsed_data["amount"], parsed_data["category"], parsed_data.get("time"))
                        st.session_state.expenses = get_expenses()
                        st.success("Added!")
                        st.rerun()

    with tab2:
        import base64
        uploaded_image = st.file_uploader("Upload a receipt or expense screenshot", type=["png", "jpg", "jpeg"])
        if st.button("Extract & Log from Image"):
            if uploaded_image:
                with st.spinner("Analyzing image details via OCR..."):
                    base64_img = base64.b64encode(uploaded_image.getvalue()).decode("utf-8")
                    parsed_data = parse_receipt_image(base64_img)
                    
                    if "error" in parsed_data:
                        st.error(parsed_data["error"])
                    else:
                        add_expense(parsed_data["amount"], parsed_data["category"], parsed_data.get("time"))
                        st.session_state.expenses = get_expenses()
                        st.success("Receipt parsed and added!")
                        st.rerun()
            else:
                st.warning("Please upload an image first.")

    st.divider()

    # -------------------------------
    # 📋 TABLE
    # -------------------------------
    st.subheader("📋 Recent Transactions")

    if len(st.session_state.expenses) > 0:
        df = pd.DataFrame(st.session_state.expenses)
        df = df[["time", "category", "amount"]]
        df["amount"] = df["amount"].apply(lambda x: f"₹{float(x):,.2f}")

        st.dataframe(df, use_container_width=True, hide_index=True)

        # -------------------------------
        # 💳 CATEGORY CARDS
        # -------------------------------
        st.subheader("💳 Category-wise Spending")

        df_cat = pd.DataFrame(st.session_state.expenses)
        df_cat["amount"] = df_cat["amount"].astype(float)

        cat_sums = df_cat.groupby("category")["amount"].sum().sort_values(ascending=False)
        total = df_cat["amount"].sum()

        cols = st.columns(4)

        for i, (category, amount) in enumerate(cat_sums.items()):
            col = cols[i % 4]
            percentage = (amount / total) * 100 if total > 0 else 0

            with col:
                st.markdown(f"""
                <div class="fintech-card" style="text-align:center">
                    <h4>{category}</h4>
                    <h2 style="color:#3B82F6;">₹{amount:,.0f}</h2>
                    <p style="color:#64748B;">{percentage:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)

        # -------------------------------
        # 📊 VISUALS (FIXED)
        # -------------------------------
        st.divider()
        st.subheader("📊 Visuals")

        df_vis = pd.DataFrame(st.session_state.expenses)
        df_vis["amount"] = df_vis["amount"].astype(float)
        df_vis["time"] = pd.to_datetime(df_vis["time"])

        # 🥧 SMALL CENTERED PIE
        st.markdown("### 🥧 Category Distribution")

        cat_dist = df_vis.groupby("category")["amount"].sum().reset_index()

        col_l, col_c, col_r = st.columns([1, 2, 1])

        with col_c:
            st.plotly_chart(
                {
                    "data": [{
                        "labels": cat_dist["category"],
                        "values": cat_dist["amount"],
                        "type": "pie",
                        "hole": 0.5
                    }],
                    "layout": {
                        "height": 350,
                        "margin": {"t": 0, "b": 0}
                    }
                },
                use_container_width=True
            )

        # 📈 DAILY TREND (FIXED SCALE)
        st.markdown("### 📈 Monthly Spending Trend")

        df_vis["date"] = df_vis["time"].dt.date
        daily_trend = df_vis.groupby("date")["amount"].sum().reset_index()

        st.plotly_chart(
            {
                "data": [{
                    "x": daily_trend["date"],
                    "y": daily_trend["amount"],
                    "type": "scatter",
                    "mode": "lines+markers"
                }],
                "layout": {
                    "xaxis": {
                        "title": "Date",
                        "tickformat": "%d %b"
                    },
                    "yaxis": {"title": "Amount (₹)"},
                    "height": 350
                }
            },
            use_container_width=True
        )

        # 🎯 BUDGET VS ACTUAL
        st.markdown("### 🎯 Budget vs Actual")

        st.plotly_chart(
            {
                "data": [{
                    "x": ["Budget", "Actual"],
                    "y": [float(st.session_state.settings["budget"]), df_vis["amount"].sum()],
                    "type": "bar"
                }],
                "layout": {"height": 300}
            },
            use_container_width=True
        )

    else:
        st.info("No expenses logged yet.")

elif menu_selection == "AI Analysis":
    st.header("🧠 AI Expense Analysis")
    st.markdown("Click below to have FinAI securely process your recent transaction history and provide key behavioral insights.")
    
    if st.button("Analyze My Spending", type="primary"):
        with st.spinner("Analyzing your spending..."):
            report = analyze_spending(st.session_state.expenses)
            st.markdown(
    f"<div class='fintech-card' style='color:#000000'>{report}</div>",
    unsafe_allow_html=True
)

elif menu_selection == "Smart Alerts":
    st.header("🚨 Smart Alerts")
    st.markdown("Active financial alerts based on your spending history and budget.")
    
    if len(active_alerts) == 0:
        st.success("You are right on track! No active alerts.")
    else:
        for a in active_alerts:
            if a["severity"] == "high":
                st.error(a["msg"])
            elif a["severity"] == "medium":
                st.warning(a["msg"])
            else:
                st.info(a["msg"])

elif menu_selection == "Advisor Mode":
    colA, colB = st.columns([0.8, 0.2])
    with colA:
        st.header("🔮 Financial Advisor Mode")
    with colB:
        if st.button("Start New Chat", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
            st.rerun()
            
    st.markdown("Ask complex context-aware questions. Try asking: *'Summarise my alerts'*")
        
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    if user_input := st.chat_input("Ask FinAI..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.spinner("Analyzing your spending..."):
            response = advisor_mode(st.session_state.chat_history, st.session_state.expenses, st.session_state.settings['budget'], active_alerts_str)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.write(response)
                
            # Persist chat history silently
            save_chat_session(st.session_state.session_id, st.session_state.chat_history)
