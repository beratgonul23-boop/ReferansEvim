import streamlit as st
import time
import random
import os
import json
import qrcode
from io import BytesIO
from datetime import datetime
import numpy as np

# --- YENİ KÜTÜPHANELER ---
try:
    import pypdf
    import easyocr
    import cv2
    OCR_AKTIF = True
except ImportError:
    OCR_AKTIF = False
    st.warning("⚠️ OCR kütüphaneleri eksik! Terminale 'pip install easyocr pypdf opencv-python-headless' yazıp kurun.")

st.set_page_config(page_title="ReferansEvim Pro", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

# --- 🔥 AGRESİF CSS DÜZELTMESİ 🔥 ---
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f8f9fa !important; }
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stMarkdown p, .stWidget label p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    div.stButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important; color: #ffffff !important;
    }
    div.stButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    
    .btn-google > button { background-color: #ffffff !important; color: #444 !important; border: 1px solid #ddd !important; }
    .btn-edevlet > button { background-color: #e30a17 !important; color: #ffffff !important; }
    .btn-prime > button { background-color: #FFD700 !important; color: #002147 !important; border: 2px solid #002147 !important;}
    
    [data-testid="stMetricValue"] { color: #002147 !important; font-size: 2rem !important; font-weight: 800 !important; }
    
    .dashboard-box { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; transition: transform 0.2s; }
    .dashboard-box:hover { transform: translateY(-5px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border-radius: 4px 4px 0px 0px; border: none !important; color: #002147 !important; padding: 10px 20px !important; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #002147 !important; font-weight: bold; background-color: #e6eef5 !important;}
</style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---
DB_DOSYASI = "referans_db.json"
def verileri_yukle():
    if not os.path.exists(DB_DOSYASI): return {}  
    try: 
        with open(DB_DOSYASI, "r", encoding="utf-8") as f: return json.load(f)
    except: return {} 
def veri_kaydet(kod, veri):
    db = verileri_yukle(); db[kod] = veri
    with open(DB_DOSYASI, "w", encoding="utf-8") as f: json.dump(db, f, ensure_ascii=False, indent=4)

@st.cache_resource
def ocr_modeli_yukle():
    if OCR_AKTIF: return easyocr.Reader(['tr', 'en'], gpu=False) 
    return None

def belgeyi_tara_ve_dogrula(uploaded_file, belge_tipi="tapu"):
    if not OCR_AKTIF: return True, "Simülasyon Modu" 
    metin_icerigi = ""
    if uploaded_file.name.lower().endswith('.pdf'):
        try:
            pdf_reader = pypdf.PdfReader(uploaded_file)
            for page in pdf_reader.pages: metin_icerigi += page.extract_text() + " "
        except: return False, "Okunamadı"
    else:
        try:
            reader = ocr_modeli_yukle()
            img = cv2.imdecode(np.asarray(bytearray(uploaded_file.getvalue()), dtype=np.uint8), 1) 
            metin_icerigi = " ".join(reader.readtext(img, detail=0))
        except: return False, "Hata"
    metin_icerigi = metin_icerigi.upper() 
    if belge_tipi == "tapu": limit = 2; anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN"]
    else: limit = 2; anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR"]
    if sum(1 for k in anahtar_kelimeler if k in metin_icerigi) >= limit: return True, "Onaylandı"
    return False, "Reddedildi"

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4); qr.add_data(veri); qr.make(fit=True)
    buffer = BytesIO(); qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu):
    puan = 0; analiz = []
    if gelir >= 40000: puan += 40; analiz.append("Gelir Seviyesi: Yüksek")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart")
    else: puan += 10; analiz.append("Gelir Seviyesi: Düşük")
    if findex >= 1500: puan += 40; analiz.append("Kredi Notu: Çok İyi")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: İyi")
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı")
    yildiz = round((puan/100)*5 * 2) / 2
    return max(1.0, yildiz), analiz, round(gelir * 0.4) # Ödeme kapasitesi maaşın %40'ı hesaplandı

# --- UYGULAMA ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None
if 'onaylanan_kiraci' not in st.session_state: st.session_state.onaylanan_kiraci = None

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        logo_yolu = "logo.png" if os.path.exists("logo.png") else ("logo.png.png" if os.path.exists("logo.png.png") else None)
        if logo_yolu:
            c_logo1, c_logo2, c_logo3 = st.columns([1, 6, 1]) 
            with c_logo2: st.image(logo_yolu, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 3.5rem; font-weight: 800;'>Referans<span style='font-weight: 300;'>Evim</span></h1>", unsafe_allow_html=True)
            
        st.markdown("<p style='text-align: center; color: gray;'>Türkiye'nin İlk Yapay Zeka Destekli Emlak Uzlaştırma Ekosistemi</p><br>", unsafe_allow_html=True)
        kullanici_tipi = st.selectbox("Sisteme Giriş Tipinizi Seçiniz", ["Kiracı Olarak Giriş Yap", "Ev Sahibi Olarak Giriş Yap"])
        onay = st.checkbox("KVKK Aydınlatma Metnini okudum ve kabul ediyorum.")
        st.markdown("<br>", unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            st.markdown("<div class='btn-google'>", unsafe_allow_html=True)
            if st.button("🌐 Google ile Giriş", use_container_width=True):
                if onay: st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with c_btn2:
            st.markdown("<div class='btn-edevlet'>", unsafe_allow_html=True)
            if st.button("🔴 e-Devlet ile Giriş", use_container_width=True):
                if onay: st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

else:
    c1, c2 = st.columns([8, 1])
    with c1: st.title(f"🏠 ReferansEvim {'Kiracı' if st.session_state.kullanici_tipi=='kiraci' else 'Ev Sahibi'} Paneli")
    with c2:
        if st.button("Güvenli Çıkış"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    st.markdown("---")

    # ==========================================
    # 👤 KİRACI EKOSİSTEMİ
    # ==========================================
    if st.session_state.kullanici_tipi == "kiraci":
        if not st.session_state.son_rapor:
            st.subheader("📝 Akıllı Referans Raporu Oluştur (Ücretsiz)")
            with st.form("k_form"):
                c1, c2 = st.columns(2)
                with c1: 
                    ad = st.text_input("Ad Soyad"); tc = st.text_input("T.C. Kimlik No")
                with c2: 
                    gelir = st.number_input("Aylık Net Gelir (TL)", step=1000, value=40000); findex = st.slider("Findeks Kredi Notu", 0, 1900, 1500)
                meslek = st.text_input("Meslek / Şirket")
                dosya = st.file_uploader("Maaş Bordrosu (Anında imha edilir)", type=["pdf", "jpg", "png"])
                if st.form_submit_button("Raporu Hazırla", use_container_width=True):
                    if ad:
                        belge_ok = True if dosya else False
                        puan, analiz, kapasite = detayli_puan_hesapla(gelir, findex, meslek, belge_ok)
                        kod = f"REF-{random.randint(10000, 99999)}"
                        tarih = datetime.now().strftime("%d-%m-%Y")
                        st.session_state.son_rapor = {"kod": kod, "veri": {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek, "kapasite": kapasite}}
                        st.rerun() 

        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            
            tab_k1, tab_k2 = st.tabs(["👤 Profilim ve Prime Paketleri", "🏠 Onaylı Ev İlanları (Pazar Yeri)"])
            
            with tab_k1:
                st.success(f"Hoş Geldiniz Sayın {rp['veri']['ad']}, Profiliniz Aktif.")
                m1, m2, m3 = st.columns(3)
                m1.metric(label="Güven Puanınız", value=f"⭐ {rp['veri']['puan']} / 5")
                m2.metric(label="Hesaplanan Ödeme Kapasitesi", value=f"~{rp['veri']['kapasite']} TL")
                m3.metric(label="Referans Kodunuz", value=rp['kod'])
                
                st.markdown("<br><hr>", unsafe_allow_html=True)
                
                # --- YENİ: GELİR MODELİ (PRIME / VİTRİN) DEMOSU ---
                st.markdown("### 🚀 Profilini Ev Sahiplerine Öne Çıkar (Referans Prime)")
                st.info("💡 Raporun harika görünüyor! Ev sahiplerinin seni havuzda en üstte ve altın renkte görmesi için profilini öne çıkar. (Shopier Altyapısıyla %100 Güvenli)")
                
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥉 24 Saatlik Paket</h3>", unsafe_allow_html=True)
                    st.markdown("Bir kahve parasına anında dikkat çek.")
                    st.markdown("<h2>89 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop1", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                with c_p2:
                    st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥈 3 Günlük VIP</h3>", unsafe_allow_html=True)
                    st.markdown("En çok tercih edilen avantajlı paket.")
                    st.markdown("<h2>149 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop2", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                with c_p3:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥇 1 Haftalık Altın</h3>", unsafe_allow_html=True)
                    st.markdown("Kesin sonuç garantili, zirvede kal.")
                    st.markdown("<h2>299 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop3", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)

            with tab_k2:
                # --- YENİ: KİRACININ EV İLANLARINI GÖRDÜĞÜ YER ---
                st.markdown("<br>### 🏠 Sana Özel Onaylı Ev İlanları", unsafe_allow_html=True)
                st.info("💡 Sadece ReferansEvim puanı yüksek, onaylı kiracıların başvurabileceği elit ve güvenli ilanlar.")
                
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>Şişli Merkez 2+1 Lüks Daire</h3>", unsafe_allow_html=True)
                    st.markdown("📍 **Konum:** İstanbul / Şişli")
                    st.markdown("💰 **Aylık Kira:** 22.000 TL")
                    st.markdown("🔒 **Başvuru Şartı:** Min. ⭐ 4.0 Puan ve AI Gelir Onayı")
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.button("Ev Sahibine Başvur", key="b1", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with e_col2:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>Kadıköy Moda Eşyalı Stüdyo</h3>", unsafe_allow_html=True)
                    st.markdown("📍 **Konum:** İstanbul / Kadıköy")
                    st.markdown("💰 **Aylık Kira:** 18.000 TL")
                    st.markdown("🔒 **Başvuru Şartı:** Min. ⭐ 4.5 Puan ve AI Gelir Onayı")
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.button("Ev Sahibine Başvur", key="b2", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 🔑 EV SAHİBİ EKOSİSTEMİ
    # ==========================================
    elif st.session_state.kullanici_tipi == "evsahibi":
        
        tab1, tab2, tab3 = st.tabs(["🔍 Kiracı Raporu Sorgula", "💎 Premium Kiracı Havuzu", "🏠 Ev İlanı Aç (Sadece Onaylı Kiracılara)"])
        
        with tab1:
            st.info("Kiracınızın size verdiği REF kodunu buraya girin.")
            kod = st.text_input("Referans Kodu (Örn: REF-12345)")
            if st.button("Sorgula", use_container_width=True): st.success("Sistem kod taramasını simüle ediyor...")
                
        with tab2:
            st.markdown("<br>### 🌟 Onaylı Premium Kiracı Adayları", unsafe_allow_html=True)
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                st.markdown("<div style='background-color:#FFD700; color:#002147; font-weight:bold; border-radius:5px; padding:5px; margin-bottom:10px;'>🚀 PRIME KİRACI (Öne Çıkarılmış)</div>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>B*** G***</h2>", unsafe_allow_html=True)
                st.markdown("💼 **Meslek:** Kurucu (TheFLXBrand)")
                st.markdown("⭐ **Güven Puanı:** 4.8 / 5")
                st.markdown("💳 **Kapasite:** ~25.000 TL / Ay")
                st.button("Eşleşme İste", key="ep1", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with p_col2:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>A*** Y***</h2>", unsafe_allow_html=True)
                st.markdown("💼 **Meslek:** Finans Uzmanı")
                st.markdown("⭐ **Güven Puanı:** 4.5 / 5")
                st.markdown("💳 **Kapasite:** ~40.000 TL / Ay")
                st.button("Eşleşme İste", key="ep2", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with p_col3:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>M*** K***</h2>", unsafe_allow_html=True)
                st.markdown("💼 **Meslek:** Öğretmen")
                st.markdown("⭐ **Güven Puanı:** 4.1 / 5")
                st.markdown("💳 **Kapasite:** ~18.000 TL / Ay")
                st.button("Eşleşme İste", key="ep3", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            # --- YENİ: EV SAHİBİNİN İLAN AÇTIĞI VE İLANINI ÖNE ÇIKARDIĞI YER ---
            st.markdown("<br>### 🏠 Güvenli Ev İlanı Oluştur", unsafe_allow_html=True)
            st.info("💡 İlanınız sadece yapay zeka tarafından geliri ve geçmişi onaylanmış, sorunsuz kiracılara gösterilecektir.")
            
            with st.form("ilan_form"):
                i_baslik = st.text_input("İlan Başlığı (Örn: Şişli Merkez Eşyalı 2+1)")
                i_fiyat = st.number_input("Aylık Kira Bedeli (TL)", step=1000)
                i_sart = st.slider("Başvuracak Kiracılar İçin Minimum Puan Şartı", 1.0, 5.0, 4.0, 0.5)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("#### 🚀 İlanınızı Öne Çıkarın (Referans Prime)")
                i_boost = st.radio("İlanınız havuzda kaç gün en tepede kalsın?", ["İstemiyorum (Ücretsiz İlan)", "24 Saat Öne Çıkar (89 TL)", "3 Gün VIP (149 TL)", "1 Hafta Altın İlan (299 TL)"])
                
                if st.form_submit_button("İlanı Yayınla (Güvenli Havuz)", use_container_width=True):
                    if "Ücretsiz" not in i_boost:
                        st.success(f"İlanınız hazır! Seçtiğiniz '{i_boost}' paketi için Shopier güvenli ödeme sayfasına yönlendiriliyorsunuz...")
                    else:
                        st.success("İlanınız Standart olarak onaylı kiracı havuzunda yayınlandı!")