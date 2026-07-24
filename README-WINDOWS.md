# Türkmenabat ERP v1.0 — Windows Desktop

Полноценный Windows-клиент для существующей ERP-системы на Render.

## Возможности

- отдельное Windows-приложение;
- авторизация через действующий ERP-сервер;
- сохранение cookies и сессии;
- все модули ERP внутри приложения;
- кнопки Назад, Вперёд, Обновить и Главная;
- печать накладных, ПКО, РКО и других документов;
- скачивание файлов;
- проверка доступности сервера;
- безопасное HTTPS-подключение;
- внешние ссылки открываются в обычном браузере;
- локальный файл настроек;
- сборка EXE через PyInstaller;
- установщик через Inno Setup;
- GitHub Actions для автоматической Windows-сборки.

## Как добавить в GitHub

Загрузите в корень репозитория:

- папку `desktop`;
- папку `.github`.

Структура:

```text
Turkmenabat-ERP/
├── app/
├── android/
├── desktop/
├── .github/
├── render.yaml
└── requirements.txt
```

## Быстрый запуск на Windows

1. Установите Python 3.12.
2. Откройте папку `desktop`.
3. Запустите `run.bat`.

## Сборка EXE

1. Поместите файл иконки в:

```text
desktop/assets/app.ico
```

2. Запустите:

```text
desktop/build_windows.bat
```

Готовая программа:

```text
desktop/dist/Turkmenabat ERP/Turkmenabat ERP.exe
```

Важно: PySide6 WebEngine создаёт папку с дополнительными DLL. Нельзя переносить только один EXE.
Нужно переносить всю папку `Turkmenabat ERP`.

## Создание установщика

1. Установите Inno Setup.
2. Сначала выполните `build_windows.bat`.
3. Откройте:

```text
desktop/installer/TurkmenabatERP.iss
```

4. Нажмите Compile.

Установщик появится здесь:

```text
desktop/installer/output/Turkmenabat-ERP-Setup-v1.0.exe
```

## Автоматическая сборка через GitHub

После загрузки файлов откройте:

```text
GitHub → Actions → Build Windows Desktop → Run workflow
```

После завершения скачайте Artifact:

```text
Turkmenabat-ERP-Windows
```

## Настройка сервера

По умолчанию:

```text
https://turkmenabat-erp.onrender.com/
```

После первого запуска пользовательский конфиг хранится в:

```text
%APPDATA%\TurkmenabatERP\config.json
```

## Следующий этап

- улучшить адаптивность ERP для Android и Windows;
- сделать нативный директорский дашборд;
- добавить push-уведомления;
- добавить автоматическое обновление Windows-клиента;
- добавить офлайн-режим для аварийной работы.
