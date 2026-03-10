import streamlit as st
import time
import random
import os
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
    st.warning("⚠️ OCR (Metin Okuma) eksik! Terminale 'pip install easyocr pypdf opencv-python-headless' yazarsanız gerçek yapay zeka taraması açılır. Şu an Simülasyon Modunda çalışıyor.")

# --- FIREBASE BULUT BAĞLANTISI ---
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # Streamlit'in kasasından şifreleri gizlice al
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = init_firebase()
    FIREBASE_AKTIF = True
except Exception as e:
    FIREBASE_AKTIF = False
    st.error(f"⚠️ Bulut veritabanına bağlanılamadı. Lütfen Streamlit Secrets ayarlarını kontrol edin. Hata: {e}")

st.set_page_config(page_title="ReferansEvim Pro", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

# --- 🔥 AGRESİF GÖRÜNÜRLÜK DÜZELTMESİ 🔥 ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"], .stApp { background-color: #f8f9fa !important; }
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stMarkdown p, .stWidget label p, .stAlert p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea, .stFileUploader label, .stSlider div {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    [data-testid="stMetricValue"] { color: #002147 !important; font-size: 2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] p { color: #002147 !important; font-size: 1rem !important; }
    
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important; color: #ffffff !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    div.stButton > button *, div.stDownloadButton > button *, div.stFormSubmitButton > button * { color: #ffffff !important; }
    
    .btn-google button { background-color: #ffffff !important; color: #444 !important; border: 1px solid #ddd !important; }
    .btn-google button * { color: #444 !important; }
    .btn-edevlet button { background-color: #e30a17 !important; color: #ffffff !important; }
    .btn-edevlet button * { color: #ffffff !important; }
    .btn-prime button { background-color: #FFD700 !important; color: #002147 !important; border: 2px solid #002147 !important;}
    .btn-prime button * { color: #002147 !important; } 
    
    [data-baseweb="tab-panel"] h3 { color: #002147 !important; }
    .dashboard-box { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; transition: transform 0.2s; }
    .dashboard-box:hover { transform: translateY(-5px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border-radius: 4px 4px 0px 0px; border: none !important; color: #002147 !important; padding: 10px 20px !important; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #002147 !important; font-weight: bold; background-color: #e6eef5 !important;}
</style>
""", unsafe_allow_html=True)

# --- BULUT VERİTABANI FONKSİYONLARI ---
def veri_kaydet(kod, veri):
    if FIREBASE_AKTIF:
        db.collection('referanslar').document(kod).set(veri)

def veri_getir(kod):
    if FIREBASE_AKTIF:
        doc = db.collection('referanslar').document(kod).get()
        if doc.exists:
            return doc.to_dict()
    return None

def belgeyi_tara_ve_dogrula(uploaded_file, belge_tipi="tapu"):
    if not OCR_AKTIF: 
        isim = uploaded_file.name.lower()
        if "logo" in isim or "ekran" in isim or "screenshot" in isim or "png.png" in isim:
            return False, "Sistem belgenin bir logo veya ekran görüntüsü olduğunu tespit etti. Lütfen resmi bir belge yükleyin!"
        return True, "Belge formatı uygun bulundu (Simülasyon Modu)"
        
    metin_icerigi = ""
    if uploaded_file.name.lower().endswith('.pdf'):
        try:
            pdf_reader = pypdf.PdfReader(uploaded_file)
            for page in pdf_reader.pages: metin_icerigi += page.extract_text() + " "
        except: return False, "PDF Okunamadı"
    else:
        try:
            reader = easyocr.Reader(['tr', 'en'], gpu=False) 
            bytes_data = uploaded_file.getvalue()
            image = np.asarray(bytearray(bytes_data), dtype=np.uint8)
            img = cv2.imdecode(image, 1) 
            result = reader.readtext(img, detail=0)
            metin_icerigi = " ".join(result)
        except Exception as e: return False, "Resim Hatası"
        
    metin_icerigi = metin_icerigi.upper() 
    if belge_tipi == "tapu": limit = 2; anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN"]
    else: limit = 2; anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR", "KAZANÇ", "DÖKÜMÜ"]
    eslesme_sayisi = sum(1 for kelime in anahtar_kelimeler if kelime in metin_icerigi)
    if eslesme_sayisi >= limit: return True, "Yapay Zeka Onayı Başarılı!"
    else: return False, "Belge içeriği doğrulanamadı."

def resmi_sozlesme_metni_hazirla(kiraci_adi, adres, kira_bedeli, depozito, odeme_gunu):
    tarih = datetime.now().strftime("%d/%m/%Y")
    return f"KİRA SÖZLEŞMESİ TASLAĞI\nTarih: {tarih}\n\nKiracı: {kiraci_adi}\nAdres: {adres}\nAylık Kira: {kira_bedeli} TL\nDepozito: {depozito} TL\nÖdeme Günü: {odeme_gunu}\n\nİşbu sözleşme ReferansEvim Uzlaştırma Platformu aracılığıyla hazırlanmıştır."

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
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (+20p)")
    else: analiz.append("Maaş Bordrosu: Yüklenmedi (0p)")
    yildiz = round((puan/100)*5 * 2) / 2
    if yildiz < 1: yildiz = 1.0 
    return yildiz, analiz

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
            st.subheader("📝 Akıllı Referans Raporu Oluştur")
            with st.form("k_form"):
                c1, c2 = st.columns(2)
                with c1: 
                    ad = st.text_input("Ad Soyad")
                    tc = st.text_input("T.C. Kimlik No (Saklanmaz)")
                    meslek = st.text_input("Meslek / Şirket")
                with c2: 
                    gelir = st.number_input("Aylık Net Gelir (TL)", step=1000, value=40000)
                    kapasite_input = st.number_input("Aylık Ödeyebileceğiniz Maks. Kira Bütçeniz (TL)", step=1000, value=15000)
                    findex = st.slider("Tahmini Findeks Kredi Notu", 0, 1900, 1500)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                dosya = st.file_uploader("Maaş Bordrosu (Anında imha edilir)", type=["pdf", "jpg", "png"])
                
                if st.form_submit_button("Raporu Hazırla ve Buluta Kaydet ☁️", use_container_width=True):
                    if not ad: st.error("Lütfen isminizi giriniz.")
                    else:
                        belge_ok = False
                        if dosya:
                            ok, msg = belgeyi_tara_ve_dogrula(dosya, "maas")
                            if ok: belge_ok = True; st.success(f"Belge Onaylandı: {msg}")
                            else: st.error(f"Reddedildi: {msg}")
                        
                        puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, belge_ok)
                        kod = f"REF-{random.randint(10000, 99999)}"
                        tarih = datetime.now().strftime("%d-%m-%Y")
                        veri = {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek, "kapasite": kapasite_input}
                        
                        # --- BULUTA YAZIYORUZ ---
                        veri_kaydet(kod, veri)
                        
                        st.session_state.son_rapor = {"kod": kod, "veri": veri}
                        st.rerun() 

        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            tab_k1, tab_k2 = st.tabs(["👤 Profilim ve Prime Paketleri", "🏠 Onaylı Ev İlanları (Pazar Yeri)"])
            
            with tab_k1:
                st.success(f"Hoş Geldiniz Sayın {rp['veri']['ad']}, Profiliniz Buluta Kaydedildi ve Aktif.")
                m1, m2, m3 = st.columns(3)
                m1.metric(label="ReferansEvim Güven Puanınız", value=f"⭐ {rp['veri']['puan']} / 5")
                m2.metric(label="Maksimum Kira Bütçeniz", value=f"{rp['veri']['kapasite']} TL")
                m3.metric(label="Mevcut Referans Kodunuz", value=rp['kod'])
                st.markdown("<br><hr>", unsafe_allow_html=True)
                
                st.markdown("### 🚀 Profilini Ev Sahiplerine Öne Çıkar (Referans Prime)")
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥉 24 Saatlik Paket</h3>", unsafe_allow_html=True)
                    st.markdown("<h2>89 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop1", use_container_width=True): st.success("Yönlendirme simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                with c_p2:
                    st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥈 3 Günlük VIP</h3>", unsafe_allow_html=True)
                    st.markdown("<h2>149 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop2", use_container_width=True): st.success("Yönlendirme simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                with c_p3:
                    st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>🥇 1 Haftalık Altın</h3>", unsafe_allow_html=True)
                    st.markdown("<h2>299 TL</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='btn-prime'>", unsafe_allow_html=True)
                    if st.button("Shopier ile Öde", key="shop3", use_container_width=True): st.success("Yönlendirme simüle edildi.")
                    st.markdown("</div></div>", unsafe_allow_html=True)

            with tab_k2:
                st.markdown("<br>### 🏠 Sana Özel Onaylı Ev İlanları", unsafe_allow_html=True)
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>Şişli Merkez 2+1 Lüks Daire</h3>", unsafe_allow_html=True)
                    st.markdown("💰 **Aylık Kira:** 22.000 TL")
                    st.markdown("🔒 **Şart:** Min ⭐ 4.0 Puan")
                    st.button("Ev Sahibine Başvur", key="b1", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with e_col2:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#002147;'>Kadıköy Moda Eşyalı Stüdyo</h3>", unsafe_allow_html=True)
                    st.markdown("💰 **Aylık Kira:** 18.000 TL")
                    st.markdown("🔒 **Şart:** Min ⭐ 4.5 Puan")
                    st.button("Ev Sahibine Başvur", key="b2", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 🔑 EV SAHİBİ EKOSİSTEMİ
    # ==========================================
    elif st.session_state.kullanici_tipi == "evsahibi":
        tab1, tab2, tab3 = st.tabs(["🔍 Buluttan Kiracı Sorgula", "💎 Premium Kiracı Havuzu", "🏠 Ev İlanı Aç"])
        
        with tab1:
            if not st.session_state.onaylanan_kiraci:
                st.subheader("🛡️ Bulut Veritabanı Sorgulama")
                kod = st.text_input("Kiracının Verdiği Kod (Örn: REF-12345)")
                if st.button("Bulutta Ara ☁️ 🔍", use_container_width=True):
                    if kod:
                        with st.spinner("Google Firebase Sunucuları Taranıyor..."):
                            time.sleep(1)
                            # --- BULUTTAN OKUYORUZ ---
                            bulut_veri = veri_getir(kod)
                            if bulut_veri:
                                st.session_state.onaylanan_kiraci = bulut_veri['ad']
                                st.session_state.kiraci_puan = bulut_veri['puan']
                                st.rerun() 
                            else: st.warning("Girdiğiniz kod bulut sunucularında bulunamadı.")
                    else: st.error("Lütfen bir kod girin.")
            
            if st.session_state.onaylanan_kiraci:
                k_isim = st.session_state.onaylanan_kiraci
                k_puan = st.session_state.kiraci_puan
                st.success("✅ Kiracı Profili Buluttan Çekildi.")
                m1, m2 = st.columns(2)
                m1.metric(label="Mevcut Kiracı Adayı", value=k_isim, delta=f"⭐ {k_puan}")
                if st.button("Farklı Bir Kod Sorgula"): 
                    st.session_state.onaylanan_kiraci = None; st.rerun()
                st.markdown("<br><hr><br>", unsafe_allow_html=True)
                
                c_sol, c_sag = st.columns([2,1])
                with c_sol:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.subheader("🗓️ Aylık Kira Takip Çizelgesi")
                    st.markdown("""| Ay | Beklenen Tutar | Ödeme Durumu | Ev Sahibi Onayı |\n|---|---|---|---|\n| Ocak 2026 | 15.000 TL | 🟢 Ödendi | ✅ Onaylandı |\n| Mart 2026 | 15.000 TL | ⏳ Bekleniyor | 🔘 Onay Bekliyor |""")
                    if st.button("Ödemeyi Onayla"): st.success("✅ Onaylandı.")
                    st.markdown("</div>", unsafe_allow_html=True)

                with c_sag:
                    st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                    st.subheader("🤝 Sözleşme Modülü")
                    with st.form("s_form"):
                        tapu = st.file_uploader("Tapu Belgenizi Yükleyin", type=["pdf", "jpg", "png"])
                        adres = st.text_area("Kiralanan Adres")
                        kira = st.number_input("Aylık Kira Bedeli (TL)", step=1000, value=15000)
                        depozito = st.number_input("Depozito (TL)", step=1000, value=15000)
                        gun = st.text_input("Ödeme Günü")
                        s_uret = st.form_submit_button("📄 Güvenli Sözleşme Üret", use_container_width=True)
                        if s_uret:
                            if not tapu: st.error("Tapu belgenizi yükleyin.")
                            elif not adres or not gun: st.error("Adres ve gün girin.")
                            else:
                                ok, msg = belgeyi_tara_ve_dogrula(tapu, "tapu")
                                if not ok: st.error(f"Güvenlik İhlali: {msg}")
                                else:
                                    st.success("✅ Tapu doğrulandı. Sözleşme Hazır!")
                                    metin = resmi_sozlesme_metni_hazirla(k_isim, adres, kira, depozito, gun)
                                    st.download_button("📥 Sözleşmeyi İndir (TXT)", metin, "sozlesme.txt", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<br>### 🌟 Onaylı Premium Kiracı Adayları", unsafe_allow_html=True)
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.markdown("<div class='dashboard-box' style='text-align:center; border: 2px solid #FFD700;'>", unsafe_allow_html=True)
                st.markdown("<div style='background-color:#FFD700; color:#002147; font-weight:bold; border-radius:5px; padding:5px; margin-bottom:10px;'>🚀 PRIME KİRACI</div>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>B*** G***</h2>", unsafe_allow_html=True)
                st.markdown("💳 **Bütçe:** 25.000 TL")
                st.button("Eşleşme İste", key="ep1", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with p_col2:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>A*** Y***</h2>", unsafe_allow_html=True)
                st.markdown("💳 **Bütçe:** 40.000 TL")
                st.button("Eşleşme İste", key="ep2", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with p_col3:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h2 style='color:#002147;'>M*** K***</h2>", unsafe_allow_html=True)
                st.markdown("💳 **Bütçe:** 18.000 TL")
                st.button("Eşleşme İste", key="ep3", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<br>### 🏠 Güvenli Ev İlanı Oluştur", unsafe_allow_html=True)
            with st.form("ilan_form"):
                st.text_input("İlan Başlığı")
                st.number_input("Aylık Kira Bedeli (TL)", step=1000)
                st.slider("Minimum Puan Şartı", 1.0, 5.0, 4.0, 0.5)
                st.markdown("#### 🚀 İlanınızı Öne Çıkarın (Referans Prime)")
                i_boost = st.radio("Seçiminiz:", ["Ücretsiz İlan", "24 Saat Prime İlan (89 TL)"])
                if st.form_submit_button("İlanı Yayınla", use_container_width=True):
                    st.success("İlanınız havuzda yayınlandı!")