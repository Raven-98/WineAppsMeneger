# 🍷 WineAppsManager

**WineAppsManager** — це проста програма для керування Windows-додатками в у Linux. Додаток дозволяє легко запускати, додавати та видаляти Wine-програми.

---

## ⚙️ Можливості

- 📂  Встановлення та додавання нових Windows-додатків на власні префікси
- 🖱 Запуск додатків
- ⚙️ Зміна конфігурації запуску
- 🗑 Видалення програм
- 🍷 Керування версіями wine

---

## 🍷 Сторонні збірки Wine

Цей проєкт підтримує використання попередньо зібраних версій Wine зі сторонніх джерел:

- [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom) від GloriousEggroll
- [Wine-GE](https://github.com/GloriousEggroll/wine-ge-custom) від GloriousEggroll
- [Bottles](https://github.com/bottlesdevs/wine) збірки

**Усі заслуги за ці збірки належать їхнім авторам. Цей проєкт не поширює та не змінює ці збірки.**

📌 **ЗВЕРНІТЬ УВАГУ:** Існують передумови для використання [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom). Будь ласка, ознайомтеся на сторінці [проекту](https://github.com/GloriousEggroll/proton-ge-custom/blob/master/README.md#installation).

---

## 🛠 Встановлення

### Варіант 1 — Готовий інсталятор (рекомендується для більшості користувачів)

1. Скачайте останню версію інсталятора з розділу [Releases](https://github.com/Raven-98/WineAppsManager/releases) (файл з розширенням `.run`).

2. Дайте інсталятору права на виконання:

```bash
chmod +x WineAppsManager-<version>.run
```
3. Запустіть інсталятор:

```bash
./WineAppsManager-<version>.run
```

Інсталятор виконає всі необхідні дії: перевірить залежності, створить віртуальне оточення, встановить залежності Python і збереже програму у вашому домашньому каталозі.

### Варіант 2 — Встановлення з вихідного коду (для розробників і тестувальників)

1. Клонувати репозиторій:

```bash
git clone https://github.com/Raven-98/WineAppsManager.git
cd WineAppsManager
```

2. Створити і активувати віртуальне середовище Python:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Встановити необхідні залежності:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Зібрати `rc_resources.py` (необхідно після кожної зміни qml-файлів та файлів зображень):

```bash
 pyside6-rcc resources.qrc -o rc_resources.py 
```
5. Зкомпілювати переклади:

```bash
pyside6-lrelease translations/en_US.ts -qm locales/en_US.qm
pyside6-lrelease translations/uk_UA.ts -qm locales/uk_UA.qm
```

7. Завантажити [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher)

```bash
curl -L https://github.com/Open-Wine-Components/umu-launcher/releases/download/1.2.6/umu-launcher-1.2.6-zipapp.tar | tar -xf - && mv umu/umu-run ./umu-run && rm -rf umu
```
*Ви можете використовувати інші версії `umu-launcher`, проте наразі підтримується лише використання `umu-launcher-zipapp`*

7. Запустити програму:

```bash
python main.py
```


