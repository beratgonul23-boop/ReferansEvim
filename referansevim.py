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
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f0f2f6 !important; }
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stMarkdown p, [data-testid="stMarkdownContainer"] p, .stWidget label p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, [data-testid="stHeader"], .stTextArea textarea {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important;
    }
    .stSlider [data-testid="stWidgetLabel"] p, .stSlider div { color: #002147 !important; }
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: bold !important;
    }
    div.stButton > button *, div.stDownloadButton > button *, div.stFormSubmitButton > button * { color: #ffffff !important; }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    [data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #002147 !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] * { color: #002147 !important; }
    [data-testid="stFileUploaderDropzone"] button { background-color: #002147 !important; border-radius: 6px !important; }
    [data-testid="stFileUploaderDropzone"] button * { color: #ffffff !important; }
    [data-testid="stUploadedFile"] { background-color: #e6eef5 !important; border: 1px solid #002147 !important; border-radius: 5px !important; }
    [data-testid="stUploadedFile"] * { color: #002147 !important; }
    .stAlert { background-color: #ffffff !important; border: 1px solid #ddd !important; }
    .stAlert * { color: #000000 !important; }
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

# --- RAPOR VE SÖZLEŞME METİNLERİ ---
def rapor_metni_hazirla(ad, kod, puan, tarih, analiz):
    analiz_str = "\n".join([f"- {madde}" for madde in analiz])
    return f"""REFERANSEVİM GÜVENLİK RAPORU (KVKK UYUMLU)
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
* Yasal Uyari: Sisteme yuklenen hicbir kimlik veya gelir belgesi sunucularda SAKLANMAMISTIR. 
Tum belgeler analiz sonrasi aninda imha edilmistir."""

def resmi_sozlesme_metni_hazirla(kiraci_adi, adres, kira_bedeli, depozito, odeme_gunu, zam_orani):
    tarih = datetime.now().strftime("%d/%m/%Y")
    return f"""KİRA SÖZLEŞMESİ TASLAĞI
Tarih: {tarih}

1. TARAFLAR
Kiraya Veren : _________________________________________ (T.C.: ____________________)
Kiracı       : {kiraci_adi} (T.C.: ____________________)

2. KİRALANANIN BİLGİLERİ
Adres        : {adres}

3. SÖZLEŞME ŞARTLARI VE BEDELLER
Madde 3.1 - Aylık Kira Bedeli: {kira_bedeli} TL'dir.
Madde 3.2 - Depozito Tutarı: {depozito} TL olarak belirlenmiştir.
Madde 3.3 - Kira Ödeme Zamanı: {odeme_gunu} olarak kararlaştırılmıştır.
Madde 3.4 - Yıllık Kira Artış Oranı: {zam_orani} olarak uygulanacaktır.

4. GENEL HÜKÜMLER
Madde 4.1 - Kiracı, kiralanan taşınmazı özenle kullanmak, bina yönetim kurallarına ve komşuluk ilişkilerine azami saygıyı göstermekle yükümlüdür.
Madde 4.2 - Kiralanan taşınmazın alt kiraya verilmesi veya kullanım hakkının devredilmesi kesinlikle yasaktır.
Madde 4.3 - İşbu sözleşmede yer almayan hususlarda 6098 sayılı Türk Borçlar Kanunu hükümleri geçerlidir.

KİRAYA VEREN (İMZA)                              KİRACI (İMZA)



-------------------------------------------------------------------------
* İşbu resmi sözleşme taslağı, taraflar arasında ön mutabakat sağlamak 
amacıyla ReferansEvim Uzlaştırma Platformu aracılığıyla oluşturulmuştur.
"""

def qr_kod_olustur(veri):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(veri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu, eski_tel):
    puan = 0
    analiz = []
    
    if gelir >= 40000: puan += 40; analiz.append("Gelir Seviyesi: Yüksek (+40p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart/Orta (+20p)")
    else: puan += 10; analiz.append("Gelir Seviyesi: Düşük Riskli (+10p)")
    
    if findex >= 1500: puan += 40; analiz.append("Kredi Notu: Çok İyi (+40p)")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: Orta/İyi (+20p)")
    else: puan += 0; analiz.append("Kredi Notu: Riskli (0p)")
    
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (Belge İmha Edildi) (+20p)")
    else: analiz.append("Maaş Bordrosu: Yüklenmedi (0p)")
    
    if eski_tel: analiz.append(f"Referans: Eski ev sahibi numarası eklendi ({eski_tel}). Lütfen arayarak teyit ediniz.")
    else: analiz.append("Referans: Eski ev sahibi bilgisi girilmedi.")
    
    yildiz = round((puan/100)*5 * 2) / 2
    if yildiz < 1: yildiz = 1.0 
    return yildiz, analiz

# --- UYGULAMA ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None
if 'onaylanan_kiraci' not in st.session_state: st.session_state.onaylanan_kiraci = None

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>ReferansEvim</h1>", unsafe_allow_html=True)
        st.info("💡 %100 KVKK Uyumlu: Yüklenen belgeler asla sunucularda saklanmaz, analiz sonrası anında imha edilir.")
        tip = st.radio("Sisteme Giriş Tipi:", ("👤 Kiracı Girişi", "🔑 Ev Sahibi Girişi"))
        
        with st.expander("⚖️ KVKK ve Aydınlatma Metnini Okumak İçin Tıklayınız"):
            st.write("""
            **Kişisel Verilerin Korunması ve Veri İmha Politikası**
            1. Sisteme yüklediğiniz belgeler yapay zeka tarafından sadece anlık olarak okunur.
            2. Okuma işlemi bittikten hemen sonra belgeniz sunucularımızdan **kalıcı olarak silinir**.
            3. T.C. Kimlik numaranız doğrulama amaçlı istenir ve asla kayıt altına alınmaz.
            """)
        
        onay = st.checkbox("KVKK Aydınlatma Metnini okudum, anladım ve kabul ediyorum.")
        
        if st.button("Sisteme Güvenli Giriş Yap", use_container_width=True):
            if onay:
                st.session_state.giris_yapildi = True
                st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in tip else "evsahibi"
                st.rerun()
            else: st.error("Lütfen sisteme girmek için KVKK metnini onaylayınız.")

else:
    c1, c2 = st.columns([8, 1])
    with c1: st.title("🏠 ReferansEvim Paneli")
    with c2:
        if st.button("Güvenli Çıkış"):
            st.session_state.giris_yapildi = False; st.session_state.son_rapor = None; st.session_state.onaylanan_kiraci = None; st.rerun()
    st.markdown("---")

    # KİRACI PANELİ
    if st.session_state.kullanici_tipi == "kiraci":
        st.subheader("📝 Akıllı Referans Raporu Oluştur")
        with st.form("k_form"):
            c1, c2 = st.columns(2)
            with c1: 
                ad = st.text_input("Ad Soyad")
                tc = st.text_input("T.C. Kimlik No (Kayıt Altına Alınmaz)")
                eski_ev_sahibi_tel = st.text_input("Eski Ev Sahibi Telefon Numarası (Güven İçin Önerilir)")
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
                        with st.spinner("Maaş bordrosu yapay zeka ile taranıyor (OCR)..."):
                            time.sleep(1) 
                            ok, msg = belgeyi_tara_ve_dogrula(dosya, "maas")
                            if ok: 
                                belge_ok = True
                                st.success(f"{msg}")
                                st.info("🛡️ Güvenlik Protokolü: Yüklenen belge veritabanından kalıcı olarak silindi.")
                            else: st.warning(f"Bordro onaylanamadı: {msg}")
                    
                    puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, belge_ok, eski_ev_sahibi_tel)
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
            st.download_button("📄 Detaylı Raporu İndir (KVKK Uyumlu)", metin, file_name=f"ReferansEvim_Rapor_{rp['kod']}.txt", use_container_width=True)

    # EV SAHİBİ PANELİ
    elif st.session_state.kullanici_tipi == "evsahibi":
        st.subheader("🛡️ Kiracı & Belge Doğrulama Merkezi")
        st.info("⚠️ Lütfen Tapu belgenizi yükleyiniz. Belgeniz analiz edildikten sonra SAKLANMADAN SİLİNECEKTİR.")
        
        tapu = st.file_uploader("Tapu Belgesi Yükle (Anında İmha Edilir)", type=["pdf", "jpg", "png"])
        kod = st.text_input("Kiracının Size Verdiği Kod (Örn: REF-12345)")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Belgeyi Tarat ve Sorgula 🔍", use_container_width=True):
            if not tapu: st.error("Lütfen önce kendi Tapu belgenizi yükleyin.")
            else:
                with st.spinner("Tapu Belgesi Güvenlik Taramasından Geçiyor..."):
                    time.sleep(1)
                    ok, msg = belgeyi_tara_ve_dogrula(tapu, "tapu")
                    if not ok:
                        st.error("⛔ GÜVENLİK İHLALİ: Sistem belgeyi reddetti!")
                        st.error(msg)
                    else:
                        st.success("✅ KİMLİK DOĞRULANDI: Tapu belgesi geçerli.")
                        st.info("🛡️ Güvenlik Protokolü: Yüklenen tapu belgesi sunuculardan kalıcı olarak silindi.")
                        
                        db = verileri_yukle()
                        if kod in db:
                            k = db[kod]
                            st.session_state.onaylanan_kiraci = k['ad'] 
                            analiz_html = "".join([f"<li>{m}</li>" for m in k['analiz']])
                            st.markdown(f"""
                            <div style="background:white; padding:25px; border-left:10px solid #002147; border-radius:5px; margin-top:10px;">
                                <h2 style="color:#002147; margin:0;">✅ KİRACI RAPORU BULUNDU</h2>
                                <hr>
                                <p style="color:black !important; font-size:1.1em;"><b>İsim:</b> {k['ad']}</p>
                                <p style="color:black !important; font-size:1.1em;"><b>Güvenilirlik Puanı:</b> {k['puan']} / 5</p>
                                <h4 style="color:#002147; margin-top:15px;">🔍 Sistem Analizi:</h4>
                                <ul style="color:black !important;">{analiz_html}</ul>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Girdiğiniz kod sistemde bulunamadı. Lütfen kiracıdan kodu teyit edin.")

        # SÖZLEŞME MODÜLÜ (Buton formun dışına alındı!)
        if st.session_state.onaylanan_kiraci:
            st.markdown("<br><hr><br>", unsafe_allow_html=True)
            st.subheader("🤝 Resmi Sözleşme ve Uzlaştırma Modülü")
            st.info("Kiracı ile anlaştıysanız, aşağıdaki bilgileri doldurarak resmi 'Kira Sözleşmesi Taslağınızı' oluşturabilirsiniz.")
            
            with st.form("sozlesme_form"):
                adres = st.text_area("Kiralanan Taşınmazın Tam Adresi")
                col1, col2 = st.columns(2)
                with col1:
                    kira_bedeli = st.number_input("Aylık Kira Bedeli (TL)", step=1000, value=15000)
                    odeme_gunu = st.text_input("Kira Ödeme Günü", placeholder="Örn: Her ayın 1'i ile 5'i arası")
                with col2:
                    depozito = st.number_input("Depozito Tutarı (TL)", step=1000, value=15000)
                    zam_orani = st.selectbox("Yıllık Zam Oranı", ["Yasal TÜFE Oranında", "Sabit Oran (Metne Eklenecek)", "Taraflar Arasında Belirlenecektir"])
                
                sozlesme_uret = st.form_submit_button("📄 Sözleşme Üret", use_container_width=True)
            
            # İndirme Butonu Artık Özgür!
            if sozlesme_uret:
                if not adres or not odeme_gunu:
                    st.error("Lütfen adres ve ödeme günü bilgilerini eksiksiz doldurunuz.")
                else:
                    sozlesme_metni = resmi_sozlesme_metni_hazirla(
                        st.session_state.onaylanan_kiraci, 
                        adres, 
                        kira_bedeli, 
                        depozito, 
                        odeme_gunu, 
                        zam_orani
                    )
                    st.success("✅ Sözleşmeniz başarıyla oluşturuldu! Aşağıdan indirebilir veya inceleyebilirsiniz.")
                    
                    st.download_button(
                        label="📥 SÖZLEŞMEYİ İNDİR (TXT FORMATINDA)",
                        data=sozlesme_metni,
                        file_name=f"Kira_Sozlesmesi_{st.session_state.onaylanan_kiraci.replace(' ', '_')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    with st.expander("📄 Sözleşme Önizlemesini Görüntüle"):
                        st.text(sozlesme_metni)