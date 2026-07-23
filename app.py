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

# تفعيل التحقق قبل فتح التطبيق
if check_password():
    # الترحيب المخصص
    st.markdown("<h3 style='text-align: center; color: #4B9CD3;'>👨‍💻 تصميم المهندس/ حسن إبراهيم</h3>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    st.title("📄 نظام إعادة تسمية تقارير الـ PDF تلقائياً")
    st.write("قم برفع ملفات الـ PDF وسيقوم النظام بقراءتها واستخراج صيغة التسمية الواقعة بعد كلمة (Report No) وتصحيح أخطاء الـ OCR تلقائياً.")

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
                        
                        # منطقة القص العلوية للبحث عن رقم التقرير بدقة
                        rect = fitz.Rect(width * 0.25, height * 0.03, width * 0.99, height * 0.35)
                        
                        # زيادة دقة الصورة لـ 400 وتحويلها لرمادي لتحسين دقة القراءة جداً
                        pix = page.get_pixmap(clip=rect, dpi=400, colorspace=fitz.csGRAY)
                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        
                        # إجبار القارئ على التعرف على هذه الرموز فقط لتجنب الشوائب
                        allowlist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-./ '
                        text = reader.readtext(img_array, detail=0, paragraph=True, allowlist=allowlist)
                        full_text = " ".join(text).upper()
                        
                        clean_name = ""
                        
                        # تعبير نمطي مرن يلتقط ما بعد REPORT NO
                        report_match = re.search(r'REP(?:ORT)?[\s\.\-_]*NO[:\s\.\-_]*([A-Z0-9\-_/\.\s]{3,35})', full_text)
                        
                        if report_match:
                            raw_code = report_match.group(1).strip()
                            
                            # --- فلتر التصحيح الذكي (Smart Correction Filter) ---
                            # بيعالج اللخبطة البصرية المعتادة في الـ OCR من غير ما يجبره على اسم مشروع ثابت
                            corrected_code = raw_code.replace('P.', 'P-')
                            corrected_code = corrected_code.replace('O', '0')
                            corrected_code = corrected_code.replace('J', '3')
                            corrected_code = corrected_code.replace('-A-', '-4-')
                            corrected_code = corrected_code.replace('WAT', 'WQT')
                            
                            # تنظيف المسافات والرموز غير المسموحة في أسماء الويندوز
                            extracted_code = re.sub(r'[\s/\\:\*\?"<>\|]+', '-', corrected_code).strip('-')
                            
                            if extracted_code:
                                clean_name = f"{extracted_code}.pdf"
                            else:
                                clean_name = filename
                        else:
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
