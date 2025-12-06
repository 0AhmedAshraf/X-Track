import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
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

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa !important; color: #212529 !important; }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important; color: #333333 !important; border-color: #ced4da !important;
    }
    
    /* Cards */
    .premium-card { background-color: #ffffff !important; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #dee2e6; }
    .food-item-box { background-color: #ffffff !important; border-radius: 15px; padding: 15px; margin-bottom: 10px; border: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; color: #212529; }
    
    /* Buttons */
    .stButton button { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white !important; border: none; border-radius: 12px; height: 45px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الاتصال
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
# 3. دوال التعامل مع الداتا (Fixed & Safe)
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
    except Exception as e: st.error(f"Error saving: {e}")

# --- دالة الإصلاح (Reset) ---
def repair_database():
    """تمسح كل شيء وتعيد بناء الجداول بشكل صحيح"""
    with st.spinner("جاري تهيئة قاعدة البيانات... لا تقلق!"):
        # 1. Entries
        df_entries = pd.DataFrame(columns=['id', 'date', 'meal_type', 'food_name', 'quantity', 'unit', 'calories', 'protein', 'carbs', 'fat'])
        write_sheet_safe(SHEET_ENTRIES, df_entries)
        
        # 2. Goals
        df_goals = pd.DataFrame([{'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}])
        write_sheet_safe(SHEET_GOALS, df_goals)
        
        # 3. Metrics
        df_metrics = pd.DataFrame(columns=['date', 'muscle_mass', 'fat_percentage', 'water_percentage', 'steps', 'avg_heart_rate', 'sleep_hours', 'weight'])
        write_sheet_safe(SHEET_METRICS, df_metrics)
        
        # 4. Library
        df_lib = pd.DataFrame(columns=['food_name', 'default_unit', 'calories_per_unit', 'protein_per_unit', 'carbs_per_unit', 'fat_per_unit'])
        write_sheet_safe(SHEET_LIBRARY, df_lib)
        
        st.success("✅ تم إصلاح النظام! جرب الآن.")
        st.rerun()

def save_entry(item, meal_type):
    df = read_sheet_safe(SHEET_ENTRIES)
    # توليد ID
    new_id = 1
    if not df.empty and 'id' in df.columns:
        # تحويل لـ numeric لتجنب الأخطاء
        ids = pd.to_numeric(df['id'], errors='coerce').fillna(0)
        new_id = int(ids.max()) + 1
        
    new_row = {
        'id': new_id,
        'date': str(date.today()), # تأكيد أن التاريخ نص
        'meal_type': str(meal_type),
        'food_name': str(item['name']),
        'quantity': float(item['qty']),
        'unit': str(item['unit']),
        'calories': float(item.get('cals', 0)),
        'protein': float(item.get('pro', 0)),
        'carbs': float(item.get('carb', 0)),
        'fat': float(item.get('fat', 0))
    }
    
    # دمج البيانات
    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_sheet_safe(SHEET_ENTRIES, updated_df)

def get_data(d=1):
    df = read_sheet_safe(SHEET_ENTRIES)
    if df.empty: return df
    
    # التأكد من عمود التاريخ
    if 'date' not in df.columns: return pd.DataFrame()
    
    # تنظيف التواريخ
    df['date_obj'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    target = date.today()
    
    if d == 1:
        return df[df['date_obj'] == target].fillna(0)
    else:
        start = target - timedelta(days=d)
        return df[df['date_obj'] >= start].fillna(0)

# (باقي الدوال الأساسية مختصرة)
def delete_entry(eid): df=read_sheet_safe(SHEET_ENTRIES); df=df[df['id']!=eid]; write_sheet_safe(SHEET_ENTRIES,df)
def get_db_goals(): df=read_sheet_safe(SHEET_GOALS); return df.iloc[-1].to_dict() if not df.empty else {'cal_goal':2000,'pro_goal':150}
def update_db_goals(c,p,cb,f): df=pd.DataFrame([{'cal_goal':int(c),'pro_goal':int(p),'carb_goal':int(cb),'fat_goal':int(f)}]); write_sheet_safe(SHEET_GOALS,df)
def clean_json(txt): txt=txt.replace("```json","").replace("```","").strip(); m=re.search(r'\{.*\}',txt,re.DOTALL); return m.group(0) if m else txt
def get_ai_analysis(txt):
    if not model: return [], None
    prompt = f"""خبير تغذية. حلل: "{txt}". رد JSON فقط بدون أي كلام زيادة: {{ "items": [ {{ "name": "اسم", "qty": رقم, "unit": "وحدة", "cals": رقم, "pro": رقم, "carb": رقم, "fat": رقم }} ], "health_check": {{ "status": "green", "title": "عنوان", "message": "نصيحة" }} }}"""
    try: res=model.generate_content(prompt); data=json.loads(clean_json(res.text)); return data.get("items",[]), data.get("health_check",None)
    except: return [], None

# Callbacks
def sb_cb(): update_db_goals(st.session_state.ucg, st.session_state.upg, st.session_state.ucb, st.session_state.ufg)

# Init State
if 'ucg' not in st.session_state:
    g=get_db_goals()
    st.session_state.ucg=int(g.get('cal_goal',2000))
    st.session_state.upg=int(g.get('pro_goal',150))
    st.session_state.ucb=int(g.get('carb_goal',250))
    st.session_state.ufg=int(g.get('fat_goal',70))

# ==========================================
# 4. الواجهة الرئيسية
# ==========================================
def main():
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        st.number_input("Calories", 1000, 5000, key='ucg', step=50, on_change=sb_cb)
        
        st.divider()
        # --- الزر السحري للإصلاح ---
        st.warning("اضغط هنا مرة واحدة فقط لإصلاح الملف:")
        if st.button("🛠️ Reset & Repair Database"):
            repair_database()

    st.title("X-Track Cloud ☁️")

    tabs = st.tabs(["🏠 Home", "🍽️ Log", "⚙️ Admin"])

    # === 1. Dashboard ===
    with tabs[0]:
        df = get_data(1)
        # التحويل لأرقام للتأكد
        if not df.empty:
            cals = pd.to_numeric(df['calories'], errors='coerce').sum()
            pro = pd.to_numeric(df['protein'], errors='coerce').sum()
        else: cals=0; pro=0
        
        st.metric("Calories Consumed 🔥", f"{int(cals)}", f"{int(st.session_state.ucg - cals)} left")
        
        st.subheader("🤖 AI Add")
        ui = st.text_input("أكلت ايه؟", placeholder="بيضتين مسلوقين")
        if st.button("Add", type="primary"):
            if ui:
                with st.spinner("Analyzing..."):
                    it, hc = get_ai_analysis(ui)
                    if it:
                        for i in it: save_entry(i, "Meal")
                        st.success("Saved!")
                        st.rerun()
                    else: st.error("AI Error")

    # === 2. Log ===
    with tabs[1]:
        st.subheader("🍽️ Today's Food")
        if not df.empty:
            for i, r in df.iterrows():
                # عرض آمن
                c = float(r['calories']) if r['calories'] else 0
                p = float(r['protein']) if r['protein'] else 0
                st.markdown(f"<div class='food-item-box'><b>{r['food_name']}</b> <span>{c:.0f} cal | P:{p:.0f}</span></div>", unsafe_allow_html=True)
                if st.button("Del", key=f"d{r['id']}"): delete_entry(r['id']); st.rerun()
        else: st.info("No food yet.")

    # === 3. Admin (للتأكد) ===
    with tabs[2]:
        st.write("Raw Data View (Debug):")
        st.dataframe(df)

if __name__ == "__main__":
    main()
