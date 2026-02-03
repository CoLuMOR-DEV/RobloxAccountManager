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
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps
from tkinter import messagebox
import tkinter.font as tkfont
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DRIVER_PATH = r"msedgedriver.exe"

APP_NAME = "cx.manager"
VERSION = "v0.1.0"

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
    "use_bootstrapper": True,
    "bootstrapper_preference": "Auto",
    "presence_tracking": True,
    "presence_interval": 10,
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

class FontService:
    family_ui = "Segoe UI"
    family_mono = "Consolas"

    @classmethod
    def init(cls, root):
        try:
            fams = set(tkfont.families(root))
        except Exception:
            fams = set()

        ui_candidates = [
            "SF Pro Display", "SF Pro Text", "San Francisco", "Helvetica Neue", "Segoe UI Variable", "Segoe UI"
        ]
        
        mono_candidates = [
            "SF Mono", "Cascadia Mono", "Consolas"
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


class ThemeService:
    LIGHT_PALETTE = {
        "bg": "#F2F2F7", "sidebar": "#F2F2F7", "card_bg": "#FFFFFF", "card_hover": "#E5E5EA",
        "text_main": "#000000", "text_sub": "#6E6E73", "success": "#34C759", "danger": "#FF3B30",
        "warning": "#FF9500", "gray": "#8E8E93", "link": "#007AFF", "input_bg": "#FFFFFF",
        "border": "#C6C6C8", "separator": "#C6C6C8", "accent": "#007AFF", "accent_hover": "#338CFF",
    }

    DARK_PALETTE = {
        "bg": "#000000", "sidebar": "#000000", "card_bg": "#1C1C1E", "card_hover": "#2C2C2E",
        "text_main": "#FFFFFF", "text_sub": "#8E8E93", "success": "#30D158", "danger": "#FF453A",
        "warning": "#FF9F0A", "gray": "#8E8E93", "link": "#64D2FF", "input_bg": "#2C2C2E",
        "border": "#3A3A3C", "separator": "#3A3A3C", "accent": "#0A84FF", "accent_hover": "#409CFF", 
    }

    ACCENTS_LIGHT = {
        "Blue": ("#007AFF", "#338CFF"), "Green": ("#34C759", "#5CD77F"),
        "Orange": ("#FF9500", "#FFB13A"), "Purple": ("#AF52DE", "#C77BEB"), "Pink": ("#FF2D55", "#FF5C7B"),
    }

    ACCENTS_DARK = {
        "Blue": ("#0A84FF", "#409CFF"), "Green": ("#30D158", "#5CE27A"),
        "Orange": ("#FF9F0A", "#FFB54A"), "Purple": ("#BF5AF2", "#D17CFA"), "Pink": ("#FF375F", "#FF5C7C"),
    }

    @classmethod
    def apply(cls):
        mode = (CONFIG.get("theme_mode") or "Dark").strip()
        if mode.lower() not in ("dark", "light", "system"): mode = "Dark"
        try: ctk.set_appearance_mode(mode.capitalize())
        except Exception: pass

        is_dark = mode.lower() == "dark" or (mode.lower() == "system")
        palette = cls.DARK_PALETTE if is_dark else cls.LIGHT_PALETTE
        THEME.update(palette)

        accent_name = (CONFIG.get("accent_color") or "Blue").strip().title()
        if is_dark: accent_map = cls.ACCENTS_DARK
        else: accent_map = cls.ACCENTS_LIGHT
            
        if accent_name not in accent_map: accent_name = "Blue"
        a, ah = accent_map[accent_name]
        THEME["accent"] = a
        THEME["accent_hover"] = ah
        if not is_dark: THEME["link"] = a 
        else: THEME["link"] = THEME["link"]

ctk.set_default_color_theme("blue")


class Utils:
    @staticmethod
    def ensure_dirs():
        for d in DIRS.values(): os.makedirs(d, exist_ok=True)
        if not os.path.exists(FILES["log"]):
            try:
                with open(FILES["log"], "w") as f: f.write(f"[{datetime.now()}] cx.manager started\n")
            except Exception: pass
        if os.path.exists(DIRS["sessions"]):
            try: shutil.rmtree(DIRS["sessions"]); os.makedirs(DIRS["sessions"], exist_ok=True)
            except Exception: pass

    @staticmethod
    def log_to_file(msg):
        try:
            with open(FILES["log"], "a", encoding="utf-8") as f: f.write(f"{msg}\n")
        except Exception: pass

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
    def random_string(length=8):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(random.choice(chars) for _ in range(length))
        
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
        img = img.resize((100, 100))
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


class PerformanceTweak:
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
        settings_data = PerformanceTweak.get_settings(enabled)
        for root, dirs, files in os.walk(roblox_versions):
            if "RobloxPlayerBeta.exe" in files:
                c_path = os.path.join(root, "ClientSettings")
                os.makedirs(c_path, exist_ok=True)
                with open(os.path.join(c_path, "ClientAppSettings.json"), "w") as f:
                    json.dump(settings_data, f)


class WebhookService:
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
    def send_launch_log(api_ref, username, game_name, place_id, initial_job_id, user_id, manual_track=False, robux="0", server_info=None):
        url = CONFIG.get("discord_webhook")
        if not url: return

        def _task():
            final_game_name = game_name
            if place_id:
                try:
                    fetched_name = api_ref.get_game_name(place_id)
                    if fetched_name and fetched_name != f"Place {place_id}":
                        final_game_name = fetched_name
                except: pass

            real_job_id = initial_job_id
            if not real_job_id and user_id and not manual_track:
                real_job_id = WebhookService.resolve_job_id(api_ref, user_id)

            game_link = f"https://www.roblox.com/games/{place_id}"
            user_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://tr.rbxcdn.com/53eb9b17fe1432a809c73a13889b5006/150/150/Image/Png"
            
            try:
                r_icon = requests.get(f"https://thumbnails.roblox.com/v1/places/gameicons?placeIds={place_id}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false").json()
                final_icon = r_icon['data'][0]['imageUrl']
            except:
                final_icon = user_thumb

            fields = [
                {"name": "Game", "value": f"[{final_game_name}]({game_link})", "inline": True},
                {"name": "Robux", "value": f"R$ {robux}", "inline": True},
                {"name": "Status", "value": "Active" if not manual_track else "Moved/Updated", "inline": True}
            ]

            if server_info:
                ping = server_info.get('ping', 'N/A')
                players = f"{server_info.get('playing', '?')}/{server_info.get('maxPlayers', '?')}"
                fps = int(server_info.get('fps', 0))
                fields.append({"name": "Server Stats", "value": f"Ping: {ping}ms | Players: {players} | FPS: {fps}", "inline": False})

            fields.append({"name": "Job ID", "value": f"||{real_job_id or 'Auto-Match'}||", "inline": False})
            fields.append({"name": "Place ID", "value": f"{place_id}", "inline": False})

            embed = {
                "title": f"Session Update: {username}",
                "url": game_link,
                "color": 0x0A84FF,
                "author": {
                    "name": "cx.manager",
                    "icon_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Roblox_player_icon_black.svg/1200px-Roblox_player_icon_black.svg.png"
                },
                "fields": fields,
                "thumbnail": { "url": user_thumb },
                "image": { "url": final_icon },
                "footer": {"text": f"cx.manager {VERSION}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            try: requests.post(url, json={"username": "cx.manager", "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Roblox_player_icon_black.svg/1200px-Roblox_player_icon_black.svg.png", "embeds": [embed]})
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


class CryptoUtil:
    @staticmethod
    def encrypt(t): return "ENC_" + base64.b64encode(t.encode()).decode() if t else ""
    @staticmethod
    def decrypt(t): return base64.b64decode(t[4:]).decode() if t and t.startswith("ENC_") else t


class BootstrapperService:
    CANDIDATES = [
        ("Bloxstrap", ("Bloxstrap", "Bloxstrap.exe")),
        ("Fishstrap", ("Fishstrap", "Fishstrap.exe")),
        ("Voidstrap", ("Voidstrap", "Voidstrap.exe")),
        ("Froststrap", ("Froststrap", "Froststrap.exe")),
        ("Plexity", ("Plexity", "Plexity.exe")),
    ]

    @classmethod
    def get_names(cls):
        return [name for name, _ in cls.CANDIDATES]

    @classmethod
    def find(cls, preference="Auto"):
        local_app_data = os.getenv("LOCALAPPDATA")
        if not local_app_data:
            return None
        order = []
        if preference and preference != "Auto" and preference in cls.get_names():
            order.append(preference)
        for name in cls.get_names():
            if name not in order:
                order.append(name)
        for name in order:
            folder, exe = dict(cls.CANDIDATES)[name]
            path = os.path.join(local_app_data, folder, exe)
            if os.path.exists(path):
                return name, path
        return None


class ConfigService:
    @staticmethod
    def load():
        if os.path.exists(FILES["config"]):
            try:
                with open(FILES["config"], "r") as f: CONFIG.update(json.load(f))
            except: pass

        CONFIG.setdefault("theme_mode", "Dark")
        CONFIG.setdefault("accent_color", "Blue")
        CONFIG.setdefault("fps_unlock", False)
        CONFIG.setdefault("potato_mode", False)
        if "use_bootstrapper" not in CONFIG and "use_fishstrap" in CONFIG:
            CONFIG["use_bootstrapper"] = CONFIG.get("use_fishstrap", True)
        CONFIG.setdefault("use_bootstrapper", True)
        CONFIG.setdefault("bootstrapper_preference", "Auto")
        CONFIG.setdefault("presence_tracking", True)
        CONFIG.setdefault("presence_interval", 10)
        CONFIG.pop("use_fishstrap", None)
        CONFIG.setdefault("discord_webhook", "")
        ThemeService.apply()

    @staticmethod
    def save():
        try:
            with open(FILES["config"], "w") as f: json.dump(CONFIG, f, indent=4)
        except: pass


class AccountStore:
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


class FPSOptimizer:
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


class HttpClient:
    _sess = requests.Session()
    _sess.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    })
    @classmethod
    def get(cls, url): return cls._sess.get(url, timeout=10)
    @classmethod
    def post(cls, url, json=None): return cls._sess.post(url, json=json, timeout=10)
    @classmethod
    def set_cookie(cls, cookie):
         if cookie: cls._sess.cookies[".ROBLOSECURITY"] = cookie


class AssetLoader:
    _pool = ThreadPoolExecutor(max_workers=4)

    @staticmethod
    def fetch_avatar_async(uid, path, cb, size=(32, 32)):
        def _task():
            try:
                if os.path.exists(path):
                    if os.path.getsize(path) > 100:
                        try:
                            pil_img = Utils.circle_crop(Image.open(path).convert("RGBA"))
                            cb(ctk.CTkImage(pil_img, size=size)); return
                        except: pass
                    else:
                        try: os.remove(path)
                        except: pass
                
                r = HttpClient.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=150x150&format=Png&isCircular=false")
                if r.status_code == 200:
                    d = r.json().get("data", [])
                    if d and d[0]["state"] == "Completed":
                        img_url = d[0]["imageUrl"]
                        ir = HttpClient.get(img_url)
                        if ir.status_code == 200 and len(ir.content) > 100:
                             with open(path, "wb") as f: f.write(ir.content)
                             pil_img = Utils.circle_crop(Image.open(BytesIO(ir.content)).convert("RGBA"))
                             cb(ctk.CTkImage(pil_img, size=size))
            except: pass
        AssetLoader._pool.submit(_task)

    @staticmethod
    def fetch_image_async(url, path, cb, size=(128, 128)):
        def _task():
            try:
                if os.path.exists(path):
                    if os.path.getsize(path) > 100:
                         try: cb(ctk.CTkImage(Image.open(path), size=size)); return
                         except: pass
                    else:
                        try: os.remove(path)
                        except: pass

                if not url: return
                r = HttpClient.get(url)
                if r.status_code == 200 and len(r.content) > 100:
                    with open(path, "wb") as f: f.write(r.content)
                    cb(ctk.CTkImage(Image.open(BytesIO(r.content)), size=size))
            except: pass
        AssetLoader._pool.submit(_task)

    @staticmethod
    def get_cached_avatar(uid):
        p = f"{DIRS['cache']}/{uid}.png"
        if os.path.exists(p) and os.path.getsize(p) > 100:
            try:
                img = Image.open(p).convert("RGBA")
                pil_img = Utils.circle_crop(img)
                return ctk.CTkImage(pil_img, size=(32, 32))
            except: pass
        return None


class RobloxClient:
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
            job_p = f"%26gameId%3D{job_id}" if job_id else ""
            
            req_type = "RequestGameJob" if job_id else "RequestGame"
            
            url = f"https%3A%2F%2Fassetgame.roblox.com%2Fgame%2FPlaceLauncher.ashx%3Frequest%3D{req_type}%26browserTrackerId%3D{ts}%26placeId%3D{place}{job_p}%26isPlayTogetherGame%3Dfalse"
            
            if CONFIG.get("use_bootstrapper", True):
                preference = CONFIG.get("bootstrapper_preference", "Auto")
                found = BootstrapperService.find(preference)
                if found:
                    name, path = found
                    launch_arg = f"roblox-player:1+launchmode:play+gameinfo:{ticket}+launchtime:{ts}+placelauncherurl:{url}"
                    subprocess.Popen([path, launch_arg])
                    return f"Launched via {name}"
                self.log("No supported bootstrappers found. Using default...")

            cmd = f"roblox-player:1+launchmode:play+gameinfo:{ticket}+launchtime:{ts}+placelauncherurl:{url}"
            os.startfile(cmd)
            return True
        except Exception as e: return str(e)

    def get_game_name(self, place_id):
        try:
            r = HttpClient.get(f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}")
            d = r.json()
            if d and len(d) > 0: return d[0]["name"]
            
            r2 = HttpClient.get(f"https://games.roblox.com/v1/games?universeIds={place_id}")
            d2 = r2.json()
            if d2.get("data"): return d2["data"][0]["name"]

            return f"Place {place_id}"
        except: return f"Place {place_id}"

    def get_game_max_players(self, place_id):
        try:
            r = HttpClient.get(f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}")
            d = r.json()
            if d and len(d) > 0: return d[0]["maxPlayers"]
            return 20 
        except: return 20

    def search_games_new(self, query):
        try:
            search_q = query if query else "Simulator"
            
            url = f"https://apis.roblox.com/search-api/omni-search?searchQuery={search_q}&sessionId={str(uuid.uuid4())}&pageType=all&maxRows=12"
            
            r = HttpClient.get(url)
            d = r.json()
            
            raw_games = []
            
            if "searchResults" in d:
                for grp in d["searchResults"]:
                    if grp.get("contentGroupType") == "Game":
                         raw_games.extend(grp.get("contents", []))
            
            if not raw_games: 
                print(f"[DEBUG] No raw games found for: {search_q}")
                return []
            
            raw_games = raw_games[:12]
            
            u_ids = [str(g["contentId"]) for g in raw_games]
            u_str = ",".join(u_ids)
            
            details_url = f"https://games.roblox.com/v1/games?universeIds={u_str}"
            details_r = HttpClient.get(details_url)
            details_data = details_r.json().get("data", [])
            
            icons_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={u_str}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false"
            icons_r = HttpClient.get(icons_url)
            icons_data = icons_r.json().get("data", [])
            
            d_map = {str(x["id"]): x for x in details_data}
            i_map = {str(x["targetId"]): x["imageUrl"] for x in icons_data}
            
            final = []
            for g in raw_games:
                uid = str(g["contentId"])
                
                if uid in d_map:
                    info = d_map[uid]
                    final.append({
                        "name": info.get("name", g.get("name", "Unknown")), 
                        "placeId": str(info.get("rootPlaceId")),
                        "universeId": uid,
                        "iconUrl": i_map.get(uid),
                        "playing": info.get("playing", 0)
                    })
            
            print(f"[DEBUG] Search '{search_q}' returned {len(final)} playable games.")
            return final

        except Exception as e:
            print(f"[ERROR] New Search Logic Failed: {e}")
            return []

    def get_servers(self, place_id, cursor=None, sort_order="Desc", limit=50):
        try:
            url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?sortOrder={sort_order}&limit={limit}&excludeFullGames=false"
            if cursor: url += f"&cursor={cursor}"
            r = HttpClient.get(url); data = r.json()
            
            if r.status_code != 200 or not data.get("data"):
                try:
                    r2 = HttpClient.get(f"https://games.roblox.com/v1/games?universeIds={place_id}")
                    pid = r2.json()["data"][0]["rootPlaceId"]
                    url = f"https://games.roblox.com/v1/games/{pid}/servers/Public?sortOrder={sort_order}&limit={limit}&excludeFullGames=false"
                    if cursor: url += f"&cursor={cursor}"
                    r = HttpClient.get(url); data = r.json()
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
        try: return HttpClient.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [user], "excludeBannedUsers": True}).json()["data"][0]["id"]
        except: return None
    
    def get_presence(self, uid):
        try: 
            return HttpClient.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [uid]}).json()["userPresences"][0]
        except: 
            return None

    def check_own_presence(self, cookie, uid):
        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = cookie
        try:
            r = s.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [uid]}, timeout=5)
            if r.status_code == 200:
                return r.json()["userPresences"][0]
        except: pass
        return None


