import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import random
from datetime import date, timedelta, datetime

# ==========================================
# 1. إعداد الصفحة والستايل (Light Mode Fixed ☀️)
# ==========================================
st.set_page_config(
    page_title="X-Track Cloud ☁️",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa !important; color: #212529 !important; }
    h1, h2, h3, h4, h5, p, label, div, span { color: #212529 !important; }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important; color: #333333 !important; border-color: #ced4da !important;
    }
    ul[data-baseweb="menu"] { background-color: #ffffff !important; }
    li[data-baseweb="option"] { color: #333333 !important; }
    li[data-baseweb="option"]:hover, li[aria-selected="true"] { background-color: #e9ecef !important; }

    /* Cards */
    .premium-card { background-color: #ffffff !important; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #dee2e6; }
    .food-item-box { background-color: #ffffff !important; border-radius: 15px; padding: 15px; margin-bottom: 10px; border: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; color: #212529; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    
    /* Buttons */
    .stButton button { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white !important; border: none; border-radius: 12px; height: 45px; font-weight: bold; box-shadow: 0 4px 10px rgba(52, 152, 219, 0.2); }
    .calc-option { background: #ffffff; border: 1px solid #ced4da; border-radius: 15px; padding: 15px; text-align: center; color: #212529; }
    
    /* Alerts */
    .health-alert { padding: 15px; border-radius: 10px; margin: 10px 0; border-right: 5px solid; color: #333; }
    .alert-green { background-color: #d1e7dd; border-color: #0f5132; color: #0f5132; }
    .alert-red { background-color: #f8d7da; border-color: #842029; color: #842029; }
    
    .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الإعدادات والاتصال
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

SHEET_ENTRIES = "entries"
SHEET_GOALS = "user_goals"
SHEET_METRICS = "health_metrics"
SHEET_LIBRARY = "food_library"

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try: model = genai.GenerativeModel('gemini-2.0-flash')
    except: model = None
else: model = None

# ==========================================
# 3. دوال التعامل مع الداتا (Fixed & Robust)
# ==========================================
def read_sheet_safe(worksheet):
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        return df if df is not None else pd.DataFrame()
    except: return pd.DataFrame()

def write_sheet_safe(worksheet, df):
    try:
        conn.update(worksheet=worksheet, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"Save Error: {e}")

# --- دالة الإصلاح (الحل السحري) ---
def repair_database():
    """تقوم هذه الدالة بمسح الشيت وإنشاء العواميد الصحيحة"""
    # 1. إصلاح جدول الوجبات
    df_entries = pd.DataFrame(columns=['id', 'date', 'meal_type', 'food_name', 'quantity', 'unit', 'calories', 'protein', 'carbs', 'fat'])
    write_sheet_safe(SHEET_ENTRIES, df_entries)
    
    # 2. إصلاح جدول الأهداف
    df_goals = pd.DataFrame([{'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}])
    write_sheet_safe(SHEET_GOALS, df_goals)
    
    # 3. إصلاح جدول القياسات
    df_metrics = pd.DataFrame(columns=['date', 'muscle_mass', 'fat_percentage', 'water_percentage', 'steps', 'avg_heart_rate', 'sleep_hours', 'weight'])
    write_sheet_safe(SHEET_METRICS, df_metrics)
    
    # 4. إصلاح المكتبة
    df_lib = pd.DataFrame(columns=['food_name', 'default_unit', 'calories_per_unit', 'protein_per_unit', 'carbs_per_unit', 'fat_per_unit'])
    write_sheet_safe(SHEET_LIBRARY, df_lib)
    
    st.toast("✅ تم إصلاح قاعدة البيانات بنجاح!")
    st.rerun()

def get_db_goals():
    df = read_sheet_safe(SHEET_GOALS)
    if not df.empty and 'cal_goal' in df.columns: return df.iloc[-1].to_dict()
    return {'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}

def update_db_goals(cals, pro, carb, fat):
    new_goals = pd.DataFrame([{'cal_goal': int(cals), 'pro_goal': int(pro), 'carb_goal': int(carb), 'fat_goal': int(fat)}])
    write_sheet_safe(SHEET_GOALS, new_goals)

# Callbacks
def sidebar_callback():
    update_db_goals(st.session_state.user_cal_goal, st.session_state.user_pro_goal, st.session_state.user_carb_goal, st.session_state.user_fat_goal)

def calculator_callback(cals, pro, carb, fat):
    st.session_state.user_cal_goal = int(cals)
    st.session_state.user_pro_goal = int(pro)
    st.session_state.user_carb_goal = int(carb)
    st.session_state.user_fat_goal = int(fat)
    update_db_goals(cals, pro, carb, fat)
    st.toast("✅ Updated!")

if 'user_cal_goal' not in st.session_state:
    g = get_db_goals()
    st.session_state.user_cal_goal = int(g.get('cal_goal', 2000))
    st.session_state.user_pro_goal = int(g.get('pro_goal', 150))
    st.session_state.user_carb_goal = int(g.get('carb_goal', 250))
    st.session_state.user_fat_goal = int(g.get('fat_goal', 70))

if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ==========================================
# 4. الوظائف المنطقية
# ==========================================
def plot_donut_chart(title, current, total, color):
    safe_curr = int(current) if pd.notnull(current) else 0
    safe_tot = int(total) if pd.notnull(total) and total > 0 else 1
    remaining = max(0, safe_tot - safe_curr)
    fig = go.Figure(data=[go.Pie(labels=['Used', 'Remaining'], values=[safe_curr, remaining], hole=.75, marker_colors=[color, "#f1f3f5"], textinfo='none', hoverinfo='label+value', sort=False)])
    fig.update_layout(showlegend=False, height=160, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', annotations=[dict(text=f"<b style='font-size:20px; color:#2c3e50'>{safe_curr}</b><br><span style='font-size:12px; color:#95a5a6'>/{safe_tot}g</span>", x=0.5, y=0.5, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown(f"<div style='text-align:center; font-weight:bold; color:{color}; margin-top:-10px;'>{title}</div>", unsafe_allow_html=True)

def clean_json_string(text):
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match: return match.group(0)
    return text

def get_gemini_analysis(text):
    if not model: return [], None, None
    prompt = f"""أنت خبير تغذية. حلل: "{text}". رد JSON فقط: {{ "items": [ {{ "name": "اسم", "qty": رقم, "unit": "وحدة", "cals": رقم, "pro": رقم, "carb": رقم, "fat": رقم }} ], "health_check": {{ "status": "green/yellow/red", "title": "عنوان", "message": "نصيحة" }}, "smart_suggestion": "اقتراح أو null" }}"""
    try:
        res = model.generate_content(prompt)
        data = json.loads(clean_json_string(res.text))
        return data.get("items", []), data.get("health_check", None), data.get("smart_suggestion", None)
    except: return [], None, None

def get_chat_response(user_input, context_data):
    if not model: return "يرجى تفعيل API KEY"
    system_prompt = f"""أنت مساعد تغذية في X-Track. بيانات: هدف {context_data['cal_goal']}، استهلاك {context_data['cal_curr']}، متبقي {context_data['cal_rem']}. سؤال: "{user_input}". رد قصير."""
    try: return model.generate_content(system_prompt).text
    except: return "خطأ."

def get_ai_coach_plan(weight, avg_cals, avg_pro, goal, location, level, days, metrics):
    if not model: return "API Error"
    m_txt = ""
    if metrics:
        if metrics.get('muscle_mass') and metrics['muscle_mass'] > 0: m_txt += f"- عضلات: {metrics['muscle_mass']}kg\n"
    prompt = f"""أنت X-Track Coach. المتدرب: {weight}kg، هدفه: {goal}. متوسط أكله: {avg_cals:.0f} سعرة. بيانات: {m_txt}. المكان: {location}. الأيام: {days}. المطلوب (Markdown): 1. تحليل. 2. نصيحة. 3. جدول تمرين."""
    try: return model.generate_content(prompt).text
    except: return "حدث خطأ"

def calculate_calories(gender, age, weight, height, activity):
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == "ذكر" else -161)
    return bmr * {"خامل": 1.2, "خفيف": 1.375, "متوسط": 1.55, "عالي": 1.725, "شاق": 1.9}.get(activity, 1.2)

def save_entry(item, meal_type):
    df = read_sheet_safe(SHEET_ENTRIES)
    new_id = 1 if df.empty else (int(df['id'].max()) + 1)
    
    new_row = {
        'id': new_id,
        'date': str(date.today()), # تنسيق نصي ثابت
        'meal_type': meal_type,
        'food_name': item['name'],
        'quantity': float(item['qty']),
        'unit': item['unit'],
        'calories': float(item.get('cals', 0)),
        'protein': float(item.get('pro', 0)),
        'carbs': float(item.get('carb', 0)),
        'fat': float(item.get('fat', 0))
    }
    
    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_sheet_safe(SHEET_ENTRIES, updated_df)

def delete_entry(entry_id):
    df = read_sheet_safe(SHEET_ENTRIES)
    if not df.empty:
        df = df[df['id'] != entry_id]
        write_sheet_safe(SHEET_ENTRIES, df)

def get_data(d=1):
    df = read_sheet_safe(SHEET_ENTRIES)
    if df.empty: return df
    
    # تحويل التاريخ للتأكد من التنسيق، ثم تحويله لنص للمقارنة
    try:
        # تأكد إن العمود موجود
        if 'date' not in df.columns: return pd.DataFrame()
        
        # تحويل لـ datetime للفلترة، ثم سترينج للمقارنة
        df['dt_obj'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        target = date.today()
        
        if d == 1:
            filtered = df[df['dt_obj'] == target]
        else:
            start = target - timedelta(days=d)
            filtered = df[df['dt_obj'] >= start]
            
        return filtered.fillna(0)
    except Exception as e:
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

def save_weight(w):
    df = read_sheet_safe(SHEET_METRICS)
    new_row = {'date': str(date.today()), 'weight': w}
    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_sheet_safe(SHEET_METRICS, updated_df)

def get_weight_data(): return read_sheet_safe(SHEET_METRICS)

def save_health_metrics(mu, fa, wa, st, hr, sl):
    df = read_sheet_safe(SHEET_METRICS)
    new_row = {'date': str(date.today()), 'muscle_mass': mu, 'fat_percentage': fa, 'water_percentage': wa, 'steps': st, 'avg_heart_rate': hr, 'sleep_hours': sl}
    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_sheet_safe(SHEET_METRICS, updated_df)

def get_latest_metrics():
    df = read_sheet_safe(SHEET_METRICS)
    if not df.empty: return df.iloc[-1].to_dict()
    return None

def get_cached_foods():
    df = read_sheet_safe(SHEET_LIBRARY)
    if not df.empty and 'food_name' in df.columns: return df['food_name'].tolist()
    return []

def get_food_details_from_cache(fn):
    df = read_sheet_safe(SHEET_LIBRARY)
    row = df[df['food_name'] == fn]
    if not row.empty:
        r = row.iloc[0]
        return {'name': r['food_name'], 'unit': r['default_unit'], 'cals': r['calories_per_unit'], 'pro': r['protein_per_unit'], 'carb': r['carbs_per_unit'], 'fat': r['fat_per_unit']}
    return None

def cache_food_item(i):
    df = read_sheet_safe(SHEET_LIBRARY)
    if df.empty or i['name'] not in df['food_name'].values:
        new_row = {'food_name': i['name'], 'default_unit': i['unit'], 'calories_per_unit': i['cals'], 'protein_per_unit': i['pro'], 'carbs_per_unit': i['carb'], 'fat_per_unit': i['fat']}
        updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        write_sheet_safe(SHEET_LIBRARY, updated_df)

def get_streak():
    df = read_sheet_safe(SHEET_ENTRIES)
    if df.empty or 'date' not in df.columns: return 0
    try:
        dates = sorted(pd.to_datetime(df['date'], errors='coerce').dt.date.unique(), reverse=True)
        if not dates: return 0
        streak = 0; check = dates[0]
        if check != date.today() and check != date.today() - timedelta(1): return 0
        for d in dates:
            if d == check: streak+=1; check-=timedelta(1)
            else: break
        return streak
    except: return 0

QUOTES = ["💪 الألم يزول، الفخر يدوم.", "🔥 أنت أقوى مما تتخيل.", "🚀 استمر، النتائج قادمة."]

# ==========================================
# 4. الواجهة الرئيسية
# ==========================================
def main():
    # --- Sidebar ---
    with st.sidebar:
        streak = get_streak()
        st.markdown(f"<h2 style='text-align:center; color:#3498db;'>X-Track ⚡</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#e3f2fd; border:1px solid #90caf9; padding:8px; border-radius:10px; color:#1565c0; text-align:center;'>🔥 {streak} Days Streak</div>", unsafe_allow_html=True)
        st.divider()
        st.header("⚙️ Goals")
        st.number_input("Calories", 1000, 5000, key='user_cal_goal', step=50, on_change=sidebar_callback)
        st.number_input("Protein (g)", 50, 300, key='user_pro_goal', step=10, on_change=sidebar_callback)
        st.number_input("Carbs (g)", 50, 500, key='user_carb_goal', step=10, on_change=sidebar_callback)
        st.number_input("Fat (g)", 20, 200, key='user_fat_goal', step=5, on_change=sidebar_callback)
        st.divider()
        
        # --- زر الإصلاح (مهم جداً) ---
        if st.button("⚠️ Repair Database"):
            repair_database()

    if not GEMINI_API_KEY: st.error("⚠️ يرجى تفعيل مفتاح API"); st.stop()

    st.title("X-Track Cloud ☁️")

    tabs = st.tabs(["🏠 Home", "🍽️ Log", "🧮 Calculator", "⚖️ Body", "🏋️ Coach", "📈 Trends"])

    # === 1. Dashboard ===
    with tabs[0]:
        df = get_data(1)
        if not df.empty:
            cals_today = df["calories"].sum(); pro_today = df["protein"].sum(); fat_today = df["fat"].sum(); carb_today = df["carbs"].sum()
        else: cals_today=0; pro_today=0; fat_today=0; carb_today=0
        
        context_data = {'cal_goal': st.session_state.user_cal_goal, 'cal_curr': int(cals_today), 'cal_rem': int(st.session_state.user_cal_goal - cals_today), 'pro_goal': st.session_state.user_pro_goal, 'pro_curr': int(pro_today)}

        if cals_today >= st.session_state.user_cal_goal: st.toast("🎉 Goal Reached!")

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: plot_donut_chart("Calories 🔥", cals_today, st.session_state.user_cal_goal, "#ff6b6b")
        with c2: plot_donut_chart("Protein 🥩", pro_today, st.session_state.user_pro_goal, "#4ecdc4")
        c3, c4 = st.columns(2)
        with c3: plot_donut_chart("Carbs 🍞", carb_today, st.session_state.user_carb_goal, "#feca57")
        with c4: plot_donut_chart("Fat 🥑", fat_today, st.session_state.user_fat_goal, "#a29bfe")
        st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("🚀 Quick Add")
        col_lib, col_ai = st.columns([1, 2])
        
        with col_lib:
            st.markdown("<div class='premium-card'>📚 <b>Library</b>", unsafe_allow_html=True)
            cf = get_cached_foods()
            sf = st.selectbox("Select:", ["--"] + cf, label_visibility="collapsed")
            if sf != "--":
                fd = get_food_details_from_cache(sf)
                if st.button("➕ Add"): save_entry({'name': fd['name'], 'qty': 1, 'unit': fd['unit'], 'cals': fd['cals'], 'pro': fd['pro'], 'carb': fd['carb'], 'fat': fd['fat']}, "سناك 🍏"); st.toast("Added!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_ai:
            st.markdown("<div class='premium-card'>🤖 <b>AI Scan</b>", unsafe_allow_html=True)
            ui = st.text_input("Type food...", placeholder="e.g. 2 eggs and toast")
            if st.button("Analyze & Add", type="primary"):
                if ui:
                    with st.spinner("Analyzing..."):
                        it, hc, sg = get_gemini_analysis(ui)
                        if it:
                            for i in it: save_entry(i, "وجبة 🥘"); cache_food_item(i)
                            st.session_state.hc = hc; st.session_state.sg = sg; st.success("Added!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            if "hc" in st.session_state and st.session_state.hc:
                fb = st.session_state.hc; cls = "alert-red" if fb['status']=='red' else "alert-green"
                st.markdown(f"<div class='health-alert {cls}'><b>{fb['title']}</b><br>{fb['message']}</div>", unsafe_allow_html=True)

    # --- CHAT INPUT (Global) ---
    if prompt := st.chat_input("Ask X-Track assistant..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("..."):
                response = get_chat_response(prompt, context_data)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

    # === 2. Log ===
    with tabs[1]:
        st.markdown("### 🍽️ Today's Log")
        
        # --- زر لعرض الداتا الخام للمساعدة في الحل ---
        with st.expander("Debug: Show Raw Data"):
            st.write(df)
            
        if not df.empty:
            for index, row in df.iterrows():
                cal = row.get('calories') or 0; pro = row.get('protein') or 0; carb = row.get('carbs') or 0; fat = row.get('fat') or 0
                st.markdown(f"""
                <div class="food-item-box">
                    <div>
                        <div style="font-weight:bold; font-size:16px;">{row['food_name']}</div>
                        <div style="color:#666; font-size:12px;">{row['quantity']} {row['unit']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#e74c3c; font-weight:bold;">{int(cal)} cal</div>
                        <div style="font-size:11px; color:#555;">P:{int(pro)} C:{int(carb)} F:{int(fat)}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
                if st.button("Delete", key=f"d_{row['id']}"): delete_entry(row['id']); st.rerun()
        else: st.info("No food logged yet.")

    # === 3. Calculator (Same Logic) ===
    with tabs[2]:
        st.markdown("### 🧮 Smart Calculator")
        with st.form("calc_form"):
            c1, c2 = st.columns(2)
            with c1:
                gender = st.selectbox("Gender", ["Male", "Female"])
                age = st.number_input("Age", 10, 100, 25)
            with c2:
                weight_calc = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)
                height = st.number_input("Height (cm)", 100, 250, 170)
            activity = st.selectbox("Activity", ["خامل", "خفيف", "متوسط", "عالي", "شاق"])
            calc_submit = st.form_submit_button("Calculate")
        
        if calc_submit:
            tdee = calculate_calories("ذكر" if gender=="Male" else "أنثى", age, weight_calc, height, activity)
            st.session_state.calc_results = tdee

        if 'calc_results' in st.session_state:
            tdee = st.session_state.calc_results
            cut, bulk = tdee - 500, tdee + 500
            s_pro = weight_calc * 2.0
            cut_carb, cut_fat = (cut*0.5)/4, (cut*0.25)/9
            main_carb, main_fat = (tdee*0.5)/4, (tdee*0.25)/9
            bulk_carb, bulk_fat = (bulk*0.5)/4, (bulk*0.25)/9

            st.markdown("---")
            st.subheader("Choose your goal:")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='calc-option'>📉 <b>Cut</b><br><span style='color:#e74c3c'>{cut:.0f}</span></div>", unsafe_allow_html=True)
                st.button("Select Cut", on_click=calculator_callback, args=(cut, s_pro, cut_carb, cut_fat))
            with c2:
                st.markdown(f"<div class='calc-option'>⚖️ <b>Maintain</b><br><span style='color:#3498db'>{tdee:.0f}</span></div>", unsafe_allow_html=True)
                st.button("Select Maintain", on_click=calculator_callback, args=(tdee, s_pro, main_carb, main_fat))
            with c3:
                st.markdown(f"<div class='calc-option'>📈 <b>Bulk</b><br><span style='color:#2ecc71'>{bulk:.0f}</span></div>", unsafe_allow_html=True)
                st.button("Select Bulk", on_click=calculator_callback, args=(bulk, s_pro, bulk_carb, bulk_fat))

    # === 4. Body, 5. Coach, 6. Trends ===
    # (تم اختصارها هنا، الكود الكامل يحتوي عليها بنفس المنطق)
    with tabs[3]:
        st.markdown("### ⚖️ Body Metrics")
        w_in=st.number_input("Weight",30.0,200.0,70.0,0.1)
        if st.button("Save Weight"): save_weight(w_in); st.rerun()
        df_w=get_weight_data()
        if not df_w.empty: st.plotly_chart(px.area(df_w,x="date",y="weight",title="Weight Progress"),use_container_width=True)

    with tabs[4]:
        st.markdown("### 🏋️ AI Coach")
        if st.button("Generate Plan"):
            df7=get_data(7); ac=df7["calories"].sum()/7 if not df7.empty else 0; ap=df7["protein"].sum()/7 if not df7.empty else 0
            cw=get_weight_data().iloc[-1]['weight'] if not get_weight_data().empty else 70.0
            mts=get_latest_metrics()
            with st.spinner("..."): st.markdown(get_ai_coach_plan(cw,ac,ap,"Lose","Gym","Beginner",4,mts))

    with tabs[5]:
        st.header("📅 30-Day History")
        df_30 = get_data(30)
        if not df_30.empty:
            daily = df_30.groupby("date")["calories"].sum().reset_index()
            fig = px.bar(daily, x="date", y="calories", title="Daily Calories", text_auto=True, color_discrete_sequence=["#3498db"])
            fig.add_hline(y=st.session_state.user_cal_goal, line_dash="dot", line_color="red", annotation_text="Goal")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_30.sort_values(by="date", ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
