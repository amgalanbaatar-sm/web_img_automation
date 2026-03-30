import streamlit as st
import cloudinary
import cloudinary.uploader
import re

# --- 1. PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "admin"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Inventory Portal")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Inventory Portal")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect Access Code.")
        return False
    else:
        return True

# --- 2. CLOUDINARY CONFIG ---
def init_cloudinary():
    try:
        # .strip() is added here to prevent "Invalid Signature" errors caused by accidental spaces
        cloudinary.config(
            cloud_name = st.secrets["CLOUDINARY_NAME"].strip(),
            api_key = st.secrets["CLOUDINARY_KEY"].strip(),
            api_secret = st.secrets["CLOUDINARY_SECRET"].strip(),
            secure = True
        )
        return True
    except Exception as e:
        st.error(f"Cloudinary Config Error: {e}")
        return False

# --- 3. MAIN APP UI ---
st.set_page_config(page_title="Car Image Uploader", page_icon="📤")

if check_password():
    st.title("📤 Car Inventory Uploader")
    
    if init_cloudinary():
        # --- METADATA SECTION ---
        st.header("1. Car Details")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            brand = st.text_input("Brand (Required)", placeholder="TOYOTA")
            model = st.text_input("Model", placeholder="Sai")
        with col2:
            year = st.text_input("Year", placeholder="2018")
            vin = st.text_input("VIN / Chassis (Required)", placeholder="AZK10-12345")
        with col3:
            mileage = st.text_input("Mileage", placeholder="85000")
            status = st.selectbox("Status", ["Coming", "Available", "Sold"])

        # --- FILE UPLOAD SECTION ---
        st.header("2. Images")
        uploaded_files = st.file_uploader(
            "Drag and drop images here", 
            type=['png', 'jpg', 'jpeg', 'webp'], 
            accept_multiple_files=True
        )

        if uploaded_files:
            st.info(f"✔ {len(uploaded_files)} images ready for upload.")

        # --- UPLOAD EXECUTION ---
        if st.button("🚀 Start Bulk Upload"):
            if not vin or not brand:
                st.error("Please enter both Brand and VIN/Chassis No.")
            elif not uploaded_files:
                st.error("Please select images first.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                uploaded_urls = []
                
                # Sanitize folder path
                clean_brand = re.sub(r'[^a-zA-Z0-9]', '', brand).upper()
                clean_vin = re.sub(r'[^a-zA-Z0-9]', '', vin).upper()
                folder_path = f"inventory/{clean_brand}/{clean_vin}"
                
                # Build metadata - ONLY include non-empty values
                meta_dict = {}
                if brand: meta_dict["brand"] = brand
                if model: meta_dict["model"] = model
                if year: meta_dict["year"] = year
                if vin: meta_dict["vin"] = vin
                if mileage: meta_dict["mileage"] = mileage
                if status: meta_dict["status"] = status

                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name} ({i+1}/{len(uploaded_files)})...")
                    
                    try:
                        # Uploading
                        res = cloudinary.uploader.upload(
                            file,
                            folder = folder_path,
                            use_filename = True,
                            unique_filename = True,
                            context = meta_dict, # Passed as a clean dictionary
                            tags = [clean_brand, status]
                        )
                        uploaded_urls.append(res['secure_url'])
                    except Exception as e:
                        st.error(f"Failed to upload {file.name}: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.empty()
                
                if uploaded_urls:
                    st.success(f"✅ Upload Complete! {len(uploaded_urls)} images saved.")
                    
                    st.subheader("Results for Spreadsheet")
                    st.write("**Main Image:**")
                    st.code(uploaded_urls[0], language="text")
                    
                    st.write("**Image List (Comma Separated):**")
                    st.code(", ".join(uploaded_urls), language="text")
                    
                    st.image(uploaded_urls[0], caption="Main Image Preview", width=300)
                    st.balloons()
