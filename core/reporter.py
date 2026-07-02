import json
import os
from datetime import datetime
from pathlib import Path

CIKTI_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cikti", "raporlar")

RAPOR_GOVDE_SABLONU = """
<div class="header">
    <h1>Yargu Framework v2.9.0</h1>
    <p class="subtitle">LLM Kirmizi Takim (Red Team) Test Raporu</p>
    <p class="author">AltaySec Bunyesinde Gelistirilmistir | Arda Mecik</p>
</div>

<div class="ozet">
    <h2>Yurutucu Ozet</h2>
    <div class="ozet-kartlari">
        <div class="kart {skor_renk}">
            <span class="kart-deger">{genel_skor}/100</span>
            <span class="kart-etiket">Guvenlik Skoru</span>
        </div>
        <div class="kart">
            <span class="kart-deger">{test_sayisi}</span>
            <span class="kart-etiket">Toplam Test</span>
        </div>
        <div class="kart {saldiri_renk}">
            <span class="kart-deger">{basarili_saldiri_sayisi}</span>
            <span class="kart-etiket">Basarili Saldiri</span>
        </div>
        <div class="kart">
            <span class="kart-deger">{savunma_orani}%</span>
            <span class="kart-etiket">Savunma Orani</span>
        </div>
    </div>
</div>

<div class="hedef-bilgisi">
    <h2>Hedef Bilgileri</h2>
    <table>
        {hedef_bilgisi_satirlari}
    </table>
</div>

<div class="kategori-bazli">
    <h2>Kategori Bazli Sonuclar</h2>
    <table>
        <tr><th>Kategori</th><th>Test Sayisi</th><th>Basarili Saldiri</th><th>Basari Orani</th></tr>
        {kategori_satirlari}
    </table>
</div>

<div class="zafiyet-dagilimi">
    <h2>Zafiyet Seviyesi Dagilimi</h2>
    <table>
        <tr><th>Seviye</th><th>Adet</th></tr>
        {zafiyet_satirlari}
    </table>
</div>

<div class="test-detaylari">
    <h2>Test Detaylari</h2>
    {test_kartlari}
</div>

<div class="footer">
    <p>Yargu Framework v2.9.0 - AltaySec Bunyesinde Gelistirilmistir | Arda Mecik</p>
    <p>Rapor Olusturma: {rapor_tarihi}</p>
    <p>Test Baslangic: {baslangic_zamani} | Bitis: {bitis_zamani}</p>
</div>
"""

TEST_KARTI_SABLONU = """
<div class="test-karti {zafiyet_sinifi}">
    <div class="test-baslik">
        <span class="test-id">#{test_no}</span>
        <span class="test-kategori">{kategori}</span>
        <span class="zafiyet-etiketi {zafiyet_sinifi}">{zafiyet_durumu}</span>
    </div>
    <div class="test-icerik">
        <div class="test-payload">
            <strong>Payload:</strong>
            <pre>{payload}</pre>
        </div>
        <div class="test-yanit">
            <strong>Yanit:</strong>
            <pre>{yanit}</pre>
        </div>
        <div class="test-meta">
            <span>Zafiyet Turu: {zafiyet_turu}</span>
            <span>Seviye: {zafiyet_seviyesi}</span>
            <span>Skor Etkisi: {skor_etkisi}</span>
            <span>Reddedildi: {reddedildi}</span>
            {kaynak_ajan_satiri}
        </div>
    </div>
</div>
"""

