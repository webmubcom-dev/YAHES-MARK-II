# -*- coding: utf-8 -*-
"""
Y.A.H.E.S v6.3 - Gemini AI (Süper Debug Sürümü)
"""

import os
import sys
import json
import math
import random
import re
import socket
import urllib.request
import urllib.parse
import webbrowser
import threading
import time
import queue
import subprocess
import glob
import difflib
from datetime import datetime, timedelta

import numpy as np

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

import tkinter as tk
from tkinter import messagebox, scrolledtext

# ============================================================
# --- GEMINI AI ---
# ============================================================
GEMINI_AKTIF = False
_genai_client = None
_gemini_model_adi = "gemini-2.0-flash"
_gemini_son_hata = ""

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AKTIF = True
except Exception as e:
    print(f"[Gemini Uyarısı]: google-genai yüklenemedi: {e}")

# ============================================================
# --- DOSYA YOLLARI (ÇOKLU ARAMA) ---
# ============================================================
try:
    SCRIPT_DIZINI = os.path.dirname(os.path.abspath(__file__))
except Exception:
    SCRIPT_DIZINI = os.getcwd()

# API anahtarını aranacak klasörler
KEY_ARAMA_DIZINLERI = [
    SCRIPT_DIZINI,
    os.getcwd(),
    os.path.expanduser("~"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Masaüstü"),
    os.path.join(os.path.expanduser("~"), "Desktop", "YAHES-2"),
    os.path.join(os.path.expanduser("~"), "Masaüstü", "YAHES-2"),
    r"C:\Users\M\Desktop\YAHES-2",
]
# Aynı olanları temizle
_tmp = []
for _d in KEY_ARAMA_DIZINLERI:
    if _d and _d not in _tmp and os.path.isdir(_d):
        _tmp.append(_d)
KEY_ARAMA_DIZINLERI = _tmp

# Dosya yolları
GEMINI_KEY_DOSYASI = os.path.join(SCRIPT_DIZINI, "gemini_api_key.txt")
GEMINI_GECMIS_DOSYASI = os.path.join(SCRIPT_DIZINI, "gemini_sohbet_gecmisi.json")

RUTIN_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_rutinler.json")
ALARM_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_alarmlar.json")
HAFIZA_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_hafiza.json")
GECMIS_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_gecmis.txt")
OGRENME_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_ogrenme.json")
MOD_DOSYASI = os.path.join(SCRIPT_DIZINI, "mark_v_mod.json")

# --- SİSTEM MONİTÖRÜ ---
SISTEM_MONITOR_AKTIF = True
try:
    import psutil
except Exception:
    SISTEM_MONITOR_AKTIF = False

# --- KLAVYE ---
SES_KONTROL_AKTIF = True
try:
    import keyboard
except Exception:
    SES_KONTROL_AKTIF = False

# --- SES TANIMA ---
SES_TANIMA_AKTIF = True
try:
    import speech_recognition as sr
except Exception:
    SES_TANIMA_AKTIF = False

# --- SYSTEM TRAY ---
TRAY_AKTIF = True
try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    TRAY_AKTIF = False

ASISTAN_SES_DURUMU = True
UYANDIRMA_KELIMELERI = ["hey yahes", "yahes", "hey yaves"]
WAKE_WORD_AKTIF = True

RUTIN_PENCERE_TAM_EKRAN = True

VARSAYILAN_RUTINLER = {
    "sabah": {
        "aciklama": "Sabah rutini",
        "adimlar": ["hava_otomatik", "saat", "gunaydin"],
        "otomatik_saat": "07:00",
        "aktif": True
    }
}

MOTIVASYON_MESAJLARI = [
    "Bugün harika şeyler başaracaksınız efendim, kendinize güvenin!",
    "Her büyük yolculuk bir adımla başlar. Hadi başlayalım!",
    "Başarı, her gün tekrarlanan küçük çabaların toplamıdır.",
    "Hedefinize odaklanın, sınırları zorlayın!",
    "Bugün yapabileceğiniz en iyi şeyi yapın, gerisi gelecek."
]

# ============================================================
# --- GEMINI AI MOTORU ---
# ============================================================
_gemini_kilit = threading.Lock()
_gemini_sohbet_gecmisi = []
_GEMINI_SISTEM_PROMPT = (
    "Sen Y.A.H.E.S adında bir yapay zeka asistanısın. "
    "Türkçe konuşuyorsun. Kullanıcıya 'efendim' diye hitap ediyorsun. "
    "Kısa, net ve yardımcı cevaplar ver. "
    "Yanıtların en fazla 2-3 cümle olsun. "
    "Matematik, tarih, bilim, kod, çeviri gibi her konuda yardımcı ol."
)


def _temizle_anahtar(metin):
    """Anahtarı her türlü görünmez karakterden temizler."""
    if not metin:
        return ""
    # BOM ve görünmez karakterleri temizle
    metin = metin.replace("\ufeff", "")   # BOM
    metin = metin.replace("\x00", "")     # NULL
    metin = metin.replace("\r", "")       # CR
    metin = metin.replace("\n", "")       # LF
    metin = metin.replace("\t", "")       # TAB
    metin = metin.replace(" ", "")        # BOŞLUK
    metin = metin.replace('"', "")        # TIRNAK
    metin = metin.replace("'", "")        # TIRNAK
    metin = metin.strip()
    # Görünmez unicode karakterleri temizle
    temiz = ""
    for ch in metin:
        kod = ord(ch)
        # Sadece yazdırılabilir ASCII + AQ. formatı karakterleri
        if 33 <= kod <= 126:
            temiz += ch
    return temiz.strip()


def _dosya_debug(dosya_yolu):
    """Dosya hakkında detaylı bilgi yazdırır."""
    try:
        if not os.path.exists(dosya_yolu):
            print(f"[Debug]: Dosya YOK: {dosya_yolu}")
            return None

        boyut = os.path.getsize(dosya_yolu)
        print(f"[Debug]: Dosya VAR: {dosya_yolu}")
        print(f"[Debug]: Boyut: {boyut} byte")

        # Binary olarak ilk 200 byte'ı oku
        with open(dosya_yolu, "rb") as f:
            ham = f.read(200)
        print(f"[Debug]: Ham ilk 50 byte: {ham[:50]!r}")

        # Metin olarak oku
        with open(dosya_yolu, "r", encoding="utf-8-sig", errors="ignore") as f:
            icerik = f.read()
        print(f"[Debug]: Metin uzunluk: {len(icerik)} karakter")
        print(f"[Debug]: İlk 60 karakter: {icerik[:60]!r}")
        print(f"[Debug]: İlk 10 codepoint: {[ord(c) for c in icerik[:10]]}")

        return icerik
    except Exception as e:
        print(f"[Debug]: Okuma hatası: {e}")
        return None


def gemini_key_yukle():
    """API anahtarını tüm olası konumlardan okur."""
    print("\n" + "=" * 60)
    print("  API ANAHTARI ARANIYOR")
    print("=" * 60)

    # 1) Ortam değişkeni
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and len(key) > 20:
        print(f"[Gemini]: ✓ Ortam değişkeninden okundu (uzunluk: {len(key)})")
        return _temizle_anahtar(key)

    # 2) Tüm olası klasörlerde ara
    aday_dosyalar = []
    for d in KEY_ARAMA_DIZINLERI:
        aday_dosyalar.append(os.path.join(d, "gemini_api_key.txt"))
        aday_dosyalar.append(os.path.join(d, "Gemini_API_Key.txt"))
        aday_dosyalar.append(os.path.join(d, "gemini_api_key.TXT"))
        aday_dosyalar.append(os.path.join(d, "api_key.txt"))
        aday_dosyalar.append(os.path.join(d, "gemini_key.txt"))

    # Tekrarları kaldır
    gorulen = set()
    benzersiz = []
    for y in aday_dosyalar:
        norm = os.path.normcase(os.path.abspath(y))
        if norm not in gorulen:
            gorulen.add(norm)
            benzersiz.append(y)

    print(f"[Gemini]: {len(benzersiz)} olası konumda aranıyor...")
    for y in benzersiz:
        if os.path.exists(y):
            print(f"[Gemini]: ✓ BULUNDU: {y}")
            icerik = _dosya_debug(y)
            if icerik is None:
                continue
            temiz = _temizle_anahtar(icerik)
            if temiz and len(temiz) > 20 and "BURAYA" not in temiz.upper():
                print(f"[Gemini]: ✓ Anahtar temizlendi.")
                print(f"[Gemini]: Uzunluk: {len(temiz)}")
                print(f"[Gemini]: Başlangıç: {temiz[:10]}...")
                print(f"[Gemini]: Bitiş: ...{temiz[-6:]}")
                print("=" * 60 + "\n")
                return temiz
            else:
                print(f"[Gemini]: ⚠ Anahtar geçersiz: '{temiz[:30]}'")

    # 3) Hiçbir yerde bulunamadı → script yanına oluştur
    print(f"[Gemini]: ✗ Hiçbir konumda bulunamadı!")
    print(f"[Gemini]: Şu klasörlere bakıldı:")
    for d in KEY_ARAMA_DIZINLERI:
        print(f"           {d}")
    try:
        with open(GEMINI_KEY_DOSYASI, "w", encoding="utf-8") as f:
            f.write("BURAYA_GEMINI_API_KEY_YAZ")
        print(f"[Gemini]: ✓ Oluşturuldu: {GEMINI_KEY_DOSYASI}")
        print(f"[Gemini]: İçine AQ. ile başlayan anahtarı yazın.")
    except Exception as e:
        print(f"[Gemini]: Oluşturulamadı: {e}")
    print("=" * 60 + "\n")
    return ""


def gemini_baslat():
    """Gemini API'sini başlatır."""
    global _genai_client, _gemini_model_adi, _gemini_son_hata

    if not GEMINI_AKTIF:
        _gemini_son_hata = "google-genai modülü yok"
        print("[Gemini]: ✗ 'pip install google-genai' gerekli.")
        return False

    key = gemini_key_yukle()
    if not key:
        _gemini_son_hata = "API anahtarı bulunamadı"
        return False

    print(f"[Gemini]: Client oluşturuluyor... ({key[:8]}...)")
    try:
        _genai_client = genai.Client(api_key=key)
        print("[Gemini]: ✓ Client oluşturuldu.")
    except Exception as e:
        _gemini_son_hata = f"Client: {type(e).__name__}: {e}"
        print(f"[Gemini]: ✗ {_gemini_son_hata}")
        _genai_client = None
        return False

    # Model listesi
    modeller = []
    try:
        print("[Gemini]: Modeller listeleniyor...")
        for m in _genai_client.models.list():
            ad = getattr(m, "name", "")
            if ad.startswith("models/"):
                ad = ad[7:]
            if "gemini" in ad.lower():
                modeller.append(ad)
        print(f"[Gemini]: {len(modeller)} model bulundu: {modeller[:8]}")
    except Exception as e:
        print(f"[Gemini]: Model listesi alınamadı: {e}")

    # Öncelik sırası
    oncelik = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash",
               "gemini-2.0-flash-lite", "gemini-1.5-pro"]
    denenecekler = []
    for istenen in oncelik:
        if istenen in modeller:
            denenecekler.append(istenen)
    for m in modeller:
        if m not in denenecekler:
            denenecekler.append(m)

    print(f"[Gemini]: Denenecek modeller: {denenecekler[:5]}")

    # Test
    for model_adi in denenecekler[:6]:
        try:
            print(f"[Gemini]: Deneniyor: {model_adi}")
            response = _genai_client.models.generate_content(
                model=model_adi,
                contents="Merhaba, tek cümle cevap ver."
            )
            if response and hasattr(response, "text") and response.text:
                _gemini_model_adi = model_adi
                print(f"[Gemini]: ✓✓✓ BAŞARILI! Model: {model_adi}")
                print(f"[Gemini]: Yanıt: {response.text[:80]}")
                return True
            else:
                print(f"[Gemini]: ✗ Boş yanıt")
        except Exception as e:
            print(f"[Gemini]: ✗ {model_adi}: {type(e).__name__}: {str(e)[:150]}")

    _gemini_son_hata = "Hiçbir model çalışmadı"
    _genai_client = None
    print("[Gemini]: ✗✗✗ Tüm modeller başarısız.")
    return False


def gemini_sohbet_gecmisi_yukle():
    global _gemini_sohbet_gecmisi
    if os.path.exists(GEMINI_GECMIS_DOSYASI):
        try:
            with open(GEMINI_GECMIS_DOSYASI, "r", encoding="utf-8") as f:
                _gemini_sohbet_gecmisi = json.load(f)
        except Exception:
            _gemini_sohbet_gecmisi = []
    _gemini_sohbet_gecmisi = _gemini_sohbet_gecmisi[-20:]


