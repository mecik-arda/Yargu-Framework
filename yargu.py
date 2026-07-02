import sys
import io
import os

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.parser import arguman_parser_olustur
from cli.interactive import interaktif_menu_sor
from cli.ui import goster_banner, ekran_temizle, cikis_yap_animasyon, REKLAM, SARI, KIRMIZI, CYAN, SIFIRLA
from cli.commands import (
    api_testi_calistir,
    web_testi_calistir,
    proxy_modu_calistir,
    rapor_olustur_calistir,
    karsilastirma_calistir,
    payload_yonetimi_calistir,
    poison_calistir,
    tool_testi_calistir,
    mcp_testi_calistir,
    agent_testi_calistir,
    benchmark_calistir,
    otonom_calistir,
    marketplace_calistir,
    dashboard_calistir,
    stealth_calistir,
    cloud_calistir
)

def main():
    komut_haritasi = {
        "test-api": api_testi_calistir,
        "test-web": web_testi_calistir,
        "test-tool": tool_testi_calistir,
        "test-mcp": mcp_testi_calistir,
        "test-agent": agent_testi_calistir,
        "proxy": proxy_modu_calistir,
        "rapor": rapor_olustur_calistir,
        "karsilastir": karsilastirma_calistir,
        "payload": payload_yonetimi_calistir,
        "poison": poison_calistir,
        "benchmark": benchmark_calistir,
        "otonom": otonom_calistir,
        "marketplace": marketplace_calistir,
        "dashboard": dashboard_calistir,
        "stealth": stealth_calistir,
        "cloud": cloud_calistir
    }

    parser = arguman_parser_olustur()

    if len(sys.argv) == 1:
        import time
        print("\n" + CYAN + "[*] Yargu Framework başlatılıyor" + SIFIRLA, end="")
        for _ in range(3):
            time.sleep(0.4)
            print(CYAN + "." + SIFIRLA, end="", flush=True)
        print("\n")
        
        while True:
            try:
                ekran_temizle()
                goster_banner()
                parsed_args = interaktif_menu_sor(parser)
                if parsed_args is None:
                    continue
                    
                fonksiyon = komut_haritasi.get(parsed_args.komut)
                if fonksiyon:
                    try:
                        fonksiyon(parsed_args)
                    except SystemExit:
                        pass
                    except Exception as e:
                        print(f"{KIRMIZI}[-] Beklenmeyen hata: {e}{SIFIRLA}")
                print("\n" + SARI + "-"*60 + SIFIRLA + "\n")
                input(f"{CYAN}Ana menüye dönmek için Enter'a basın...{SIFIRLA}")
            except KeyboardInterrupt:
                cikis_yap_animasyon()
    else:
        args = parser.parse_args()
        if not args.komut:
            parser.print_help()
            print(f"\n{REKLAM}")
            return 0
            
        fonksiyon = komut_haritasi.get(args.komut)
        if fonksiyon:
            cikis_kodu = fonksiyon(args)
            if cikis_kodu is not None:
                sys.exit(cikis_kodu)
        else:
            parser.print_help()
            print(f"\n{REKLAM}")

if __name__ == "__main__":
    main()
