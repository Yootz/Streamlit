# AAR Weather Analysis Dashboard

Dashboard Streamlit untuk menganalisis data cuaca berdasarkan `REGION`, `ESTATE_NAME`, atau `DIVISION_NAME`. Grafik dikelompokkan ke dalam kategori analisis, dan hanya kategori yang dipilih yang ditampilkan.

## Instalasi

Pastikan Python tersedia, lalu buka PowerShell di folder proyek.

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> Jika PowerShell memblokir aktivasi environment, jalankan `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, lalu buka kembali PowerShell dan aktifkan `venv`.

## Menjalankan aplikasi

Jalankan dari folder proyek dengan virtual environment aktif:

```powershell
python -m streamlit run app.py
```

Gunakan URL lokal yang ditampilkan di terminal. Unggah file CSV atau XLSX. File XLSX dibaca dari worksheet pertama. Dataset harus mempunyai setidaknya satu kolom lokasi: `REGION`, `ESTATE_NAME`, atau `DIVISION_NAME`. Pilih tingkat lokasi, nilai lokasi atau `Semua`, lalu kategori analisis.

Gunakan Python yang sama untuk instalasi paket dan menjalankan aplikasi. Bila muncul `ModuleNotFoundError`, aktifkan `venv` terlebih dahulu dan ulangi perintah di atas.

## Kolom dataset

Nama kolom dikenali tanpa membedakan huruf besar-kecil; spasi dan garis bawah pada nama juga dinormalisasi. Kolom yang tidak tersedia tidak akan menggagalkan aplikasi, tetapi analisis terkait tidak ditampilkan. Nilai metrik yang tidak dapat dikonversi menjadi angka dianggap kosong.

### Identitas, waktu, dan lokasi

| Kolom | Keterangan | Penggunaan |
| --- | --- | --- |
| `DATE_RECORD` | Tanggal pencatatan, misalnya `4/27/2020`. | Sumbu waktu untuk grafik tren. |
| `REGION` | Nama wilayah, misalnya `RIAU`. | Pilihan tingkat lokasi dan filter. |
| `ESTATE_NAME` | Nama estate, misalnya `PT. A`. | Pilihan tingkat lokasi dan filter. |
| `DIVISION_NAME` | Nama divisi, misalnya `SUNGAI RAYA`. | Pilihan tingkat lokasi dan filter. |
| `ESTATE_ID` | ID numerik estate. | Identitas pada sumber data; tidak digunakan sebagai filter dashboard. |
| `DIVISION_ID` | ID numerik divisi. | Identitas pada sumber data; tidak digunakan sebagai filter dashboard. |

### Metrik cuaca

| Kolom | Keterangan | Analisis |
| --- | --- | --- |
| `TEMP_MEAN` | Suhu rata-rata per pencatatan. | Tren rata-rata. |
| `TEMP_MIN` | Suhu minimum per pencatatan. | Tren rata-rata suhu minimum. |
| `TEMP_MAX` | Suhu maksimum per pencatatan. | Tren rata-rata suhu maksimum. |
| `DIURNAL` | Rentang/perbedaan suhu harian. | Tren rata-rata. |
| `DEW` | Nilai titik embun. | Tren rata-rata. |
| `RH` | Kelembapan relatif, biasanya dalam persen. | Tren rata-rata. |
| `RAINFALL` | Curah hujan per pencatatan, misalnya `10.7`. | Total per tanggal. |
| `RAINDAY` | Indikator atau jumlah hari hujan per pencatatan. | Total per tanggal. |
| `SOLAR_RAD` | Nilai radiasi matahari. Satuan mengikuti sumber data. | Tren rata-rata. |
| `WIND_SPEED` | Kecepatan angin. Satuan mengikuti sumber data. | Tren rata-rata. |
| `WIND_GUST` | Hembusan angin. Satuan mengikuti sumber data. | Tren rata-rata. |

### Kolom opsional

Skema inti di `columns_name.md` belum mencantumkan tekanan udara, arah angin, atau indeks UV. Dashboard akan menggunakannya jika kolom tersedia dengan salah satu nama berikut:

| Analisis | Nama kolom yang dikenali | Cara ditampilkan |
| --- | --- | --- |
| Tekanan udara | `PRESSURE`, `AIR_PRESSURE`, `ATM_PRESSURE`, `ATMOSPHERIC_PRESSURE`, `BAROMETRIC_PRESSURE`, `PRES`, `TEKANAN_UDARA` | Tren rata-rata. |
| Arah angin | `WIND_DIRECTION`, `WIND_DIR`, `WIND_DIRECTION_DEG`, `WIND_DIRECTION_DEGREES`, `WDIR`, `ARAH_ANGIN` | Jumlah pengamatan per arah mata angin; nilai derajat dan singkatan arah umum didukung. |
| Indeks UV | `UV_INDEX`, `INDEX_UV`, `UVI`, `UV` | Tren rata-rata. |

Metrik cuaca diagregasi per tanggal jika `DATE_RECORD` tersedia dan valid. Saat memilih `Semua`, grafik tren dibatasi ke 10 lokasi dengan pengamatan terbanyak agar lebih mudah dibaca.