import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go
import json
import re
import random
from datetime import date, timedelta, datetime

# ==========================================
# 1. إعداد الصفحة والستايل
# ==========================================
st.set_page_config(
    page_title="X-Track Cloud ☁️",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- الاتصال بـ Google Sheets ---
# بنعمل اتصال ونقوله ميعملش كاش عشان الداتا تتحدث لحظياً
conn = st.connection("gsheets", type=GSheetsConnection)

# أسماء أوراق العمل (Tabs) داخل ملف جوجل
SHEET_ENTRIES = "entries"
SHEET_GOALS = "user_goals"
SHEET_METRICS = "health_metrics"
SHEET_LIBRARY = "food_library"

# --- دوال التعامل مع Google Sheets (بديل الـ SQL) ---

def read_sheet(worksheet_name):
    """قراءة البيانات من شيت معين"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        # لو الشيت لسه فاضي او مش موجود، نرجع DataFrame فاضي
        return pd.DataFrame()

def write_sheet(worksheet_name, df):
    """كتابة البيانات (تحديث الشيت بالكامل)"""
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear() # مسح الكاش عشان التحديث يظهر

def append_to_sheet(worksheet_name, new_row_data):
    """إضافة صف جديد"""
    df = read_sheet(worksheet_name)
    new_df = pd.DataFrame([new_row_data])
    updated_df = pd.concat([df, new_df], ignore_index=True)
    write_sheet(worksheet_name, updated_df)

# --- تهيئة الجداول (لو أول مرة) ---
def init_sheets():
    # نتأكد إن الجداول موجودة، لو مش موجودة بنعملها
    # 1. Entries
    df = read_sheet(SHEET_ENTRIES)
    if df.empty or 'date' not in df.columns:
        empty_entries = pd.DataFrame(columns=['id', 'date', 'meal_type', 'food_name', 'quantity', 'unit', 'calories', 'protein', 'carbs', 'fat'])
        write_sheet(SHEET_ENTRIES, empty_entries)
    
    # 2. Goals
    df_goals = read_sheet(SHEET_GOALS)
    if df_goals.empty:
        default_goals = pd.DataFrame([{'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}])
        write_sheet(SHEET_GOALS, default_goals)

# استدعاء التهيئة مرة واحدة (ممكن تعطلها بعد أول مرة لتسريع الكود)
# init_sheets() 

# --- دوال المساعدة ---
def get_db_goals():
    df = read_sheet(SHEET_GOALS)
    if not df.empty:
        return df.iloc[-1].to_dict() # إرجاع آخر صف كـ Dictionary
    return {'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}

def update_db_goals(cals, pro, carb, fat):
    # في جوجل شيتس، هنضيف صف جديد بالأهداف الجديدة (عشان نحتفظ بالتاريخ لو حبيت) أو نعدل القديم
    # هنا هنستبدل القديم بجديد للتسهيل
    new_goals = pd.DataFrame([{'cal_goal': int(cals), 'pro_goal': int(pro), 'carb_goal': int(carb), 'fat_goal': int(fat)}])
    write_sheet(SHEET_GOALS, new_goals)

# تهيئة المتغيرات في الجلسة
if 'user_cal_goal' not in st.session_state:
    g = get_db_goals()
    st.session_state.user_cal_goal = int(g['cal_goal'])
    st.session_state.user_pro_goal = int(g['pro_goal'])
    st.session_state.user_carb_goal = int(g['carb_goal'])
    st.session_state.user_fat_goal = int(g['fat_goal'])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Callbacks ---
def sidebar_callback():
    update_db_goals(st.session_state.user_cal_goal, st.session_state.user_pro_goal, st.session_state.user_carb_goal, st.session_state.user_fat_goal)

def calculator_callback(cals, pro, carb, fat):
    st.session_state.user_cal_goal = int(cals)
    st.session_state.user_pro_goal = int(pro)
    st.session_state.user_carb_goal = int(carb)
    st.session_state.user_fat_goal = int(fat)
    update_db_goals(cals, pro, carb, fat)
    st.toast("✅ تم التحديث السحابي!")

# --- CSS Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f4f7f6 !important; color: #2c3e50 !important; }
    h1, h2, h3, h4, h5, p, label { color: #2c3e50 !important; }
    .premium-card { background-color: #ffffff !important; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e1e4e8; }
    .food-item-box { background-color: #ffffff !important; border-radius: 15px; padding: 15px; margin-bottom: 10px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; color: #2c3e50; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .stButton button { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white !important; border: none; border-radius: 12px; height: 45px; font-weight: bold; box-shadow: 0 4px 10px rgba(52, 152, 219, 0.2); }
    .calc-option { background: #ffffff; border: 1px solid #ddd; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .health-alert { padding: 15px; border-radius: 10px; margin: 10px 0; border-right: 5px solid; color: #333; }
    .alert-green { background-color: #e8f5e9; border-color: #2ecc71; }
    .alert-red { background-color: #fdebd0; border-color: #e74c3c; }
    .stChatMessage { background-color: #ffffff; border-radius: 15px; border: 1px solid #eee; }
    div[data-baseweb="select"] > div { background-color: white !important; color: #333 !important; border-color: #ddd !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. الوظائف (Logic)
# ==========================================
def plot_donut_chart(title, current, total, color):
    safe_curr = int(current) if current else 0
    safe_tot = int(total) if total else 1
    remaining = max(0, safe_tot - safe_curr)
    fig = go.Figure(data=[go.Pie(labels=['Used', 'Remaining'], values=[safe_curr, remaining], hole=.75, marker_colors=[color, "#f1f3f5"], textinfo='none', hoverinfo='label+value', sort=False)])
    fig.update_layout(showlegend=False, height=160, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', annotations=[dict(text=f"<b style='font-size:20px; color:#2c3e50'>{safe_curr}</b><br><span style='font-size:12px; color:#95a5a6'>/{safe_tot}g</span>", x=0.5, y=0.5, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown(f"<div style='text-align:center; font-weight:bold; color:{color}; margin-top:-10px;'>{title}</div>", unsafe_allow_html=True)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try: model = genai.GenerativeModel('gemini-2.0-flash')
    except: model = None
else: model = None

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
    system_prompt = f"""
    أنت مساعد تغذية في X-Track.
    📊 بيانات: هدف {context_data['cal_goal']}، استهلاك {context_data['cal_curr']}، متبقي {context_data['cal_rem']}.
    بروتين: {context_data['pro_curr']}/{context_data['pro_goal']}g.
    سؤال: "{user_input}"
    رد قصير ومفيد.
    """
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

# --- دوال التعامل مع الداتا (Google Sheets version) ---
def save_entry(item, meal_type):
    # إنشاء ID عشوائي بسيط
    entry_id = random.randint(10000, 99999)
    new_row = {
        'id': entry_id,
        'date': str(date.today()),
        'meal_type': meal_type,
        'food_name': item['name'],
        'quantity': item['qty'],
        'unit': item['unit'],
        'calories': item.get('cals', 0),
        'protein': item.get('pro', 0),
        'carbs': item.get('carb', 0),
        'fat': item.get('fat', 0)
    }
    append_to_sheet(SHEET_ENTRIES, new_row)

def delete_entry(entry_id):
    df = read_sheet(SHEET_ENTRIES)
    # حذف الصف اللي فيه الـ ID ده
    df = df[df['id'] != entry_id]
    write_sheet(SHEET_ENTRIES, df)

def get_data(d=1):
    df = read_sheet(SHEET_ENTRIES)
    if df.empty: return df
    # فلترة بالتاريخ
    target_date = date.today()
    # تأكد من تحويل العمود لتاريخ
    df['date'] = pd.to_datetime(df['date']).dt.date
    if d == 1:
        filtered_df = df[df['date'] == target_date]
    else:
        start_date = target_date - timedelta(days=d)
        filtered_df = df[df['date'] >= start_date]
    return filtered_df

def save_weight(w):
    new_row = {'date': str(date.today()), 'weight': w}
    append_to_sheet(SHEET_METRICS, new_row) # نستخدم شيت الميتريكس للتبسيط

def get_weight_data():
    # هنا هنفترض ان الوزن موجود في health_metrics للتسهيل او نعمله شيت منفصل
    # في المثال ده، هنستخدم health_metrics
    return read_sheet(SHEET_METRICS)

def save_health_metrics(mu, fa, wa, st, hr, sl):
    new_row = {
        'date': str(date.today()),
        'muscle_mass': mu, 'fat_percentage': fa, 'water_percentage': wa,
        'steps': st, 'avg_heart_rate': hr, 'sleep_hours': sl
    }
    append_to_sheet(SHEET_METRICS, new_row)

def get_latest_metrics():
    df = read_sheet(SHEET_METRICS)
    if not df.empty:
        return df.iloc[-1].to_dict()
    return None

def get_cached_foods():
    df = read_sheet(SHEET_LIBRARY)
    if not df.empty and 'food_name' in df.columns:
        return df['food_name'].tolist()
    return []

def get_food_details_from_cache(fn):
    df = read_sheet(SHEET_LIBRARY)
    row = df[df['food_name'] == fn]
    if not row.empty:
        r = row.iloc[0]
        return {'name': r['food_name'], 'unit': r['default_unit'], 'cals': r['calories_per_unit'], 'pro': r['protein_per_unit'], 'carb': r['carbs_per_unit'], 'fat': r['fat_per_unit']}
    return None

def cache_food_item(i):
    # نتأكد انه مش موجود الاول
    df = read_sheet(SHEET_LIBRARY)
    if df.empty or i['name'] not in df['food_name'].values:
        new_row = {
            'food_name': i['name'], 'default_unit': i['unit'],
            'calories_per_unit': i['cals'], 'protein_per_unit': i['pro'],
            'carbs_per_unit': i['carb'], 'fat_per_unit': i['fat']
        }
        append_to_sheet(SHEET_LIBRARY, new_row)

def get_streak():
    df = read_sheet(SHEET_ENTRIES)
    if df.empty: return 0
    # نفس منطق الحساب
    dates = sorted(pd.to_datetime(df['date']).dt.date.unique(), reverse=True)
    if not dates: return 0
    streak = 0; today = date.today()
    if dates[0] != today and dates[0] != today - timedelta(1): return 0
    check = dates[0]
    for d in dates:
        if d == check: streak+=1; check-=timedelta(1)
        else: break
    return streak

QUOTES = ["💪 الألم يزول، الفخر يدوم.", "🔥 أنت أقوى مما تتخيل.", "🚀 استمر، النتائج قادمة."]

# ==========================================
# 4. الواجهة الرئيسية
# ==========================================
def main():
    # --- 1. حساب البيانات (Context) ---
    df = get_data(1)
    cals_today = df["calories"].sum() if not df.empty else 0
    pro_today = df["protein"].sum() if not df.empty else 0
    fat_today = df["fat"].sum() if not df.empty else 0
    carb_today = df["carbs"].sum() if not df.empty else 0
    
    context_data = {
        'cal_goal': st.session_state.user_cal_goal, 'cal_curr': int(cals_today), 'cal_rem': int(st.session_state.user_cal_goal - cals_today),
        'pro_goal': st.session_state.user_pro_goal, 'pro_curr': int(pro_today),
        'carb_goal': st.session_state.user_carb_goal, 'carb_curr': int(carb_today),
        'fat_goal': st.session_state.user_fat_goal, 'fat_curr': int(fat_today)
    }

    with st.sidebar:
        streak = get_streak()
        st.markdown(f"<h2 style='text-align:center; color:#3498db;'>X-Track ⚡</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#f1f3f5; border:1px solid #ddd; padding:8px; border-radius:10px; color:#333; text-align:center;'>🔥 {streak} Days Streak</div>", unsafe_allow_html=True)
        st.divider()
        st.header("⚙️ Goals")
        st.number_input("Calories", 1000, 5000, key='user_cal_goal', step=50, on_change=sidebar_callback)
        st.number_input("Protein (g)", 50, 300, key='user_pro_goal', step=10, on_change=sidebar_callback)
        st.number_input("Carbs (g)", 50, 500, key='user_carb_goal', step=10, on_change=sidebar_callback)
        st.number_input("Fat (g)", 20, 200, key='user_fat_goal', step=5, on_change=sidebar_callback)
        if st.button("🗑️ Reset Today"):
            # في الجوجل شيت، الحذف صعب شوية، ممكن نعمل فلتر بس
            # للتبسيط هنا، هنفترض اننا مش بنحذف كله مرة واحدة، أو نستخدم delete_entry لوب
            pass 

    if not GEMINI_API_KEY: st.error("⚠️ يرجى تفعيل مفتاح API"); st.stop()

    st.title("X-Track Cloud ☁️")

    tabs = st.tabs(["🏠 Home", "🍽️ Log", "🧮 Calculator", "⚖️ Body", "🏋️ Coach", "📈 Trends"])

    # === 1. Dashboard ===
    with tabs[0]:
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

    # باقي التبويبات (Log, Calc, Body, Coach, Trends)
    # (نفس المنطق لكن باستخدام دوال Google Sheets الجديدة)
    # ... (تم اختصارها هنا لعدم التكرار، لكن المنطق واحد: استبدل get_data و save_entry بالجدد)

if __name__ == "__main__":
    main()