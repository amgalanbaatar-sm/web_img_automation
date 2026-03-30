import streamlit as st
import cloudinary
import cloudinary.uploader
import pandas as pd
import re
import io

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
# Changed layout to "centered" to fix the ultrawide screen stretching issue
st.set_page_config(page_title="Bulk Car Uploader", page_icon="📤", layout="centered")

if check_password():
    st.title("🚗 CSV-Driven Inventory Uploader")
    
    if init_cloudinary():
        st.header("1. Upload Inventory CSV")
        st.info("💡 Ensure your CSV has columns named **Brand**, **Series**, and **VIN**. Use a **Tags** column with dash-separated values (e.g., `Coming-Hot-Promo`).")
        
        uploaded_csv = st.file_uploader("Upload CSV File", type=['csv'])
        
        if uploaded_csv:
            df = pd.read_csv(uploaded_csv)
            st.subheader("Data Preview")
            st.dataframe(df.head(3), use_container_width=True)
            
            cols_lower = [str(c).lower().strip() for c in df.columns]
            
            if not all(req in cols_lower for req in ['brand', 'series', 'vin']):
                st.error("🚨 Missing required columns! Your CSV must contain 'Brand', 'Series', and 'VIN'.")
                st.stop()
                
            st.header("2. Assign Images per Vehicle")
            
            upload_queue = []
            
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                
                row_lower = {str(k).lower().strip(): v for k, v in row_dict.items()}
                brand = str(row_lower.get('brand', 'Unknown'))
                series = str(row_lower.get('series', 'Unknown'))
                vin = str(row_lower.get('vin', 'Unknown'))
                
                with st.expander(f"🚙 {brand} {series} | VIN: {vin}", expanded=False):
                    c1, c2 = st.columns(2)
                    with c1:
                        main_img = st.file_uploader("Upload Main Image (1)", type=['png', 'jpg', 'jpeg', 'webp'], key=f"main_{index}")
                    with c2:
                        # Updated label to explicitly instruct users about the drag-and-drop folder feature
                        other_imgs = st.file_uploader("Upload Other Images (Drag & Drop a folder here)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True, key=f"other_{index}")
                    
                    upload_queue.append({
                        "index": index,
                        "row_dict": row_dict,
                        "main_img": main_img,
                        "other_imgs": other_imgs,
                        "brand": brand,
                        "series": series,
                        "vin": vin
                    })
            
            st.header("3. Execute Upload")
            
            ready_to_process = any(item['main_img'] is not None or len(item['other_imgs']) > 0 for item in upload_queue)
            
            if st.button("🚀 Begin Processing Staged Images", disabled=not ready_to_process, type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = []
                
                for i, item in enumerate(upload_queue):
                    status_text.text(f"Processing row {i+1}/{len(upload_queue)} (VIN: {item['vin']})...")
                    
                    context_dict = {}
                    for k, v in item['row_dict'].items():
                        if pd.notna(v) and str(v).strip() != "":
                            clean_val = str(v).replace('=', '').replace('|', '') 
                            context_dict[str(k)] = clean_val
                    
                    tags = []
                    tags_col = next((k for k in item['row_dict'].keys() if str(k).lower().strip() == 'tags'), None)
                    if tags_col and pd.notna(item['row_dict'][tags_col]):
                        raw_tags = str(item['row_dict'][tags_col]).split('-')
                        tags = [t.strip() for t in raw_tags if t.strip()]
                    
                    clean_brand = re.sub(r'[^a-zA-Z0-9]', '', item['brand']).upper()
                    clean_series = re.sub(r'[^a-zA-Z0-9]', '', item['series']).upper()
                    clean_vin = re.sub(r'[^a-zA-Z0-9]', '', item['vin']).upper()
                    folder_path = f"inventory/{clean_brand}/{clean_series}/{clean_vin}"
                    
                    main_url = ""
                    other_urls = []
                    
                    if item['main_img']:
                        try:
                            res = cloudinary.uploader.upload(
                                item['main_img'],
                                folder=folder_path,
                                context=context_dict,
                                tags=tags + ["main"],
                                use_filename=True,
                                unique_filename=True,
                                overwrite=True
                            )
                            main_url = res['secure_url']
                        except Exception as e:
                            st.error(f"Error with Main Image for VIN {item['vin']}: {e}")
                    
                    if item['other_imgs']:
                        for file in item['other_imgs']:
                            try:
                                res = cloudinary.uploader.upload(
                                    file,
                                    folder=folder_path,
                                    context=context_dict,
                                    tags=tags,
                                    use_filename=True,
                                    unique_filename=True,
                                    overwrite=True
                                )
                                other_urls.append(res['secure_url'])
                            except Exception as e:
                                st.error(f"Error with Other Image for VIN {item['vin']}: {e}")
                    
                    updated_row = item['row_dict'].copy()
                    updated_row['MAIN_IMG_URL'] = main_url
                    updated_row['OTHER_IMG_URLS'] = ", ".join(other_urls)
                    results.append(updated_row)
                    
                    progress_bar.progress((i + 1) / len(upload_queue))
                
                status_text.success("✅ All uploads completed successfully!")
                
                st.session_state['processed_df'] = pd.DataFrame(results)

            # --- 4. RESULTS & DOWNLOAD ---
            if 'processed_df' in st.session_state:
                st.subheader("Final Output")
                st.dataframe(st.session_state['processed_df'], use_container_width=True)
                
                csv_data = st.session_state['processed_df'].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Updated Inventory CSV",
                    data=csv_data,
                    file_name="updated_inventory_with_urls.csv",
                    mime="text/csv",
                    type="primary"
                )
