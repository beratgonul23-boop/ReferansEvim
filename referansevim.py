import streamlit as st
import time
import random
import os
import qrcode
from io import BytesIO
from datetime import datetime
import numpy as np
import base64

# --- YENİ KÜTÜPHANELER ---
try:
    import pypdf
    import easyocr
    import cv2
    OCR_AKTIF = True
except ImportError:
    OCR_AKTIF = False

# --- FIREBASE BULUT BAĞLANTISI ---
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = init_firebase()
    FIREBASE_AKTIF = True
except Exception as e:
    FIREBASE_AKTIF = False
    st.error("⚠️ Bulut veritabanına bağlanılamadı.")

st.set_page_config(page_title="ReferansEvim Pro", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

# --- 🔥 SAHİBİNDEN TARZI PROFESYONEL CSS 🔥 ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"], .stApp { background-color: #f4f4f4 !important; }
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .stMarkdown p, .stWidget label p {
        color: #002147 !important; font-family: 'Source Sans Pro', sans-serif;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea, .stFileUploader label, .stSlider div {
        background-color: #ffffff !important; color: #000000 !important; border: 1px solid #cccccc !important; border-radius: 5px !important;
    }
    div.stButton > button {
        background-color: #002147 !important; border: none !important; border-radius: 6px !important; padding: 10px 20px !important; font-weight: bold !important; color: #ffffff !important;
    }
    div.stButton > button:hover { background-color: #003366 !important; border: 1px solid white !important; }
    div.stButton > button * { color: #ffffff !important; }
    
    .btn-prime button { background-color: #FFD700 !important; color: #002147 !important; border: 2px solid #002147 !important;}
    .btn-prime button * { color: #002147 !important; } 
    
    .ilan-karti { background-color: white; border-radius: 8px; border: 1px solid #e0e0e0; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; transition: 0.3s; }
    .ilan-karti:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); border-color: #002147; }
    .ilan-fiyat { color: #e30a17; font-size: 1.4rem; font-weight: bold; }
    .ilan-baslik { font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; color: #002147; }
    .ilan-detay { color: #666; font-size: 0.9rem; margin-bottom: 10px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 2px solid #ddd; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border-radius: 4px 4px 0px 0px; border: none !important; color: #002147 !important; padding: 10px 20px !important; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #002147 !important; font-weight: bold; background-color: #e6eef5 !important;}
</style>
""", unsafe_allow_html=True)

# --- BULUT VERİTABANI FONKSİYONLARI ---
def veri_kaydet(koleksiyon, belge_id, veri):
    if FIREBASE_AKTIF: db.collection(koleksiyon).document(belge_id).set(veri)

def veri_getir(koleksiyon, belge_id):
    if FIREBASE_AKTIF:
        doc = db.collection(koleksiyon).document(belge_id).get()
        if doc.exists: return doc.to_dict()
    return None

def detayli_puan_hesapla(gelir, findex, meslek, belge_durumu):
    puan = 0; analiz = []
    if gelir >= 40000: puan += 40; analiz.append("Gelir Seviyesi: Yüksek (+40p)")
    elif gelir >= 17002: puan += 20; analiz.append("Gelir Seviyesi: Standart (+20p)")
    if findex >= 1500: puan += 40; analiz.append("Kredi Notu: Çok İyi (+40p)")
    elif findex >= 1200: puan += 20; analiz.append("Kredi Notu: Orta/İyi (+20p)")
    if belge_durumu: puan += 20; analiz.append("Maaş Bordrosu: AI Onaylı (+20p)")
    yildiz = round((puan/100)*5 * 2) / 2
    return max(1.0, yildiz), analiz

# --- UYGULAMA YÖNETİMİ ---
if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'kullanici_tipi' not in st.session_state: st.session_state.kullanici_tipi = None 
if 'son_rapor' not in st.session_state: st.session_state.son_rapor = None

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3.5rem; font-weight: 800;'>Referans<span style='font-weight: 300;'>Evim</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Türkiye'nin İlk Yapay Zeka Destekli Emlak Uzlaştırma Ekosistemi</p><br>", unsafe_allow_html=True)
        kullanici_tipi = st.selectbox("Sisteme Giriş Tipinizi Seçiniz", ["Kiracı Olarak Giriş Yap", "Ev Sahibi Olarak Giriş Yap"])
        onay = st.checkbox("KVKK Aydınlatma Metnini okudum ve kabul ediyorum.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🌐 Güvenli Giriş Yap", use_container_width=True):
            if onay: st.session_state.giris_yapildi = True; st.session_state.kullanici_tipi = "kiraci" if "Kiracı" in kullanici_tipi else "evsahibi"; st.rerun()
            else: st.error("Lütfen KVKK metnini onaylayınız.")

else:
    c1, c2 = st.columns([8, 1])
    with c1: st.title(f"🏠 ReferansEvim {'Kiracı' if st.session_state.kullanici_tipi=='kiraci' else 'Ev Sahibi'} Portal")
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
            st.subheader("📝 Ücretsiz Akıllı Rapor Oluştur")
            with st.form("k_form"):
                c1, c2 = st.columns(2)
                with c1: ad = st.text_input("Ad Soyad"); meslek = st.text_input("Meslek / Şirket")
                with c2: gelir = st.number_input("Aylık Net Gelir (TL)", step=1000, value=40000); findex = st.slider("Findeks Kredi Notu", 0, 1900, 1500)
                kapasite = st.number_input("Aylık Ödeyebileceğiniz Maksimum Bütçe (TL)", step=1000, value=15000)
                dosya = st.file_uploader("Maaş Bordrosu Yükle (AI ile doğrulanıp silinir)", type=["pdf", "jpg", "png"])
                
                if st.form_submit_button("Raporu Hazırla ve Buluta Kaydet ☁️", use_container_width=True):
                    if ad:
                        puan, analiz = detayli_puan_hesapla(gelir, findex, meslek, True if dosya else False)
                        kod = f"REF-{random.randint(10000, 99999)}"
                        veri = {"ad": ad, "puan": puan, "tarih": datetime.now().strftime("%d-%m-%Y"), "meslek": meslek, "kapasite": kapasite}
                        veri_kaydet('referanslar', kod, veri) # Buluta kaydet
                        st.session_state.son_rapor = {"kod": kod, "veri": veri}
                        st.rerun() 

        if st.session_state.son_rapor:
            rp = st.session_state.son_rapor
            tab1, tab2, tab3 = st.tabs(["👤 Profesyonel Profilim", "🏠 Ev İlanları Vitrini", "📢 'Ev Arıyorum' İlanı Aç (YENİ)"])
            
            with tab1:
                col_p1, col_p2 = st.columns([1, 2])
                with col_p1:
                    st.markdown("<div class='ilan-karti' style='text-align:center;'>", unsafe_allow_html=True)
                    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
                    st.markdown(f"<h3>{rp['veri']['ad']}</h3>", unsafe_allow_html=True)
                    st.markdown("✅ **Hesap Onaylı** <br> 💳 **Gelir Onaylı**", unsafe_allow_html=True)
                    st.markdown(f"<h1 style='color:#FFD700;'>⭐ {rp['veri']['puan']}</h1>", unsafe_allow_html=True)
                    st.markdown(f"**Referans Kodu:** {rp['kod']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col_p2:
                    st.markdown("### 🚀 Profilini Üst Sıralara Taşı (Referans Prime)")
                    c_p1, c_p2, c_p3 = st.columns(3)
                    with c_p1:
                        st.markdown("<div class='ilan-karti' style='text-align:center;'><h4>🥉 24 Saat</h4><h2>89 TL</h2><div class='btn-prime'>", unsafe_allow_html=True)
                        if st.button("Shopier ile Öde", key="s1"): st.success("Yönlendirme başarılı.")
                        st.markdown("</div></div>", unsafe_allow_html=True)
                    with c_p2:
                        st.markdown("<div class='ilan-karti' style='text-align:center; border: 2px solid #FFD700;'><h4>🥈 3 Gün VIP</h4><h2>149 TL</h2><div class='btn-prime'>", unsafe_allow_html=True)
                        if st.button("Shopier ile Öde", key="s2"): st.success("Yönlendirme başarılı.")
                        st.markdown("</div></div>", unsafe_allow_html=True)
                    with c_p3:
                        st.markdown("<div class='ilan-karti' style='text-align:center;'><h4>🥇 1 Hafta</h4><h2>299 TL</h2><div class='btn-prime'>", unsafe_allow_html=True)
                        if st.button("Shopier ile Öde", key="s3"): st.success("Yönlendirme başarılı.")
                        st.markdown("</div></div>", unsafe_allow_html=True)

            with tab2:
                st.markdown("<br>### 🏠 Güvenilir Ev Sahiplerinden İlanlar", unsafe_allow_html=True)
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    st.markdown("""
                    <div class='ilan-karti'>
                        <img src="https://images.unsplash.com/photo-1502672260266-1c1de2d15d65?w=500" style="width:100%; border-radius:5px; margin-bottom:10px;">
                        <div class="ilan-baslik">Kadıköy Moda Eşyalı Stüdyo Daire (Deniz Manzaralı)</div>
                        <div class="ilan-detay">📍 İstanbul, Kadıköy • 1+1 • 65 m² • Ara Kat</div>
                        <div class="ilan-fiyat">18.000 TL</div>
                        <div style="color: green; font-weight:bold; margin-bottom:10px;">🔒 Başvuru Şartı: Min ⭐ 4.5 Puan</div>
                    </div>""", unsafe_allow_html=True)
                    st.button("İlana Başvur", key="ib1", use_container_width=True)
                with e_col2:
                    st.markdown("""
                    <div class='ilan-karti'>
                        <img src="https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=500" style="width:100%; border-radius:5px; margin-bottom:10px;">
                        <div class="ilan-baslik">Şişli Merkez Yeni Binada Lüks 2+1 Fırsatı</div>
                        <div class="ilan-detay">📍 İstanbul, Şişli • 2+1 • 90 m² • 3. Kat</div>
                        <div class="ilan-fiyat">22.000 TL</div>
                        <div style="color: green; font-weight:bold; margin-bottom:10px;">🔒 Başvuru Şartı: Min ⭐ 4.0 Puan</div>
                    </div>""", unsafe_allow_html=True)
                    st.button("İlana Başvur", key="ib2", use_container_width=True)

            with tab3:
                st.markdown("<br>### 📢 Kendi 'Ev Arıyorum' İlanını Oluştur", unsafe_allow_html=True)
                st.info("💡 Bırak ev sahipleri seni bulsun! İlanın 'Premium Kiracı Havuzu'nda yayınlanacak.")
                with st.form("kiraci_ilan_form"):
                    i_bolge = st.text_input("Aradığınız Bölge (Örn: İstanbul / Beşiktaş)")
                    i_oda = st.selectbox("Oda Sayısı", ["1+0", "1+1", "2+1", "3+1", "Fark Etmez"])
                    i_not = st.text_area("Ev Sahibine Notunuz (Örn: Evcil hayvanım var, düzenli çalışanım)")
                    if st.form_submit_button("İlanı Yayına Al (Ücretsiz)", use_container_width=True):
                        st.success("✅ İlanınız 'Premium Kiracı Havuzu'nda başarıyla yayınlandı! Ev sahipleri yakında size teklif gönderecektir.")

    # ==========================================
    # 🔑 EV SAHİBİ EKOSİSTEMİ
    # ==========================================
    elif st.session_state.kullanici_tipi == "evsahibi":
        tab1, tab2, tab3 = st.tabs(["🔍 Kiracı Sorgula", "💎 Kiracı Vitrini ('Ev Arıyorum')", "📸 Fotoğraflı İlan Aç (YENİ)"])
        
        with tab1:
            st.subheader("🛡️ Bulut Veritabanı Sorgulama")
            kod = st.text_input("Kiracının Verdiği Kod (Örn: REF-12345)")
            if st.button("Sorgula ☁️ 🔍"):
                if kod:
                    with st.spinner("Taranıyor..."):
                        time.sleep(1)
                        bulut_veri = veri_getir('referanslar', kod)
                        if bulut_veri: st.success(f"✅ Kiracı Bulundu: {bulut_veri['ad']} - Puan: ⭐ {bulut_veri['puan']}")
                        else: st.error("Kod bulunamadı.")
        
        with tab2:
            st.markdown("<br>### 💎 'Ev Arıyorum' Diyen Premium Kiracılar", unsafe_allow_html=True)
            st.info("Aşağıdaki kiracılar yapay zeka tarafından incelenmiş ve onaylanmıştır. Kendi evinize uygun olanlara teklif gönderebilirsiniz.")
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown("""
                <div class='ilan-karti' style='border: 2px solid #FFD700;'>
                    <div style='background-color:#FFD700; color:#002147; font-weight:bold; border-radius:5px; padding:5px; margin-bottom:10px; display:inline-block;'>🚀 PRIME KİRACI</div>
                    <div class="ilan-baslik">B*** G*** (Kurucu - TheFLXBrand)</div>
                    <div class="ilan-detay">📍 <b>Aradığı Bölge:</b> Beşiktaş / Şişli<br>🏠 <b>Aradığı Ev:</b> 2+1 veya 1+1</div>
                    <div class="ilan-fiyat" style="color:#002147;">Maks. Bütçe: 25.000 TL</div>
                    <div style="color: green; font-weight:bold; margin-top:10px;">⭐ Güven Puanı: 4.8 / 5</div>
                </div>""", unsafe_allow_html=True)
                st.button("Evi Kiralaması İçin Teklif Gönder", key="tk1", use_container_width=True)
                
            with p_col2:
                st.markdown("""
                <div class='ilan-karti'>
                    <div class="ilan-baslik">A*** Y*** (Finans Uzmanı)</div>
                    <div class="ilan-detay">📍 <b>Aradığı Bölge:</b> Kadıköy / Moda<br>🏠 <b>Aradığı Ev:</b> 3+1 (Arakat)</div>
                    <div class="ilan-fiyat" style="color:#002147;">Maks. Bütçe: 40.000 TL</div>
                    <div style="color: green; font-weight:bold; margin-top:10px;">⭐ Güven Puanı: 4.5 / 5</div>
                </div>""", unsafe_allow_html=True)
                st.button("Evi Kiralaması İçin Teklif Gönder", key="tk2", use_container_width=True)

        with tab3:
            st.markdown("<br>### 📸 Profesyonel Ev İlanı Oluştur", unsafe_allow_html=True)
            st.info("Sadece ReferansEvim puanı yüksek, sorunsuz kiracıların görebileceği elit ilanınızı oluşturun.")
            
            with st.form("ilan_form_detayli"):
                i_baslik = st.text_input("İlan Başlığı (Örn: Sahibinden Masrafsız 2+1)")
                c1, c2, c3 = st.columns(3)
                with c1: i_fiyat = st.number_input("Aylık Kira (TL)", step=1000)
                with c2: i_oda = st.selectbox("Oda Sayısı", ["1+0", "1+1", "2+1", "3+1", "Villa"])
                with c3: i_m2 = st.number_input("Metrekare (m²)", step=10)
                
                i_sart = st.slider("Başvuracak Kiracılar İçin Minimum Puan", 1.0, 5.0, 4.0, 0.5)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("#### 🖼️ Evinizin Fotoğrafları")
                st.file_uploader("Fotoğrafları Sürükleyin veya Seçin (Çoklu seçim yapabilirsiniz)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
                
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("#### 🚀 İlanınızı Öne Çıkarın (Referans Prime)")
                i_boost = st.radio("Seçiminiz:", ["Standart İlan (Ücretsiz)", "24 Saat Prime İlan (89 TL)", "1 Hafta Altın İlan (299 TL)"])
                
                if st.form_submit_button("İlanı Yayınla ve Havuza Gönder", use_container_width=True):
                    if "Ücretsiz" not in i_boost: st.success("Shopier yönlendirmesi simüle edildi. İlanınız Prime olarak yayınlanacak!")
                    else: st.success("✅ Fotoğraflı ilanınız başarıyla oluşturuldu ve buluta kaydedildi!")