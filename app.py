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
st.set_page_config(page_title="X-Track Debug 🛠️", layout="centered", initial_sidebar_state="collapsed")

# --- CSS بسيط وواضح ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    * { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #333; }
    .stButton button { width: 100%; border-radius: 10px; font-weight: bold; }
    .success-box { background-color: #d1e7dd; padding: 10px; border-radius: 10px; color: #0f5132; margin-bottom: 10px;}
    .error-box { background-color: #f8d7da; padding: 10px; border-radius: 10px; color: #842029; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الاتصال (بدون إخفاء أخطاء)
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⛔ خطأ قاتل في الاتصال بـ Google Sheets:\n{e}")
    st.stop()

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try: model = genai.GenerativeModel('gemini-2.0-flash')
    except: model = None
else: model = None

# ==========================================
# 3. دوال التعامل مع الداتا (صريحة جداً)
# ==========================================
def read_sheet_raw(worksheet):
    # هذه الدالة لن تخفي الخطأ، ستظهره لك لتعرف السبب
    return conn.read(worksheet=worksheet, ttl=0)

def write_sheet_raw(worksheet, df):
    conn.update(worksheet=worksheet, data=df)
    st.cache_data.clear()

def repair_database():
    """يقوم بمسح الجداول وإعادة إنشائها بالهيكل الصحيح"""
    status = st.status("جاري إصلاح قاعدة البيانات...", expanded=True)
    try:
        # 1. إصلاح Entries
        status.write("⏳ جاري تهيئة جدول الوجبات (entries)...")
        df_entries = pd.DataFrame(columns=['id', 'date', 'meal_type', 'food_name', 'quantity', 'unit', 'calories', 'protein', 'carbs', 'fat'])
        write_sheet_raw("entries", df_entries)
        
        # 2. إصلاح Goals
        status.write("⏳ جاري تهيئة جدول الأهداف (user_goals)...")
        df_goals = pd.DataFrame([{'cal_goal': 2000, 'pro_goal': 150, 'carb_goal': 250, 'fat_goal': 70}])
        write_sheet_raw("user_goals", df_goals)
        
        # 3. إصلاح Metrics
        status.write("⏳ جاري تهيئة جدول القياسات (health_metrics)...")
        df_metrics = pd.DataFrame(columns=['date', 'muscle_mass', 'fat_percentage', 'water_percentage', 'steps', 'avg_heart_rate', 'sleep_hours', 'weight'])
        write_sheet_raw("health_metrics", df_metrics)
        
        # 4. إصلاح Library
        status.write("⏳ جاري تهيئة المكتبة (food_library)...")
        df_lib = pd.DataFrame(columns=['food_name', 'default_unit', 'calories_per_unit', 'protein_per_unit', 'carbs_per_unit', 'fat_per_unit'])
        write_sheet_raw("food_library", df_lib)
        
        status.update(label="✅ تمت عملية الإصلاح بنجاح! قاعدة البيانات جاهزة.", state="complete", expanded=False)
        st.success("تم إعادة ضبط النظام. جرب الإضافة الآن.")
        
    except Exception as e:
        status.update(label="❌ فشل الإصلاح", state="error")
        st.error(f"تفاصيل الخطأ: {e}")
        st.info("تأكد أنك أنشأت التبويبات (entries, user_goals, ...) داخل ملف Google Sheet يدوياً.")

def save_entry(item, meal_type):
    try:
        # قراءة البيانات الحالية
        try:
            df = read_sheet_raw("entries")
        except:
            df = pd.DataFrame(columns=['id', 'date', 'meal_type', 'food_name', 'quantity', 'unit', 'calories', 'protein', 'carbs', 'fat'])

        # تجهيز الصف الجديد
        # معالجة القيم الفارغة
        cals = float(item.get('cals') or 0)
        pro = float(item.get('pro') or 0)
        carb = float(item.get('carb') or 0)
        fat = float(item.get('fat') or 0)
        
        # تحديد ID
        new_id = 1
        if not df.empty and 'id' in df.columns:
            # تنظيف عمود الـ ID من أي قيم غير رقمية
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0)
            new_id = int(df['id'].max()) + 1

        new_row = {
            'id': new_id,
            'date': str(date.today()),
            'meal_type': str(meal_type),
            'food_name': str(item['name']),
            'quantity': float(item['qty']),
            'unit': str(item['unit']),
            'calories': cals,
            'protein': pro,
            'carbs': carb,
            'fat': fat
        }
        
        # الدمج والحفظ
        updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        write_sheet_raw("entries", updated_df)
        return True
    except Exception as e:
        st.error(f"خطأ أثناء الحفظ: {e}")
        return False

# ==========================================
# 4. الواجهة والمنطق
# ==========================================
def main():
    st.title("X-Track Debugger 🛠️")
    
    # --- زر اختبار الاتصال (أول حاجة تعملها) ---
    if st.button("🔌 اضغط هنا لاختبار الاتصال بجوجل (Test Connection)", type="secondary"):
        try:
            df_test = read_sheet_raw("entries")
            st.success(f"✅ الاتصال ناجح! تم قراءة الجدول 'entries'. عدد الصفوف: {len(df_test)}")
            st.write(df_test.head())
        except Exception as e:
            st.error(f"❌ الاتصال فشل. السبب:\n{e}")
            st.warning("تأكد أنك أضفت إيميل الروبوت (Service Account) كـ Editor في ملف الشيت، وأنك أنشأت التبويب 'entries'.")

    # --- القائمة الجانبية ---
    with st.sidebar:
        st.header("أدوات الصيانة")
        if st.button("⚠️ إعادة ضبط المصنع (Repair DB)", type="primary"):
            repair_database()
            
    # --- التبويبات ---
    tabs = st.tabs(["🏠 إضافة يدوية (Test)", "🤖 إضافة ذكية (AI)", "📋 السجل (Log)"])

    # 1. إضافة يدوية للتجربة (عشان نتأكد العيب مش من AI)
    with tabs[0]:
        st.subheader("تجربة إضافة بدون ذكاء اصطناعي")
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            name = c1.text_input("اسم الأكل", "تجربة")
            cal = c2.number_input("سعرات", 100)
            submitted = st.form_submit_button("حفظ تجريبي")
            if submitted:
                item = {'name': name, 'qty': 1, 'unit': 'test', 'cals': cal, 'pro': 0, 'carb': 0, 'fat': 0}
                if save_entry(item, "تجربة"):
                    st.success("✅ تمت الإضافة! روح شوف السجل.")

    # 2. إضافة الذكاء الاصطناعي
    with tabs[1]:
        st.subheader("تجربة Gemini")
        user_input = st.text_input("أكلت إيه؟")
        if st.button("تحليل"):
            if not model:
                st.error("مفتاح Gemini API غير موجود")
            else:
                prompt = f"""حلل: "{user_input}". رد JSON فقط: {{ "items": [ {{ "name": "اسم", "qty": رقم, "unit": "وحدة", "cals": رقم, "pro": رقم, "carb": رقم, "fat": رقم }} ] }}"""
                try:
                    res = model.generate_content(prompt)
                    clean = res.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean)
                    items = data.get("items", [])
                    if items:
                        for i in items:
                            st.write(f"سيتم حفظ: {i['name']} ({i['cals']} cal)")
                            save_entry(i, "وجبة")
                        st.success("تم الحفظ!")
                    else:
                        st.warning("لم يتعرف على الطعام")
                except Exception as e:
                    st.error(f"خطأ AI: {e}")

    # 3. السجل (مع عرض الأخطاء لو فاضي)
    with tabs[2]:
        st.subheader("بيانات الجدول 'entries'")
        try:
            df = read_sheet_raw("entries")
            if df.empty:
                st.info("الجدول موجود بس فاضي.")
            else:
                # تحويل التاريخ للتأكد
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
                    today_df = df[df['date'] == date.today()]
                    st.metric("عدد وجبات اليوم", len(today_df))
                    st.dataframe(df)
                else:
                    st.warning("الجدول موجود بس مفيهوش عمود 'date'!")
                    st.dataframe(df)
        except Exception as e:
            st.error(f"مش عارف أقرأ السجل: {e}")

if __name__ == "__main__":
    main()
