import streamlit as st
import cloudinary
import cloudinary.uploader
import re

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
        # Strictly follow the expert advice to use clean, stripped credentials
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
            brand_in = st.text_input("Brand", placeholder="TOYOTA").strip()
            model_in = st.text_input("Model", placeholder="Sai").strip()
        with c2:
            year_in = st.text_input("Year", placeholder="2018").strip()
            vin_in = st.text_input("VIN / Chassis", placeholder="AZK10-12345").strip()
        with c3:
            mileage_in = st.text_input("Mileage", placeholder="85000").strip()
            status_in = st.selectbox("Status", ["Coming", "Available", "Sold"])

        # --- FILE UPLOAD SECTION ---
        st.header("2. Select Images")
        uploaded_files = st.file_uploader(
            "Select multiple images", 
            type=['png', 'jpg', 'jpeg', 'webp'], 
            accept_multiple_files=True
        )

        # --- UPLOAD EXECUTION ---
        if st.button("🚀 Start Bulk Upload"):
            if not vin_in or not brand_in:
                st.error("Brand and VIN are required.")
            elif not uploaded_files:
                st.error("Please select at least one image.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                uploaded_urls = []
                
                # Pruning and cleaning inputs
                clean_brand = re.sub(r'[^a-zA-Z0-9]', '', brand_in).upper()
                clean_vin = re.sub(r'[^a-zA-Z0-9]', '', vin_in).upper()
                
                # 1. BUILD CLEAN PARAMS (Strictly following expert diagnosis)
                # We build a dictionary and ONLY add keys that have values.
                # This prevents "key=|" (empty values) from entering the signature.
                
                # Build Context (Metadata)
                ctx = {}
                if brand_in: ctx["brand"] = brand_in
                if model_in: ctx["model"] = model_in
                if year_in: ctx["year"] = year_in
                if vin_in: ctx["vin"] = vin_in
                if mileage_in: ctx["mileage"] = mileage_in
                ctx["status"] = status_in

                # Build Tags
                tags = [clean_brand, status_in]
                if year_in: tags.append(year_in)

                # Initialize final params dictionary
                # This dictionary contains only non-empty, valid parameters
                upload_params = {
                    "folder": f"inventory/{clean_brand}/{clean_vin}",
                    "tags": tags,
                    "context": ctx,
                    "use_filename": True,
                    "unique_filename": True,
                    "overwrite": True
                }

                # 2. LOOP THROUGH FILES
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {file.name} ({i+1}/{len(uploaded_files)})...")
                    
                    try:
                        # Passing the clean upload_params to the SDK
                        # The SDK handles the timestamp and signature generation automatically
                        res = cloudinary.uploader.upload(
                            file,
                            **upload_params
                        )
                        uploaded_urls.append(res['secure_url'])
                    except Exception as e:
                        st.error(f"Error with {file.name}: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.empty()
                
                if uploaded_urls:
                    st.success(f"✅ Successfully uploaded {len(uploaded_urls)} images!")
                    st.subheader("Results for Spreadsheet")
                    st.write("**MAIN_IMG:**")
                    st.code(uploaded_urls[0], language="text")
                    st.write("**IMG_LIST:**")
                    st.code(", ".join(uploaded_urls), language="text")
                    st.image(uploaded_urls[0], width=300)
                    st.balloons()
