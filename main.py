# This Python file uses the following encoding: utf-8
import sys
import subprocess
import os
import re
import asyncio
import aiohttp
import tarfile
import shutil
import sqlite3
from PySide6.QtGui import QGuiApplication
# from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject
from PySide6.QtCore import Signal, Slot
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QLocale
from PySide6.QtCore import QTranslator
from PySide6.QtCore import QSettings
from pathlib import Path
from queue import Queue
from threading import Thread
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import astuple
from dataclasses import asdict
import logging
import configparser
import json
import time
import threading


"""
Оскільки базовий wine потрібно компілювати що займає багато часу,
для початку використаю wine від GloriousEggroll

Також є репозиторії від:
    - Kron4ek [https://github.com/Kron4ek/Wine-Builds/releases]
Їх також вірто розглянути, оскільки GE версії орієнтовані на ігри

Ще є репозиторій https://github.com/mmtrt/WINE_AppImage
"""


APP_NAME = "WineAppsManager"
APP_SETTINGS_DIR = ".wineappsmanager"
WINE_APPS_DIR = APP_SETTINGS_DIR + "/wine-apps"
WINE_VERSIONS_DIR = APP_SETTINGS_DIR + "/wine-versions"
APPS_CONFIGURE = APP_SETTINGS_DIR + "/apps_configure.db"
WINE_VERSIONS_CACHE = APP_SETTINGS_DIR + "/wine_releases_cache.json"
WINE_CACHE_LIVE = 600 # 10 хвилин
WINE_GE_RELEASES_URL = "https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases"
PROTON_GE_RELEASES_URL = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases"
BOTTLES_RELEASES_URL = "https://api.github.com/repos/bottlesdevs/wine/releases"
WIN_VER_MAP = {
    "Windows XP": "winxp",
    "Windows 7": "win7",
    "Windows 8": "win8",
    "Windows 8.1": "win81",
    "Windows 10": "win10"
}

APP_PATH = Path(__file__).parent
APP_VERSION = (APP_PATH / "VERSION").read_text().strip()


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AppData:
    name: str = ''
    wine_prefix_path: str = ''
    wine_path: str = ''
    wine_version: str = ''
    wine_bit: str = ''
    exe_path: str = ''
    icon_path: str = ''
    settings_json: str = ''
    desktop_list: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)


class AsyncWorker(QObject):
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self.run_loop)
        self.thread.start()

    def run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        while True:
            task = self.queue.get()
            if task is None:
                break
            self.loop.run_until_complete(task)

    def add_task(self, task) -> None:
        self.queue.put(task)

    def stop(self) -> None:
        self.queue.put(None)
        self.thread.join()


class AppSettingsDB(QObject):
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path.home() / APPS_CONFIGURE
        else:
            db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    wine_prefix_path TEXT NOT NULL,
                    wine_path TEXT NOT NULL,
                    wine_version TEXT NOT NULL,
                    wine_bit TEXT NOT NULL,
                    exe_path TEXT NOT NULL,
                    icon_path TEXT,
                    settings_json TEXT,
                    desktop_list TEXT
                )
            """)

    def save_settings(self, appData: AppData) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO app_settings (name, wine_prefix_path, wine_path, wine_version, wine_bit, exe_path, icon_path, settings_json, desktop_list)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    wine_prefix_path=excluded.wine_prefix_path,
                    wine_path=excluded.wine_path,
                    wine_version=excluded.wine_version,
                    wine_bit=excluded.wine_bit,
                    exe_path=excluded.exe_path,
                    icon_path=excluded.icon_path,
                    settings_json=excluded.settings_json,
                    desktop_list=excluded.desktop_list
            """, astuple(appData))

    def get_settings(self, name: str) -> AppData:
        cursor = self.conn.execute('SELECT * FROM app_settings WHERE name=?', (name,))
        row = cursor.fetchone()
        return AppData.from_dict(dict(row)) if row else None

    def get_columns(self, columns: list) -> dict:
        columns_str = ', '.join(columns)
        cursor = self.conn.execute(f"SELECT id, {columns_str} FROM app_settings")
        rows = cursor.fetchall()
        # result = { column: [] for column in columns }
        result = {}
        for row in rows:
            row_id = row[0]
        #     for idx, column in enumerate(columns):
        #         value = row[idx + 1]
        #         result[column].append({row_id: value})
            result[row_id] = {columns[i]: row[i + 1] for i in range(len(columns))}
        return result

    def delete_settings(self, name: str) -> None:
        with self.conn:
            self.conn.execute('DELETE FROM app_settings WHERE name=?', (name,))

    def list_apps(self) -> list:
        cursor = self.conn.execute('SELECT name FROM app_settings')
        return [row[0] for row in cursor.fetchall()]