HTML_SABLONU = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yargu Framework - LLM Kirmizi Takim Raporu</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 12px; padding: 30px; text-align: center; margin-bottom: 24px; }}
        .header h1 {{ font-size: 2em; color: #f59e0b; margin-bottom: 8px; }}
        .header .subtitle {{ font-size: 1.1em; color: #94a3b8; }}
        .header .author {{ font-size: 0.9em; color: #64748b; margin-top: 8px; }}
        .ozet {{ margin-bottom: 24px; }}
        .ozet h2, .hedef-bilgisi h2, .kategori-bazli h2, .zafiyet-dagilimi h2, .test-detaylari h2 {{ color: #f59e0b; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        .ozet-kartlari {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
        .kart {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; text-align: center; }}
        .kart-deger {{ display: block; font-size: 2em; font-weight: bold; }}
        .kart-etiket {{ display: block; color: #64748b; margin-top: 4px; font-size: 0.85em; }}
        .kart.tehlike .kart-deger {{ color: #ef4444; }}
        .kart.basarili .kart-deger {{ color: #22c55e; }}
        .kart.uyari .kart-deger {{ color: #f59e0b; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 10px; overflow: hidden; border: 1px solid #334155; }}
        th {{ background: #334155; color: #f59e0b; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-top: 1px solid #1e293b; }}
        tr:nth-child(even) {{ background: #0f172a; }}
        .test-karti {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; margin-bottom: 12px; overflow: hidden; }}
        .test-karti.zafiyetli {{ border-left: 4px solid #ef4444; }}
        .test-karti.guvenli {{ border-left: 4px solid #22c55e; }}
        .test-karti.belirsiz {{ border-left: 4px solid #f59e0b; }}
        .test-baslik {{ padding: 12px 16px; background: #334155; display: flex; align-items: center; gap: 12px; cursor: pointer; }}
        .test-baslik:hover {{ background: #3b4f6b; }}
        .test-id {{ background: #0f172a; padding: 4px 10px; border-radius: 20px; font-weight: bold; color: #f59e0b; }}
        .test-kategori {{ text-transform: uppercase; font-size: 0.75em; color: #94a3b8; letter-spacing: 1px; }}
        .zafiyet-etiketi {{ padding: 4px 12px; border-radius: 20px; font-size: 0.8em; margin-left: auto; }}
        .zafiyet-etiketi.zafiyetli {{ background: #7f1d1d; color: #fca5a5; }}
        .zafiyet-etiketi.guvenli {{ background: #14532d; color: #86efac; }}
        .zafiyet-etiketi.belirsiz {{ background: #713f12; color: #fde68a; }}
        .test-icerik {{ padding: 16px; display: none; }}
        .test-karti.acik .test-icerik {{ display: block; }}
        .test-icerik pre {{ background: #0f172a; padding: 12px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; font-size: 0.85em; margin-top: 8px; border: 1px solid #334155; }}
        .test-meta {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; color: #64748b; font-size: 0.85em; }}
        .footer {{ text-align: center; color: #475569; font-size: 0.8em; margin-top: 40px; padding: 20px; border-top: 1px solid #1e293b; }}
        .grafik-konteyner {{ background: #1e293b; border-radius: 10px; padding: 20px; margin: 16px 0; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        {icerik}
    </div>
    <script>
        document.querySelectorAll('.test-baslik').forEach(function(baslik) {{
            baslik.addEventListener('click', function() {{
                this.parentElement.classList.toggle('acik');
            }});
        }});
    </script>
</body>
</html>
"""


class Raporlayici:
    def __init__(self, sonuclar=None, hedef_bilgisi=None, baslangic_zamani=None, bitis_zamani=None):
        self.sonuclar = sonuclar or []
        self.hedef_bilgisi = hedef_bilgisi or {}
        self.baslangic_zamani = baslangic_zamani or datetime.now()
        self.bitis_zamani = bitis_zamani or datetime.now()

    def ozet_rapor_olustur(self, skor_ozeti=None):
        if skor_ozeti is None:
            from .evaluator import Degerlendirici
            degerlendirici = Degerlendirici()
            degerlendirici.sonuclar = self.sonuclar
            skor_ozeti = degerlendirici.guvenlik_skoru_hesapla()
        cizgiler = "=" * 60
        ozet = [
            f"\n{cizgiler}",
            "  YARGU FRAMEWORK v2.9.0 - TEST RAPORU",
            f"  AltaySec Bunyesinde Gelistirilmistir | Arda Mecik",
            f"{cizgiler}",
            f"  Genel Guvenlik Skoru: {skor_ozeti['genel_skor']}/100",
            f"  Toplam Test: {skor_ozeti['test_sayisi']}",
            f"  Basarili Saldiri: {skor_ozeti['basarili_saldiri_sayisi']}",
            f"  Savunma Orani: %{100 - skor_ozeti['basarili_saldiri_sayisi'] / max(1, skor_ozeti['test_sayisi']) * 100:.1f}",
            f"{cizgiler}",
            "  Kategori Bazli Sonuclar:",
        ]
        for kat, veri in skor_ozeti.get("kategori_bazli", {}).items():
            ozet.append(f"    {kat}: {veri['basarili']}/{veri['test_sayisi']} basarili")
        ozet.append(f"{cizgiler}")
        ozet.append("  Zafiyet Dagilimi:")
        for seviye, adet in skor_ozeti.get("zafiyet_dagilimi", {}).items():
            if adet > 0:
                ozet.append(f"    {seviye.upper()}: {adet} adet")
        ozet.append(f"{cizgiler}")
        ozet.append(f"  Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        ozet.append(f"  Yargu Framework - AltaySec Bunyesinde Gelistirilmistir | Arda Mecik")
        ozet.append(f"{cizgiler}\n")
        return "\n".join(ozet)

    def html_raporu_olustur(self, dosya_yolu=None, skor_ozeti=None):
        import html as html_lib
        if skor_ozeti is None:
            from .evaluator import Degerlendirici
            degerlendirici = Degerlendirici()
            degerlendirici.sonuclar = self.sonuclar
            skor_ozeti = degerlendirici.guvenlik_skoru_hesapla()
        genel_skor = skor_ozeti["genel_skor"]
        skor_renk = "tehlike" if genel_skor < 50 else ("uyari" if genel_skor < 75 else "basarili")
        basarili = skor_ozeti["basarili_saldiri_sayisi"]
        saldiri_renk = "tehlike" if basarili > skor_ozeti["test_sayisi"] * 0.5 else ("uyari" if basarili > 0 else "basarili")
        savunma_orani = round(100 - basarili / max(1, skor_ozeti["test_sayisi"]) * 100, 1)
        hedef_satirlari = ""
        for anahtar, deger in self.hedef_bilgisi.items():
            hedef_satirlari += f"<tr><td><strong>{html_lib.escape(str(anahtar))}</strong></td><td>{html_lib.escape(str(deger))}</td></tr>\n"
        if not hedef_satirlari:
            hedef_satirlari = "<tr><td colspan='2'>Hedef bilgisi belirtilmedi</td></tr>"
        kategori_satirlari = ""
        for kat, veri in skor_ozeti.get("kategori_bazli", {}).items():
            oran = round(veri["basarili"] / max(1, veri["test_sayisi"]) * 100, 1)
            kategori_satirlari += f"<tr><td>{kat}</td><td>{veri['test_sayisi']}</td><td>{veri['basarili']}</td><td>%{oran}</td></tr>\n"
        if not kategori_satirlari:
            kategori_satirlari = "<tr><td colspan='4'>Kategori verisi bulunamadi</td></tr>"
        zafiyet_satirlari = ""
        seviye_renkleri = {"kritik": "#ef4444", "yuksek": "#f97316", "orta": "#f59e0b", "dusuk": "#22c55e"}
        for seviye, adet in skor_ozeti.get("zafiyet_dagilimi", {}).items():
            renk = seviye_renkleri.get(seviye, "#94a3b8")
            zafiyet_satirlari += f"<tr><td><span style='color:{renk};font-weight:bold;'>{seviye.upper()}</span></td><td>{adet}</td></tr>\n"
        test_kartlari = ""
        for i, sonuc in enumerate(self.sonuclar, 1):
            zafiyet_var = sonuc.get("zafiyet_var", False)
            zafiyet_sinifi = "zafiyetli" if zafiyet_var else "guvenli"
            zafiyet_durumu = "ZAFIYET BULUNDU" if zafiyet_var else "GUVENLI"
            kaynak_ajan = sonuc.get("kaynak_ajan", "")
            kaynak_ajan_satiri = f"<span>Ajan: {html_lib.escape(str(kaynak_ajan))}</span>" if kaynak_ajan else ""
            test_kartlari += TEST_KARTI_SABLONU.format(
                test_no=i,
                kategori=sonuc.get("saldiri_turu", "bilinmiyor").upper(),
                zafiyet_sinifi=zafiyet_sinifi,
                zafiyet_durumu=zafiyet_durumu,
                payload=html_lib.escape(sonuc.get("payload", "Belirtilmedi")[:500]),
                yanit=html_lib.escape(sonuc.get("yanit", "Yanit alinamadi")[:500]),
                zafiyet_turu=sonuc.get("zafiyet_turu", "bilinmiyor"),
                zafiyet_seviyesi=sonuc.get("zafiyet_seviyesi", "belirsiz").upper(),
                skor_etkisi=sonuc.get("guvenlik_skoru_etkisi", 0),
                reddedildi="Evet" if sonuc.get("reddedildi") else "Hayir",
                kaynak_ajan_satiri=kaynak_ajan_satiri
            )
        icerik = RAPOR_GOVDE_SABLONU.format(
            genel_skor=genel_skor,
            skor_renk=skor_renk,
            test_sayisi=skor_ozeti["test_sayisi"],
            basarili_saldiri_sayisi=basarili,
            saldiri_renk=saldiri_renk,
            savunma_orani=savunma_orani,
            hedef_bilgisi_satirlari=hedef_satirlari,
            kategori_satirlari=kategori_satirlari,
            zafiyet_satirlari=zafiyet_satirlari,
            test_kartlari=test_kartlari,
            rapor_tarihi=datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            baslangic_zamani=self.baslangic_zamani.strftime("%d.%m.%Y %H:%M:%S") if hasattr(self.baslangic_zamani, 'strftime') else str(self.baslangic_zamani),
            bitis_zamani=self.bitis_zamani.strftime("%d.%m.%Y %H:%M:%S") if hasattr(self.bitis_zamani, 'strftime') else str(self.bitis_zamani)
        )
        html = HTML_SABLONU.format(icerik=icerik)
        if dosya_yolu:
            Path(dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(html)
            return dosya_yolu
        return html

    def json_raporu_olustur(self, dosya_yolu=None, skor_ozeti=None):
        if skor_ozeti is None:
            from .evaluator import Degerlendirici
            degerlendirici = Degerlendirici()
            degerlendirici.sonuclar = self.sonuclar
            skor_ozeti = degerlendirici.guvenlik_skoru_hesapla()
        rapor = {
            "arac": "Yargu Framework v2.9.0",
            "gelistirici": "AltaySec | Arda Mecik",
            "rapor_tarihi": datetime.now().isoformat(),
            "test_baslangic": self.baslangic_zamani.isoformat() if hasattr(self.baslangic_zamani, 'isoformat') else str(self.baslangic_zamani),
            "test_bitis": self.bitis_zamani.isoformat() if hasattr(self.bitis_zamani, 'isoformat') else str(self.bitis_zamani),
            "hedef_bilgisi": self.hedef_bilgisi,
            "skor_ozeti": skor_ozeti,
            "test_sonuclari": self.sonuclar
        }
        if dosya_yolu:
            Path(dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(rapor, f, ensure_ascii=False, indent=2)
            return dosya_yolu
        return json.dumps(rapor, ensure_ascii=False, indent=2)

    def markdown_raporu_olustur(self, dosya_yolu=None, skor_ozeti=None):
        if skor_ozeti is None:
            from .evaluator import Degerlendirici
            degerlendirici = Degerlendirici()
            degerlendirici.sonuclar = self.sonuclar
            skor_ozeti = degerlendirici.guvenlik_skoru_hesapla()
        md = []
        md.append("# Yargu Framework v2.9.0 - Test Raporu\n")
        md.append("**AltaySec Bunyesinde Gelistirilmistir | Arda Mecik**\n")
        md.append("---\n")
        md.append("## Yurutucu Ozet\n")
        md.append(f"- **Genel Guvenlik Skoru:** {skor_ozeti['genel_skor']}/100")
        md.append(f"- **Toplam Test:** {skor_ozeti['test_sayisi']}")
        md.append(f"- **Basarili Saldiri:** {skor_ozeti['basarili_saldiri_sayisi']}")
        md.append(f"- **Savunma Orani:** %{100 - skor_ozeti['basarili_saldiri_sayisi'] / max(1, skor_ozeti['test_sayisi']) * 100:.1f}\n")
        if self.hedef_bilgisi:
            md.append("## Hedef Bilgileri\n")
            for anahtar, deger in self.hedef_bilgisi.items():
                md.append(f"- **{anahtar}:** {deger}")
            md.append("")
        md.append("## Kategori Bazli Sonuclar\n")
        md.append("| Kategori | Test | Basarili | Oran |")
        md.append("|----------|------|----------|------|")
        for kat, veri in skor_ozeti.get("kategori_bazli", {}).items():
            oran = round(veri["basarili"] / max(1, veri["test_sayisi"]) * 100, 1)
            md.append(f"| {kat} | {veri['test_sayisi']} | {veri['basarili']} | %{oran} |")
        md.append("")
        md.append("## Zafiyet Dagilimi\n")
        md.append("| Seviye | Adet |")
        md.append("|--------|------|")
        for seviye, adet in skor_ozeti.get("zafiyet_dagilimi", {}).items():
            if adet > 0:
                md.append(f"| {seviye.upper()} | {adet} |")
        md.append("")
        md.append("## Test Detaylari\n")
        for i, sonuc in enumerate(self.sonuclar, 1):
            durum = "[-] ZAFIYET BULUNDU" if sonuc.get("zafiyet_var") else "[+] GUVENLI"
            md.append(f"### Test #{i} - {durum}\n")
            md.append(f"- **Kategori:** {sonuc.get('saldiri_turu', 'bilinmiyor')}")
            md.append(f"- **Zafiyet Turu:** {sonuc.get('zafiyet_turu', 'bilinmiyor')}")
            md.append(f"- **Seviye:** {sonuc.get('zafiyet_seviyesi', 'belirsiz').upper()}")
            md.append(f"- **Reddedildi:** {'Evet' if sonuc.get('reddedildi') else 'Hayir'}")
            md.append(f"\n**Payload:**\n```\n{sonuc.get('payload', 'Belirtilmedi')[:300]}\n```")
            md.append(f"\n**Yanit:**\n```\n{sonuc.get('yanit', 'Yanit alinamadi')[:300]}\n```\n")
        md.append("---\n")
        md.append(f"*Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}*")
        md.append("*Yargu Framework v2.9.0 - AltaySec Bunyesinde Gelistirilmistir | Arda Mecik*")
        icerik = "\n".join(md)
        if dosya_yolu:
            Path(dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(icerik)
            return dosya_yolu
        return icerik

    def rapor_uret(self, format="html", cikti_dosyasi=None, skor_ozeti=None):
        ureticiler = {
            "html": self.html_raporu_olustur,
            "json": self.json_raporu_olustur,
            "markdown": self.markdown_raporu_olustur
        }
        if format not in ureticiler:
            raise ValueError(f"Desteklenmeyen rapor formati: {format}. Desteklenenler: {', '.join(ureticiler.keys())}")
        return ureticiler[format](dosya_yolu=cikti_dosyasi, skor_ozeti=skor_ozeti)

    def hepsini_uret(self, cikti_dizini=None, dosya_adi=None):
        if cikti_dizini is None:
            cikti_dizini = CIKTI_DIZINI
        if dosya_adi is None:
            dosya_adi = f"yargu_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        Path(cikti_dizini).mkdir(parents=True, exist_ok=True)
        from .evaluator import Degerlendirici
        degerlendirici = Degerlendirici()
        degerlendirici.sonuclar = self.sonuclar
        skor_ozeti = degerlendirici.guvenlik_skoru_hesapla()
        sonuclar = {}
        for format in ["html", "json", "markdown"]:
            dosya_yolu = os.path.join(cikti_dizini, f"{dosya_adi}.{format}")
            self.rapor_uret(format=format, cikti_dosyasi=dosya_yolu, skor_ozeti=skor_ozeti)
            sonuclar[format] = dosya_yolu
        return sonuclar
