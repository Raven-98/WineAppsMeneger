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
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject
from PySide6.QtCore import Signal, Slot
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from pathlib import Path
from queue import Queue
from threading import Thread
# from bs4 import BeautifulSoup
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import astuple
from dataclasses import asdict


"""
Оскільки базовий wine потрібно компілювати що займає багато часу,
для початку використаю wine-ge
"""


APP_NAME = "WineAppsManager"
APP_VERSION = "0.0.0-3"
APP_SETTINGS_DIR = ".wineappsmanager"
WINE_APPS_DIR = APP_SETTINGS_DIR + "/wine-apps"
WINE_VERSIONS_DIR = APP_SETTINGS_DIR + "/wine-versions"
# WINE_SOURCE_URL = "https://dl.winehq.org/wine/source/"
# WINE_DIST_URL = "https://dl.winehq.org/wine-builds/ubuntu/dists/"
WINE_GE_RELEASES_URL = "https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases"
WIN_VER_MAP = {
    "Windows XP": "winxp",
    "Windows 7": "win7",
    "Windows 8": "win8",
    "Windows 8.1": "win81",
    "Windows 10": "win10"
}


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
            db_path = Path.home() / APP_SETTINGS_DIR / "settings.db"
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
                    settings_json TEXT
                )
            """)

    def save_settings(self, appData: AppData) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO app_settings (name, wine_prefix_path, wine_path, wine_version, wine_bit, exe_path, icon_path, settings_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    wine_prefix_path=excluded.wine_prefix_path,
                    wine_path=excluded.wine_path,
                    wine_version=excluded.wine_version,
                    wine_bit=excluded.wine_bit,
                    exe_path=excluded.exe_path,
                    icon_path=excluded.icon_path,
                    settings_json=excluded.settings_json
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

    def __init__(self):
        super().__init__()
        self.async_worker = AsyncWorker()
        QCoreApplication.instance().aboutToQuit.connect(self._on_about_to_quit)
        self.appDB = AppSettingsDB()
        self.saveSettingsSignal.connect(self.saveSettings)
        self._saveInstSettingsSignal.connect(self._save_inst_settings)
        self.deleteSettingsSignal.connect(self.deleteSettings)
        self.deleteAppSignal.connect(self.scanApplications)

# private

    @Slot()
    def _on_about_to_quit(self) -> None:
        self.async_worker.stop()

    @Slot(dict)
    def _save_inst_settings(self, data: dict) -> None:
        self.appDB.save_settings(AppData.from_dict(data))
        self.scanApplications()

    async def _install_application(self, data: dict) -> None:
        await self._inst_add_app(data)

    async def _add_application(self, data: dict) -> None:
        await self._inst_add_app(data, False)

    async def _inst_add_app(self, data: dict, inst: bool = True):
        wine_prefix_path = Path.home() / WINE_APPS_DIR / data['appName']
        wine_path = self._get_wine_path(data['wine'], data['winBit'])
        if not wine_path:
            self.error.emit(f"Wine version {data['wine']} not found.")
            return
        if wine_prefix_path.exists():
            self.error.emit(f"Application '{data['appName']}' already exists.")
            return
        self.message.emit(f"{'Installing' if inst else 'Adding'} {data['appName']}...")
        wine_prefix_path.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["WINEPREFIX"] = str(wine_prefix_path)
        env["WINEARCH"] = "win32" if "32 bit" in data['winBit'] else "win64"
        wine_version = WIN_VER_MAP.get(data['winVer'], "win10")

        process = None
        try:
            subprocess.run([wine_path, "reg", "add", "HKCU\\Software\\Wine\\WineCfg\\Config", "/v", "Version", "/d", wine_version, "/f"], env=env)
            if inst:
                process = subprocess.Popen(
                            [wine_path, data['appExe']],
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                process.wait()
        except Exception as e:
            self.error.emit(f"{'Installation' if inst else 'Adding'} failed: {e}")

        exe_path = None
        if inst:
            if process and process.returncode == 0:
                self.message.emit(f"{data['appName']} installed successfully.")
                sys_reg_path = None
                while_count = 0
                while not sys_reg_path and while_count <= 25:
                    sys_reg_path = self._get_exe_path(wine_prefix_path / "system.reg")
                    if not sys_reg_path:
                        while_count += 1
                        await asyncio.sleep(1)
                exe_path = self._win_path_to_unix(sys_reg_path, wine_prefix_path)
            else:
                self.error.emit(f"Installer exited with code {process.returncode}.")
                if os.path.exists(wine_prefix_path):
                    shutil.rmtree(wine_prefix_path)
        else:
            self.message.emit(f"{data['appName']} added successfully.")
            exe_path = data['appExe']

        ## Шукаємо файл з іконкою
        # !!! Працює лише з програмами які були встановлені через системний wine !!!
        app_icon_file = None
        if exe_path:
            app_name = exe_path.parts[-1].replace(".exe", "")
            icons_path = Path.home() / ".local/share/icons/hicolor/32x32/apps"
            app_icon_file = next(icons_path.glob(f"*{app_name}*"), None)
        if not app_icon_file:
            self.error.emit(f"Icon for {wine_prefix_path.stem} not found")
        ##

        if exe_path:
            stt_data = {
                "name" : data['appName'],
                "wine_prefix_path" : str(wine_prefix_path),
                "wine_path" : str(wine_path),
                "wine_version" : str(data['wine']),
                "wine_bit" : str(data['winBit']),
                "exe_path" : str(exe_path),
                "icon_path" : str(app_icon_file) if app_icon_file else None,
                "settings_json" :  None
            }
            self._saveInstSettingsSignal.emit(stt_data)

    async def _delete_app(self, app_settings: AppData) -> None:
        try:
            appName = app_settings.name
            system_reg_path = f"{app_settings.wine_prefix_path}/system.reg"
            with open(system_reg_path, "r", encoding="utf-8") as reg_file:
                reg_data = reg_file.read()
            exe_dir_ux = app_settings.exe_path
            exe_dir_ux = exe_dir_ux[:exe_dir_ux.rfind('/')]
            exe_dir = self._unix_path_to_win(exe_dir_ux, app_settings.wine_prefix_path).replace("\\", "\\\\")
            escaped_dir = re.escape(exe_dir)
            match = re.search(fr'"UninstallString"="\\*"?{escaped_dir}([^"]+)"', reg_data)
            uninst_exe = None
            if match:
                uninst_path = match.group(1)
                uninst_path = uninst_path.split("\\")
                for i, part in enumerate(uninst_path):
                    if part.lower().endswith(".exe"):
                        uninst_exe = part
                        break
            ## Видалення додаткових файлів що створює системний wine
            app_exe = None
            match = re.search(fr'"DisplayIcon"="\\*"?{escaped_dir}([^"]+)"', reg_data)
            if match:
                uninst_path = match.group(1)
                uninst_path = uninst_path.split("\\")
                for i, part in enumerate(uninst_path):
                    if part.lower().endswith(".exe"):
                        app_exe = part
                        break
            if app_exe:
                app_name = app_exe.replace(".exe", "")
                icons_base_path = Path.home() / ".local/share/icons/hicolor"
                icons_path_lst = [folder for folder in os.listdir(icons_base_path) if os.path.isdir(os.path.join(icons_base_path, folder))]
                for folder in icons_path_lst:
                    icons_path = icons_base_path / folder / "apps"
                    # app_icon_file = next(icons_path.glob(f"*{app_name}*"), None)
                    app_icons_lst = list(icons_path.glob(f"*{app_name}*"))
                    for app_icon_file in app_icons_lst:
                        os.remove(app_icon_file)
                        self.message.emit(f"Removed {app_icon_file}")
                    if uninst_exe:
                        uinst_icons_lst = list(icons_path.glob(f"*{uninst_exe.replace('.exe', '')}*"))
                        for uninst_icon_file in uinst_icons_lst:
                            os.remove(uninst_icon_file)
                            self.message.emit(f"Removed {uninst_icon_file}")
            ##
            if uninst_exe:
                env = os.environ.copy()
                env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
                command = [app_settings.wine_path, f"{exe_dir_ux}/{uninst_exe}"]
                process = subprocess.Popen(command, env=env)
                process.wait()
            shutil.rmtree(app_settings.wine_prefix_path)
            self.deleteSettingsSignal.emit(appName)
            self.message.emit(f"{appName} deleted")
            self.deleteAppSignal.emit()
        except Exception as e:
            self.error.emit(e)
            # tested
            raise

    def _get_installed_apps(self) -> None:
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

    def _get_db_apps(self) -> None:
        db_apps = self.appDB.get_columns(['name', 'icon_path'])
        result = []
        for key in db_apps.keys():
            result.append({'name': db_apps[key]['name'], 'icon': db_apps[key]['icon_path']})
        return result

    async def _get_wine_list(self) -> None:
        # versions = await self._get_wine_versions()
        versions = {}
        sys_wine = self._find_system_wine()
        if sys_wine:
            versions[sys_wine] = ["system", True]
        # versions = await self._get_wine_ge_versions()
        versions.update(await self._get_wine_ge_versions())
        self.getedWineList.emit(versions)

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

### Потрібна компіляція, що максимально не зручно
    # async def _fetch_url(self, session, url):
    #     async with session.get(url) as response:
    #         response.raise_for_status()
    #         return await response.text()

    # async def _get_wine_versions(self):
    #     async with aiohttp.ClientSession() as session:
    #         main_page = await self._fetch_url(session, WINE_SOURCE_URL)
    #         soup = BeautifulSoup(main_page, "lxml")

    #         # Отримання підкаталогів версій
    #         version_dirs = [a['href'] for a in soup.find_all('a', href=True) if re.match(r'\d+\.\d+/', a['href'])]

    #         tasks = []
    #         for version_dir in version_dirs:
    #             sub_url = WINE_SOURCE_URL + version_dir
    #             tasks.append(self._fetch_url(session, sub_url))

    #         sub_pages = await asyncio.gather(*tasks)

    #         all_versions = []
    #         for sub_page in sub_pages:
    #             sub_soup = BeautifulSoup(sub_page, "lxml")
    #             versions = [
    #                 a['href'] for a in sub_soup.find_all('a', href=True)
    #                 if re.match(r'wine-\d+\.\d+(\.\d+)?\.tar\.xz', a['href'])
    #             ]
    #             all_versions.extend([v.replace('.tar.xz', '') for v in versions])

    #         versions = [v for v in sorted(set(all_versions), reverse=True) if not v.endswith('.sign')]
    #         return versions
###

### Покищо залишимо без реалізації оскільки потрібно додатково доукомплектовувати збірки

    # async def _get_wine_versions(self):
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(WINE_DIST_URL) as response:
    #             if response.status == 200:
    #                 html = await response.text()
    #                 soup = BeautifulSoup(html, 'html.parser')
    #                 # dists = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('/') and a['href'].count('/') == 1]
    #                 dists = list(set(
    #                     a['href'] for a in soup.find_all('a', href=True)
    #                     if a['href'].endswith('/') and a['href'].count('/') == 1
    #                 ))
    #                 for dist in dists:
    #                     dist_url = WINE_DIST_URL + dist
    #                     await self.check_for_stable_wine(session, dist_url)
    #             else:
    #                 self.error.emit(f"Failed to retrieve the list of distributions: {response.status}")

    # async def check_for_stable_wine(self, session, dist_url):
    #     # print(session, dist_url)
    #     binary_url = dist_url + "main/binary-amd64/"
    #     async with session.get(binary_url) as response:
    #         if response.status == 200:
    #             html = await response.text()
    #             soup = BeautifulSoup(html, 'html.parser')

    #             # wine_files = [a['href'] for a in soup.find_all('a', href=True) if 'wine-stable' in a['href']]
    #             wine_files = list(set([a['href'] for a in soup.find_all('a', href=True) if 'wine-stable-amd64' in a['href']]))

    #             if wine_files:
    #                 print(f"Found stable Wine packages in {dist_url}:")
    #                 for wine_file in wine_files:
    #                     print(f"  {binary_url}{wine_file}")
    #         else:
    #             self.error.emit(f"Failed to retrieve the binary list for {dist_url}: {response.status}")
###

    async def _get_wine_ge_versions(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(WINE_GE_RELEASES_URL) as response:
                if response.status == 200:
                    installed_wines = self._get_installed_wines()
                    releases = await response.json()
                    # versions = {release['tag_name'] : release['assets'][0]['browser_download_url'] for release in releases}
                    versions = {}
                    for release in releases:
                        version_name = release['tag_name']
                        download_url = None
                        installed = True if version_name in installed_wines else False
                        for asset in release['assets']:
                            if asset['name'].endswith('.tar.xz'):
                                download_url = asset['browser_download_url']
                                break
                        if not download_url:
                            self.error.emit("No .tar.xz archive found in this release for {version_name}.")
                            continue
                        versions[version_name] = [download_url, installed]
                    return versions
                else:
                    self.error.emit(f"Failed to retrieve releases: {response.status}")
                    return {}

    async def _download_wine_ge_version(self, version: str, download_url: str) -> None:
        self.message.emit(f"Downloading Wine GE version {version}...")
        save_path = Path.home() / WINE_VERSIONS_DIR / f"{version}.tar.xz"
        if save_path.exists():
            self.message.emit(f"{version} already exists at {save_path}. Skipping download.")
            self._extract_tar_xz(version)
            return
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        with open(save_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024 * 8)
                                if not chunk:
                                    break
                                f.write(chunk)
                        self.message.emit(f"Downloaded {version} to {save_path}")
                        self._extract_tar_xz(version)
                    else:
                        self.error.emit(f"Failed to download {version}: {response.status}")
        except Exception as e:
             self.error.emit(f"Error downloading {version}: {str(e)}")
        self.wineStatusChanged.emit()

    def _extract_tar_xz(self, version: str) -> None:
        archive_path = Path.home() / WINE_VERSIONS_DIR / f"{version}.tar.xz"
        extract_to = Path.home() / WINE_VERSIONS_DIR
        if not Path(archive_path).exists():
            self.error.emit(f"Archive {archive_path} does not exist.")
            return
        extract_to.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(path=extract_to, filter=self._filter_function)
            with tarfile.open(archive_path, "r:xz") as tar:
                members = tar.getmembers()
                top_level_directory = members[0].name.split('/')[0]
            original_folder_path = os.path.join(extract_to, top_level_directory)
            renamed_folder_path = os.path.join(extract_to, version)
            if os.path.exists(original_folder_path):
                os.rename(original_folder_path, renamed_folder_path)
            self.message.emit(f"Extracted {version} to {extract_to}")
        except tarfile.TarError as e:
            self.error.emit(f"Error extracting {version}: {str(e)}")
        except Exception as e:
            self.error.emit(f"Unexpected error extracting {version}: {str(e)}")

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
                self.message.emit(f"Found {wine_dir.stem}")
                installed_wines.append(wine_dir.stem)
        self.message.emit("Scanning complete")
        return installed_wines

    async def _uninstall_wine(self, version: str) -> None:
        wine_path = Path.home() / WINE_VERSIONS_DIR / version
        archive_path = Path.home() / WINE_VERSIONS_DIR / f"{version}.tar.xz"
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

    def _get_exe_path(self, system_reg_path: Path) -> str:
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
            wine_bit = "bin/wine" if "32 bit" in win_bit else "bin/wine64"
            wine_path = Path.home() / WINE_VERSIONS_DIR / wine_version / wine_bit
        return wine_path

# public

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
        self.async_worker.add_task(self._download_wine_ge_version(version, download_url))

    @Slot(str)
    def uninstallWine(self, version: str) -> None:
        self.async_worker.add_task(self._uninstall_wine(version))

    @Slot()
    def getWineList(self) -> None:
        # asyncio.run(self._get_wine_list())   # Маю провисання виводу діалога
        self.async_worker.add_task(self._get_wine_list())

    @Slot(result=list)
    def getInstalledWines(self) -> list:
        return self._get_installed_wines()

    @Slot(str)
    def runApp(self, appName: str) -> None:
        try:
            app_settings = self.appDB.get_settings(appName)
            env = os.environ.copy()
            env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
            command = [app_settings.wine_path, app_settings.exe_path]
            process = subprocess.Popen(command, env=env)
            self.message.emit(f"Started process with PID: {process.pid}")
        except Exception as e:
            self.error.emit(e)

    @Slot(str)
    def runWinecng(self, appName: str) -> None:
        try:
            app_settings = self.appDB.get_settings(appName)
            env = os.environ.copy()
            env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
            command = [app_settings.wine_path, "winecfg"]
            process = subprocess.Popen(command, env=env)
            self.message.emit(f"Started process with PID: {process.pid}")
        except Exception as e:
            self.error.emit(e)

    @Slot(str)
    def runWinetricks(self, appName: str) -> None:
        try:
            app_settings = self.appDB.get_settings(appName)
            env = os.environ.copy()
            env["WINE"] = str(app_settings.wine_path)
            env["WINEPREFIX"] = str(app_settings.wine_prefix_path)
            command = ["winetricks"]
            process = subprocess.Popen(command, env=env)
            self.message.emit(f"Started process with PID: {process.pid}")
        except Exception as e:
            self.error.emit(e)

    @Slot(str, str, result=str)
    def getWinePath(self, wine_version: str, win_bit: str) -> str:
        return str(self._get_wine_path(wine_version, win_bit))


    @Slot()
    def test(self): pass
        # print(self.appDB.get_columns(["name", "exe_path"]))
        # print(self._get_db_apps())
    #     wine_prefix = Path.home() / WINE_APPS_DIR / "cpu-z"
    #     p = self._get_exe_path(wine_prefix / "system.reg")
    #     print(self._win_path_to_unix(p, wine_prefix))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon("icon.png"))

    engine = QQmlApplicationEngine()
    qml_file = Path(__file__).resolve().parent / "main.qml"

    appEngine = AppEngine()
    engine.rootContext().setContextProperty("qApp", app)
    engine.rootContext().setContextProperty("AppEngine", appEngine)

    engine.load(qml_file)
    if not engine.rootObjects():
        sys.exit(-1)

    appEngine.initScanApp()

    sys.exit(app.exec())
