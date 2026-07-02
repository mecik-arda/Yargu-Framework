import requests
import json
import os

class BaglantiHatasi(Exception):
    pass

class YetkilendirmeHatasi(Exception):
    pass

class KotaHatasi(Exception):
    pass

class ZamanAsimiHatasi(Exception):
    pass

class OllamaBaglayici:
    def __init__(self, model_adi="llama3.1:8b", api_url="http://localhost:11434", sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_url = api_url.rstrip("/")
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        try:
            yanit = requests.get(f"{self.api_url}/api/tags", timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"Ollama baglantisi basarisiz: {self.api_url} - Durum kodu: {yanit.status_code}")
            modeller = yanit.json().get("models", [])
            model_adlari = [m["name"] for m in modeller]
            if self.model_adi not in model_adlari:
                raise BaglantiHatasi(f"Model bulunamadi: {self.model_adi}. Mevcut modeller: {', '.join(model_adlari)}")
            return True
        except requests.exceptions.ConnectionError:
            raise BaglantiHatasi(f"Ollama'ya baglanilamadi: {self.api_url}. Ollama'nin calistigindan emin olun.")
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"Ollama baglanti zamani asimi: {self.zaman_asimi} saniye")

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        if gecmis is None:
            gecmis = []
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        for g in gecmis:
            mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {
            "model": self.model_adi,
            "messages": mesaj_listesi,
            "stream": False,
            "options": {
                "temperature": self.sicaklik,
                "num_predict": self.max_token
            }
        }
        try:
            yanit = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"API yanit hatasi: {yanit.status_code} - {yanit.text}")
            veri = yanit.json()
            cevap = veri.get("message", {}).get("content", "")
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("eval_count", 0)}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"API yanit zamani asimi: {self.zaman_asimi} saniye")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        sonuclar = []
        gecmis = []
        for mesaj in mesaj_listesi:
            sonuc = self.mesaj_gonder(mesaj, gecmis)
            sonuclar.append(sonuc)
            gecmis.append({"role": "user", "content": mesaj})
            gecmis.append({"role": "assistant", "content": sonuc["yanit"]})
            if len(gecmis) > 40:
                gecmis = gecmis[-20:]
        return sonuclar

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        if gecmis is None:
            gecmis = []
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        for g in gecmis:
            mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {"model": self.model_adi, "messages": mesaj_listesi, "stream": False, "options": {"temperature": self.sicaklik, "num_predict": self.max_token}}
        if arac_tanimlari:
            payload["tools"] = _araclari_openai_formatina_donustur(arac_tanimlari)
        try:
            yanit = requests.post(f"{self.api_url}/api/chat", json=payload, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"Ollama API yanit hatasi: {yanit.status_code} - {yanit.text}")
            veri = yanit.json()
            mesaj_icerigi = veri.get("message", {})
            cevap = mesaj_icerigi.get("content", "")
            arac_cagrilari = mesaj_icerigi.get("tool_calls", [])
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("eval_count", 0), "arac_cagrilari": arac_cagrilari}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"API yanit zamani asimi: {self.zaman_asimi} saniye")

    def api_anahtari_kontrol(self):
        return True

    def model_bilgisi(self):
        try:
            yanit = requests.post(f"{self.api_url}/api/show", json={"name": self.model_adi}, timeout=10)
            veri = yanit.json()
            return {"model_adi": self.model_adi, "api_turu": "Ollama", "api_url": self.api_url, "parametre_sayisi": veri.get("parameters", "bilinmiyor")}
        except:
            return {"model_adi": self.model_adi, "api_turu": "Ollama", "api_url": self.api_url, "parametre_sayisi": "bilinmiyor"}


