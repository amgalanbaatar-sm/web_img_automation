import streamlit as st
import cloudinary
import cloudinary.uploader
import requests
from bs4 import BeautifulSoup
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Car Image Porter", page_icon="📸")

# --- UI STYLING ---
st.markdown("""
    <style>
    .stTextArea textarea { font-family: monospace; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CREDENTIALS ---
st.sidebar.title("☁️ Cloudinary Settings")
st.sidebar.markdown("Get these from your [Cloudinary Dashboard](https://cloudinary.com/console)")
cl_name = st.sidebar.text_input("Cloud Name")
cl_key = st.sidebar.text_input("API Key")
cl_secret = st.sidebar.text_input("API Secret", type="password")

# --- HELPER FUNCTIONS ---
def init_cloudinary():
    if cl_name and cl_key and cl_secret:
        cloudinary.config(cloud_name=cl_name, api_key=cl_key, api_secret=cl_secret)
        return True
    return False

def get_car_metadata(soup, url):
    """Attempt to scrape car name/details for Cloudinary metadata"""
    meta = {"title": "Unknown Car", "tags": ["imported"]}
    
    try:
        if "beforward.jp" in url:
            title = soup.find('h1').text.strip() if soup.find('h1') else "Beforward Car"
            meta["title"] = title
            meta["tags"].append("beforward")
        elif "sbtjapan.com" in url:
            title = soup.find('h1').text.strip() if soup.find('h1') else "SBT Car"
            meta["title"] = title
            meta["tags"].append("sbt")
    except:
        pass
    return meta

def extract_image_urls(url):
    """Scraper logic for dealer sites"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    images = []
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        car_meta = get_car_metadata(soup, url)

        if "beforward.jp" in url:
            # Look for catalog images and convert thumbnails to large versions
            for img in soup.find_all('img', src=re.compile(r'catalog')):
                src = img.get('src')
                # Replace thumbnail segment '/t/' with large segment '/l/'
                large_url = src.replace('/t/', '/l/').split('?')[0]
                if not large_url.startswith('http'): large_url = "https:" + large_url
                if large_url not in images: images.append(large_url)

        elif "sbtjapan.com" in url:
            for img in soup.find_all('img', src=re.compile(r'images.sbtjapan.com')):
                src = img.get('data-src') or img.get('src')
                if src:
                    full_src = src.split('?')[0]
                    if full_src not in images: images.append(full_src)
        
        else:
            # Fallback for generic sites
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and src.startswith('http'): images.append(src)
                
        return images, car_meta
    except Exception as e:
        st.error(f"Error accessing link: {e}")
        return [], {}

# --- MAIN APP UI ---
st.title("🚗 Car Image Auto-Porter")
st.write("Extract high-res images from dealer links and save them to Cloudinary.")

if not init_cloudinary():
    st.info("👈 Please enter your Cloudinary API credentials in the sidebar to begin.")
    st.stop()

# Input area
raw_input = st.text_area(
    "Enter Links (Single, Multiple lines, or Comma-separated):", 
    height=150, 
    placeholder="https://www.beforward.jp/toyota/sai/...\nhttps://www.sbtjapan.com/..."
)

if st.button("🚀 Process & Upload"):
    # Clean links (handle commas and newlines)
    links = re.split(r'[,\n]', raw_input)
    links = [l.strip() for l in links if l.strip()]

    if not links:
        st.error("No valid links detected.")
    else:
        for idx, link in enumerate(links):
            with st.expander(f"Processing Link {idx+1}: {link[:50]}...", expanded=True):
                st.write("🔍 Extracting images...")
                img_urls, meta = extract_image_urls(link)
                
                if not img_urls:
                    st.warning("Could not find any images for this link.")
                    continue
                
                st.write(f"📸 Found **{len(img_urls)}** images. Uploading to Cloudinary...")
                
                progress_bar = st.progress(0)
                uploaded_urls = []
                
                # Cloudinary Upload
                folder_name = re.sub(r'[^a-zA-Z0-9]', '_', meta['title'])[:50]
                
                for i, img_url in enumerate(img_urls[:30]): # Limit to 30 images for safety
                    try:
                        result = cloudinary.uploader.upload(
                            img_url,
                            folder=f"car_inventory/{folder_name}",
                            tags=meta["tags"],
                            context={"source_url": link, "car_name": meta["title"]}
                        )
                        uploaded_urls.append(result['secure_url'])
                    except:
                        pass
                    progress_bar.progress((i + 1) / min(len(img_urls), 30))
                
                if uploaded_urls:
                    st.success(f"Successfully uploaded {len(uploaded_urls)} images!")
                    st.image(uploaded_urls[0], width=300, caption="Preview of Main Image")
                    st.code(", ".join(uploaded_urls), language="text")
                else:
                    st.error("Upload failed for all images.")

st.balloons()
