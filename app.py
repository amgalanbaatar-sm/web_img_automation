import streamlit as st
import cloudinary
import cloudinary.uploader
import re
import time

# --- 1. ACCESS CONTROL ---
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
        # We strip() to ensure no hidden newline characters from the secrets manager
        cloudinary.config(
            cloud_name = st.secrets["CLOUDINARY_NAME"].strip(),
            api_key = st.secrets["CLOUDINARY_KEY"].strip(),
            api_secret = st.secrets["CLOUDINARY_SECRET"].strip(),
            secure = True
        )
        return True
    except Exception as e:
        st.error(f"Configuration Error: {e}")
        return False

# --- 3. MAIN APP UI ---
st.set_page_config(page_title="Car Uploader", page_icon="📤")

if check_password():
    st.title("🚗 Car Inventory Uploader")
    
    if init_cloudinary():
        # --- METADATA SECTION ---
        st.header("1. Car Details")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            brand = st.text_input("Brand", placeholder="TOYOTA").strip()
            model = st.text_input("Model", placeholder="Sai").strip()
        with c2:
            year = st.text_input("Year", placeholder="2018").strip()
            vin = st.text_input("VIN / Chassis", placeholder="AZK10-12345").strip()
        with c3:
            mileage = st.text_input("Mileage", placeholder="85000").strip()
            status = st.selectbox("Status", ["Coming", "Available", "Sold"])

        # --- FILE UPLOAD SECTION ---
        st.header("2. Select Images")
        uploaded_files = st.file_uploader(
            "Select multiple images or drag folder contents here", 
            type=['png', 'jpg', 'jpeg', 'webp'], 
            accept_multiple_files=True
        )

        # --- UPLOAD EXECUTION ---
        if st.button("🚀 Start Bulk Upload"):
            if not vin or not brand:
                st.error("Brand and VIN are required to create the folder structure.")
            elif not uploaded_files:
                st.error("Please select at least one image.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                uploaded_urls = []
                
                # Sanitize identifiers for folder naming
                clean_brand = re.sub(r'[^a-zA-Z0-9]', '', brand).upper()
                clean_vin = re.sub(r'[^a-zA-Z0-9]', '', vin).upper()
                folder_path = f"inventory/{clean_brand}/{clean_vin}"
                
                # 1. BUILD CLEAN METADATA (Context)
                # We strictly exclude any empty strings to prevent signature mismatch
                meta_dict = {}
                if brand: meta_dict["brand"] = brand
                if model: meta_dict["model"] = model
                if year: meta_dict["year"] = year
                if vin: meta_dict["vin"] = vin
                if mileage: meta_dict["mileage"] = mileage
                meta_dict["status"] = status

                # 2. PREPARE TAGS
                tag_list = [clean_brand, status]
                if year: tag_list.append(year)

                # 3. LOOP THROUGH FILES
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {file.name} ({i+1}/{len(uploaded_files)})...")
                    
                    try:
                        # We use the explicit params here. 
                        # Cloudinary SDK will generate the signature based on these.
                        res = cloudinary.uploader.upload(
                            file,
                            folder = folder_path,
                            context = meta_dict,
                            tags = tag_list,
                            use_filename = True,
                            unique_filename = True,
                            overwrite = True
                        )
                        uploaded_urls.append(res['secure_url'])
                    except Exception as e:
                        st.error(f"Error with {file.name}: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.empty()
                
                if uploaded_urls:
                    st.success(f"✅ Successfully uploaded {len(uploaded_urls)} images!")
                    
                    # Formatting results for the 'Inventory' Google Sheet
                    st.subheader("Results for Spreadsheet")
                    
                    st.write("**Column: MAIN_IMG (First URL)**")
                    st.code(uploaded_urls[0], language="text")
                    
                    st.write("**Column: IMG_LIST (All URLs comma-separated)**")
                    st.code(", ".join(uploaded_urls), language="text")
                    
                    st.image(uploaded_urls[0], caption="Preview of Main Image", width=400)
                    st.balloons()
