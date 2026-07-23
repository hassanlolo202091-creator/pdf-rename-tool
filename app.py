import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import re
import os
import zipfile
import tempfile
import easyocr

# إعداد واجهة الصفحة
st.set_page_config(page_title="PDF Rename Tool", page_icon="📄", layout="centered")

# --- نظام حماية الباسورد ---
PASSWORD = "123"

def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 تسجيل الدخول مطلوب")
        st.text_input("الرجاء إدخال كلمة المرور لدخول التطبيق:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 تسجيل الدخول مطلوب")
        st.text_input("الرجاء إدخال كلمة المرور لدخول التطبيق:", type="password", on_change=password_entered, key="password")
        st.error("😕 كلمة المرور غير صحيحة، حاول مرة أخرى.")
        return False
    else:
        return True

if check_password():
    st.markdown("<h3 style='text-align: center; color: #4B9CD3;'>👨‍💻 تصميم المهندس/ حسن إبراهيم</h3>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    st.title("📄 نظام إعادة تسمية تقارير الـ PDF تلقائياً")
    st.write("قم برفع ملفات الـ PDF وسيقوم النظام بمعالجتها واستخراج أُم الكود الصحيح بدقة متناهية.")

    @st.cache_resource
    def load_reader():
        return easyocr.Reader(['en'])

    with st.spinner("جاري تهيئة قارئ النصوص (OCR)... برجاء الانتظار"):
        reader = load_reader()

    uploaded_files = st.file_uploader("اختر ملفات الـ PDF أو اسحبها هنا", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 بدء المعالجة وإعادة التسمية"):
            processed_files = []
            
            with tempfile.TemporaryDirectory() as tmpdirname:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_files = len(uploaded_files)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    filename = uploaded_file.name
                    status_text.text(f"جاري معالجة الملف ({i+1}/{total_files}): {filename}")
                    
                    input_path = os.path.join(tmpdirname, filename)
                    with open(input_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    try:
                        doc = fitz.open(input_path)
                        page = doc[0]
                        width, height = page.rect.width, page.rect.height
                        
                        # توسيع نطاق القراءة قليلاً لضمان عدم قطع أطراف الكود
                        rect = fitz.Rect(width * 0.30, height * 0.03, width * 0.99, height * 0.32)
                        pix = page.get_pixmap(clip=rect, dpi=300)
                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        
                        text = reader.readtext(img_array, detail=0, paragraph=True)
                        full_text = " ".join(text).upper()
                        
                        clean_name = ""
                        
                        # 🟢 الحل الجذري: البحث عن أي تسلسل يحتوي على P30350 أو يشبهه بداخل النص بغض النظر عن أخطاء الـ OCR
                        # والبحث عن رقم التقرير النهائي (مثل RT-0036 أو ما يشابهه) لضمان دمج الاسم كاملاً
                        match_full = re.search(r'(P[-_\s]*303[50SO]+\b.*?RT[-_\s]*\d+)', full_text)
                        
                        if match_full:
                            raw_code = match_full.group(1)
                            # تنظيف وتصحيح الأخطاء الشائعة للـ OCR تلقائياً
                            fixed_code = raw_code.replace(" ", "").replace("_", "-")
                            fixed_code = fixed_code.replace("O", "0").replace("J", "3").replace("S", "5")
                            # ضمان الصيغة القياسية الصحيحة للمشروع
                            if "WQT" in full_text:
                                clean_name = f"P30350-KTI-WQT-PIP-RT-{re.search(r'RT[-_\s]*(\d+)', fixed_code).group(1)}.pdf"
                            elif "RDS" in full_text:
                                clean_name = f"P-30350-RDS-4-KTI-PIP-RT-{re.search(r'RT[-_\s]*(\d+)', fixed_code).group(1)}.pdf"
                            else:
                                clean_name = f"{fixed_code}.pdf"
                        else:
                            # لو لم يتم مطابقة النمط الكامل، ابحث عن كلمة Report No ورقمها مباشرة
                            report_no_match = re.search(r'REPORT\s*NO[:\s]*([A-Z0-9\-_]+)', full_text)
                            if report_no_match:
                                r_no = report_no_match.group(1).replace("O", "0").replace("J", "3")
                                clean_name = f"{r_no}.pdf"
                            else:
                                # لو فشل تماماً، اترك اسم الملف الأصلي كما هو لضمان عدم إتلافه
                                clean_name = filename
                        
                        doc.close()
                        
                        output_path = os.path.join(tmpdirname, clean_name)
                        os.rename(input_path, output_path)
                        processed_files.append((output_path, clean_name))
                        
                    except Exception as e:
                        st.error(f"خطأ في معالجة {filename}: {e}")
                    
                    progress_bar.progress((i + 1) / total_files)
                
                status_text.text("تم الانتهاء من المعالجة بنجاح! 🎉")
                
                zip_path = os.path.join(tmpdirname, "renamed_reports.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file_path, clean_name in processed_files:
                        zipf.write(file_path, arcname=clean_name)
                
                with open(zip_path, "rb") as f:
                    bytes_data = f.read()
                    
                st.download_button(
                    label="📥 تحميل كافة الملفات بعد إعادة التسمية (ZIP)",
                    data=bytes_data,
                    file_name="renamed_reports.zip",
                    mime="application/zip"
                )
