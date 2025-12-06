import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
import re
from datetime import date

# ==========================================
# 1. إعداد الصفحة
# ==========================================
st.set_page_config(page_title="X-Track Tester 🧪", layout="centered")
st.title("🧪 X-Track Diagnostic Mode")

# ==========================================
# 2. فحص المفاتيح (Secrets Check)
# ==========================================
st.subheader("1️⃣ فحص المفاتيح (Secrets)")

gemini_key = st.secrets.get("GEMINI_API_KEY", "")
if gemini_key:
    st.success(f"✅ مفتاح Gemini موجود (يبدأ بـ: {gemini_key[:5]}...)")
    genai.configure(api_key=gemini_key)
else:
    st.error("❌ مفتاح Gemini غير موجود في secrets.toml")
    st.stop()

# ==========================================
# 3. اختبار الذكاء الاصطناعي (AI Test)
# ==========================================
st.subheader("2️⃣ اختبار الذكاء الاصطناعي (Gemini)")

user_input = st.text_input("جرب تكتب أي أكلة هنا (مثلاً: تفاحة):", "تفاحة")

if st.button("اختبار الـ AI"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        # 1. تجربة رد بسيط
        response = model.generate_content("رد بكلمة واحدة: مرحبا")
        st.info(f"🟢 حالة الاتصال: {response.text}")
        
        # 2. تجربة التحليل (السبب المحتمل للمشكلة)
        prompt = f"""
        أنت خبير تغذية. حلل: "{user_input}".
        المطلوب: رد بصيغة JSON فقط وبدون أي علامات Markdown.
        الشكل: {{ "items": [ {{ "name": "اسم", "qty": 1, "unit": "عدد", "cals": 0, "pro": 0, "carb": 0, "fat": 0 }} ] }}
        """
        res_json = model.generate_content(prompt)
        st.text("الرد الخام من Gemini:")
        st.code(res_json.text) # هنا هيبان لو الرد مش JSON
        
        # محاولة التنظيف
        clean_text = res_json.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        st.success("✅ التحليل والتحويل لـ JSON نجح!")
        st.write(data)
        
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء الاتصال بـ Gemini:\n{e}")

# ==========================================
# 4. اختبار قاعدة البيانات (Sheets Test)
# ==========================================
st.subheader("3️⃣ اختبار قاعدة البيانات (Google Sheets)")

if st.button("اختبار الاتصال والحفظ"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # محاولة قراءة
        df = conn.read(worksheet="entries", ttl=0)
        st.success(f"✅ الاتصال نجح! عدد الوجبات المسجلة: {len(df)}")
        st.write(df.head())
        
        # محاولة كتابة تجريبية
        import time
        test_id = int(time.time())
        new_row = pd.DataFrame([{
            "id": test_id, "date": str(date.today()), "meal_type": "Test", 
            "food_name": "Test Item", "quantity": 1, "unit": "Test", 
            "calories": 0, "protein": 0, "carbs": 0, "fat": 0
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="entries", data=updated_df)
        st.success("✅ تمت الكتابة بنجاح! (تم إضافة Test Item)")
        
    except Exception as e:
        st.error(f"❌ فشل الاتصال بـ Google Sheets:\n{e}")
        st.warning("تأكد أنك أنشأت صفحة اسمها 'entries' في ملف الإكسل وأن الإيميل مضاف كـ Editor.")
