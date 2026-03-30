import streamlit as st
import cloudinary
import cloudinary.uploader
import requests
from bs4 import BeautifulSoup
import re
import time

# --- 1. PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Car Porter Access")
        st.text_input("Enter Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Car Porter Access")
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

# --- 3. ADVANCED SCRAPER LOGIC ---
def extract_car_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    
    images = []
    car_name = "Imported_Car"
    
    # Extract ID for SBT
    sbt_id_match = re.search(r'([A-Z]{2}\d{4,})', url)
    car_id = sbt_id_match.group(1) if sbt_id_match else None

    try:
        # Try to fetch the page
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        if soup.find('h1'):
            car_name = soup.find('h1').text.strip()
        elif car_id:
            car_name = f"SBT_{car_id}"

        # --- SBT SPECIFIC LOGIC ---
        if "sbtjapan.com" in url:
            # Method A: Scrape standard links
            found_images = re.findall(r'https://images\.sbtjapan\.com/images/car/[^"\'>\s]+\.jpg', res.text)
            for img in found_images:
                full_img = img.replace('_t.jpg', '.jpg').replace('_m.jpg', '.jpg')
                if full_img not in images: images.append(full_img)
            
            # Method B: Direct Probe (If A finds nothing)
            if len(images) < 5 and car_id:
                st.info(f"Page content restricted. Probing SBT image servers for ID: {car_id}...")
                for i in range(1, 31): # Try first 30 images
                    test_url = f"https://images.sbtjapan.com/images/car/{car_id}/{i}.jpg"
                    # We check if image exists with a HEAD request (fast)
                    if requests.head(test_url, headers=headers).status_code == 200:
                        images.append(test_url)
                    else:
                        break # Stop when no more images are found

        # --- BEFORWARD SPECIFIC LOGIC ---
        elif "beforward.jp" in url:
            for img in soup.find_all('img', src=re.compile(r'catalog')):
                src = img.get('src')
                large_url = src.replace('/t/', '/l/').split('?')[0]
                if not large_url.startswith('http'): large_url = "https:" + large_url
                if large_url not in images: images.append(large_url)

        # --- FALLBACK ---
        else:
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and src.startswith('http'): images.append(src)

    except Exception as e:
        st.error(f"Connection error: {e}")
        
    return list(dict.fromkeys(images)), car_name # Deduplicate while keeping order

# --- 4. MAIN APP UI ---
st.set_page_config(page_title="Car Image Porter", page_icon="🚗")

if check_password():
    st.title("🚗 Car Image Auto-Porter")
    st.write("Bypassing dealer blocks for **SBTJapan** and **BeForward**.")

    if init_cloudinary():
        raw_input = st.text_area("Paste links (Comma or New Line separated):", height=150)

        if st.button("🚀 Process & Upload"):
            links = [l.strip() for l in re.split(r'[,\n]', raw_input) if l.strip()]

            if not links:
                st.error("No links provided.")
            else:
                for idx, link in enumerate(links):
                    with st.expander(f"Car {idx+1}: {link[:40]}...", expanded=True):
                        img_urls, car_name = extract_car_data(link)
                        
                        if not img_urls:
                            st.error("❌ Still no images found. The site is heavily blocking this server.")
                            continue
                        
                        st.write(f"✅ Found **{len(img_urls)}** high-res images.")
                        
                        progress_bar = st.progress(0)
                        uploaded_urls = []
                        folder_name = re.sub(r'[^a-zA-Z0-9]', '_', car_name)[:50]

                        for i, img_url in enumerate(img_urls):
                            try:
                                res = cloudinary.uploader.upload(
                                    img_url,
                                    folder = f"auto_imports/{folder_name}",
                                    context = {"car_name": car_name, "source": link}
                                )
                                uploaded_urls.append(res['secure_url'])
                            except:
                                pass
                            progress_bar.progress((i + 1) / len(img_urls))
                        
                        if uploaded_urls:
                            st.success(f"Uploaded {len(uploaded_urls)} images to Cloudinary!")
                            st.text_area("Copy Links:", value=", ".join(uploaded_urls), key=f"out_{idx}")
                            st.image(uploaded_urls[0], width=200)
                st.balloons()
