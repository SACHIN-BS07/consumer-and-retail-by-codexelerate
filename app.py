import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. SET PAGE CONFIG (Must be first) ---
st.set_page_config(
    page_title="DECIBAL DRIFT| Enterprise",
    page_icon="🔮",
    layout="wide"
)

# --- 2. DYNAMIC ULTRA-MODERN CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap');

    .stApp {
        background: linear-gradient(-45deg, #1a0033, #4b0082, #800080, #2d0036);
        background-size: 400% 400%;
        animation: gradientShift 12s ease infinite;
        font-family: 'Outfit', sans-serif;
        color: #ffffff;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 105, 180, 0.3) !important;
        padding: 20px !important;
        border-radius: 20px !important;
        backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    .hero-text {
        font-size: 4rem;
        font-weight: 800;
        background: linear-gradient(to right, #ff69b4, #da70d6, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        letter-spacing: -3px;
    }

    [data-testid="stSidebar"] {
        background-color: rgba(15, 0, 25, 0.95) !important;
        border-right: 2px solid rgba(255, 105, 180, 0.2);
    }

    .insight-glow {
        background: rgba(255, 105, 180, 0.15);
        border: 1px solid #ff69b4;
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 0 20px rgba(255, 105, 180, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. UI LAYOUT ---
header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown('<h1 class="hero-text">DECIBAL DRIFT</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: #ffb6c1; font-size: 1.2rem;'>NEURAL TREND ANALYTICS & STRATEGIC INTEL</p>", unsafe_allow_html=True)
with header_right:
    st.markdown(f"<div style='text-align:right; color:#10b981; font-family:monospace; margin-top:30px;'>PROTOCOL: ACTIVE<br>{datetime.now().strftime('%H:%M:%S UTC')}</div>", unsafe_allow_html=True)

st.divider()

# --- 4. SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🛠️ SIGNAL CONTROLS")
    asin = st.text_input("Product ASIN", placeholder="B08N5KWB9H")
    api_key = st.text_input("RapidAPI Token", type="password")
    
    c1, c2 = st.columns(2)
    with c1: fetch_btn = st.button("🚀 FETCH")
    with c2: history_btn = st.button("🗄️ LOGS")
    
    st.markdown("---")
    uploaded_file = st.file_uploader("INGEST CSV DATASHEET", type=["csv"])

# --- 5. BACKEND INTEGRATION ---
res = None

# --- FIND THIS IN SIDEBAR OR SIDEBAR LOGIC ---
if history_btn:
    with st.spinner("Accessing Database..."):
        try:
            h_res = requests.get("http://127.0.0.1:8000/history", timeout=5)
            if h_res.status_code == 200:
                raw_data = h_res.json()
                # FLATTENING: Extracting values from the 'stats' dictionary
                flat_history = []
                for entry in raw_data:
                    # Get stats safely, default to 0 if missing
                    stats = entry.get("stats", {})
                    flat_history.append({
                        "Timestamp": entry.get("timestamp"),
                        "Source": entry.get("source"),
                        "Total Reviews": stats.get("total", 0),
                        "Bot Threats": stats.get("bots", 0),
                        "AI Strategy": entry.get("ai_insight", "N/A")
                    })
                st.session_state['history_data'] = flat_history
            else:
                st.error("Database connection failed.")
        except Exception as e:
            st.error(f"Error: {e}")

if fetch_btn and asin and api_key:
    with st.spinner("Analyzing Live Stream..."):
        try:
            response = requests.get(f"http://127.0.0.1:8000/fetch-live?asin={asin}&api_key={api_key}", timeout=30)
            if response.status_code == 200: res = response.json()
        except: st.error("API Connection Failed.")
elif uploaded_file:
    with st.spinner("Processing Data File..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
            response = requests.post("http://127.0.0.1:8000/analyze", files=files, timeout=60)
            if response.status_code == 200: res = response.json()
            else: st.error(f"Error: {response.text}")
        except: st.error("File Analysis Failed.")

# --- 6. OUTPUT DASHBOARD ---
# --- 6. OUTPUT DASHBOARD ---
if res:
    # --- CLEAN LLM STRATEGIC SUMMARY ---
    st.markdown("### 🛰️ STRATEGIC INTELLIGENCE BRIEF")
    st.markdown(f"""
    <div class="insight-glow" style="border-left: 5px solid #ff69b4;">
        <p style="font-size: 1.25rem; line-height: 1.6; color: #ffffff; margin-bottom: 0px;">
            {res.get('ai_insight', 'Generating intelligence brief...')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Core Metrics Follow...
    m1, m2, m3, m4 = st.columns(4)
    # ... rest of metrics logic ...

    # Core Metrics
    m1, m2, m3, m4 = st.columns(4)
    total = res.get('stats', {}).get('total', 0)
    bots = res.get('stats', {}).get('bots', 0)
    feed_len = len(res.get('feed', []))
    
    m1.metric("TOTAL DATA", total)
    m2.metric("BOT THREATS", bots, delta_color="inverse")
    m3.metric("CLEAN FEED", feed_len)
    health = round((feed_len / total) * 100, 1) if total > 0 else 0
    m4.metric("SIGNAL HEALTH", f"{health}%")

    # Layer 3 Trends
    st.write("")
    st.subheader("📡 Layer 3: Feature Drift Detection")
    trends = res.get('trends', [])
    if trends:
        t_cols = st.columns(len(trends))
        for i, t in enumerate(trends):
            with t_cols[i]:
                trends = res.get('trends', [])
    if trends:
        t_cols = st.columns(len(trends))
        for i, t in enumerate(trends):
            with t_cols[i]:
                # --- NEW DYNAMIC COLOR LOGIC ---
                status_class = t.get('class', 'Isolated Case')
                
                if status_class == "Critical Issue":
                    color = "#ff0000"  # Bright Red
                elif status_class == "Systemic Issue":
                    color = "#ffa500"  # Orange
                else:
                    color = "#10b981"  # Emerald Green
                
                # Update the HTML border and text with the dynamic color
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 2px solid {color}; box-shadow: 0 0 10px {color}33;">
                    <small style="color: #ffb6c1;">{t.get('feature', 'Metric')}</small>
                    <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{t.get('drift', 0)}%</div>
                    <p style="font-size: 0.8rem; height: 40px; overflow: hidden;">{t.get('summary', '')}</p>
                    <div style="font-size: 10px; font-weight: bold; color: {color}; letter-spacing: 1px;">{status_class.upper()}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # Data Navigation
    tab1, tab2, tab3, tab4, tab5= st.tabs(["[ 🧠 NEURAL FEED ]", "[ 🔴 BOT QUARANTINE ]", "[ 📊 ANALYTICS ]", "[ 📈 COMPARISON ]","[⚠️ SARCASM]"])
    
    with tab1:
        df_clean = pd.DataFrame(res.get('feed', []))

    st.dataframe(
                df_clean,
                use_container_width=True,
                column_config={
                    "Sentimental Score": st.column_config.ProgressColumn("Sentiment", min_value=-1, max_value=1),
                    "Confidence Score": st.column_config.NumberColumn("AI Rank", format="%.2f ⭐")
                }
            )
    
    with tab2:
        bot_list = res.get('bots', [])
        if bot_list:
            st.dataframe(pd.DataFrame(bot_list, columns=["Blocked Signal"]), use_container_width=True)
        else:
            st.info("No bot signatures detected.")

    with tab3:
        if res.get('feed'):
            df_pie = pd.DataFrame(res['feed'])
            if 'Feature' in df_pie.columns:
                fig = px.pie(df_pie, names='Feature', hole=0.6, color_discrete_sequence=px.colors.sequential.RdPu)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
    with tab4:
        st.subheader("Cross-Product Health Leaderboard")
        # Ensure the backend is sending 'comparison' data
        if res.get('comparison') and len(res['comparison']) > 0:
            st.table(pd.DataFrame(res['comparison']))
        else:
            st.info("Upload file with a 'Product Name' column to compare multiple items.")
    with tab5:
        if res.get('feed'):
            df_display = pd.DataFrame(res['feed'])
            # Filter specifically for Sarcasm
            if 'Flag' in df_display.columns:
                sarcasm_df = df_display[df_display['Flag'] == "Ambiguous Sarcasm"]
                if not sarcasm_df.empty:
                    st.dataframe(sarcasm_df, use_container_width=True)
                else:
                    st.info("No sarcastic anomalies detected.")        
          

# --- 7. HISTORY TABLE ---
if 'history_data' in st.session_state:
    st.divider()
    st.subheader("📜 Historical Archives")
    h_df = pd.DataFrame(st.session_state['history_data'])
    
    if not h_df.empty:
        # This will now show the columns: Timestamp, Source, Total Reviews, Bot Threats, AI Strategy
        st.dataframe(h_df, use_container_width=True)
    else:
        st.info("No records found in the archive.")
        st.dataframe(pd.DataFrame(flat_history), use_container_width=True)