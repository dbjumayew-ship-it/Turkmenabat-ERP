from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QToolBar,
)


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def writable_config_path() -> Path:
    base = Path(os.getenv("APPDATA", Path.home())) / "TurkmenabatERP"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def load_config() -> dict:
    defaults_path = resource_path("config.json")
    user_path = writable_config_path()

    if not user_path.exists() and defaults_path.exists():
        user_path.write_text(defaults_path.read_text(encoding="utf-8"), encoding="utf-8")

    path = user_path if user_path.exists() else defaults_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "app_name": "Türkmenabat ERP",
            "server_url": "https://turkmenabat-erp.onrender.com/",
            "health_url": "https://turkmenabat-erp.onrender.com/health",
            "window_width": 1440,
            "window_height": 900,
            "allow_external_links": True,
        }


class ErpPage(QWebEnginePage):
    def __init__(self, server_host: str, allow_external_links: bool, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.allow_external_links = allow_external_links

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        host = url.host()
        if host and host != self.server_host and self.allow_external_links:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.server_url = self.config["server_url"]
        self.health_url = self.config.get("health_url", self.server_url)
        self.server_host = urlparse(self.server_url).hostname or ""

        self.setWindowTitle(self.config.get("app_name", "Türkmenabat ERP"))
        self.resize(
            int(self.config.get("window_width", 1440)),
            int(self.config.get("window_height", 900)),
        )

        icon_path = resource_path("assets/app.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.web = QWebEngineView(self)
        page = ErpPage(
            self.server_host,
            bool(self.config.get("allow_external_links", True)),
            self.web,
        )
        self.web.setPage(page)
        self.setCentralWidget(self.web)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.setVisible(False)

        self.status_label = QLabel("Готово")
        status = QStatusBar()
        status.addWidget(self.status_label, 1)
        status.addPermanentWidget(self.progress)
        self.setStatusBar(status)

        self._build_toolbar()
        self._connect_signals()
        self._configure_profile()

        self.server_timer = QTimer(self)
        self.server_timer.setInterval(60_000)
        self.server_timer.timeout.connect(self.check_server_status)
        self.server_timer.start()

        QTimer.singleShot(300, self.open_home)

    def _build_toolbar(self):
        toolbar = QToolBar("Навигация", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        actions = [
            ("Назад", self.web_back, QKeySequence.Back),
            ("Вперёд", self.web.forward, QKeySequence.Forward),
            ("Обновить", self.web.reload, QKeySequence.Refresh),
            ("Главная", self.open_home, QKeySequence("Ctrl+H")),
            ("Печать", self.print_page, QKeySequence.Print),
            ("Настройки", self.open_settings_file, QKeySequence("Ctrl+,")),
        ]

        for title, callback, shortcut in actions:
            action = QAction(title, self)
            action.triggered.connect(callback)
            action.setShortcut(shortcut)
            toolbar.addAction(action)

    def _connect_signals(self):
        self.web.loadStarted.connect(self.on_load_started)
        self.web.loadProgress.connect(self.on_load_progress)
        self.web.loadFinished.connect(self.on_load_finished)
        self.web.titleChanged.connect(self.on_title_changed)
        self.web.page().profile().downloadRequested.connect(self.on_download_requested)

    def _configure_profile(self):
        profile = QWebEngineProfile.defaultProfile()
        cache_dir = Path(os.getenv("LOCALAPPDATA", Path.home())) / "TurkmenabatERP" / "cache"
        storage_dir = Path(os.getenv("APPDATA", Path.home())) / "TurkmenabatERP" / "webdata"
        cache_dir.mkdir(parents=True, exist_ok=True)
        storage_dir.mkdir(parents=True, exist_ok=True)
        profile.setCachePath(str(cache_dir))
        profile.setPersistentStoragePath(str(storage_dir))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

    def open_home(self):
        self.web.load(QUrl(self.server_url))

    def web_back(self):
        if self.web.history().canGoBack():
            self.web.back()

    def on_load_started(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("Загрузка…")

    def on_load_progress(self, value: int):
        self.progress.setValue(value)

    def on_load_finished(self, success: bool):
        self.progress.setVisible(False)
        if success:
            self.status_label.setText("Подключено к ERP")
        else:
            self.status_label.setText("Ошибка подключения")
            self.show_connection_error()

    def on_title_changed(self, title: str):
        base = self.config.get("app_name", "Türkmenabat ERP")
        self.setWindowTitle(f"{title} — {base}" if title else base)

    def show_connection_error(self):
        answer = QMessageBox.warning(
            self,
            "Сервер недоступен",
            "Не удалось открыть ERP-сервер.\n\n"
            "Проверьте интернет, Render и адрес сервера.",
            QMessageBox.Retry | QMessageBox.Cancel,
            QMessageBox.Retry,
        )
        if answer == QMessageBox.Retry:
            self.open_home()

    def check_server_status(self):
        try:
            response = requests.get(self.health_url, timeout=8)
            if response.ok:
                self.status_label.setText("Сервер доступен")
            else:
                self.status_label.setText(f"Сервер: HTTP {response.status_code}")
        except requests.RequestException:
            self.status_label.setText("Сервер недоступен")

    def on_download_requested(self, download: QWebEngineDownloadRequest):
        suggested = download.downloadFileName() or "download"
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл",
            str(Path.home() / "Downloads" / suggested),
        )
        if not selected:
            download.cancel()
            return

        target = Path(selected)
        download.setDownloadDirectory(str(target.parent))
        download.setDownloadFileName(target.name)
        download.accept()
        self.status_label.setText(f"Скачивание: {target.name}")

    def print_page(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self.web.print(printer)

    def open_settings_file(self):
        path = writable_config_path()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        QMessageBox.information(
            self,
            "Настройки",
            "Файл настроек открыт.\n"
            "После изменения адреса сервера перезапустите приложение.",
        )

    def closeEvent(self, event):
        self.web.page().profile().cookieStore().deleteSessionCookies()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Türkmenabat ERP")
    app.setOrganizationName("Türkmenabat")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