class OpenAIBaglayici:
    def __init__(self, model_adi="gpt-4o", api_anahtari=None, sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_anahtari = api_anahtari or os.environ.get("OPENAI_API_KEY", "")
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        self.api_anahtari_kontrol()
        try:
            import openai
            self.istemci = openai.OpenAI(api_key=self.api_anahtari, timeout=self.zaman_asimi)
            return True
        except ImportError:
            raise BaglantiHatasi("openai paketi yuklu degil. 'pip install openai' ile yukleyin.")

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        self.api_anahtari_kontrol()
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        try:
            yanit = self.istemci.chat.completions.create(model=self.model_adi, messages=mesaj_listesi, max_tokens=self.max_token, temperature=self.sicaklik)
            cevap = yanit.choices[0].message.content or ""
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": yanit.usage.total_tokens if yanit.usage else 0}
        except Exception as e:
            raise BaglantiHatasi(f"OpenAI API hatasi: {str(e)}")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        sonuclar = []
        gecmis = []
        for mesaj in mesaj_listesi:
            sonuc = self.mesaj_gonder(mesaj, gecmis)
            sonuclar.append(sonuc)
            gecmis.append({"role": "user", "content": mesaj})
            gecmis.append({"role": "assistant", "content": sonuc["yanit"]})
            if len(gecmis) > 40:
                gecmis = gecmis[-20:]
        return sonuclar

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        self.api_anahtari_kontrol()
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        try:
            kwargs = {"model": self.model_adi, "messages": mesaj_listesi, "max_tokens": self.max_token, "temperature": self.sicaklik}
            if arac_tanimlari:
                kwargs["tools"] = _araclari_openai_formatina_donustur(arac_tanimlari)
            yanit = self.istemci.chat.completions.create(**kwargs)
            secim = yanit.choices[0]
            cevap = secim.message.content or ""
            arac_cagrilari = []
            if secim.message.tool_calls:
                for tc in secim.message.tool_calls:
                    arac_cagrilari.append({"ad": tc.function.name, "parametreler": tc.function.arguments})
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": yanit.usage.total_tokens if yanit.usage else 0, "arac_cagrilari": arac_cagrilari}
        except Exception as e:
            raise BaglantiHatasi(f"OpenAI API hatasi: {str(e)}")

    def gorsel_gonder(self, metin, gorsel_base64, gorsel_formati="png"):
        self.api_anahtari_kontrol()
        mesaj_icerigi = [
            {"type": "text", "text": metin},
            {"type": "image_url", "image_url": {"url": f"data:image/{gorsel_formati};base64,{gorsel_base64}"}}
        ]
        try:
            yanit = self.istemci.chat.completions.create(
                model=self.model_adi, messages=[{"role": "user", "content": mesaj_icerigi}],
                max_tokens=self.max_token, temperature=self.sicaklik
            )
            cevap = yanit.choices[0].message.content
            return {"yanit": cevap, "model": self.model_adi, "token_sayisi": yanit.usage.total_tokens if yanit.usage else 0}
        except Exception as e:
            raise BaglantiHatasi(f"OpenAI gorsel API hatasi: {str(e)}")

    def api_anahtari_kontrol(self):
        if not self.api_anahtari:
            raise YetkilendirmeHatasi("OpenAI API anahtari bulunamadi. --api-anahtari parametresi ile belirtin veya OPENAI_API_KEY ortam degiskeni tanimlayin.")

    def model_bilgisi(self):
        return {"model_adi": self.model_adi, "api_turu": "OpenAI", "api_url": "https://api.openai.com/v1", "parametre_sayisi": "bilinmiyor"}


class GeminiBaglayici:
    def __init__(self, model_adi="gemini-2.0-flash", api_anahtari=None, sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_anahtari = api_anahtari or os.environ.get("GEMINI_API_KEY", "")
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        self.api_anahtari_kontrol()
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_anahtari)
            self.model = genai.GenerativeModel(self.model_adi)
            return True
        except ImportError:
            raise BaglantiHatasi("google-generativeai paketi yuklu degil. 'pip install google-generativeai' ile yukleyin.")

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        self.api_anahtari_kontrol()
        import google.generativeai as genai
        try:
            if self.sistem_promptu:
                sistemli_model = genai.GenerativeModel(self.model_adi, system_instruction=self.sistem_promptu)
            else:
                sistemli_model = self.model
            tam_mesaj = mesaj
            if gecmis:
                gecmis_metni = "\n".join([f"{g.get('role', 'user')}: {g.get('content', '')}" for g in gecmis])
                tam_mesaj = f"{gecmis_metni}\nuser: {mesaj}"
            yanit = sistemli_model.generate_content(tam_mesaj)
            cevap = yanit.text
            self.son_gecmis = [{"role": "user", "content": mesaj}, {"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": 0}
        except Exception as e:
            raise BaglantiHatasi(f"Gemini API hatasi: {str(e)}")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        sonuclar = []
        for mesaj in mesaj_listesi:
            sonuc = self.mesaj_gonder(mesaj)
            sonuclar.append(sonuc)
        return sonuclar

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        self.api_anahtari_kontrol()
        import google.generativeai as genai
        try:
            if self.sistem_promptu:
                sistemli_model = genai.GenerativeModel(self.model_adi, system_instruction=self.sistem_promptu)
            else:
                sistemli_model = self.model
            tam_mesaj = mesaj
            if gecmis:
                gecmis_metni = "\n".join([f"{g.get('role', 'user')}: {g.get('content', '')}" for g in gecmis])
                tam_mesaj = f"{gecmis_metni}\nuser: {mesaj}"
            yanit = sistemli_model.generate_content(tam_mesaj)
            cevap = yanit.text
            self.son_gecmis = [{"role": "user", "content": mesaj}, {"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": 0, "arac_cagrilari": []}
        except Exception as e:
            raise BaglantiHatasi(f"Gemini API hatasi: {str(e)}")

    def gorsel_gonder(self, metin, gorsel_base64, gorsel_formati="png"):
        self.api_anahtari_kontrol()
        import google.generativeai as genai
        try:
            if self.sistem_promptu:
                sistemli_model = genai.GenerativeModel(self.model_adi, system_instruction=self.sistem_promptu)
            else:
                sistemli_model = self.model
            gorsel_parca = {"mime_type": f"image/{gorsel_formati}", "data": gorsel_base64}
            yanit = sistemli_model.generate_content([metin, gorsel_parca])
            cevap = yanit.text
            return {"yanit": cevap, "model": self.model_adi, "token_sayisi": 0}
        except Exception as e:
            raise BaglantiHatasi(f"Gemini gorsel API hatasi: {str(e)}")

    def api_anahtari_kontrol(self):
        if not self.api_anahtari:
            raise YetkilendirmeHatasi("Gemini API anahtari bulunamadi. --api-anahtari parametresi ile belirtin veya GEMINI_API_KEY ortam degiskeni tanimlayin.")

    def model_bilgisi(self):
        return {"model_adi": self.model_adi, "api_turu": "Gemini", "api_url": "https://generativelanguage.googleapis.com", "parametre_sayisi": "bilinmiyor"}


class ClaudeBaglayici:
    def __init__(self, model_adi="claude-sonnet-5", api_anahtari=None, sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_anahtari = api_anahtari or os.environ.get("ANTHROPIC_API_KEY", "")
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        self.api_anahtari_kontrol()
        try:
            import anthropic
            self.istemci = anthropic.Anthropic(api_key=self.api_anahtari, timeout=self.zaman_asimi)
            return True
        except ImportError:
            raise BaglantiHatasi("anthropic paketi yuklu degil. 'pip install anthropic' ile yukleyin.")

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        self.api_anahtari_kontrol()
        mesaj_listesi = []
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        try:
            kwargs = {"model": self.model_adi, "max_tokens": self.max_token, "messages": mesaj_listesi}
            if self.sistem_promptu:
                kwargs["system"] = self.sistem_promptu
            yanit = self.istemci.messages.create(**kwargs)
            cevap = yanit.content[0].text
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": yanit.usage.output_tokens if hasattr(yanit, 'usage') else 0}
        except Exception as e:
            raise BaglantiHatasi(f"Claude API hatasi: {str(e)}")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        sonuclar = []
        gecmis = []
        for mesaj in mesaj_listesi:
            sonuc = self.mesaj_gonder(mesaj, gecmis)
            sonuclar.append(sonuc)
            gecmis.append({"role": "user", "content": mesaj})
            gecmis.append({"role": "assistant", "content": sonuc["yanit"]})
            if len(gecmis) > 40:
                gecmis = gecmis[-20:]
        return sonuclar

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        self.api_anahtari_kontrol()
        mesaj_listesi = []
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        try:
            kwargs = {"model": self.model_adi, "max_tokens": self.max_token, "messages": mesaj_listesi}
            if self.sistem_promptu:
                kwargs["system"] = self.sistem_promptu
            if arac_tanimlari:
                kwargs["tools"] = _araclari_claude_formatina_donustur(arac_tanimlari)
            yanit = self.istemci.messages.create(**kwargs)
            cevap = ""
            arac_cagrilari = []
            for blok in yanit.content:
                if blok.type == "text":
                    cevap += blok.text
                elif blok.type == "tool_use":
                    arac_cagrilari.append({"ad": blok.name, "parametreler": str(blok.input)})
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": yanit.usage.output_tokens if hasattr(yanit, 'usage') else 0, "arac_cagrilari": arac_cagrilari}
        except Exception as e:
            raise BaglantiHatasi(f"Claude API hatasi: {str(e)}")

    def gorsel_gonder(self, metin, gorsel_base64, gorsel_formati="png"):
        self.api_anahtari_kontrol()
        mesaj_icerigi = [
            {"type": "image", "source": {"type": "base64", "media_type": f"image/{gorsel_formati}", "data": gorsel_base64}},
            {"type": "text", "text": metin}
        ]
        try:
            kwargs = {"model": self.model_adi, "max_tokens": self.max_token, "messages": [{"role": "user", "content": mesaj_icerigi}]}
            if self.sistem_promptu:
                kwargs["system"] = self.sistem_promptu
            yanit = self.istemci.messages.create(**kwargs)
            cevap = ""
            for blok in yanit.content:
                if blok.type == "text":
                    cevap += blok.text
            return {"yanit": cevap, "model": self.model_adi, "token_sayisi": yanit.usage.output_tokens if hasattr(yanit, 'usage') else 0}
        except Exception as e:
            raise BaglantiHatasi(f"Claude gorsel API hatasi: {str(e)}")

    def api_anahtari_kontrol(self):
        if not self.api_anahtari:
            raise YetkilendirmeHatasi("Anthropic API anahtari bulunamadi. --api-anahtari parametresi ile belirtin veya ANTHROPIC_API_KEY ortam degiskeni tanimlayin.")

    def model_bilgisi(self):
        return {"model_adi": self.model_adi, "api_turu": "Claude (Anthropic)", "api_url": "https://api.anthropic.com", "parametre_sayisi": "bilinmiyor"}


class LMStudioBaglayici:
    def __init__(self, model_adi="local-model", api_url="http://localhost:1234/v1", sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_url = api_url.rstrip("/")
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        try:
            yanit = requests.get(f"{self.api_url}/models", timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"LM Studio baglantisi basarisiz: {self.api_url}")
            return True
        except requests.exceptions.ConnectionError:
            raise BaglantiHatasi(f"LM Studio'ya baglanilamadi: {self.api_url}")

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {"model": self.model_adi, "messages": mesaj_listesi, "temperature": self.sicaklik, "max_tokens": self.max_token}
        try:
            yanit = requests.post(f"{self.api_url}/chat/completions", json=payload, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"LM Studio API yanit hatasi: {yanit.status_code}")
            veri = yanit.json()
            cevap = veri["choices"][0]["message"]["content"]
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("usage", {}).get("total_tokens", 0)}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"LM Studio API yanit zamani asimi: {self.zaman_asimi} saniye")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        sonuclar = []
        gecmis = []
        for mesaj in mesaj_listesi:
            sonuc = self.mesaj_gonder(mesaj, gecmis)
            sonuclar.append(sonuc)
            gecmis.append({"role": "user", "content": mesaj})
            gecmis.append({"role": "assistant", "content": sonuc["yanit"]})
            if len(gecmis) > 40:
                gecmis = gecmis[-20:]
        return sonuclar

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {"model": self.model_adi, "messages": mesaj_listesi, "temperature": self.sicaklik, "max_tokens": self.max_token}
        if arac_tanimlari:
            payload["tools"] = _araclari_openai_formatina_donustur(arac_tanimlari)
        try:
            yanit = requests.post(f"{self.api_url}/chat/completions", json=payload, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"LM Studio API yanit hatasi: {yanit.status_code}")
            veri = yanit.json()
            secim = veri["choices"][0]
            mesaj_icerigi = secim.get("message", {})
            cevap = mesaj_icerigi.get("content", "")
            arac_cagrilari = mesaj_icerigi.get("tool_calls", [])
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("usage", {}).get("total_tokens", 0), "arac_cagrilari": arac_cagrilari}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"LM Studio API yanit zamani asimi: {self.zaman_asimi} saniye")

    def api_anahtari_kontrol(self):
        return True

    def model_bilgisi(self):
        try:
            yanit = requests.get(f"{self.api_url}/models", timeout=10)
            veri = yanit.json()
            model_adi = veri.get("data", [{}])[0].get("id", self.model_adi) if veri.get("data") else self.model_adi
            return {"model_adi": model_adi, "api_turu": "LM Studio (OpenAI uyumlu)", "api_url": self.api_url, "parametre_sayisi": "bilinmiyor"}
        except:
            return {"model_adi": self.model_adi, "api_turu": "LM Studio", "api_url": self.api_url, "parametre_sayisi": "bilinmiyor"}


class GenericOpenAIBaglayici:
    def __init__(self, model_adi="model", api_url="http://localhost:8000/v1", api_anahtari="not-needed", sistem_promptu="", zaman_asimi=30, max_token=2048, sicaklik=0.7):
        self.model_adi = model_adi
        self.api_url = api_url.rstrip("/")
        self.api_anahtari = api_anahtari
        self.sistem_promptu = sistem_promptu
        self.zaman_asimi = zaman_asimi
        self.max_token = max_token
        self.sicaklik = sicaklik
        self.son_gecmis = []

    def baglan(self):
        try:
            yanit = requests.get(f"{self.api_url}/models", timeout=self.zaman_asimi)
            return True
        except:
            return True

    def sistem_promptu_ayarla(self, prompt):
        self.sistem_promptu = prompt

    def mesaj_gonder(self, mesaj, gecmis=None):
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {"model": self.model_adi, "messages": mesaj_listesi, "temperature": self.sicaklik, "max_tokens": self.max_token}
        basliklar = {"Authorization": f"Bearer {self.api_anahtari}", "Content-Type": "application/json"}
        try:
            yanit = requests.post(f"{self.api_url}/chat/completions", json=payload, headers=basliklar, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"API yanit hatasi: {yanit.status_code} - {yanit.text}")
            veri = yanit.json()
            cevap = veri["choices"][0]["message"]["content"]
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("usage", {}).get("total_tokens", 0)}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"API yanit zamani asimi: {self.zaman_asimi} saniye")

    def coklu_mesaj_gonder(self, mesaj_listesi):
        return [self.mesaj_gonder(m) for m in mesaj_listesi]

    def mesaj_gonder_tool_ile(self, mesaj, arac_tanimlari=None, gecmis=None):
        mesaj_listesi = []
        if self.sistem_promptu:
            mesaj_listesi.append({"role": "system", "content": self.sistem_promptu})
        if gecmis:
            for g in gecmis:
                mesaj_listesi.append({"role": g.get("role", "user"), "content": g.get("content", "")})
        mesaj_listesi.append({"role": "user", "content": mesaj})
        payload = {"model": self.model_adi, "messages": mesaj_listesi, "temperature": self.sicaklik, "max_tokens": self.max_token}
        if arac_tanimlari:
            payload["tools"] = _araclari_openai_formatina_donustur(arac_tanimlari)
        basliklar = {"Authorization": f"Bearer {self.api_anahtari}", "Content-Type": "application/json"}
        try:
            yanit = requests.post(f"{self.api_url}/chat/completions", json=payload, headers=basliklar, timeout=self.zaman_asimi)
            if yanit.status_code != 200:
                raise BaglantiHatasi(f"API yanit hatasi: {yanit.status_code} - {yanit.text}")
            veri = yanit.json()
            secim = veri["choices"][0]
            mesaj_icerigi = secim.get("message", {})
            cevap = mesaj_icerigi.get("content", "")
            arac_cagrilari = mesaj_icerigi.get("tool_calls", [])
            self.son_gecmis = mesaj_listesi + [{"role": "assistant", "content": cevap}]
            return {"yanit": cevap, "model": self.model_adi, "gecikme_ms": 0, "token_sayisi": veri.get("usage", {}).get("total_tokens", 0), "arac_cagrilari": arac_cagrilari}
        except requests.exceptions.Timeout:
            raise ZamanAsimiHatasi(f"API yanit zamani asimi: {self.zaman_asimi} saniye")

    def api_anahtari_kontrol(self):
        return True

    def model_bilgisi(self):
        return {"model_adi": self.model_adi, "api_turu": "Generic OpenAI Uyumlu", "api_url": self.api_url, "parametre_sayisi": "bilinmiyor"}


