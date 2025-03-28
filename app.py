import pandas as pd
import pickle
import json
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURASI GOOGLE SHEETS ---
credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])

# Load credentials
if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
    json_credentials = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
else:
    st.error("GOOGLE_SHEETS_CREDENTIALS tidak ditemukan di Streamlit Secrets!")
# Buat credential dari JSON
creds = Credentials.from_service_account_info(credentials_dict)
# Nama spreadsheet
SPREADSHEET_NAME = "Prediksi prestasi"
sheet = client.open(SPREADSHEET_NAME).sheet1

# Header tetap
HEADER = ["No", "Nama", "Jenis Kelamin", "Umur", "Kelas", 
          "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", 
          "Jenis Bullying", "Prediksi Prestasi"]

if not sheet.row_values(1):  # Jika kosong, tambahkan header
    sheet.append_row(HEADER)

# Load model regresi
with open("D:/prediksi/model_regresi.pkl", "rb") as f:
    model = pickle.load(f)

st.title("Aplikasi Prediksi Prestasi Belajar")

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

# Fungsi mencari nomor yang belum digunakan
def get_next_available_number(sheet):
    data = sheet.get_all_values()
    if len(data) <= 1:
        return 1  # Jika hanya ada header, mulai dari 1

    # Ambil semua nomor yang ada
    existing_numbers = set(int(row[0]) for row in data[1:] if row[0].isdigit())

    # Cari nomor terkecil yang belum digunakan
    next_no = 1
    while next_no in existing_numbers:
        next_no += 1

    return next_no

# Menggunakan nomor urut tetap dan menyisipkan di tempat yang sesuai
if st.button("Prediksi!"):
    if not nama:
        st.error("Nama siswa harus diisi!")
    elif jenis_kelamin is None:
        st.error("Jenis kelamin harus dipilih!")
    else:
        input_data = [[bullying, sosial, mental]]
        hasil_prediksi = model.predict(input_data)[0]
        st.success(f"Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f}")

        # Ambil nomor urut yang tersedia
        next_no = get_next_available_number(sheet)

        new_row = [next_no, nama, jenis_kelamin, umur, kelas, bullying, sosial, mental, jenis_bullying, hasil_prediksi]

        # Sisipkan data di posisi yang sesuai
        sheet.append_row(new_row)

        st.info(f"Hasil prediksi disimpan ke Google Sheets dengan No {next_no}!")

# --- 2. MODE UPLOAD CSV ---
elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

    if uploaded_file is not None:
        df_siswa = pd.read_csv(uploaded_file)

        # Pastikan format kolom benar
        if not {"Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", "Jenis Kelamin"}.issubset(df_siswa.columns):
            st.error("Format CSV tidak sesuai! Pastikan memiliki kolom yang benar.")
        else:
            # Normalisasi data agar format seragam
            df_siswa["Jenis Kelamin"] = df_siswa["Jenis Kelamin"].str.strip().str.lower().map({
                "l": "Laki-laki", "p": "Perempuan", "laki-laki": "Laki-laki", "perempuan": "Perempuan"
            })

            df_siswa["Jenis Bullying"] = df_siswa["Jenis Bullying"].str.strip().str.capitalize()

            # Prediksi
            X = df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]]
            df_siswa["Prediksi Prestasi"] = model.predict(X)

            st.subheader("Hasil Prediksi")
            st.dataframe(df_siswa)

            # Tambahkan data ke Google Sheets
            for i, row in df_siswa.iterrows():
                new_row = [i + 1, row["Nama"], row["Jenis Kelamin"], row["Umur"], row["Kelas"], 
                           row["Tingkat Bullying"], row["Dukungan Sosial"], row["Kesehatan Mental"], 
                           row["Jenis Bullying"], row["Prediksi Prestasi"]]
                sheet.append_row(new_row)

            st.success("Prediksi selesai! Hasil disimpan ke Google Sheets.")


            # --- 3. TAMPILKAN & HAPUS RIWAYAT ---
st.subheader("Riwayat Prediksi")

# Ambil data terbaru dari Google Sheets
data = sheet.get_all_values()

if len(data) > 1:
    df_riwayat = pd.DataFrame(data[1:], columns=HEADER)  
else:
    df_riwayat = pd.DataFrame(columns=HEADER)

if not df_riwayat.empty:
    st.dataframe(df_riwayat)

    # Hapus Seluruh Riwayat
    if st.button("Hapus Semua Riwayat"):
        sheet.clear()
        sheet.append_row(HEADER)
        st.warning("Seluruh riwayat prediksi telah dihapus!")
        st.rerun()

    # Hapus Data Tertentu
    if len(df_riwayat) > 0:
        nama_hapus = st.selectbox("Pilih Nama yang Akan Dihapus", df_riwayat["Nama"].unique())
        if st.button("Hapus Data Ini"):
            df_riwayat = df_riwayat[df_riwayat["Nama"] != nama_hapus]

            # Simpan ulang data ke Google Sheets setelah penghapusan
            sheet.clear()
            sheet.append_row(HEADER)
            for i, row in df_riwayat.iterrows():
                sheet.append_row(row.tolist())

            st.warning(f"Data untuk {nama_hapus} telah dihapus!")
            st.rerun()
else:
    st.write("Belum ada riwayat prediksi.")


# --- 3. ANALISIS JENIS BULLYING ---
st.subheader("📊 Analisis Jenis Bullying")

# Ambil data terbaru dari Google Sheets
data = sheet.get_all_values()

if len(data) > 1:
    df_riwayat = pd.DataFrame(data[1:], columns=HEADER)  
else:
    df_riwayat = pd.DataFrame(columns=HEADER)

if not df_riwayat.empty and "Jenis Bullying" in df_riwayat.columns:
    bullying_counts = df_riwayat["Jenis Bullying"].value_counts()

    # Buat grafik
    fig, ax = plt.subplots(figsize=(8, 6))
    bullying_counts.plot(kind="bar", ax=ax, color=['blue', 'red', 'green', 'purple', 'orange'])
    ax.set_title("Jumlah Kasus Berdasarkan Jenis Bullying")
    ax.set_xlabel("Jenis Bullying")
    ax.set_ylabel("Jumlah Kasus")
    ax.tick_params(axis="x", labelrotation=30)
    st.pyplot(fig)

    # Simpan grafik ke dalam buffer sebagai PNG
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", bbox_inches="tight")
    img_buffer.seek(0)

    # Tombol Download Grafik
    st.download_button(
        label="📥 Download Grafik",
        data=img_buffer,
        file_name="grafik_bullying.png",
        mime="image/png"
    )

    # Tampilkan informasi bullying terbanyak dan tersedikit
    if not bullying_counts.empty:
        st.write(f"📌 Jenis bullying yang paling banyak terjadi: {bullying_counts.idxmax()} ({bullying_counts.max()} kasus)")
        st.write(f"📌 Jenis bullying yang paling sedikit terjadi: {bullying_counts.idxmin()} ({bullying_counts.min()} kasus)")
else:
    st.write("⚠ Tidak ada data bullying untuk dianalisis.")

# --- 4. DOWNLOAD RIWAYAT ---
if not df_riwayat.empty:
    csv = df_riwayat.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Riwayat Prediksi", data=csv, file_name="riwayat_prediksi.csv", mime="text/csv")
