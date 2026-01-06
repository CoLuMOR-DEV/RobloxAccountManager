import customtkinter as ctk
import json
import os
import threading
import time
import requests
import base64
import sys
import uuid
import webbrowser
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps
from tkinter import messagebox
import tkinter.font as tkfont

# ==========================================
#           SELENIUM EDGE IMPORTS
# ==========================================
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
#           CONFIGURATION & THEME
# ==========================================

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DRIVER_PATH = r"msedgedriver.exe"

APP_NAME = "cx.manager"
VERSION = "v2.2.2 (Compact + Image Fix)"

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
DEFAULT_PLACE_ID = "4924922222"

DIRS = {
    "data": "data",
    "cache": "data/cache",
    "sessions": "data/sessions"
}

FILES = {
    "accounts": "data/cx_accounts.json",
    "config": "data/config.json",
    "log": "data/latest.log"
}

CONFIG = {
    "theme_mode": "Dark",
    "accent_color": "Blue",
    "fps_unlock": False,
    "potato_mode": False,
    "multi_session": False,
    "use_fishstrap": True,
    "discord_webhook": ""
}

THEME = {
    "bg": "#0b0b10", 
    "sidebar": "#0b0b10", 
    "card_bg": "#1c1c1e",
    "card_hover": "#2c2c2e",
    "text_main": "#ffffff",
    "text_sub": "#8e8e93",
    "accent": "#0a84ff",
    "accent_hover": "#409cff",
    "success": "#30d158",
    "danger": "#ff453a",
    "warning": "#ff9f0a",
    "gray": "#8e8e93",
    "link": "#64d2ff",
    "input_bg": "#2c2c2e",
    "border": "#3a3a3c",
    "separator": "#3a3a3c",
}

# ==========================================
#        iOS THEME + FONT MANAGEMENT
# ==========================================

class FontManager:
    family_ui = "Segoe UI"
    family_mono = "Consolas"

    @classmethod
    def init(cls, root):
        try:
            fams = set(tkfont.families(root))
        except Exception:
            fams = set()

        ui_candidates = [
            "SF Pro Display", 
            "SF Pro Text", 
            "San Francisco", 
            "Helvetica Neue", 
            "Segoe UI Variable", 
            "Segoe UI"
        ]
        
        mono_candidates = [
            "SF Mono", 
            "Cascadia Mono", 
            "Consolas"
        ]

        for f in ui_candidates:
            if f in fams:
                cls.family_ui = f
                break

        for f in mono_candidates:
            if f in fams:
                cls.family_mono = f
                break

    @classmethod
    def ui(cls, size, weight="normal"):
        return (cls.family_ui, size, weight)

    @classmethod
    def mono(cls, size, weight="normal"):
        return (cls.family_mono, size, weight)


class ThemeManager:
    IOS_LIGHT = {
        "bg": "#F2F2F7", 
        "sidebar": "#F2F2F7", 
        "card_bg": "#FFFFFF", 
        "card_hover": "#E5E5EA",
        "text_main": "#000000", 
        "text_sub": "#6E6E73", 
        "success": "#34C759", 
        "danger": "#FF3B30",
        "warning": "#FF9500", 
        "gray": "#8E8E93", 
        "link": "#007AFF", 
        "input_bg": "#FFFFFF",
        "border": "#C6C6C8", 
        "separator": "#C6C6C8", 
        "accent": "#007AFF", 
        "accent_hover": "#338CFF",
    }

    IOS_DARK = {
        "bg": "#000000", 
        "sidebar": "#000000", 
        "card_bg": "#1C1C1E", 
        "card_hover": "#2C2C2E", 
        "text_main": "#FFFFFF", 
        "text_sub": "#8E8E93", 
        "success": "#30D158", 
        "danger": "#FF453A", 
        "warning": "#FF9F0A", 
        "gray": "#8E8E93", 
        "link": "#64D2FF", 
        "input_bg": "#2C2C2E", 
        "border": "#3A3A3C", 
        "separator": "#3A3A3C", 
        "accent": "#0A84FF", 
        "accent_hover": "#409CFF", 
    }

    ACCENTS_LIGHT = {
        "Blue": ("#007AFF", "#338CFF"),
        "Green": ("#34C759", "#5CD77F"),
        "Orange": ("#FF9500", "#FFB13A"),
        "Purple": ("#AF52DE", "#C77BEB"),
        "Pink": ("#FF2D55", "#FF5C7B"),
    }

    ACCENTS_DARK = {
        "Blue": ("#0A84FF", "#409CFF"),
        "Green": ("#30D158", "#5CE27A"),
        "Orange": ("#FF9F0A", "#FFB54A"),
        "Purple": ("#BF5AF2", "#D17CFA"),
        "Pink": ("#FF375F", "#FF5C7C"),
    }

    @classmethod
    def apply(cls):
        mode = (CONFIG.get("theme_mode") or "Dark").strip()
        
        if mode.lower() not in ("dark", "light", "system"):
            mode = "Dark"

        try:
            ctk.set_appearance_mode(mode.capitalize())
        except Exception:
            pass

        is_dark = mode.lower() == "dark" or (mode.lower() == "system")
        palette = cls.IOS_DARK if is_dark else cls.IOS_LIGHT
        THEME.update(palette)

        accent_name = (CONFIG.get("accent_color") or "Blue").strip().title()
        
        if is_dark:
            accent_map = cls.ACCENTS_DARK
        else:
            accent_map = cls.ACCENTS_LIGHT
            
        if accent_name not in accent_map:
            accent_name = "Blue"
            
        a, ah = accent_map[accent_name]
        
        THEME["accent"] = a
        THEME["accent_hover"] = ah
        
        if not is_dark:
            THEME["link"] = a 
        else:
            THEME["link"] = THEME["link"]

ctk.set_default_color_theme("blue")


# ==========================================
#              HELPER CLASSES
# ==========================================

class Utils:
    @staticmethod
    def ensure_dirs():
        for d in DIRS.values():
            os.makedirs(d, exist_ok=True)
        if not os.path.exists(FILES["log"]):
            try:
                with open(FILES["log"], "w") as f:
                    f.write(f"[{datetime.now()}] cx.manager started\n")
            except Exception:
                pass
        
        if os.path.exists(DIRS["sessions"]):
            try:
                shutil.rmtree(DIRS["sessions"])
                os.makedirs(DIRS["sessions"], exist_ok=True)
            except Exception:
                pass

    @staticmethod
    def log_to_file(msg):
        try:
            with open(FILES["log"], "a", encoding="utf-8") as f:
                f.write(f"{msg}\n")
        except Exception:
            pass

    @staticmethod
    def timestamp_msg(msg):
        t = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{t}] {msg}"
        Utils.log_to_file(formatted)
        return formatted

    @staticmethod
    def time_ago(ts):
        if not ts: return "Never"
        diff = time.time() - ts
        if diff < 60: return "Just now"
        if diff < 3600: return f"{int(diff // 60)}m ago"
        return f"{int(diff // 3600)}h ago"
        
    @staticmethod
    def clean_game_cache():
        try:
            if os.path.exists(DIRS["cache"]):
                for f in os.listdir(DIRS["cache"]):
                    if f.startswith("univ_") and f.endswith(".png"):
                        try: os.remove(os.path.join(DIRS["cache"], f))
                        except: pass
        except: pass

    @staticmethod
    def center_window(window, width, height):
        window.update_idletasks()
        try:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
        except:
            screen_width = 1920
            screen_height = 1080
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    @staticmethod
    def circle_crop(img):
        # Resize to smaller first to save processing if big
        img = img.resize((150, 150), Image.Resampling.LANCZOS)
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + img.size, fill=255)
        output = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        return output

    @staticmethod
    def compute_account_health(acc: dict) -> int:
        score = 0
        try:
            if acc.get("status") == "OK": score += 40
            if int(acc.get("robux", 0)) > 0: score += 20
            if time.time() - acc.get("last_used", 0) < 3600: score += 20
            if acc.get("userid"): score += 20
        except: pass
        return min(score, 100)


