import json
import os
import uuid
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

AKTIF_TESTLER = {}
TEST_SONUCLARI = {}
API_KULLANICILARI = {"admin": os.environ.get("YARGU_API_TOKEN", "yargu-admin-token-2024")}
OTURUM_TOKENLERI = {}

HTML_SWAGGER = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><title>Yargu Cloud API v3.0.0</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:40px}
h1{color:#38bdf8;margin-bottom:8px}h2{color:#94a3b8;font-size:1rem;margin-bottom:24px}
.endpoint{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:12px;display:flex;gap:16px;align-items:center}
.method{font-weight:700;font-size:.75rem;padding:4px 10px;border-radius:4px;min-width:56px;text-align:center}
.post{background:#166534;color:#22c55e}.get{background:#1e3a5f;color:#38bdf8}.delete{background:#7f1d1d;color:#ef4444}
.path{font-family:monospace}.desc{color:#64748b;font-size:.8rem}
.token{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:20px;margin-top:24px}
.token code{color:#38bdf8;font-size:1.2rem}</style></head><body>
<h1>Yargu Cloud API v3.0.0</h1><h2>AltaySec Bunyesinde Gelistirilmistir | Arda Mecik</h2>
<div class="endpoint"><span class="method post">POST</span><span class="path">/api/test</span><span class="desc">Guvenlik testi baslat</span></div>
<div class="endpoint"><span class="method get">GET</span><span class="path">/api/test/{id}</span><span class="desc">Test durumunu sorgula</span></div>
<div class="endpoint"><span class="method get">GET</span><span class="path">/api/test/{id}/sonuc</span><span class="desc">Test sonucunu al</span></div>
<div class="endpoint"><span class="method post">POST</span><span class="path">/api/benchmark</span><span class="desc">Benchmark baslat</span></div>
<div class="endpoint"><span class="method post">POST</span><span class="path">/api/otonom</span><span class="desc">Otonom pentest baslat</span></div>
<div class="endpoint"><span class="method get">GET</span><span class="path">/api/models</span><span class="desc">Desteklenen modelleri listele</span></div>
<div class="endpoint"><span class="method get">GET</span><span class="path">/api/payloads</span><span class="desc">Payload kategorilerini listele</span></div>
<div class="endpoint"><span class="method get">GET</span><span class="path">/api/health</span><span class="desc">Saglik kontrolu</span></div>
<div class="endpoint"><span class="method post">POST</span><span class="path">/api/auth/login</span><span class="desc">Oturum ac</span></div>
<div class="token"><strong>Varsayilan Token:</strong> <code>yargu-admin-token-2024</code></div>
</body></html>"""

DESTEKLENEN_MODELLER = [
    {"hedef": "ollama", "modeller": ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "mistral:7b"]},
    {"hedef": "openai", "modeller": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
    {"hedef": "claude", "modeller": ["claude-sonnet-5", "claude-haiku-4-5", "claude-opus-4-8"]},
    {"hedef": "gemini", "modeller": ["gemini-2.0-flash", "gemini-2.0-pro"]}
]

PAYLOAD_KATEGORILERI = ["jailbreak", "extraction", "injection", "injection_dolayli", "injection_kalici", "injection_gizli", "injection_cakistirma", "injection_ozyinelemeli", "web_ozel", "tool_injection", "multimodal_injection"]


def _test_calistir_arka_planda(test_id, config):
    AKTIF_TESTLER[test_id] = {"durum": "calisiyor", "baslangic": datetime.now().isoformat(), "config": config}
    try:
        from core.connector import baglayici_olustur
        from core.evaluator import Degerlendirici
        from core.attacker import Saldirgan
        kwargs = {"model_adi": config["model"], "zaman_asimi": config.get("zaman_asimi", 30)}
        if config.get("api_anahtari"):
            kwargs["api_anahtari"] = config["api_anahtari"]
        if config.get("url"):
            kwargs["api_url"] = config["url"]
        baglayici = baglayici_olustur(config["hedef"], **kwargs)
        baglayici.baglan()
        degerlendirici = Degerlendirici()
        saldirgan = Saldirgan(konu=config.get("konu", "zararli yazilim"))
        payloadlar = saldirgan.payload_yukle(kategori=config.get("kategori", "hepsi"))
        limit = config.get("limit", 0)
        if limit > 0 and len(payloadlar) > limit:
            import random
            payloadlar = random.sample(payloadlar, limit)
        for payload in payloadlar:
            mesaj = saldirgan.payload_dinamik_olustur(payload.get("sablon", ""))
            saldiri_turu = payload.get("saldiri_turu") or payload.get("kategori", "bilinmiyor")
            try:
                sonuc = baglayici.mesaj_gonder(mesaj)
                degerlendirici.yanit_analiz_et(sonuc.get("yanit", ""), saldiri_turu, payload=mesaj)
            except Exception:
                continue
        skor = degerlendirici.guvenlik_skoru_hesapla()
        TEST_SONUCLARI[test_id] = {"skor": skor, "sonuclar": degerlendirici.sonuclar, "tamamlanma": datetime.now().isoformat()}
        AKTIF_TESTLER[test_id]["durum"] = "tamamlandi"
    except Exception as e:
        AKTIF_TESTLER[test_id]["durum"] = "hata"
        AKTIF_TESTLER[test_id]["hata"] = str(e)[:200]


class YarguAPIHandler(BaseHTTPRequestHandler):
    def _json(self, veri, durum=200):
        self.send_response(durum)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(veri, ensure_ascii=False).encode("utf-8"))

    def _html(self, html, durum=200):
        self.send_response(durum)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _body_oku(self):
        uzunluk = int(self.headers.get("Content-Length", 0))
        if uzunluk > 0:
            try:
                return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None

    def _token_kontrol(self):
        auth = self.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
        if token in API_KULLANICILARI.values() or token in OTURUM_TOKENLERI:
            return True
        self._json({"hata": "Yetkisiz erisim. Authorization: Bearer <token> gerekli."}, 401)
        return False

    def _yol_ayristir(self):
        parsed = urlparse(self.path)
        yol = parsed.path.rstrip("/")
        return yol, parse_qs(parsed.query)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        yol, params = self._yol_ayristir()
        if yol == "" or yol == "/docs":
            self._html(HTML_SWAGGER)
        elif yol == "/api/health":
            self._json({"durum": "saglikli", "versiyon": "3.0.0", "aktif_testler": len(AKTIF_TESTLER), "zaman": datetime.now().isoformat()})
        elif yol.startswith("/api/test/") and "/sonuc" in yol:
            test_id = yol.split("/api/test/")[1].split("/sonuc")[0]
            if test_id in TEST_SONUCLARI:
                self._json(TEST_SONUCLARI[test_id])
            else:
                self._json({"hata": "Test sonucu henuz hazir degil veya test bulunamadi"}, 404)
        elif yol.startswith("/api/test/"):
            test_id = yol.split("/api/test/")[1]
            if test_id in AKTIF_TESTLER:
                self._json(AKTIF_TESTLER[test_id])
            else:
                self._json({"hata": "Test bulunamadi"}, 404)
        elif yol == "/api/models":
            self._json(DESTEKLENEN_MODELLER)
        elif yol == "/api/payloads":
            self._json(PAYLOAD_KATEGORILERI)
        elif yol == "/api/testler":
            self._json({"aktif": list(AKTIF_TESTLER.keys()), "tamamlanan": list(TEST_SONUCLARI.keys())})
        else:
            self._json({"hata": "Endpoint bulunamadi"}, 404)

    def do_POST(self):
        yol, _ = self._yol_ayristir()
        if yol == "/api/auth/login":
            body = self._body_oku()
            if body is None:
                self._json({"hata": "Gecersiz JSON body"}, 400)
                return
            kullanici = body.get("kullanici", "")
            sifre = body.get("token", "")
            if kullanici in API_KULLANICILARI and sifre == API_KULLANICILARI[kullanici]:
                oturum = str(uuid.uuid4())[:16]
                OTURUM_TOKENLERI[oturum] = kullanici
                self._json({"token": oturum, "kullanici": kullanici})
            else:
                self._json({"hata": "Gecersiz kimlik"}, 401)
        elif not self._token_kontrol():
            return
        elif yol == "/api/test":
            config = self._body_oku()
            if config is None:
                self._json({"hata": "Gecersiz JSON body"}, 400)
                return
            if not config.get("hedef") or not config.get("model"):
                self._json({"hata": "hedef ve model zorunludur"}, 400)
                return
            test_id = f"test-{uuid.uuid4().hex[:8]}"
            AKTIF_TESTLER[test_id] = {"durum": "baslatiliyor", "baslangic": datetime.now().isoformat()}
            thread = threading.Thread(target=_test_calistir_arka_planda, args=(test_id, config), daemon=True)
            thread.start()
            self._json({"test_id": test_id, "durum": "baslatildi", "sorgu": f"/api/test/{test_id}"}, 202)
        elif yol == "/api/benchmark":
            config = self._body_oku()
            if config is None:
                self._json({"hata": "Gecersiz JSON body"}, 400)
                return
            test_id = f"bm-{uuid.uuid4().hex[:8]}"
            AKTIF_TESTLER[test_id] = {"durum": "baslatiliyor", "baslangic": datetime.now().isoformat(), "config": config, "tip": "benchmark"}
            self._json({"test_id": test_id, "durum": "baslatildi", "sorgu": f"/api/test/{test_id}"}, 202)
        elif yol == "/api/otonom":
            config = self._body_oku()
            if config is None:
                self._json({"hata": "Gecersiz JSON body"}, 400)
                return
            test_id = f"oto-{uuid.uuid4().hex[:8]}"
            AKTIF_TESTLER[test_id] = {"durum": "baslatiliyor", "baslangic": datetime.now().isoformat(), "config": config, "tip": "otonom"}
            self._json({"test_id": test_id, "durum": "baslatildi", "sorgu": f"/api/test/{test_id}"}, 202)
        else:
            self._json({"hata": "Endpoint bulunamadi"}, 404)

    def log_message(self, format, *args):
        pass


class YarguCloudAPI:
    def __init__(self, port=8000):
        self.port = port
        self.httpd = None
        self.thread = None

    def baslat(self, port=None):
        if port:
            self.port = port
        self.httpd = HTTPServer(("0.0.0.0", self.port), YarguAPIHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return f"http://localhost:{self.port}"

    def durdur(self):
        if self.httpd:
            self.httpd.shutdown()

    @staticmethod
    def durum():
        return {"aktif_testler": len(AKTIF_TESTLER), "tamamlanan_testler": len(TEST_SONUCLARI), "kullanicilar": len(API_KULLANICILARI), "oturumlar": len(OTURUM_TOKENLERI)}
