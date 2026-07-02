import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path

CIKTI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cikti")
Path(CIKTI_DIZINI).mkdir(parents=True, exist_ok=True)


class ProxyHatasi(Exception):
    pass


class ProxyYakalayici:
    def __init__(self, port=8080, hedef_api_desenleri=None, sertifika_yolu=None):
        self.port = port
        self.hedef_api_desenleri = hedef_api_desenleri or []
        self.sertifika_yolu = sertifika_yolu
        self.calisiyor = False
        self.yakalanan_istekler = []
        self.yakalanan_yanitlar = []
        self.istek_gecmisi = []
        self.proxy_sunucusu = None
        self.kilit = threading.Lock()

    def baslat(self):
        try:
            import mitmproxy
        except ImportError:
            raise ProxyHatasi("mitmproxy paketi yuklu degil. 'pip install mitmproxy' ile yukleyin.")
        self.calisiyor = True
        return True

    def durdur(self):
        self.calisiyor = False
        return True

    def istek_kaydet(self, istek_verisi):
        with self.kilit:
            istek_verisi["yakalama_zamani"] = datetime.now().isoformat()
            istek_verisi["id"] = len(self.istek_gecmisi) + 1
            self.istek_gecmisi.append(istek_verisi)
            if any(desen in istek_verisi.get("url", "") for desen in self.hedef_api_desenleri) or not self.hedef_api_desenleri:
                self.yakalanan_istekler.append(istek_verisi)

    def yanit_kaydet(self, yanit_verisi):
        with self.kilit:
            yanit_verisi["kayit_zamani"] = datetime.now().isoformat()
            self.yakalanan_yanitlar.append(yanit_verisi)

    def yakalanan_istekleri_al(self, filtre=None):
        with self.kilit:
            if filtre:
                return [i for i in self.yakalanan_istekler if filtre in str(i)]
            return list(self.yakalanan_istekler)

    def yakalanan_yanitlari_al(self, filtre=None):
        with self.kilit:
            if filtre:
                return [y for y in self.yakalanan_yanitlar if filtre in str(y)]
            return list(self.yakalanan_yanitlar)

    def istek_tekrarla(self, istek_id, yeni_payload=None):
        with self.kilit:
            for istek in self.yakalanan_istekler:
                if istek.get("id") == istek_id:
                    tekrar_istek = dict(istek)
                    if yeni_payload:
                        tekrar_istek["body"] = yeni_payload
                    return tekrar_istek
        return None

    def filtrele(self, endpoint_deseni):
        return [i for i in self.yakalanan_istekler if endpoint_deseni in i.get("url", "")]

    def chatbot_api_desenlerini_getir(self):
        return [
            "https://api-iam.intercom.io/",
            "https://api.intercom.io/",
            "https://app.intercom.io/",
            "https://drift.com/api/",
            "https://api.drift.com/",
            "zendesk.com/api/v2/",
            "https://api.tawk.to/",
            "https://api.crisp.chat/v1/",
            "https://api.hubapi.com/conversations/",
            "/api/chat",
            "/api/message",
            "/webhook",
            "/conversation"
        ]

    def son_llm_istegini_al(self):
        with self.kilit:
            for istek in reversed(self.yakalanan_istekler):
                body = istek.get("body", "")
                if isinstance(body, dict):
                    body = json.dumps(body)
                if any(k in str(body).lower() for k in ["prompt", "message", "messages", "content", "input", "text"]):
                    return istek
        return None

    def son_llm_yanitini_al(self):
        with self.kilit:
            for yanit in reversed(self.yakalanan_yanitlar):
                body = yanit.get("body", "")
                if isinstance(body, dict):
                    body = json.dumps(body)
                if any(k in str(body).lower() for k in ["response", "output", "text", "content", "message", "choices"]):
                    return yanit
        return None

    def istek_gecmisi_kaydet(self, dosya_yolu=None):
        if not dosya_yolu:
            dosya_yolu = os.path.join(CIKTI_DIZINI, f"proxy_gecmisi_{int(time.time())}.json")
        with self.kilit:
            veri = {
                "proxy_port": self.port,
                "kayit_zamani": datetime.now().isoformat(),
                "toplam_istek": len(self.istek_gecmisi),
                "yakalanan_istek": len(self.yakalanan_istekler),
                "yakalanan_yanit": len(self.yakalanan_yanitlar),
                "istek_gecmisi": self.istek_gecmisi
            }
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=2)
            return dosya_yolu

    def istek_gecmisi_yukle(self, dosya_yolu):
        if not os.path.exists(dosya_yolu):
            return False
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            veri = json.load(f)
        with self.kilit:
            self.istek_gecmisi = veri.get("istek_gecmisi", [])
            self.yakalanan_istekler = [i for i in self.istek_gecmisi if "url" in i]
            self.yakalanan_yanitlar = [i for i in self.istek_gecmisi if "status_code" in i]
        return True

    def calisma_durumu(self):
        return self.calisiyor

    def istatistikler(self):
        with self.kilit:
            return {
                "calisiyor": self.calisiyor,
                "port": self.port,
                "toplam_yakalanan_istek": len(self.yakalanan_istekler),
                "toplam_yakalanan_yanit": len(self.yakalanan_yanitlar),
                "toplam_gecmis": len(self.istek_gecmisi)
            }