class PotatoMode:
    @staticmethod
    def get_settings(enabled=True):
        if enabled:
            return {
                "DFIntTaskSchedulerTargetFps": 15,
                "FIntRenderShadowIntensity": 0,
                "FIntDebugTextureManagerSkipPrio": 1,
                "FFlagDebugDisableShadowMap": "True",
                "DFFlagVideoSimplePreRoll": "True",
            }
        return {"DFIntTaskSchedulerTargetFps": 60}

    @staticmethod
    def apply(enabled=True):
        local_app_data = os.getenv("LOCALAPPDATA")
        roblox_versions = os.path.join(local_app_data, "Roblox", "Versions")
        if not os.path.exists(roblox_versions): return
        settings_data = PotatoMode.get_settings(enabled)
        for root, dirs, files in os.walk(roblox_versions):
            if "RobloxPlayerBeta.exe" in files:
                c_path = os.path.join(root, "ClientSettings")
                os.makedirs(c_path, exist_ok=True)
                with open(os.path.join(c_path, "ClientAppSettings.json"), "w") as f:
                    json.dump(settings_data, f)


class DiscordNotifier:
    @staticmethod
    def resolve_job_id(api_ref, user_id):
        if not user_id: return None
        for _ in range(15):
            time.sleep(3)
            presence = api_ref.get_presence(user_id)
            if presence and presence.get("userPresenceType") == 2:
                return presence.get("gameId")
        return None

    @staticmethod
    def send_launch_log(api_ref, username, game_name, place_id, initial_job_id, user_id, manual_track=False, robux="0"):
        url = CONFIG.get("discord_webhook")
        if not url: return

        def _task():
            real_job_id = initial_job_id
            if not real_job_id and user_id:
                real_job_id = DiscordNotifier.resolve_job_id(api_ref, user_id)

            game_link = f"https://www.roblox.com/games/{place_id}"
            user_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://tr.rbxcdn.com/53eb9b17fe1432a809c73a13889b5006/150/150/Image/Png"
            
            try:
                r_icon = requests.get(f"https://thumbnails.roblox.com/v1/places/gameicons?placeIds={place_id}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false").json()
                final_icon = r_icon['data'][0]['imageUrl']
            except:
                final_icon = user_thumb

            embed = {
                "title": f"Session Started: {username}",
                "url": game_link,
                "color": 0x0A84FF,
                "fields": [
                    {
                        "name": "Game", 
                        "value": f"{game_name} \n([View Game Page]({game_link}))", 
                        "inline": True
                    },
                    {
                        "name": "Robux", 
                        "value": f"R$ {robux}", 
                        "inline": True
                    },
                    {
                        "name": "Status", 
                        "value": "Launching via Manager", 
                        "inline": True
                    }
                ],
                "thumbnail": {"url": final_icon},
                "author": {"name": "cx.manager", "icon_url": user_thumb},
                "footer": {"text": f"cx.manager {VERSION}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            try: requests.post(url, json={"embeds": [embed]})
            except: pass

        threading.Thread(target=_task, daemon=True).start()

    @staticmethod
    def send_test(url):
        if not url: return "No URL provided."
        try:
            embed = {
                "title": "Webhook Connected",
                "description": "cx.manager is successfully linked.",
                "color": 0x30D158,
                "footer": {"text": f"cx.manager {VERSION}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            r = requests.post(url, json={"embeds": [embed]})
            return f"Sent (Status: {r.status_code})"
        except Exception as e:
            return f"Error: {e}"


class Security:
    @staticmethod
    def encrypt(t): return "ENC_" + base64.b64encode(t.encode()).decode() if t else ""
    @staticmethod
    def decrypt(t): return base64.b64decode(t[4:]).decode() if t and t.startswith("ENC_") else t


class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(FILES["config"]):
            try:
                with open(FILES["config"], "r") as f:
                    CONFIG.update(json.load(f))
            except: pass

        CONFIG.setdefault("theme_mode", "Dark")
        CONFIG.setdefault("accent_color", "Blue")
        CONFIG.setdefault("fps_unlock", False)
        CONFIG.setdefault("potato_mode", False)
        CONFIG.setdefault("use_fishstrap", True)
        CONFIG.setdefault("discord_webhook", "")
        ThemeManager.apply()

    @staticmethod
    def save():
        try:
            with open(FILES["config"], "w") as f:
                json.dump(CONFIG, f, indent=4)
        except: pass


class DataManager:
    @staticmethod
    def load():
        if os.path.exists(FILES["accounts"]):
            try:
                with open(FILES["accounts"]) as f: return json.load(f)
            except: pass
        return []

    @staticmethod
    def save(d):
        try:
            with open(FILES["accounts"], "w") as f: json.dump(d, f, indent=4)
        except: pass


class FPSUnlocker:
    @staticmethod
    def toggle_unlock(enable):
        local_app_data = os.getenv("LOCALAPPDATA")
        roblox_versions = os.path.join(local_app_data, "Roblox", "Versions")
        if not os.path.exists(roblox_versions): return "Roblox not found."
        count = 0
        try:
            for root, dirs, files in os.walk(roblox_versions):
                if "RobloxPlayerBeta.exe" in files:
                    settings_dir = os.path.join(root, "ClientSettings")
                    settings_file = os.path.join(settings_dir, "ClientAppSettings.json")
                    if enable:
                        if not os.path.exists(settings_dir): os.makedirs(settings_dir)
                        with open(settings_file, "w") as f: json.dump({"DFIntTaskSchedulerTargetFps": 9999}, f)
                        count += 1
                    else:
                        if os.path.exists(settings_file): os.remove(settings_file); count += 1
            return f"Applied to {count} versions."
        except Exception as e: return f"Error: {e}"


class GlobalSession:
    _sess = requests.Session()
    _sess.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    })
    @classmethod
    def get(cls, url): return cls._sess.get(url, timeout=10)
    @classmethod
    def post(cls, url, json=None): return cls._sess.post(url, json=json, timeout=10)


class ImageHandler:
    @staticmethod
    def fetch_avatar_async(uid, path, cb, size=(45, 45)):
        def _task():
            try:
                # 1. Try Cache
                if os.path.exists(path):
                    if os.path.getsize(path) > 100:
                        try:
                            pil_img = Utils.circle_crop(Image.open(path).convert("RGBA"))
                            cb(ctk.CTkImage(pil_img, size=size)); return
                        except: pass
                    else:
                        try: os.remove(path) # Corrupt/empty
                        except: pass
                
                # 2. Fetch
                r = GlobalSession.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=150x150&format=Png&isCircular=false")
                if r.status_code == 200:
                    d = r.json().get("data", [])
                    if d and d[0]["state"] == "Completed":
                        img_url = d[0]["imageUrl"]
                        ir = GlobalSession.get(img_url)
                        if ir.status_code == 200 and len(ir.content) > 100:
                             with open(path, "wb") as f: f.write(ir.content)
                             pil_img = Utils.circle_crop(Image.open(BytesIO(ir.content)).convert("RGBA"))
                             cb(ctk.CTkImage(pil_img, size=size))
            except Exception as e:
                print(f"Avatar Fetch Error {uid}: {e}")
        threading.Thread(target=_task, daemon=True).start()

    @staticmethod
    def fetch_image_async(url, path, cb, size=(128, 128)):
        def _task():
            try:
                # 1. Try Cache
                if os.path.exists(path):
                    if os.path.getsize(path) > 100:
                         try: cb(ctk.CTkImage(Image.open(path), size=size)); return
                         except: pass
                    else:
                        try: os.remove(path)
                        except: pass

                # 2. Fetch
                if not url: return
                r = GlobalSession.get(url)
                if r.status_code == 200 and len(r.content) > 100:
                    with open(path, "wb") as f: f.write(r.content)
                    cb(ctk.CTkImage(Image.open(BytesIO(r.content)), size=size))
            except Exception as e:
                print(f"Image Fetch Error: {e}")
        threading.Thread(target=_task, daemon=True).start()

    @staticmethod
    def get_cached_avatar(uid):
        p = f"{DIRS['cache']}/{uid}.png"
        if os.path.exists(p) and os.path.getsize(p) > 100:
            try:
                img = Image.open(p).convert("RGBA")
                pil_img = Utils.circle_crop(img)
                return ctk.CTkImage(pil_img, size=(45, 45))
            except: pass
        return None


# ==========================================
#            CORE LOGIC CLASSES
# ==========================================

class RobloxAPI:
    def __init__(self, log_func): self.log = log_func
    
    def _create_session(self, proxy=None):
        s = requests.Session()
        s.headers.update({"User-Agent": DEFAULT_UA, "Origin": "https://www.roblox.com", "Referer": "https://www.roblox.com/"})
        if proxy: s.proxies.update({"http": proxy, "https": proxy})
        return s

    def launch(self, acc, place, ua, job_id=None, proxy=None):
        cookie = acc.get("cookie")
        s = self._create_session(proxy)
        if ua: s.headers.update({"User-Agent": ua})
        
        try:
            s.cookies[".ROBLOSECURITY"] = cookie
            csrf_req = s.post("https://auth.roblox.com/v2/logout", timeout=10)
            csrf = csrf_req.headers.get("x-csrf-token")
            if not csrf: return "Invalid Cookie / No CSRF"
            
            r = s.post("https://auth.roblox.com/v1/authentication-ticket", headers={"x-csrf-token": csrf, "Content-Type": "application/json"}, timeout=10)
            ticket = r.headers.get("rbx-authentication-ticket")
            if not ticket: return f"Launch Error: No Ticket (Code {r.status_code})"
            
            ts = int(time.time() * 1000)
            req = "RequestGameJob" if job_id else "RequestGame"
            job_p = f"%26gameId%3D{job_id}" if job_id else ""
            url = f"https%3A%2F%2Fassetgame.roblox.com%2Fgame%2FPlaceLauncher.ashx%3Frequest%3D{req}%26browserTrackerId%3D{ts}%26placeId%3D{place}{job_p}%26isPlayTogetherGame%3Dfalse"
            
            # Fishstrap Integration
            if CONFIG.get("use_fishstrap", True):
                local_app_data = os.getenv('LOCALAPPDATA')
                fish_path = os.path.join(local_app_data, "Fishstrap", "Fishstrap.exe")
                if not os.path.exists(fish_path): 
                    fish_path = os.path.join(local_app_data, "Bloxstrap", "Bloxstrap.exe")
                
                if os.path.exists(fish_path):
                    launch_arg = f"roblox-player:1+launchmode:play+gameinfo:{ticket}+launchtime:{ts}+placelauncherurl:{url}"
                    subprocess.Popen([fish_path, launch_arg])
                    return "Launched via Fishstrap"
                else:
                    self.log("Fishstrap/Bloxstrap not found. Using default...")

            # Default Launch
            cmd = f"roblox-player:1+launchmode:play+gameinfo:{ticket}+launchtime:{ts}+placelauncherurl:{url}"
            os.startfile(cmd)
            return True
        except Exception as e: return str(e)

    def get_game_name(self, place_id):
        try:
            r = GlobalSession.get(f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}")
            d = r.json()
            if d and len(d) > 0: return d[0]["name"]
            
            r2 = GlobalSession.get(f"https://games.roblox.com/v1/games?universeIds={place_id}")
            d2 = r2.json()
            if d2.get("data"): return d2["data"][0]["name"]

            return f"Place {place_id}"
        except: return f"Place {place_id}"

    def search_games_optimized(self, query):
        try:
            sid = str(uuid.uuid4())
            r = GlobalSession.get(f"https://apis.roblox.com/search-api/omni-search?searchQuery={query}&sessionId={sid}&pageType=all")
            d = r.json(); uids = []; results = []
            if "searchResults" in d:
                for grp in d["searchResults"]:
                    if grp.get("contentGroupType") == "Game":
                        for g in grp.get("contents", []):
                            if len(uids) >= 12: break
                            uid = g.get("contentId")
                            if uid: uids.append(uid); results.append({"name": g.get("name"), "universeId": uid, "placeId": None, "iconUrl": None})
            if not uids: return []
            u_str = ",".join(map(str, uids))
            games = GlobalSession.get(f"https://games.roblox.com/v1/games?universeIds={u_str}").json().get("data", [])
            icons = GlobalSession.get(f"https://thumbnails.roblox.com/v1/games/icons?universeIds={u_str}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false").json().get("data", [])
            u_map = {str(g["id"]): str(g["rootPlaceId"]) for g in games}
            i_map = {str(i["targetId"]): i["imageUrl"] for i in icons}
            final = []
            for res in results:
                uid = str(res["universeId"])
                if uid in u_map: res["placeId"] = u_map[uid]; res["iconUrl"] = i_map.get(uid); final.append(res)
            return final
        except: return []

    def get_servers(self, place_id, cursor=None, sort_order="Desc"):
        try:
            url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?sortOrder={sort_order}&limit=25"
            if cursor: url += f"&cursor={cursor}"
            r = GlobalSession.get(url); data = r.json()
            if r.status_code != 200 or not data.get("data"):
                try:
                    r2 = GlobalSession.get(f"https://games.roblox.com/v1/games?universeIds={place_id}")
                    pid = r2.json()["data"][0]["rootPlaceId"]
                    url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?sortOrder={sort_order}&limit=25"
                    if cursor: url += f"&cursor={cursor}"
                    r = GlobalSession.get(url); data = r.json()
                except: pass
            return data.get("data", []), data.get("nextPageCursor")
        except: return [], None

    def stats(self, cookie, ua, proxy=None):
        sess = self._create_session(proxy)
        if ua: sess.headers.update({"User-Agent": ua})
        sess.cookies[".ROBLOSECURITY"] = cookie
        try:
            r = sess.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
            if r.status_code == 401: return {"status": "Expired"}
            u = r.json()
            curr = sess.get(f"https://economy.roblox.com/v1/users/{u['id']}/currency", timeout=10).json()
            return {"userid": str(u["id"]), "display_name": u["displayName"], "robux": str(curr.get("robux", 0)), "status": "OK"}
        except: return {"status": "Invalid"}

    def get_id(self, user):
        try: return GlobalSession.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [user], "excludeBannedUsers": True}).json()["data"][0]["id"]
        except: return None
    def get_presence(self, uid):
        try: return GlobalSession.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [uid]}).json()["userPresences"][0]
        except: return None


