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

# --- AGRESİF CSS DÜZELTMESİ (KOYU MOD ENGELLEYİCİ) ---
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f0f2f6 !important; }
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stMarkdown p, [data-testid="stMarkdownContainer"] p, .stWidget label p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, [data-testid="stHeader"] {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    .stSlider [data-testid="stWidgetLabel"] p, .stSlider div { color: #002147 !important; }
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #002147 !important; color: #ffffff !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #003366 !important; color: #ffffff !important; border: 1px solid white !important;
    }
    div.stButton > button p, div.stDownloadButton > button p { color: #ffffff !important; }
    [data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #002147 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] * { color: #002147 !important; }
    [data-testid="stFileUploaderDropzone"] button { background-color: #002147 !important; color: #ffffff !important; border-radius: 6px !important; }
    [data-testid="stFileUploaderDropzone"] button * { color: #ffffff !important; }
    [data-testid="stUploadedFile"] { background-color: #e6eef5 !important; border: 1px solid #002147 !important; border-radius: 5px !important; }
    [data-testid="stUploadedFile"] * { color: #002147 !important; }
    .stAlert { background-color: #ffffff !important; border: 1px solid #ddd !important; color: #000000 !important; }
    .stAlert div[data-testid="stMarkdownContainer"] p { color: #000000 !important; }
    [data-testid="stForm"] { background-color: transparent !important; border: none !important; }
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
    if OCR_AKTIF: return easyocr.Reader(['tr', 'en'], gpu=False) 
    return None

def belgeyi_tara_ve_dogrula(uploaded_file, belge_tipi="tapu"):
    if not OCR_AKTIF: return True, "Simülasyon Modu (OCR eksik)" 
    metin_icerigi = ""
    if uploaded_file.name.lower().endswith('.pdf'):
        try:
            pdf_reader = pypdf.PdfReader(uploaded_file)
            for page in pdf_reader.pages: metin_icerigi += page.extract_text() + " "
        except: return False, "PDF dosyası okunamadı."
    else:
        try:
            reader = ocr_modeli_yukle()
            bytes_data = uploaded_file.getvalue()
            image = np.asarray(bytearray(bytes_data), dtype=np.uint8)
            img = cv2.imdecode(image, 1) 
            result = reader.readtext(img, detail=0)
            metin_icerigi = " ".join(result)
        except Exception as e: return False, f"Resim hatası: {str(e)}"

    metin_icerigi = metin_icerigi.upper() 
    if belge_tipi == "tapu":
        anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN", "NİTELİĞİ", "TÜRKİYE"]
        limit = 2 
    else: 
        anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR", "KAZANÇ", "DÖKÜMÜ"]
        limit = 2

    eslesme_sayisi = 0
    bulunanlar = []
    for kelime in anahtar_kelimeler:
        if kelime in metin_icerigi:
            eslesme_sayisi += 1; bulunanlar.append(kelime)

    if eslesme_sayisi >= limit: return True, f"Doğrulandı! ({', '.join(bulunanlar)})"
    else: return False, f"Anahtar kelime bulunamadı. (Okunan: {metin_icerigi[:50]}...)"

# --- RAPOR, QR VE PUANLAMA ---
def rapor_metni_hazirla(ad, kod, puan, tarih, analiz):
    # Analiz listesini alt alta düzgün yazdıralım
    analiz_str = "\n".join([f"- {madde}" for madde in analiz])
    return f"""REFERANSEVİM GÜVENLİK RAPORU
----------------------------------
Referans Kodu: {kod}
Sorgulama Tarihi: {tarih}
----------------------------------
KİRACI BİLGİLERİ
Ad Soyad: {ad}
Güvenilirlik Puanı: {puan} / 5

DETAYLI ANALİZ:
{analiz_str}
----------------------------------
Bu belge ReferansEvim yapay zeka ve OCR sistemleri tarafindan dogrulanmistir. Yasal sorumluluk beyan edene aittir."""

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(veri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu, eski_ev_sahibi_ref):
    puan = 0
    analiz = []
    
    # Gelir
    if gelir >= 40000: puan += 30; analiz.append("Gelir Seviyesi: Yüksek (+30p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart/Orta (+20p)")
    else: puan += 10; analiz.append("Gelir Seviyesi: Düşük Riskli (+10p)")
    
    # Findeks
    if findex >= 1500: puan += 30; analiz.append("Kredi Notu: Çok İyi (+30p)")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: Orta/İyi (+20p)")
    else: puan += 0; analiz.append("Kredi Notu: Riskli (0p)")
    
    # Belge (Bordro)
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (+20p)")
    else: analiz.append("Maaş Bordrosu: Yüklenmedi (0p)")
    
    # Eski Ev Sahibi Referansı (YENİ EKLENEN VİZYON)
    if eski_ev_sahibi_ref == "5 Yıldız (Çok İyi)":
        puan += 20; analiz.append("Eski Ev Sahibi Referansı: Kusursuz (+20p)")
    elif eski_ev_sahibi_ref == "4 Yıldız (İyi)":
        puan += 10; analiz.append("Eski Ev Sahibi Referansı: Olumlu (+10p)")
    elif eski_ev_sahibi_ref == "3 Yıldız (Orta)":
        puan += 0; analiz.append("Eski Ev Sahibi Referansı: Nötr (0p)")
    elif eski_ev_sahibi_ref in ["1 Yıldız (Kötü)", "2 Yıldız (Zayıf)"]:
        puan -= 20; analiz.append("Eski Ev Sahibi Referansı: NEGATİF RİSK (-20p)")
    else:
        analiz.append("Eski Ev Sahibi Referansı: Yok/Belirtilmedi (0p)")
    
    # Toplam puanı 100 üzerinden 5 yıldıza çevirme
    if puan < 0: puan = 0
    if puan > 100: puan = 100
    yildiz = round((puan/100)*5 * 2) / 2
    if yildiz < 1: yildiz = 1.0 # Minimum 1 yıldız
    return yildiz, analiz

# --- UYGULAMA ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>ReferansEvim</h1>", unsafe_allow_html=True)
        st.info("💡 Sistem, yapay zeka ile belge doğrulama ve referans ağı içerir.")
        tip = st.radio("Seçiniz:", ("👤 Kiracı Girişi", "🔑 Ev Sahibi Girişi"))
        onay = st.checkbox("Yasal Sorumluluk Beyanı: Girdiğim tüm bilgilerin doğruluğunu onaylıyorum.")
        if st.button("Sisteme Giriş Yap", use_container_width=True):
            if onay:
                st.session_state.giris_yapildi = True
                st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in tip else "evsahibi"
                st.rerun()
            else: st.error("Lütfen yasal uyarıyı onaylayınız.")

else:
    c1, c2 = st.columns([8, 1])
    with c1: st.title("🏠 ReferansEvim Paneli")
    with c2:
        if st.button("Güvenli Çıkış"):
            st.session_state.giris_yapildi = False; st.session_state.son_rapor = None; st.rerun()
    st.markdown("---")

    # KİRACI PANELİ
    if st.session_state.kullanici_tipi == "kiraci":
        st.subheader("📝 Akıllı Referans Raporu Oluştur")
        with st.form("k_form"):
            c1, c2 = st.columns(2)
            with c1: 
                ad = st.text_input("Ad Soyad")
                tc = st.text_input("T.C. Kimlik No")
                eski_ev_sahibi = st.selectbox("Eski Ev Sahibinizin Sizin İçin Referans Puanı", 
                                             ["İlk Defa Eve Çıkıyorum / Referans Yok", "5 Yıldız (Çok İyi)", "4 Yıldız (İyi)", "3 Yıldız (Orta)", "2 Yıldız (Zayıf)", "1 Yıldız (Kötü)"])
            with c2: 
                gelir = st.number_input("Aylık Net Gelir (TL)", step=1000)
                findex = st.slider("Tahmini Findeks Kredi Notu", 0, 1900, 1100)
                meslek = st.text_input("Meslek / Şirket")
            
            st.markdown("<hr>", unsafe_allow_html=True)
            dosya = st.file_uploader("Maaş Bordrosu (Yapay Zeka Onayı Ekstra Puan Kazandırır)", type=["pdf", "jpg", "png"])
            
            if st.form_submit_button("Analiz Et ve Raporu Hazırla"):
                if not ad: st.error("Lütfen isminizi giriniz.")
                else:
                    belge_ok = False
                    if dosya:
                        with st.spinner("Maaş bordrosu yapay zeka ile taranıyor (OCR)..."):
                            time.sleep(0.5)
                            ok, msg = belgeyi_tara_ve_dogrula(dosya, "maas")
                            if ok: belge_ok = True; st.success(msg)
                            else: st.warning(f"Bordro onaylanamadı: {msg}")
                    
                    puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, belge_ok, eski_ev_sahibi)
                    kod = f"REF-{random.randint(10000, 99999)}"
                    tarih = datetime.now().strftime("%d-%m-%Y")
                    veri = {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek}
                    veri_kaydet(kod, veri)
                    st.session_state.son_rapor = {"kod": kod, "veri": veri}
        
        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            st.success("✅ Referans Raporunuz Başarıyla Oluşturuldu!")
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
                with st.expander("📊 Referans Puanı Analiz Detayı (Ev Sahibine Gidecek)"):
                    for madde in rp['veri']['analiz']:
                        st.write(madde)
            with cr:
                qr_txt = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], rp['veri']['analiz'])
                st.image(qr_kod_olustur(qr_txt), caption="Ev Sahibi İçin Taratılabilir QR", use_container_width=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            metin = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], rp['veri']['analiz'])
            st.download_button("📄 Detaylı Raporu İndir (PDF/TXT Formatında)", metin, file_name=f"ReferansEvim_Rapor_{rp['kod']}.txt")

    # EV SAHİBİ PANELİ
    elif st.session_state.kullanici_tipi == "evsahibi":
        st.subheader("🛡️ Kiracı & Belge Doğrulama Merkezi")
        st.info("⚠️ Sisteme yetkisiz erişimi engellemek için lütfen Tapu belgenizi yükleyiniz. AI sistemimiz belgeyi teyit edecektir.")
        
        tapu = st.file_uploader("Tapu Belgesi Yükle (OCR Kontrolü)", type=["pdf", "jpg", "png"])
        kod = st.text_input("Kiracının Size Verdiği Kod (Örn: REF-12345)")