import streamlit as st
import cloudinary
import cloudinary.uploader
import re

# --- 1. PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Inventory Upload Portal")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Inventory Upload Portal")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect Access Code.")
        return False
    else:
        return True

# --- 2. CLOUDINARY CONFIG ---
def init_cloudinary():
    try:
        cloudinary.config(
            cloud_name = st.secrets["CLOUDINARY_NAME"],
            api_key = st.secrets["CLOUDINARY_KEY"],
            api_secret = st.secrets["CLOUDINARY_SECRET"]
        )
        return True
    except Exception as e:
        st.error(f"Cloudinary Config Error: {e}")
        return False

# --- 3. MAIN APP UI ---
st.set_page_config(page_title="Car Image Uploader", page_icon="📤")

if check_password():
    st.title("📤 Car Image & Metadata Uploader")
    st.markdown("Upload local images and assign metadata for your inventory.")

    if init_cloudinary():
        # --- METADATA SECTION ---
        st.header("1. Car Details (Metadata)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            brand = st.text_input("Brand", placeholder="e.g. TOYOTA")
            model = st.text_input("Model", placeholder="e.g. PRIUS")
        with col2:
            year = st.text_input("Year", placeholder="e.g. 2015")
            vin = st.text_input("VIN / Chassis No", placeholder="e.g. ZVW30-1234567")
        with col3:
            mileage = st.text_input("Mileage", placeholder="e.g. 120000")
            status = st.selectbox("Status", ["Coming", "Available", "Sold"])

        # --- FILE UPLOAD SECTION ---
        st.header("2. Upload Images")
        st.info("💡 **Tip:** To upload a folder, press `Ctrl+A` (or `Cmd+A`) inside the folder to select all images and drag them here.")
        
        uploaded_files = st.file_uploader(
            "Select Images", 
            type=['png', 'jpg', 'jpeg', 'webp'], 
            accept_multiple_files=True
        )

        if uploaded_files:
            st.write(f"📁 {len(uploaded_files)} images selected.")

        # --- UPLOAD EXECUTION ---
        if st.button("🚀 Start Bulk Upload"):
            if not vin or not brand:
                st.error("Please enter at least the Brand and VIN to organize files.")
            elif not uploaded_files:
                st.error("No images selected for upload.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                uploaded_urls = []
                
                # Create a safe folder name
                folder_path = f"inventory/{brand.upper()}/{vin.upper()}"
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Uploading image {i+1} of {len(uploaded_files)}...")
                    
                    try:
                        # Upload to Cloudinary
                        # We use 'context' for metadata and 'tags' for categorization
                        res = cloudinary.uploader.upload(
                            file,
                            folder = folder_path,
                            use_filename = True,
                            unique_filename = True,
                            context = {
                                "brand": brand,
                                "model": model,
                                "year": year,
                                "vin": vin,
                                "mileage": mileage,
                                "status": status
                            },
                            tags = [brand, status, year]
                        )
                        uploaded_urls.append(res['secure_url'])
                    except Exception as e:
                        st.error(f"Failed to upload {file.name}: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.empty()
                
                if uploaded_urls:
                    st.success(f"✅ Successfully uploaded {len(uploaded_urls)} images to Cloudinary!")
                    st.balloons()
                    
                    # Output for copy-pasting back to Excel/Sheets
                    st.subheader("Cloudinary URLs (Copy for your Sheet)")
                    
                    st.write("**Main Image (First one):**")
                    st.code(uploaded_urls[0], language="text")
                    
                    st.write("**All Images (Comma Separated list):**")
                    st.code(", ".join(uploaded_urls), language="text")
                    
                    # Preview the first image
                    st.image(uploaded_urls[0], caption="Main Image Preview", width=300)