class Browser:
    def __init__(self, log_func): self.log = log_func
    def open(self, u, p, cookie, target_url, cb, mode="NORMAL", proxy=None):
        self.log(f"Opening Edge Browser ({mode})...")
        driver = None
        try:
            o = EdgeOptions(); o.use_chromium = True; o.binary_location = EDGE_BINARY_PATH
            o.add_argument("--no-sandbox"); o.add_argument("--disable-gpu")
            o.add_argument("--disable-dev-shm-usage"); o.add_argument("--disable-blink-features=AutomationControlled")
            o.add_argument("--disable-extensions"); o.add_experimental_option("excludeSwitches", ["enable-automation"])
            o.add_experimental_option("useAutomationExtension", False); o.page_load_strategy = "normal"
            if proxy: o.add_argument(f"--proxy-server={proxy}")
            if os.path.exists(DRIVER_PATH): driver = webdriver.Edge(service=Service(executable_path=DRIVER_PATH), options=o)
            else: self.log("Driver not found in folder. Trying system path..."); driver = webdriver.Edge(options=o)
            try: 
                w,h = driver.execute_script("return [window.screen.availWidth, window.screen.availHeight]")
                driver.set_window_rect(x=(w-1000)//2, y=(h-800)//2, width=1000, height=800)
            except: pass
            
            if cookie:
                try: driver.get("https://www.roblox.com/404"); driver.delete_all_cookies(); driver.add_cookie({"name": ".ROBLOSECURITY", "value": cookie, "domain": ".roblox.com", "path": "/"}); driver.get(target_url)
                except Exception as e: self.log(f"Injection Warning: {e}")
            else:
                driver.get(target_url)
                if u and p and "login" in target_url:
                    self.log(f"Attempting auto-login for {u}...")
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-username")))
                        driver.find_element(By.ID, "login-username").send_keys(u); time.sleep(0.5)
                        driver.find_element(By.ID, "login-password").send_keys(p); time.sleep(0.5)
                        driver.find_element(By.ID, "login-button").click()
                    except Exception as e: self.log(f"Auto-login failed: {e}")
            if mode == "LOGIN_ONLY":
                start = time.time()
                while time.time() - start < 300:
                    try:
                        if not driver.window_handles: break
                        if "home" in driver.current_url:
                            c = driver.get_cookies()
                            sec = next((x["value"] for x in c if x["name"] == ".ROBLOSECURITY"), None)
                            if sec: cb(u, p, sec, driver.execute_script("return navigator.userAgent;")); break
                    except: break
                    time.sleep(1)
                driver.quit(); return
            while driver.window_handles: time.sleep(1)
        except Exception as e:
            self.log(f"Browser Error: {e}"); 
            if driver: 
                try: driver.quit()
                except: pass


# ==========================================
#                UI CLASSES
# ==========================================

class IOSCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=kwargs.pop("fg_color", THEME["card_bg"]),
            corner_radius=kwargs.pop("corner_radius", 18),
            border_width=kwargs.pop("border_width", 1),
            border_color=kwargs.pop("border_color", THEME["border"]),
            **kwargs
        )

