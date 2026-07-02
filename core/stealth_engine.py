import random
import time
import json
import os
from datetime import datetime

VERI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")

USER_AGENT_LISTESI = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

EKran_COZUNURLUKLERI = [(1920, 1080), (2560, 1440), (1680, 1050), (1440, 900), (1366, 768)]

DIL_AYARLARI = ["tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9,tr;q=0.8", "tr;q=0.9,en;q=0.8,de;q=0.5"]

ZAMAN_DILIMLERI = ["Europe/Istanbul", "America/New_York", "Europe/London", "Asia/Tokyo"]

INSAN_DAVRANIS_PROFILLERI = {
    "hizli_okuyucu": {"yazma_gecikmesi": (30, 80), "fare_gecikmesi": (100, 300), "scroll_gecikmesi": (200, 500)},
    "normal": {"yazma_gecikmesi": (80, 200), "fare_gecikmesi": (300, 800), "scroll_gecikmesi": (500, 1500)},
    "yavas_okuyucu": {"yazma_gecikmesi": (200, 500), "fare_gecikmesi": (500, 1500), "scroll_gecikmesi": (1000, 3000)}
}

CAPTCHA_TETIKLEYICILER = ["captcha", "recaptcha", "hcaptcha", "turnstile", "verify", "robot", "insan misin", "are you human", "dogrula"]

RATE_LIMIT_POLITIKALARI = {
    "agresif": {"istek_araligi": (0.5, 1.5), "burst_siniri": 5, "burst_penaltisi": 10},
    "normal": {"istek_araligi": (2.0, 4.0), "burst_siniri": 3, "burst_penaltisi": 15},
    "temkinli": {"istek_araligi": (5.0, 10.0), "burst_siniri": 1, "burst_penaltisi": 30}
}


