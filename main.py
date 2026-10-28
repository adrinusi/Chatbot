import argparse
import json
import os
import threading
import time
import uuid
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI

# ========================================
# 1. KONFIGURASI
# ========================================

load_dotenv()

API_KEY = os.getenv("DEPLOY_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
MODEL = os.getenv(
    "DEPLOY_MODEL",
    "deepseek-ai/deepseek-v4.1-flash-1017",
)
BASE_URL = "https://api-cdn.deploy.com/api/v1"
MAX_RETRY = 3
MAX_RIWAYAT = 20  # jumlah pesan terakhir yang dikirim sebagai konteks

if not API_KEY:
    raise SystemExit(
        "ERROR: DEPLOY_API_KEY tidak ditemukan!\n"
        "Pastikan file .env ada di folder yang sama dengan main.py."
    )

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
    timeout=60,
    max_retries=0,
)

# ========================================
# 2. INSTRUKSI CHATBOT
# ========================================

SYSTEM_INSTRUCTION = """
Kamu adalah MenuPintar, chatbot rekomendasi menu makanan dan minuman.
Kamu ngobrol seperti teman yang jago urusan makanan: santai, ramah,
natural, dan tidak kaku.

Cara menjawab:
1. Kalau pengguna minta rekomendasi, langsung kasih 2-4 pilihan menu
   beserta alasan singkat kenapa cocok. Jangan menahan jawaban dengan
   banyak pertanyaan.
2. Tanyakan hal tambahan (budget, selera, pantangan, bahan yang ada,
   mau masak atau beli) hanya jika memang perlu, maksimal 1-2
   pertanyaan, dan sebaiknya setelah memberi rekomendasi awal.
3. Jangan menanyakan atau berasumsi soal pekerjaan, status, atau latar
   belakang pengguna (misalnya mahasiswa atau bukan).
4. Sesuaikan dengan konteks yang disebut pengguna: anggaran, bahan di
   rumah, suasana hati, cuaca, waktu makan, jumlah orang, diet, atau
   acara tertentu.
5. Kalau pengguna ingin masak, berikan bahan dan langkah yang ringkas
   dan mudah diikuti. Kalau ingin beli, sarankan jenis tempat atau
   menu yang umum dicari.
6. Jika menyebut harga, tulis dalam rupiah dan jelaskan bahwa itu
   hanya perkiraan.
7. Jangan menganggap semua bahan makanan tersedia di rumah pengguna.
8. Bisa merekomendasikan masakan Indonesia, masakan daerah, maupun
   masakan internasional sesuai permintaan.
9. Pakai bahasa Indonesia santai tapi jelas. Boleh pakai emoji
   secukupnya. Jawaban singkat dan enak dibaca, tidak bertele-tele.
10. Kalau diminta di luar topik makanan, jawab singkat lalu arahkan
    kembali ke makanan dengan ramah.

Batasan: jangan mengaku sebagai ahli gizi atau dokter, dan jangan
memberi diagnosis medis. Untuk alergi atau kondisi kesehatan, ingatkan
dengan halus agar pengguna memastikan sendiri atau konsultasi ke
tenaga ahli.
"""

# ========================================
# 3. FUNGSI MENGIRIM PESAN KE DEEPSEEK
# ========================================

def tanya_deepseek(pertanyaan, riwayat):
    # Simpan pertanyaan baru sementara
    riwayat.append({
        "role": "user",
        "content": pertanyaan
    })

    for percobaan in range(MAX_RETRY):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    *riwayat[-MAX_RIWAYAT:],
                ],
                temperature=0.8,
                max_tokens=700,
            )

            jawaban = response.choices[0].message.content

            if not isinstance(jawaban, str) or not jawaban.strip():
                finish_reason = response.choices[0].finish_reason
                refusal = getattr(response.choices[0].message, "refusal", None)
                if isinstance(refusal, str) and refusal.strip():
                    jawaban = refusal
                else:
                    alasan = finish_reason or "tidak tersedia"
                    riwayat.pop()
                    return (
                        "API mengembalikan jawaban kosong "
                        f"(finish_reason: {alasan}). Coba kirim ulang."
                    )

            # Simpan jawaban agar konteks percakapan terjaga
            riwayat.append({
                "role": "assistant",
                "content": jawaban
            })
            del riwayat[:-MAX_RIWAYAT]

            return jawaban

        except openai.APIError as error:
            status_code = (
                error.status_code
                if isinstance(error, openai.APIStatusError)
                else None
            )
            retryable = (
                status_code in (429, 500, 502, 503, 504)
                or isinstance(
                    error,
                    (openai.APIConnectionError, openai.APITimeoutError),
                )
            )

            if retryable and percobaan < MAX_RETRY - 1:
                jeda = 2 ** (percobaan + 1)
                print("\nServer API sedang sibuk atau koneksi bermasalah.")
                print(
                    f"Mencoba kembali ({percobaan + 2}/{MAX_RETRY}) "
                    f"dalam {jeda} detik...\n"
                )

                time.sleep(jeda)
                continue

            riwayat.pop()

            if status_code == 401:
                return (
                    "API menolak key (HTTP 401). Periksa DEPLOY_API_KEY "
                    "dan pastikan key berasal dari penyedia endpoint ini."
                )

            if status_code == 403:
                return (
                    "Akses ditolak (HTTP 403). Periksa izin API dan "
                    "status akun pada penyedia endpoint."
                )

            if status_code == 404:
                return (
                    f"Model '{MODEL}' tidak ditemukan atau tidak dapat "
                    "diakses. Periksa ID model di dokumentasi endpoint."
                )

            if status_code == 429:
                return "Batas permintaan/kuota API tercapai. Periksa akun API."

            if retryable:
                return "Server API belum merespons. Silakan coba beberapa saat lagi."

            return f"Kesalahan API: {error}"

        except (ValueError, IndexError, TypeError) as error:
            riwayat.pop()
            return f"Respons API tidak sesuai format: {error}"

    # Pengaman jika seluruh percobaan gagal
    if riwayat and riwayat[-1].get("role") == "user":
        riwayat.pop()

    return "Maaf, permintaan API gagal. Silakan coba kembali."