class ModernButton(ctk.CTkButton):
    def __init__(self, master, type="primary", **kwargs):
        colors = {
            "primary": (THEME["accent"], THEME["accent_hover"]),
            "accent": (THEME["accent"], THEME["accent_hover"]),
            "success": (THEME["success"], THEME["success"]),
            "danger": (THEME["danger"], THEME["danger"]),
            "warning": (THEME["warning"], THEME["warning"]),
            "subtle": (THEME["card_hover"], THEME["border"]),
        }
        fg, hover = colors.get(type, colors["primary"])
        
        # --- FIXED: Pop ALL potential duplicate arguments ---
        h = kwargs.pop("height", 28) # Default height lowered for compact mode
        c_rad = kwargs.pop("corner_radius", 14)
        bg_col = kwargs.pop("fg_color", fg)
        hov_col = kwargs.pop("hover_color", hover)
        txt_col = kwargs.pop("text_color", "#FFFFFF" if type != "subtle" else THEME["text_main"])
        fnt = kwargs.pop("font", FontManager.ui(12, "bold"))
        
        super().__init__(
            master,
            corner_radius=c_rad,
            fg_color=bg_col,
            hover_color=hov_col,
            text_color=txt_col,
            font=fnt,
            height=h,
            **kwargs,
        )


class CenterDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.title(title)
        self.res = None
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        IOSCard(self).pack(fill="both", expand=True, padx=12, pady=12)
        container = self.winfo_children()[-1]
        ctk.CTkLabel(container, text=prompt, text_color=THEME["text_main"], font=FontManager.ui(13, "bold")).pack(pady=(14, 8), padx=18)
        self.entry = ctk.CTkEntry(container, width=260, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.entry.pack(pady=5, padx=18)
        ModernButton(container, text="OK", type="primary", command=self.ok).pack(pady=(12, 14))
        Utils.center_window(self, 340, 180)
    def ok(self):
        self.res = self.entry.get()
        self.destroy()
    def ask(self):
        self.wait_window()
        return self.res


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Settings")
        self.callback = callback
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        
        wrap = IOSCard(self)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)
        
        ctk.CTkLabel(wrap, text="Appearance", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        self.mode = ctk.StringVar(value=CONFIG.get("theme_mode", "Dark"))
        self.mode_menu = ctk.CTkOptionMenu(wrap, variable=self.mode, values=["System", "Light", "Dark"], fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.mode_menu.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(wrap, text="Accent Color", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.accent = ctk.StringVar(value=CONFIG.get("accent_color", "Blue"))
        self.accent_menu = ctk.CTkOptionMenu(wrap, variable=self.accent, values=["Blue", "Green", "Orange", "Purple", "Pink"], fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.accent_menu.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(wrap, text="Discord Webhook URL", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.webhook_entry = ctk.CTkEntry(wrap, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.webhook_entry.insert(0, CONFIG.get("discord_webhook", ""))
        self.webhook_entry.pack(fill="x", padx=16, pady=(0, 12))

        self.fps_var = ctk.BooleanVar(value=CONFIG.get("fps_unlock", False))
        self.potato_var = ctk.BooleanVar(value=CONFIG.get("potato_mode", False))
        self.fish_var = ctk.BooleanVar(value=CONFIG.get("use_fishstrap", True))

        toggles = ctk.CTkFrame(wrap, fg_color="transparent")
        toggles.pack(fill="x", padx=16, pady=(2, 12))

        self.fps_sw = ctk.CTkSwitch(toggles, text="FPS Unlocker", variable=self.fps_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.fps_sw.pack(anchor="w", pady=6)
        self.potato_sw = ctk.CTkSwitch(toggles, text="Potato Mode (Low GFX)", variable=self.potato_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.potato_sw.pack(anchor="w", pady=6)
        self.fish_sw = ctk.CTkSwitch(toggles, text="Use Fishstrap (Multi-Instance)", variable=self.fish_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.fish_sw.pack(anchor="w", pady=6)
        
        # Test Webhook Button
        ModernButton(wrap, text="Test Webhook", type="warning", command=self.test_webhook).pack(fill="x", padx=16, pady=(0, 6))

        ModernButton(wrap, text="Save & Apply", type="primary", command=self.save).pack(fill="x", padx=16, pady=(6, 14))
        Utils.center_window(self, 380, 600)
    
    def test_webhook(self):
        url = self.webhook_entry.get().strip()
        res = DiscordNotifier.send_test(url)
        messagebox.showinfo("Webhook Test", res)

    def save(self):
        CONFIG["theme_mode"] = self.mode.get()
        CONFIG["accent_color"] = self.accent.get()
        CONFIG["discord_webhook"] = self.webhook_entry.get().strip()
        if self.fps_var.get() != CONFIG.get("fps_unlock", False):
            CONFIG["fps_unlock"] = self.fps_var.get()
            FPSUnlocker.toggle_unlock(CONFIG["fps_unlock"])
        CONFIG["potato_mode"] = self.potato_var.get()
        PotatoMode.apply(CONFIG["potato_mode"])
        CONFIG["use_fishstrap"] = self.fish_var.get()
        ConfigManager.save()
        ThemeManager.apply()
        self.callback()
        self.destroy()


class AccountEditor(ctk.CTkToplevel):
    def __init__(self, parent, acc, callback, api, app_ref):
        super().__init__(parent)
        self.title(f"Manage: {acc['username']}")
        self.acc = acc
        self.cb = callback
        self.api = api
        self.app = app_ref
        self.grab_set()
        self.configure(fg_color=THEME["bg"])

        self.tabs = ctk.CTkTabview(self, text_color=THEME["text_main"], segmented_button_fg_color=THEME["card_bg"], segmented_button_selected_color=THEME["accent"], segmented_button_selected_hover_color=THEME["accent_hover"], segmented_button_unselected_color=THEME["card_bg"], segmented_button_unselected_hover_color=THEME["card_hover"])
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        # Tab 1: Profile
        t_prof = self.tabs.add("Profile")
        ctk.CTkLabel(t_prof, text="Alias / Display Name", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.name_entry = ctk.CTkEntry(t_prof, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.name_entry.insert(0, acc.get("username", ""))
        self.name_entry.pack(pady=6)

        ctk.CTkLabel(t_prof, text="Group / Category", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.grp_entry = ctk.CTkEntry(t_prof, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.grp_entry.insert(0, acc.get("group", "Ungrouped"))
        self.grp_entry.pack(pady=6)

        ctk.CTkLabel(t_prof, text="Notes", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.notes_box = ctk.CTkTextbox(t_prof, width=320, height=90, fg_color=THEME["input_bg"], text_color=THEME["text_main"], corner_radius=12, border_width=1, border_color=THEME["border"], font=FontManager.ui(12))
        self.notes_box.insert("0.0", acc.get("notes", ""))
        self.notes_box.pack(pady=6)

        # Tab 2: Games
        t_game = self.tabs.add("Games & Servers")
        ctk.CTkLabel(t_game, text="Default Place ID", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.place_entry = ctk.CTkEntry(t_game, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        pid = acc.get("default_place_id", "")
        if not pid:
            pid = acc.get("game_id", DEFAULT_PLACE_ID)
        self.place_entry.insert(0, str(pid))
        self.place_entry.pack(pady=6)

        btn_box = ctk.CTkFrame(t_game, fg_color="transparent")
        btn_box.pack(pady=14)
        ModernButton(btn_box, text="Open Game Browser", width=160, type="primary", command=self.open_game_browser).pack(side="left", padx=6)
        ModernButton(btn_box, text="Open Server Browser", width=170, type="warning", command=self.open_server_browser).pack(side="left", padx=6)
        ctk.CTkLabel(t_game, text="Tip: Use Game Browser to set ID automatically.", font=FontManager.ui(11), text_color=THEME["text_sub"]).pack(pady=10)

        # Tab 3: Data
        t_data = self.tabs.add("Data")
        ctk.CTkLabel(t_data, text="User ID", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        uid_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        uid_entry.insert(0, str(acc.get("userid", "Unknown")))
        uid_entry.configure(state="readonly")
        uid_entry.pack(pady=6)
        
        ctk.CTkLabel(t_data, text=".ROBLOSECURITY Cookie", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.cookie_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.cookie_entry.insert(0, acc.get("cookie", ""))
        self.cookie_entry.pack(pady=6)

        # Proxy Editor
        ctk.CTkLabel(t_data, text="Proxy (http://user:pass@ip:port)", text_color=THEME["text_sub"], font=FontManager.ui(12, "bold")).pack(pady=(12, 2))
        self.proxy_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.proxy_entry.insert(0, acc.get("proxy", ""))
        self.proxy_entry.pack(pady=6)

        ModernButton(self, text="Save Changes", type="success", command=self.save).pack(fill="x", padx=18, pady=(0, 16))
        Utils.center_window(self, 440, 600)

    def open_game_browser(self):
        def cb(pid, target_ignored, name):
            if pid:
                self.place_entry.delete(0, "end")
                self.place_entry.insert(0, str(pid))
                self.lift()
        GameSelector(self, cb, [], self.app, is_sub_window=True)

    def open_server_browser(self):
        pid = self.place_entry.get().strip()
        if not pid:
            messagebox.showerror("Error", "No Place ID set.")
            return
        ServerBrowser(self.app, pid, self.acc, self.api, self.app.launch)
        self.destroy()

    def save(self):
        pid = self.place_entry.get().strip()
        old_pid = self.acc.get("default_place_id", "")
        
        self.acc.update({
            "username": self.name_entry.get(),
            "group": self.grp_entry.get(),
            "notes": self.notes_box.get("0.0", "end").strip(),
            "default_place_id": pid,
            "proxy": self.proxy_entry.get().strip()
        })
        
        c_val = self.cookie_entry.get().strip()
        if c_val and c_val != self.acc.get("cookie", ""):
             self.acc["cookie"] = c_val
        
        if pid != old_pid and pid:
            def _log_change():
                game_name = self.api.get_game_name(pid)
                self.app.safe_log(f"Changed Game for [{self.acc['username']}] to [{game_name}]")
            threading.Thread(target=_log_change, daemon=True).start()

        DataManager.save(self.app.data)
        self.cb()
        self.destroy()


class ServerBrowser(ctk.CTkToplevel):
    def __init__(self, parent, place_id, account_data, api_ref, launcher_callback):
        super().__init__(parent)
        self.title(f"Server Browser")
        self.api = api_ref
        self.place_id = place_id
        self.account = account_data
        self.launcher = launcher_callback
        self.cursor_stack = []
        self.current_cursor = None
        self.sort_order = ctk.StringVar(value="Desc")
        self.filter_private = ctk.BooleanVar(value=True)
        self.attributes("-topmost", True)
        self.focus_force()
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        
        self.top_f = IOSCard(self)
        self.top_f.pack(fill="x", padx=12, pady=12)
        
        self.title_lbl = ctk.CTkLabel(self.top_f, text=f"Loading...", font=("Arial", 12, "bold"), text_color=THEME["text_main"])
        self.title_lbl.pack(side="left", padx=10)
        
        threading.Thread(target=self.set_title, daemon=True).start()

        ModernButton(self.top_f, text="↻", width=42, type="primary", command=self.reload_fresh).pack(side="right", padx=6, pady=8)
        self.sort_menu = ctk.CTkOptionMenu(self.top_f, variable=self.sort_order, values=["Desc", "Asc"], command=self.reload_fresh, width=90, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.sort_menu.pack(side="right", padx=6)
        self.chk_private = ctk.CTkCheckBox(self.top_f, text="Hide VIP", variable=self.filter_private, command=self.reload_fresh, width=90, font=FontManager.ui(11), text_color=THEME["text_main"], hover_color=THEME["accent"])
        self.chk_private.pack(side="right", padx=10)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)
        self.status_lbl = ctk.CTkLabel(self.scroll, text="Loading...", font=FontManager.ui(12), text_color=THEME["text_sub"])
        self.status_lbl.pack(pady=20)
        
        self.ctrl_f = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_f.pack(fill="x", padx=12, pady=12)
        self.btn_prev = ModernButton(self.ctrl_f, text="< Prev", width=90, type="subtle", command=self.prev_page)
        self.btn_prev.pack(side="left")
        self.btn_next = ModernButton(self.ctrl_f, text="Next >", width=90, type="subtle", command=self.next_page)
        self.btn_next.pack(side="right")
        
        Utils.center_window(self, 600, 600)
        self.reload_fresh()

    def set_title(self):
        name = self.api.get_game_name(self.place_id)
        if self.winfo_exists():
            self.title_lbl.configure(text=name)

    def reload_fresh(self, _=None):
        self.cursor_stack = []
        self.current_cursor = None
        self.btn_prev.configure(state="disabled")
        threading.Thread(target=self.load_servers, daemon=True).start()

    def load_servers(self, cursor=None):
        self.after(0, lambda: self.status_lbl.configure(text="Fetching servers..."))
        try:
            servers, next_cursor = self.api.get_servers(self.place_id, cursor, self.sort_order.get())
            self.after(0, lambda: self.display_servers(servers, next_cursor))
        except Exception as e:
            self.after(0, lambda: self.status_lbl.configure(text="Error loading servers"))

    def display_servers(self, servers, next_cursor):
        if not self.winfo_exists(): return
        for w in self.scroll.winfo_children(): w.destroy()
        if not servers:
            ctk.CTkLabel(self.scroll, text="No servers found.", text_color=THEME["text_sub"], font=FontManager.ui(12)).pack(pady=20)
            self.btn_next.configure(state="disabled")
            return
        
        count = 0
        for s in servers:
            if self.filter_private.get() and s.get("vipServerId"): continue
            job_id = s.get("id")
            if not job_id: continue

            f = IOSCard(self.scroll, corner_radius=16)
            f.pack(fill="x", pady=6)
            info = f"Players: {s.get('playing', 0)}/{s.get('maxPlayers', 0)} | Ping: {s.get('ping', '?')}ms | {int(s.get('fps', 0))} FPS"
            ctk.CTkLabel(f, text=info, font=FontManager.mono(12, "bold"), text_color=THEME["text_main"]).pack(side="left", padx=12, pady=10)
            short_id = job_id[:8] + "..." if len(job_id) > 8 else job_id
            ctk.CTkLabel(f, text=f"ID: {short_id}", font=FontManager.mono(10), text_color=THEME["text_sub"]).pack(side="left", padx=6)
            ModernButton(f, text="Join", width=70, type="success", command=lambda j=job_id: self.join_server(j)).pack(side="right", padx=8, pady=8)
            ModernButton(f, text="Copy", width=62, type="subtle", command=lambda j=job_id: self.copy_id(j)).pack(side="right", padx=6, pady=8)
            count += 1

        if count == 0:
            ctk.CTkLabel(self.scroll, text="All servers on this page filtered.", text_color=THEME["text_sub"]).pack(pady=10)
        self.current_cursor = next_cursor
        self.btn_next.configure(state="normal" if next_cursor else "disabled")
        self.btn_prev.configure(state="normal" if self.cursor_stack else "disabled")

    def copy_id(self, job_id):
        self.clipboard_clear()
        self.clipboard_append(job_id)
        self.update() 

    def next_page(self):
        if self.current_cursor:
            self.cursor_stack.append(self.current_cursor)
            threading.Thread(target=self.load_servers, args=(self.current_cursor,), daemon=True).start()

    def prev_page(self):
        if self.cursor_stack:
            self.reload_fresh()

    def join_server(self, job_id):
        if self.account: 
            self.launcher(self.account, job_id)
            self.destroy()


class GameSelector(ctk.CTkToplevel):
    def __init__(self, parent, callback, accounts, app_ref, pre_select_user=None, is_sub_window=False):
        super().__init__(parent)
        self.title("Select Game")
        self.callback = callback
        self.api = RobloxAPI(lambda x: None)
        self.accounts = accounts
        self.app = app_ref
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure(fg_color=THEME["bg"])
        
        self.attributes("-topmost", True)
        self.focus_force()
        if is_sub_window:
            self.grab_set()
        
        top_frame = IOSCard(self)
        top_frame.pack(fill="x", padx=12, pady=12)
        
        if self.accounts:
            ctk.CTkLabel(top_frame, text="Apply to Account:", text_color=THEME["text_main"], font=FontManager.ui(12, "bold")).pack(side="left", padx=10)
            self.acc_var = ctk.StringVar(value="Global Tool Only")
            acc_names = ["Global Tool Only"] + ["All Accounts"] + [a["username"] for a in self.accounts]
            self.acc_menu = ctk.CTkOptionMenu(top_frame, values=acc_names, variable=self.acc_var, width=170, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
            self.acc_menu.pack(side="left", padx=8)
            if pre_select_user:
                self.acc_var.set(pre_select_user)
        else:
             self.acc_var = ctk.StringVar(value="Global Tool Only")
        
        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Search games...", width=160, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)
        ModernButton(top_frame, text="Search", width=80, type="primary", command=self.do_search).pack(side="right", padx=10)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)
        Utils.center_window(self, 720, 620)
        self.do_search("Simulator")

    def do_search(self, query=None):
        q = query if query else self.search_entry.get()
        if not q: return
        for w in self.scroll.winfo_children(): w.destroy()
        threading.Thread(target=self._search_thread, args=(q,), daemon=True).start()

    def _search_thread(self, query): 
        games = self.api.search_games_optimized(query)
        self.after(0, lambda: self._display_results(games))

    def _display_results(self, games):
        if not self.winfo_exists(): return
        row = 0; col = 0
        for g in games:
            f = IOSCard(self.scroll, corner_radius=18)
            f.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            img_lbl = ctk.CTkLabel(f, text="Loading...", width=100, height=100, text_color=THEME["text_sub"])
            img_lbl.pack(pady=8)
            if g.get("iconUrl"):
                ImageHandler.fetch_image_async(g["iconUrl"], f"{DIRS['cache']}/univ_{g['universeId']}.png", lambda img, lbl=img_lbl: lbl.configure(image=img, text=""), size=(128, 128))
            ctk.CTkLabel(f, text=g["name"][:22], font=FontManager.ui(12, "bold"), text_color=THEME["text_main"]).pack(pady=(0, 8))
            btn_frame = ctk.CTkFrame(f, fg_color="transparent"); btn_frame.pack(pady=(0, 12))
            
            ModernButton(btn_frame, text="Select", width=80, type="success", command=lambda pid=g['placeId'], name=g['name']: self.select_game(pid, name)).pack(side="left", padx=5)
            ModernButton(btn_frame, text="Servers", width=80, type="warning", command=lambda pid=(g['placeId'] or g['universeId']): self.open_servers(pid)).pack(side="left", padx=5)
            col += 1
            if col > 2: col = 0; row += 1

    def select_game(self, pid, name):
        target = self.acc_var.get()
        self.callback(pid, target, name)
        self.on_close()

    def open_servers(self, pid):
        target_user = self.acc_var.get()
        acc = next((a for a in self.accounts if a["username"] == target_user), None)
        if target_user in ("Global Tool Only", "All Accounts"):
            acc = self.app.get_acc()
        if acc: 
            sb = ServerBrowser(self.app, pid, acc, self.api, self.app.launch)
            self.app.windows.append(sb)
        else: 
            messagebox.showerror("Error", "Select a valid account.")

    def on_close(self): 
        Utils.clean_game_cache()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        FontManager.init(self)
        Utils.ensure_dirs()
        ConfigManager.load()
        ThemeManager.apply()

        self.title(f"{APP_NAME}")
        self.geometry("1150x780")
        self.configure(fg_color=THEME["bg"])
        
        self.api = RobloxAPI(self.safe_log)
        self.browser = Browser(self.safe_log)
        self.data = DataManager.load()
        self.windows = []
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=0,
            fg_color=THEME["sidebar"],
            border_width=1,
            border_color=THEME["separator"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(26, 10))

        ctk.CTkLabel(
            header,
            text="cx.manager",
            font=FontManager.ui(26, "bold"),
            text_color=THEME["text_main"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=VERSION,
            font=FontManager.ui(11),
            text_color=THEME["text_sub"],
        ).pack(anchor="w", pady=(2, 0))
        
        self.side_btn(self.sidebar, "Import Accounts", self.import_data)
        self.side_btn(self.sidebar, "Add Account", self.manual)
        self.side_btn(self.sidebar, "Refresh All", self.refresh)
        
        # Kill Switch
        def kill_all():
            if messagebox.askyesno("Panic", "Force close ALL Roblox instances?"):
                subprocess.call("taskkill /F /IM RobloxPlayerBeta.exe", shell=True)
                self.safe_log("[ALERT] Killed all Roblox processes.")
        self.side_btn(self.sidebar, "Kill All Roblox", kill_all, color="danger")
        
        self.side_btn(self.sidebar, "Check Health", self.check_health)
        self.side_btn(self.sidebar, "Settings", self.open_settings)
        
        self.status_bar = ctk.CTkLabel(
            self.sidebar, text="Ready", text_color=THEME["text_sub"], anchor="w", font=FontManager.ui(11)
        )
        self.status_bar.pack(side="bottom", fill="x", padx=16, pady=(6, 6))

        self.console = ctk.CTkTextbox(
            self.sidebar,
            height=160,
            corner_radius=16,
            fg_color=THEME["card_bg"],
            text_color=THEME["text_sub"],
            border_width=1,
            border_color=THEME["border"],
            font=FontManager.mono(11),
        )
        self.console.pack(fill="x", padx=16, pady=(0, 16), side="bottom")

        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.tabs = ctk.CTkTabview(
            self.main_area,
            fg_color="transparent",
            segmented_button_fg_color=THEME["card_bg"],
            segmented_button_selected_color=THEME["accent"],
            segmented_button_selected_hover_color=THEME["accent_hover"],
            segmented_button_unselected_color=THEME["card_bg"],
            segmented_button_unselected_hover_color=THEME["card_hover"],
            text_color=THEME["text_main"],
        )
        self.tabs.pack(fill="both", expand=True)
        self.tabs.add("Accounts")
        self.tabs.add("Game Tools")
        
        self.scroll = ctk.CTkScrollableFrame(
            self.tabs.tab("Accounts"),
            fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["accent"],
        )
        self.scroll.pack(fill="both", expand=True)
        self.scroll._parent_canvas.bind_all(
            "<MouseWheel>", lambda e: self.scroll._parent_canvas.yview_scroll(int(-1 * (e.delta / 120) * 5), "units")
        )
        
        self.setup_tools()
        Utils.center_window(self, 1150, 780)
        self.refresh_ui()

    def side_btn(self, parent, text, cmd, color="primary"):
        btn = ModernButton(
            parent,
            text=text,
            command=cmd,
            width=220,
            height=42,
            corner_radius=14,
            fg_color=THEME["card_bg"] if color == "primary" else THEME[color],
            hover_color=THEME["card_hover"] if color == "primary" else THEME["danger"],
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_main"],
            font=FontManager.ui(12, "bold"),
            type=color
        )
        btn.pack(pady=7, padx=16)

    def safe_log(self, m): 
        msg = Utils.timestamp_msg(m)
        self.after(0, lambda: self.console.insert("end", msg + "\n") or self.console.see("end"))
        self.after(0, lambda: self.status_bar.configure(text=m[:30] + "..."))

    def check_health(self):
        self.safe_log("[INFO] Checking cookie health...")
        def check_task(acc):
            if "cookie" in acc:
                res = self.api.stats(acc['cookie'], acc.get('user_agent'), acc.get('proxy'))
                acc["health_status"] = "good" if res.get("status") == "OK" else "bad"
        def run_check():
            with ThreadPoolExecutor(max_workers=15) as executor:
                executor.map(check_task, self.data)
            self.after(0, self.refresh_ui)
            self.safe_log("[SUCCESS] Health Check Complete.")
        threading.Thread(target=run_check, daemon=True).start()

    def refresh_ui(self):
        # Ensure account fields exist
        for a in self.data:
            a.setdefault("locked", False)
            a.setdefault("last_job_id", None)
            
        for w in self.scroll.winfo_children(): w.destroy()
        for acc in self.data:
            grp = acc.get('group', 'Ungrouped')
            if grp == 'Ungrouped': grp = "Verified" if "cookie" in acc else "Non-Verified"
            acc['_display_group'] = grp
        self.data.sort(key=lambda x: (x['_display_group'], 0 if "cookie" in x else 1, x['username'].lower()))
        
        current_group = None
        for acc in self.data:
            grp = acc['_display_group']
            if grp != current_group:
                current_group = grp
                gf = ctk.CTkFrame(self.scroll, height=30, fg_color="transparent")
                gf.pack(fill="x", pady=(15, 5))
                ctk.CTkLabel(gf, text=f"📂 {grp}", font=FontManager.ui(14, "bold"), text_color=THEME["text_sub"]).pack(side="left", padx=6)
            self.card(acc)
            
        acc_names = [a['username'] for a in self.data if "cookie" in a]
        if not acc_names: acc_names = ["No Verified Accounts"]
        if hasattr(self, 'job_acc_menu'):
            self.job_acc_menu.configure(values=acc_names)
            if self.job_acc_var.get() not in acc_names: self.job_acc_var.set(acc_names[0])

    def card(self, acc):
        # Determine status color
        is_verified = "cookie" in acc
        status_text = "Not Verified"
        stat_col = THEME["gray"]
        
        if is_verified:
            status_text = acc.get('custom_status', 'Idle')
            if status_text == 'Idle': 
                 diff = time.time() - acc.get('last_used', 0)
                 if diff < 300: status_text = "Online"; stat_col = THEME["success"]
                 elif diff < 3600: status_text = "Away"; stat_col = THEME["warning"]
                 else: stat_col = THEME["text_sub"]
            else: stat_col = THEME["text_sub"]

        # Card Container (Compact Padding)
        c = IOSCard(self.scroll, corner_radius=16, border_width=0, fg_color=THEME["card_bg"]) 
        c.pack(fill="x", pady=2, padx=6)
        
        # Left Strip (The "Border" visual replacement)
        strip_col = stat_col if is_verified else THEME["border"]
        strip = ctk.CTkFrame(c, width=4, fg_color=strip_col, corner_radius=0)
        strip.pack(side="left", fill="y")
        
        # Main Content Wrapper (Reduced Pady to 5 to fit inside better)
        content = ctk.CTkFrame(c, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=8, pady=2)

        # 1. Avatar (Left side of content)
        img_container = ctk.CTkFrame(content, fg_color="transparent")
        img_container.pack(side="left")
        
        img_lbl = ctk.CTkLabel(img_container, text="", width=45)
        img_lbl.pack()
        
        if ImageHandler.get_cached_avatar(acc.get("userid")): 
            img_lbl.configure(image=ImageHandler.get_cached_avatar(acc.get("userid")))
        else: 
            ImageHandler.fetch_avatar_async(acc.get("userid"), f"{DIRS['cache']}/{acc.get('userid')}.png", lambda img, l=img_lbl: l.configure(image=img))

        # 2. Info Column (Username, Status, R$)
        info_col = ctk.CTkFrame(content, fg_color="transparent")
        info_col.pack(side="left", padx=(10, 0), anchor="center")

        # Row A: Dot + Username (Tight fit: padx=4)
        name_row = ctk.CTkFrame(info_col, fg_color="transparent")
        name_row.pack(anchor="w")
        
        ctk.CTkLabel(name_row, text="●", text_color=stat_col, font=("Arial", 12)).pack(side="left")
        ctk.CTkLabel(name_row, text=acc['username'], font=FontManager.ui(14, "bold"), text_color=THEME["text_main"]).pack(side="left", padx=(4, 0))

        # Row B: Meta Data (R$ | Game Name | Status)
        meta_row = ctk.CTkFrame(info_col, fg_color="transparent")
        meta_row.pack(anchor="w", pady=(0, 0))
        
        if is_verified:
            ctk.CTkLabel(meta_row, text=f"R$ {acc.get('robux','0')}", font=FontManager.ui(11, "bold"), text_color=THEME["text_sub"]).pack(side="left")
            ctk.CTkLabel(meta_row, text=" • ", font=FontManager.ui(11), text_color=THEME["border"]).pack(side="left")
            
            game_name = acc.get('last_played_name','Unknown')
            place_id = acc.get('game_id')
            
            # Shorten game name if too long
            display_game = (game_name[:20] + '..') if len(game_name) > 20 else game_name
            
            if place_id and game_name != "Unknown":
                g_btn = ctk.CTkButton(meta_row, text=display_game, width=20, height=18, fg_color="transparent", text_color=THEME["link"], font=FontManager.ui(11), hover=False, command=lambda p=place_id: webbrowser.open(f"https://www.roblox.com/games/{p}"))
                g_btn.pack(side="left")
            else:
                ctk.CTkLabel(meta_row, text=display_game, font=FontManager.ui(11), text_color=THEME["text_sub"]).pack(side="left")

            # --- STATUS RE-ADDED HERE ---
            ctk.CTkLabel(meta_row, text=" • ", font=FontManager.ui(11), text_color=THEME["border"]).pack(side="left")
            ctk.CTkLabel(meta_row, text=status_text, font=FontManager.ui(11), text_color=stat_col).pack(side="left")

        else:
            ctk.CTkLabel(meta_row, text="Not verified", font=FontManager.ui(11), text_color=THEME["text_sub"]).pack(side="left")

        # 3. Actions Group (Right Side)
        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.pack(side="right")
        
        if is_verified:
            h = Utils.compute_account_health(acc)
            ctk.CTkLabel(actions, text=f"❤ {h}%", font=FontManager.ui(11, "bold"), text_color=THEME["success"] if h>70 else THEME["warning"]).pack(side="left", padx=(0, 8))

            # Buttons (Reduced height to 28)
            ModernButton(actions, text="Launch", width=70, height=28, type="primary", command=lambda: self.launch(acc)).pack(side="left", padx=3)
            ModernButton(actions, text="Games", width=60, height=28, type="subtle", command=lambda: self.open_game_selector_for(acc)).pack(side="left", padx=3)
            ModernButton(actions, text="Servers", width=60, height=28, type="subtle", command=lambda: self.open_server_browser_for(acc)).pack(side="left", padx=3)
            
            # Icon Buttons for Job ID
            ModernButton(actions, text="🆔", width=30, height=28, type="subtle", command=lambda: self.join_job_dialog(acc)).pack(side="left", padx=3)

        else:
            ModernButton(actions, text="Login", width=70, height=28, type="warning", command=lambda: self.login(acc)).pack(side="left", padx=4)
        
        # Icon Buttons for Settings/Delete
        ModernButton(actions, text="⚙", width=30, height=28, type="subtle", command=lambda: self.show_menu(acc)).pack(side="left", padx=3)
        ModernButton(actions, text="🗑", width=30, height=28, type="danger", command=lambda: self.delete(acc)).pack(side="left", padx=3)

    def show_menu(self, acc):
        global parent
        parent = self
        AccountEditor(self, acc, lambda: self.refresh_ui(), self.api, self)
        
    def open_game_selector_for(self, acc):
        def cb(pid, target_acc, game_name):
            if pid:
                acc['default_place_id'] = str(pid)
                acc['last_played_name'] = game_name
                DataManager.save(self.data)
                self.safe_log(f"Changed Game for [{acc['username']}] to [{game_name}]")
                self.refresh_ui()
        GameSelector(self, cb, [], self, is_sub_window=True)

    def open_server_browser_for(self, acc):
        pid = acc.get('default_place_id') or acc.get('game_id')
        if not pid:
            messagebox.showerror("Error", "No game set for this account.")
            return
        ServerBrowser(self, pid, acc, self.api, self.launch)
        
    def join_job_dialog(self, acc):
        # Quick dialog for Job ID
        dialog = CenterDialog(self, "Join Job ID", "Paste Job ID or Deep Link:")
        res = dialog.ask()
        if res:
            # Strip link if pasted full link
            clean_id = res
            if "gameInstanceId=" in res:
                try:
                    clean_id = res.split("gameInstanceId=")[1].split("&")[0]
                except:
                    pass
            self.launch(acc, clean_id)

    def track_account(self, acc):
        # Kept for backward compat but removed from UI button
        pass

    def launch(self, acc, job=None):
        if acc.get("locked"):
            self.safe_log(f"[WARN] {acc['username']} is locked.")
            return

        self.safe_log(f"[INFO] Attempting to launch {acc['username']}...")
        acc['last_used'] = time.time()
        pid = job if job else acc.get('default_place_id', DEFAULT_PLACE_ID)
        
        # If joining via Job ID, we might not know the place ID from the job string alone easily
        # So we default to their saved place ID if job is just an ID string
        if job and "placeId=" in job:
             # Deep link parsing
             try:
                 pid = job.split("placeId=")[1].split("&")[0]
                 job = job.split("gameInstanceId=")[1].split("&")[0]
             except: pass
        
        if job:
            acc["last_job_id"] = job 
            game_name = acc.get('last_played_name', 'Unknown Game')
        else:
             # Fetch Name for better UI
             game_name = self.api.get_game_name(pid)
             acc['last_played_name'] = game_name
             acc['game_id'] = pid
             
        DataManager.save(self.data)
        self.refresh_ui()
        DiscordNotifier.send_launch_log(self.api, acc['username'], game_name, pid, job, acc.get('userid'), manual_track=False, robux=acc.get('robux','0'))
        threading.Thread(target=self._launch_t, args=(acc, pid, job), daemon=True).start()
        
    def _launch_t(self, acc, pid, job):
        res = self.api.launch(acc, pid, acc.get('user_agent'), job, acc.get('proxy'))
        if res is True or "Fishstrap" in str(res) or "Bloxstrap" in str(res): 
            self.safe_log(f"[SUCCESS] Launched {acc['username']}")
        else: 
            self.safe_log(f"[ERROR] Launch Error: {res}")
        
    def login(self, acc): 
        threading.Thread(target=self.browser.open, args=(acc['username'], Security.decrypt(acc.get('password')), acc.get('cookie'), "https://www.roblox.com/home", self.update_acc, "LOGIN_ONLY", acc.get('proxy')), daemon=True).start()
        
    def manual(self): 
        threading.Thread(target=self.browser.open, args=("", "", None, "https://www.roblox.com/login", self.update_acc, "LOGIN_ONLY"), daemon=True).start()
        
    def update_acc(self, u, p, c, ua):
        stats = self.api.stats(c, ua)
        name = stats.get('display_name') or u or "New Account"
        found = False
        for a in self.data:
            if a['username'] == u: 
                a.update({"cookie":c, "password":Security.encrypt(p), "user_agent":ua})
                a.update(stats)
                found=True
        if not found: 
            self.data.append({"username":name, "password":Security.encrypt(p), "cookie":c, "user_agent":ua, **stats})
        DataManager.save(self.data)
        self.after(0, self.refresh_ui)
        self.safe_log(f"[SUCCESS] Saved {name}")
        
    def delete(self, acc): 
        if messagebox.askyesno("Confirm", "Delete?"): self.data.remove(acc); DataManager.save(self.data); self.refresh_ui()
            
    def refresh(self): 
        # INTEGRATED: Parallel Refresh Logic
        self.safe_log("[INFO] Refreshing all accounts (Parallel)...")
        
        def update_task(acc):
            if "cookie" in acc:
                stats = self.api.stats(acc['cookie'], acc.get('user_agent'), acc.get('proxy'))
                acc.update(stats)
                
                # FORCE UPDATE GAME NAME
                pid = acc.get('default_place_id') or acc.get('game_id')
                if pid:
                    real_name = self.api.get_game_name(pid)
                    acc['last_played_name'] = real_name
                    acc['game_id'] = pid
                            
                acc['health'] = Utils.compute_account_health(acc)

        def run_parallel():
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(update_task, self.data)
            
            self.after(0, self.refresh_ui)
            self.safe_log("[SUCCESS] Refresh complete.")

        threading.Thread(target=run_parallel, daemon=True).start()
        
    def import_data(self):
        t = CenterDialog(self,"Import","User:Pass").ask()
        if t: 
            for l in t.splitlines():
                if ":" in l: u, p = l.split(":", 1); self.data.append({"username":u.strip(), "password":Security.encrypt(p.strip())})
            DataManager.save(self.data); self.refresh_ui()
            
    def open_settings(self): SettingsDialog(self, lambda:[ConfigManager.load(), self.retheme(), self.refresh_ui()])

    def retheme(self):
        ThemeManager.apply()
        self.configure(fg_color=THEME["bg"])
        
    def setup_tools(self):
        t = self.tabs.tab("Game Tools")
        for w in t.winfo_children(): w.destroy()
        
        f1 = IOSCard(t, corner_radius=18)
        f1.pack(fill="x", pady=10, padx=12)
        ctk.CTkLabel(f1, text="Join by Job ID", font=FontManager.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        r1 = ctk.CTkFrame(f1, fg_color="transparent"); r1.pack(fill="x", padx=14, pady=14)
        self.job = ctk.CTkEntry(r1, placeholder_text="Enter Job ID...", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.job.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.job_acc_var = ctk.StringVar(value="Select Account")
        self.job_acc_menu = ctk.CTkOptionMenu(r1, variable=self.job_acc_var, values=[], width=190, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.job_acc_menu.pack(side="left", padx=(0,10))
        ModernButton(r1, text="Launch", width=90, type="accent", command=self.manual_job_launch).pack(side="right")
        
        f2 = IOSCard(t, corner_radius=18)
        f2.pack(fill="x", pady=10, padx=12)
        ctk.CTkLabel(f2, text="Global Place Override", font=FontManager.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        r2 = ctk.CTkFrame(f2, fg_color="transparent"); r2.pack(fill="x", padx=14, pady=14)
        self.place = ctk.CTkEntry(r2, placeholder_text="Place ID...", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.place.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ModernButton(r2, text="Browse", width=90, type="primary", command=self.open_game_selector).pack(side="right")

        f3 = IOSCard(t, corner_radius=18)
        f3.pack(fill="x", pady=10, padx=12)
        ctk.CTkLabel(f3, text="Find User Server", font=FontManager.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        r3 = ctk.CTkFrame(f3, fg_color="transparent"); r3.pack(fill="x", padx=14, pady=14)
        self.pu = ctk.CTkEntry(r3, placeholder_text="Username...", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.pu.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ModernButton(r3, text="Find", width=90, type="warning", command=self.t_find).pack(side="right")

    def manual_job_launch(self):
        jid = self.job.get().strip()
        user = self.job_acc_var.get()
        if not jid: 
            self.safe_log("Please enter a Job ID.")
            return
        acc = next((a for a in self.data if a["username"] == user), None)
        if acc and "cookie" in acc: 
            self.launch(acc, jid)
        else: 
            self.safe_log("Please select a valid verified account.")
            
    def t_find(self): 
        threading.Thread(target=self._find_t, args=(self.get_acc(), self.pu.get()), daemon=True).start()
        
    def _find_t(self, a, u):
        if not a: return
        uid = self.api.get_id(u)
        p = self.api.get_presence(uid)
        if p and p.get('gameId'): 
            self.launch(a, p['gameId'])
        else: 
            self.safe_log("User offline/hidden")
            
    def get_acc(self): 
        return next((a for a in self.data if "cookie" in a), None)
        
    def open_game_selector(self):
        """Opens the game selector dialog."""
        def cb(pid, target_acc, game_name):
            if pid:
                self.place.delete(0, "end")
                self.place.insert(0, str(pid))
                
                if target_acc == "All Accounts":
                    for acc in self.data:
                        acc['default_place_id'] = str(pid)
                        acc['last_played_name'] = game_name
                    DataManager.save(self.data)
                    self.safe_log(f"[INFO] Successfully changed all Game to [{game_name}] Place ID: [{pid}]")
                    self.refresh_ui()
                    
                elif target_acc and target_acc != "Global Tool Only":
                    acc = next((a for a in self.data if a['username'] == target_acc), None)
                    if acc: 
                        acc['default_place_id'] = str(pid)
                        acc['last_played_name'] = game_name
                        DataManager.save(self.data)
                        self.safe_log(f"Changed Game for [{acc['username']}] to [{game_name}]")
                        self.launch(acc, pid)
                else:
                    self.safe_log(f"Selected: {game_name}")
        
        GameSelector(self, cb, self.data, self)

if __name__ == "__main__":
    app = App()
    app.mainloop()