class SettingsManager(QObject):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Raven-98", APP_NAME)

    @Slot(str, str)
    def saveSetting(self, key: str, value: str) -> None:
        self.settings.setValue(key, value)

    @Slot(str, result=str)
    def loadSetting(self, key: str) -> str:
        return self.settings.value(key, "")


class AppEngine(QObject):
    updateModelSignal = Signal(list)
    error = Signal(str)
    message = Signal(str)
    # getedWineList = Signal(list)
    getedWineList = Signal(dict)
    wineStatusChanged = Signal()
    saveSettingsSignal = Signal(dict)
    _saveInstSettingsSignal = Signal(dict)
    deleteSettingsSignal = Signal(str)
    deleteAppSignal = Signal()
    appStarted = Signal(str)
    appExited = Signal(str)
    runningAppsChanged = Signal(list)
    # setedLanguage = Signal()

    def __init__(self):
        super().__init__()
        self.async_worker = AsyncWorker()
        QCoreApplication.instance().aboutToQuit.connect(self._on_about_to_quit)

        self.appDB = AppSettingsDB()
        self.running_apps: dict[str, subprocess.Popen] = {}

        # self.error.connect(self.onError)
        # self.message.connect(self.onMessage)
        self.saveSettingsSignal.connect(self.saveSettings)
        self._saveInstSettingsSignal.connect(self._save_inst_settings)
        self.deleteSettingsSignal.connect(self.deleteSettings)
        self.deleteAppSignal.connect(self.scanApplications)

