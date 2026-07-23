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

st.title("📄 نظام إعادة تسمية تقارير الـ PDF تلقائياً")
st.write("قم برفع ملفات الـ PDF وسيقوم النظام بقراءتها، استخراج أرقام التقارير، وإعادة تسميتها بالشكل المعياري الصحيح.")

# تحميل قارئ النصوص (مخبأ مؤقتاً لعدم إبطاء التطبيق)
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

with st.spinner("جاري تهيئة قارئ النصوص (OCR)... برجاء الانتظار"):
    reader = load_reader()

# نافذة لرفع الملفات
uploaded_files = st.file_uploader("اختر ملفات الـ PDF أو اسحبها هنا", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 بدء المعالجة وإعادة التسمية"):
        processed_files = []
        
        # إنشاء مجلد مؤقت للعمليات
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
                    
                    # منطقة القص العلوية
                    rect = fitz.Rect(width * 0.35, height * 0.05, width * 0.98, height * 0.25)
                    pix = page.get_pixmap(clip=rect, dpi=300)
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    
                    # قراءة النص
                    text = reader.readtext(img_array, detail=0, paragraph=True)
                    full_text = " ".join(text).upper()
                    
                    # البحث عن النمط
                    match = re.search(r'P[-_A-Z0-9\s\|\+]+?RT[-_\|\s]*(\d+)', full_text)
                    
                    if match:
                        raw_match = match.group(0)
                        report_num = match.group(1)
                        
                        if len(report_num) == 5 and report_num.startswith('0'):
                            report_num = report_num[1:]
                            
                        if 'RDS' in raw_match or 'RDS' in full_text:
                            clean_name = f"P-30350-RDS-4-KTI-PIP-RT-{report_num}.pdf"
                        elif 'WQT' in raw_match or 'WQT' in full_text:
                            clean_name = f"P30350-KTI-WQT-PIP-RT-{report_num}.pdf"
                        else:
                            clean_name = f"P-30350-UNKNOWN-RT-{report_num}.pdf"
                    else:
                        clean_name = f"unnamed_{filename}"
                    
                    doc.close()
                    
                    output_path = os.path.join(tmpdirname, clean_name)
                    # حفظ الملف بالاسم الجديد
                    os.rename(input_path, output_path)
                    processed_files.append((output_path, clean_name))
                    
                except Exception as e:
                    st.error(f"خطأ في معالجة {filename}: {e}")
                
                progress_bar.progress((i + 1) / total_files)
            
            status_text.text("تم الانتهاء من المعالجة بنجاح! 🎉")
            
            # ضغط الملفات في ملف ZIP لتنزيلها مرة واحدة
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