def gemini_sohbet_gecmisi_kaydet():
    try:
        with open(GEMINI_GECMIS_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(_gemini_sohbet_gecmisi[-20:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def gemini_sor(soru, baglam=""):
    if _genai_client is None:
        return None

    with _gemini_kilit:
        try:
            tam_prompt = soru
            if baglam:
                tam_prompt = f"[Bağlam: {baglam}]\n\n{soru}"

            if _gemini_sohbet_gecmisi:
                gecmis_txt = "\n".join([
                    f"{m['rol']}: {m['metin']}" for m in _gemini_sohbet_gecmisi[-6:]
                ])
                tam_prompt = f"Önceki konuşma:\n{gecmis_txt}\n\nYeni soru: {soru}"

            tam_prompt = f"{_GEMINI_SISTEM_PROMPT}\n\n---\n\n{tam_prompt}"

            response = _genai_client.models.generate_content(
                model=_gemini_model_adi,
                contents=tam_prompt
            )

            if response and hasattr(response, "text") and response.text:
                metin = response.text.strip()
                _gemini_sohbet_gecmisi.append({"rol": "Kullanıcı", "metin": soru})
                _gemini_sohbet_gecmisi.append({"rol": "YAHES", "metin": metin})
                gemini_sohbet_gecmisi_kaydet()
                return metin
            return None
        except Exception as e:
            print(f"[Gemini Hatası]: {type(e).__name__}: {e}")
            return None


def gemini_sor_async(soru, baglam="", callback=None):
    def _iş():
        yanit = gemini_sor(soru, baglam)
        if yanit:
            konustur(yanit)
            if callback:
                try:
                    callback(yanit)
                except Exception:
                    pass
    threading.Thread(target=_iş, daemon=True).start()


def gemini_gecmisi_temizle():
    global _gemini_sohbet_gecmisi
    _gemini_sohbet_gecmisi = []
    try:
        if os.path.exists(GEMINI_GECMIS_DOSYASI):
            os.remove(GEMINI_GECMIS_DOSYASI)
    except Exception:
        pass


# ============================================================
# --- TEK ÖRNEK KİLİDİ ---
# ============================================================
_KILIT_SOCKET = None

def tek_ornek_kontrol():
    global _KILIT_SOCKET
    try:
        _KILIT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _KILIT_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _KILIT_SOCKET.bind(("127.0.0.1", 51999))
        _KILIT_SOCKET.listen(1)
        return True
    except socket.error:
        return False

# ============================================================
# --- OTTOMATİK BAŞLANGIÇ ---
# ============================================================
def otomatik_baslangic_kur():
    if not sys.platform.startswith("win"):
        return
    try:
        script_yolu = os.path.abspath(__file__)
    except Exception:
        return
    vbs_yolu = os.path.join(os.path.dirname(script_yolu), "yahes_baslat.vbs")
    gorev_adi = "YAHES_Otomatik_Baslat"
    vbs_icerik = f'''Set WshShell = CreateObject("WScript.Shell")
pythonw = "pythonw.exe"
On Error Resume Next
WshShell.Run pythonw & " ""{script_yolu}""", 0, False
If Err.Number <> 0 Then
    WshShell.Run "python.exe ""{script_yolu}""", 0, False
End If
'''
    try:
        with open(vbs_yolu, "w", encoding="utf-8") as f:
            f.write(vbs_icerik)
    except Exception:
        return
    try:
        kontrol = subprocess.run(["schtasks", "/Query", "/TN", gorev_adi],
                                 capture_output=True, timeout=10)
        if kontrol.returncode == 0:
            return
    except Exception:
        pass
    try:
        subprocess.run([
            "schtasks", "/Create", "/TN", gorev_adi,
            "/TR", f'wscript.exe "{vbs_yolu}"',
            "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"
        ], capture_output=True, timeout=15)
    except Exception:
        pass

# ============================================================
# --- UYKU ENGELLEME ---
# ============================================================
def uyku_engelle():
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    except Exception:
        pass

# ============================================================
# --- MOD SİSTEMİ ---
# ============================================================
AKTIF_MOD = "normal"
MOD_BILGILERI = {
    "normal":      {"renk": "#00ffff", "ikon": "◆",  "ad": "NORMAL MOD"},
    "beyaz_sayfa": {"renk": "#ffffff", "ikon": "📄", "ad": "BEYAZ SAYFA"},
    "rahatlik":    {"renk": "#ff88cc", "ikon": "🎵", "ad": "RAHATLIK MODU"},
    "odak":        {"renk": "#00ff88", "ikon": "🎯", "ad": "ODAK MODU"},
    "gece":        {"renk": "#8844ff", "ikon": "🌙", "ad": "GECE MODU"},
    "ai":          {"renk": "#ff8800", "ikon": "🧠", "ad": "AI MODU"},
}
RAHATLIK_LINKLERI = [
    "https://www.youtube.com/feed/subscriptions",
    "https://www.youtube.com/playlist?list=WL",
    "https://www.youtube.com/feed/history",
]

def mod_yukle():
    try:
        if os.path.exists(MOD_DOSYASI):
            with open(MOD_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f).get("mod", "normal")
    except Exception:
        pass
    return "normal"

def mod_kaydet(m):
    try:
        with open(MOD_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"mod": m}, f, ensure_ascii=False)
    except Exception:
        pass

def beyaz_sayfa_temizle():
    silinen = []
    for dosya, ad in [
        (OGRENME_DOSYASI, "Öğrenilenler"),
        (GECMIS_DOSYASI, "Geçmiş"),
        (HAFIZA_DOSYASI, "Hafıza (isim)"),
        (ALARM_DOSYASI, "Alarmlar"),
        (RUTIN_DOSYASI, "Rutinler"),
        (GEMINI_GECMIS_DOSYASI, "AI Sohbet Geçmişi"),
    ]:
        try:
            if os.path.exists(dosya):
                os.remove(dosya)
                silinen.append(ad)
        except Exception:
            pass
    return silinen

# ============================================================
# --- GUI LOG ---
# ============================================================
_gui_log_queue = queue.Queue()
_original_stdout = sys.stdout
_GUI_REF = None

class GuiLogger:
    def write(self, msg):
        if msg:
            try:
                _original_stdout.write(msg)
            except Exception:
                pass
            _gui_log_queue.put(msg)
    def flush(self):
        try:
            _original_stdout.flush()
        except Exception:
            pass

sys.stdout = GuiLogger()

# ============================================================
# --- SES MOTORU ---
# ============================================================
SES_AKTIF = True
EDGE_TTS_AKTIF = False
_pygame_hazir = False

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AKTIF = True
except Exception:
    pass

try:
    import pygame
    pygame.mixer.pre_init(frequency=24000, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    _pygame_hazir = True
except Exception:
    pass

JARVIS_SES = "tr-TR-EmelNeural"
JARVIS_RATE = "-5%"
JARVIS_PITCH = "-2Hz"
JARVIS_VOLUME = "+0%"

PYTTSX3_AKTIF = True
try:
    import pyttsx3
except Exception:
    PYTTSX3_AKTIF = False

_ses_kilidi = threading.Lock()

def _jarvis_bip():
    if not _pygame_hazir:
        return
    try:
        sure = 0.08
        frekans = 880
        ornekleme = 22050
        t = np.linspace(0, sure, int(ornekleme * sure), False)
        dalga = np.sin(frekans * t * 2 * np.pi) * 0.25
        fade_len = int(len(dalga) * 0.4)
        dalga[-fade_len:] *= np.linspace(1, 0, fade_len)
        ses = (dalga * 32767).astype(np.int16)
        ses = np.column_stack((ses, ses))
        pygame.sndarray.make_sound(ses).play()
        time.sleep(0.1)
    except Exception:
        pass

def _edge_tts_konus(metin):
    if not _pygame_hazir:
        return False
    try:
        gecici = os.path.join(SCRIPT_DIZINI, f"yashes_ses_{int(time.time()*1000)}_{random.randint(0,9999)}.mp3")
        async def _u():
            c = edge_tts.Communicate(metin, JARVIS_SES,
                                     rate=JARVIS_RATE, pitch=JARVIS_PITCH, volume=JARVIS_VOLUME)
            await c.save(gecici)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_u())
        finally:
            try: loop.close()
            except: pass
        if not os.path.exists(gecici):
            return False
        pygame.mixer.music.load(gecici)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        try: os.remove(gecici)
        except: pass
        return True
    except Exception:
        return False

def _pyttsx3_konus(metin):
    if not PYTTSX3_AKTIF:
        return False
    try:
        e = pyttsx3.init()
        e.setProperty('rate', 165)
        e.setProperty('volume', 1.0)
        for v in e.getProperty('voices'):
            vi = (v.name + v.id).lower()
            if "turkish" in vi or "tolga" in vi or "tr" in vi:
                e.setProperty('voice', v.id)
                break
        e.say(metin)
        e.runAndWait()
        return True
    except Exception:
        return False

def _konustur_ic(metin):
    global _GUI_REF
    if _GUI_REF is not None:
        try: _GUI_REF.konusuyor = True
        except Exception: pass
    try:
        if not ASISTAN_SES_DURUMU:
            print(f"> [Ses Kapalı]: {metin}"); return
        temiz = (str(metin)
                 .replace("http://","").replace("https://","")
                 .replace("www.","").replace("|",",")
                 .replace("->","sonuç").replace("<b>","").replace("</b>","")
                 .replace("<br>"," ")
                 .replace("⚠️","").replace("✓","").replace("⏰","")
                 .replace("🔊","").replace("🔇","").replace("📌","")
                 .replace("🟢","").replace("⚪","").replace("🌤","")
                 .replace("💰","").replace("🕐","").replace("🔍","")
                 .replace("📺","").replace("📚","").replace("💡","")
                 .replace("💻","").replace("❓","").replace("🌡","")
                 .replace("📄","").replace("🎵","").replace("🎯","")
                 .replace("🌙","").replace("◆","").replace("🧠",""))
        print(f"> {temiz}")
        if not SES_AKTIF: return
        with _ses_kilidi:
            if EDGE_TTS_AKTIF and _pygame_hazir:
                try: _jarvis_bip()
                except: pass
                if _edge_tts_konus(temiz): return
            _pyttsx3_konus(temiz)
    finally:
        if _GUI_REF is not None:
            try: _GUI_REF.konusuyor = False
            except Exception: pass

def konustur(metin):
    _konustur_ic(metin)

def konustur_async(metin):
    threading.Thread(target=_konustur_ic, args=(metin,), daemon=True).start()

def bildirim_goster(baslik, mesaj):
    def a():
        p = tk.Tk()
        p.overrideredirect(True)
        p.configure(bg="#0b0f19")
        p.attributes("-topmost", True)
        sw, sh = p.winfo_screenwidth(), p.winfo_screenheight()
        p.geometry(f"340x100+{sw-360}+{sh-150}")
        tk.Label(p, text=baslik, font=("Helvetica", 11, "bold"),
                 fg="#00ffff", bg="#0b0f19").pack(anchor="w", padx=10, pady=(10, 2))
        tk.Label(p, text=mesaj, font=("Helvetica", 9), fg="#ffffff",
                 bg="#0b0f19", wraplength=320).pack(anchor="w", padx=10)
        p.after(2500, p.destroy)
        p.mainloop()
    threading.Thread(target=a, daemon=True).start()

def tab_ses_kontrol_dinleyicisi():
    global ASISTAN_SES_DURUMU
    if not SES_KONTROL_AKTIF: return
    def tb(e):
        global ASISTAN_SES_DURUMU
        ASISTAN_SES_DURUMU = not ASISTAN_SES_DURUMU
        if ASISTAN_SES_DURUMU:
            bildirim_goster("🔊 Ses Açıldı", "Sesli yanıtlar aktif.")
        else:
            bildirim_goster("🔇 Ses Kapandı", "Sesli yanıtlar gizli.")
    try:
        keyboard.on_press_key("tab", tb)
    except Exception:
        pass

if SES_KONTROL_AKTIF:
    threading.Thread(target=tab_ses_kontrol_dinleyicisi, daemon=True).start()

# ============================================================
# --- 3D SPLASH ---
# ============================================================
class Yahes3DAnimasyon:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#010205")
        self.g = self.root.winfo_screenwidth()
        self.y = self.root.winfo_screenheight()
        self.root.geometry(f"{self.g}x{self.y}+0+0")
        self.c = tk.Canvas(self.root, width=self.g, height=self.y,
                           bg="#010205", highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.aci = 0.0
        self.z = 350.0
        self.s = 0
        self.dongu()
        self.root.mainloop()

    def proj(self, x, y, z):
        fl = 500.0
        f = fl / (max(1.0, z + self.z))
        return self.g/2 + x*f, self.y/2 + y*f, f

    def dongu(self):
        self.c.delete("all")
        self.s += 1
        self.aci += 0.03
        sx = math.sin(self.aci) * 20
        sy = math.cos(self.aci * 0.7) * 10
        for dz in range(50, 0, -4):
            r = int(40 + (50-dz)*3.5)
            renk = f"#00{hex(min(255,max(50,r)))[2:].zfill(2)}ff"
            x2, y2, f = self.proj(sx, sy, dz)
            fb = int(85*f)
            if fb > 5:
                self.c.create_text(x2, y2, text="Y.A.H.E.S",
                                   font=("Helvetica", fb, "bold"), fill=renk)
        x2, y2, f = self.proj(sx, sy, 0)
        self.c.create_text(x2, y2, text="Y.A.H.E.S",
                           font=("Helvetica", int(85*f), "bold"), fill="#00ffff")
        if self.s > 95:
            self.root.quit(); self.root.destroy(); return
        self.root.after(25, self.dongu)

# ============================================================
# --- MİKROFON ---
# ============================================================
def sesli_komut_al(sessiz=False):
    if not SES_TANIMA_AKTIF: return ""
    r = sr.Recognizer()
    try:
        with sr.Microphone() as src:
            if not sessiz: print("[Dinleniyor...]")
            r.adjust_for_ambient_noise(src, duration=0.4)
            try:
                a = r.listen(src, timeout=5, phrase_time_limit=7)
                k = r.recognize_google(a, language="tr-TR")
                if not sessiz: print(f"Algılanan: {k}")
                return k.lower().strip()
            except Exception:
                return ""
    except Exception:
        return ""

# ============================================================
# --- ALKIŞ ALGILAMA ---
# ============================================================
ALKIŞ_AKTIF = True
_alkis_callback = None
_alkis_3_callback = None

def alkis_dinleyici(callback, callback_3=None):
    global _alkis_callback, _alkis_3_callback
    _alkis_callback = callback
    _alkis_3_callback = callback_3
    if not SES_TANIMA_AKTIF:
        return
    try:
        import pyaudio
    except Exception:
        return

    def dinle():
        CHUNK = 1024
        RATE = 44100
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
        except Exception:
            return
        esik = 3500
        bekleme = 0.7
        min_aralik = 0.12
        seri_sifirla = 1.5
        alkis_zamanlari = []
        son_uyari = 0
        try:
            while True:
                try:
                    veri = stream.read(CHUNK, exception_on_overflow=False)
                    ses = np.frombuffer(veri, dtype=np.int16)
                    peak = int(np.max(np.abs(ses)))
                    rms = int(np.sqrt(np.mean(ses.astype(np.float32) ** 2)))
                    simdi = time.time()
                    if alkis_zamanlari and (simdi - alkis_zamanlari[-1]) > seri_sifirla:
                        alkis_zamanlari = []
                    if peak > esik and rms > esik * 0.4:
                        if alkis_zamanlari and (simdi - alkis_zamanlari[-1]) < min_aralik:
                            continue
                        alkis_zamanlari.append(simdi)
                        alkis_zamanlari = [t for t in alkis_zamanlari if simdi - t <= 2.0]
                        if len(alkis_zamanlari) >= 3:
                            if simdi - son_uyari > 2.0:
                                if _alkis_3_callback:
                                    try: _alkis_3_callback()
                                    except Exception: pass
                                son_uyari = simdi
                                alkis_zamanlari = []
                                continue
                        elif len(alkis_zamanlari) == 2:
                            if (alkis_zamanlari[-1] - alkis_zamanlari[0]) < bekleme:
                                def _kontrol(zamanlar=alkis_zamanlari):
                                    time.sleep(0.45)
                                    if len(zamanlar) == 2:
                                        simdi2 = time.time()
                                        if simdi2 - son_uyari > 2.0:
                                            if _alkis_callback:
                                                try: _alkis_callback()
                                                except Exception: pass
                                        zamanlar.clear()
                                threading.Thread(target=_kontrol, daemon=True).start()
                            else:
                                alkis_zamanlari = [alkis_zamanlari[-1]]
                except Exception:
                    time.sleep(0.01)
        except Exception:
            pass
        finally:
            try:
                stream.stop_stream(); stream.close(); p.terminate()
            except Exception:
                pass

    threading.Thread(target=dinle, daemon=True).start()

# ============================================================
# --- WAKE WORD ---
# ============================================================
wake_word_event = threading.Event()
wake_word_durdur = threading.Event()

def wake_word_dinleyici():
    if not SES_TANIMA_AKTIF or not WAKE_WORD_AKTIF: return
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    while not wake_word_durdur.is_set():
        if _GUI_REF is not None and getattr(_GUI_REF, "surekli_dinleme", False):
            time.sleep(0.5)
            continue
        try:
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.3)
                try:
                    a = r.listen(src, timeout=3, phrase_time_limit=4)
                    m = r.recognize_google(a, language="tr-TR").lower().strip()
                    for kw in UYANDIRMA_KELIMELERI:
                        if kw in m or "yahes" in m:
                            konustur_async("Buyurun efendim.")
                            wake_word_event.set()
                            break
                except Exception:
                    continue
        except Exception:
            time.sleep(1)

def wake_word_baslat():
    threading.Thread(target=wake_word_dinleyici, daemon=True).start()

# ============================================================
# --- DOSYA ---
# ============================================================
def hafiza_yukle():
    if os.path.exists(HAFIZA_DOSYASI):
        try:
            with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def hafiza_kaydet(d):
    with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

def gecmise_yaz(m):
    try:
        with open(GECMIS_DOSYASI, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {m}\n")
    except: pass

def _normalize(s):
    if not s: return ""
    s = str(s).lower().strip()
    tr = {"ı":"i","İ":"i","ş":"s","Ş":"s","ğ":"g","Ğ":"g",
          "ü":"u","Ü":"u","ö":"o","Ö":"o","ç":"c","Ç":"c"}
    for a, b in tr.items():
        s = s.replace(a, b)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def ogrenme_yukle():
    if os.path.exists(OGRENME_DOSYASI):
        try:
            with open(OGRENME_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def ogrenme_kaydet(d):
    with open(OGRENME_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

def ogrenme_ara(s):
    d = ogrenme_yukle()
    if not d: return None
    st = _normalize(s)
    if not st or len(st) < 2: return None
    for k, v in d.items():
        if _normalize(k) == st:
            return v
    st_kelimeler = set(st.split())
    en_iyi = None
    en_uzun = 0
    for k, v in d.items():
        nk = _normalize(k)
        if not nk or len(nk) < 2: continue
        nk_kelimeler = set(nk.split())
        if len(nk) >= 3 and nk_kelimeler.issubset(st_kelimeler):
            if len(nk) > en_uzun:
                en_uzun = len(nk); en_iyi = v
        elif len(st) >= 3 and nk in st:
            if len(nk) > en_uzun:
                en_uzun = len(nk); en_iyi = v
    return en_iyi

def ogrenme_ekle(s, c):
    d = ogrenme_yukle()
    anahtar = _normalize(s)
    if not anahtar:
        return False
    d[anahtar] = c.strip()
    ogrenme_kaydet(d)
    print(f"✓ Öğrendim: '{anahtar}' -> '{c.strip()}'")
    return True

def ogrenme_sil(s):
    d = ogrenme_yukle()
    anahtar = _normalize(s)
    if not anahtar: return False
    if anahtar in d:
        del d[anahtar]; ogrenme_kaydet(d)
        print(f"✓ Silindi: '{anahtar}'"); return True
    for k in list(d.keys()):
        if anahtar in k or k in anahtar:
            del d[k]; ogrenme_kaydet(d)
            print(f"✓ Silindi: '{k}'"); return True
    return False

def ogrenme_listele():
    d = ogrenme_yukle()
    if not d:
        print("Öğrenilmiş bir şey yok."); return
    print("═"*60); print(f"ÖĞRENİLMİŞ CEVAPLAR ({len(d)})"); print("═"*60)
    for i, (s, c) in enumerate(d.items(), 1):
        print(f"{i:3d}. ❓ {s}")
        print(f"     💬 {c}")
    print("═"*60)

UNVANLAR = ["efendim", "değerli dostum", "üstadım", "kıymetli kullanıcım"]
def unvan_getir(k): return f"{k} {random.choice(UNVANLAR)}"

RASTGELE_BILGILER = [
    "İnsan beyninin depolama kapasitesi yaklaşık 2.5 petabayt.",
    "Dünyadaki toplam karınca ağırlığı, tüm insanların toplam ağırlığına yakındır.",
    "Işık hızı saniyede yaklaşık 300.000 kilometredir.",
    "Python dili adını Monty Python'dan almıştır."
]

# ============================================================
# --- SICAKLIK ---
# ============================================================
def cpu_sicakligi_getir():
    if SISTEM_MONITOR_AKTIF:
        try:
            if hasattr(psutil, "sensors_temperatures"):
                t = psutil.sensors_temperatures()
                if t:
                    for k in ["coretemp","cpu_thermal","k10temp","acpitz","cpu-thermal","zenpower","it87"]:
                        if k in t and t[k]: return t[k][0].current
                    for k, e in t.items():
                        if e: return e[0].current
        except: pass
    if sys.platform.startswith("win"):
        try:
            import wmi
            w = wmi.WMI(namespace="root\\wmi")
            s = w.MSAcpi_ThermalZoneTemperature()
            if s: return s[0].CurrentTemperature/10.0 - 273.15
        except: pass
        try:
            out = subprocess.check_output(
                ['powershell','-NoProfile','-Command',
                 "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | "
                 "Select-Object -First 1 -ExpandProperty CurrentTemperature)"],
                timeout=4, stderr=subprocess.DEVNULL).decode(errors="ignore").strip()
            if out and out.isdigit(): return int(out)/10.0 - 273.15
        except: pass
    return None

def cpu_fan_hizi_getir():
    if SISTEM_MONITOR_AKTIF:
        try:
            if hasattr(psutil, "sensors_fans"):
                f = psutil.sensors_fans()
                if f:
                    for k, v in f.items():
                        if v: return v[0].current
        except: pass
    return None

def sistem_durumu_getir():
    if not SISTEM_MONITOR_AKTIF: return "psutil yok."
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        r = f"İşlemci yüzde {cpu:.1f}. Bellek yüzde {ram.percent:.1f}. Disk yüzde {disk.percent:.1f}."
        s = cpu_sicakligi_getir()
        if s is not None: r += f" İşlemci sıcaklığı {s:.0f} derece."
        f = cpu_fan_hizi_getir()
        if f is not None: r += f" Fan {f} RPM."
        try:
            b = psutil.sensors_battery()
            if b: r += f" Batarya yüzde {b.percent:.0f}."
        except: pass
        return r
    except Exception as e: return f"Hata: {e}"

def sistem_durumu_detayli():
    if not SISTEM_MONITOR_AKTIF: print("psutil yok."); return
    try:
        print("━"*50); print("      DETAYLI SİSTEM RAPORU"); print("━"*50)
        print(f"  CPU Çekirdek : {psutil.cpu_count(logical=True)} (fiziksel: {psutil.cpu_count(logical=False)})")
        print(f"  CPU Kullanım : %{psutil.cpu_percent(interval=0.5)}")
        try:
            fr = psutil.cpu_freq()
            if fr: print(f"  CPU Frekans  : {fr.current:.0f} MHz (max: {fr.max:.0f} MHz)")
        except: pass
        s = cpu_sicakligi_getir()
        if s is not None:
            d = "Normal"
            if s > 80: d = "⚠ YÜKSEK"
            elif s > 65: d = "Ilık"
            print(f"  CPU Sıcaklık : {s:.1f}°C  [{d}]")
        else: print("  CPU Sıcaklık : Okunamadı")
        f = cpu_fan_hizi_getir()
        if f is not None: print(f"  Fan Hızı     : {f} RPM")
        ram = psutil.virtual_memory()
        print(f"  RAM Toplam   : {ram.total/(1024**3):.2f} GB")
        print(f"  RAM Kullanım : {ram.used/(1024**3):.2f} GB (%{ram.percent})")
        print(f"  RAM Boş      : {ram.available/(1024**3):.2f} GB")
        for d in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(d.mountpoint)
                print(f"  Disk {d.mountpoint:8s}: %{u.percent} ({u.free/(1024**3):.1f} GB boş)")
            except: pass
        try:
            b = psutil.sensors_battery()
            if b: print(f"  Batarya      : %{b.percent:.0f} ({'Şarj oluyor' if b.power_plugged else 'Prizde değil'})")
        except: pass
        print("━"*50)
    except Exception as e: print(f"[Sistem Hatası]: {e}")

def alarm_penceresi_goster(m, t):
    def a():
        p = tk.Tk()
        p.title(f"Y.A.H.E.S - {t.upper()}")
        p.geometry("460x290")
        p.configure(bg="#0b0f19")
        p.attributes("-topmost", True)
        tk.Label(p, text=f"⚠ {t.upper()}", font=("Helvetica", 15, "bold"),
                 fg="#00ffff", bg="#0b0f19").pack(pady=20)
        tk.Label(p, text=m, font=("Helvetica", 12), fg="#ffffff",
                 bg="#0b0f19", wraplength=420, justify="center").pack(pady=10)
        tk.Button(p, text="KAPAT", font=("Helvetica", 11, "bold"),
                  bg="#ff4444", fg="#ffffff", command=p.destroy,
                  width=20, height=2).pack(pady=20)
        p.mainloop()
    threading.Thread(target=a, daemon=True).start()

def rutin_penceresi_goster(ra, ac, ad, isim):
    def a():
        p = tk.Tk()
        p.title(f"⏰ Y.A.H.E.S - {ra.upper()}")
        p.configure(bg="#01050f")
        if RUTIN_PENCERE_TAM_EKRAN: p.attributes("-fullscreen", True)
        else:
            sw, sh = p.winfo_screenwidth(), p.winfo_screenheight()
            w, h = 900, 700; x, y = (sw-w)//2, (sh-h)//2
            p.geometry(f"{w}x{h}+{x}+{y}")
        p.attributes("-topmost", True); p.lift(); p.focus_force()
        c = tk.Canvas(p, bg="#01050f", highlightthickness=0)
        c.pack(fill="both", expand=True)
        W = p.winfo_screenwidth() if RUTIN_PENCERE_TAM_EKRAN else 900
        H = p.winfo_screenheight() if RUTIN_PENCERE_TAM_EKRAN else 700
        s = [0]; kb = [None]
        def bg():
            c.delete("bg_anim")
            t = s[0]*0.05
            for i in range(0, H, 6):
                g = 80 + math.sin(t + i*0.02)*60
                rt = int(30 + math.sin(t + i*0.01)*20)
                r = f"#00{max(10, min(255, rt)):02x}ff"
                c.create_line(0, i, g, i, fill=r, width=1, tags="bg_anim")
                c.create_line(W, i, W-g, i, fill=r, width=1, tags="bg_anim")
        def ic():
            c.delete("icerik")
            c.create_text(W//2, H*0.13, text=f"⏰ {ra.upper()} RUTİNİ",
                          font=("Helvetica", int(H*0.06), "bold"),
                          fill="#00ffff", tags="icerik")
            if ac: c.create_text(W//2, H*0.23, text=ac,
                                 font=("Helvetica", int(H*0.025)),
                                 fill="#aaddff", tags="icerik")
            sl = f"Günaydın {isim}!" if "sabah" in ra else f"Merhaba {isim}!"
            c.create_text(W//2, H*0.31, text=sl,
                          font=("Helvetica", int(H*0.03), "italic"),
                          fill="#ffffff", tags="icerik")
            c.create_text(W//2, H*0.38,
                          text=datetime.now().strftime("%d.%m.%Y  %H:%M"),
                          font=("Helvetica", int(H*0.022)),
                          fill="#88bbdd", tags="icerik")
            c.create_text(W//2, H*0.45, text="— YAPILACAKLAR —",
                          font=("Helvetica", int(H*0.022), "bold"),
                          fill="#00ffff", tags="icerik")
            es = {"hava_otomatik":"🌤 Hava", "saat":"🕐 Saat",
                  "gunaydin":"☀️ Günaydın", "iyigeceler":"🌙 İyi geceler",
                  "motivasyon":"💪 Motivasyon", "doviz":"💱 Döviz",
                  "bilgi":"💡 Bilgi", "sistem":"💻 Sistem"}
            for i, a_ in enumerate(ad):
                c.create_text(W//2, H*0.51 + i*(H*0.055),
                              text=es.get(a_, f"• {a_}"),
                              font=("Helvetica", int(H*0.028)),
                              fill="#ffffff", tags="icerik")
            c.create_text(W//2, H*0.85, text="Kapatana kadar açık",
                          font=("Helvetica", int(H*0.018), "italic"),
                          fill="#6688aa", tags="icerik")
            if kb[0]: kb[0].destroy()
            kb[0] = tk.Button(p, text="✓ RUTİNİ KAPAT",
                font=("Helvetica", int(H*0.022), "bold"),
                bg="#00aaff", fg="#ffffff", relief="flat", bd=0,
                command=p.destroy)
            kb[0].place(relx=0.5, rely=0.91, anchor="center",
                        width=int(W*0.3), height=int(H*0.06))
        def d():
            s[0] += 1; bg()
            if s[0] == 1: ic()
            p.bind("<Escape>", lambda e: p.destroy())
            p.after(50, d)
        d(); p.mainloop()
    threading.Thread(target=a, daemon=True).start()

def alarmlari_yukle():
    if os.path.exists(ALARM_DOSYASI):
        try:
            with open(ALARM_DOSYASI, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def alarmlari_kaydet(a):
    with open(ALARM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(a, f, ensure_ascii=False, indent=4)

def rutinleri_yukle():
    if os.path.exists(RUTIN_DOSYASI):
        try:
            with open(RUTIN_DOSYASI, "r", encoding="utf-8") as f: return json.load(f)
        except: return VARSAYILAN_RUTINLER
    with open(RUTIN_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(VARSAYILAN_RUTINLER, f, ensure_ascii=False, indent=4)
    return VARSAYILAN_RUTINLER

def rutinleri_kaydet(r):
    with open(RUTIN_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=4)

def rutin_calistir(ra, isim, otomatik=False):
    rl = rutinleri_yukle()
    ra = ra.lower().strip()
    if ra not in rl:
        if not otomatik: konustur_async(f"'{ra}' bulunamadı.")
        return
    r = rl[ra]
    if otomatik and not r.get("aktif", False): return
    print(f"===== {ra.upper()} =====")
    rutin_penceresi_goster(ra, r.get("aciklama",""), r.get("adimlar",[]), isim)
    def anlat():
        konustur(f"{ra} başlıyor.")
        for a in r.get("adimlar", []):
            try:
                if a == "hava_otomatik": konustur(hava_durumu_getir("Istanbul"))
                elif a == "saat": konustur(f"Saat {datetime.now().strftime('%H:%M')}")
                elif a == "gunaydin": konustur(f"Günaydın {unvan_getir(isim)}!")
                elif a == "iyigeceler": konustur(f"İyi geceler {unvan_getir(isim)}!")
                elif a == "motivasyon": konustur(random.choice(MOTIVASYON_MESAJLARI))
                elif a == "doviz": konustur(doviz_kuru_getir())
                elif a == "bilgi": konustur(random.choice(RASTGELE_BILGILER))
                elif a == "sistem": konustur(sistem_durumu_getir())
                else: konustur(a)
                time.sleep(0.3)
            except Exception as e: print(f"[Rutin Hata]: {a} -> {e}")
        konustur(f"{ra} bitti.")
    threading.Thread(target=anlat, daemon=True).start()

def rutin_ekle_gui(ra, ac, ads, os_=""):
    ra = ra.strip().lower()
    if not ra: return False
    ad = [a.strip().strip("'\"") for a in ads.split(",") if a.strip()]
    if not ad: return False
    ak = False
    if os_:
        if re.match(r'^\d{1,2}[:\.]\d{2}$', os_):
            p = os_.replace(".", ":").split(":")
            os_ = f"{int(p[0]):02d}:{int(p[1]):02d}"; ak = True
        else: os_ = ""
    rl = rutinleri_yukle()
    rl[ra] = {"aciklama": ac or "Kullanıcı rutini", "adimlar": ad,
              "otomatik_saat": os_, "aktif": ak}
    rutinleri_kaydet(rl)
    print(f"✓ '{ra}' kaydedildi!"); return True

def rutin_duzenle_gui(ra, ya="", yad="", ys=""):
    rl = rutinleri_yukle()
    ra = ra.lower().strip()
    if ra not in rl: return False
    r = rl[ra]
    if ya: r["aciklama"] = ya
    if yad: r["adimlar"] = [a.strip().strip("'\"") for a in yad.split(",") if a.strip()]
    if ys:
        if ys.lower() in ["yok","hayir","hayır"]:
            r["otomatik_saat"] = ""; r["aktif"] = False
        elif re.match(r'^\d{1,2}[:\.]\d{2}$', ys):
            p = ys.replace(".", ":").split(":")
            r["otomatik_saat"] = f"{int(p[0]):02d}:{int(p[1]):02d}"; r["aktif"] = True
    rl[ra] = r; rutinleri_kaydet(rl)
    print(f"✓ '{ra}' güncellendi!"); return True

def rutin_sil(ra):
    rl = rutinleri_yukle()
    a = ra.lower().strip()
    if a in rl:
        del rl[a]; rutinleri_kaydet(rl); print(f"✓ '{a}' silindi.")
    else: print(f"'{a}' bulunamadı.")

def rutin_listele():
    rl = rutinleri_yukle()
    if not rl: print("Rutin yok."); return
    print("═"*60); print("KAYITLI RUTİNLER"); print("═"*60)
    for ad, r in rl.items():
        d = f"🟢 AKTİF {r.get('otomatik_saat')}" if r.get("aktif") else "⚪ ELLE"
        print(f"📌 {ad.upper()} [{d}]")
        print(f"   {r.get('aciklama','')}")
        print(f"   {', '.join(r.get('adimlar',[]))}")
    print("═"*60)

def arka_plan_rutin_kontrol():
    son = {}
    while True:
        try:
            s = datetime.now()
            ss = s.strftime("%H:%M"); sg = s.strftime("%Y-%m-%d")
            rl = rutinleri_yukle()
            isim = hafiza_yukle().get("isim", "Kullanıcı")
            for ad, r in rl.items():
                if not r.get("aktif", False): continue
                os_ = r.get("otomatik_saat","")
                if not os_: continue
                if os_ == ss:
                    k = f"{sg} {ss}"
                    if son.get(ad) == k: continue
                    bildirim_goster(f"⏰ {ad}", f"Saat {os_}")
                    son[ad] = k
                    threading.Thread(target=rutin_calistir, args=(ad, isim, True), daemon=True).start()
        except Exception:
            pass
        time.sleep(20)

def arka_plan_alarm_kontrol():
    while True:
        try:
            al = alarmlari_yukle()
            sz = datetime.now().strftime("%Y-%m-%d %H:%M")
            gn = []; deg = False
            for a in al:
                if a["zaman"] <= sz and not a.get("caldi", False):
                    t = a.get("tur","Hatırlatma"); m = a.get("mesaj","Vakit geldi!")
                    konustur_async(f"Dikkat! {m}")
                    alarm_penceresi_goster(m, t)
                    a["caldi"] = True; deg = True
                if not a.get("caldi", False): gn.append(a)
            if deg: alarmlari_kaydet(gn)
        except Exception:
            pass
        time.sleep(10)

threading.Thread(target=arka_plan_alarm_kontrol, daemon=True).start()
threading.Thread(target=arka_plan_rutin_kontrol, daemon=True).start()

def akilli_zaman_cozumle(m):
    s = datetime.now()
    hz = s + timedelta(hours=1)
    m = m.lower()
    mm = re.search(r'(\d{1,2})[:\.](\d{2})', m)
    if mm:
        sa, dk = int(mm.group(1)), int(mm.group(2))
        if "yarın" in m or "yarin" in m:
            hg = s + timedelta(days=1)
            hz = hg.replace(hour=sa, minute=dk, second=0, microsecond=0)
        else:
            hz = s.replace(hour=sa, minute=dk, second=0, microsecond=0)
            if hz < s: hz += timedelta(days=1)
    return hz.strftime("%Y-%m-%d %H:%M")

def menuyu_goster():
    print("""
╔══════════════════════════════════════════════════╗
║   Y.A.H.E.S v6.3 - KOMUTLAR + GEMINI AI          ║
╠══════════════════════════════════════════════════╣
║  🧠 GEMINI AI                                    ║
║   • Herhangi bir soru sorun → AI yanıtlar       ║
║   • "ai modu", "ai durum", "ai geçmişi temizle" ║
╠══════════════════════════════════════════════════╣
║  👏 ALKIŞ                                        ║
║   • 👏👏 2 alkış  : Tam ekran / pencere          ║
║   • 👏👏👏 3 alkış : Sürekli dinleme AÇ/KAPA     ║
╠══════════════════════════════════════════════════╣
║  🚀 UYGULAMA AÇMA (AKILLI)                       ║
║   • chrome, not, hesap, spotify, vscode...      ║
╠══════════════════════════════════════════════════╣
║  🎭 MODLAR                                       ║
║   • normal, rahatlık, odak, gece, ai            ║
╠══════════════════════════════════════════════════╣
║  📋 DİĞER                                        ║
║   • google, youtube, wiki, hava, doviz, saat    ║
║   • sistem, alarm, rutin, öğren                 ║
╚══════════════════════════════════════════════════╝
""")

# --- WEB ---
def google_ara(s):
    if BeautifulSoup is None: return "BS4 yok."
    try:
        u = f"https://www.google.com/search?q={urllib.parse.quote(s)}&hl=tr"
        rq = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            sp = BeautifulSoup(r.read().decode('utf-8', errors='ignore'), 'html.parser')
            res = []
            for g in sp.find_all('div', class_='g'):
                t = g.find('h3')
                sn = g.find('div', class_='VwiC3b') or g.find('div', class_='IsZA1e')
                if t and sn: res.append(f"{t.get_text().strip()}: {sn.get_text().strip()}")
                if len(res) >= 2: break
            return "Sonuçlar: " + " | ".join(res) if res else "Bulunamadı."
    except: return "Google hatası."

def hava_durumu_getir(s="Istanbul"):
    try:
        gu = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(s)}&count=1&language=tr&format=json"
        rq = urllib.request.Request(gu, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            gd = json.loads(r.read().decode('utf-8'))
            if "results" not in gd or not gd["results"]: return f"{s} bulunamadı."
            la, lo = gd["results"][0]["latitude"], gd["results"][0]["longitude"]
            ad = gd["results"][0]["name"]
        wu = f"https://api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        rq = urllib.request.Request(wu, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            w = json.loads(r.read().decode('utf-8')).get("current", {})
            hd = {0:"Açık",1:"Genellikle açık",2:"Parçalı bulutlu",3:"Çok bulutlu",
                  45:"Sisli",51:"Çisenti",61:"Hafif yağmur",63:"Yağmurlu",
                  71:"Hafif kar",95:"Fırtınalı"}
            return f"{ad}: {hd.get(w.get('weather_code',0),'Bulutlu')}. Sıcaklık {w.get('temperature_2m')}, nem %{w.get('relative_humidity_2m')}, rüzgar {w.get('wind_speed_10m')} km/s."
    except: return "Hava alınamadı."

def vikipedi_ara(s):
    try:
        su = f"https://tr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(s)}&format=json"
        rq = urllib.request.Request(su, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            res = json.loads(r.read().decode('utf-8')).get("query",{}).get("search",[])
            if not res: return "Bulunamadı."
            b = res[0]["title"]
        su2 = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(b)}"
        rq = urllib.request.Request(su2, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            return f"{b}: {json.loads(r.read().decode('utf-8')).get('extract')}"
    except: return "Wiki hatası."

def doviz_kuru_getir():
    try:
        u = "https://api.exchangerate-api.com/v4/latest/USD"
        rq = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=5) as r:
            d = json.loads(r.read().decode('utf-8'))['rates']
            t, e = d.get('TRY',0), d.get('EUR',1)
            return f"1 Dolar: {t:.2f} TL, 1 Euro: {t/e:.2f} TL."
    except: return "Döviz alınamadı."

def youtube_ara_ve_ac(s):
    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(s)}")
    return f"{s} YouTube'da açıldı."

# ============================================================
# --- AKILLI UYGULAMA BAŞLATICI ---
# ============================================================
UYGULAMA_ALIASLARI = {
    "chrome": ["chrome", "google", "google chrome", "tarayici", "tarayıcı", "internet", "web", "krom"],
    "msedge": ["edge", "microsoft edge", "ms edge"],
    "firefox": ["firefox", "mozila", "mozilla"],
    "opera": ["opera", "opera gx"],
    "brave": ["brave", "brave browser"],
    "notepad": ["not", "notepad", "not defteri", "notdefteri", "metin", "notepad++"],
    "winword": ["word", "microsoft word", "ms word"],
    "excel": ["excel", "microsoft excel", "ms excel", "tablo"],
    "powerpnt": ["powerpoint", "microsoft powerpoint", "sunum"],
    "outlook": ["outlook", "microsoft outlook", "mail", "e posta"],
    "Spotify": ["spotify", "spoti", "muzik", "müzik"],
    "vlc": ["vlc", "vlc player"],
    "wmplayer": ["windows media player", "media player", "wmplayer"],
    "calc": ["hesap", "hesap makinesi", "hesapmakinesi", "calc", "calculator", "matematik"],
    "explorer": ["dosya", "dosya gezgini", "explorer", "gezgin", "klasor", "klasör", "bilgisayarim"],
    "cmd": ["cmd", "komut", "komut istemi", "terminal", "command"],
    "powershell": ["powershell", "power shell", "ps"],
    "Taskmgr": ["gorev", "görev yöneticisi", "task manager", "taskmgr"],
    "control": ["kontrol", "denetim masasi", "denetim masası", "control panel"],
    "mspaint": ["paint", "boyama", "resim", "mspaint"],
    "snippingtool": ["ekran goruntusu", "ekran görüntüsü", "snipping", "kesme"],
    "magnify": ["buyutec", "büyüteç", "magnifier"],
    "osk": ["ekran klavyesi", "klavye", "osk"],
    "charmap": ["karakter", "karakter haritasi", "charmap"],
    "Code": ["vscode", "visual studio code", "vs code", "code"],
    "Discord": ["discord"],
    "Telegram": ["telegram"],
    "WhatsApp": ["whatsapp", "whatsapp desktop"],
    "Zoom": ["zoom"],
    "Teams": ["teams", "microsoft teams"],
    "steam": ["steam", "oyun"],
    "obs64": ["obs", "obs studio", "kayit", "kayıt"],
    "Git Bash": ["git", "git bash"],
    "Photoshop": ["photoshop", "ps"],
    "Illustrator": ["illustrator", "ai"],
    "Premiere": ["premiere", "premiere pro"],
    "AfterFX": ["after effects", "ae"],
}

_SISTEM_UYGULAMA_CACHE = None
_CACHE_KILIT = threading.Lock()


def _baslat_menu_uygulamalarini_tara():
    uygulamalar = {}
    start_menu_yollari = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    for sm in start_menu_yollari:
        if not os.path.isdir(sm):
            continue
        try:
            for lnk in glob.glob(os.path.join(sm, "**", "*.lnk"), recursive=True):
                ad = os.path.splitext(os.path.basename(lnk))[0].lower().strip()
                if ad and ad not in uygulamalar:
                    uygulamalar[ad] = lnk
        except Exception:
            pass
    try:
        import winreg
        anahtarlar = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for hive, yol in anahtarlar:
            try:
                with winreg.OpenKey(hive, yol) as k:
                    i = 0
                    while True:
                        try:
                            alt = winreg.EnumKey(k, i); i += 1
                            with winreg.OpenKey(k, alt) as ak:
                                try:
                                    p, _ = winreg.QueryValueEx(ak, "")
                                    ad = alt.lower().replace(".exe", "").strip()
                                    if ad and p and os.path.exists(p):
                                        uygulamalar.setdefault(ad, p)
                                except Exception:
                                    pass
                        except OSError:
                            break
            except Exception:
                pass
    except Exception:
        pass
    try:
        for yol in os.environ.get("PATH", "").split(os.pathsep):
            if not yol or not os.path.isdir(yol):
                continue
            try:
                for exe in os.listdir(yol):
                    if exe.lower().endswith(".exe"):
                        ad = exe[:-4].lower()
                        uygulamalar.setdefault(ad, os.path.join(yol, exe))
            except Exception:
                pass
    except Exception:
        pass
    return uygulamalar


def _sistem_uygulamalarini_getir():
    global _SISTEM_UYGULAMA_CACHE
    with _CACHE_KILIT:
        if _SISTEM_UYGULAMA_CACHE is None:
            print("[Uygulama Tarayıcı]: Sistem taranıyor...")
            _SISTEM_UYGULAMA_CACHE = _baslat_menu_uygulamalarini_tara()
            print(f"[Uygulama Tarayıcı]: {len(_SISTEM_UYGULAMA_CACHE)} uygulama bulundu.")
        return _SISTEM_UYGULAMA_CACHE


def _benzerlik(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def akilli_uygulama_bul(kullanici_girdisi):
    if not kullanici_girdisi:
        return None, None
    g = kullanici_girdisi.lower().strip()
    g_norm = _normalize(g)
    if not g_norm:
        return None, None
    en_iyi_alias = None
    en_iyi_skor = 0.0
    for exe, aliaslar in UYGULAMA_ALIASLARI.items():
        for al in aliaslar:
            al_n = _normalize(al)
            if al_n == g_norm:
                skor = 1.0
            elif al_n in g_norm.split() or g_norm in al_n.split():
                skor = 0.95
            elif al_n in g_norm or g_norm in al_n:
                skor = 0.8
            else:
                skor = _benzerlik(al_n, g_norm) * 0.7
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi_alias = exe
    if en_iyi_alias and en_iyi_skor >= 0.65:
        uygulamalar = _sistem_uygulamalarini_getir()
        for isim, yol in uygulamalar.items():
            if en_iyi_alias.lower() in isim.lower() or isim.lower() in en_iyi_alias.lower():
                return yol, isim
        return en_iyi_alias, en_iyi_alias
    uygulamalar = _sistem_uygulamalarini_getir()
    en_iyi = None
    en_iyi_skor2 = 0.0
    for ad, yol in uygulamalar.items():
        ad_n = _normalize(ad)
        if not ad_n:
            continue
        if ad_n == g_norm:
            return yol, ad
        if ad_n in g_norm or g_norm in ad_n:
            skor = 0.9
        else:
            skor = _benzerlik(ad_n, g_norm)
        if skor > en_iyi_skor2:
            en_iyi_skor2 = skor
            en_iyi = (yol, ad)
    if en_iyi and en_iyi_skor2 >= 0.75:
        return en_iyi
    return None, None


def uygulama_baslat(arama):
    if not arama:
        return False, "Uygulama adı belirtilmedi.", None
    bilinen_exeler = {
        "calc": "calc", "notepad": "notepad", "mspaint": "mspaint",
        "explorer": "explorer", "cmd": "cmd", "powershell": "powershell",
        "taskmgr": "taskmgr", "control": "control", "charmap": "charmap",
        "magnify": "magnify", "osk": "osk", "snippingtool": "snippingtool",
        "wmplayer": "wmplayer"
    }
    g = _normalize(arama)
    for exe, cmd in bilinen_exeler.items():
        if g == exe or g == _normalize(cmd):
            try:
                subprocess.Popen(cmd, shell=True)
                return True, f"{exe} başlatıldı efendim.", exe
            except Exception:
                pass
    yol, ad = akilli_uygulama_bul(arama)
    if yol:
        try:
            if yol.lower().endswith(".lnk"):
                os.startfile(yol)
            else:
                if os.path.exists(yol):
                    subprocess.Popen([yol], shell=False)
                else:
                    subprocess.Popen(yol, shell=True)
            return True, f"{ad} başlatıldı efendim.", ad
        except Exception as e:
            try:
                os.system(f'start "" "{yol}"')
                return True, f"{ad} başlatıldı efendim.", ad
            except Exception:
                pass
            return False, f"{ad} başlatılamadı: {e}", ad
    try:
        subprocess.Popen(arama, shell=True)
        return True, f"{arama} başlatılıyor.", arama
    except Exception:
        pass
    return False, f"'{arama}' adında bir uygulama bulamadım efendim.", None


def uygulama_listesi_yazdir():
    uygulamalar = _sistem_uygulamalarini_getir()
    print("═" * 60)
    print(f"KURULU UYGULAMALAR ({len(uygulamalar)})")
    print("═" * 60)
    sirali = sorted(uygulamalar.items())
    for i, (ad, yol) in enumerate(sirali, 1):
        print(f"{i:4d}. {ad:40s}")
        if i % 50 == 0:
            print("─" * 60)
    print("═" * 60)


# ============================================================
# --- TRAY İKON ---
# ============================================================
def tray_ikon_olustur():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(0, 20, 40), outline=(0, 255, 255), width=3)
    d.ellipse((14, 14, 50, 50), outline=(0, 200, 255), width=2)
    d.ellipse((24, 24, 40, 40), fill=(0, 255, 255))
    return img

# ============================================================
# --- GUI ---
# ============================================================
class YahesGUI:
    def __init__(self):
        global _GUI_REF
        _GUI_REF = self

        self.root = tk.Tk()
        self.root.title("Y.A.H.E.S v6.3")
        self.root.configure(bg="#000205")
        self.root.geometry("1300x840")
        self.root.minsize(1000, 680)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = (sw-1300)//2, (sh-840)//2
        self.root.geometry(f"1300x840+{x}+{y}")

        self.tam_ekran = False
        self.root.bind("<F11>", self._tam_ekran_toggle)
        self.root.protocol("WM_DELETE_WINDOW", self._cikis_dogru)

        self.isim = "Kullanıcı"
        self.islem_kuyrugu = queue.Queue()
        self.dinleme_aktif = False
        self.anim_aci = 0.0
        self.anim_sayac = 0
        self.durum_metni = "SİSTEM ÇEVRİMİÇİ"
        self._isim_bekle = False
        self._beklenen_mod = None
        self._alarm_mesaj_bekle = None
        self._ogrenme_soru = None

        self.aktif_mod = mod_yukle()
        self.mod_renk = MOD_BILGILERI.get(self.aktif_mod, MOD_BILGILERI["normal"])["renk"]

        self.surekli_dinleme = False
        self.surekli_dinleme_thread = None
        self.surekli_dinleme_durdur = threading.Event()
        self.tray = None

        self.parcaciklar = []
        for _ in range(60):
            self.parcaciklar.append({
                "x": random.uniform(0, 1300), "y": random.uniform(0, 840),
                "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(-0.3, 0.3),
                "r": random.uniform(0.5, 2.2), "a": random.uniform(0.2, 0.9)
            })
        self.matrix_kolonlar = []
        for _ in range(40):
            self.matrix_kolonlar.append({
                "x": random.randint(0, 1300), "y": random.randint(-800, 0),
                "hiz": random.uniform(2, 7), "uzunluk": random.randint(5, 18)
            })

        self.konusuyor = False
        self.metrik_cpu = 0.0
        self.metrik_ram = 0.0
        self.metrik_disk = 0.0
        self.metrik_sicaklik = None
        self.metrik_gecmis_cpu = [0]*80
        self.metrik_gecmis_ram = [0]*80
        self.metrik_guncelleme_aktif = True
        self.alkis_goster = None

        self._arayuz_kur()
        self._animasyon_baslat()
        self._log_takip_baslat()
        self._baslangic_selamla()
        self._metrik_dongusu_baslat()
        threading.Thread(target=self._islem_kuyruk_tuketici, daemon=True).start()

        if ALKIŞ_AKTIF:
            alkis_dinleyici(self._alkis_algilandi, self._alkis_3_algilandi)

        self.root.after(500, self._mod_gosterge_guncelle)
        if TRAY_AKTIF:
            self.root.after(800, self._tray_baslat)

    def _tray_baslat(self):
        try:
            menu = pystray.Menu(
                pystray.MenuItem("🖥  Göster / Gizle", self._tray_goster_gizle, default=True),
                pystray.MenuItem("🎤  Sesli Komut", lambda i, it: self.root.after(0, self._sesli_komut_tetikle)),
                pystray.MenuItem("👏  Sürekli Dinleme", lambda i, it: self.root.after(0, self._alkis_3_algilandi)),
                pystray.MenuItem("🧠  AI Geçmişi Temizle", lambda i, it: self.root.after(0, gemini_gecmisi_temizle)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("✕  Çıkış", self._tray_cikis),
            )
            self.tray = pystray.Icon("YAHES", tray_ikon_olustur(),
                                     "Y.A.H.E.S v6.3 — AI Aktif" if _genai_client else "Y.A.H.E.S v6.3",
                                     menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            print(f"[Tray Hatası]: {e}")

    def _tray_goster_gizle(self, icon=None, item=None):
        def g():
            try:
                if self.root.state() == "iconic" or not self.root.winfo_viewable():
                    self.root.deiconify(); self.root.lift(); self.root.focus_force()
                else:
                    self.root.iconify()
            except Exception:
                pass
        self.root.after(0, g)

    def _tray_cikis(self, icon=None, item=None):
        try:
            if self.tray: self.tray.stop()
        except Exception:
            pass
        self.root.after(0, self._cikis)

    def _arayuz_kur(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.arka_canvas = tk.Canvas(self.root, bg="#000205", highlightthickness=0)
        self.arka_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._ust_bar()
        orta = tk.Frame(self.root, bg="#000205")
        orta.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        orta.grid_rowconfigure(0, weight=1)
        orta.grid_columnconfigure(0, weight=0)
        orta.grid_columnconfigure(1, weight=1)
        self._sol_panel(orta)
        self._sag_panel(orta)
        self.giris_entry.focus_set()

    def _ust_bar(self):
        u = tk.Frame(self.root, bg="#01040a", height=62)
        u.grid(row=0, column=0, sticky="ew")
        u.grid_propagate(False)
        u.grid_columnconfigure(2, weight=1)
        lg = tk.Frame(u, bg="#01040a")
        lg.grid(row=0, column=0, padx=18, pady=10)
        self.logo_canvas = tk.Canvas(lg, width=38, height=38, bg="#01040a", highlightthickness=0)
        self.logo_canvas.pack(side="left")
        pts = []
        for i in range(6):
            a = math.pi/3 * i + math.pi/6
            pts.extend([19 + 16*math.cos(a), 19 + 16*math.sin(a)])
        self.logo_canvas.create_polygon(pts, outline="#00ffff", fill="#001a2a", width=2)
        self.logo_canvas.create_text(19, 19, text="Y", font=("Helvetica", 13, "bold"), fill="#00ffff")
        tk.Label(lg, text=" Y.A.H.E.S", font=("Helvetica", 17, "bold"),
                 fg="#00ffff", bg="#01040a").pack(side="left")
        ai_renk = "#ff8800" if _genai_client else "#444"
        ai_text = " v6.3 🧠AI" if _genai_client else " v6.3"
        tk.Label(lg, text=ai_text, font=("Helvetica", 9, "italic"),
                 fg=ai_renk, bg="#01040a").pack(side="left", pady=(9, 0))
        self.mod_lbl = tk.Label(u, text="  ◆ NORMAL MOD  ",
                                font=("Consolas", 10, "bold"),
                                fg="#00ffff", bg="#01040a")
        self.mod_lbl.grid(row=0, column=1, padx=(0, 15))
        self.durum_canvas = tk.Canvas(u, width=260, height=26, bg="#01040a", highlightthickness=0)
        self.durum_canvas.grid(row=0, column=2, padx=(0, 10), sticky="w")
        r = tk.Frame(u, bg="#01040a")
        r.grid(row=0, column=3, padx=15)
        self.alkis_lbl = tk.Label(r, text="👏👏👏", font=("Helvetica", 11),
                                  fg="#333", bg="#01040a")
        self.alkis_lbl.pack(side="left", padx=(0, 12))
        self.saat_ust = tk.Label(r, text="", font=("Consolas", 14, "bold"),
                                 fg="#00ffff", bg="#01040a")
        self.saat_ust.pack(side="left")
        self._saat_guncelle()
        self._ust_durum_ciz()

    def _ust_durum_ciz(self):
        try:
            c = self.durum_canvas
            c.delete("all")
            t = self.anim_sayac * 0.1
            renk = self.mod_renk
            c.create_rectangle(0, 0, 260, 26, fill="#01040a", outline="#003355")
            for i in range(30):
                x = (i * 9 + int(t * 30)) % 260
                h = 3 + abs(math.sin(t + i * 0.5)) * 12
                c.create_line(x, 13 - h, x, 13 + h, fill=renk, width=1)
            bilgi = MOD_BILGILERI.get(self.aktif_mod, MOD_BILGILERI["normal"])
            c.create_text(130, 13, text=f"{bilgi['ikon']} {bilgi['ad']} {bilgi['ikon']}",
                          font=("Consolas", 9, "bold"), fill="#ffffff")
            self.root.after(50, self._ust_durum_ciz)
        except Exception:
            pass

    def _saat_guncelle(self):
        try:
            self.saat_ust.configure(text=datetime.now().strftime("%H:%M:%S  ▸  %d.%m.%Y"))
        except Exception: pass
        self.root.after(1000, self._saat_guncelle)

    def _sol_panel(self, parent):
        sol = tk.Frame(parent, bg="#000205", width=440)
        sol.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sol.grid_propagate(False)
        self.halka_canvas = tk.Canvas(sol, width=420, height=420, bg="#000205", highlightthickness=0)
        self.halka_canvas.pack(pady=(5, 5))
        mf = tk.Frame(sol, bg="#020810", highlightthickness=1, highlightbackground="#003355")
        mf.pack(fill="x", padx=15, pady=(0, 8))
        tk.Label(mf, text="◤ SİSTEM METRİKLERİ", font=("Consolas", 10, "bold"),
                 fg="#00ffff", bg="#020810").pack(fill="x", pady=(6, 4), padx=10, anchor="w")
        self.cpu_lbl, self.cpu_canvas = self._metrik_satir(mf, "CPU", "#00ffff")
        self.ram_lbl, self.ram_canvas = self._metrik_satir(mf, "RAM", "#00aaff")
        self.disk_lbl, self.disk_canvas = self._metrik_satir(mf, "DISK", "#00ff88")
        self.sic_lbl, self.sic_canvas = self._metrik_satir(mf, "SICAKLIK", "#ff8844")
        bf = tk.Frame(sol, bg="#000205")
        bf.pack(fill="x", padx=15, pady=(0, 8))
        self.mic_btn = self._grad_btn(bf, "🎤  SESLİ KOMUT",
                                      self._mic_btn_tikla, 12,
                                      ("#001a33", "#003355"))
        self.mic_btn.pack(fill="x", pady=(0, 6), ipady=12)
        self.mic_btn.bind("<Button-3>", lambda e: self._alkis_3_algilandi())
        alt = tk.Frame(bf, bg="#000205")
        alt.pack(fill="x")
        for i in range(4):
            alt.grid_columnconfigure(i, weight=1)
        self._grad_btn(alt, "💻 SİSTEM", lambda: self._buton_komut("sistem detay"), 8,
                       ("#001522", "#002a3a")).grid(row=0, column=0, sticky="ew", padx=(0, 2), ipady=8)
        self._grad_btn(alt, "🚀 UYG", lambda: self._buton_komut("uygulama"), 8,
                       ("#001522", "#002a3a")).grid(row=0, column=1, sticky="ew", padx=2, ipady=8)
        self._grad_btn(alt, "🎭 MOD", lambda: self._buton_komut("mod"), 8,
                       ("#1a0030", "#330055")).grid(row=0, column=2, sticky="ew", padx=2, ipady=8)
        self._grad_btn(alt, "🧠 AI", lambda: self._buton_komut("ai modu"), 8,
                       ("#331100", "#552200")).grid(row=0, column=3, sticky="ew", padx=(2, 0), ipady=8)
        self._grad_btn(bf, "✕  ÇIKIŞ", self._cikis, 11,
                       ("#330000", "#660000")).pack(fill="x", pady=(6, 0), ipady=8)

    def _metrik_satir(self, parent, etiket, renk):
        f = tk.Frame(parent, bg="#020810")
        f.pack(fill="x", padx=10, pady=3)
        lbl = tk.Label(f, text=f"{etiket:9s}  0%", font=("Consolas", 9, "bold"),
                       fg=renk, bg="#020810", anchor="w", width=15)
        lbl.pack(side="left")
        c = tk.Canvas(f, height=11, bg="#00101a", highlightthickness=0, bd=0)
        c.pack(side="left", fill="x", expand=True, padx=(5, 5))
        return lbl, c

    def _metrik_ciz(self, lbl, canvas, yuzde, renk, ek):
        try:
            lbl.configure(text=f"{ek:9s}  {yuzde:.0f}%")
            canvas.delete("all")
            w = canvas.winfo_width() or 200
            h = 11
            canvas.create_rectangle(0, 0, w, h, fill="#00101a", outline="#002a3a")
            dolu = max(0, min(1, yuzde/100.0)) * w
            r = renk
            if yuzde > 85: r = "#ff2222"
            elif yuzde > 65: r = "#ffaa22"
            canvas.create_rectangle(0, 0, dolu, h, fill=r, outline="")
            canvas.create_line(0, 1, dolu, 1, fill="#ffffff", width=1)
            for i in range(1, 20):
                x = w * i / 20
                canvas.create_line(x, 0, x, h, fill="#000610", width=1)
        except Exception: pass

    def _grad_btn(self, parent, metin, komut, fs, renkler):
        bg1, bg2 = renkler
        b = tk.Button(parent, text=metin, font=("Helvetica", fs, "bold"),
                      bg=bg1, fg="#00ffff", activebackground=bg2, activeforeground="#ffffff",
                      relief="flat", bd=0, cursor="hand2", highlightthickness=0, command=komut)
        def oe(e):
            try: b.configure(bg=bg2, fg="#ffffff")
            except: pass
        def ol(e):
            try: b.configure(bg=bg1, fg="#00ffff")
            except: pass
        b.bind("<Enter>", oe); b.bind("<Leave>", ol)
        return b

    def _sag_panel(self, parent):
        sag = tk.Frame(parent, bg="#000205")
        sag.grid(row=0, column=1, sticky="nsew")
        sag.grid_rowconfigure(0, weight=1)
        sag.grid_rowconfigure(1, weight=0)
        sag.grid_rowconfigure(2, weight=0)
        sag.grid_columnconfigure(0, weight=1)
        lf = tk.Frame(sag, bg="#020810", highlightthickness=1, highlightbackground="#003355")
        lf.grid(row=0, column=0, sticky="nsew")
        lf.grid_rowconfigure(1, weight=1)
        lf.grid_columnconfigure(0, weight=1)
        bf = tk.Frame(lf, bg="#020810")
        bf.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        tk.Label(bf, text="◤ SİSTEM KONSOLU", font=("Consolas", 11, "bold"),
                 fg="#00ffff", bg="#020810").pack(side="left")
        ai_durum = "🧠 AI AKTİF" if _genai_client else "🧠 AI KAPALI"
        ai_renk = "#ff8800" if _genai_client else "#666"
        tk.Label(bf, text=ai_durum, font=("Consolas", 9, "bold"),
                 fg=ai_renk, bg="#020810").pack(side="right", padx=(0, 10))
        self.log_durum = tk.Label(bf, text="● CANLI", font=("Consolas", 9, "bold"),
                                  fg="#00ff88", bg="#020810")
        self.log_durum.pack(side="right")
        self.log_text = scrolledtext.ScrolledText(
            lf, wrap="word", font=("Consolas", 10),
            bg="#000408", fg="#88ddff", insertbackground="#00ffff",
            relief="flat", bd=0, state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.log_text.tag_config("cyan", foreground="#00ffff")
        self.log_text.tag_config("green", foreground="#00ff88")
        self.log_text.tag_config("yellow", foreground="#ffcc44")
        self.log_text.tag_config("red", foreground="#ff6666")
        self.log_text.tag_config("white", foreground="#ffffff")
        self.log_text.tag_config("magenta", foreground="#cc88ff")
        self.log_text.tag_config("orange", foreground="#ff8800")
        gf = tk.Frame(sag, bg="#000205")
        gf.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        gf.grid_columnconfigure(0, weight=1)
        self.entry_glow = tk.Frame(gf, bg="#00ffff", bd=0)
        self.entry_glow.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.giris_entry = tk.Entry(self.entry_glow, font=("Consolas", 12),
                                    bg="#020810", fg="#ffffff",
                                    insertbackground="#00ffff", relief="flat", bd=0)
        self.giris_entry.pack(fill="x", padx=2, pady=2, ipady=10)
        self.giris_entry.bind("<Return>", lambda e: self._giris_gonder())
        self._grad_btn(gf, "GÖNDER  ▶", self._giris_gonder, 11,
                       ("#001522", "#003355")).grid(row=0, column=1, ipady=8, ipadx=14)
        ks = tk.Frame(sag, bg="#000205")
        ks.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        b1 = [("🧠 AI SOR","ai"),("🌤 HAVA","hava"),
              ("💰 DÖVİZ","doviz"),("🕐 SAAT","saat")]
        b2 = [("🚀 UYGULAMA","uygulama"),("📺 YOUTUBE","youtube"),
              ("🎵 RAHATLIK","rahatlık modu"),("🎯 ODAK","odak modu")]
        for i, (e, k) in enumerate(b1):
            self._grad_btn(ks, e, lambda kk=k: self._buton_komut(kk), 9,
                           ("#001522", "#002a3a")).grid(row=0, column=i, padx=2, pady=2, ipady=6, sticky="ew")
            ks.grid_columnconfigure(i, weight=1)
        for i, (e, k) in enumerate(b2):
            self._grad_btn(ks, e, lambda kk=k: self._buton_komut(kk), 9,
                           ("#001522", "#002a3a")).grid(row=1, column=i, padx=2, pady=2, ipady=6, sticky="ew")

    def _buton_komut(self, komut):
        self._log_yaz(f"\n[Buton] >> {komut}\n")
        self.islem_kuyrugu.put(komut)

    def _alkis_algilandi(self):
        def git():
            try:
                if self.alkis_goster:
                    self.root.after_cancel(self.alkis_goster)
                self.alkis_lbl.configure(fg="#00ffff")
                self.alkis_goster = self.root.after(1500, lambda: self.alkis_lbl.configure(fg="#333"))
                self.tam_ekran = not self.tam_ekran
                if self.tam_ekran:
                    self.root.deiconify()
                    self.root.attributes("-fullscreen", True)
                    self.root.lift()
                    self.root.attributes("-topmost", True)
                    self.root.after(800, lambda: self.root.attributes("-topmost", False))
                    self.root.focus_force()
                    self.giris_entry.focus_set()
                    self._log_yaz("\n" + "═"*58 + "\n")
                    self._log_yaz("   👏👏 ALKIŞ - TAM EKRAN MODU\n")
                    self._log_yaz("═"*58 + "\n")
                    konustur_async("Tam ekran modu açıldı efendim.")
                else:
                    self.root.attributes("-fullscreen", False)
                    self.root.geometry("1300x840")
                    self.root.iconify()
                    self._log_yaz("\n" + "═"*58 + "\n")
                    self._log_yaz("   👏👏 ALKIŞ - ARKA PLANA ATILDI\n")
                    self._log_yaz("═"*58 + "\n")
                    konustur_async("Arka plana alındı efendim.")
            except Exception as e:
                print(f"[Alkış GUI Hatası]: {e}")
        self.root.after(0, git)

    def _alkis_3_algilandi(self):
        def git():
            if self.surekli_dinleme:
                self._surekli_dinlemeyi_durdur()
            else:
                self._surekli_dinlemeyi_baslat()
        self.root.after(0, git)

    def _surekli_dinlemeyi_baslat(self):
        if self.surekli_dinleme:
            return
        if not SES_TANIMA_AKTIF:
            self._log_yaz("[Sürekli Dinleme]: Ses tanıma yok.\n")
            return
        self.surekli_dinleme = True
        self.surekli_dinleme_durdur.clear()
        try:
            self.mic_btn.configure(text="🟢  SÜREKLİ DİNLEME AÇIK  (kapatmak için tıkla)",
                                   bg="#003300", fg="#00ff88")
        except Exception:
            pass
        self._log_yaz("\n" + "═"*58 + "\n")
        self._log_yaz("   👏👏👏 SÜREKLİ DİNLEME MODU AÇILDI\n")
        self._log_yaz("═"*58 + "\n")
        konustur_async("Sürekli dinleme modu açıldı efendim. Sizi dinliyorum.")
        self.surekli_dinleme_thread = threading.Thread(
            target=self._surekli_dinleme_dongusu, daemon=True)
        self.surekli_dinleme_thread.start()

    def _surekli_dinlemeyi_durdur(self):
        if not self.surekli_dinleme:
            return
        self.surekli_dinleme = False
        self.surekli_dinleme_durdur.set()
        try:
            self.mic_btn.configure(text="🎤  SESLİ KOMUT", bg="#001a33", fg="#00ffff")
        except Exception:
            pass
        self._log_yaz("\n>> Sürekli dinleme modu KAPATILDI.\n")
        konustur_async("Sürekli dinleme modu kapatıldı efendim.")

    def _surekli_dinleme_dongusu(self):
        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.7
        while not self.surekli_dinleme_durdur.is_set():
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.2)
                    try:
                        audio = r.listen(src, timeout=2, phrase_time_limit=6)
                    except Exception:
                        continue
                if not self.surekli_dinleme:
                    break
                try:
                    metin = r.recognize_google(audio, language="tr-TR").lower().strip()
                except Exception:
                    continue
                if not metin:
                    continue
                for kw in UYANDIRMA_KELIMELERI:
                    if kw in metin:
                        metin = metin.replace(kw, "").strip()
                if not metin or len(metin) < 2:
                    continue
                if self.konusuyor:
                    continue
                self._log_gui(f"\n[🎤 Sürekli] {metin}\n")
                self.root.after(0, lambda m=metin: self._sesli_gonder(m))
            except Exception as e:
                self._log_gui(f"[Sürekli Dinleme Hata]: {e}\n")
                time.sleep(1)

    def _mic_btn_tikla(self):
        if self.surekli_dinleme:
            self._surekli_dinlemeyi_durdur()
        else:
            self._sesli_komut_tetikle()

    def _tam_ekran_toggle(self, event=None):
        self.tam_ekran = not self.tam_ekran
        self.root.attributes("-fullscreen", self.tam_ekran)
        if self.tam_ekran:
            self._log_yaz("[F11] Tam ekran modu aktif.\n")
        else:
            self._log_yaz("[F11] Pencere modu.\n")

    def _animasyon_baslat(self):
        self._parcacik_dongusu()
        self._animasyon_dongusu()

    def _parcacik_dongusu(self):
        try:
            c = self.arka_canvas
            c.delete("all")
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w <= 1: w = 1300
            if h <= 1: h = 840
            for kat in range(3):
                pts = []
                for x in range(0, w + 20, 20):
                    y = h * 0.15 + kat * 15 + math.sin(x * 0.008 + self.anim_sayac * 0.03 + kat) * 25
                    pts.extend([x, y])
                if len(pts) >= 4:
                    renk = ["#001a2a", "#002a3a", "#003a4a"][kat]
                    c.create_line(*pts, fill=renk, width=2, smooth=True)
            for kat in range(2):
                pts = []
                for x in range(0, w + 20, 20):
                    y = h * 0.9 + kat * 15 + math.sin(x * 0.006 - self.anim_sayac * 0.02 + kat) * 30
                    pts.extend([x, y])
                if len(pts) >= 4:
                    renk = ["#001a2a", "#002a3a"][kat]
                    c.create_line(*pts, fill=renk, width=2, smooth=True)
            for mk in self.matrix_kolonlar:
                mk["y"] += mk["hiz"]
                if mk["y"] > h + mk["uzunluk"] * 20:
                    mk["y"] = random.randint(-300, -20)
                    mk["x"] = random.randint(0, w)
                for i in range(mk["uzunluk"]):
                    yy = mk["y"] - i * 16
                    if -20 < yy < h + 20:
                        parlak = max(20, 180 - i * 9)
                        renk = f"#00{parlak:02x}88"
                        c.create_text(mk["x"], yy, text=random.choice("01アイウエオカキABCDEF"),
                                      font=("Consolas", 11, "bold"), fill=renk)
            for p in self.parcaciklar:
                p["x"] += p["vx"]; p["y"] += p["vy"]
                if p["x"] < 0: p["x"] = w
                if p["x"] > w: p["x"] = 0
                if p["y"] < 0: p["y"] = h
                if p["y"] > h: p["y"] = 0
                r = p["r"] * (1 + 0.3 * math.sin(self.anim_sayac * 0.05 + p["x"] * 0.01))
                a = p["a"] * (0.7 + 0.3 * math.sin(self.anim_sayac * 0.03 + p["y"] * 0.01))
                parlak = int(a * 200)
                renk = f"#{parlak:02x}{min(255, parlak + 40):02x}ff"
                c.create_oval(p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r,
                              fill=renk, outline="")
            for i in range(0, w, 60):
                c.create_line(i, 0, i, h, fill="#00101a", width=1)
            for j in range(0, h, 60):
                c.create_line(0, j, w, j, fill="#00101a", width=1)
        except Exception:
            pass
        self.root.after(50, self._parcacik_dongusu)

    def _animasyon_dongusu(self):
        try:
            c = self.halka_canvas
            c.delete("all")
            cx, cy = 210, 210
            self.anim_aci += 0.032
            self.anim_sayac += 1
            mod_renk = self.mod_renk
            for r, rk in [(200, "#001a2a"), (190, "#002a3a"),
                          (180, "#003a4a"), (170, "#004a5a")]:
                c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=rk, width=1)
            tarama = (self.anim_aci * 80) % 360
            c.create_arc(cx-200, cy-200, cx+200, cy+200, start=tarama, extent=25,
                         outline="#003a5a", width=3, style="arc")
            c.create_arc(cx-200, cy-200, cx+200, cy+200, start=tarama, extent=15,
                         outline=mod_renk, width=2, style="arc")
            for i in range(4):
                bas = (self.anim_aci + i * 1.5) * 180 / math.pi
                renk = ["#00ffff", "#00aaff", "#00ff88", "#00ddff"][i]
                c.create_arc(cx-195, cy-195, cx+195, cy+195, start=bas, extent=50,
                             outline="#003355", width=8, style="arc")
                c.create_arc(cx-195, cy-195, cx+195, cy+195, start=bas, extent=50,
                             outline=renk, width=3, style="arc")
            for i in range(3):
                bas = (-self.anim_aci * 1.3 + i * 2.4) * 180 / math.pi
                c.create_arc(cx-170, cy-170, cx+170, cy+170, start=bas, extent=35,
                             outline="#0088ff", width=2, style="arc")
            nab = 108 + math.sin(self.anim_sayac * 0.07) * 6
            c.create_oval(cx-nab, cy-nab, cx+nab, cy+nab, outline=mod_renk, width=2)
            nab2 = 108 + math.sin(self.anim_sayac * 0.07 - 1.5) * 6
            c.create_oval(cx-nab2, cy-nab2, cx+nab2, cy+nab2, outline="#005588", width=1)
            for i in range(3):
                faz = (self.anim_sayac * 0.06 + i * 0.6) % 1.0
                r = 95 + faz * 85
                alfa = int((1 - faz) * 80)
                if alfa > 10:
                    renk = f"#00{alfa:02x}ff"
                    c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=renk, width=1)
            it1 = int(25 + math.sin(self.anim_sayac * 0.08) * 8)
            it2 = int(15 + math.sin(self.anim_sayac * 0.08 + 0.5) * 6)
            c.create_oval(cx-88, cy-88, cx+88, cy+88,
                          fill=f"#{it2:02x}{it1:02x}3a", outline="#0088aa", width=2)
            c.create_oval(cx-80, cy-80, cx+80, cy+80, outline=mod_renk, width=1)
            c.create_text(cx, cy - 18, text="Y.A.H.E.S",
                          font=("Helvetica", 22, "bold"), fill=mod_renk)
            ai_txt = "🧠 v6.3 AI" if _genai_client else "◆ v6.3 ◆"
            ai_col = "#ff8800" if _genai_client else "#00ff88"
            c.create_text(cx, cy + 2, text=ai_txt,
                          font=("Helvetica", 9, "bold"), fill=ai_col)
            if self.surekli_dinleme:
                if self.anim_sayac % 30 < 15:
                    c.create_text(cx, cy + 20, text="🟢 DİNLİYOR",
                                  font=("Helvetica", 8, "bold"), fill="#00ff88")
                else:
                    c.create_text(cx, cy + 20, text="🟢 DİNLİYOR",
                                  font=("Helvetica", 8, "bold"), fill="#00aa55")
            else:
                if self.anim_sayac % 60 < 30:
                    c.create_text(cx, cy + 20, text="● AKTİF",
                                  font=("Helvetica", 8, "bold"), fill="#00ff88")
                else:
                    c.create_text(cx, cy + 20, text="● AKTİF",
                                  font=("Helvetica", 8, "bold"), fill="#00aa55")
            bilgi = MOD_BILGILERI.get(self.aktif_mod, MOD_BILGILERI["normal"])
            c.create_text(cx, cy + 38, text=bilgi["ad"],
                          font=("Helvetica", 7, "bold"), fill=bilgi["renk"])
            for i in range(20):
                aci = self.anim_aci * 2 + i * (math.pi / 10)
                x1 = cx + math.cos(aci) * 92
                y1 = cy + math.sin(aci) * 92
                x2 = cx + math.cos(aci) * 140
                y2 = cy + math.sin(aci) * 140
                c.create_line(x1, y1, x2, y2, fill="#005588", width=1)
            for i in range(16):
                aci = self.anim_aci * 0.6 + i * (math.pi / 8)
                r = 205 + math.sin(self.anim_sayac * 0.05 + i) * 4
                x = cx + math.cos(aci) * r
                y = cy + math.sin(aci) * r
                r2 = 2 if i % 2 == 0 else 1
                c.create_oval(x-r2, y-r2, x+r2, y+r2, fill=mod_renk, outline="")
        except Exception:
            pass
        self.root.after(40, self._animasyon_dongusu)

    def _metrik_dongusu_baslat(self):
        def d():
            while self.metrik_guncelleme_aktif:
                try:
                    if SISTEM_MONITOR_AKTIF:
                        self.metrik_cpu = psutil.cpu_percent(interval=None)
                        self.metrik_ram = psutil.virtual_memory().percent
                        try: self.metrik_disk = psutil.disk_usage('/').percent
                        except: pass
                        if int(time.time()) % 3 == 0:
                            s = cpu_sicakligi_getir()
                            if s is not None: self.metrik_sicaklik = s
                    self.metrik_gecmis_cpu.pop(0); self.metrik_gecmis_cpu.append(self.metrik_cpu)
                    self.metrik_gecmis_ram.pop(0); self.metrik_gecmis_ram.append(self.metrik_ram)
                    self.root.after(0, self._metrik_gui)
                except: pass
                time.sleep(1.0)
        threading.Thread(target=d, daemon=True).start()

    def _metrik_gui(self):
        try:
            self._metrik_ciz(self.cpu_lbl, self.cpu_canvas, self.metrik_cpu, "#00ffff", "CPU")
            self._metrik_ciz(self.ram_lbl, self.ram_canvas, self.metrik_ram, "#00aaff", "RAM")
            self._metrik_ciz(self.disk_lbl, self.disk_canvas, self.metrik_disk, "#00ff88", "DISK")
            if self.metrik_sicaklik is not None:
                sy = min(100, self.metrik_sicaklik)
                self._metrik_ciz(self.sic_lbl, self.sic_canvas, sy, "#ff8844",
                                 f"{self.metrik_sicaklik:>4.0f}C")
            else:
                try: self.sic_lbl.configure(text="SICAKLIK     --")
                except: pass
        except: pass

    def _log_takip_baslat(self):
        def t():
            while True:
                try:
                    m = _gui_log_queue.get(timeout=0.1)
                    try: self.root.after(0, lambda mm=m: self._log_yaz(mm))
                    except: pass
                except queue.Empty: continue
                except: time.sleep(0.1)
        threading.Thread(target=t, daemon=True).start()

    def _log_yaz(self, msg):
        try:
            self.log_text.configure(state="normal")
            et = "cyan"
            u = msg.upper()
            if "[AI]" in u or "GEMINI" in u: et = "orange"
            elif "HATA" in u or "⚠" in msg: et = "red"
            elif "✓" in msg or "TAMAMLANDI" in u: et = "green"
            elif "⏰" in msg or "ALARM" in u: et = "yellow"
            elif "ÖĞREND" in u: et = "magenta"
            self.log_text.insert("end", msg, et)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except: pass

    def _log_gui(self, msg):
        try: self.root.after(0, lambda m=msg: self._log_yaz(m))
        except: pass

    def _mod_degistir(self, yeni_mod):
        if yeni_mod not in MOD_BILGILERI:
            konustur_async(f"'{yeni_mod}' modu bulunamadı.")
            return
        self.aktif_mod = yeni_mod
        self.mod_renk = MOD_BILGILERI[yeni_mod]["renk"]
        mod_kaydet(yeni_mod)
        bilgi = MOD_BILGILERI[yeni_mod]
        self._log_yaz(f"\n{'═'*58}\n")
        self._log_yaz(f"   {bilgi['ikon']} {bilgi['ad']} AKTİF\n")
        self._log_yaz(f"{'═'*58}\n")
        if yeni_mod == "rahatlik":
            self._log_yaz(">> YouTube liste ve abonelikler açılıyor...\n")
            konustur_async("Rahatlık modu aktif. YouTube listeleriniz açılıyor efendim.")
            def yt():
                time.sleep(1.2)
                for link in RAHATLIK_LINKLERI[:2]:
                    webbrowser.open(link)
                    time.sleep(1.5)
            threading.Thread(target=yt, daemon=True).start()
        elif yeni_mod == "odak":
            self._log_yaz(">> Odak modu: Pomodoro başlatıldı.\n")
            konustur_async("Odak modu aktif. 25 dakika çalışma, 5 dakika mola öneriyorum.")
            bildirim_goster("🎯 ODAK MODU", "25 dk çalışma → 5 dk mola")
            def pomo():
                time.sleep(25*60)
                bildirim_goster("🎯 MOLA VAKTİ", "5 dakika mola verin!")
                konustur_async("Mola vakti efendim.")
            threading.Thread(target=pomo, daemon=True).start()
        elif yeni_mod == "gece":
            self._log_yaz(">> Gece modu: Sessiz tema.\n")
            konustur_async("Gece modu aktif. İyi dinlenmeler efendim.")
            bildirim_goster("🌙 GECE MODU", "Sessiz mod aktif")
        elif yeni_mod == "ai":
            if _genai_client:
                self._log_yaz(">> 🧠 AI Modu aktif. Her şeyi sorabilirsiniz.\n")
                konustur_async("Yapay zeka modu aktif efendim. Ne sormak istersiniz?")
                bildirim_goster("🧠 AI MODU", "Gemini AI aktif")
            else:
                self._log_yaz(">> ⚠ AI modu için Gemini API anahtarı gerekli.\n")
                konustur_async("Yapay zeka modu için API anahtarı gerekli efendim.")
                self.aktif_mod = "normal"
                self.mod_renk = MOD_BILGILERI["normal"]["renk"]
                mod_kaydet("normal")
        elif yeni_mod == "normal":
            konustur_async("Normal moda dönüldü.")
        self._mod_gosterge_guncelle()

    def _mod_gosterge_guncelle(self):
        try:
            bilgi = MOD_BILGILERI.get(self.aktif_mod, MOD_BILGILERI["normal"])
            self.mod_lbl.configure(text=f"  {bilgi['ikon']} {bilgi['ad']}  ",
                                   fg=bilgi["renk"], bg="#01040a")
        except: pass

    def _mod_bilgi(self):
        bilgi = MOD_BILGILERI.get(self.aktif_mod, MOD_BILGILERI["normal"])
        konustur_async(f"Şu an {bilgi['ad']} aktif efendim.")
        self._log_yaz(f">> Aktif mod: {bilgi['ad']}\n")
        self._log_yaz(">> Modlar: normal, beyaz sayfa, rahatlık, odak, gece, ai\n")

    def _beyaz_sayfa_onay(self):
        p = tk.Toplevel(self.root)
        p.title("⚠ BEYAZ SAYFA")
        p.configure(bg="#0a0202")
        p.geometry("440x270")
        p.attributes("-topmost", True)
        sw, sh = p.winfo_screenwidth(), p.winfo_screenheight()
        p.geometry(f"440x270+{(sw-440)//2}+{(sh-270)//2}")
        tk.Label(p, text="⚠ BEYAZ SAYFA MODU", font=("Helvetica", 15, "bold"),
                 fg="#ff3333", bg="#0a0202").pack(pady=(20, 8))
        tk.Label(p, text="TÜM öğrenilenler, geçmiş, alarmlar,\nrutinler ve hafıza SİLİNECEK.\nBu işlem geri alınamaz!",
                 font=("Helvetica", 10), fg="#ffcccc", bg="#0a0202",
                 justify="center").pack(pady=10)
        bf = tk.Frame(p, bg="#0a0202"); bf.pack(pady=15)
        def onay():
            p.destroy()
            silinen = beyaz_sayfa_temizle()
            self._log_yaz("\n" + "═"*58 + "\n")
            self._log_yaz("   📄 BEYAZ SAYFA — Her şey sıfırlandı\n")
            self._log_yaz("═"*58 + "\n")
            self._log_yaz(f">> Silinen: {', '.join(silinen) if silinen else 'Hiçbir şey'}\n")
            konustur_async("Her şey sıfırlandı efendim. Yeni bir sayfa açıldı.")
            bildirim_goster("📄 BEYAZ SAYFA", "Sistem sıfırlandı")
            self.aktif_mod = "normal"
            mod_kaydet("normal")
            self._mod_gosterge_guncelle()
        tk.Button(bf, text="✓ EVET, SİL", bg="#330000", fg="#ff6666",
                  font=("Helvetica", 10, "bold"), width=14,
                  command=onay).pack(side="left", padx=5)
        tk.Button(bf, text="✕ İPTAL", bg="#001522", fg="#00ffff",
                  font=("Helvetica", 10, "bold"), width=14,
                  command=p.destroy).pack(side="left", padx=5)

    def _baslangic_selamla(self):
        def g():
            time.sleep(0.5)
            self._log_gui("\n" + "═"*58 + "\n")
            self._log_gui("     Y.A.H.E.S v6.3 - GEMINI AI ENTEGRE\n")
            self._log_gui("═"*58 + "\n\n")
            if _genai_client:
                self._log_gui(f"🧠 [AI]: Gemini bağlantısı AKTİF ({_gemini_model_adi})\n")
                self._log_gui(">> Her türlü soruyu sorabilirsiniz.\n\n")
            else:
                self._log_gui("⚠ [AI]: Gemini bağlantısı KAPALI\n")
                self._log_gui(f">> Sebep: {_gemini_son_hata}\n")
                self._log_gui(f">> '{GEMINI_KEY_DOSYASI}' dosyasına API anahtarı yazın.\n\n")
            h = hafiza_yukle()
            if "isim" not in h:
                self._log_gui(">> Size nasıl hitap etmemi istersiniz?\n")
                konustur("Size nasıl hitap etmemi istersiniz?")
                self._isim_bekle = True
            else:
                self.isim = h["isim"]
                selam = f"Tekrar hoş geldiniz {unvan_getir(self.isim)}!"
                if _genai_client:
                    threading.Thread(target=lambda: gemini_sor_async(
                        f"Kullanıcıya kısa bir karşılama mesajı yaz. İsmi {self.isim}. "
                        "1 cümle olsun, samimi ve motivasyon verici.",
                        callback=lambda y: self._log_gui(f"🧠 [AI]: {y}\n")
                    ), daemon=True).start()
                else:
                    konustur(selam)
                self._log_gui(f">> Hoş geldiniz {self.isim}\n")
                self._hazir()
        threading.Thread(target=g, daemon=True).start()

    def _isim_kaydet(self, isim):
        isim = isim.strip() or "Kullanıcı"
        h = hafiza_yukle(); h["isim"] = isim; hafiza_kaydet(h)
        self.isim = isim
        self._isim_bekle = False
        konustur(f"Tanıştığımıza memnun oldum {isim}.")
        self._log_gui(f">> İsminiz: {isim}\n")
        self._hazir()

    def _hazir(self):
        self._log_gui("\n")
        menuyu_goster()
        self._log_gui("\n[🧠 AI]: Herhangi bir soru sorun, cevaplayayım.\n")
        self._log_gui("[👏 Alkış]: 2 alkış → tam ekran | 3 alkış → sürekli dinleme\n")
        self._log_gui("[F11]: Tam ekran/pencere geçişi.\n\n")
        if WAKE_WORD_AKTIF and SES_TANIMA_AKTIF:
            wake_word_baslat()

    def _giris_gonder(self):
        m = self.giris_entry.get().strip()
        self.giris_entry.delete(0, "end")
        if not m: return
        if self._isim_bekle:
            self._isim_kaydet(m); return
        if self._ogrenme_soru is not None:
            s = self._ogrenme_soru
            self._ogrenme_soru = None
            ok = ogrenme_ekle(s, m)
            if ok:
                konustur_async("Teşekkürler, öğrendim.")
                self._log_yaz(f">> ✓ Öğrenildi: '{s}' → '{m}'\n")
            else:
                self._log_yaz(f">> ⚠ Öğrenilemedi.\n")
            return
        if self._beklenen_mod is not None:
            mod = self._beklenen_mod
            self._beklenen_mod = None
            self._log_yaz(f"[{self.isim}] >> {m}\n")
            threading.Thread(target=self._mod_isle, args=(mod, m), daemon=True).start()
            return
        self._log_yaz(f"\n[{self.isim}] >> {m}\n")
        self.islem_kuyrugu.put(m)

    def _sesli_komut_tetikle(self):
        if self.dinleme_aktif: return
        if not SES_TANIMA_AKTIF:
            self._log_yaz("[Hata]: Ses tanıma yok.\n"); return
        def g():
            self.dinleme_aktif = True
            self.root.after(0, lambda: self.mic_btn.configure(
                text="🎤  DİNLENİYOR...", bg="#550000", fg="#ff6666"))
            try:
                k = sesli_komut_al()
                if k:
                    self.root.after(0, lambda kk=k: self._log_yaz(f"[Sesli] {kk}\n"))
                    self.root.after(0, lambda kk=k: self._sesli_gonder(kk))
                else:
                    self.root.after(0, lambda: self._log_yaz("[Sesli] Anlaşılamadı.\n"))
            finally:
                self.dinleme_aktif = False
                self.root.after(0, lambda: self.mic_btn.configure(
                    text="🎤  SESLİ KOMUT", bg="#001a33", fg="#00ffff"))
        threading.Thread(target=g, daemon=True).start()

    def _sesli_gonder(self, m):
        m = m.strip()
        if not m: return
        self.giris_entry.delete(0, "end")
        self.giris_entry.insert(0, m)
        self._giris_gonder()

    def _islem_kuyruk_tuketici(self):
        while True:
            try:
                i = self.islem_kuyrugu.get(timeout=0.2)
                if i is None: continue
                try: self._komutu_isle(i)
                except Exception as e:
                    try: self._log_gui(f"[Komut Hatası]: {e}\n")
                    except: pass
            except queue.Empty: continue
            except: time.sleep(0.1)

    def _ai_yanitla(self, soru):
        if not _genai_client:
            konustur_async("Yapay zeka bağlantısı yok efendim. API anahtarı gerekli.")
            self._log_yaz(">> ⚠ Gemini API bağlantısı yok.\n")
            return
        self._log_yaz(f"\n🧠 [AI'ya soruluyor]: {soru}\n")
        def _iş():
            yanit = gemini_sor(soru)
            if yanit:
                self._log_gui(f"\n🧠 [AI]: {yanit}\n")
                konustur(yanit)
            else:
                self._log_gui(">> ⚠ AI yanıt veremedi.\n")
                konustur("Yanıt alınamadı efendim.")
        threading.Thread(target=_iş, daemon=True).start()

    def _komutu_isle(self, islem):
        if not islem: return
        islem_orj = islem.strip()
        islem = islem.lower()
        gecmise_yaz(f"Komut: {islem}")

        if islem == "cikis":
            self.root.after(0, self._cikis); return

        try:
            if islem in ["ai", "ai modu", "yapay zeka", "yapay zeka modu"]:
                self.root.after(0, lambda: self._mod_degistir("ai"))
                return
            if islem in ["ai geçmişi temizle", "ai gecmisi temizle", "sohbeti temizle",
                         "ai sıfırla", "ai sifirla"]:
                gemini_gecmisi_temizle()
                self._log_yaz(">> 🧠 AI sohbet geçmişi temizlendi.\n")
                konustur_async("Yapay zeka sohbet geçmişi temizlendi efendim.")
                return
            if islem in ["ai durum", "ai status", "yapay zeka durumu"]:
                if _genai_client:
                    konustur_async(f"Yapay zeka aktif. Model: {_gemini_model_adi}")
                    self._log_yaz(f">> 🧠 AI: AKTİF ({_gemini_model_adi})\n")
                else:
                    konustur_async("Yapay zeka bağlantısı yok efendim.")
                    self._log_yaz(f">> 🧠 AI: KAPALI ({_gemini_son_hata})\n")
                return
            if islem.startswith("ai sor ") or islem.startswith("ai: "):
                s = islem.replace("ai sor ", "", 1).replace("ai: ", "", 1).strip()
                if s:
                    self._ai_yanitla(s)
                return

            if islem in ["öğrendiklerim", "ogrendiklerim", "ne öğrendin", "öğrenilenler"]:
                ogrenme_listele(); return
            if islem.startswith("öğren ") or islem.startswith("ogren "):
                s = re.sub(r'^(öğren|ogren)\s+', '', islem, count=1).strip()
                if s:
                    self._ogrenme_soru = s
                    self._log_yaz(f"\n>> '{s}' sorusuna ne cevap vereyim?\n")
                    konustur_async(f"'{s}' sorusuna ne cevap vermemi istersiniz?")
                else:
                    konustur_async("Ne öğretmek istersiniz? 'öğren X' şeklinde söyleyin.")
                return
            if islem.startswith("unut "):
                s = islem.replace("unut","",1).strip()
                if s:
                    if ogrenme_sil(s):
                        konustur_async(f"'{s}' unutuldu.")
                        self._log_yaz(f">> ✓ Unutuldu: '{s}'\n")
                    else:
                        konustur_async(f"'{s}' bulunamadı.")
                return
            if islem in ["sürekli dinleme", "surekli dinleme", "dinlemeye başla", "dinlemeye basla"]:
                self.root.after(0, self._surekli_dinlemeyi_baslat); return
            if islem in ["dinlemeyi durdur", "sürekli dinlemeyi kapat",
                         "surekli dinlemeyi kapat", "dinlemeyi kapat"]:
                self.root.after(0, self._surekli_dinlemeyi_durdur); return
            if islem in ["beyaz sayfa", "beyazsayfa", "hafızayı sil", "hafizayi sil",
                         "sıfırla", "sifirla", "kendini sil", "her şeyi sil"]:
                self.root.after(0, self._beyaz_sayfa_onay); return
            elif islem in ["rahatlık modu", "rahatlik modu", "rahatla", "rahat mod"]:
                self.root.after(0, lambda: self._mod_degistir("rahatlik")); return
            elif islem in ["odak modu", "odaklan", "çalışma modu", "calisma modu"]:
                self.root.after(0, lambda: self._mod_degistir("odak")); return
            elif islem in ["gece modu", "gece", "uyku modu"]:
                self.root.after(0, lambda: self._mod_degistir("gece")); return
            elif islem in ["normal mod", "gündüz modu", "gunduz modu"]:
                self.root.after(0, lambda: self._mod_degistir("normal")); return
            elif islem in ["mod", "hangi mod", "aktif mod", "modlar"]:
                self.root.after(0, self._mod_bilgi); return

            m_ac = re.match(r'^(.+?)\s+(aç|ac|başlat|baslat|başlatır|calistir|çalıştır)$', islem)
            if m_ac:
                hedef = m_ac.group(1).strip()
                if hedef in ["uygulama", "program"]:
                    self._girdi_iste("Hangi uygulamayı açayım?", "uyg_ac")
                else:
                    self._log_yaz(f"\n>> 🚀 {hedef} başlatılıyor...\n")
                    def _ac():
                        bas, msg, ad = uygulama_baslat(hedef)
                        self._log_gui(f">> {'✓' if bas else '⚠'} {msg}\n")
                        konustur_async(msg)
                    threading.Thread(target=_ac, daemon=True).start()
                return
            m_ac2 = re.match(r'^(aç|ac|başlat|baslat|çalıştır|calistir)\s+(.+)$', islem)
            if m_ac2:
                hedef = m_ac2.group(2).strip()
                if hedef in ["uygulama", "program"]:
                    self._girdi_iste("Hangi uygulamayı açayım?", "uyg_ac")
                else:
                    self._log_yaz(f"\n>> 🚀 {hedef} başlatılıyor...\n")
                    def _ac2():
                        bas, msg, ad = uygulama_baslat(hedef)
                        self._log_gui(f">> {'✓' if bas else '⚠'} {msg}\n")
                        konustur_async(msg)
                    threading.Thread(target=_ac2, daemon=True).start()
                return
            if len(islem.split()) <= 3:
                norm_islem = _normalize(islem)
                for exe, aliaslar in UYGULAMA_ALIASLARI.items():
                    for al in aliaslar:
                        al_n = _normalize(al)
                        if norm_islem == al_n:
                            self._log_yaz(f"\n>> 🚀 {exe} başlatılıyor...\n")
                            def _ac3(e=exe):
                                bas, msg, ad = uygulama_baslat(e)
                                self._log_gui(f">> {'✓' if bas else '⚠'} {msg}\n")
                                konustur_async(msg)
                            threading.Thread(target=_ac3, daemon=True).start()
                            return

            if islem in ["uygulama listesi", "uygulamalar", "kurulu uygulamalar", "programlar"]:
                threading.Thread(target=uygulama_listesi_yazdir, daemon=True).start()
                konustur_async("Kurulu uygulamalar konsola yazdırılıyor efendim.")
                return
            if islem in ["uygulama tara", "uygulamaları tara", "yeniden tara"]:
                global _SISTEM_UYGULAMA_CACHE
                _SISTEM_UYGULAMA_CACHE = None
                threading.Thread(target=_sistem_uygulamalarini_getir, daemon=True).start()
                konustur_async("Uygulamalar yeniden taranıyor efendim.")
                return
            if islem in ["uyg", "uygulama", "program"]:
                self._girdi_iste("Hangi uygulamayı açayım?", "uyg_ac")
                return

            ogr = ogrenme_ara(islem)
            if ogr:
                self._log_yaz(f">> [Öğrenilmiş] {ogr}\n")
                konustur_async(ogr)
                return

            if any(k in islem for k in ["selam","merhaba","nasılsın","nasıl","naber","nbr"]):
                konustur_async(random.choice([
                    f"Teşekkür ederim {unvan_getir(self.isim)}, iyiyim.",
                    "Harika çalışıyorum efendim!",
                    "Çok iyiyim teşekkürler, siz nasılsınız?"]))
            elif any(k in islem for k in ["teşekkür","sağol","saol"]):
                konustur_async(f"Rica ederim {unvan_getir(self.isim)}.")
            elif islem in ["yardim","menu","komutlar","yardım"]:
                menuyu_goster()
            elif islem in ["sistem","cpu","ram","işlemci"]:
                konustur_async(sistem_durumu_getir())
                threading.Thread(target=sistem_durumu_detayli, daemon=True).start()
            elif islem in ["sistem detay","detaylı sistem","sistem detayı"]:
                threading.Thread(target=sistem_durumu_detayli, daemon=True).start()
                konustur_async(sistem_durumu_getir())
            elif islem in ["rutin","rutinler"]:
                rutin_listele()
            elif islem.startswith("rutin ekle"):
                self.root.after(0, self._rutin_ekle_dialog)
            elif islem.startswith("rutin düzenle"):
                a = islem.replace("rutin düzenle","").strip()
                if a: self.root.after(0, lambda aa=a: self._rutin_duzenle_dialog(aa))
            elif islem.startswith("rutin sil"):
                a = islem.replace("rutin sil","").strip()
                if a: rutin_sil(a)
            elif islem.startswith("rutin "):
                a = islem.replace("rutin","").strip()
                if a: rutin_calistir(a, self.isim, otomatik=False)
            elif islem in ["google","ara"]:
                self._girdi_iste("Ne aratmak istersiniz?", "google_ara")
            elif islem in ["youtube","yt"]:
                self._girdi_iste("YouTube'da ne aratayım?", "youtube_ara")
            elif islem in ["wiki","vikipedi"]:
                self._girdi_iste("Vikipedi'de ne aratayım?", "wiki_ara")
            elif islem in ["saat"]:
                konustur_async(f"Şu an saat {datetime.now().strftime('%H:%M, %d.%m.%Y')}")
            elif islem in ["hava","havadurumu","hava durumu"]:
                self._girdi_iste("Hangi şehir? (Boş = Istanbul)", "hava_sor")
            elif islem in ["doviz","kur","döviz"]:
                konustur_async(doviz_kuru_getir())
            elif islem == "bilgi":
                konustur_async(random.choice(RASTGELE_BILGILER))
            elif islem in ["alarm","hatirlatma","hatırlatma"]:
                self._girdi_iste("Ne zaman? Örnek: yarın 07:00", "alarm_zaman")
            elif islem in ["alarmlar"]:
                l = alarmlari_yukle()
                ak = [a for a in l if not a.get("caldi", False)]
                if ak:
                    konustur_async(f"{len(ak)} aktif alarm var.")
                    for a in ak: print(f"-> {a['zaman']} | {a['mesaj']}")
                else: konustur_async("Aktif alarm yok.")
            elif islem in ["+","-","*","/"]:
                self.root.after(0, lambda i=islem: self._matematik_dialog(i))
            elif islem in ["tam ekran","tamekran","fullscreen","f11"]:
                self.root.after(0, self._tam_ekran_toggle)
                konustur_async("Tam ekran modu değiştirildi.")
            else:
                if _genai_client:
                    self._ai_yanitla(islem_orj)
                else:
                    konustur_async(f"'{islem}' komutunu bilmiyorum efendim. "
                                   f"Yapay zeka için API anahtarı gerekli.")
                    self._log_yaz(f"\n>> Bilinmeyen: '{islem}'\n")
                    self._log_yaz(f">> AI için '{GEMINI_KEY_DOSYASI}' dosyasına anahtar yazın.\n")
        except Exception as e:
            try: self._log_gui(f"[Komut Hatası]: {e}\n")
            except: pass

    def _girdi_iste(self, baslik, mod):
        self._beklenen_mod = mod
        self._log_gui(f">> {baslik}\n")
        konustur_async(baslik)
        self.root.after(0, lambda: (self.giris_entry.delete(0, "end"),
                                    self.giris_entry.focus_set()))

    def _mod_isle(self, mod, d):
        try:
            if mod == "google_ara":
                if d: konustur_async(google_ara(d))
            elif mod == "youtube_ara":
                if d: konustur_async(youtube_ara_ve_ac(d))
            elif mod == "wiki_ara":
                if d: konustur_async(vikipedi_ara(d))
            elif mod == "hava_sor":
                konustur_async(hava_durumu_getir(d or "Istanbul"))
            elif mod == "uyg_ac":
                if d:
                    self._log_yaz(f"\n>> 🚀 {d} başlatılıyor...\n")
                    bas, msg, ad = uygulama_baslat(d)
                    self._log_yaz(f">> {'✓' if bas else '⚠'} {msg}\n")
                    konustur_async(msg)
            elif mod == "alarm_zaman":
                if d:
                    h = akilli_zaman_cozumle(d)
                    self._alarm_mesaj_bekle = h
                    self._girdi_iste("Mesaj ne olsun?", "alarm_mesaj")
            elif mod == "alarm_mesaj":
                h = self._alarm_mesaj_bekle
                if h and d:
                    l = alarmlari_yukle()
                    l.append({"tur":"alarm","zaman":h,"mesaj":d,"caldi":False})
                    alarmlari_kaydet(l)
                    konustur_async(f"{h} için alarm kuruldu.")
                    self._alarm_mesaj_bekle = None
        except Exception as e:
            self._log_gui(f"[Mod Hatası]: {e}\n")

    def _matematik_dialog(self, islem):
        p = tk.Toplevel(self.root)
        p.title("Matematik")
        p.configure(bg="#020810")
        p.geometry("300x230")
        p.attributes("-topmost", True)
        tk.Label(p, text=f"İşlem: {islem}", font=("Helvetica", 12, "bold"),
                 fg="#00ffff", bg="#020810").pack(pady=10)
        tk.Label(p, text="1. Sayı:", fg="#fff", bg="#020810").pack()
        e1 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e1.pack()
        tk.Label(p, text="2. Sayı:", fg="#fff", bg="#020810").pack()
        e2 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e2.pack()
        def h():
            try:
                s1, s2 = float(e1.get()), float(e2.get())
                if islem == "+": r = s1+s2
                elif islem == "-": r = s1-s2
                elif islem == "*": r = s1*s2
                elif islem == "/": r = s1/s2 if s2 != 0 else "Sıfıra bölünemez"
                konustur_async(f"Sonuç: {r}"); p.destroy()
            except: konustur_async("Hatalı giriş.")
        tk.Button(p, text="HESAPLA", bg="#003355", fg="#00ffff",
                  command=h).pack(pady=10)

    def _rutin_ekle_dialog(self):
        p = tk.Toplevel(self.root)
        p.title("Yeni Rutin")
        p.configure(bg="#020810")
        p.geometry("460x420")
        p.attributes("-topmost", True)
        def lbl(t):
            tk.Label(p, text=t, fg="#00ffff", bg="#020810",
                     font=("Helvetica", 10, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        lbl("Rutin Adı:")
        e1 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e1.pack(fill="x", padx=20)
        lbl("Açıklama:")
        e2 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e2.pack(fill="x", padx=20)
        lbl("Adımlar:")
        tk.Label(p, text="hava_otomatik, saat, gunaydin, iyigeceler,\nmotivasyon, doviz, bilgi, sistem",
                 fg="#6688aa", bg="#020810", font=("Helvetica", 8, "italic"),
                 justify="left").pack(anchor="w", padx=20)
        e3 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e3.pack(fill="x", padx=20)
        lbl("Otomatik Saat (SS:DD):")
        e4 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e4.pack(fill="x", padx=20)
        def k():
            if rutin_ekle_gui(e1.get(), e2.get(), e3.get(), e4.get()): p.destroy()
        tk.Button(p, text="KAYDET", bg="#003355", fg="#00ffff",
                  font=("Helvetica", 11, "bold"), command=k).pack(pady=15)

    def _rutin_duzenle_dialog(self, ad):
        rl = rutinleri_yukle()
        if ad not in rl:
            konustur_async(f"'{ad}' bulunamadı."); return
        r = rl[ad]
        p = tk.Toplevel(self.root)
        p.title(f"Düzenle: {ad}")
        p.configure(bg="#020810")
        p.geometry("460x360")
        p.attributes("-topmost", True)
        def lbl(t):
            tk.Label(p, text=t, fg="#00ffff", bg="#020810",
                     font=("Helvetica", 10, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        lbl("Açıklama:")
        e1 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e1.insert(0, r.get("aciklama","")); e1.pack(fill="x", padx=20)
        lbl("Adımlar:")
        e2 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e2.insert(0, ", ".join(r.get("adimlar",[]))); e2.pack(fill="x", padx=20)
        lbl("Otomatik Saat:")
        e3 = tk.Entry(p, bg="#020810", fg="#fff", insertbackground="#0ff")
        e3.insert(0, r.get("otomatik_saat","")); e3.pack(fill="x", padx=20)
        def k():
            rutin_duzenle_gui(ad, e1.get(), e2.get(), e3.get()); p.destroy()
        tk.Button(p, text="GÜNCELLE", bg="#003355", fg="#00ffff",
                  font=("Helvetica", 11, "bold"), command=k).pack(pady=15)

    def _cikis_dogru(self):
        self._log_yaz("\n>> Pencere simge durumuna küçültüldü.\n")
        try: self.root.iconify()
        except: pass

    def _cikis(self):
        self.metrik_guncelleme_aktif = False
        wake_word_durdur.set()
        self.surekli_dinleme_durdur.set()
        self.surekli_dinleme = False
        try:
            if self.tray: self.tray.stop()
        except: pass
        konustur_async(f"Görüşmek üzere {unvan_getir(self.isim)}!")
        self.root.after(900, self.root.destroy)

    def run(self):
        self.root.mainloop()

# ============================================================
# --- ANA ---
# ============================================================
def main():
    if not tek_ornek_kontrol():
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showinfo("Y.A.H.E.S",
                "Zaten çalışıyor.\nSistem tepsisindeki ikona bakın.")
            r.destroy()
        except Exception:
            pass
        return

    uyku_engelle()
    otomatik_baslangic_kur()

    print("[Sistem]: Y.A.H.E.S v6.3 başlatılıyor...")
    print(f"[Sistem]: Script klasörü: {SCRIPT_DIZINI}")
    print(f"[Sistem]: Çalışma klasörü: {os.getcwd()}")
    if GEMINI_AKTIF:
        print("[Gemini]: Başlatılıyor...")
        basarili = gemini_baslat()
        if basarili:
            gemini_sohbet_gecmisi_yukle()
            print("[Gemini]: ✓✓✓ AI HAZIR!")
        else:
            print(f"[Gemini]: ✗ AI başlatılamadı: {_gemini_son_hata}")
    else:
        print("[Gemini]: Modül yok. 'pip install google-genai'")

    if "--no-splash" not in sys.argv:
        try:
            Yahes3DAnimasyon()
        except Exception as e:
            print(f"[Splash Hatası]: {e}")

    gui = YahesGUI()
    gui.run()

if __name__ == "__main__":
    main()