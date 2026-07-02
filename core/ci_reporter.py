import os
import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


class CIReporter:
    def __init__(self, esik_degeri=70):
        self.esik_degeri = esik_degeri

    def junit_xml_uret(self, sonuclar, cikti_yolu, test_adi="Yargu LLM Security Test"):
        test_sayisi = len(sonuclar)
        basarisiz_sayisi = sum(1 for s in sonuclar if s.get("zafiyet_var"))
        kok = Element("testsuite")
        kok.set("name", test_adi)
        kok.set("tests", str(test_sayisi))
        kok.set("failures", str(basarisiz_sayisi))
        kok.set("errors", "0")
        kok.set("time", "0.0")
        kok.set("timestamp", datetime.now().isoformat())
        for sonuc in sonuclar:
            test_case = SubElement(kok, "testcase")
            test_case.set("name", sonuc.get("test_id", "bilinmiyor"))
            test_case.set("classname", sonuc.get("saldiri_turu", "genel"))
            if sonuc.get("zafiyet_var"):
                hata = SubElement(test_case, "failure")
                hata.set("message", f"ZAFIYET BULUNDU: {sonuc.get('zafiyet_seviyesi', 'bilinmiyor')}")
                hata.set("type", sonuc.get("zafiyet_turu", "bilinmiyor"))
                hata.text = sonuc.get("payload", "")[:500]
        ham_xml = tostring(kok, encoding="unicode")
        guzel_xml = parseString(ham_xml).toprettyxml(indent="  ")
        Path(cikti_yolu).parent.mkdir(parents=True, exist_ok=True)
        with open(cikti_yolu, "w", encoding="utf-8") as f:
            f.write(guzel_xml)
        return cikti_yolu

    def json_summary_uret(self, sonuclar, skor_ozeti=None):
        ozet = {
            "tool": "Yargu Framework v2.9.0",
            "timestamp": datetime.now().isoformat(),
            "score": skor_ozeti.get("genel_skor", 0) if skor_ozeti else 0,
            "total_tests": len(sonuclar),
            "vulnerabilities_found": sum(1 for s in sonuclar if s.get("zafiyet_var")),
            "threshold": self.esik_degeri,
            "passed": False,
            "severity_breakdown": {"kritik": 0, "yuksek": 0, "orta": 0, "dusuk": 0}
        }
        for s in sonuclar:
            if s.get("zafiyet_var"):
                seviye = s.get("zafiyet_seviyesi", "dusuk")
                if seviye in ozet["severity_breakdown"]:
                    ozet["severity_breakdown"][seviye] += 1
        ozet["passed"] = ozet["score"] >= self.esik_degeri
        return ozet

    def exit_code_hesapla(self, skor):
        if skor < self.esik_degeri:
            return 1
        return 0

    def pipeline_durum_mesaji(self, skor):
        if skor >= self.esik_degeri:
            return f"PASSED: Guvenlik skoru {skor}/100 >= esik {self.esik_degeri}"
        else:
            return f"FAILED: Guvenlik skoru {skor}/100 < esik {self.esik_degeri}"

    def tum_ciktilar_uret(self, sonuclar, cikti_dizini, skor_ozeti=None, test_adi="Yargu LLM Security Test"):
        Path(cikti_dizini).mkdir(parents=True, exist_ok=True)
        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        ciktilar = {}
        junit_yolu = os.path.join(cikti_dizini, f"yargu-junit-{zaman}.xml")
        self.junit_xml_uret(sonuclar, junit_yolu, test_adi)
        ciktilar["junit"] = junit_yolu
        json_ozet = self.json_summary_uret(sonuclar, skor_ozeti)
        json_yolu = os.path.join(cikti_dizini, f"yargu-ci-summary-{zaman}.json")
        with open(json_yolu, "w", encoding="utf-8") as f:
            json.dump(json_ozet, f, ensure_ascii=False, indent=2)
        ciktilar["json_summary"] = json_yolu
        return ciktilar
