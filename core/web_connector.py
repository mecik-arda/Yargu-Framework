import asyncio
import json
import os
import random
import time
from pathlib import Path

class ChatbotBulunamadi(Exception):
    pass

class IframeGecisHatasi(Exception):
    pass

class TarayiciHatasi(Exception):
    pass

class WebZamanAsimi(Exception):
    pass

OTURUM_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cikti", "oturumlar")
Path(OTURUM_DIZINI).mkdir(parents=True, exist_ok=True)


class WebBotBaglayici:
    def __init__(self, tarayici_turu="chromium", goruntulu=False, proxy_port=None, oturum_dosyasi=None, gizli_mod=True, bekleme_suresi=2.0):
        self.tarayici_turu = tarayici_turu
        self.goruntulu = goruntulu
        self.proxy_port = proxy_port
        self.oturum_dosyasi = oturum_dosyasi
        self.gizli_mod = gizli_mod
        self.bekleme_suresi = bekleme_suresi
        self.tarayici = None
        self.context = None
        self.sayfa = None
        self.iframe_frame = None
        self.widget_secici = None
        self.iframe_secici = None
        self.input_secici = None
        self.gonder_secici = None
        self.yanit_secici = None
        self.acma_secici = None
        self.chatbot_acik = False
        self.hata_modu = False

    async def baslat(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise TarayiciHatasi("playwright paketi yuklu degil. 'pip install playwright && playwright install' komutunu calistirin.")
        self._pw = await async_playwright().start()
        baslatma_kwargs = {"headless": not self.goruntulu}
        if self.tarayici_turu == "chromium":
            baslatma_kwargs["args"] = [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox"
            ]
            self.tarayici = await self._pw.chromium.launch(**baslatma_kwargs)
        elif self.tarayici_turu == "firefox":
            self.tarayici = await self._pw.firefox.launch(**baslatma_kwargs)
        elif self.tarayici_turu == "webkit":
            self.tarayici = await self._pw.webkit.launch(**baslatma_kwargs)
        else:
            raise TarayiciHatasi(f"Desteklenmeyen tarayici: {self.tarayici_turu}")
        context_kwargs = {}
        if self.proxy_port:
            context_kwargs["proxy"] = {"server": f"http://localhost:{self.proxy_port}"}
        if self.oturum_dosyasi and os.path.exists(self.oturum_dosyasi):
            context_kwargs["storage_state"] = self.oturum_dosyasi
        self.context = await self.tarayici.new_context(**context_kwargs)
        if self.gizli_mod:
            await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.sayfa = await self.context.new_page()
        return True

    async def siteye_git(self, url, bekleme=5):
        if not self.sayfa:
            await self.baslat()
        try:
            await self.sayfa.goto(url, timeout=bekleme * 1000, wait_until="networkidle")
            await asyncio.sleep(self.bekleme_suresi)
            return True
        except Exception as e:
            raise TarayiciHatasi(f"Siteye gidilemedi: {url} - {str(e)}")

    async def chatbot_bul(self, secici=None, otomatik=True, chatbot_imzasi=None):
        if not self.sayfa:
            raise ChatbotBulunamadi("Tarayici baslatilmadi. Once siteye_git() cagrisi yapin.")
        if secici:
            self.widget_secici = secici
            try:
                widget = await self.sayfa.wait_for_selector(secici, timeout=5000)
                if widget:
                    self.acma_secici = secici
                    return {"durum": "bulundu", "secici": secici}
            except:
                pass
        if otomatik and chatbot_imzasi:
            platform_verisi = chatbot_imzasi
            acma_secici = platform_verisi.get("acma_butonu_secici")
            if acma_secici:
                try:
                    widget = await self.sayfa.wait_for_selector(acma_secici, timeout=5000)
                    if widget:
                        self.widget_secici = acma_secici
                        self.acma_secici = acma_secici
                        self.iframe_secici = platform_verisi.get("iframe_secici")
                        self.input_secici = platform_verisi.get("input_secici")
                        self.gonder_secici = platform_verisi.get("gonder_secici")
                        self.yanit_secici = platform_verisi.get("yanit_secici")
                        return {"durum": "bulundu", "secici": acma_secici}
                except:
                    pass
        genel_seciciler = [
            "[aria-label*='chat' i]", "[aria-label*='sohbet' i]", "[aria-label*='mesaj' i]",
            "button[class*='chat']", "button[class*='widget']", "div[class*='launcher']",
            "[aria-label*='destek' i]", "button[class*='messenger']"
        ]
        for secici_deneme in genel_seciciler:
            try:
                widget = await self.sayfa.wait_for_selector(secici_deneme, timeout=3000)
                if widget:
                    self.widget_secici = secici_deneme
                    self.acma_secici = secici_deneme
                    return {"durum": "bulundu", "secici": secici_deneme}
            except:
                continue
        raise ChatbotBulunamadi("Sayfada chatbot bulunamadi. --widget-secici ile manuel secici belirtin.")

    async def sohbeti_ac(self):
        if not self.acma_secici:
            raise ChatbotBulunamadi("Chatbot secicisi tanimli degil.")
        try:
            if self.gizli_mod:
                await self._fare_hareket_ettir_hedefe(self.acma_secici)
            widget_eleman = await self.sayfa.wait_for_selector(self.acma_secici, timeout=5000)
            if widget_eleman:
                await widget_eleman.click()
                await asyncio.sleep(self.bekleme_suresi + 1)
                self.chatbot_acik = True
                if self.iframe_secici:
                    await self._iframe_gec()
                return True
        except Exception as e:
            raise ChatbotBulunamadi(f"Chatbot acilamadi: {str(e)}")
        return False

    async def _iframe_gec(self):
        try:
            await asyncio.sleep(2)
            iframe = await self.sayfa.wait_for_selector(self.iframe_secici, timeout=5000)
            if iframe:
                self.iframe_frame = await iframe.content_frame()
                if not self.iframe_frame:
                    self.iframe_frame = self.sayfa.frame(name=self.iframe_secici) or self.sayfa.frame(url=self.iframe_secici)
                return True
        except:
            pass
        for frame in self.sayfa.frames:
            if frame != self.sayfa.main_frame:
                self.iframe_frame = frame
                return True
        return False

    async def mesaj_yaz(self, mesaj, insan_gibi=True):
        hedef_sayfa = self.iframe_frame or self.sayfa
        if not self.input_secici:
            self.input_secici = "textarea, input[type='text'], div[contenteditable='true'], div[role='textbox']"
        try:
            input_eleman = await hedef_sayfa.wait_for_selector(self.input_secici, timeout=5000)
            if input_eleman:
                await input_eleman.click()
                await asyncio.sleep(0.3)
                if self.gizli_mod and insan_gibi:
                    await self._insan_gibi_yaz(input_eleman, mesaj)
                else:
                    await input_eleman.fill(mesaj)
                return True
        except Exception as e:
            self.hata_modu = True
        return False

    async def _insan_gibi_yaz(self, eleman, mesaj):
        for karakter in mesaj:
            await eleman.type(karakter, delay=random.randint(50, 200))
            if random.random() < 0.03:
                await asyncio.sleep(random.uniform(0.2, 0.6))
                await eleman.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await eleman.type(karakter, delay=random.randint(30, 100))

    async def _fare_hareket_ettir_hedefe(self, secici):
        try:
            hedef = await self.sayfa.wait_for_selector(secici, timeout=3000)
            if hedef:
                kutu = await hedef.bounding_box()
                if kutu:
                    hedef_x = kutu["x"] + kutu["width"] / 2
                    hedef_y = kutu["y"] + kutu["height"] / 2
                    baslangic_x = random.randint(100, 500)
                    baslangic_y = random.randint(100, 400)
                    adimlar = random.randint(5, 12)
                    for i in range(adimlar + 1):
                        t = i / adimlar
                        ara_x = baslangic_x + (hedef_x - baslangic_x) * t + random.uniform(-20, 20) * (1 - abs(t - 0.5) * 2)
                        ara_y = baslangic_y + (hedef_y - baslangic_y) * t + random.uniform(-10, 10) * (1 - abs(t - 0.5) * 2)
                        await self.sayfa.mouse.move(ara_x, ara_y)
                        await asyncio.sleep(random.uniform(0.03, 0.08))
        except:
            pass

    async def mesaj_gonder(self):
        hedef_sayfa = self.iframe_frame or self.sayfa
        if not self.gonder_secici:
            self.gonder_secici = "button[type='submit'], [aria-label*='send' i], [aria-label*='gonder' i], button:has(svg)"
        try:
            gonder_eleman = await hedef_sayfa.wait_for_selector(self.gonder_secici, timeout=3000)
            if gonder_eleman:
                if self.gizli_mod:
                    await self._fare_hareket_ettir_hedefe(self.gonder_secici)
                await gonder_eleman.click()
                return True
        except:
            pass
        try:
            input_eleman = await hedef_sayfa.wait_for_selector(self.input_secici, timeout=2000)
            if input_eleman:
                await input_eleman.press("Enter")
                return True
        except:
            pass
        self.hata_modu = True
        return False

    async def mesaj_gonder_ve_bekle(self, mesaj, insan_gibi=True):
        await self.mesaj_yaz(mesaj, insan_gibi)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        await self.mesaj_gonder()
        await asyncio.sleep(self.bekleme_suresi)

    async def yanit_oku(self, bekleme=10):
        hedef_sayfa = self.iframe_frame or self.sayfa
        if not self.yanit_secici:
            self.yanit_secici = "[class*='message'], [class*='mesaj'], .chat-bubble, .bot-message, .agent-message, [class*='response']"
        try:
            await asyncio.sleep(bekleme)
            yanitlar = await hedef_sayfa.query_selector_all(self.yanit_secici)
            if yanitlar:
                en_son = yanitlar[-1]
                metin = await en_son.inner_text()
                return metin.strip()
        except:
            pass
        try:
            yanit_alanlari = await hedef_sayfa.query_selector_all("div, p, span")
            metinler = []
            for el in yanit_alanlari[-20:]:
                try:
                    metin = await el.inner_text()
                    if metin and len(metin) > 20 and metin not in metinler:
                        metinler.append(metin)
                except:
                    pass
            if metinler:
                return metinler[-1] if len(metinler) == 1 else "\n".join(metinler[-3:])
        except:
            pass
        return ""

    async def son_yaniti_al(self):
        return await self.yanit_oku()

    async def ekran_goruntusu_al(self, dosya_yolu):
        if self.sayfa:
            Path(dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
            await self.sayfa.screenshot(path=dosya_yolu, full_page=False)
            return dosya_yolu
        return None

    async def dosya_yukle(self, dosya_yolu):
        hedef_sayfa = self.iframe_frame or self.sayfa
        dosya_input_secicileri = ["input[type='file']", "input[accept]", "button[aria-label*='attach' i]", "button[aria-label*='dosya' i]", "[class*='upload']", "[class*='attach']"]
        for secici in dosya_input_secicileri:
            try:
                input_el = await hedef_sayfa.wait_for_selector(secici, timeout=3000)
                if input_el:
                    await input_el.set_input_files(dosya_yolu)
                    await asyncio.sleep(self.bekleme_suresi)
                    return True
            except:
                continue
        return False

    async def oturum_kaydet(self, dosya_yolu=None):
        if not dosya_yolu:
            dosya_yolu = os.path.join(OTURUM_DIZINI, f"oturum_{int(time.time())}.json")
        if self.context:
            await self.context.storage_state(path=dosya_yolu)
            return dosya_yolu
        return None

    async def oturum_yukle(self, dosya_yolu):
        if os.path.exists(dosya_yolu):
            self.oturum_dosyasi = dosya_yolu
            return True
        return False

    async def sayfayi_yenile(self):
        if self.sayfa:
            await self.sayfa.reload()
            await asyncio.sleep(self.bekleme_suresi)
            self.chatbot_acik = False
            self.iframe_frame = None
            return True
        return False

    async def kapat(self):
        if self.tarayici:
            await self.tarayici.close()
        if hasattr(self, '_pw') and self._pw:
            await self._pw.stop()
        self.sayfa = None
        self.context = None
        self.iframe_frame = None
        self.chatbot_acik = False

    def eszamanli_calistir(self, async_fonksiyon, *args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_fonksiyon(*args, **kwargs))
