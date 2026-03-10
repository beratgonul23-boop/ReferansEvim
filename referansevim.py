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
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stMarkdown p, [data-testid="stMarkdownContainer"] p, .stWidget label p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, [data-testid="stHeader"], .stTextArea textarea {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important;
    }
    div.stButton > button *, div.stDownloadButton > button *, div.stFormSubmitButton > button * { color: #ffffff !important; }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    
    .btn-google > button { background-color: #ffffff !important; color: #444 !important; border: 1px solid #ddd !important; }
    .btn-google > button * { color: #444 !important; }
    .btn-edevlet > button { background-color: #e30a17 !important; color: #ffffff !important; }
    
    [data-testid="stMetricValue"] { color: #002147 !important; font-size: 2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricDelta"] { font-size: 1rem !important; }
    
    .dashboard-box { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
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
    db = verileri_yukle()
    db[kod] = veri
    with open(DB_DOSYASI, "w", encoding="utf-8") as f: json.dump(db, f, ensure_ascii=False, indent=4)

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
    if belge_tipi == "tapu": anahtar_kelimeler = ["TAPU", "SENEDİ", "TAŞINMAZ", "ADA", "PARSEL", "ARSA", "MESKEN", "NİTELİĞİ", "TÜRKİYE"]; limit = 2 
    else: anahtar_kelimeler = ["MAAŞ", "BORDRO", "ÜCRET", "SGK", "GELİR", "KAZANÇ", "DÖKÜMÜ"]; limit = 2
    eslesme_sayisi = sum(1 for kelime in anahtar_kelimeler if kelime in metin_icerigi)
    if eslesme_sayisi >= limit: return True, "Doğrulandı!"
    else: return False, "Okunamadı."

def rapor_metni_hazirla(ad, kod, puan, tarih, analiz):
    analiz_str = "\n".join([f"- {madde}" for madde in analiz])
    return f"REFERANSEVİM GÜVENLİK RAPORU (KVKK UYUMLU)\n----------------------------------\nReferans Kodu: {kod}\nSorgulama Tarihi: {tarih}\n----------------------------------\nKİRACI BİLGİLERİ\nAd Soyad: {ad}\nGüvenilirlik Puanı: {puan} / 5\n\nDETAYLI ANALİZ:\n{analiz_str}\n----------------------------------\n* Yasal Uyari: Sisteme yuklenen hicbir kimlik veya gelir belgesi sunucularda SAKLANMAMISTIR."

def resmi_sozlesme_metni_hazirla(kiraci_adi, adres, kira_bedeli, depozito, odeme_gunu, zam_orani):
    return f"KİRA SÖZLEŞMESİ TASLAĞI\n\nKiracı: {kiraci_adi}\nAdres: {adres}\nAylık Kira: {kira_bedeli} TL\nÖdeme Günü: {odeme_gunu}\n\nİşbu sözleşme ReferansEvim aracılığıyla hazırlanmıştır."

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4); qr.add_data(veri); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white"); buffer = BytesIO(); img.save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu, eski_tel):
    puan = 0; analiz = []
    if gelir >= 40000: puan += 40; analiz.append("Gelir Seviyesi: Yüksek (+40p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart/Orta (+20p)")
    else: puan += 10; analiz.append("Gelir Seviyesi: Düşük Riskli (+10p)")
    if findex >= 1500: puan += 40; analiz.append("Kredi Notu: Çok İyi (+40p)")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: Orta/İyi (+20p)")
    else: puan += 0; analiz.append("Kredi Notu: Riskli (0p)")
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (Belge İmha Edildi) (+20p)")
    else: analiz.append("Maaş Bordrosu: Yüklenmedi (0p)")
    if eski_tel: analiz.append(f"Referans: Eski ev sahibi eklendi. Teyit ediniz.")
    else: analiz.append("Referans: Eski ev sahibi bilgisi girilmedi.")
    yildiz = round((puan/100)*5 * 2) / 2
    if yildiz < 1: yildiz = 1.0 
    return yildiz, analiz

# --- UYGULAMA ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None
if 'onaylanan_kiraci' not in st.session_state: st.session_state.onaylanan_kiraci = None
if 'kiraci_puan' not in st.session_state: st.session_state.kiraci_puan = None

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
            
        st.markdown("<p style='text-align: center; color: gray;'>Türkiye'nin İlk Yapay Zeka Destekli Kiracı Doğrulama ve Uzlaştırma Platformu</p><br>", unsafe_allow_html=True)
        st.info("💡 %100 KVKK Uyumlu: Yüklenen belgeler asla sunucularda saklanmaz, analiz sonrası anında imha edilir.")
        kullanici_tipi = st.selectbox("Sisteme Giriş Tipinizi Seçiniz", ["Kiracı Olarak Giriş Yap", "Ev Sahibi Olarak Giriş Yap"])
        
        with st.expander("⚖️ KVKK ve Aydınlatma Metnini Okumak İçin Tıklayınız"):
            st.write("**Kişisel Verilerin Korunması ve Veri İmha Politikası**\n1. Belgeler yapay zeka tarafından okunur ve anında silinir.\n2. T.C. Kimlik numarası asla kayıt altına alınmaz.")
        
        onay = st.checkbox("KVKK Aydınlatma Metnini okudum, anladım ve kabul ediyorum.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            st.markdown("<div class='btn-google'>", unsafe_allow_html=True)
            if st.button("🌐 Google ile Giriş", use_container_width=True):
                if onay:
                    st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
                else: st.error("Lütfen KVKK metnini onaylayınız.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_btn2:
            st.markdown("<div class='btn-edevlet'>", unsafe_allow_html=True)
            if st.button("🔴 e-Devlet ile Giriş", use_container_width=True):
                if onay:
                    st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
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
    # 👤 KİRACI PANELİ VE KONTROL EKRANI (DASHBOARD)
    # ==========================================
    if st.session_state.kullanici_tipi == "kiraci":
        
        # EĞER RAPOR YOKSA FORM GÖSTER
        if not st.session_state.son_rapor:
            st.subheader("📝 Akıllı Referans Raporu Oluştur")
            with st.form("k_form"):
                c1, c2 = st.columns(2)
                with c1: 
                    ad = st.text_input("Ad Soyad")
                    tc = st.text_input("T.C. Kimlik No (Kayıt Altına Alınmaz)")
                    eski_ev_sahibi_tel = st.text_input("Eski Ev Sahibi Telefon Numarası")
                with c2: 
                    gelir = st.number_input("Aylık Net Gelir (TL)", step=1000)
                    findex = st.slider("Tahmini Findeks Kredi Notu", 0, 1900, 1100)
                    meslek = st.text_input("Meslek / Şirket")
                
                st.markdown("<hr>", unsafe_allow_html=True)
                dosya = st.file_uploader("Maaş Bordrosu (Verileriniz saklanmaz, anında imha edilir)", type=["pdf", "jpg", "png"])
                
                if st.form_submit_button("Analiz Et ve Raporu Hazırla", use_container_width=True):
                    if not ad: st.error("Lütfen isminizi giriniz.")
                    else:
                        belge_ok = False
                        if dosya:
                            with st.spinner("Maaş bordrosu yapay zeka ile taranıyor..."):
                                time.sleep(1) 
                                ok, msg = belgeyi_tara_ve_dogrula(dosya, "maas")
                                if ok: belge_ok = True; st.success(msg)
                        
                        puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, belge_ok, eski_ev_sahibi_tel)
                        kod = f"REF-{random.randint(10000, 99999)}"
                        tarih = datetime.now().strftime("%d-%m-%Y")
                        veri = {"ad": ad, "puan": puan, "tarih": tarih, "analiz": analiz, "meslek": meslek}
                        veri_kaydet(kod, veri)
                        st.session_state.son_rapor = {"kod": kod, "veri": veri}
                        st.rerun() # Paneli yenilemek için

        # EĞER RAPOR VARSA DASHBOARD (KONTROL PANELİ) GÖSTER
        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            st.success(f"Hoş Geldiniz Sayın {rp['veri']['ad']}, Profiliniz Aktif.")
            
            # KİRACI DASHBOARD METRİKLERİ
            m1, m2, m3 = st.columns(3)
            m1.metric(label="ReferansEvim Güven Puanınız", value=f"⭐ {rp['veri']['puan']} / 5", delta="Platform Ortalamasının Üstünde", delta_color="normal")
            m2.metric(label="Yaklaşan Kira Ödemesi", value="Bekleniyor", delta="Henüz sözleşme eşleşmesi yapılmadı", delta_color="off")
            m3.metric(label="Mevcut Referans Kodunuz", value=rp['kod'], delta="Ev Sahibinizle Paylaşın", delta_color="normal")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # KİRACI PROFİL VE SİCİL DETAYI
            c_sol, c_sag = st.columns([2,1])
            with c_sol:
                st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                st.subheader("📊 Dijital Kira Sicili ve Raporunuz")
                st.write("Bu rapor sizin dijital emlak itibarınızdır. Düzenli kira ödedikçe puanınız artar, yeni ev kiralarken bir adım önde olursunuz.")
                with st.expander("Sistem Analiz Detaylarınızı Görüntüleyin"):
                    for madde in rp['veri']['analiz']: st.write(madde)
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                st.subheader("💳 Kira Ödeme Geçmişi")
                st.info("Sistemimizde aktif bir kira sözleşmeniz bulunduğunda ödemelerinizi buradan takip edebilir ve ev sahibine dekont iletebilirsiniz.")
                st.button("Dekont Yükle / Ev Sahibine Bildir (Yakında)", disabled=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c_sag:
                st.markdown("<div class='dashboard-box' style='text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color:#002147;'>Ev Sahibiyle Paylaş</h4>", unsafe_allow_html=True)
                qr_txt = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], rp['veri']['analiz'])
                st.image(qr_kod_olustur(qr_txt), use_container_width=True)
                st.markdown(f"<h2>{rp['kod']}</h2>", unsafe_allow_html=True)
                metin = rapor_metni_hazirla(rp['veri']['ad'], rp['kod'], rp['veri']['puan'], rp['veri']['tarih'], rp['veri']['analiz'])
                st.download_button("📄 PDF/TXT İndir", metin, file_name=f"ReferansEvim_{rp['kod']}.txt", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 🔑 EV SAHİBİ PANELİ VE KONTROL EKRANI (DASHBOARD)
    # ==========================================
    elif st.session_state.kullanici_tipi == "evsahibi":
        
        if not st.session_state.onaylanan_kiraci:
            st.subheader("🛡️ Kiracı & Belge Doğrulama Merkezi")
            st.info("⚠️ Lütfen Tapu belgenizi yükleyiniz. Belgeniz analiz edildikten sonra SAKLANMADAN SİLİNECEKTİR.")
            
            tapu = st.file_uploader("Tapu Belgesi Yükle (Anında İmha Edilir)", type=["pdf", "jpg", "png"])
            kod = st.text_input("Kiracının Size Verdiği Kod (Örn: REF-12345)")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Belgeyi Tarat ve Sorgula 🔍", use_container_width=True):
                if not tapu: st.error("Lütfen önce kendi Tapu belgenizi yükleyin.")
                else:
                    with st.spinner("Güvenlik Taraması Yapılıyor..."):
                        time.sleep(1)
                        ok, msg = belgeyi_tara_ve_dogrula(tapu, "tapu")
                        if not ok: st.error(msg)
                        else:
                            st.success("✅ Tapu belgesi geçerli, anında imha edildi.")
                            db = verileri_yukle()
                            if kod in db:
                                st.session_state.onaylanan_kiraci = db[kod]['ad']
                                st.session_state.kiraci_puan = db[kod]['puan']
                                st.rerun() # Dashboard'a geçiş için sayfayı yenile
                            else:
                                st.warning("Girdiğiniz kod sistemde bulunamadı.")
        
        # EĞER KİRACI BULUNDUYSA EV SAHİBİ DASHBOARD GÖSTER
        if st.session_state.onaylanan_kiraci:
            k_isim = st.session_state.onaylanan_kiraci
            k_puan = st.session_state.kiraci_puan
            
            st.success("✅ Sistem Onaylı Emlak Yönetim Paneline Hoş Geldiniz.")
            
            # EV SAHİBİ DASHBOARD METRİKLERİ
            m1, m2, m3 = st.columns(3)
            m1.metric(label="Mevcut Aktif Kiracınız", value=k_isim, delta=f"Güven Puanı: ⭐ {k_puan}", delta_color="normal")
            m2.metric(label="Aylık Beklenen Kira Geliri", value="15.000 TL", delta="Ödeme Bekleniyor", delta_color="off")
            m3.metric(label="Sözleşme Durumu", value="Taslak Hazır", delta="E-Devlet Onayı Bekleniyor", delta_color="normal")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            c_sol, c_sag = st.columns([2,1])
            
            with c_sol:
                st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                st.subheader("🗓️ Aylık Kira Takip Çizelgesi")
                st.write("Kiracınızın ödemelerini buradan takip edebilir, zamanında yapılan ödemeleri onaylayarak kiracınızın ReferansEvim itibarını artırabilirsiniz.")
                
                # SİMÜLASYON TABLO
                st.markdown("""
                | Ay | Beklenen Tutar | Ödeme Durumu | Ev Sahibi Onayı |
                |---|---|---|---|
                | Ocak 2026 | 15.000 TL | 🟢 Ödendi | ✅ Onaylandı |
                | Şubat 2026 | 15.000 TL | 🟢 Ödendi | ✅ Onaylandı |
                | Mart 2026 | 15.000 TL | ⏳ Bekleniyor | 🔘 Onay Bekliyor |
                """)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Mart Ayı Ödemesini Onayla (Kiracının Puanını Artır)", use_container_width=True):
                    st.success("✅ Ödeme başarıyla onaylandı. Kiracının güvenilirlik puanına +0.1 eklendi.")
                st.markdown("</div>", unsafe_allow_html=True)

            with c_sag:
                st.markdown("<div class='dashboard-box'>", unsafe_allow_html=True)
                st.subheader("🤝 Sözleşme Modülü")
                st.info("E-Devlet veya manuel imza öncesi resmi sözleşme taslağınızı anında üretin.")
                with st.form("s_form"):
                    adres = st.text_input("Adres")
                    kira = st.number_input("Kira Tutarı (TL)", value=15000)
                    gun = st.text_input("Ödeme Günü")
                    s_uret = st.form_submit_button("📄 Taslak Üret", use_container_width=True)
                    if s_uret:
                        if adres and gun:
                            metin = resmi_sozlesme_metni_hazirla(k_isim, adres, kira, 15000, gun, "TÜFE")
                            st.success("Sözleşme Hazır!")
                            st.download_button("📥 İndir", metin, "sozlesme.txt", use_container_width=True)
                        else: st.error("Lütfen adres ve gün girin.")
                st.markdown("</div>", unsafe_allow_html=True)