class StealthEngine:
    def __init__(self, politika="normal"):
        self.politika = RATE_LIMIT_POLITIKALARI.get(politika, RATE_LIMIT_POLITIKALARI["normal"])
        self.user_agent = random.choice(USER_AGENT_LISTESI)
        self.ekran_cozunurlugu = random.choice(EKran_COZUNURLUKLERI)
        self.dil_ayari = random.choice(DIL_AYARLARI)
        self.zaman_dilimi = random.choice(ZAMAN_DILIMLERI)
        self.davranis_profili = random.choice(list(INSAN_DAVRANIS_PROFILLERI.keys()))
        self.istek_sayaci = 0
        self.son_islem_zamani = time.time()
        self.session_verileri = {}

    def user_agent_rotasyonu(self):
        yeni_ua = random.choice([ua for ua in USER_AGENT_LISTESI if ua != self.user_agent])
        self.user_agent = yeni_ua
        return yeni_ua

    def gercekci_tarayici_profili_olustur(self):
        return {
            "user_agent": self.user_agent,
            "ekran": f"{self.ekran_cozunurlugu[0]}x{self.ekran_cozunurlugu[1]}",
            "dil": self.dil_ayari,
            "zaman_dilimi": self.zaman_dilimi,
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "webgl_vendor": random.choice(["Google Inc.", "Intel Inc.", "NVIDIA Corporation", "AMD"]),
            "donanim_paralelligi": random.choice([4, 8, 12, 16]),
            "dokunmatik_destegi": random.choice([True, False]),
            "pdf_destegi": True
        }

    def insan_davranis_simulasyonu(self, profil=None):
        if profil is None:
            profil = self.davranis_profili
        davranis = INSAN_DAVRANIS_PROFILLERI.get(profil, INSAN_DAVRANIS_PROFILLERI["normal"])
        yazma_gecikmesi = random.uniform(*davranis["yazma_gecikmesi"]) / 1000.0
        fare_gecikmesi = random.uniform(*davranis["fare_gecikmesi"]) / 1000.0
        scroll_gecikmesi = random.uniform(*davranis["scroll_gecikmesi"]) / 1000.0
        return {"yazma_gecikmesi": round(yazma_gecikmesi, 3), "fare_gecikmesi": round(fare_gecikmesi, 3), "scroll_gecikmesi": round(scroll_gecikmesi, 3), "profil": profil}

    def rate_limit_adaptif(self, hedef_yanit_suresi=None):
        self.istek_sayaci += 1
        simdi = time.time()
        gecen_sure = simdi - self.son_islem_zamani
        if hedef_yanit_suresi and hedef_yanit_suresi < 0.5:
            yeni_aralik = (self.politika["istek_araligi"][0] * 1.5, self.politika["istek_araligi"][1] * 1.5)
        elif self.istek_sayaci > self.politika["burst_siniri"]:
            time.sleep(self.politika["burst_penaltisi"])
            self.istek_sayaci = 0
            yeni_aralik = self.politika["istek_araligi"]
        else:
            yeni_aralik = self.politika["istek_araligi"]
        bekleme_suresi = random.uniform(*yeni_aralik)
        self.son_islem_zamani = simdi
        return bekleme_suresi

    def captcha_tespit_ve_bekleme(self, sayfa_kaynagi=""):
        if not sayfa_kaynagi:
            return False
        sayfa_lower = sayfa_kaynagi.lower() if isinstance(sayfa_kaynagi, str) else str(sayfa_kaynagi).lower()
        captcha_var = any(tetik in sayfa_lower for tetik in CAPTCHA_TETIKLEYICILER)
        if captcha_var:
            time.sleep(random.uniform(30, 60))
        return captcha_var

    def session_izolasyonu(self, test_id=None):
        if test_id is None:
            test_id = f"session_{random.randint(10000, 99999)}"
        self.session_verileri[test_id] = {
            "olusturulma": datetime.now().isoformat(),
            "user_agent": self.user_agent,
            "profil": self.gercekci_tarayici_profili_olustur(),
            "davranis": self.insan_davranis_simulasyonu()
        }
        return self.session_verileri[test_id]

    def zaman_bazli_davranis_profili(self, saat=None):
        if saat is None:
            saat = datetime.now().hour
        if 8 <= saat < 18:
            return {"mod": "mesai_saati", "davranis": "normal", "typing_hizi": "normal", "scroll_sikligi": "dusuk"}
        elif 18 <= saat < 23:
            return {"mod": "aksam", "davranis": "hizli_okuyucu", "typing_hizi": "hizli", "scroll_sikligi": "yuksek"}
        else:
            return {"mod": "gece", "davranis": "yavas_okuyucu", "typing_hizi": "yavas", "scroll_sikligi": "cok_dusuk"}

    def tls_parmak_izi_rasgele(self):
        ja3_varyasyonlari = [
            "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0",
            "771,4865-4867-4866-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0",
            "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,5-10-11-13-23-27-35-43-45-51-17513-65281,29-23-24,0"
        ]
        return {"ja3": random.choice(ja3_varyasyonlari), "ja4": f"t13d{random.randint(1516,1519)}h2_{random.choice(['i','n'])}"}

    def anti_bot_tespit_enjeksiyonu(self):
        return {
            "navigator.webdriver": False,
            "navigator.plugins.length": random.randint(3, 8),
            "navigator.languages": self.dil_ayari.split(","),
            "screen.colorDepth": 24,
            "screen.pixelDepth": 24,
            "navigator.hardwareConcurrency": random.choice([4, 8, 12, 16]),
            "navigator.deviceMemory": random.choice([4, 8, 16]),
            "chrome.loadTimes": True,
            "chrome.csi": True
        }

    def tam_stealth_profili_olustur(self):
        return {
            "tarayici": self.gercekci_tarayici_profili_olustur(),
            "davranis": self.insan_davranis_simulasyonu(),
            "tls": self.tls_parmak_izi_rasgele(),
            "anti_bot": self.anti_bot_tespit_enjeksiyonu(),
            "zaman_profili": self.zaman_bazli_davranis_profili(),
            "rate_limit": {"politika": self.politika, "istek_sayaci": self.istek_sayaci}
        }
