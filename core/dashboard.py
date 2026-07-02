import json
import os
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

VERI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Yargu Dashboard v2.9.0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.header{background:#1e293b;padding:16px 24px;border-bottom:2px solid #334155;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:1.3rem;color:#38bdf8}.header span{color:#94a3b8;font-size:.8rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;padding:24px}
.kart{background:#1e293b;border-radius:10px;padding:20px;border:1px solid #334155}
.kart h3{color:#94a3b8;font-size:.75rem;text-transform:uppercase;margin-bottom:8px}
.kart .deger{font-size:1.8rem;font-weight:700}.kart .alt{font-size:.7rem;color:#64748b;margin-top:4px}
.basarili .deger{color:#22c55e}.basarisiz .deger{color:#ef4444}.uyari .deger{color:#f59e0b}
.test-listesi{padding:0 24px 24px}.test-kart{background:#1e293b;border-radius:8px;padding:12px 16px;margin-bottom:8px;border-left:4px solid #334155;display:flex;justify-content:space-between;align-items:center}
.test-kart.zafiyetli{border-left-color:#ef4444}.test-kart.guvenli{border-left-color:#22c55e}
.test-kategori{font-size:.7rem;color:#64748b}.grafik-alani{padding:0 24px 24px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
.bar{height:20px;background:#334155;border-radius:4px;overflow:hidden;margin:4px 0}
.bar-dolu{height:100%;border-radius:4px;transition:width .3s}
.bar-etiket{font-size:.7rem;display:flex;justify-content:space-between;margin-top:2px}
footer{text-align:center;padding:16px;color:#475569;font-size:.7rem;border-top:1px solid #1e293b}
</style>
</head>
<body>
<div class="header"><h1>Yargu Dashboard v2.9.0</h1><span>AltaySec | Arda Meçik</span></div>
<div class="grid">
<div class="kart"><h3>Toplam Test</h3><div class="deger">{toplam_test}</div></div>
<div class="kart basarili"><h3>Başarılı Saldırı</h3><div class="deger">{basarili_saldiri}</div></div>
<div class="kart basarisiz"><h3>Başarısız</h3><div class="deger">{basarisiz}</div></div>
<div class="kart uyari"><h3>Güvenlik Skoru</h3><div class="deger">{skor}/100</div></div>
</div>
<div class="grafik-alani"><div class="kart"><h3>Kategori Bazlı Başarı</h3>{kategori_barlari}</div><div class="kart"><h3>Zafiyet Dağılımı</h3>{zafiyet_barlari}</div></div>
<div class="test-listesi"><h3 style="margin-bottom:12px;color:#94a3b8">Son Testler</h3>{test_kartlari}</div>
<footer>Yargu Framework v2.9.0 — AltaySec Bünyesinde Geliştirilmiştir | Arda Meçik</footer>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    dashboard_verisi = {"toplam_test": 0, "basarili_saldiri": 0, "basarisiz": 0, "skor": 100, "kategori_bazli": {}, "zafiyet_dagilimi": {}, "son_testler": [], "olay_kuyrugu": [], "uyari_esikleri": {"skor": 70}}
    _kilit = threading.Lock()

    def _html_yanit(self, html_icerik, durum=200):
        self.send_response(durum)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_icerik.encode("utf-8"))

    def _json_yanit(self, veri):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(veri, ensure_ascii=False).encode("utf-8"))

    def _dashboard_html_uret(self):
        v = DashboardHandler.dashboard_verisi
        kategori_barlari = ""
        for kat, veri in v.get("kategori_bazli", {}).items():
            if veri.get("toplam", 0) > 0:
                oran = veri.get("basarili", 0) / veri["toplam"] * 100
                renk = "#ef4444" if oran > 30 else ("#f59e0b" if oran > 10 else "#22c55e")
                kategori_barlari += f'<div class="bar-etiket"><span>{kat}</span><span>%{oran:.0f}</span></div><div class="bar"><div class="bar-dolu" style="width:{oran}%;background:{renk}"></div></div>'
        zafiyet_barlari = ""
        for seviye, sayi in v.get("zafiyet_dagilimi", {}).items():
            if sayi > 0:
                max_sayi = max(v["zafiyet_dagilimi"].values()) if v["zafiyet_dagilimi"] else 1
                oran = sayi / max_sayi * 100
                renk = {"kritik": "#ef4444", "yuksek": "#f59e0b", "orta": "#3b82f6", "dusuk": "#22c55e"}.get(seviye, "#94a3b8")
                zafiyet_barlari += f'<div class="bar-etiket"><span>{seviye}</span><span>{sayi}</span></div><div class="bar"><div class="bar-dolu" style="width:{oran}%;background:{renk}"></div></div>'
        test_kartlari = ""
        for t in list(v.get("son_testler", []))[-20:]:
            sinif = "zafiyetli" if t.get("zafiyet_var") else "guvenli"
            durum = "ZAFIYET" if t.get("zafiyet_var") else "GUVENLI"
            test_kartlari += f'<div class="test-kart {sinif}"><div><strong>#{t.get("id","?")}</strong> <span class="test-kategori">{t.get("kategori","?")}</span></div><div>{durum} ({t.get("seviye","?")})</div></div>'
        return DASHBOARD_HTML.format(toplam_test=v.get("toplam_test", 0), basarili_saldiri=v.get("basarili_saldiri", 0), basarisiz=v.get("basarisiz", 0), skor=v.get("skor", 100), kategori_barlari=kategori_barlari, zafiyet_barlari=zafiyet_barlari, test_kartlari=test_kartlari or '<p style="color:#64748b">Henuz test yapilmadi.</p>')

    def do_GET(self):
        if self.path == "/":
            self._html_yanit(self._dashboard_html_uret())
        elif self.path == "/api/durum":
            self._json_yanit(DashboardHandler.dashboard_verisi)
        elif self.path == "/api/olaylar":
            olaylar = DashboardHandler.dashboard_verisi.get("olay_kuyrugu", [])[-50:]
            self._json_yanit(olaylar)
        elif self.path == "/api/istatistik":
            v = DashboardHandler.dashboard_verisi
            self._json_yanit({"toplam_test": v["toplam_test"], "skor": v["skor"], "basarili_saldiri": v["basarili_saldiri"], "zaman": datetime.now().isoformat()})
        else:
            self._html_yanit("<h1>404</h1>", 404)

    def log_message(self, format, *args):
        pass


class SecurityDashboard:
    def __init__(self, port=8080):
        self.port = port
        self.httpd = None
        self.calisma = threading.Event()
        self.thread = None

    def baslat(self, port=None):
        if port:
            self.port = port
        self.httpd = HTTPServer(("0.0.0.0", self.port), DashboardHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return f"http://localhost:{self.port}"

    def durdur(self):
        if self.httpd:
            self.httpd.shutdown()

    def test_sonucu_ekle(self, sonuc):
        with DashboardHandler._kilit:
            DashboardHandler.dashboard_verisi["toplam_test"] += 1
            DashboardHandler.dashboard_verisi["son_testler"].append({
                "id": sonuc.get("test_id", "?"),
                "kategori": sonuc.get("saldiri_turu", "?"),
                "zafiyet_var": sonuc.get("zafiyet_var", False),
                "seviye": sonuc.get("zafiyet_seviyesi", "?"),
                "skor_etkisi": sonuc.get("guvenlik_skoru_etkisi", 0),
                "zaman": datetime.now().isoformat()
            })
            if sonuc.get("zafiyet_var"):
                DashboardHandler.dashboard_verisi["basarili_saldiri"] += 1
                seviye = sonuc.get("zafiyet_seviyesi", "orta")
                if seviye not in DashboardHandler.dashboard_verisi["zafiyet_dagilimi"]:
                    DashboardHandler.dashboard_verisi["zafiyet_dagilimi"][seviye] = 0
                DashboardHandler.dashboard_verisi["zafiyet_dagilimi"][seviye] += 1
            else:
                DashboardHandler.dashboard_verisi["basarisiz"] += 1
            kat = sonuc.get("saldiri_turu", "bilinmiyor")
            if kat not in DashboardHandler.dashboard_verisi["kategori_bazli"]:
                DashboardHandler.dashboard_verisi["kategori_bazli"][kat] = {"toplam": 0, "basarili": 0}
            DashboardHandler.dashboard_verisi["kategori_bazli"][kat]["toplam"] += 1
            if sonuc.get("zafiyet_var"):
                DashboardHandler.dashboard_verisi["kategori_bazli"][kat]["basarili"] += 1
            skor_etkisi = sonuc.get("guvenlik_skoru_etkisi", 0)
            DashboardHandler.dashboard_verisi["skor"] = max(0, min(100, DashboardHandler.dashboard_verisi["skor"] + skor_etkisi))
            DashboardHandler.dashboard_verisi["olay_kuyrugu"].append({"tip": "test_sonucu", "veri": sonuc.get("test_id", "?"), "zaman": datetime.now().isoformat()})
            esik = DashboardHandler.dashboard_verisi["uyari_esikleri"]["skor"]
            if DashboardHandler.dashboard_verisi["skor"] < esik and DashboardHandler.dashboard_verisi["toplam_test"] > 0:
                DashboardHandler.dashboard_verisi["olay_kuyrugu"].append({"tip": "uyari", "mesaj": f"Guvenlik skoru {DashboardHandler.dashboard_verisi['skor']} esigin altinda! ({esik})", "zaman": datetime.now().isoformat()})

    def uyari_esikleri_ayarla(self, skor_esigi=70):
        DashboardHandler.dashboard_verisi["uyari_esikleri"]["skor"] = skor_esigi

    def skor_sifirla(self):
        with DashboardHandler._kilit:
            DashboardHandler.dashboard_verisi = {"toplam_test": 0, "basarili_saldiri": 0, "basarisiz": 0, "skor": 100, "kategori_bazli": {}, "zafiyet_dagilimi": {}, "son_testler": [], "olay_kuyrugu": [], "uyari_esikleri": {"skor": 70}}
