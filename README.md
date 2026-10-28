# Menu Pintar

Menu Pintar adalah chatbot rekomendasi makanan yang menyediakan antarmuka web
dan mode terminal (CLI). Pengguna dapat meminta ide menu, rekomendasi sesuai
budget atau bahan yang tersedia, maupun resep singkat. Jawaban dibuat oleh model
AI melalui endpoint API yang dikonfigurasi di aplikasi.

## Isi proyek

```text
.
├── main.py           # Backend Python, integrasi AI, server HTTP, dan mode CLI
└── web/
    ├── index.html    # Struktur halaman, kelas Tailwind, dan interaksi browser
    └── styles.css    # Gradien latar, animasi chat, dan aturan CSS khusus
```

## Cara kerja kode

### Backend — `main.py`

1. Memuat variabel konfigurasi dari file `.env` dengan `python-dotenv`.
2. Membuat klien API yang kompatibel dengan pustaka `openai`, menggunakan
   endpoint Deploy yang didefinisikan di dalam kode.
3. `tanya_deepseek()` mengirim instruksi chatbot dan riwayat percakapan ke model.
   Fungsi ini membatasi konteks ke 20 pesan terakhir, mencoba ulang beberapa
   jenis kegagalan API, dan mengembalikan jawaban atau pesan kesalahan.
4. `jalankan_web()` memulai server HTTP lokal pada `127.0.0.1`. Server menyajikan
   halaman web dan menangani permintaan chat/reset.
5. `jalankan_cli()` menyediakan percakapan langsung di terminal, dengan perintah
   `reset` untuk mengosongkan riwayat dan `keluar` untuk berhenti.
6. `main()` memilih mode web secara default. Tambahkan argumen `--cli` untuk mode
   terminal.

Server membuat sesi berbasis cookie `menupintar_session`. Riwayat tiap sesi
disimpan di memori, sehingga tidak dibagikan dengan sesi browser lain dan akan
hilang saat server dimulai ulang.

### Frontend — `web/index.html` dan `web/styles.css`

- `index.html` berisi markup halaman, utility class Tailwind, serta JavaScript
  untuk mengirim pesan, tombol saran, indikator mengetik, dan reset chat.
- Pesan dikirim ke backend dengan `fetch()`. Teks jawaban asisten dirender sebagai
  paragraf, daftar, serta format inline sederhana seperti tebal dan kode.
- `styles.css` berisi styling yang tidak praktis ditulis sebagai utility, seperti
  gradien dekoratif, animasi pesan/indikator mengetik, dan dukungan reduced motion.
- Tailwind dimuat dari CDN, jadi browser memerlukan koneksi internet untuk
  mengunduh Tailwind.

## Persiapan

Pastikan Python tersedia, lalu buka PowerShell pada folder proyek.

### 1. Buat dan aktifkan virtual environment (disarankan)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Jika PowerShell menolak aktivasi karena kebijakan eksekusi, gunakan Command
Prompt dan jalankan:

```bat
.venv\Scripts\activate.bat
```

### 2. Pasang dependensi Python

```powershell
python -m pip install openai python-dotenv
```

### 3. Isi konfigurasi API

Buat atau edit file `.env` di folder yang sama dengan `main.py`:

```dotenv
DEPLOY_API_KEY=isi_api_key_anda
DEPLOY_MODEL=deepseek-ai/deepseek-v4.1-flash-1017
MENUPINTAR_PORT=8000
```

- `DEPLOY_API_KEY`: API key untuk penyedia endpoint yang dipakai aplikasi.
  Jangan masukkan key sungguhan ke README atau commit ke Git.
- `DEPLOY_MODEL`: ID model yang tersedia untuk akun/endpoint tersebut. Jika tidak
  diatur, aplikasi menggunakan `deepseek-ai/deepseek-v4.1-flash-1017`.
- `MENUPINTAR_PORT`: port server web; nilai default adalah `8000`.
- Kode juga menerima `DEEPSEEK_API_KEY` jika `DEPLOY_API_KEY` tidak diatur, tetapi
  endpoint API tetap diarahkan ke URL Deploy yang ditentukan di `main.py`.

Jangan publikasikan file `.env`. Jika menggunakan key sungguhan, pastikan file
tersebut dikecualikan dari version control.

## Menjalankan aplikasi

### Mode web (default)

```powershell
python main.py
```

Server mencetak alamat lokal, secara default `http://127.0.0.1:8000`, dan
mencoba membukanya di browser. Hentikan server dengan `Ctrl+C`.

Untuk memakai port lain, atur variabel sebelum menjalankan:

```powershell
$env:MENUPINTAR_PORT = "8080"
python main.py
```

### Mode terminal (CLI)

```powershell
python main.py --cli
```

Ketik pesan di prompt. Gunakan `reset` untuk menghapus riwayat percakapan,
atau `keluar` untuk menutup aplikasi.

## API internal

Server web menyediakan dua endpoint POST. Keduanya menerima JSON dan hanya
tersedia di server lokal yang dijalankan aplikasi.

### `POST /api/chat`

Permintaan:

```json
{"message": "Aku ingin makan hangat dengan budget Rp25.000"}
```

Respons berhasil:

```json
{"answer": "Contoh jawaban dari chatbot"}
```

Pesan kosong atau lebih dari 4.000 karakter ditolak.

### `POST /api/reset`

Menghapus riwayat chat untuk sesi browser yang mengirim permintaan.

## Mengubah instruksi dan tampilan

- Ubah persona, gaya bahasa, atau aturan jawaban pada `SYSTEM_INSTRUCTION` di
  `main.py`.
- Ubah markup, teks, warna, dan utility class pada `web/index.html`.
- Ubah animasi atau CSS khusus pada `web/styles.css`.
- Jika mengganti endpoint atau penyedia AI, periksa `BASE_URL`, nama model, dan
  kompatibilitas API di `main.py`.

## Pemecahan masalah

- **Aplikasi berhenti dengan pesan API key tidak ditemukan:** pastikan `.env`
  berada di direktori yang sama dengan `main.py` dan nama variabel key benar.
- **API menolak permintaan:** verifikasi key, akses akun, model, kuota, serta
  kecocokan key dengan endpoint yang dipakai.
- **Port sudah digunakan:** pilih port lain melalui `MENUPINTAR_PORT`.
- **Halaman tidak mendapat jawaban:** pastikan server Python masih berjalan dan
  periksa pesan yang dicetak di terminal.
- **Tailwind tidak termuat:** pastikan browser memiliki akses internet. Perlu
  diketahui, Content Security Policy yang dikirim backend saat ini hanya
  mengizinkan skrip dari origin sendiri, sementara Tailwind diambil dari
  `cdn.tailwindcss.com`; kebijakan ini dapat memblokir Tailwind pada mode web.
