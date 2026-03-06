import streamlit as st
import time
import random
import os
import json
import qrcode
from io import BytesIO
from datetime import datetime
import numpy as np

# --- YENİ KÜTÜPHANELER (Hata Yönetimi ile) ---
try:
    import pypdf
    import easyocr
    import cv2
    OCR_AKTIF = True
except ImportError:
    OCR_AKTIF = False
    st.warning("⚠️ OCR kütüphaneleri eksik! Terminale 'pip install easyocr pypdf opencv-python-headless' yazıp kurun. Aksi halde belge okuma çalışmaz.")

# --- AYARLAR ---
st.set_page_config(page_title="ReferansEvim Pro", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

# --- 🔥 AGRESİF CSS DÜZELTMESİ 🔥 ---
st.markdown("""
<style>
    /* 1. ANA UYGULAMA ARKA PLANI */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #f0f2f6 !important;
    }

    /* 2. GENEL METİN RENKLERİ (Lacivert) */
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stMarkdown p, 
    [data-testid="stMarkdownContainer"] p, .stWidget label p {
        color: #002147 !important;
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    /* 3. GİRİŞ KUTULARI (BEYAZ ZEMİN, SİYAH YAZI) */
    .stTextInput input, .stNumberInput input, .stSelectbox div, 
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
    }
    .stSlider [data-testid="stWidgetLabel"] p, .stSlider div {
        color: #002147 !important;
    }

    /* 4. GENEL BUTONLAR (LACİVERT ZEMİN, BEYAZ YAZI) */
    div.stButton > button, 
    div.stDownloadButton > button, 
    div.stFormSubmitButton > button {
        background-color: #002147 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover, 
    div.stDownloadButton > button:hover {
        background-color: #003366 !important;
        color: #ffffff !important;
        border: 1px solid white !important;
    }
    div.stButton > button p, div.stDownloadButton > button p {
        color: #ffffff !important;
    }

    /* 5. 🔥 DOSYA YÜKLEME KUTUSU (LAZER ÇÖZÜM) 🔥 */
    /* Yükleme alanının çerçevesi ve arka planı */
    [data-testid="stFileUploader"] section {
        background-color: #ffffff !important;
        border: 2px dashed #002147 !important;
    }
    /* "Drag and drop file here" yazıları */
    [data-testid="stFileUploaderDropzoneInstructions"] * {
        color: #002147 !important;
    }
    /* "Browse files" butonu (Özel hedefleme) */
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #002147 !important;
        color: #ffffff !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploaderDropzone"] button * {
        color: #ffffff !important;
    }
    /* YÜKLENEN DOSYANIN ADININ ÇIKTIĞI KISIM (Görünmez olan yer) */
    [data-testid="stUploadedFile"] {
        background-color: #e6eef5 !important; /* Hafif mavi/gri arka plan */
        border: 1px solid #002147 !important;
        border-radius: 5px !important;
    }
    /* Yüklenen dosyanın adı, boyutu, çarpı işareti vs. hepsi Lacivert olacak */
    [data-testid="stUploadedFile"] * {
        color: #002147 !important;
    }

    /* 6. UYARI VE BİLGİ KUTULARI */
    .stAlert {
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        color: #000000 !important;
    }
    .stAlert div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    [data-testid="stForm"] {
        background-color: transparent !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI ---
DB_DOSYASI = "referans_db.json"
def verileri_yukle():
    if not os.path.exists(DB_DOSYASI): return {}  
    try: 
        with open(DB_DOSYASI, "r", encoding="utf-8") as f: return json.load(f)
    except: return {} 
def veri_kaydet(kod, veri):
    db = verileri_yukle()
    db[kod] = veri
    with open(DB_DOSYASI, "w", encoding="utf-8") as f: json.dump(db, f, ensure_ascii=False, indent=4)

# --- GERÇEK BELGE ANALİZİ (OCR) ---
@st.cache_resource
def ocr_modeli_yukle():
    if OCR_AKTIF:
        return easyocr.Reader(['tr', 'en'], gpu=False) 
    return None

def belgeyi_tara_ve_dogrula(uploaded_file, belge_tipi="tapu"):
    if not OCR_AKTIF:
        return True, "Simülasyon Modu (OCR kütüphanesi eksik, varsayılan onay)" 

    metin_icerigi = ""
    
    if uploaded_file.name.lower().endswith('.pdf'):
        try:
            pdf_reader = pypdf.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                metin_icerigi += page.extract_text() + " "
        except:
            return False, "PDF dosyası okunamadı veya bozuk."
    else:
        try:
            reader = ocr_modeli_yukle()
            bytes_data = uploaded_file.getvalue()
            image = np.asarray(bytearray(bytes_data), dtype=np.uint8)
            img = cv2.imdecode(image, 1) 
            
            result = reader.readtext(img, detail=0)
            metin_icerigi = " ".join(result)
        except Exception as e:
            return False, f"Resim işlenirken hata oluştu: {str(e)}"

    metin_icerigi = metin_icerigi.upper() 
    
    if belge_tipi == "tapu":
        anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN", "KAT MÜLKİYETİ", "NİTELİĞİ", "TÜRKİYE"]
        limit = 2 
    else: 
        anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR", "KAZANÇ", "DÖKÜMÜ", "HİZMET"]
        limit = 2

    eslesme_sayisi = 0
    bulunanlar = []
    for kelime in anahtar_kelimeler:
        if kelime in metin_icerigi:
            eslesme_sayisi += 1
            bulunanlar.append(kelime)

    if eslesme_sayisi >= limit:
        return True, f"Doğrulandı! Bulunan detaylar: {', '.join(bulunanlar)}"
    else:
        return False, f"Belge içeriği doğrulanamadı. İlgili anahtar kelimeler bulunamadı. (Okunan Metin: {metin_icerigi[:100]}...)"

# --- RAPOR VE QR ---
def rapor_metni_hazirla(ad, kod, puan, tarih, analiz):
    return f"REFERANSEVİM GÜVENLİK RAPORU\n------------------------\nKod: {kod}\nTarih: {tarih}\nKiraci: {ad}\nPuan: {puan}/5\nDurum: {analiz}\n------------------------\nBu belge ReferansEvim yapay zeka sistemi tarafindan dogrulanmistir."

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(veri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu):
    puan = 0
    analiz = []
    if gelir >= 30000: puan += 40; analiz.append("Gelir İyi (+40p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Orta (+20p)")
    else: puan += 10; analiz.append("Gelir Düşük (+10p)")
    
    if findex >= 1200: puan += 40; analiz.append("Kredi Notu İyi (+40p)")
    else: puan += 10; analiz.append("Kredi Notu Riskli (+10p)")
    
    if belge_durumu: puan += 20; analiz.append("Bordro Doğrulandı (+20p)")
    else: analiz.append("Bordro Yok/Geçersiz (+0p)")
    
    yildiz = round((puan/100)*5 * 2) / 2
    return yildiz, analiz

# --- UYGULAMA ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None

# GİRİŞ EKRANI
if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>ReferansEvim</h1>", unsafe_allow_html=True)
        st.info("💡 Güvenli Mod: Belgeler Yapay Zeka (OCR) ile taranmaktadır.")
        tip = st.radio("Seçiniz:", ("👤 Kiracı Girişi", "🔑 Ev Sahibi Girişi"))
        onay = st.checkbox("Yasal Sorumluluk Beyanı: Bilgilerimin doğruluğunu onaylıyorum.")
        if st.button("Giriş Yap", use_container_width=True):
            if onay:
                st.session_state.giris_yapildi = True
                st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in tip else "evsahibi"
                st.rerun()
            else: st.error("Lütfen yasal uyarıyı onaylayınız.")

else: # ANA PANEL
    c1, c2 = st.columns([8, 1])
    with c1: st.title("🏠 ReferansEvim Paneli")
    with c2:
        if st.button("Çıkış"):
            st.session_state.giris_yapildi = False; st.session_state.son_rapor = None; st.rerun()
    st.markdown("---")

    # KİRACI PANELİ
    if st.session_state.kullanici_tipi == "kiraci":
        st.subheader("📝 Rapor Oluştur")
        with st.form("k_form"):
            c1, c2 = st.columns(2)
            with c1: ad = st.text_input("Ad Soyad"); tc = st.text_input("T.C.")
            with c2: gelir = st.number_input("Gelir (TL)", step=1000); findex = st.slider("Findeks Notu", 0, 1900, 1100); meslek = st.text_input("Meslek")
            dosya = st.file_uploader("Maaş Bordrosu (Zorunlu Değil ama Puan Artırır)", type=["pdf", "jpg", "png"])
            if st.form_submit_button("Analiz Et ve Puanla"):
                if not ad: st.error("Lütfen isminizi giriniz.")
                else:
                    belge_ok = False
                    if dosya:
                        with st.spinner("Maaş bordrosu taranıyor (AI)..."):
                            time.sleep(0.5)
                            ok, msg = belgeyi_tara_ve_dogrula(dosya, "maas")
                            if ok: belge_ok = True; st.success(msg)
                            else: st.warning(f"Bordro kabul edilmedi: {msg}")
                    
                    puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, belge_ok)
                    kod = f"REF-{random.randint(10000, 99999)}"
                    tarih = datetime.now().strftime("%d-%m-%Y")
                    veri = {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek}
                    veri_kaydet(kod, veri)
                    st.session_state.son_rapor = {"kod": kod, "veri": veri}
        
        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            st.success("✅ Raporunuz Hazır!")
            cl, cr = st.columns([2,1])
            with cl:
                st.markdown(f"""
                <div style='border:2px solid #002147; padding:20px; border-radius:10px; text-align:center; background-color:white;'>
                    <h3 style='color:#002147; margin:0;'>KODUNUZ</h3>
                    <h1 style='color:#002147; font-size:3em;'>{rp['kod']}</h1>
                    <hr>
                    <h1 style='color:#FFD700; margin:0;'>⭐ {rp['veri']['puan']} / 5</h1>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("📊 Puan Analiz Detayı"):
                    for madde in rp['veri']['analiz']:
                        st.write(madde)
            with cr:
                qr_txt = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], "Sistem Onaylı")
                st.image(qr_kod_olustur(qr_txt), caption="Ev Sahibi İçin QR", use_container_width=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            metin = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], "Sistem Onaylı")
            st.download_button("📄 Raporu İndir (PDF/TXT)", metin, file_name=f"ReferansEvim_Rapor_{rp['kod']}.txt")

    # EV SAHİBİ PANELİ
    elif st.session_state.kullanici_tipi == "evsahibi":
        st.subheader("🛡️ Belge Doğrulama Merkezi")
        st.info("⚠️ Sorgulama yapabilmek için kendi Tapu belgenizi yüklemeniz gerekmektedir. AI sistemimiz belgeyi okuyacaktır.")
        
        tapu = st.file_uploader("Tapu Belgesi Yükle (Zorunlu)", type=["pdf", "jpg", "png"])
        kod = st.text_input("Kiracı Kodu (REF-XXXXX)")
        
        if st.button("Belgeyi Tara ve Sorgula 🔍"):
            if not tapu: st.error("Lütfen önce kendi Tapu belgenizi yükleyin.")
            else:
                with st.spinner("Tapu Belgesi Yapay Zeka ile Okunuyor (OCR)..."):
                    ok, msg = belgeyi_tara_ve_dogrula(tapu, "tapu")
                    
                    if not ok:
                        st.error("⛔ SİSTEM REDDETTİ!")
                        st.error(msg)
                        st.image(tapu, caption="Reddedilen Belge", width=200)
                    else:
                        st.success("✅ TAPU ONAYLANDI: Belge geçerli görünüyor.")
                        st.info(msg) 
                        
                        db = verileri_yukle()
                        if kod in db:
                            k = db[kod]
                            st.markdown(f"""
                            <div style="background:white; padding:25px; border-left:10px solid #002147; border-radius:5px; margin-top:10px;">
                                <h2 style="color:#002147; margin:0;">✅ KİRACI BİLGİLERİ DOĞRULANDI</h2>
                                <hr>
                                <p style="color:black !important; font-size:1.1em;"><b>İsim:</b> {k['ad']}</p>
                                <p style="color:black !important; font-size:1.1em;"><b>Puan:</b> {k['puan']} / 5</p>
                                <p style="color:black !important;"><b>Meslek:</b> {k.get('meslek', 'Belirtilmedi')}</p>
                                <p style="color:black !important; font-size:0.8em;"><em>Oluşturma Tarihi: {k['tarih']}</em></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            txt = rapor_metni_hazirla(k['ad'], kod, k['puan'], k['tarih'], "Orijinal ve Onaylı")
                            st.download_button("📄 Kiracı Raporunu İndir", txt, file_name=f"ReferansEvim_Sorgu_{kod}.txt")
                        else:
                            st.warning("Bu kod sistemde bulunamadı.")