BAGLAYICI_HARITASI = {
    "ollama": OllamaBaglayici,
    "openai": OpenAIBaglayici,
    "gemini": GeminiBaglayici,
    "claude": ClaudeBaglayici,
    "lmstudio": LMStudioBaglayici,
    "generic": GenericOpenAIBaglayici,
}


def _araclari_openai_formatina_donustur(arac_tanimlari):
    if not arac_tanimlari:
        return None
    openai_araclari = []
    for arac in arac_tanimlari:
        ozellikler = {}
        for param_adi, param_detay in arac.get("parametreler", {}).items():
            ozellikler[param_adi] = {"type": param_detay.get("tip", "string"), "description": param_detay.get("aciklama", "")}
        openai_arac = {"type": "function", "function": {"name": arac.get("ad", ""), "description": arac.get("aciklama", ""), "parameters": {"type": "object", "properties": ozellikler, "required": list(ozellikler.keys()) if ozellikler else []}}}
        openai_araclari.append(openai_arac)
    return openai_araclari


def _araclari_claude_formatina_donustur(arac_tanimlari):
    if not arac_tanimlari:
        return None
    claude_araclari = []
    for arac in arac_tanimlari:
        ozellikler = {}
        for param_adi, param_detay in arac.get("parametreler", {}).items():
            ozellikler[param_adi] = {"type": param_detay.get("tip", "string"), "description": param_detay.get("aciklama", "")}
        claude_arac = {"name": arac.get("ad", ""), "description": arac.get("aciklama", ""), "input_schema": {"type": "object", "properties": ozellikler, "required": list(ozellikler.keys()) if ozellikler else []}}
        claude_araclari.append(claude_arac)
    return claude_araclari


def baglayici_olustur(hedef, **kwargs):
    if hedef not in BAGLAYICI_HARITASI:
        raise BaglantiHatasi(f"Desteklenmeyen hedef: {hedef}. Desteklenenler: {', '.join(BAGLAYICI_HARITASI.keys())}")
    baglayici_sinifi = BAGLAYICI_HARITASI[hedef]
    return baglayici_sinifi(**kwargs)
