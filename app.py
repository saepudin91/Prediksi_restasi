import pandas as pd
import pickle
import json
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials


if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
    try:
        # Load kredensial dengan cara yang benar
        credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(credentials_dict)
        st.success("Kredensial berhasil dimuat!")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat kredensial: {e}")
else:
    st.error("GOOGLE_SHEETS_CREDENTIALS tidak ditemukan di secrets!")

st.write("Secrets yang ditemukan:", list(st.secrets.keys()))

if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
    try:
        credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
        st.success("GOOGLE_SHEETS_CREDENTIALS ditemukan dan berhasil di-load!")
    except json.JSONDecodeError:
        st.error("Format JSON di secrets.toml salah! Cek kembali formatnya.")
else:
    st.error("GOOGLE_SHEETS_CREDENTIALS tidak ditemukan di secrets!")

# Load kredensial dari secrets
credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = Credentials.from_service_account_info(credentials_dict)
client = gspread.authorize(creds)

# Akses Google Sheets
SPREADSHEET_NAME = "Prediksi prestasi"
sheet = client.open(SPREADSHEET_NAME).sheet1

st.success("Berhasil terhubung ke Google Sheets!")

# Header tetap
HEADER = ["No", "Nama", "Jenis Kelamin", "Umur", "Kelas", 
          "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", 
          "Jenis Bullying", "Prediksi Prestasi"]

if not sheet.row_values(1):  # Jika kosong, tambahkan header
    sheet.append_row(HEADER)

# Load model regresi
try:
    with open("D:/prediksi/model_regresi.pkl", "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    st.error("Model regresi tidak ditemukan! Pastikan file 'model_regresi.pkl' ada di D:/prediksi/")
    st.stop()

st.title("Aplikasi Prediksi Prestasi Belajar")

# Fungsi mencari nomor yang belum digunakan
def get_next_available_number(sheet):
    data = sheet.get_all_values()
    if len(data) <= 1:
        return 1  # Jika hanya ada header, mulai dari 1
    existing_numbers = set()
    for row in data[1:]:
        try:
            existing_numbers.add(int(row[0]))
        except ValueError:
            continue
    next_no = 1
    while next_no in existing_numbers:
        next_no += 1
    return next_no

# Pilihan mode input
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

    if st.button("Prediksi!"):
        if not nama:
            st.error("Nama siswa harus diisi!")
        elif jenis_kelamin is None:
            st.error("Jenis kelamin harus dipilih!")
        else:
            input_data = [[bullying, sosial, mental]]
            hasil_prediksi = model.predict(input_data)[0]
            st.success(f"Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f}")

            next_no = get_next_available_number(sheet)
            new_row = [next_no, nama, jenis_kelamin, umur, kelas, bullying, sosial, mental, jenis_bullying, hasil_prediksi]
            sheet.append_row(new_row)
            st.info(f"Hasil prediksi disimpan ke Google Sheets dengan No {next_no}!")

elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])
    if uploaded_file is not None:
        df_siswa = pd.read_csv(uploaded_file)
        if not {"Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", "Jenis Kelamin"}.issubset(df_siswa.columns):
            st.error("Format CSV tidak sesuai! Pastikan memiliki kolom yang benar.")
        else:
            df_siswa["Prediksi Prestasi"] = model.predict(df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]])
            st.subheader("Hasil Prediksi")
            st.dataframe(df_siswa)
            for i, row in df_siswa.iterrows():
                next_no = get_next_available_number(sheet)
                new_row = [next_no] + row.tolist()
                sheet.append_row(new_row)
            st.success("Prediksi selesai! Hasil disimpan ke Google Sheets.")

st.subheader("Riwayat Prediksi")
data = sheet.get_all_values()
df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)
st.dataframe(df_riwayat) if not df_riwayat.empty else st.write("Belum ada riwayat prediksi.")

if st.button("Hapus Semua Riwayat"):
    sheet.clear()
    sheet.append_row(HEADER)
    st.warning("Seluruh riwayat prediksi telah dihapus!")
    st.rerun()

st.subheader("📊 Analisis Jenis Bullying")
if not df_riwayat.empty and "Jenis Bullying" in df_riwayat.columns:
    bullying_counts = df_riwayat["Jenis Bullying"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 6))
    bullying_counts.plot(kind="bar", ax=ax, color=['blue', 'red', 'green', 'purple', 'orange'])
    ax.set_title("Jumlah Kasus Berdasarkan Jenis Bullying")
    ax.set_xlabel("Jenis Bullying")
    ax.set_ylabel("Jumlah Kasus")
    ax.tick_params(axis="x", labelrotation=30)
    st.pyplot(fig)

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", bbox_inches="tight")
    img_buffer.seek(0)
    st.download_button("📥 Download Grafik", data=img_buffer, file_name="grafik_bullying.png", mime="image/png")

    st.write(f"📌 Bullying terbanyak: {bullying_counts.idxmax()} ({bullying_counts.max()} kasus)")
    st.write(f"📌 Bullying tersedikit: {bullying_counts.idxmin()} ({bullying_counts.min()} kasus)")

if not df_riwayat.empty:
    csv = df_riwayat.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Riwayat Prediksi", data=csv, file_name="riwayat_prediksi.csv", mime="text/csv")
