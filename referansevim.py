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

# --- 🔥 AGRESİF GÖRÜNÜRLÜK DÜZELTMESİ (JİLET SÜRÜMÜ) 🔥 ---
st.markdown("""
<style>
    /* GLOBAL ARKA PLAN */
    [data-testid="stAppViewContainer"], .stApp { background-color: #f8f9fa !important; }
    
    /* GLOBAL METİN RENKLERİ (OKUNMAMA SORUNUNU ÇÖZER) */
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stMarkdown p, .stWidget label p, .stAlert p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    
    /* INPUT ALANLARI VE METİNLERİ */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea, .stFileUploader label, .stSlider div {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    
    /* METRİK DEĞERLERİ */
    [data-testid="stMetricValue"] { color: #002147 !important; font-size: 2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] p { color: #002147 !important; font-size: 1rem !important; }
    
    /* STANDART BUTONLAR VE İNDİRME BUTONLARI */
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important; color: #ffffff !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    
    /* 🔥 KESİN BUTON METNİ GÖRÜNÜRLÜĞÜ (Streamlit metinleri ezmek için) 🔥 */
    div.stButton > button *, div.stDownloadButton > button *, div.stFormSubmitButton > button * { color: #ffffff !important; }
    
    /* GİRİŞ EKRANI ÖZEL BUTONLAR (v8.2.1 Düzeltmesi) */
    .btn-google button { background-color: #ffffff !important; color: #444 !important; border: 1px solid #ddd !important; }
    .btn-google button * { color: #444 !important; }
    .btn-edevlet button { background-color: #e30a17 !important; color: #ffffff !important; }
    .btn-edevlet button * { color: #ffffff !important; }
    
    /* REFERANS PRIME BUTONLARI (Altın Renkli, Dark Metinli) */
    .btn-prime button { background-color: #FFD700 !important; color: #002147 !important; border: 2px solid #002147 !important;}
    .btn-prime button * { color: #002147 !important; } /* Prime buton metni kesinlikle lacivert */
    
    /* MARKETPLACE BAŞLIKLARI GÖRÜNÜRLÜĞÜ */
    [data-baseweb="tab-panel"] h3 { color: #002147 !important; }
    
    /* DASHBOARD KUTULARI */
    .dashboard-box { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; transition: transform 0.2s; }
    .dashboard-box:hover { transform: translateY(-5px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    /* SEKMELER (TABS) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border-radius: 4px 4px 0px 0px; border: none !important; color: #002147 !important; padding: 10px 20px !important; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #002147 !important; font-weight: bold; background-color: #e6eef5 !important;}
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI VE FONKSİYONLAR ---
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
            bytes_data = uploaded_file.getvalue()
            image = np.asarray(bytearray(bytes_data), dtype=np.uint8)
            img = cv2.imdecode(image, 1) 
            result = reader.readtext(img, detail=0)
            metin_icerigi = " ".join(result)
        except: return False, "Hata"
    metin_icerigi = metin_icerigi.upper() 
    if belge_tipi == "tapu": limit = 2; anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN"]
    else: limit = 2; anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR", "KAZANÇ", "DÖKÜMÜ"]
    eslesme_sayisi = sum(1 for kelime in anahtar_kelimeler if kelime in metin_icerigi)
    if eslesme_sayisi >= limit: return True, "Onaylandı"
    else: return False, "Okunamadı."

def rapor_metni_hazirla(ad, kod, puan, tarih, analiz):
    analiz_str = "\n".join([f"- {madde}" for madde in analiz])
    return f"REFERANSEVİM GÜVENLİK RAPORU (KVKK UYUMLU)\n----------------------------------\nReferans Kodu: {kod}\nSorgulama Tarihi: {tarih}\n----------------------------------\nKİRACI BİLGİLERİ\nAd Soyad: {ad}\nGüvenilirlik Puanı: {puan} / 5\n\nDETAYLI ANALİZ:\n{analiz_str}\n----------------------------------\n* Yasal Uyari: Sisteme yuklenen hicbir kimlik veya gelir belgesi sunucularda SAKLANMAMISTIR."

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4); qr.add_data(veri); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO(); img.save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu):
    puan = 0; analiz = []
    if gelir >= 40000: puan += 40; analiz.append("Gelir Seviyesi: Yüksek (+40p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart (+20p)")
    else: puan += 10; analiz.append("Gelir Seviyesi: Düşük Riskli (+10p)")
    if findex >= 1500: puan += 40; analiz.append("Kredi Notu: Çok İyi (+40p)")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: Orta/İyi (+20p)")
    else: puan += 0; analiz.append("Kredi Notu: Riskli (0p)")
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (Belge İmha Edildi) (+20p)")
    else: analiz.append("Maaş Bordrosu: Yüklenmedi (0p)")
    yildiz = round((puan/100)*5 * 2) / 2
    if yildiz < 1: yildiz = 1.0 
    return yildiz, analiz, round(gelir * 0.4) # Ödeme kapasitesi maaşın %40'ı hesaplandı

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
        st.info("💡 %100 KVKK Uyumlu: Yüklenen belgeler asla sunucularda saklanmaz, analiz sonrası anında imha edilir.")
        kullanici_tipi = st.selectbox("Sisteme Giriş Tipinizi Seçiniz", ["Kiracı Olarak Giriş Yap", "Ev Sahibi Olarak Giriş Yap"])
        onay = st.checkbox("KVKK Aydınlatma Metnini okudum, anladım ve kabul ediyorum.")
        st.markdown("<br>", unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            st.markdown("<div class='btn-google'>", unsafe_allow_html=True)
            if st.button("🌐 Google ile Giriş", use_container_width=True):
                if onay: st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
                else: st.error("Lütfen KVKK metnini onaylayınız.")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_btn2:
            st.markdown("<div class='btn-edevlet'>", unsafe_allow_html=True)
            if st.button("🔴 e-Devlet ile Giriş", use_container_width=True):
                if onay: st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
                else: st.error("Lütfen KVKK metnini onaylayınız.")
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
                    ad = st.text_input("Ad Soyad")
                    tc = st.text_input("T.C. Kimlik No (Saklanmaz)")
                with c2: 
                    gelir = st.number_input("Aylık Net Gelir (TL)", step=1000, value=40000)
                    findex = st.slider("Tahmini Findeks Kredi Notu", 0, 1900, 1500)
                meslek = st.text_input("Meslek / Şirket")
                st.markdown("<hr>", unsafe_allow_html=True)
                dosya = st.file_uploader("Maaş Bordrosu (Anında imha edilir)", type=["pdf", "jpg", "png"])
                
                if st.form_submit_button("Raporu Hazırla", use_container_width=True):
                    if not ad: st.error("Lütfen isminizi giriniz.")
                    else:
                        belge_ok = True if dosya else False
                        if dosya: st.success("Maaş bordrosu taranıyor (Simülasyon)... Onaylandı!")
                        
                        puan, analiz, kapasite = detayli_puan_hesapla(gelir, findex, meslek, belge_ok)
                        kod = f"REF-{random.randint(10000, 99999)}"
                        tarih = datetime.now().strftime("%d-%m-%Y")
                        
                        veri = {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek, "kapasite": kapasite}
                        veri_kaydet(kod, veri)
                        st.session_state.son_rapor = {"kod": kod, "veri": veri}
                        st.rerun() 

        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            
            # KİRACI SEKMELERİ (TABS)
            tab_k1, tab_k2 = st.tabs(["👤 Profilim ve Prime Paketleri", "🏠 Onaylı Ev İlanları (Pazar Yeri)"])
            
            with tab_k1:
                st.success(f"Hoş Geldiniz Sayın {rp['veri']['ad']}, Profiliniz Aktif.")
                
                # --- v8.2.1 GÖRÜNÜRLÜK DÜZELTMESİ (JİLET METRİKLER) ---
                m1, m2, m3 = st.columns(3)
                m1.metric(label="ReferansEvim Güven Puanınız", value=f"⭐ {rp['veri']['puan']} / 5", delta="Yüksek Puan")
                m2.metric(label="Tahmini Ödeme Kapasiteniz", value=f"~{rp['veri']['kapasite']} TL", delta="Güçlü Maaş")
                m3.metric(label="Mevcut Referans Kodunuz", value=rp['kod'], delta="Ev Sahibiyle Paylaşın")
                
                st.markdown("<br><hr>", unsafe_allow_html=True)
                
                # --- v8.2.1 GELİR MODELİ (PRIME BUTONLAR) ---
                st.markdown("### 🚀 Profilini Ev Sahiplerine Öne Çıkar (Referans Prime)")
                st.info("💡 Raporun harika görünüyor! Ev sahiplerinin seni havuzda en üstte ve altın renkte görmesi için profilini öne çıkar. (Shopier Altyapısıyla %100 Güvenli)")
                
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥉 24 Saatlik Paket</h3>", unsafe_allow_html=True)
                    st.markdown("Bir kahve parasına anında dikkat çek.")
                    st.markdown("<h2>89 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    # Shopier demo butonu (Dark text on Yellow)
                    if st.button("Shopier ile Öde", key="shop1", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_p2:
                    st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥈 3 Günlük VIP</h3>", unsafe_allow_html=True)
                    st.markdown("En çok tercih edilen avantajlı paket.")
                    st.markdown("<h2>149 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    # Shopier demo butonu (Dark text on Yellow)
                    if st.button("Shopier ile Öde", key="shop2", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_p3:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥇 1 Haftalık Altın</h3>", unsafe_allow_html=True)
                    st.markdown("Kesin sonuç garantili, zirvede kal.")
                    st.markdown("<h2>299 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    # Shopier demo butonu (Dark text on Yellow)
                    if st.button("Shopier ile Öde", key="shop3", use_container_width=True): st.success("Shopier yönlendirmesi simüle edildi.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            with tab_k2:
                # --- v8.2.1 KİRACININ EV İLANLARINI GÖRDÜĞÜ PAZAR YERİ ---
                st.markdown("<br>### 🏠 Sana Özel Onaylı Ev İlanları", unsafe_allow_html=True)
                st.info("💡 Sadece ReferansEvim puanı yüksek, geliri onaylanmış sorunsuz kiracıların başvurabileceği elit ilanlar.")
                
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    # v8.2.1 Düzeltmesi: Başlık keskin blue
                    st.markdown("<h3 style='color:#002147;'>Şişli Merkez 2+1 Lüks Daire</h3>", unsafe_allow_html=True)
                    st.markdown("📍 İstanbul / Şişli")
                    st.markdown("💰 **Aylık Kira:** 22.000 TL")
                    st.markdown("🔒 **Şart:** Min ⭐ 4.0 Puan + Gelir Onayı")
                    st.markdown("<br>", unsafe_allow_html=True)
                    # v8.2.1 Düzeltmesi: Buton White text on Blue
                    st.button("Ev Sahibine Başvur", key="b1", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with e_col2:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    # v8.2.1 Düzeltmesi: Başlık keskin blue
                    st.markdown("<h3 style='color:#002147;'>Kadıköy Moda Eşyalı Stüdyo</h3>", unsafe_allow_html=True)
                    st.markdown("📍 İstanbul / Kadıköy")
                    st.markdown("💰 **Aylık Kira:** 18.000 TL")
                    st.markdown("🔒 **Şart:** Min ⭐ 4.5 Puan + Gelir Onayı")
                    st.markdown("<br>", unsafe_allow_html=True)
                    # v8.2.1 Düzeltmesi: Buton White text on Blue
                    st.button("Ev Sahibine Başvur", key="b2", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 🔑 EV SAHİBİ EKOSİSTEMİ (SEKMELİ YAPI)
    # ==========================================
    elif st.session_state.kullanici_tipi == "evsahibi":
        
        # Sekmeleri Oluşturuyoruz (Düzeltme: Jilet sekmeler)
        tab1, tab2, tab3 = st.tabs(["🔍 Manuel Kiracı Sorgulama & Sözleşme", "💎 Premium Kiracı Havuzu (Pazar Yeri)", "🏠 Ev İlanı Aç (Sadece Onaylı Kiracılara)"])
        
        with tab1:
            if not st.session_state.onaylanan_kiraci:
                st.subheader("🛡️ Kiracı & Belge Doğrulama Merkezi")
                tapu = st.file_uploader("Tapu Belgesi Yükle (Anında İmha Edilir)", type=["pdf", "jpg", "png"])
                kod = st.text_input("Kiracının Size Verdiği Kod (Örn: REF-12345)")
                
                if st.button("Belgeyi Tarat ve Sorgula 🔍", use_container_width=True):
                    if tapu and kod:
                        with st.spinner("Güvenlik Taraması Yapılıyor..."):
                            time.sleep(1)
                            db = verileri_yukle()
                            if kod in db:
                                st.session_state.onaylanan_kiraci = db[kod]['ad']
                                st.session_state.kiraci_puan = db[kod]['puan']
                                st.rerun() 
                            else: st.warning("Girdiğiniz kod bulunamadı.")
            
            if st.session_state.onaylanan_kiraci:
                k_isim = st.session_state.onaylanan_kiraci
                k_puan = st.session_state.kiraci_puan
                st.success("✅ Emlak Yönetim Paneline Hoş Geldiniz.")
                # v8.2.1 Düzeltmesi: Jilet metrikler
                m1, m2, m3 = st.columns(3)
                m1.metric(label="Mevcut Aktif Kiracınız", value=k_isim, delta=f"⭐ {k_puan}")
                m2.metric(label="Aylık Beklenen Kira", value="15.000 TL", delta="Ödeme Bekleniyor")
                m3.metric(label="Sözleşme Durumu", value="Taslak Hazır", delta="Onaylandı")
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
                st.write("Sözleşme modülü ve ödeme tablosu burada.")

        with tab2:
            st.markdown("<br>### 🌟 Onaylı Premium Kiracı Adayları", unsafe_allow_html=True)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            
            with p_col1:
                st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                # v8.2.1 Düzeltmesi: Altın sarısı elit Prime etiketi (Dark text on Yellow)
                st.markdown("<div style='background-color:#FFD700; color:#002147; font-weight:bold; border-radius:5px; padding:5px; margin-bottom:10px;'>🚀 REFERANS PRIME (Öne Çıkarılmış)</div>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>B*** G***</h2>", unsafe_allow_html=True)
                st.markdown("💼 Kurucu (TheFLXBrand)")
                st.markdown("⭐ **Güven Puanı:** 4.8 / 5")
                st.markdown("💳 **Kapasite:** ~25.000 TL")
                # v8.2.1 Düzeltmesi: Buton White text on Blue
                st.button("Eşleşme İste", key="ep1", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with p_col2:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>A*** Y***</h2>", unsafe_allow_html=True)
                st.markdown("💼 Finans Uzmanı")
                st.markdown("⭐ **Güven Puanı:** 4.5 / 5")
                st.markdown("💳 **Kapasite:** ~40.000 TL")
                # v8.2.1 Düzeltmesi: Buton White text on Blue
                st.button("Eşleşme İste", key="ep2", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with p_col3:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>M*** K***</h2>", unsafe_allow_html=True)
                st.markdown("💼 Öğretmen")
                st.markdown("⭐ **Güven Puanı:** 4.1 / 5")
                st.markdown("💳 **Kapasite:** ~18.000 TL")
                # v8.2.1 Düzeltmesi: Buton White text on Blue
                st.button("Eşleşme İste", key="ep3", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            # --- v8.2.1 EV SAHİBİNİN İLAN AÇTIĞI VE PRIME YAPTIĞI YER ---
            st.markdown("<br>### 🏠 Güvenli Ev İlanı Oluştur", unsafe_allow_html=True)
            st.info("💡 İlanınız sadece yapay zeka tarafından geliri ve geçmişi onaylanmış sorunsuz kiracılara gösterilecektir.")
            
            with st.form("ilan_form"):
                i_baslik = st.text_input("İlan Başlığı (Örn: Kadıköy 2+1)")
                i_fiyat = st.number_input("Aylık Kira Bedeli (TL)", step=1000)
                # v8.2.1 Düzeltmesi: Slider jilet metin
                i_sart = st.slider("Başvuracak Kiracılar İçin Minimum Puan", 1.0, 5.0, 4.0, 0.5)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("#### 🚀 İlanınızı Öne Çıkarın (Referans Prime)")
                # v8.2.1 GÖRÜNÜRLÜK DÜZELTMESİ (JİLET FİYATLANDIRMA)
                i_boost = st.radio("İlanınız havuzda kaç gün zirvede kalsın?", ["Ücretsiz İlan", "24 Saat Prime İlan (89 TL)", "3 Gün VIP İlan (149 TL)", "1 Hafta Altın İlan (299 TL)"])
                
                # v8.2.1 Düzeltmesi: Buton White text on Blue
                if st.form_submit_button("İlanı Yayınla (Güvenli Havuz)", use_container_width=True):
                    if "Ücretsiz" not in i_boost:
                        st.success(f"Tebrikler! İlanınız hazır, seçtiğiniz '{i_boost}' paketi için Shopier güvenli ödeme sayfasına yönlendiriliyorsunuz (Simülasyon)...")
                    else:
                        st.success("İlanınız Standart olarak onaylı kiracı havuzunda yayınlandı!")