## private

    @Slot()
    def _on_about_to_quit(self) -> None:
        self.async_worker.stop()

    @Slot(dict)
    def _save_inst_settings(self, data: dict) -> None:
        self.appDB.save_settings(AppData.from_dict(data))
        self.scanApplications()

    async def _install_application(self, data: dict) -> None:
        await self._inst_or_add_app(data)

    async def _add_application(self, data: dict) -> None:
        await self._inst_or_add_app(data, False)

    async def _inst_or_add_app(self, data: dict, inst: bool = True) -> None:
        if not self._validate_installation_input(data):
            return

        wine_prefix_path = self._create_prefix(data['appName'])
        wine_path = self._get_wine_path(data['wine'], data['winBit'])
        env = self._prepare_wine_env(wine_prefix_path, data['winBit'])
        self._set_wine_registry_version(wine_path, env, data['winVer'])

        exe_path = await self._install_or_add(data, wine_prefix_path, wine_path, env, inst)
        if not exe_path:
            return

        app_icon_file, usr_app_data = await self._handle_desktop_files(wine_prefix_path)
        self._save_app_metadata(data, wine_prefix_path, wine_path, exe_path, app_icon_file, usr_app_data)

    def _validate_installation_input(self, data: dict) -> bool:
        wine_prefix_path = Path.home() / WINE_APPS_DIR / data['appName']
        if wine_prefix_path.exists():
            self.error.emit(f"Application '{data['appName']}' already exists.")
            return False

        wine_path = self._get_wine_path(data['wine'], data['winBit'])
        if not wine_path:
            self.error.emit(f"Wine version {data['wine']} not found.")
            return False

        return True

    def _create_prefix(self, app_name: str) -> Path:
        wine_prefix_path = Path.home() / WINE_APPS_DIR / app_name
        wine_prefix_path.mkdir(parents=True, exist_ok=True)
        return wine_prefix_path

    async def _install_or_add(self, data, wine_prefix_path, wine_path, env, inst: bool):
        self.message.emit(f"{'Installing' if inst else 'Adding'} {data['appName']}...")

        if inst:
            exe_path = await self._run_installer(wine_prefix_path, wine_path, data['appExe'], env, data['appName'])
            if not exe_path:
                return None
            self.message.emit(f"{data['appName']} installed successfully.")
        else:
            exe_path = data['appExe']
            self.message.emit(f"{data['appName']} added successfully.")

        return exe_path

    async def _handle_desktop_files(self, wine_prefix_path: Path):
        app_icon_file = None
        usr_app_data = await self._parse_user_reg(wine_prefix_path)

        if usr_app_data:
            for file in usr_app_data["menu_list"]:
                os.remove(file)
            app_icon_file = self._find_app_icon(wine_prefix_path, usr_app_data["desktop_list"])

        return app_icon_file, usr_app_data

    def _save_app_metadata(self, data, wine_prefix_path, wine_path, exe_path, app_icon_file, usr_app_data):
        stt_data = {
            "name": data['appName'],
            "wine_prefix_path": str(wine_prefix_path),
            "wine_path": str(wine_path),
            "wine_version": str(data['wine']),
            "wine_bit": str(data['winBit']),
            "exe_path": str(exe_path),
            "icon_path": str(app_icon_file) if app_icon_file else None,
            "settings_json": None,
            "desktop_list": "|".join(usr_app_data["desktop_list"]) if usr_app_data else ""
        }
        self._saveInstSettingsSignal.emit(stt_data)

    def _prepare_wine_env(self, wine_prefix_path: Path, win_bit: str) -> dict:
        env = os.environ.copy()
        env["WINEPREFIX"] = str(wine_prefix_path)
        env["WINEARCH"] = "win32" if "32 bit" in win_bit else "win64"
        return env

    def _set_wine_registry_version(self, wine_path: str, env: dict, win_ver: str) -> None:
        try:
            wine_version = WIN_VER_MAP.get(win_ver, "win10")
            subprocess.run([wine_path, "reg", "add", "HKCU\\Software\\Wine\\WineCfg\\Config", "/v", "Version", "/d", wine_version, "/f"], env=env)
        except Exception as e:
            self.error.emit(f"Failed to set Wine version in registry: {e}")

    async def _run_installer(self, wine_prefix_path: Path, wine_path: Path, app_exe: str, env: dict, app_name: str) -> Path:
        process = None
        try:
            process = subprocess.Popen(
                        [wine_path, app_exe],
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
            process.wait()
        except Exception as e:
            self.error.emit(f"Installation failed: {e}")

        if process and process.returncode == 0:
            self.message.emit(f"{app_name} installed successfully.")
            return await self._parse_system_reg(wine_prefix_path)
        else:
            self.error.emit(f"Installer exited with code {process.returncode}.")
            if os.path.exists(wine_prefix_path):
                shutil.rmtree(wine_prefix_path)
        return None

    async def _parse_system_reg(self, wine_prefix_path: Path) -> Path:
        sys_reg_path = None
        while_count = 0
        while not sys_reg_path and while_count <= 25:
            sys_reg_path = self._get_sys_reg_exe_path(wine_prefix_path / "system.reg")
            if not sys_reg_path:
                while_count += 1
                await asyncio.sleep(1)
        return self._win_path_to_unix(sys_reg_path, wine_prefix_path)

    async def _parse_user_reg(self, wine_prefix_path: Path) -> dict | None:
        user_reg_path = wine_prefix_path / "user.reg"
        content = None
        while_count = 0
        while not content and while_count <= 25:
            try:
                with open(user_reg_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except FileNotFoundError:
                self.error.emit(f"File {user_reg_path} not found.")
                while_count += 1
                await asyncio.sleep(1)
        if not content:
            return None

        section_match = re.search(r'\[Software\\\\Wine\\\\MenuFiles\](.*?)\n\n', content, re.DOTALL)
        if not section_match:
            self.error.emit("The [Software\\Wine\\MenuFiles] partition was not found.")
            return None

        section_content = section_match.group(1)

        menu_entries = {
            "desktop_list": [],
            "menu_list": []
        }
        for line in section_content.strip().splitlines():
            match = re.match(r'"(.+?\.desktop)"="(.+?)"', line)
            if match:
                desktop_file = match.group(1).split(':')[-1].replace('\\\\', '/')
                menu_entries["desktop_list"].append(desktop_file)
            match = re.match(r'"(.+?\.menu)"="(.+?)"', line)
            if match:
                desktop_file = match.group(1).split(':')[-1].replace('\\\\', '/')
                menu_entries["menu_list"].append(desktop_file)

        return menu_entries

    def _find_app_icon(self, wine_prefix_path: Path, desktop_list: list) -> Path:
        for desktop in desktop_list:
            if "proton_shortcuts" in desktop and not str(wine_prefix_path) in desktop:
                desktop_data = self._parse_desktop_file(f"{wine_prefix_path}/drive_c{desktop}")
            else:
                desktop_data = self._parse_desktop_file(desktop)
            if "Uninstall" in desktop_data['Name']:
                continue
            if ".exe" in desktop_data['StartupWMClass']:
                if "proton_shortcuts" in desktop:
                    icons_path = Path(f"{wine_prefix_path}/drive_c/proton_shortcuts/icons/32x32/apps")
                else:
                    icons_path = Path.home() / ".local/share/icons/hicolor/32x32/apps"
                app_icon_file = next(icons_path.glob(f"*{desktop_data['Icon']}*"), None)
                return app_icon_file
        return None

    def _parse_desktop_file(self, desktop_path: str) -> dict:
        config = configparser.ConfigParser(strict=False)
        config.read(desktop_path, encoding='utf-8')
        result = {
            "Name": None,
            "Exec": None,
            "Icon": None,
            "StartupWMClass": None,
        }
        if 'Desktop Entry' in config:
            section = config['Desktop Entry']
            result['Name'] = section.get('Name')
            result['Exec'] = section.get('Exec')
            result['Icon'] = section.get('Icon')
            result['StartupWMClass'] = section.get('StartupWMClass')
        return result

    async def _delete_app(self, app_settings: AppData) -> None:
        try:
            app_name = app_settings.name
            exe_dir_ux = self._get_exe_directory(app_settings)
            uninstall_exe = self._get_uninstall_exe(app_settings, exe_dir_ux)

            self._remove_app_icons(app_settings, exe_dir_ux, uninstall_exe)
            self._remove_desktop_files(app_settings.desktop_list)

            if uninstall_exe:
                self._run_uninstaller(app_settings, exe_dir_ux, uninstall_exe)

            shutil.rmtree(app_settings.wine_prefix_path)
            self.deleteSettingsSignal.emit(app_name)
            self.message.emit(f"{app_name} deleted")
            self.deleteAppSignal.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _get_exe_directory(self, app_settings: AppData) -> str:
        exe_path = app_settings.exe_path
        return exe_path[:exe_path.rfind('/')]

    def _get_uninstall_exe(self, app_settings: AppData, exe_dir_ux: str) -> str | None:
        system_reg_path = f"{app_settings.wine_prefix_path}/system.reg"
        try:
            with open(system_reg_path, "r", encoding="utf-8") as reg_file:
                reg_data = reg_file.read()
            exe_dir_win = self._unix_path_to_win(exe_dir_ux, app_settings.wine_prefix_path).replace("\\", "\\\\")
            match = re.search(fr'"UninstallString"="\\*"?{re.escape(exe_dir_win)}([^\"]+)?"', reg_data)
            if match:
                parts = match.group(1).split("\\")
                for part in parts:
                    if part.lower().endswith(".exe"):
                        return part
        except Exception as e:
            self.error.emit(f"Error reading uninstall exe: {e}")
        return None

    def _remove_app_icons(self, app_settings: AppData, exe_dir_ux: str, uninstall_exe: str | None):
        system_reg_path = f"{app_settings.wine_prefix_path}/system.reg"
        try:
            with open(system_reg_path, "r", encoding="utf-8") as reg_file:
                reg_data = reg_file.read()
            match = re.search(fr'"DisplayIcon"="\\*"?{re.escape(self._unix_path_to_win(exe_dir_ux, app_settings.wine_prefix_path))}([^\"]+)?"', reg_data)
            if match:
                exe_name = match.group(1).split("\\")[-1].replace(".exe", "")
                self._remove_icons_by_name(exe_name)
                if uninstall_exe:
                    self._remove_icons_by_name(uninstall_exe.replace(".exe", ""))
        except Exception as e:
            self.error.emit(f"Failed to remove icons: {e}")

    def _remove_icons_by_name(self, name: str):
        icons_base_path = Path.home() / ".local/share/icons/hicolor"
        for folder in icons_base_path.glob("*/apps"):
            for icon_file in folder.glob(f"*{name}*"):
                try:
                    os.remove(icon_file)
                    self.message.emit(f"Removed {icon_file}")
                except Exception as e:
                    self.error.emit(f"Failed to remove {icon_file}: {e}")

    def _remove_desktop_files(self, desktop_list_str: str):
        for desktop_file in desktop_list_str.split('|'):
            try:
                os.remove(desktop_file)
                self.message.emit(f"Removed desktop file: {desktop_file}")
            except FileNotFoundError:
                self.message.emit(f"Desktop file not found: {desktop_file}")
            except Exception as e:
                self.error.emit(f"Failed to remove desktop file {desktop_file}: {e}")

    def _run_uninstaller(self, app_settings: AppData, exe_dir_ux: str, uninstall_exe: str):
        env = os.environ.copy()
        env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
        command = [app_settings.wine_path, f"{exe_dir_ux}/{uninstall_exe}"]
        try:
            process = subprocess.Popen(command, env=env)
            process.wait()
        except Exception as e:
            self.error.emit(f"Error running uninstaller: {e}")

    def _get_installed_apps(self) -> list:
        wine_apps_path = Path.home() / WINE_APPS_DIR

        if not wine_apps_path.is_dir():
            self.error.emit(str(wine_apps_path) + " does not exist.")
            wine_apps_path.mkdir(parents=True)
            self.message.emit(str(wine_apps_path) + " created.")
            return []

        installed_apps = []
        self.message.emit("Search for installed applications...")

        # Проходимо по кожній програмі в каталозі Wine
        for app_dir in wine_apps_path.iterdir():
            if app_dir.is_dir():
                self.message.emit(f"Found {app_dir.stem}")
            app_data = self.appDB.get_settings(app_dir.stem)
            installed_apps.append({'name': app_dir.stem, 'icon': app_data.icon_path if app_data else None })
            self.message.emit(f"{app_dir.stem} added to the list")

        return installed_apps

    def _get_db_apps(self) -> list:
        db_apps = self.appDB.get_columns(['name', 'icon_path'])
        result = []
        for key in db_apps.keys():
            result.append({'name': db_apps[key]['name'], 'icon': db_apps[key]['icon_path']})
        return result

    async def _get_wine_list(self) -> None:
        versions = self._load_cached_wine_list()
        if versions is None:
            versions = await self._get_origin_wine_list()
            self._save_cached_wine_list(versions)
        else:
            self._mark_installed_wines(versions)
        self.getedWineList.emit(versions)

    def _mark_installed_wines(self, versions: dict) -> None:
        installed_wines = self._get_installed_wines()
        for wine in versions.keys():
            if wine.split(' - ')[0] != 'system':
                versions[wine][1] = wine in installed_wines

    async def _update_wine_list(self) -> None:
        versions = await self._get_origin_wine_list()
        self._save_cached_wine_list(versions)
        self.getedWineList.emit(versions)

    async def _get_origin_wine_list(self) -> dict:
        '''
            Елемент має структуру: '{тип wine} - {версія wine}': ['{url для завантаження}', '{чи інстальовано}', "{published_at}"]
        '''
        # versions = await self._get_wine_versions()
        versions = {}
        sys_wine = self._find_system_wine()
        if sys_wine:
            versions[f"system - {sys_wine}"] = ["", True, ""]
        # versions = await self._get_wine_ge_versions()
        versions.update(await self._get_wine_ge_versions())
        versions.update(await self._get_proton_ge_versions())
        versions.update(await self._get_bottles_versions())
        return versions

    def _save_cached_wine_list(self, wine_list: dict) -> None:
        self.message.emit("Saving cached data")
        cache_file = self._get_wine_cache_file()
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(wine_list, f, indent=2)
            self.message.emit(f"Wine list cached at {cache_file}")
        except Exception as e:
            self.error.emit(f"Failed to cache wine list: {str(e)}")

    def _load_cached_wine_list(self) -> dict:
        self.message.emit("Loading cached data")
        cache_file = self._get_wine_cache_file()
        if not cache_file.exists():
            self.message.emit("No cached wine list found.")
            return None
        cache_age = time.time() - cache_file.stat().st_mtime
        max_cache_age = WINE_CACHE_LIVE
        if cache_age > max_cache_age:
            self.message.emit("Cached data is expired.")
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.error.emit(f"Failed to load cached wine list: {str(e)}")
            return None

    def _get_wine_cache_file(self) -> Path:
        return Path.home() / WINE_VERSIONS_CACHE

    def _find_system_wine(self) -> str:
        wine_path = shutil.which("wine")
        if wine_path:
            try:
                result = subprocess.run([wine_path, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.message.emit(f"Found system Wine: {version} at {wine_path}")
                    return version
                else:
                    self.error.emit("Wine found but failed to get version.")
            except Exception as e:
                self.error.emit(f"Error while checking Wine version: {e}")
        else:
            self.error.emit("System Wine not found in PATH.")
        return None

    async def _get_wine_ge_versions(self) -> dict:
        return await self._fetch_github_releases(WINE_GE_RELEASES_URL, "Wine-GE")

    async def _get_proton_ge_versions(self) -> dict:
        return await self._fetch_github_releases(PROTON_GE_RELEASES_URL, "Proton-GE")

    async def _get_bottles_versions(self) -> dict:
        return await self._fetch_github_releases(BOTTLES_RELEASES_URL, "Bottles")

    async def _fetch_github_releases(self, url: str, tp: str) -> dict:
        versions = {}
        installed_wines = self._get_installed_wines()
        page = 1
        per_page = 100  # максимум для GitHub API
        async with aiohttp.ClientSession() as session:
            while True:
                paged_url = f"{url}?per_page={per_page}&page={page}"
                async with session.get(paged_url) as response:
                    if response.status != 200:
                        self.error.emit(f"Failed to retrieve releases: {response.status}")
                        break
                    releases = await response.json()
                    if not releases:
                        break
                    for release in releases:
                        version_name = f"{tp} - {release['tag_name']}"
                        download_url = None
                        for asset in release['assets']:
                            if asset['name'].endswith('.tar.xz') or asset['name'].endswith('.tar.gz'):
                                download_url = asset['browser_download_url']
                                break
                        if not download_url:
                            self.error.emit(f"No .tar.xz or .tar.gz archive found in this release for {version_name}.")
                            continue
                        installed = version_name in installed_wines
                        published_at = release["published_at"]
                        versions[version_name] = [download_url, installed, published_at]
                    page += 1
        return versions

    async def _install_wine(self, version: str, download_url: str) -> None:
        await self._download_github_releases(version, download_url)

    async def _download_github_releases(self, version: str, download_url: str) -> None:
        self.message.emit(f"Downloading Wine version {version}...")
        save_path = self._get_wine_archive_path(version, download_url)

        if save_path.exists():
            self.message.emit(f"{version} already exists. Skipping download.")
            self._extract_tar(version)
            return

        self._prepare_archive_directory(save_path)
        success = await self._stream_download(download_url, save_path)
        if success:
            self._extract_tar(version)
        self.wineStatusChanged.emit()


    def _get_wine_archive_path(self, version: str, url: str) -> Path:
        ext = url.split('.')[-1]
        return Path.home() / WINE_VERSIONS_DIR / f"{version}.tar.{ext}"


    def _prepare_archive_directory(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)


    async def _stream_download(self, url: str, dest_path: Path) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.error.emit(f"Download failed: {response.status}")
                        return False
                    with open(dest_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
            self.message.emit(f"Downloaded to {dest_path}")
            return True
        except Exception as e:
            self.error.emit(f"Error during download: {str(e)}")
            return False

    def _extract_tar(self, version: str) -> None:
        archive_dir = Path.home() / WINE_VERSIONS_DIR
        archive_path = self._find_tar_archive(archive_dir, version)
        if not archive_path:
            self.error.emit(f"Archive for {version} not found.")
            return

        extract_to = archive_dir
        extract_to.mkdir(parents=True, exist_ok=True)

        mode = self._get_tar_mode(archive_path)
        if not mode:
            self.error.emit(f"Unsupported archive format: {archive_path.name}")
            return

        try:
            with tarfile.open(archive_path, mode) as tar:
                tar.extractall(path=extract_to, filter=self._filter_function)

            top_level_dir = self._get_top_level_dir_from_tar(archive_path, mode)
            if not top_level_dir:
                self.error.emit(f"Could not determine top-level directory in {archive_path.name}")
                return

            original_folder = extract_to / top_level_dir
            renamed_folder = extract_to / version
            if original_folder.exists():
                os.rename(original_folder, renamed_folder)

            self.message.emit(f"Extracted {version} to {extract_to}")
        except Exception as e:
            self.error.emit(f"Failed to extract {version}: {str(e)}")

    def _find_tar_archive(self, archive_dir: Path, version: str) -> Path | None:
        for ext in ["xz", "gz"]:
            candidate = archive_dir / f"{version}.tar.{ext}"
            if candidate.exists():
                return candidate
        return None

    def _get_tar_mode(self, archive_path: Path) -> str | None:
        if archive_path.suffixes[-2:] == ['.tar', '.xz']:
            return "r:xz"
        elif archive_path.suffixes[-2:] == ['.tar', '.gz']:
            return "r:gz"
        return None

    def _get_top_level_dir_from_tar(self, archive_path: Path, mode: str) -> str | None:
        try:
            with tarfile.open(archive_path, mode) as tar:
                members = tar.getmembers()
                if not members:
                    return None
                return members[0].name.split('/')[0]
        except Exception:
            return None

    def _filter_function(self, tarinfo, path):
        return tarinfo

    def _get_installed_wines(self) -> list:
        sys_wine = self._find_system_wine()

        installed_wines = []
        if sys_wine:
            installed_wines.append(sys_wine)

        wine_versions_path = Path.home() / WINE_VERSIONS_DIR

        if not wine_versions_path.is_dir():
            self.error.emit(str(wine_versions_path) + " does not exist.")
            wine_versions_path.mkdir(parents=True)
            self.message.emit(str(wine_versions_path) + " created.")
            return installed_wines

        self.message.emit("Search for installed wines...")
        for wine_dir in wine_versions_path.iterdir():
            if wine_dir.is_dir():
                self.message.emit(f"Found {wine_dir.name}")
                installed_wines.append(wine_dir.name)
        self.message.emit("Scanning complete")
        return installed_wines

    async def _uninstall_wine(self, version: str) -> None:
        wine_path = Path.home() / WINE_VERSIONS_DIR / version
        archive_path = next((Path.home() / WINE_VERSIONS_DIR).glob(f"{version}.tar.*"), None)
        try:
            if wine_path.exists():
                shutil.rmtree(wine_path)
                self.message.emit(f"Removed folder {wine_path}")
            else:
                self.message.emit(f"Folder {wine_path} does not exist")
            if archive_path.exists():
                archive_path.unlink()
                self.message.emit(f"Removed archive {archive_path}")
            else:
                self.message.emit(f"Archive {archive_path} does not exist")
        except Exception as e:
            self.error.emit(f"Failed to remove {version}: {str(e)}")
        self.wineStatusChanged.emit()

    def _get_sys_reg_exe_path(self, system_reg_path: Path) -> str:
        try:
            with open(system_reg_path, "r", encoding="utf-8") as reg_file:
                reg_data = reg_file.read()
            match = re.search(r'"DisplayIcon"="([^"]+)"', reg_data)
            if match:
                exe_path = match.group(1)
                self.message.emit(f"Executable path found: {exe_path}")
                return exe_path
            else:
                self.error.emit("Executable path not found in registry.")
                return None
        except FileNotFoundError:
            self.error.emit(f"File {system_reg_path} not found.")
            return None
        except Exception as e:
            print(f"Error reading registry file: {e}")
            return None

    def _win_path_to_unix(self, win_path: str, wine_prefix: Path) -> Path:
        path = win_path.replace("C:\\", "")
        path = path.replace("\\", "/")
        return wine_prefix / f"drive_c{path}"

    def _unix_path_to_win(self, unix_path: str, wine_prefix: str) -> str:
        path = unix_path.replace(wine_prefix, "")
        path = path.replace("/drive_c", "C:")
        path = path.replace("/", "\\")
        return path

    def _get_wine_path(self, wine_version: str, win_bit: str) -> Path:
        wine_path = None
        wine_lst = self._get_installed_wines()
        if wine_version == self._find_system_wine():
            wine_path = "wine"
        elif wine_version in wine_lst:
            # wine_bit = "wine" if "32 bit" in win_bit else "wine64"
            wine_bit = "wine"
            root_dir = Path.home() / WINE_VERSIONS_DIR / wine_version
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    if filename in wine_bit:
                        full_path = Path(dirpath) / filename
                        if os.access(full_path, os.X_OK):
                            wine_path = full_path
        return wine_path

    def _build_app_environment(self, app_settings: AppData) -> dict:
        env = os.environ.copy()
        env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
        if app_settings.settings_json:
            try:
                settings = json.loads(app_settings.settings_json)
                if "env" in settings:
                    for pair in settings["env"].split():
                        if '=' in pair:
                            key, val = pair.split('=', 1)
                            env[key] = val
            except Exception as e:
                self.error.emit(f"Failed to parse settings_json: {e}")
        if app_settings.wine_version.split(' - ')[0] == "Proton-GE":
            env["PROTONPATH"] = str(app_settings.wine_path).replace("/files/bin/wine", "")
        return env

    def _get_run_command(self, app_settings: AppData) -> list:
        if app_settings.wine_version.split(' - ')[0] == "Proton-GE":
            return [APP_PATH / "umu-run", app_settings.exe_path]
        else:
            return [app_settings.wine_path, app_settings.exe_path]

    def _prepare_winecfg_env(self, app_settings: AppData) -> dict:
        env = os.environ.copy()
        env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
        return env

    def _prepare_winetricks_env(self, app_settings: AppData) -> dict:
        env = os.environ.copy()
        env["WINE"] = str(app_settings.wine_path)
        env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
        return env

    def _is_app_running(self, appName: str) -> bool:
        proc = self.running_apps.get(appName)
        return proc is not None and proc.poll() is None

    def _monitor_process(self, appName: str, proc: subprocess.Popen):
        proc.wait()
        self.running_apps.pop(appName, None)
        self.message.emit(f"{appName} exited.")
        self.appExited.emit(appName)
        self.runningAppsChanged.emit(list(self.running_apps.keys()))

    def _find_available_languages(self) -> list:
        langs = []
        lang_dir = APP_PATH / "locales"
        for file in os.listdir(lang_dir):
            if file.endswith(".qm"):
                info = self._get_language_info_from_qm(file)
                if info:
                    langs.append(info)
        return langs

    def _get_language_info_from_qm(self, filename: str) -> dict:
        match = re.match(r'([a-z]{2})(?:_([A-Z]{2}))?\.qm', filename)
        if not match:
            return None
        lang = match.group(1)
        country = match.group(2) if match.group(2) else ""
        locale_code = f"{lang}_{country}" if country else lang
        locale = QLocale(locale_code)
        name = locale.nativeLanguageName().capitalize()
        return { "name": name, "code": locale_code}

## public

    @Slot(dict)
    def saveSettings(self, data: dict) -> None:
        self.appDB.save_settings(AppData.from_dict(data))

    @Slot(str)
    def deleteSettings(self, name: str) -> None:
        self.appDB.delete_settings(name)

    @Slot(str, result=dict)
    def getSettings(self, name: str) -> dict:
        stt = self.appDB.get_settings(name)
        return asdict(stt) if stt else asdict(AppData())
    @Slot()
    def scanApplications(self) -> None:
        try:
            installed_apps = self._get_installed_apps()
            self.updateModelSignal.emit(installed_apps)
            self.message.emit("Scanning complete")
        except FileNotFoundError:
            self.error.emit("Wine is not installed or not found in the system PATH.")
            self.updateModelSignal.emit([])

    @Slot()
    def initScanApp(self) -> None:
         installed_apps = self._get_db_apps()
         self.updateModelSignal.emit(installed_apps)
         self.message.emit("Scanning complete")

    @Slot(dict)
    def installApplication(self, data: dict) -> None:
        self.async_worker.add_task(self._install_application(data))

    @Slot(dict)
    def addApplication(self, data: dict) -> None:
        self.async_worker.add_task(self._add_application(data))

    @Slot(str)
    def deleteApp(self, appName: str) -> None:
        app_settings = self.appDB.get_settings(appName)
        self.async_worker.add_task(self._delete_app(app_settings))

    @Slot(str, str)
    def installWine(self, version: str, download_url: str) -> None:
        self.async_worker.add_task(self._install_wine(version, download_url))

    @Slot(str)
    def uninstallWine(self, version: str) -> None:
        self.async_worker.add_task(self._uninstall_wine(version))

    @Slot()
    def getWineList(self) -> None:
        # asyncio.run(self._get_wine_list())   # Маю провисання виводу діалога
        self.async_worker.add_task(self._get_wine_list())

    @Slot()
    def updateWineList(self) -> None:
        self.async_worker.add_task(self._update_wine_list())

    @Slot(result=list)
    def getInstalledWines(self) -> list:
        return self._get_installed_wines()

    @Slot(str)
    def runApp(self, appName: str) -> None:
        if appName in self.running_apps and self._is_app_running(appName):
            self.message.emit(f"{appName} is already running.")
            return
        try:
            app_settings = self.appDB.get_settings(appName)
            env = self._build_app_environment(app_settings)
            command = self._get_run_command(app_settings)            
            process = subprocess.Popen(command, env=env)
            self.running_apps[appName] = process
            self.message.emit(f"Started {appName} with PID {process.pid}")
            self.appStarted.emit(appName)
            self.runningAppsChanged.emit(list(self.running_apps.keys()))
            threading.Thread(target=self._monitor_process, args=(appName, process), daemon=True).start()
        except Exception as e:
            self.error.emit(str(e))

    @Slot(str)
    def terminateApp(self, appName: str) -> None:
        proc = self.running_apps.get(appName)
        if proc and proc.poll() is None:
            proc.terminate()
            self.message.emit(f"{appName} terminated.")
        else:
            self.message.emit(f"{appName} is not running.")

    @Slot(str)
    def runWinecfg(self, appName: str) -> None:
        try:
            app_settings = self.appDB.get_settings(appName)
            env = self._prepare_winecfg_env(app_settings)
            command = [app_settings.wine_path, "winecfg"]
            process = subprocess.Popen(command, env=env)
            self.message.emit(f"Started process with PID: {process.pid}")
        except Exception as e:
            self.error.emit(e)

    @Slot(str)
    def runWinetricks(self, appName: str) -> None:
        try:
            app_settings = self.appDB.get_settings(appName)
            env = self._prepare_winetricks_env(app_settings)
            process = subprocess.Popen(["winetricks"], env=env)
            self.message.emit(f"Started process with PID: {process.pid}")
        except Exception as e:
            self.error.emit(str(e))

    @Slot(str, str, result=str)
    def getWinePath(self, wine_version: str, win_bit: str) -> str:
        return str(self._get_wine_path(wine_version, win_bit))

    @Slot(result=bool)
    def hasRunningApps(self) -> bool:
        return any(proc.poll() is None for proc in self.running_apps.values())

    @Slot(str, result=bool)
    def isAppRunning(self, appName: str) -> bool:
        return self._is_app_running(appName)

    @Slot(result=list)
    def getLanguagesList(self) -> list:
        return self._find_available_languages()

    @Slot(str)
    def setLanguage(self, lang: str, reload: bool = True) -> None:
        if hasattr(self, "translator"):
            QGuiApplication.instance().removeTranslator(self.translator)
        self.translator = QTranslator()
        if self.translator.load(f"{lang}.qm", "locales"):
            QGuiApplication.instance().installTranslator(self.translator)
            self.message.emit(f"Language changed to {lang}")
        else:
            self.error.emit(f"Failed to load translation for {lang}")
        self.settingsManager.saveSetting("lang", lang)
        if reload:
            self._reload_ui()
        # self.setedLanguage.emit()

    @Slot(str)
    def onError(self, err: str) -> None:
        logger.error(err)

    @Slot(str)
    def onMessage(self, mess: str) -> None:
        logger.info(mess)


if __name__ == "__main__":
    import rc_resources

    app = QGuiApplication(sys.argv)
    # app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(":/img/icon.png"))

    engine = QQmlApplicationEngine()

    appEngine = AppEngine()
    settingsManager = SettingsManager()

    appEngine.settingsManager = settingsManager
    def reload_ui():
        for obj in engine.rootObjects():
            obj.deleteLater()
        engine.clearComponentCache()
        engine.load("qrc:/qml/main.qml")
        appEngine.initScanApp()
    appEngine._reload_ui = reload_ui
    # appEngine.setedLanguage.connect(reload_ui)

    currLang = settingsManager.loadSetting("lang")
    if currLang:
        appEngine.setLanguage(currLang, False)

    engine.rootContext().setContextProperty("qApp", app)
    engine.rootContext().setContextProperty("AppEngine", appEngine)
    engine.rootContext().setContextProperty("SettingsManager", settingsManager)

    engine.addImportPath("qrc:/qml")

    engine.load("qrc:/qml/main.qml")
    if not engine.rootObjects():
        sys.exit(-1)

    appEngine.initScanApp()

    sys.exit(app.exec())
