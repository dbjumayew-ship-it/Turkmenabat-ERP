# Türkmenabat ERP v0.9 — Android

Это Android-клиент для действующей ERP-системы:

`https://turkmenabat-erp.onrender.com`

## Что работает

- авторизация через существующий сервер;
- сохранение серверной сессии в WebView;
- доступ ко всем модулям ERP;
- обновление страницы свайпом вниз;
- проверка подключения к интернету;
- отдельный экран при недоступности сервера;
- корректная кнопка «Назад»;
- внешние ссылки открываются в браузере;
- HTTPS-only соединение;
- Android 7.0 и выше.

## Как добавить в GitHub

Загрузите папку `android` в корень существующего репозитория:

```text
Turkmenabat-ERP/
├── app/
├── android/
├── render.yaml
└── requirements.txt
```

## Как открыть

1. Установите Android Studio.
2. Нажмите **Open**.
3. Выберите папку `android`.
4. Дождитесь Gradle Sync.
5. Подключите Android-телефон или запустите Emulator.
6. Нажмите ▶ Run.

## Как собрать APK

В Android Studio:

```text
Build → Build Bundle(s) / APK(s) → Build APK(s)
```

Готовый файл появится примерно здесь:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Сервер

Адрес сервера находится в:

```text
android/app/src/main/res/values/strings.xml
```

Параметр:

```xml
<string name="server_url">https://turkmenabat-erp.onrender.com/</string>
```

## Следующий Android-этап

После проверки оболочки:
- нативный экран входа;
- нативный директорский дашборд;
- push-уведомления;
- сканирование QR/штрихкода;
- камера для актов брака;
- локальный офлайн-кэш;
- роли сотрудников.
