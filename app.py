import os
import json
import pickle
import base64
import streamlit as st
import gspread
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2 import service_account

# --- DEBUG: CEK APAKAH SECRETS ADA ---
if "gcp_service_account" not in st.secrets:
    st.error("⚠ Kredensial GCP tidak ditemukan di secrets.toml!")
    st.stop()

try:
    # Konversi secrets ke dictionary
    creds_dict = dict(st.secrets["gcp_service_account"])

    # --- DEBUG: CEK FORMAT JSON ---
    st.write("📌 Debug: Isi creds_dict setelah konversi")
    st.json(creds_dict)  # Pastikan formatnya sudah benar

    # Perbaiki private key
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    # --- KONFIGURASI GOOGLE CREDENTIALS ---
    SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    # --- HUBUNGKAN KE GOOGLE SHEETS ---
    client = gspread.authorize(creds)
    st.success("✅ Koneksi ke Google Sheets berhasil!")

except Exception as e:
    st.error(f"⚠ Terjadi kesalahan saat memuat kredensial: {e}")
    st.stop()

# --- GOOGLE SHEET CONFIG ---
SPREADSHEET_ID = "1abcDEFghIJklMnOPQRstuVWxyz"  # Ganti dengan ID Google Sheets yang benar
try:
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
except Exception as e:
    st.error(f"⚠ Tidak dapat mengakses Google Sheets: {e}")
    st.stop()

HEADER = ["No", "Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying", "Prediksi Prestasi"]
if not sheet.row_values(1):
    sheet.append_row(HEADER)

# --- DEBUG: CEK MODEL REGRESI ---
if "model_regresi" not in st.secrets:
    st.error("⚠ Model regresi tidak ditemukan di secrets.toml!")
    st.stop()

st.write("📌 Debug: Isi Base64 dari secrets")
st.text(st.secrets["model_regresi"]["model_base64"][:100] + "...")  # Tampilkan 100 karakter pertama
try:
    model_base64 = st.secrets["model_regresi"]["model_base64"]
    model_data = base64.b64decode(model_base64)
    model = pickle.loads(model_data)
    st.success("✅ Model regresi berhasil dimuat!")
except Exception as e:
    st.error(f"⚠ Model regresi tidak dapat dimuat: {e}")
    st.stop()

# --- UI STREAMLIT ---
st.title("📊 Aplikasi Prediksi Prestasi Belajar")
mode = st.radio("Pilih mode input:", ("Input Manual", "Upload CSV"))

def get_next_available_number(sheet):
    data = sheet.get_all_values()
    if len(data) <= 1:
        return 1
    existing_numbers = set(int(row[0]) for row in data[1:] if row[0].isdigit())
    next_no = 1
    while next_no in existing_numbers:
        next_no += 1
    return next_no

if mode == "Input Manual":
    nama = st.text_input("Nama Siswa").strip()
    jenis_kelamin = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"], index=None)
    umur = st.number_input("Umur", min_value=5, max_value=20, step=1)
    kelas = st.number_input("Kelas", min_value=1, max_value=12, step=1)

    jenis_bullying = st.selectbox("Jenis Bullying", ["Fisik", "Verbal", "Sosial", "Cyber", "Seksual"])
    bullying = st.slider("Tingkat Bullying", 1, 10, 5)
    sosial = st.slider("Dukungan Sosial", 1, 10, 5)
    mental = st.slider("Kesehatan Mental", 1, 10, 5)

    if st.button("🔍 Prediksi!"):
        if not nama:
            st.error("⚠ Nama siswa harus diisi!")
        elif jenis_kelamin is None:
            st.error("⚠ Jenis kelamin harus dipilih!")
        else:
            input_data = [[bullying, sosial, mental]]
            hasil_prediksi = model.predict(input_data)[0]
            st.success(f"📌 Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f}")

            next_no = get_next_available_number(sheet)
            new_row = [next_no, nama, jenis_kelamin, umur, kelas, bullying, sosial, mental, jenis_bullying, hasil_prediksi]
            sheet.append_row(new_row)

            st.info(f"✅ Hasil prediksi disimpan ke Google Sheets dengan No {next_no}!")

elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

    if uploaded_file is not None:
        df_siswa = pd.read_csv(uploaded_file)

        # Pastikan kolom yang diperlukan ada dalam DataFrame
        required_columns = ["Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"]
        if not set(required_columns).issubset(df_siswa.columns):
            st.error("⚠ Format CSV tidak sesuai! Pastikan semua kolom yang diperlukan ada.")
        else:
            # Normalisasi kolom
            df_siswa["Jenis Kelamin"] = df_siswa["Jenis Kelamin"].str.strip().str.lower().map({
                "l": "Laki-laki", "p": "Perempuan", "laki-laki": "Laki-laki", "perempuan": "Perempuan"
            })
            df_siswa["Jenis Bullying"] = df_siswa["Jenis Bullying"].str.strip().str.capitalize()

            # Buat data untuk prediksi
            X = df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]]
            df_siswa["Prediksi Prestasi"] = model.predict(X)

            st.subheader("Hasil Prediksi")
            st.dataframe(df_siswa)

            for i, row in df_siswa.iterrows():
                new_row = [i + 1, row["Nama"], row["Jenis Kelamin"], row["Umur"], row["Kelas"], 
                           row["Tingkat Bullying"], row["Dukungan Sosial"], row["Kesehatan Mental"], 
                           row["Jenis Bullying"], row["Prediksi Prestasi"]]
                sheet.append_row(new_row)

            st.success("✅ Prediksi selesai! Hasil disimpan ke Google Sheets.")

# --- TAMPILKAN RIWAYAT ---
st.subheader("📜 Riwayat Prediksi")

data = sheet.get_all_values()
df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)

if not df_riwayat.empty:
    st.dataframe(df_riwayat)

# --- ANALISIS JENIS BULLYING ---
st.subheader("📊 Analisis Jenis Bullying")
if not df_riwayat.empty and "Jenis Bullying" in df_riwayat.columns:
    bullying_counts = df_riwayat["Jenis Bullying"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 6))
    bullying_counts.plot(kind="bar", ax=ax, color=['blue', 'red', 'green', 'purple', 'orange'])
    ax.set_title("Jumlah Kasus Berdasarkan Jenis Bullying")
    st.pyplot(fig)
