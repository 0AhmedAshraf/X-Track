import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
from datetime import date, timedelta

# ==========================================
# 1. إعداد الصفحة
# ==========================================
st.set_page_config(page_title="X-Track Final", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    * { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #333; }
    .premium-card { background: white; padding: 15px; border-radius: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 10px; border: 1px solid #eee; }
    .stButton button { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الاتصال
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("مشكلة في الاتصال بـ Google Sheets. تأكد من ملف secrets.toml")
    st.stop()

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try: model = genai.GenerativeModel('gemini-2.0-flash')
    except: model = None
else: model = None

# ==========================================
# 3. دوال التعامل مع الداتا (Direct & Safe)
# ==========================================
def read_sheet(name):
    try:
        # ttl=0 يعني هات الداتا فريش حالاً
        df = conn.read(worksheet=name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame() # لو فيه خطأ رجع جدول فاضي

def append_to_sheet(name, new_data):
    try:
        df = read_sheet(name)
        # تحويل الداتا الجديدة لـ DataFrame
        new_row = pd.DataFrame([new_data])
        # دمج القديم مع الجديد
        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # الحفظ
        conn.update(worksheet=name, data=updated_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"فشل الحفظ: {e}")
        return False

# --- Save Entry Logic ---
def save_entry(item, meal_type):
    # توليد ID بسيط
    import time
    new_id = int(time.time()) 
    
    row_data = {
        "id": new_id,
        "date": str(date.today()), # تاريخ نصي صريح
        "meal_type": meal_type,
        "food_name": item['name'],
        "quantity": item['qty'],
        "unit": item['unit'],
        "calories": item.get('cals', 0),
        "protein": item.get('pro', 0),
        "carbs": item.get('carb', 0),
        "fat": item.get('fat', 0)
    }
    return append_to_sheet("entries", row_data)

# --- AI Helper ---
def get_ai_analysis(text):
    if not model: return [], "No API"
    prompt = f"""حلل: "{text}". رد JSON: {{ "items": [ {{ "name": "اسم", "qty": رقم, "unit": "وحدة", "cals": رقم, "pro": رقم, "carb": رقم, "fat": رقم }} ] }}"""
    try:
        res = model.generate_content(prompt)
        clean = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean).get("items", []), None
    except: return [], "Error"

# ==========================================
# 4. الواجهة
# ==========================================
def main():
    st.title("X-Track Debugger 🕵️‍♂️")
    
    # --- إضافة وجبة ---
    st.subheader("1. إضافة وجبة")
    col1, col2 = st.columns([3, 1])
    with col1:
        txt = st.text_input("أكلت إيه؟", placeholder="مثال: بيضتين")
    with col2:
        btn = st.button("إضافة")
        
    if btn and txt:
        with st.spinner("جاري التحليل والحفظ..."):
            items, err = get_ai_analysis(txt)
            if items:
                for i in items:
                    if save_entry(i, "وجبة"):
                        st.success(f"تم حفظ: {i['name']}")
                    else:
                        st.error("فشل الحفظ في جوجل شيت")
                st.rerun()
            else:
                st.warning("لم يتم التعرف على الطعام")

    # --- عرض السجل ---
    st.divider()
    st.subheader("2. السجل (من Google Sheets)")
    
    # قراءة مباشرة
    df = read_sheet("entries")
    
    if not df.empty:
        # عرض الجدول كما هو (للتأكد)
        st.write("الداتا الخام (Raw Data):")
        st.dataframe(df)
        
        # محاولة الفلترة
        try:
            # تحويل العمود لتاريخ
            df['date_obj'] = pd.to_datetime(df['date'], errors='coerce')
            today_df = df[df['date_obj'].dt.date == date.today()]
            
            st.write(f"وجبات اليوم ({len(today_df)}):")
            for _, row in today_df.iterrows():
                st.markdown(f"""
                <div class='premium-card'>
                    <b>{row['food_name']}</b> - {row['calories']} cal
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"خطأ في عرض التاريخ: {e}")
    else:
        st.info("الملف 'entries' فاضي تماماً أو مش مقرؤ.")
        
    # --- قسم التشخيص (Debugger) ---
    st.divider()
    with st.expander("🛠️ لوحة المطور (Debug Info)"):
        st.write("حالة الاتصال:")
        if 'conn' in locals(): st.success("متصل بـ GSheets")
        
        st.write("محتوى ملف الأهداف (user_goals):")
        st.write(read_sheet("user_goals"))

if __name__ == "__main__":
    main()
