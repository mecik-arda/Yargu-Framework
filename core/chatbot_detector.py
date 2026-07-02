import json
import os
import asyncio
from enum import Enum

VERI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")
IMZA_DOSYASI = os.path.join(VERI_DIZINI, "chatbot_imzalari.json")


class ChatbotPlatform(Enum):
    INTERCOM = "intercom"
    DRIFT = "drift"
    ZENDESK = "zendesk"
    TAWKTO = "tawkto"
    CRISP = "crisp"
    HUBSPOT = "hubspot"
    OZEL = "ozel"
    BULUNAMADI = "bulunamadi"


class ChatbotDedektoru:
    def __init__(self):
        self.imzalar = self._imzalari_yukle()

    def _imzalari_yukle(self):
        try:
            with open(IMZA_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f).get("platformlar", {})
        except FileNotFoundError:
            return {}

    async def sayfa_tara(self, sayfa, bekleme_suresi=10):
        sonuclar = []
        try:
            await asyncio.sleep(bekleme_suresi)
        except:
            pass
        for platform_adi, imza in self.imzalar.items():
            if platform_adi == "ozel":
                continue
            sonuc = await self._platform_kontrol(sayfa, platform_adi, imza)
            if sonuc["guven_skoru"] > 0:
                sonuclar.append(sonuc)
        if not sonuclar:
            ozel_sonuc = await self._ozel_chatbot_tara(sayfa)
            if ozel_sonuc["guven_skoru"] > 0:
                sonuclar.append(ozel_sonuc)
        sonuclar.sort(key=lambda x: x["guven_skoru"], reverse=True)
        return sonuclar

    async def _platform_kontrol(self, sayfa, platform_adi, imza):
        guven_skoru = 0.0
        script_eslesti = await self._script_etiketleri_tara(sayfa, imza.get("script_desenleri", []))
        if script_eslesti:
            guven_skoru += 0.6
        iframe_eslesti = await self._iframe_kontrol(sayfa, imza.get("iframe_desenleri", []))
        if iframe_eslesti:
            guven_skoru += 0.5
        dom_eslesti = await self._dom_yapisi_kontrol(sayfa, imza.get("widget_secici"))
        if dom_eslesti:
            guven_skoru += 0.3
        return {
            "platform": platform_adi,
            "platform_adi": imza.get("ad", platform_adi),
            "guven_skoru": min(guven_skoru, 1.0),
            "imza": imza,
            "widget_secici": imza.get("widget_secici"),
            "iframe_secici": imza.get("iframe_secici"),
            "input_secici": imza.get("input_secici"),
            "gonder_secici": imza.get("gonder_secici"),
            "yanit_secici": imza.get("yanit_secici"),
            "acma_butonu_secici": imza.get("acma_butonu_secici"),
            "acma_js": imza.get("acma_js"),
            "iframe_kullaniyor": imza.get("iframe_kullaniyor", False),
            "dosya_yukleme_var": imza.get("dosya_yukleme_var", False)
        }

    async def _script_etiketleri_tara(self, sayfa, desenler):
        if not desenler:
            return False
        try:
            script_elemanlari = await sayfa.query_selector_all("script[src]")
            for script_el in script_elemanlari:
                src = await script_el.get_attribute("src")
                if src:
                    for desen in desenler:
                        if desen in src:
                            return True
        except:
            pass
        try:
            sayfa_icerigi = await sayfa.content()
            for desen in desenler:
                if desen in sayfa_icerigi:
                    return True
        except:
            pass
        return False

    async def _iframe_kontrol(self, sayfa, desenler):
        if not desenler:
            return False
        try:
            iframe_elemanlari = await sayfa.query_selector_all("iframe")
            for iframe in iframe_elemanlari:
                src = await iframe.get_attribute("src") or ""
                class_attr = await iframe.get_attribute("class") or ""
                id_attr = await iframe.get_attribute("id") or ""
                birlesik = f"{src} {class_attr} {id_attr}"
                for desen in desenler:
                    if desen.lower() in birlesik.lower():
                        return True
        except:
            pass
        return False

    async def _dom_yapisi_kontrol(self, sayfa, secici):
        if not secici:
            return False
        secici_listesi = [s.strip() for s in secici.split(",")]
        for tek_secici in secici_listesi:
            try:
                eleman = await sayfa.query_selector(tek_secici)
                if eleman:
                    return True
            except:
                continue
        return False

    async def _ozel_chatbot_tara(self, sayfa):
        ozel_imza = self.imzalar.get("ozel", {})
        guven_skoru = 0.0
        if await self._dom_yapisi_kontrol(sayfa, ozel_imza.get("widget_secici")):
            guven_skoru += 0.2
        if await self._iframe_kontrol(sayfa, ozel_imza.get("iframe_desenleri", [])):
            guven_skoru += 0.1
        return {
            "platform": "ozel",
            "platform_adi": "Özel / Bilinmeyen Chatbot",
            "guven_skoru": min(guven_skoru, 1.0),
            "imza": ozel_imza,
            "widget_secici": ozel_imza.get("widget_secici"),
            "iframe_secici": ozel_imza.get("iframe_secici"),
            "input_secici": ozel_imza.get("input_secici"),
            "gonder_secici": ozel_imza.get("gonder_secici"),
            "yanit_secici": ozel_imza.get("yanit_secici"),
            "acma_butonu_secici": ozel_imza.get("acma_butonu_secici"),
            "acma_js": None,
            "iframe_kullaniyor": False,
            "dosya_yukleme_var": False
        }

    async def imza_eslestir(self, sayfa):
        tespitler = await self.sayfa_tara(sayfa)
        if tespitler:
            return tespitler[0]
        return None

    async def chatbot_secicisi_bul(self, sayfa):
        imza = await self.imza_eslestir(sayfa)
        if imza:
            return imza
        ozel_imza = self.imzalar.get("ozel", {})
        return {
            "platform": "ozel",
            "platform_adi": "Özel Chatbot",
            "guven_skoru": 0.1,
            "imza": ozel_imza,
            "widget_secici": ozel_imza.get("widget_secici"),
            "iframe_secici": ozel_imza.get("iframe_secici"),
            "input_secici": ozel_imza.get("input_secici"),
            "gonder_secici": ozel_imza.get("gonder_secici"),
            "yanit_secici": ozel_imza.get("yanit_secici"),
            "acma_butonu_secici": ozel_imza.get("acma_butonu_secici"),
            "acma_js": None,
            "iframe_kullaniyor": False,
            "dosya_yukleme_var": False
        }

    async def chatbot_turu_belirle(self, sayfa):
        imza = await self.imza_eslestir(sayfa)
        if imza:
            return imza["platform"]
        return "bulunamadi"

    async def iframe_tara(self, sayfa):
        iframe_listesi = []
        try:
            iframe_elemanlari = await sayfa.query_selector_all("iframe")
            for iframe in iframe_elemanlari:
                src = await iframe.get_attribute("src") or ""
                id_attr = await iframe.get_attribute("id") or ""
                class_attr = await iframe.get_attribute("class") or ""
                iframe_listesi.append({"src": src, "id": id_attr, "class": class_attr, "chatbot_olabilir": any(k in (src + id_attr + class_attr).lower() for k in ["chat", "widget", "messenger", "support", "bot", "message"])})
        except:
            pass
        return iframe_listesi

    async def dinamik_bekleme(self, sayfa, sure=10):
        await asyncio.sleep(sure)
        return True

    def platform_listesi(self):
        return [(adi, veri.get("ad", adi)) for adi, veri in self.imzalar.items()]