def jalankan_cli():
    riwayat = []
    print("=" * 45)
    print("           MENUPINTAR AI")
    print("=" * 45)
    print("Hai! Mau makan apa hari ini? Cerita aja, aku bantu pilihin.")
    print("Ketik 'keluar' untuk mengakhiri.")
    print("Ketik 'reset' untuk menghapus riwayat chat.")
    print("-" * 45)

    while True:
        try:
            pertanyaan = input("\nKamu: ").strip()

            if not pertanyaan:
                continue

            if pertanyaan.lower() in ["keluar", "exit", "quit"]:
                print("\nMenuPintar: Sampai jumpa! Selamat makan!")
                break

            if pertanyaan.lower() == "reset":
                riwayat.clear()
                print("\nMenuPintar: Riwayat percakapan dihapus!")
                continue

            jawaban = tanya_deepseek(pertanyaan, riwayat)
            print(f"\nMenuPintar: {jawaban}")

        except KeyboardInterrupt:
            print("\n\nMenuPintar: Program dihentikan. Sampai jumpa!")
            break

        except EOFError:
            print("\nProgram selesai.")
            break


HOST = "127.0.0.1"
PORT = int(os.getenv("MENUPINTAR_PORT", "8000"))
WEB_FILE = Path(__file__).with_name("web").joinpath("index.html")
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
MAX_MESSAGE_LENGTH = 4000


class ChatRequestHandler(BaseHTTPRequestHandler):
    server_version = "MenuPintar/1.0"

    def _get_session(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        session_cookie = cookies.get("menupintar_session")
        session_id = session_cookie.value if session_cookie else ""

        try:
            uuid.UUID(session_id)
        except ValueError:
            session_id = ""

        with SESSIONS_LOCK:
            if session_id not in SESSIONS:
                session_id = str(uuid.uuid4())
                SESSIONS[session_id] = {
                    "history": [],
                    "lock": threading.Lock(),
                }

        return session_id, SESSIONS[session_id]

    def _send_json(self, status, payload, session_id=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if session_id:
            self.send_header(
                "Set-Cookie",
                f"menupintar_session={session_id}; Path=/; "
                "HttpOnly; SameSite=Strict; Max-Age=86400",
            )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return

        try:
            page = WEB_FILE.read_bytes()
        except OSError:
            self.send_error(500, "File tampilan web tidak dapat dibaca.")
            return

        session_id, _ = self._get_session()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header(
            "Set-Cookie",
            f"menupintar_session={session_id}; Path=/; "
            "HttpOnly; SameSite=Strict; Max-Age=86400",
        )
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        if self.path not in ("/api/chat", "/api/reset"):
            self._send_json(404, {"error": "Rute tidak ditemukan."})
            return

        if self.headers.get_content_type() != "application/json":
            self._send_json(
                415,
                {"error": "Kirim permintaan dengan Content-Type application/json."},
            )
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(411, {"error": "Content-Length diperlukan."})
            return

        try:
            length = int(content_length)
        except ValueError:
            self._send_json(400, {"error": "Content-Length tidak valid."})
            return

        if length < 0 or length > MAX_MESSAGE_LENGTH + 1024:
            self._send_json(413, {"error": "Permintaan terlalu besar."})
            return

        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Format JSON tidak valid."})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Isi permintaan tidak valid."})
            return

        session_id, session = self._get_session()
        if self.path == "/api/reset":
            with session["lock"]:
                session["history"].clear()
            self._send_json(200, {"ok": True}, session_id)
            return

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            self._send_json(400, {"error": "Pesan tidak boleh kosong."})
            return
        message = message.strip()
        if len(message) > MAX_MESSAGE_LENGTH:
            self._send_json(
                413,
                {"error": f"Pesan maksimal {MAX_MESSAGE_LENGTH} karakter."},
            )
            return

        with session["lock"]:
            answer = tanya_deepseek(message, session["history"])
        self._send_json(200, {"answer": answer}, session_id)

    def log_message(self, format_string, *args):
        print(f"[web] {self.address_string()} - {format_string % args}")


def jalankan_web():
    server = ThreadingHTTPServer((HOST, PORT), ChatRequestHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"MenuPintar siap dibuka di {url}")
    print("Tekan Ctrl+C untuk menghentikan server.")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer MenuPintar dihentikan.")
    finally:
            server.server_close()


def main():
    parser = argparse.ArgumentParser(description="MenuPintar AI")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Jalankan chatbot di terminal, bukan di browser.",
    )
    args = parser.parse_args()

    if args.cli:
        jalankan_cli()
    else:
        jalankan_web()


if __name__ == "__main__":
    main()