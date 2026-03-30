import streamlit as st
import cloudinary
import cloudinary.uploader
import requests
from bs4 import BeautifulSoup
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
    # Use a more realistic browser header to prevent blocking
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Determine Car Title
        title = "Imported_Car"
        if "sbtjapan" in url:
            # Try to get the ID from the URL (e.g., AB5611)
            url_parts = url.split('/')
            car_id = url_parts[-2] if "photolist" in url else url_parts[-1]
            title = f"SBT_{car_id}"
        elif soup.find('h1'):
            title = soup.find('h1').text.strip()
        
        images = []

        # 2. SBT JAPAN SPECIFIC LOGIC (Regex scan for lazy-loaded images)
        if "sbtjapan.com" in url:
            # This finds all high-res images in the page source text, even if hidden in Javascript
            found_images = re.findall(r'https://images\.sbtjapan\.com/images/car/[^"\'>\s]+\.jpg', res.text)
            for img in found_images:
                # SBT often lists thumbnails and large images. We want the ones without "_t" (thumbnail)
                full_img = img.replace('_t.jpg', '.jpg')
                if full_img not in images:
                    images.append(full_img)
        
        # 3. BEFORWARD SPECIFIC LOGIC
        elif "beforward.jp" in url:
            for img in soup.find_all('img', src=re.compile(r'catalog')):
                src = img.get('src')
                # Convert thumbnail /t/ to large /l/
                large_url = src.replace('/t/', '/l/').split('?')[0]
                if not large_url.startswith('http'): large_url = "https:" + large_url
                if large_url not in images: images.append(large_url)
        
        # 4. FALLBACK
        else:
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
    st.markdown("Works with **SBTJapan (including Photolists)** and **BeForward**.")

    if init_cloudinary():
        raw_input = st.text_area(
            "Paste Links (One per line):", 
            height=150, 
            placeholder="https://www.sbtjapan.com/mn/used-cars/AB5611/photolist"
        )

        if st.button("🚀 Process & Upload to Cloudinary"):
            links = [l.strip() for l in re.split(r'[,\n]', raw_input) if l.strip()]

            if not links:
                st.error("No links provided.")
            else:
                for idx, link in enumerate(links):
                    with st.expander(f"Car {idx+1}: {link[:50]}...", expanded=True):
                        img_urls, car_name = extract_car_data(link)
                        
                        if not img_urls:
                            st.warning(f"No images found for {link}. The site might be blocking the request.")
                            continue
                        
                        st.write(f"✅ Found **{len(img_urls)}** images for: **{car_name}**")
                        
                        progress_bar = st.progress(0)
                        uploaded_urls = []
                        folder_name = re.sub(r'[^a-zA-Z0-9]', '_', car_name)[:50]

                        # Cloudinary Upload
                        for i, img_url in enumerate(img_urls[:40]): # Increased limit to 40 for photolists
                            try:
                                res = cloudinary.uploader.upload(
                                    img_url,
                                    folder = f"auto_imports/{folder_name}",
                                    context = {"car_name": car_name, "source": link}
                                )
                                uploaded_urls.append(res['secure_url'])
                            except:
                                pass
                            progress_bar.progress((i + 1) / min(len(img_urls), 40))
                        
                        if uploaded_urls:
                            st.success(f"Uploaded {len(uploaded_urls)} images!")
                            st.image(uploaded_urls[0], width=300)
                            st.text_area("Cloudinary Links (Comma Separated):", value=", ".join(uploaded_urls), key=f"out_{idx}")
                
                st.balloons()