class WebAutomation:
    def __init__(self, log_func): self.log = log_func
    def open(self, u, p, cookie, target_url, cb, mode="NORMAL", proxy=None, signup_year=None, signup_gender=None):
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
                if u and p and mode == "SIGNUP":
                    self.log(f"Attempting auto-signup for {u}...")
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "MonthDropdown")))
                        month_el = driver.find_element(By.ID, "MonthDropdown")
                        day_el = driver.find_element(By.ID, "DayDropdown")
                        year_el = driver.find_element(By.ID, "YearDropdown")
                        month_names = [
                            "January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"
                        ]
                        month_value = random.choice(month_names)
                        day_value = random.randint(1, 28)
                        def select_dropdown(el, value, prefer_text=False):
                            try:
                                selector = Select(el)
                            except Exception:
                                return False
                            attempts = []
                            if prefer_text:
                                attempts = [("text", selector.select_by_visible_text), ("value", selector.select_by_value)]
                            else:
                                attempts = [("value", selector.select_by_value), ("text", selector.select_by_visible_text)]
                            for _, method in attempts:
                                try:
                                    method(str(value))
                                    return True
                                except Exception:
                                    continue
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                                el.click()
                                el.send_keys(str(value))
                                return True
                            except Exception:
                                return False
                        select_dropdown(month_el, month_value, prefer_text=True)
                        select_dropdown(day_el, day_value)
                        if signup_year:
                            select_dropdown(year_el, signup_year, prefer_text=True)
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "signup-username")))
                        driver.find_element(By.ID, "signup-username").send_keys(u); time.sleep(0.5)
                        driver.find_element(By.ID, "signup-password").send_keys(p); time.sleep(0.5)
                        if signup_gender in ("Male", "Female"):
                            gender_button_id = "FemaleButton" if signup_gender == "Female" else "MaleButton"
                            try:
                                gender_button = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.ID, gender_button_id))
                                )
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gender_button)
                                gender_button.click()
                            except Exception:
                                gender_label = "Female" if signup_gender == "Female" else "Male"
                                try:
                                    gender_button = WebDriverWait(driver, 5).until(
                                        EC.element_to_be_clickable((By.XPATH, f"//button[@title='{gender_label}' or contains(@aria-label, '{gender_label}')]"))
                                    )
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gender_button)
                                    gender_button.click()
                                except Exception:
                                    try:
                                        gender_button = driver.find_element(By.ID, gender_button_id)
                                        driver.execute_script("arguments[0].click();", gender_button)
                                    except Exception:
                                        pass
                        signup_clicked = False
                        for by, selector in [
                            (By.ID, "signup-button"),
                            (By.XPATH, "//button[contains(., 'Sign Up')]"),
                            (By.XPATH, "//input[@type='submit' and (contains(@value, 'Sign Up') or contains(@aria-label, 'Sign Up'))]"),
                        ]:
                            try:
                                signup_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", signup_button)
                                signup_button.click()
                                signup_clicked = True
                                break
                            except Exception:
                                try:
                                    signup_button = driver.find_element(by, selector)
                                    driver.execute_script("arguments[0].click();", signup_button)
                                    signup_clicked = True
                                    break
                                except Exception:
                                    pass
                                continue
                        if not signup_clicked:
                            self.log("Auto-signup warning: Sign Up button not found or not clickable.")
                    except Exception as e: self.log(f"Auto-signup failed: {e}")
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
            if mode == "SIGNUP":
                start = time.time()
                while time.time() - start < 600:
                    try:
                        if not driver.window_handles: break
                        c = driver.get_cookies()
                        sec = next((x["value"] for x in c if x["name"] == ".ROBLOSECURITY"), None)
                        if sec:
                            cb(u, p, sec, driver.execute_script("return navigator.userAgent;"))
                            break
                    except: break
                    time.sleep(1)
                driver.quit(); return
            while driver.window_handles: time.sleep(1)
        except Exception as e:
            self.log(f"Browser Error: {e}"); 
            if driver: 
                try: driver.quit()
                except: pass


class CardFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        forced_height = kwargs.pop("height", 40)
        if forced_height is None:
            forced_height = 0 
        
        super().__init__(
            master,
            fg_color=kwargs.pop("fg_color", THEME["card_bg"]),
            corner_radius=kwargs.pop("corner_radius", 14),
            border_width=kwargs.pop("border_width", 1),
            border_color=kwargs.pop("border_color", THEME["border"]),
            height=forced_height,
            **kwargs
        )
        if forced_height > 0:
            self.pack_propagate(False)

class ActionBtn(ctk.CTkButton):
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
        
        h = kwargs.pop("height", 24)
        c_rad = kwargs.pop("corner_radius", 10)
        bg_col = kwargs.pop("fg_color", fg)
        hov_col = kwargs.pop("hover_color", hover)
        txt_col = kwargs.pop("text_color", "#FFFFFF" if type != "subtle" else THEME["text_main"])
        fnt = kwargs.pop("font", FontService.ui(11, "bold"))
        
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


class InputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.title(title)
        self.res = None
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        CardFrame(self, height=None).pack(fill="both", expand=True, padx=12, pady=12)
        container = self.winfo_children()[-1]
        container.pack_propagate(True) 
        
        ctk.CTkLabel(container, text=prompt, text_color=THEME["text_main"], font=FontService.ui(13, "bold")).pack(pady=(14, 8), padx=18)
        self.entry = ctk.CTkEntry(container, width=260, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.entry.pack(pady=5, padx=18)
        ActionBtn(container, text="OK", type="primary", command=self.ok).pack(pady=(12, 14))
        Utils.center_window(self, 340, 180)
    def ok(self):
        self.res = self.entry.get()
        self.destroy()
    def ask(self):
        self.wait_window()
        return self.res


class ImportAccountsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Import Accounts")
        self.res = None
        self.grab_set()
        self.configure(fg_color=THEME["bg"])

        card = CardFrame(self, height=None)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        card.pack_propagate(True)

        tabs = ctk.CTkTabview(card, fg_color=THEME["card_bg"], segmented_button_selected_color=THEME["accent"])
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        user_tab = tabs.add("User:Pass")
        cookie_tab = tabs.add("RobloSecurity Cookie")

        ctk.CTkLabel(user_tab, text="Paste accounts (one per line)", text_color=THEME["text_sub"], font=FontService.ui(11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.user_text = ctk.CTkTextbox(user_tab, height=160, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.user_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(cookie_tab, text="Paste .ROBLOSECURITY cookies (one per line)", text_color=THEME["text_sub"], font=FontService.ui(11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.cookie_text = ctk.CTkTextbox(cookie_tab, height=160, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.cookie_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ActionBtn(card, text="OK", type="primary", command=lambda: self.ok(tabs.get())).pack(pady=(0, 10))
        Utils.center_window(self, 520, 340)

    def ok(self, tab_name):
        if tab_name == "User:Pass":
            text = self.user_text.get("1.0", "end").strip()
        else:
            text = self.cookie_text.get("1.0", "end").strip()
        self.res = (tab_name, text) if text else None
        self.destroy()

    def ask(self):
        self.wait_window()
        return self.res


class CreateAccountWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Create Accounts")
        self.cb = callback
        self.grab_set()
        self.configure(fg_color=THEME["bg"])

        card = CardFrame(self, height=None)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="How Many Accounts", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.count_entry = ctk.CTkEntry(card, width=200, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.count_entry.insert(0, "1")
        self.count_entry.pack(pady=6)

        ctk.CTkLabel(card, text="Base Name", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(6, 2))
        self.base_entry = ctk.CTkEntry(card, width=260, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.base_entry.insert(0, "user")
        self.base_entry.pack(pady=6)

        self.random_names_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            card,
            text="Random Names",
            variable=self.random_names_var,
            fg_color=THEME["card_hover"],
            progress_color=THEME["accent"],
            button_color=THEME["border"],
            button_hover_color=THEME["separator"],
            text_color=THEME["text_main"],
        ).pack(pady=(4, 6))

        ctk.CTkLabel(card, text="Password (if not random)", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(6, 2))
        self.password_entry = ctk.CTkEntry(card, width=260, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12, show="*")
        self.password_entry.insert(0, "Password123!")
        self.password_entry.pack(pady=6)

        self.random_pass_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            card,
            text="Random Password",
            variable=self.random_pass_var,
            fg_color=THEME["card_hover"],
            progress_color=THEME["accent"],
            button_color=THEME["border"],
            button_hover_color=THEME["separator"],
            text_color=THEME["text_main"],
        ).pack(pady=(4, 12))

        self.easy_pass_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            card,
            text="Easy Password",
            variable=self.easy_pass_var,
            fg_color=THEME["card_hover"],
            progress_color=THEME["accent"],
            button_color=THEME["border"],
            button_hover_color=THEME["separator"],
            text_color=THEME["text_main"],
        ).pack(pady=(0, 12))

        ctk.CTkLabel(card, text="Birth Year", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(6, 2))
        years = [str(y) for y in range(1970, datetime.now().year - 5)]
        self.year_var = ctk.StringVar(value=years[-1])
        self.year_menu = ctk.CTkOptionMenu(
            card,
            values=years,
            variable=self.year_var,
            fg_color=THEME["input_bg"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text_main"],
            dropdown_text_color=THEME["text_main"],
            dropdown_fg_color=THEME["card_bg"],
        )
        self.year_menu.pack(pady=6)

        ctk.CTkLabel(card, text="Gender", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(6, 2))
        self.gender_var = ctk.StringVar(value="Random")
        self.gender_menu = ctk.CTkOptionMenu(
            card,
            values=["Random", "Male", "Female"],
            variable=self.gender_var,
            fg_color=THEME["input_bg"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text_main"],
            dropdown_text_color=THEME["text_main"],
            dropdown_fg_color=THEME["card_bg"],
        )
        self.gender_menu.pack(pady=6)

        ActionBtn(card, text="Create", type="success", command=self.submit).pack(fill="x", padx=12, pady=(0, 12))
        Utils.center_window(self, 420, 620)

    def submit(self):
        try:
            count = int(self.count_entry.get().strip())
        except ValueError:
            count = 1
        count = max(1, min(count, 20))
        base = self.base_entry.get().strip()
        password = self.password_entry.get().strip()
        self.cb(
            count,
            base,
            self.random_names_var.get(),
            self.random_pass_var.get(),
            self.easy_pass_var.get(),
            password,
            int(self.year_var.get()),
            self.gender_var.get(),
        )
        self.destroy()


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Settings")
        self.callback = callback
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        
        wrap = CardFrame(self, height=None)
        wrap.pack_propagate(True)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)
        
        ctk.CTkLabel(wrap, text="Appearance", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        self.mode = ctk.StringVar(value=CONFIG.get("theme_mode", "Dark"))
        self.mode_menu = ctk.CTkOptionMenu(wrap, variable=self.mode, values=["System", "Light", "Dark"], fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.mode_menu.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(wrap, text="Accent Color", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.accent = ctk.StringVar(value=CONFIG.get("accent_color", "Blue"))
        self.accent_menu = ctk.CTkOptionMenu(wrap, variable=self.accent, values=["Blue", "Green", "Orange", "Purple", "Pink"], fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.accent_menu.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(wrap, text="Discord Webhook URL", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.webhook_entry = ctk.CTkEntry(wrap, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.webhook_entry.insert(0, CONFIG.get("discord_webhook", ""))
        self.webhook_entry.pack(fill="x", padx=16, pady=(0, 12))

        self.fps_var = ctk.BooleanVar(value=CONFIG.get("fps_unlock", False))
        self.potato_var = ctk.BooleanVar(value=CONFIG.get("potato_mode", False))
        self.bootstrapper_var = ctk.BooleanVar(value=CONFIG.get("use_bootstrapper", True))
        self.bootstrapper_pref = ctk.StringVar(value=CONFIG.get("bootstrapper_preference", "Auto"))
        self.presence_var = ctk.BooleanVar(value=CONFIG.get("presence_tracking", True))

        toggles = ctk.CTkFrame(wrap, fg_color="transparent")
        toggles.pack(fill="x", padx=16, pady=(2, 12))

        self.fps_sw = ctk.CTkSwitch(toggles, text="FPS Unlocker", variable=self.fps_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.fps_sw.pack(anchor="w", pady=6)
        self.potato_sw = ctk.CTkSwitch(toggles, text="Potato Mode (Low GFX)", variable=self.potato_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.potato_sw.pack(anchor="w", pady=6)

        ctk.CTkLabel(wrap, text="Multi-Instance", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.bootstrapper_sw = ctk.CTkSwitch(wrap, text="Use Bootstrappers (Multi-Instance)", variable=self.bootstrapper_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.bootstrapper_sw.pack(anchor="w", padx=16, pady=6)

        ctk.CTkLabel(wrap, text="Preferred Bootstrapper", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.bootstrapper_menu = ctk.CTkOptionMenu(
            wrap,
            variable=self.bootstrapper_pref,
            values=["Auto"] + BootstrapperService.get_names(),
            fg_color=THEME["input_bg"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent_hover"],
            text_color=THEME["text_main"],
            dropdown_text_color=THEME["text_main"],
            dropdown_fg_color=THEME["card_bg"],
        )
        self.bootstrapper_menu.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(wrap, text="Background Tracking", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.presence_sw = ctk.CTkSwitch(wrap, text="Presence Tracking", variable=self.presence_var, fg_color=THEME["card_hover"], progress_color=THEME["accent"], button_color=THEME["border"], button_hover_color=THEME["separator"], text_color=THEME["text_main"])
        self.presence_sw.pack(anchor="w", padx=16, pady=6)

        ctk.CTkLabel(wrap, text="Presence Check Interval (sec)", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(anchor="w", padx=16, pady=(6, 6))
        self.presence_interval_entry = ctk.CTkEntry(wrap, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.presence_interval_entry.insert(0, str(CONFIG.get("presence_interval", 10)))
        self.presence_interval_entry.pack(fill="x", padx=16, pady=(0, 12))
        
        ActionBtn(wrap, text="Test Webhook", type="warning", command=self.test_webhook).pack(fill="x", padx=16, pady=(0, 6))

        ActionBtn(wrap, text="Save & Apply", type="primary", command=self.save).pack(fill="x", padx=16, pady=(6, 14))
        Utils.center_window(self, 380, 740)
    
    def test_webhook(self):
        url = self.webhook_entry.get().strip()
        res = WebhookService.send_test(url)
        messagebox.showinfo("Webhook Test", res)

    def save(self):
        CONFIG["theme_mode"] = self.mode.get()
        CONFIG["accent_color"] = self.accent.get()
        CONFIG["discord_webhook"] = self.webhook_entry.get().strip()
        if self.fps_var.get() != CONFIG.get("fps_unlock", False):
            CONFIG["fps_unlock"] = self.fps_var.get()
            FPSOptimizer.toggle_unlock(CONFIG["fps_unlock"])
        CONFIG["potato_mode"] = self.potato_var.get()
        PerformanceTweak.apply(CONFIG["potato_mode"])
        CONFIG["use_bootstrapper"] = self.bootstrapper_var.get()
        CONFIG["bootstrapper_preference"] = self.bootstrapper_pref.get()
        CONFIG["presence_tracking"] = self.presence_var.get()
        try:
            interval = int(self.presence_interval_entry.get().strip())
        except ValueError:
            interval = 10
        CONFIG["presence_interval"] = max(5, min(interval, 300))
        ConfigService.save()
        ThemeService.apply()
        self.callback()
        self.destroy()


class ServerBrowserWindow(ctk.CTkToplevel):
    def __init__(self, parent, place_id, account_data, api_ref, launcher_callback):
        super().__init__(parent)
        game_name = api_ref.get_game_name(place_id)
        self.title(f"Servers: {game_name}")
        
        self.api = api_ref
        self.place_id = place_id
        self.account = account_data
        self.launcher = launcher_callback
        self.cursor_stack = []
        self.current_cursor = None
        self.sort_order = ctk.StringVar(value="Desc")
        self.filter_full = ctk.BooleanVar(value=True)
        
        self.sort_mode = ctk.StringVar(value="Desc")
        
        self.cached_servers = []
        self.max_players = 20 
        
        self.attributes("-topmost", True)
        self.focus_force()
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        
        self.top_f = CardFrame(self, height=None) 
        self.top_f.pack_propagate(True)
        self.top_f.pack(fill="x", padx=12, pady=12)
        
        self.title_lbl = ctk.CTkLabel(self.top_f, text=f"Loading...", font=("Arial", 12, "bold"), text_color=THEME["text_main"])
        self.title_lbl.pack(side="left", padx=10)
        
        threading.Thread(target=self.init_data, daemon=True).start()

        ActionBtn(self.top_f, text="↻", width=42, type="primary", command=self.reload_fresh).pack(side="right", padx=6, pady=8)
        
        self.sort_menu = ctk.CTkOptionMenu(self.top_f, variable=self.sort_mode, values=["Desc", "Asc"], command=self.reload_fresh, width=90, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.sort_menu.pack(side="right", padx=6)
        
        self.chk_full = ctk.CTkCheckBox(self.top_f, text="Hide Full", variable=self.filter_full, command=self.apply_local_filter, width=90, font=FontService.ui(11), text_color=THEME["text_main"], hover_color=THEME["accent"])
        self.chk_full.pack(side="right", padx=10)

        self.filters_f = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_f.pack(fill="x", padx=12, pady=(0, 5))

        self.ping_var = ctk.StringVar(value="Any Ping")
        self.ping_menu = ctk.CTkOptionMenu(self.filters_f, variable=self.ping_var, values=["Any Ping", "<50ms", "<100ms", "<150ms", "<200ms", "<300ms"], command=self.apply_local_filter, width=110, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.ping_menu.pack(side="right", padx=5)

        self.page_num = 1
        self.ctrl_f = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_f.pack(side="bottom", fill="x", padx=12, pady=12)
        self.btn_prev = ActionBtn(self.ctrl_f, text="< Prev", width=90, type="subtle", command=self.prev_page)
        self.btn_prev.pack(side="left")
        
        self.page_lbl = ctk.CTkLabel(self.ctrl_f, text="Page 1", font=FontService.ui(12, "bold"), text_color=THEME["text_sub"])
        self.page_lbl.pack(side="left", expand=True)

        self.btn_next = ActionBtn(self.ctrl_f, text="Next >", width=90, type="subtle", command=self.next_page)
        self.btn_next.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)
        self.status_lbl = ctk.CTkLabel(self.scroll, text="Loading...", font=FontService.ui(12), text_color=THEME["text_sub"])
        self.status_lbl.pack(pady=20)
        
        Utils.center_window(self, 650, 700)
        self.reload_fresh()

    def init_data(self):
        name = self.api.get_game_name(self.place_id)
        mx = self.api.get_game_max_players(self.place_id)
        if self.winfo_exists():
            self.title_lbl.configure(text=name)
            self.max_players = mx

    def reload_fresh(self, _=None):
        self.cursor_stack = []
        self.current_cursor = None
        self.cached_servers = []
        self.page_num = 1
        self.update_page_label()
        self.btn_prev.configure(state="disabled")
        threading.Thread(target=self.load_servers, daemon=True).start()

    def update_page_label(self):
        self.page_lbl.configure(text=f"Page {self.page_num}")

    def load_servers(self, cursor=None):
        self.after(0, lambda: self.status_lbl.configure(text="Fetching servers..."))
        try:
            mode = self.sort_mode.get() 
            servers, next_cursor = self.api.get_servers(self.place_id, cursor, mode, limit=100) 
            self.cached_servers = servers
            self.current_cursor = next_cursor
            self.after(0, self.apply_local_filter)
        except Exception as e:
            self.after(0, lambda: self.status_lbl.configure(text="Error loading servers"))

    def apply_local_filter(self, _=None):
        data = self.cached_servers
        
        if self.filter_full.get():
            data = [s for s in data if s.get('playing', 0) < s.get('maxPlayers', 999)]

        p_filter = self.ping_var.get()
        if p_filter != "Any Ping":
            limit = int(p_filter.replace("<", "").replace("ms", ""))
            data = [s for s in data if s.get('ping', 999) <= limit]
            
        self.apply_sort(data)

    def apply_sort(self, data=None):
        if data is None: 
            self.apply_local_filter()
            return

        mode = self.sort_mode.get()
        if mode == "Best Ping":
            data.sort(key=lambda x: x.get("ping", 9999))
        elif mode == "Worst Ping":
            data.sort(key=lambda x: x.get("ping", 0), reverse=True)
        elif mode == "Players Desc":
            data.sort(key=lambda x: x.get("playing", 0), reverse=True)
        elif mode == "Players Asc":
            data.sort(key=lambda x: x.get("playing", 9999))
            
        self.display_servers(data)

    def display_servers(self, servers):
        if not self.winfo_exists(): return
        for w in self.scroll.winfo_children(): w.destroy()
        
        if not servers:
            ctk.CTkLabel(self.scroll, text="No servers match criteria.", text_color=THEME["text_sub"], font=FontService.ui(12)).pack(pady=20)
            self.btn_next.configure(state="normal" if self.current_cursor else "disabled")
            return
        
        page_view = servers[:8]
        
        for s in page_view:
            job_id = s.get("id")
            if not job_id: continue

            f = CardFrame(self.scroll, corner_radius=0, height=None) 
            f.pack_propagate(True)
            f.pack(fill="x", pady=4, padx=6)
            
            ping = s.get('ping', '?')
            fps = int(s.get('fps', 0))
            players = f"{s.get('playing', 0)}/{s.get('maxPlayers', 0)}"
            
            info = f"Ping: {ping}ms | FPS: {fps} | Players: {players}"
            ctk.CTkLabel(f, text=info, font=FontService.mono(12, "bold"), text_color=THEME["text_main"]).pack(side="left", padx=12, pady=10)
            
            short_id = job_id[:8] + "..."
            ctk.CTkLabel(f, text=f"ID: {short_id}", font=FontService.mono(10), text_color=THEME["text_sub"]).pack(side="left", padx=6)
            
            ActionBtn(f, text="Join", width=70, type="success", command=lambda j=job_id, s=s: self.join_server(j, s)).pack(side="right", padx=8, pady=8)
            ActionBtn(f, text="Copy", width=62, type="subtle", command=lambda j=job_id: self.copy_id(j)).pack(side="right", padx=6, pady=8)

        self.btn_next.configure(state="normal" if self.current_cursor else "disabled")
        self.btn_prev.configure(state="normal" if self.cursor_stack else "disabled")

    def copy_id(self, job_id):
        self.clipboard_clear()
        self.clipboard_append(job_id)
        self.update() 

    def next_page(self):
        if self.current_cursor:
            self.cursor_stack.append(self.current_cursor)
            self.page_num += 1
            self.update_page_label()
            threading.Thread(target=self.load_servers, args=(self.current_cursor,), daemon=True).start()

    def prev_page(self):
        if self.cursor_stack:
            self.page_num = max(1, self.page_num - 1)
            self.update_page_label()
            self.reload_fresh()

    def join_server(self, job_id, server_info=None):
        if self.account: 
            self.launcher(self.account, job_id, place_override=self.place_id, server_info=server_info)
            self.destroy()


class GameSelectorWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback, accounts, app_ref, pre_select_user=None, is_sub_window=False, tool_mode="full"):
        super().__init__(parent)
        self.title("Select Game")
        self.callback = callback
        self.api = RobloxClient(lambda x: None)
        self.accounts = accounts
        self.app = app_ref
        self.tool_mode = tool_mode
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure(fg_color=THEME["bg"])
        
        self.attributes("-topmost", True)
        self.focus_force()
        if is_sub_window: self.grab_set()
        
        top_frame = CardFrame(self, height=None)
        top_frame.pack_propagate(True)
        top_frame.pack(fill="x", padx=12, pady=12)
        
        if self.tool_mode == "full" and self.accounts:
            ctk.CTkLabel(top_frame, text="Apply to Account:", text_color=THEME["text_main"], font=FontService.ui(12, "bold")).pack(side="left", padx=10)
            self.acc_var = ctk.StringVar(value="Global Tool Only")
            acc_names = ["Global Tool Only"] + ["All Accounts"] + [a["username"] for a in self.accounts]
            self.acc_menu = ctk.CTkOptionMenu(top_frame, values=acc_names, variable=self.acc_var, width=170, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
            self.acc_menu.pack(side="left", padx=8)
            if pre_select_user: self.acc_var.set(pre_select_user)
        else: 
            self.acc_var = ctk.StringVar(value="Global Tool Only")
        
        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Search games...", width=160, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.search_entry.bind("<Return>", lambda _event: self.do_search(None))
        
        ActionBtn(top_frame, text="Search", width=80, type="primary", command=lambda: self.do_search(None)).pack(side="right", padx=5)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)
        
        self.scroll.grid_columnconfigure((0, 1, 2), weight=1, uniform="a")
        
        Utils.center_window(self, 780, 650)
        
        self.do_search("")

    def do_search(self, query=None):
        if query is None: query = self.search_entry.get()
        
        for w in self.scroll.winfo_children(): w.destroy()
        
        status_text = "Searching..." if query else "Fetching Popular Games..."
        ctk.CTkLabel(self.scroll, text=status_text, text_color=THEME["text_sub"], font=FontService.ui(14)).pack(pady=50)
        
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query): 
        games = self.api.search_games_new(query)
        self.after(0, lambda: self._display_results(games))

    def _display_results(self, games):
        if not self.winfo_exists(): return
        
        for w in self.scroll.winfo_children(): w.destroy()
        
        if not games:
            ctk.CTkLabel(self.scroll, text="No games found.", text_color=THEME["text_sub"]).pack(pady=20)
            return

        row = 0; col = 0
        for g in games:
            f = CardFrame(self.scroll, corner_radius=12, height=280, width=220, fg_color="#141414", border_color=THEME["border"], border_width=1) 
            f.pack_propagate(False)
            f.grid(row=row, column=col, padx=10, pady=10)
            
            content = ctk.CTkFrame(f, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=5, pady=5)

            img_lbl = ctk.CTkLabel(content, text="", width=150, height=150, text_color=THEME["text_sub"])
            img_lbl.pack(pady=(10, 5))
            
            if g.get("iconUrl"):
                AssetLoader.fetch_image_async(g["iconUrl"], f"{DIRS['cache']}/univ_{g['universeId']}.png", lambda img, lbl=img_lbl: lbl.configure(image=img, text=""), size=(150, 150))
            
            name = g["name"]
            if len(name) > 20: name = name[:20] + "..."
            ctk.CTkLabel(content, text=name, font=FontService.ui(13, "bold"), text_color=THEME["text_main"]).pack(pady=(0, 2))
            
            playing = g.get("playing", 0)
            if playing > 0:
                 ctk.CTkLabel(content, text=f"👤 {playing:,} Playing", font=FontService.ui(11), text_color=THEME["text_sub"]).pack(pady=(0, 5))

            btn_frame = ctk.CTkFrame(f, fg_color="transparent")
            btn_frame.pack(side="bottom", pady=15)
            
            if self.tool_mode == "select_only":
                ActionBtn(btn_frame, text="Select Game", width=160, height=32, type="success", command=lambda pid=g['placeId'], name=g['name']: self.select_game(pid, name)).pack()
            else:
                ActionBtn(btn_frame, text="Select", width=90, height=32, type="success", command=lambda pid=g['placeId'], name=g['name']: self.select_game(pid, name)).pack(side="left", padx=5)
                ActionBtn(btn_frame, text="Servers", width=90, height=32, type="warning", command=lambda pid=(g['placeId'] or g['universeId']): self.open_servers(pid)).pack(side="left", padx=5)
            
            col += 1
            if col > 2: 
                col = 0
                row += 1

    def select_game(self, pid, name):
        if self.tool_mode == "full":
             target = self.acc_var.get()
             self.callback(pid, target, name)
        else:
             self.callback(pid, None, name)
        self.on_close()

    def open_servers(self, pid):
        if self.tool_mode == "select_only": return 
        target_user = self.acc_var.get()
        acc = next((a for a in self.accounts if a["username"] == target_user), None)
        if target_user in ("Global Tool Only", "All Accounts"):
            acc = self.app.get_acc()
        if acc: 
            sb = ServerBrowserWindow(self.app, pid, acc, self.api, self.app.launch)
            self.app.windows.append(sb)
        else: 
            messagebox.showerror("Error", "Select a valid account.")

    def on_close(self): 
        Utils.clean_game_cache()
        self.destroy()


class UserFinderWindow(ctk.CTkToplevel):
    def __init__(self, parent, user_data, presence_data, launcher_callback):
        super().__init__(parent)
        self.title("User Found")
        self.user = user_data
        self.presence = presence_data
        self.launcher = launcher_callback
        
        self.grab_set()
        self.configure(fg_color=THEME["bg"])
        
        card = CardFrame(self, height=None)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(card, text=f"User: {self.user}", font=FontService.ui(16, "bold"), text_color=THEME["text_main"]).pack(pady=(15, 5))
        
        game_name = presence_data.get("lastLocation", "Unknown Game")
        place_id = presence_data.get("placeId")
        job_id = presence_data.get("gameId")
        
        status = "Playing" if place_id else "Online/Offline"
        status_col = THEME["success"] if place_id else THEME["text_sub"]
        ctk.CTkLabel(card, text=status, font=FontService.ui(12, "bold"), text_color=status_col).pack(pady=(0, 10))
        
        detail_frame = ctk.CTkFrame(card, fg_color="transparent")
        detail_frame.pack(fill="x", padx=20)
        
        self._add_detail(detail_frame, "Game:", game_name)
        self._add_detail(detail_frame, "Place ID:", str(place_id) if place_id else "N/A")
        
        job_display = "Hidden/Private"
        if job_id: job_display = job_id if len(str(job_id)) < 20 else f"{str(job_id)[:20]}..."
        self._add_detail(detail_frame, "Server ID:", job_display)

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        if job_id:
             ActionBtn(btn_frame, text="Join Server", width=120, type="success", command=self.join).pack(side="left", padx=5)
             ActionBtn(btn_frame, text="Copy ID", width=100, type="subtle", command=lambda: self.copy(job_id)).pack(side="left", padx=5)
        elif place_id:
             ActionBtn(btn_frame, text="Join Game", width=120, type="warning", command=self.join_place).pack(side="left", padx=5)
             ctk.CTkLabel(card, text="(Server ID is hidden, joining random server)", font=FontService.ui(10), text_color=THEME["warning"]).pack(pady=(0,10))
        else:
             ctk.CTkLabel(card, text="User is not in a joinable game.", font=FontService.ui(12), text_color=THEME["danger"]).pack(pady=10)
             
        Utils.center_window(self, 400, 350)

    def _add_detail(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, font=FontService.ui(12, "bold"), text_color=THEME["text_sub"], width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=value, font=FontService.mono(12), text_color=THEME["text_main"], anchor="w").pack(side="left")

    def join(self):
        self.launcher(None, self.presence.get("gameId"), place_override=self.presence.get("placeId"))
        self.destroy()

    def join_place(self):
        self.launcher(None, None, place_override=self.presence.get("placeId"))
        self.destroy()

    def copy(self, txt):
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.update()


class AccountManagerWindow(ctk.CTkToplevel):
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

        t_prof = self.tabs.add("Profile")
        ctk.CTkLabel(t_prof, text="Alias / Display Name", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.name_entry = ctk.CTkEntry(t_prof, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.name_entry.insert(0, acc.get("username", ""))
        self.name_entry.pack(pady=6)

        ctk.CTkLabel(t_prof, text="Group / Category", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.grp_entry = ctk.CTkEntry(t_prof, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.grp_entry.insert(0, acc.get("group", "Ungrouped"))
        self.grp_entry.pack(pady=6)

        ctk.CTkLabel(t_prof, text="Notes", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.notes_box = ctk.CTkTextbox(t_prof, width=320, height=90, fg_color=THEME["input_bg"], text_color=THEME["text_main"], corner_radius=12, border_width=1, border_color=THEME["border"], font=FontService.ui(12))
        self.notes_box.insert("0.0", acc.get("notes", ""))
        self.notes_box.pack(pady=6)

        t_game = self.tabs.add("Games & Servers")
        ctk.CTkLabel(t_game, text="Default Place ID", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.place_entry = ctk.CTkEntry(t_game, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        pid = acc.get("default_place_id", "")
        if not pid: pid = acc.get("game_id", DEFAULT_PLACE_ID)
        self.place_entry.insert(0, str(pid))
        self.place_entry.pack(pady=6)

        btn_box = ctk.CTkFrame(t_game, fg_color="transparent")
        btn_box.pack(pady=14)
        ActionBtn(btn_box, text="Open Game Browser", width=160, type="primary", command=self.open_game_browser).pack(side="left", padx=6)
        ActionBtn(btn_box, text="Open Server Browser", width=170, type="warning", command=self.open_server_browser).pack(side="left", padx=6)
        ctk.CTkLabel(t_game, text="Tip: Use Game Browser to set ID automatically.", font=FontService.ui(11), text_color=THEME["text_sub"]).pack(pady=10)

        t_data = self.tabs.add("Data")
        ctk.CTkLabel(t_data, text="User ID", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        uid_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        uid_entry.insert(0, str(acc.get("userid", "Unknown")))
        uid_entry.configure(state="readonly")
        uid_entry.pack(pady=6)
        
        ctk.CTkLabel(t_data, text=".ROBLOSECURITY Cookie", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.cookie_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.cookie_entry.insert(0, acc.get("cookie", ""))
        self.cookie_entry.pack(pady=6)

        ctk.CTkLabel(t_data, text="Proxy (http://user:pass@ip:port)", text_color=THEME["text_sub"], font=FontService.ui(12, "bold")).pack(pady=(12, 2))
        self.proxy_entry = ctk.CTkEntry(t_data, width=320, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.proxy_entry.insert(0, acc.get("proxy", ""))
        self.proxy_entry.pack(pady=6)

        ActionBtn(self, text="Save Changes", type="success", command=self.save).pack(fill="x", padx=18, pady=(0, 16))
        Utils.center_window(self, 440, 600)

    def open_game_browser(self):
        def cb(pid, target_ignored, name):
            if pid:
                self.place_entry.delete(0, "end")
                self.place_entry.insert(0, str(pid))
                self.lift()
        GameSelectorWindow(self, cb, [], self.app, is_sub_window=True, tool_mode="select_only")

    def open_server_browser(self):
        pid = self.place_entry.get().strip()
        if not pid:
            messagebox.showerror("Error", "No Place ID set.")
            return
        ServerBrowserWindow(self.app, pid, self.acc, self.api, self.app.launch)
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

        AccountStore.save(self.app.data)
        self.cb()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        FontService.init(self)
        Utils.ensure_dirs()
        ConfigService.load()
        ThemeService.apply()

        self.title(f"{APP_NAME}")
        self.geometry("1220x840")
        self.configure(fg_color=THEME["bg"])
        icon_path = os.path.join(os.getcwd(), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.api = RobloxClient(self.safe_log)
        self.browser = WebAutomation(self.safe_log)
        self.data = AccountStore.load()
        self.windows = []
        self.sidebar_expanded = True
        self.sidebar_items = []
        
        first_acc = next((a for a in self.data if "cookie" in a), None)
        if first_acc:
            HttpClient.set_cookie(first_acc["cookie"])
        
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
            font=FontService.ui(26, "bold"),
            text_color=THEME["text_main"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=VERSION,
            font=FontService.ui(11),
            text_color=THEME["text_sub"],
        ).pack(anchor="w", pady=(2, 0))
        ActionBtn(
            header,
            text="⟷",
            width=28,
            height=24,
            type="subtle",
            command=self.toggle_sidebar,
        ).pack(side="right")
        
        self.sidebar_items.append((self.side_btn(self.sidebar, "Import Accounts", self.import_data), {"pady": 7, "padx": 16}))
        self.sidebar_items.append((self.side_btn(self.sidebar, "Add Account", self.manual), {"pady": 7, "padx": 16}))
        self.sidebar_items.append((self.side_btn(self.sidebar, "Refresh All", self.refresh), {"pady": 7, "padx": 16}))
        
        def kill_all():
            if messagebox.askyesno("Panic", "Force close ALL Roblox instances?"):
                subprocess.call("taskkill /F /IM RobloxPlayerBeta.exe", shell=True)
                self.safe_log("[ALERT] Killed all Roblox processes.")
        self.sidebar_items.append((self.side_btn(self.sidebar, "Kill All Roblox", kill_all, color="danger"), {"pady": 7, "padx": 16}))
        
        self.sidebar_items.append((self.side_btn(self.sidebar, "Create Account", self.create_accounts), {"pady": 7, "padx": 16}))
        self.sidebar_items.append((self.side_btn(self.sidebar, "Settings", self.open_settings), {"pady": 7, "padx": 16}))
        
        self.status_bar = ctk.CTkLabel(
            self.sidebar, text="Ready", text_color=THEME["text_sub"], anchor="w", font=FontService.ui(11)
        )
        self.status_bar.pack(side="bottom", fill="x", padx=16, pady=(6, 6))
        self.sidebar_items.append((self.status_bar, {"side": "bottom", "fill": "x", "padx": 16, "pady": (6, 6)}))

        self.console = ctk.CTkTextbox(
            self.sidebar,
            height=160,
            corner_radius=16,
            fg_color=THEME["card_bg"],
            text_color=THEME["text_sub"],
            border_width=1,
            border_color=THEME["border"],
            font=FontService.mono(11),
        )
        self.console.pack(fill="x", padx=16, pady=(0, 16), side="bottom")
        self.sidebar_items.append((self.console, {"fill": "x", "padx": 16, "pady": (0, 16), "side": "bottom"}))

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
        Utils.center_window(self, 1220, 840)
        self.refresh_ui()
        
        threading.Thread(target=self.tracking_loop, daemon=True).start()

    def tracking_loop(self):
        while True:
            if not CONFIG.get("presence_tracking", True):
                time.sleep(5)
                continue
            try:
                interval = int(CONFIG.get("presence_interval", 10))
            except (TypeError, ValueError):
                interval = 10
            interval = max(5, min(interval, 300))
            for acc in self.data:
                if "cookie" in acc:
                    uid = acc.get("userid")
                    if uid:
                        p = self.api.check_own_presence(acc["cookie"], uid)
                        if p:
                            new_job = p.get("gameId")
                            new_place = str(p.get("placeId"))
                            
                            last_job = acc.get("last_known_job")
                            
                            if new_job and new_job != last_job:
                                acc["last_known_job"] = new_job
                                
                                game_name = p.get("lastLocation", "Unknown Game")
                                
                                WebhookService.send_launch_log(
                                    self.api, 
                                    acc['username'], 
                                    game_name, 
                                    new_place, 
                                    new_job, 
                                    uid, 
                                    manual_track=True, 
                                    robux=acc.get('robux','0')
                                )
                                self.safe_log(f"[TRACK] {acc['username']} moved to {game_name}")

            time.sleep(interval)

    def side_btn(self, parent, text, cmd, color="primary"):
        btn = ActionBtn(
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
            font=FontService.ui(12, "bold"),
            type=color
        )
        btn.pack(pady=7, padx=16)
        return btn

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            for widget, _opts in self.sidebar_items:
                widget.pack_forget()
            self.sidebar.configure(width=70)
            self.sidebar_expanded = False
        else:
            self.sidebar.configure(width=260)
            for widget, opts in self.sidebar_items:
                widget.pack(**opts)
            self.sidebar_expanded = True

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

    def create_accounts(self):
        CreateAccountWindow(self, self.start_account_creation)

    def start_account_creation(self, count, base_name, random_names, random_password, easy_password, fallback_password, birth_year, gender):
        def _task():
            for i in range(count):
                username = self.generate_username(base_name, random_names, i, count)
                password = self.generate_password(random_password, easy_password, fallback_password)
                self.safe_log(f"[INFO] Creating account {username}...")
                self.browser.open(
                    username,
                    password,
                    None,
                    "https://www.roblox.com/signup",
                    self.update_acc,
                    mode="SIGNUP",
                    signup_year=birth_year,
                    signup_gender=gender,
                )
        threading.Thread(target=_task, daemon=True).start()

    def generate_username(self, base_name, random_names, index, total):
        base = base_name or "user"
        if random_names:
            return f"{base}{Utils.random_string(6)}"
        if total > 1:
            return f"{base}{index + 1}"
        return base

    def generate_password(self, random_password, easy_password, fallback_password):
        if random_password:
            if easy_password:
                return f"{Utils.random_string(6)}{random.randint(10, 99)}"
            return f"{Utils.random_string(8)}!{random.randint(10, 99)}"
        return fallback_password or "Password123!"

    def refresh_ui(self):
        for a in self.data:
            a.setdefault("locked", False)
            a.setdefault("last_job_id", None)
            
        for w in self.scroll.winfo_children(): w.destroy()
        
        self.scroll._parent_canvas.yview_moveto(0)
        
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
                ctk.CTkLabel(gf, text=f"📂 {grp}", font=FontService.ui(14, "bold"), text_color=THEME["text_sub"]).pack(side="left", padx=6)
            self.card(acc)
            
        acc_names = [a['username'] for a in self.data if "cookie" in a]
        if not acc_names: acc_names = ["No Verified Accounts"]
        if hasattr(self, 'job_acc_menu'):
            self.job_acc_menu.configure(values=acc_names)
            if self.job_acc_var.get() not in acc_names: self.job_acc_var.set(acc_names[0])

    def card(self, acc):
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

        c = CardFrame(self.scroll, corner_radius=12, border_width=0, fg_color=THEME["card_bg"], height=40) 
        c.pack(fill="x", pady=4, padx=6) 
        
        strip_col = stat_col if is_verified else THEME["border"]
        strip = ctk.CTkFrame(c, width=4, fg_color=strip_col, corner_radius=0)
        strip.pack(side="left", fill="y")
        
        content = ctk.CTkFrame(c, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=8)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

        left_col = ctk.CTkFrame(content, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew")

        img_container = ctk.CTkFrame(left_col, fg_color="transparent")
        img_container.pack(side="left", pady=4)
        
        img_lbl = ctk.CTkLabel(img_container, text="", width=32)
        img_lbl.pack()
        
        if AssetLoader.get_cached_avatar(acc.get("userid")): 
            img_lbl.configure(image=AssetLoader.get_cached_avatar(acc.get("userid")))
        else: 
            AssetLoader.fetch_avatar_async(acc.get("userid"), f"{DIRS['cache']}/{acc.get('userid')}.png", lambda img, l=img_lbl: l.configure(image=img))

        info_col = ctk.CTkFrame(left_col, fg_color="transparent")
        info_col.pack(side="left", padx=(10, 0))

        name_row = ctk.CTkFrame(info_col, fg_color="transparent")
        name_row.pack(anchor="w")
        
        ctk.CTkLabel(name_row, text="●", text_color=stat_col, font=("Arial", 10)).pack(side="left")
        ctk.CTkLabel(name_row, text=acc['username'], font=FontService.ui(13, "bold"), text_color=THEME["text_main"]).pack(side="left", padx=(5, 0))
        
        if is_verified:
            last_game = acc.get('last_played_name', 'Unknown')
            if len(last_game) > 20: last_game = last_game[:20] + "..."
            
            ctk.CTkLabel(name_row, text=f" • R$ {acc.get('robux','0')}", font=FontService.ui(11), text_color=THEME["text_sub"]).pack(side="left")
            
            game_btn = ctk.CTkButton(name_row, text=f" • {last_game}", font=FontService.ui(11), fg_color="transparent", hover=False, text_color=THEME["link"], width=20, command=lambda: webbrowser.open(f"https://www.roblox.com/games/{acc.get('game_id')}"))
            game_btn.pack(side="left")

            ctk.CTkLabel(name_row, text=f" • {status_text}", font=FontService.ui(11), text_color=stat_col).pack(side="left")
        else:
            ctk.CTkLabel(name_row, text=" • Not Verified", font=FontService.ui(11), text_color=THEME["text_sub"]).pack(side="left")

        actions = ctk.CTkFrame(content, fg_color="transparent", width=400)
        actions.grid(row=0, column=1, sticky="e")
        actions.grid_propagate(False)
        
        if is_verified:
            h = Utils.compute_account_health(acc)
            ctk.CTkLabel(actions, text=f"❤ {h}%", font=FontService.ui(11, "bold"), text_color=THEME["success"] if h>70 else THEME["warning"]).pack(side="left", padx=(0, 10))

            ActionBtn(actions, text="Launch", width=70, height=24, type="primary", command=lambda: self.launch(acc)).pack(side="left", padx=3)
            ActionBtn(actions, text="Games", width=60, height=24, type="warning", command=lambda: self.open_game_selector_for(acc)).pack(side="left", padx=3)
            ActionBtn(actions, text="Servers", width=60, height=24, type="warning", command=lambda: self.open_server_browser_for(acc)).pack(side="left", padx=3)
            
            ActionBtn(actions, text="Track", width=50, height=24, type="subtle", command=lambda: self.track_account(acc)).pack(side="left", padx=3)
            
            ActionBtn(actions, text="🆔", width=30, height=24, type="subtle", command=lambda: self.join_job_dialog(acc)).pack(side="left", padx=3)

        else:
            ActionBtn(actions, text="Auto", width=60, height=24, type="primary", command=lambda: self.login(acc)).pack(side="left", padx=2)
            ActionBtn(actions, text="Manual", width=60, height=24, type="warning", command=self.manual).pack(side="left", padx=2)
        
        ActionBtn(actions, text="⚙", width=30, height=24, type="subtle", command=lambda: self.show_menu(acc)).pack(side="left", padx=3)
        ActionBtn(actions, text="🗑", width=30, height=24, type="danger", command=lambda: self.delete(acc)).pack(side="left", padx=3)

    def show_menu(self, acc):
        global parent
        parent = self
        AccountManagerWindow(self, acc, lambda: self.refresh_ui(), self.api, self)
        
    def open_game_selector_for(self, acc):
        def cb(pid, target_acc, game_name):
            if pid:
                acc['default_place_id'] = str(pid)
                acc['last_played_name'] = game_name
                AccountStore.save(self.data)
                self.safe_log(f"Changed Game for [{acc['username']}] to [{game_name}]")
                self.refresh_ui()
        GameSelectorWindow(self, cb, [], self, is_sub_window=True, tool_mode="select_only")

    def open_server_browser_for(self, acc):
        pid = acc.get('default_place_id') or acc.get('game_id')
        if not pid:
            messagebox.showerror("Error", "No game set for this account.")
            return
        ServerBrowserWindow(self.app if hasattr(self, 'app') else self, pid, acc, self.api, self.launch)
        
    def join_job_dialog(self, acc):
        dialog = InputDialog(self, "Join Job ID", "Paste Job ID or Deep Link:")
        res = dialog.ask()
        if res:
            clean_id = res
            if "gameInstanceId=" in res:
                try: clean_id = res.split("gameInstanceId=")[1].split("&")[0]
                except: pass
            self.launch(acc, clean_id)

    def track_account(self, acc): 
        self.safe_log(f"[INFO] Tracking status for {acc['username']}...")
        threading.Thread(target=self.refresh).start()

    def launch(self, acc, job=None, place_override=None, server_info=None):
        if acc.get("locked"):
            self.safe_log(f"[WARN] {acc['username']} is locked.")
            return

        self.safe_log(f"[INFO] Attempting to launch {acc['username']}...")
        acc['last_used'] = time.time()
        
        pid = place_override
        if not pid and job and str(job).isdigit() and len(str(job)) < 15: 
             pid = job
             job = None 
        if not pid:
             pid = acc.get('default_place_id', DEFAULT_PLACE_ID)

        if job and "placeId=" in str(job):
             try:
                 pid = job.split("placeId=")[1].split("&")[0]
                 job = job.split("gameInstanceId=")[1].split("&")[0]
             except: pass
        
        if job:
            acc["last_job_id"] = job
            acc["last_known_job"] = job 
            game_name = acc.get('last_played_name', 'Unknown Game')
        else:
             game_name = self.api.get_game_name(pid)
             acc['last_played_name'] = game_name
             acc['game_id'] = pid
             
        AccountStore.save(self.data)
        self.refresh_ui()
        WebhookService.send_launch_log(self.api, acc['username'], game_name, pid, job, acc.get('userid'), manual_track=False, robux=acc.get('robux','0'), server_info=server_info)
        threading.Thread(target=self._launch_t, args=(acc, pid, job), daemon=True).start()
        
    def _launch_t(self, acc, pid, job):
        res = self.api.launch(acc, pid, acc.get('user_agent'), job, acc.get('proxy'))
        if res is True or (isinstance(res, str) and res.startswith("Launched via")): 
            self.safe_log(f"[SUCCESS] Launched {acc['username']}")
        else: 
            self.safe_log(f"[ERROR] Launch Error: {res}")
        
    def login(self, acc): 
        threading.Thread(target=self.browser.open, args=(acc['username'], CryptoUtil.decrypt(acc.get('password')), acc.get('cookie'), "https://www.roblox.com/home", self.update_acc, "LOGIN_ONLY", acc.get('proxy')), daemon=True).start()
        
    def manual(self): 
        threading.Thread(target=self.browser.open, args=("", "", None, "https://www.roblox.com/login", self.update_acc, "LOGIN_ONLY"), daemon=True).start()
        
    def update_acc(self, u, p, c, ua):
        stats = self.api.stats(c, ua)
        name = stats.get('display_name') or u or "New Account"
        found = False
        for a in self.data:
            if a['username'] == u: 
                a.update({"cookie":c, "password":CryptoUtil.encrypt(p), "user_agent":ua})
                a.update(stats)
                found=True
        if not found: 
            self.data.append({"username":name, "password":CryptoUtil.encrypt(p), "cookie":c, "user_agent":ua, **stats})
        AccountStore.save(self.data)
        self.after(0, self.refresh_ui)
        self.safe_log(f"[SUCCESS] Saved {name}")
        
    def delete(self, acc): 
        if messagebox.askyesno("Confirm", "Delete?"): self.data.remove(acc); AccountStore.save(self.data); self.refresh_ui()
            
    def refresh(self): 
        self.safe_log("[INFO] Refreshing all accounts (Parallel)...")
        def update_task(acc):
            if "cookie" in acc:
                stats = self.api.stats(acc['cookie'], acc.get('user_agent'), acc.get('proxy'))
                acc.update(stats)
                pid = acc.get('default_place_id') or acc.get('game_id')
                if pid:
                    real_name = self.api.get_game_name(pid)
                    acc['last_played_name'] = real_name
                    acc['game_id'] = pid
                acc['health'] = Utils.compute_account_health(acc)
        def run_parallel():
            with ThreadPoolExecutor(max_workers=10) as executor: executor.map(update_task, self.data)
            self.after(0, self.refresh_ui)
            self.safe_log("[SUCCESS] Refresh complete.")
        threading.Thread(target=run_parallel, daemon=True).start()
        
    def import_data(self):
        result = ImportAccountsDialog(self).ask()
        if result:
            mode, text = result
            if mode == "User:Pass":
                for l in text.splitlines():
                    if ":" in l:
                        u, p = l.split(":", 1)
                        self.data.append({"username": u.strip(), "password": CryptoUtil.encrypt(p.strip())})
                AccountStore.save(self.data)
                self.refresh_ui()
            else:
                cookies = []
                for l in text.splitlines():
                    line = l.strip()
                    if not line:
                        continue
                    if "ROBLOSECURITY" in line and "=" in line:
                        line = line.split("=", 1)[1].strip()
                    cookies.append(line)
                if cookies:
                    self.safe_log(f"[INFO] Importing {len(cookies)} cookies...")
                    threading.Thread(target=self._import_cookie_accounts, args=(cookies,), daemon=True).start()

    def _import_cookie_accounts(self, cookies):
        for cookie in cookies:
            stats = self.api.stats(cookie, DEFAULT_UA)
            username = stats.get("display_name") if stats.get("status") == "OK" else None
            if not username:
                cookie_hint = "".join(ch for ch in cookie[-6:] if ch.isalnum()) or Utils.random_string(6)
                username = f"Cookie-{cookie_hint}"
            self.data.append({"username": username, "cookie": cookie, "user_agent": DEFAULT_UA, **stats})
            self.safe_log(f"[SUCCESS] Imported {username}")
        AccountStore.save(self.data)
        self.after(0, self.refresh_ui)
            
    def open_settings(self): SettingsWindow(self, lambda:[ConfigService.load(), self.retheme(), self.refresh_ui()])

    def retheme(self):
        ThemeService.apply()
        self.configure(fg_color=THEME["bg"])
        
    def setup_tools(self):
        t = self.tabs.tab("Game Tools")
        for w in t.winfo_children(): w.destroy()
        
        f1 = CardFrame(t, corner_radius=18, height=None) 
        f1.pack_propagate(True)
        f1.pack(fill="x", pady=10, padx=12)
        
        ctk.CTkLabel(f1, text="Direct Join (Job ID)", font=FontService.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,4))
        
        r_acc = ctk.CTkFrame(f1, fg_color="transparent")
        r_acc.pack(fill="x", padx=14, pady=(0, 8))
        
        self.job_acc_var = ctk.StringVar(value="Select Account")
        self.job_acc_menu = ctk.CTkOptionMenu(
            r_acc, 
            variable=self.job_acc_var, 
            values=[], 
            width=200, 
            fg_color=THEME["input_bg"], 
            button_color=THEME["accent"], 
            button_hover_color=THEME["accent_hover"], 
            text_color=THEME["text_main"], 
            dropdown_text_color=THEME["text_main"], 
            dropdown_fg_color=THEME["card_bg"]
        )
        self.job_acc_menu.pack(side="left", fill="x", expand=True)

        r_ids = ctk.CTkFrame(f1, fg_color="transparent")
        r_ids.pack(fill="x", padx=14, pady=(0, 14))

        self.job_place_id = ctk.CTkEntry(r_ids, placeholder_text="Place ID", height=36, width=120, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.job_place_id.pack(side="left", padx=(0, 8))
        
        self.job_id_entry = ctk.CTkEntry(r_ids, placeholder_text="Job ID (Optional)", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.job_id_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        ActionBtn(r_ids, text="Launch", width=80, type="accent", command=self.manual_job_launch).pack(side="right")
        
        f2 = CardFrame(t, corner_radius=18, height=None)
        f2.pack_propagate(True)
        f2.pack(fill="x", pady=10, padx=12)
        ctk.CTkLabel(f2, text="Global Place Override", font=FontService.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        r2 = ctk.CTkFrame(f2, fg_color="transparent"); r2.pack(fill="x", padx=14, pady=14)
        self.place = ctk.CTkEntry(r2, placeholder_text="Place ID...", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.place.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ActionBtn(r2, text="Browse", width=90, type="primary", command=self.open_game_selector).pack(side="right")

        f3 = CardFrame(t, corner_radius=18, height=None)
        f3.pack_propagate(True)
        f3.pack(fill="x", pady=10, padx=12)
        ctk.CTkLabel(f3, text="Find User Server", font=FontService.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        r3 = ctk.CTkFrame(f3, fg_color="transparent"); r3.pack(fill="x", padx=14, pady=14)
        self.pu = ctk.CTkEntry(r3, placeholder_text="Username...", height=36, fg_color=THEME["input_bg"], text_color=THEME["text_main"], border_color=THEME["border"], border_width=1, corner_radius=12)
        self.pu.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ActionBtn(r3, text="Find", width=90, type="warning", command=self.t_find).pack(side="right")
        
        f4 = CardFrame(t, corner_radius=18, height=None)
        f4.pack_propagate(True)
        f4.pack(fill="x", pady=10, padx=12)
        
        ctk.CTkLabel(f4, text="Smart Preferences (Ping Only)", font=FontService.ui(12, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=16, pady=(14,0))
        
        r4 = ctk.CTkFrame(f4, fg_color="transparent")
        r4.pack(fill="x", padx=14, pady=14)
        
        self.pref_ping = ctk.CTkOptionMenu(r4, values=["Best Connection", "Worst Connection", "Random"], width=200, fg_color=THEME["input_bg"], button_color=THEME["accent"], button_hover_color=THEME["accent_hover"], text_color=THEME["text_main"], dropdown_text_color=THEME["text_main"], dropdown_fg_color=THEME["card_bg"])
        self.pref_ping.pack(side="left", fill="x", expand=True)
        self.pref_ping.set("Best Connection")

    def manual_job_launch(self):
        user = self.job_acc_var.get()
        pid = self.job_place_id.get().strip()
        jid = self.job_id_entry.get().strip() 
        
        acc = next((a for a in self.data if a["username"] == user), None)
        
        if not acc or "cookie" not in acc:
            self.safe_log("Please select a valid verified account.")
            return

        if not pid:
             self.safe_log("Error: Place ID is required for Job ID joining.")
             return

        if not jid:
             strategy = self.pref_ping.get()
             self.safe_log(f"Auto-finding server for {pid}: {strategy}...")
             
             def _find_and_launch():
                 servers, _ = self.api.get_servers(pid, limit=100) 
                 if servers:
                     valid = [s for s in servers if not s.get("vipServerId")]
                     if valid:
                         if strategy == "Best Connection":
                             valid.sort(key=lambda x: x.get("ping", 9999))
                             target = valid[0]
                         elif strategy == "Worst Connection":
                             valid.sort(key=lambda x: x.get("ping", 0), reverse=True)
                             target = valid[0]
                         else: 
                             target = random.choice(valid)
                         
                         self.launch(acc, target["id"], place_override=pid, server_info=target)
                     else:
                         self.safe_log("No matching servers found.")
                 else:
                     self.safe_log("Failed to fetch server list.")
             threading.Thread(target=_find_and_launch).start()
        else:
             self.launch(acc, jid, place_override=pid)

    def t_find(self): 
        threading.Thread(target=self._find_t, args=(self.pu.get(),), daemon=True).start()
        
    def _find_t(self, u):
        if not u: return
        acc = self.get_acc()
        if not acc: 
             self.safe_log("No verified account available for lookup.")
             return

        self.safe_log(f"Looking up user {u}...")
        uid = self.api.get_id(u)
        if not uid:
             self.safe_log("User not found.")
             return

        p = self.api.check_own_presence(acc["cookie"], uid)
        
        self.after(0, lambda: UserFinderWindow(self, u, p if p else {}, lambda j, p: self.launch(acc, j, place_override=p)))

            
    def get_acc(self): 
        return next((a for a in self.data if "cookie" in a), None)
        
    def open_game_selector(self):
        def cb(pid, target_acc, game_name):
            if pid:
                self.place.delete(0, "end")
                self.place.insert(0, str(pid))
                
                if target_acc == "All Accounts":
                    for acc in self.data:
                        acc['default_place_id'] = str(pid)
                        acc['last_played_name'] = game_name
                    AccountStore.save(self.data)
                    self.safe_log(f"[INFO] Successfully changed all Game to [{game_name}] Place ID: [{pid}]")
                    self.refresh_ui()
                    
                elif target_acc and target_acc != "Global Tool Only":
                    acc = next((a for a in self.data if a['username'] == target_acc), None)
                    if acc: 
                        acc['default_place_id'] = str(pid)
                        acc['last_played_name'] = game_name
                        AccountStore.save(self.data)
                        self.safe_log(f"Changed Game for [{acc['username']}] to [{game_name}]")
                        self.launch(acc, pid)
                else:
                    self.safe_log(f"Selected: {game_name}")
        
        GameSelectorWindow(self, cb, self.data, self)

if __name__ == "__main__":
    app = App()
    app.mainloop()
