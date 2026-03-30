import streamlit as st
import cloudinary
import cloudinary.uploader
import requests
from bs4 import BeautifulSoup
import re

# --- 1. PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Access Restricted")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Access Restricted")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect Access Code.")
        return False
    else:
        return True

# --- 2. CONFIGURATION & SCRAPER LOGIC ---
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

def extract_car_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Determine Title
        title = "Unknown_Car"
        if soup.find('h1'):
            title = soup.find('h1').text.strip()
        
        images = []
        if "beforward.jp" in url:
            # Scrape Beforward (Force Large Images)
            for img in soup.find_all('img', src=re.compile(r'catalog')):
                src = img.get('src')
                large_url = src.replace('/t/', '/l/').split('?')[0]
                if not large_url.startswith('http'): large_url = "https:" + large_url
                if large_url not in images: images.append(large_url)
        
        elif "sbtjapan.com" in url:
            # Scrape SBT
            for img in soup.find_all('img', src=re.compile(r'images.sbtjapan.com')):
                src = img.get('data-src') or img.get('src')
                if src:
                    full_src = src.split('?')[0]
                    if full_src not in images: images.append(full_src)
        else:
            # Fallback
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and src.startswith('http'): images.append(src)

        return images, title
    except Exception as e:
        st.error(f"Error fetching {url}: {e}")
        return [], "Error"

# --- 3. MAIN APP UI ---
st.set_page_config(page_title="Car Image Porter", page_icon="📸")

if check_password():
    st.title("🚗 Car Image Auto-Porter")
    st.markdown("Extract dealer images and upload them to your Cloudinary account.")

    if init_cloudinary():
        # Input Section
        raw_input = st.text_area(
            "Paste Links (Multiple lines or Comma-separated):", 
            height=150, 
            placeholder="https://www.beforward.jp/...\nhttps://www.sbtjapan.com/..."
        )

        if st.button("🚀 Process & Upload to Cloudinary"):
            # Split by comma or newline
            links = re.split(r'[,\n]', raw_input)
            links = [l.strip() for l in links if l.strip()]

            if not links:
                st.error("No links provided.")
            else:
                for idx, link in enumerate(links):
                    with st.expander(f"Car {idx+1}: {link[:50]}...", expanded=True):
                        st.info("🔍 Scraping website...")
                        img_urls, car_name = extract_car_data(link)
                        
                        if not img_urls:
                            st.warning("No images found.")
                            continue
                        
                        st.write(f"✅ Found **{len(img_urls)}** images for: **{car_name}**")
                        
                        # Uploading
                        progress_bar = st.progress(0)
                        uploaded_urls = []
                        folder_safe_name = re.sub(r'[^a-zA-Z0-9]', '_', car_name)[:50]

                        for i, img_url in enumerate(img_urls[:30]): # Limit to 30 images
                            try:
                                res = cloudinary.uploader.upload(
                                    img_url,
                                    folder = f"auto_imports/{folder_safe_name}",
                                    context = {"car_name": car_name, "source": link}
                                )
                                uploaded_urls.append(res['secure_url'])
                            except:
                                pass
                            progress_bar.progress((i + 1) / min(len(img_urls), 30))
                        
                        if uploaded_urls:
                            st.success(f"Uploaded {len(uploaded_urls)} images!")
                            st.image(uploaded_urls[0], width=300, caption="Main Image Preview")
                            # Provide the text for the user to copy
                            st.text_area("Copy these Cloudinary Links:", value=", ".join(uploaded_urls), key=f"out_{idx}")
                
                st.balloons()
