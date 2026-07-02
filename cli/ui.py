import os
import sys

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    YESIL = Fore.GREEN
    KIRMIZI = Fore.RED
    SARI = Fore.YELLOW
    MAVI = Fore.CYAN
    MOR = Fore.MAGENTA
    CYAN = Fore.LIGHTBLUE_EX
    SIFIRLA = Style.RESET_ALL
except ImportError:
    YESIL = KIRMIZI = SARI = MAVI = MOR = CYAN = SIFIRLA = ""

BANNER = f"""
{CYAN}+==========================================================+
|                                                          |
|   YARGU FRAMEWORK v2.9.0                                 |
|                                                          |
|   LLM Kirmizi Takim (Red Team) Test Araci                |
|                                                          |
|   AltaySec Bunyesinde Gelistirilmistir | Arda Mecik      |
|                                                          |
+==========================================================+{SIFIRLA}
"""

REKLAM = f"{SARI}[ Yargu Framework v2.9.0 - AltaySec Bünyesinde Geliştirilmiştir | Arda Meçik ]{SIFIRLA}"

UYARI_MESAJI = f"""
{KIRMIZI}[!] UYARI: Bu araç sadece yetkilendirilmiş güvenlik testleri için kullanılmalıdır.
[!] Test edilecek hedefin sahibinden yazılı izin alınması gerekmektedir.
[!] Yetkisiz kullanım yasa dışıdır ve hukuki sorumluluk doğurur.{SIFIRLA}
"""

def goster_banner():
    print(BANNER)
    print(REKLAM)
    print()

def goster_uyari():
    print(UYARI_MESAJI)
    print()

def ekran_temizle():
    os.system("cls" if os.name == "nt" else "clear")

def cikis_yap_animasyon():
    import time
    print(f"\n{KIRMIZI}[*] Yargu Framework kapatılıyor{SIFIRLA}", end="")
    for _ in range(3):
        time.sleep(0.3)
        print(KIRMIZI + "." + SIFIRLA, end="", flush=True)
    print(f"\n\n{REKLAM}\n")
    sys.exit(0)
