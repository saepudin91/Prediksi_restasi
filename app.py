import pandas as pd
import pickle
import json
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.write("Secrets Keys:", list(st.secrets.keys()))

# Cek apakah GOOGLE_SHEETS_CREDENTIALS ada
if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
    try:
        credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
        creds = Credentials.from_service_account_info(credentials_dict)
        client = gspread.authorize(creds)

        # Akses Google Sheets
        SPREADSHEET_NAME = "Prediksi prestasi"
        sheet = client.open(SPREADSHEET_NAME).sheet1

        st.success("✅ Berhasil terhubung ke Google Sheets!")
    except Exception as e:
        st.error(f"❌ Gagal terhubung ke Google Sheets: {e}")
        sheet = None
else:
    st.error("GOOGLE_SHEETS_CREDENTIALS tidak ditemukan di Streamlit Secrets!")
    sheet = None

# Header tetap
HEADER = ["No", "Nama", "Jenis Kelamin", "Umur", "Kelas", 
          "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", 
          "Jenis Bullying", "Prediksi Prestasi"]

if sheet:
    try:
        existing_header = sheet.row_values(1)
        if not existing_header or existing_header != HEADER:
            sheet.clear()
            sheet.append_row(HEADER)
    except Exception as e:
        st.error(f"❌ Gagal memeriksa header Google Sheets: {e}")

# Load model regresi
try:
    with open("D:/prediksi/model_regresi.pkl", "rb") as f:
        model = pickle.load(f)
except Exception as e:
    st.error(f"❌ Gagal memuat model regresi: {e}")
    model = None

st.title("📊 Aplikasi Prediksi Prestasi Belajar")

# Fungsi mencari nomor urut yang tersedia
def get_next_available_number(sheet):
    try:
        data = sheet.get_all_values()
        if len(data) <= 1:
            return 1  # Jika hanya ada header, mulai dari 1

        # Ambil semua nomor yang ada
        existing_numbers = {int(row[0]) for row in data[1:] if row[0].isdigit()}

        # Cari nomor terkecil yang belum digunakan
        next_no = 1
        while next_no in existing_numbers:
            next_no += 1

        return next_no
    except Exception as e:
        st.error(f"❌ Gagal mencari nomor urut: {e}")
        return None

# --- 1. MODE INPUT MANUAL ---
mode = st.radio("Pilih mode input:", ("Input Manual", "Upload CSV"))

if mode == "Input Manual":
    nama = st.text_input("Nama Siswa").strip()
    jenis_kelamin = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"], index=None)
    umur = st.number_input("Umur", min_value=5, max_value=20, step=1)
    kelas = st.number_input("Kelas", min_value=1, max_value=12, step=1)

    jenis_bullying = st.selectbox("Jenis Bullying", ["Fisik", "Verbal", "Sosial", "Cyber", "Seksual"])
    bullying = st.slider("Tingkat Bullying", 1, 10, 5)
    sosial = st.slider("Dukungan Sosial", 1, 10, 5)
    mental = st.slider("Kesehatan Mental", 1, 10, 5)

    if st.button("Prediksi!") and model and sheet:
        if not nama:
            st.error("⚠ Nama siswa harus diisi!")
        elif jenis_kelamin is None:
            st.error("⚠ Jenis kelamin harus dipilih!")
        else:
            input_data = [[bullying, sosial, mental]]
            hasil_prediksi = model.predict(input_data)[0]
            st.success(f"✅ Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f}")

            # Ambil nomor urut yang tersedia
            next_no = get_next_available_number(sheet)

            if next_no is not None:
                new_row = [next_no, nama, jenis_kelamin, umur, kelas, bullying, sosial, mental, jenis_bullying, hasil_prediksi]
                sheet.append_row(new_row)
                st.info(f"📌 Hasil prediksi disimpan ke Google Sheets dengan No {next_no}!")

# --- 2. MODE UPLOAD CSV ---
elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

    if uploaded_file is not None and model and sheet:
        df_siswa = pd.read_csv(uploaded_file)

        # Pastikan format kolom benar
        required_columns = {"Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"}
        if not required_columns.issubset(df_siswa.columns):
            st.error("⚠ Format CSV tidak sesuai! Pastikan memiliki kolom yang benar.")
        else:
            # Normalisasi data agar format seragam
            df_siswa["Jenis Kelamin"] = df_siswa["Jenis Kelamin"].str.strip().str.lower().map({
                "l": "Laki-laki", "p": "Perempuan", "laki-laki": "Laki-laki", "perempuan": "Perempuan"
            })

            df_siswa["Jenis Bullying"] = df_siswa["Jenis Bullying"].str.strip().str.capitalize()

            # Prediksi
            X = df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]]
            df_siswa["Prediksi Prestasi"] = model.predict(X)

            st.subheader("📊 Hasil Prediksi")
            st.dataframe(df_siswa)

            # Tambahkan data ke Google Sheets
            for i, row in df_siswa.iterrows():
                new_row = [i + 1] + row.tolist()
                sheet.append_row(new_row)

            st.success("✅ Prediksi selesai! Hasil disimpan ke Google Sheets.")

# --- 3. ANALISIS JENIS BULLYING ---
st.subheader("📊 Analisis Jenis Bullying")
if sheet:
    try:
        data = sheet.get_all_values()
        df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)

        if not df_riwayat.empty and "Jenis Bullying" in df_riwayat.columns:
            bullying_counts = df_riwayat["Jenis Bullying"].value_counts()
            fig, ax = plt.subplots(figsize=(8, 6))
            bullying_counts.plot(kind="bar", ax=ax, color=['blue', 'red', 'green', 'purple', 'orange'])
            ax.set_title("Jumlah Kasus Berdasarkan Jenis Bullying")
            ax.set_xlabel("Jenis Bullying")
            ax.set_ylabel("Jumlah Kasus")
            ax.tick_params(axis="x", labelrotation=30)
            st.pyplot(fig)

            # Menampilkan informasi
            st.write(f"📌 Paling banyak: {bullying_counts.idxmax()} ({bullying_counts.max()} kasus)")
            st.write(f"📌 Paling sedikit: {bullying_counts.idxmin()} ({bullying_counts.min()} kasus)")
    except Exception as e:
        st.error(f"⚠ Gagal mengambil data: {e}")
