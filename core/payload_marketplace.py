import json
import os
import time
import random
from datetime import datetime, timedelta

VERI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri")
MARKETPLACE_DOSYASI = os.path.join(VERI_DIZINI, "marketplace_veri.json")

VARSAYILAN_MARKETPLACE = {
    "payloadlar": [],
    "oylamalar": {},
    "model_basari": {},
    "istatistikler": {"toplam_payload": 0, "toplam_oy": 0, "son_guncelleme": None}
}


def _marketplace_yukle():
    try:
        with open(MARKETPLACE_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(VARSAYILAN_MARKETPLACE)


def _marketplace_kaydet(veri):
    os.makedirs(os.path.dirname(MARKETPLACE_DOSYASI), exist_ok=True)
    with open(MARKETPLACE_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


class PayloadMarketplace:
    def __init__(self):
        self.veri = _marketplace_yukle()
        if not self.veri.get("payloadlar"):
            self.veri = dict(VARSAYILAN_MARKETPLACE)

    def payload_paylas(self, payload, lisans="MIT", kullanici="anonim"):
        yeni = {
            "id": f"mp-{int(time.time())}-{random.randint(100, 999)}",
            "ad": payload.get("ad", "Isimsiz Payload"),
            "kategori": payload.get("kategori", "jailbreak"),
            "dil": payload.get("dil", "tr"),
            "sablon": payload.get("sablon", ""),
            "zorluk": payload.get("zorluk", "orta"),
            "lisans": lisans,
            "kullanici": kullanici,
            "paylasim_tarihi": datetime.now().isoformat(),
            "indirme_sayisi": 0,
            "begeni_sayisi": 0,
            "versiyon": 1,
            "etiketler": payload.get("etiketler", [])
        }
        self.veri["payloadlar"].append(yeni)
        self.veri["istatistikler"]["toplam_payload"] = len(self.veri["payloadlar"])
        self.veri["istatistikler"]["son_guncelleme"] = datetime.now().isoformat()
        _marketplace_kaydet(self.veri)
        return yeni

    def payload_ara(self, kategori=None, dil=None, zorluk=None, etiket=None, siralama="yeni"):
        sonuclar = list(self.veri["payloadlar"])
        if kategori:
            sonuclar = [p for p in sonuclar if p.get("kategori") == kategori]
        if dil:
            sonuclar = [p for p in sonuclar if p.get("dil") == dil]
        if zorluk:
            sonuclar = [p for p in sonuclar if p.get("zorluk") == zorluk]
        if etiket:
            sonuclar = [p for p in sonuclar if etiket in p.get("etiketler", [])]
        if siralama == "yeni":
            sonuclar.sort(key=lambda p: p.get("paylasim_tarihi", ""), reverse=True)
        elif siralama == "populer":
            sonuclar.sort(key=lambda p: p.get("begeni_sayisi", 0), reverse=True)
        elif siralama == "cok_indirilen":
            sonuclar.sort(key=lambda p: p.get("indirme_sayisi", 0), reverse=True)
        return sonuclar

    def trending_payloadlar_getir(self, kategori=None, zaman_araligi="haftalik"):
        simdi = datetime.now()
        if zaman_araligi == "haftalik":
            esik = simdi - timedelta(days=7)
        elif zaman_araligi == "aylik":
            esik = simdi - timedelta(days=30)
        else:
            esik = simdi - timedelta(days=1)
        adaylar = self.payload_ara(kategori=kategori)
        son_donem = [p for p in adaylar if p.get("paylasim_tarihi", "2000") >= esik.isoformat()]
        son_donem.sort(key=lambda p: (p.get("begeni_sayisi", 0) * 2 + p.get("indirme_sayisi", 0)), reverse=True)
        return son_donem[:20]

    def payload_oy_ver(self, payload_id, begeni=True):
        if payload_id not in self.veri["oylamalar"]:
            self.veri["oylamalar"][payload_id] = {"begeni": 0, "begenmeme": 0}
        if begeni:
            self.veri["oylamalar"][payload_id]["begeni"] += 1
        else:
            self.veri["oylamalar"][payload_id]["begenmeme"] += 1
        for p in self.veri["payloadlar"]:
            if p["id"] == payload_id:
                p["begeni_sayisi"] = self.veri["oylamalar"][payload_id]["begeni"]
                break
        self.veri["istatistikler"]["toplam_oy"] = sum(1 for _ in self.veri["oylamalar"])
        _marketplace_kaydet(self.veri)
        return self.veri["oylamalar"][payload_id]

    def payload_indir(self, payload_id):
        for p in self.veri["payloadlar"]:
            if p["id"] == payload_id:
                p["indirme_sayisi"] += 1
                _marketplace_kaydet(self.veri)
                return p
        return None

    def model_bazli_basari_siralamasi(self, model_adi=None):
        siralamalar = []
        for pid, basarilar in self.veri.get("model_basari", {}).items():
            for model, veri in basarilar.items():
                if model_adi is None or model == model_adi:
                    siralamalar.append({"payload_id": pid, "model": model, "basarili": veri.get("basarili", 0), "basarisiz": veri.get("basarisiz", 0)})
        siralamalar.sort(key=lambda s: s["basarili"] / max(s["basarili"] + s["basarisiz"], 1), reverse=True)
        return siralamalar[:50]

    def basari_raporla(self, payload_id, model_adi, basarili=True):
        if payload_id not in self.veri["model_basari"]:
            self.veri["model_basari"][payload_id] = {}
        if model_adi not in self.veri["model_basari"][payload_id]:
            self.veri["model_basari"][payload_id][model_adi] = {"basarili": 0, "basarisiz": 0}
        if basarili:
            self.veri["model_basari"][payload_id][model_adi]["basarili"] += 1
        else:
            self.veri["model_basari"][payload_id][model_adi]["basarisiz"] += 1
        _marketplace_kaydet(self.veri)

    def topluluk_istatistikleri(self):
        payloadlar = self.veri.get("payloadlar", [])
        if not payloadlar:
            return {"toplam": 0, "kategori_bazli": {}, "dil_bazli": {}, "en_populer": None}
        kat_bazli = {}
        dil_bazli = {}
        for p in payloadlar:
            kat = p.get("kategori", "diger")
            dil = p.get("dil", "tr")
            kat_bazli[kat] = kat_bazli.get(kat, 0) + 1
            dil_bazli[dil] = dil_bazli.get(dil, 0) + 1
        en_populer = max(payloadlar, key=lambda p: p.get("begeni_sayisi", 0)) if payloadlar else None
        return {"toplam": len(payloadlar), "kategori_bazli": kat_bazli, "dil_bazli": dil_bazli, "en_populer": en_populer["ad"] if en_populer else None, "son_guncelleme": self.veri["istatistikler"]["son_guncelleme"]}

    def abonelik_akisi_olustur(self, kategoriler=None, diller=None, limit=20):
        adaylar = self.payload_ara(siralama="yeni")
        if kategoriler:
            adaylar = [p for p in adaylar if p.get("kategori") in kategoriler]
        if diller:
            adaylar = [p for p in adaylar if p.get("dil") in diller]
        return adaylar[:limit]

    def otomatik_guncelleme_denetle(self, son_kontrol_tarihi=None):
        if son_kontrol_tarihi is None:
            return {"guncelleme_var": len(self.veri["payloadlar"]) > 0}
        yeni_payloadlar = [p for p in self.veri["payloadlar"] if p.get("paylasim_tarihi", "2000") > son_kontrol_tarihi]
        return {"guncelleme_var": len(yeni_payloadlar) > 0, "yeni_payload_sayisi": len(yeni_payloadlar), "yeni_payloadlar": yeni_payloadlar[:10]}
