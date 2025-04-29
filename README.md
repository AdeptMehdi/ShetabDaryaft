# شتاب دریافت (ShetabDaryaft)

<div dir="rtl">

<p align="center">
  <img src="./img/logo.png" alt="لوگوی شتاب دریافت" width="200" />
</p>

<p align="center">
    <a href="#ویژگی‌ها">ویژگی‌ها</a> •
    <a href="#تصاویر">تصاویر</a> •
    <a href="#نصب-و-راه‌اندازی">نصب و راه‌اندازی</a> •
    <a href="#استفاده">استفاده</a> •
    <a href="#تکنولوژی‌ها">تکنولوژی‌ها</a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/زبان-Python-blue" alt="زبان" />
    <img src="https://img.shields.io/badge/رابط%20کاربری-Tkinter-blueviolet" alt="رابط کاربری" />
    <img src="https://img.shields.io/badge/پلتفرم-ویندوز-green" alt="پلتفرم" />
    <img src="https://img.shields.io/badge/زبان-فارسی-orange" alt="زبان" />
    <img src="https://img.shields.io/badge/نسخه-1.0.1-red" alt="نسخه" />
</p>

## 📝 معرفی

**شتاب دریافت** یک نرم‌افزار مدیریت دانلود مدرن و پیشرفته به زبان فارسی است که با پایتون توسعه داده شده است. این برنامه با طراحی زیبا و کاربرپسند، امکان دانلود چندنخی فایل‌ها را برای کاربران فارسی‌زبان فراهم می‌کند. رابط کاربری کاملاً فارسی با پشتیبانی از راست به چپ و فونت فارسی استاندارد، استفاده از این نرم‌افزار را برای کاربران ایرانی بسیار آسان نموده است.

## ✨ ویژگی‌ها

- **رابط کاربری مدرن و حرفه‌ای** با طراحی جدید مانند دانلود منیجرهای معروف
- **سایدبار اختصاصی** برای دسترسی سریع به امکانات برنامه
- **سه تم زیبا**:
  - **Aqua**: تم آبی اختصاصی 
  - **Dark**: تم تیره برای استفاده در شب
  - **Cyborg**: تم مدرن با رنگ‌های سبز و تیره
- **دانلود چندنخی (Multi-threaded)** برای افزایش سرعت دانلود
- **نمایش آمار دانلودها** با رنگ‌بندی متمایز برای هر وضعیت
- **قابلیت مدیریت دانلود‌ها** (شروع، توقف، ازسرگیری، حذف)
- **نمایش اطلاعات دانلود** شامل سرعت، حجم فایل و زمان باقی‌مانده
- **نوار پیشرفت رنگی** متناسب با وضعیت هر دانلود
- **آیکون‌های وضعیت** برای تشخیص سریع وضعیت دانلودها
- **تاریخچه دانلود** برای دسترسی به دانلودهای قبلی
- **امکان انتخاب اندازه فونت** برای خوانایی بهتر
- **نمایش وضعیت دانلودها** در نوار وضعیت

## 🖼️ تصاویر

<p align="center">
  <img src="assets/screenshot.png" alt="تصویر محیط نرم‌افزار" width="700" />
</p>

## 🔧 نصب و راه‌اندازی

### پیش‌نیازها

- پایتون ۳.۸ یا بالاتر
- پکیج‌های مورد نیاز (در فایل requirements.txt)

### مراحل نصب

```bash
# کلون کردن مخزن
git clone https://github.com/YourUsername/ShetabDaryaft.git

# رفتن به دایرکتوری پروژه
cd ShetabDaryaft

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای برنامه
python shetabdaryaft.py
```

## 📋 استفاده

1. **افزودن دانلود جدید**: روی دکمه "دانلود جدید" در سایدبار یا از منوی فایل کلیک کنید.
2. **مدیریت دانلود‌ها**: با انتخاب دانلود و استفاده از دکمه‌های کنترلی در نوار ابزار، دانلود‌ها را مدیریت کنید.
3. **تغییر تم**: از طریق منوی تنظیمات می‌توانید تم ظاهری برنامه را به آبی، تیره یا سایبورگ تغییر دهید.
4. **تنظیم اندازه فونت**: برای راحتی بیشتر در خواندن، می‌توانید اندازه فونت را تغییر دهید.
5. **مشاهده آمار دانلودها**: در سایدبار تعداد دانلودهای فعال، متوقف شده و تکمیل شده را مشاهده کنید.

## 🔧 تکنولوژی‌ها

- **Python**: زبان برنامه‌نویسی اصلی
- **Tkinter**: برای ایجاد رابط کاربری
- **Requests**: برای مدیریت درخواست‌های HTTP
- **Threading**: برای پیاده‌سازی دانلود چندنخی
- **Pillow**: برای مدیریت تصاویر و آیکون‌ها

## 🧩 ساختار پروژه

```
ShetabDaryaft/
├── shetabdaryaft.py     # فایل اصلی برنامه
├── requirements.txt     # وابستگی‌های پروژه
├── config.json          # تنظیمات برنامه
├── download_history.json # تاریخچه دانلودها
├── assets/              # فایل‌های گرافیکی
│   ├── logo.png
│   └── icon.ico
├── img/                 # تصاویر
├── font/                # فونت‌های فارسی
│   ├── BYekan+.ttf
│   └── BYekan+ Bold.ttf
├── temp/                # فایل‌های موقت
└── README.md            # این فایل
```

## 🔄 بروزرسانی‌ها

آخرین بروزرسانی: بهار ۱۴۰۴
- **طراحی مجدد رابط کاربری** با الهام از دانلود منیجرهای مدرن
- **اضافه شدن سایدبار** برای دسترسی سریع‌تر به امکانات
- **افزودن تم سایبورگ** با ترکیب رنگ سبز و تیره
- **بهبود نمایش آیتم‌های دانلود** با افکت‌های هاور و رنگ‌بندی مناسب
- **امکان تنظیم اندازه فونت** برای خوانایی بهتر
- **نمایش آیکون‌های وضعیت** برای تشخیص سریع‌تر وضعیت دانلودها
- **نمایش آمار دانلودها** در سایدبار

</div>

---

# ShetabDaryaft (Fast Download)

<div dir="ltr">

<p align="center">
  <img src="./img/logo.png" alt="ShetabDaryaft Logo" width="200" />
</p>

<p align="center">
    <a href="#features">Features</a> •
    <a href="#screenshots">Screenshots</a> •
    <a href="#installation">Installation</a> •
    <a href="#usage">Usage</a> •
    <a href="#technologies">Technologies</a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Language-Python-blue" alt="Language" />
    <img src="https://img.shields.io/badge/UI-Tkinter-blueviolet" alt="UI" />
    <img src="https://img.shields.io/badge/Platform-Windows-green" alt="Platform" />
    <img src="https://img.shields.io/badge/Language-Persian-orange" alt="Language" />
    <img src="https://img.shields.io/badge/Version-1.0.1-red" alt="Version" />
</p>

## 📝 Introduction

**ShetabDaryaft** (meaning "Fast Download" in Persian) is a modern and advanced download manager developed in Python with a complete Persian language interface. With its beautiful and user-friendly design, it provides multi-threaded file downloads for Persian-speaking users. The fully Persian user interface with right-to-left support and standard Persian fonts makes this software extremely easy to use for Iranian users.

## ✨ Features

- **Modern and professional UI** with new design similar to popular download managers
- **Dedicated sidebar** for quick access to application features
- **Three beautiful themes**:
  - **Aqua**: Custom blue theme
  - **Dark**: Dark theme for night use
  - **Cyborg**: Modern theme with green and dark colors
- **Multi-threaded downloading** for increased download speed
- **Download statistics display** with distinctive coloring for each status
- **Download management** (start, pause, resume, remove)
- **Download information display** including speed, file size, and remaining time
- **Colored progress bars** corresponding to each download status
- **Status icons** for quick identification of download status
- **Download history** for accessing previous downloads
- **Font size selection** for better readability
- **Download status display** in status bar

## 🖼️ Screenshots

<p align="center">
  <img src="assets/screenshot.png" alt="Application Screenshot" width="700" />
</p>

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- Required packages (in requirements.txt)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/YourUsername/ShetabDaryaft.git

# Go to project directory
cd ShetabDaryaft

# Install dependencies
pip install -r requirements.txt

# Run the application
python shetabdaryaft.py
```

## 📋 Usage

1. **Add new download**: Click on the "New Download" button in the sidebar or from the File menu.
2. **Manage downloads**: Select a download and use the control buttons in the toolbar to manage downloads.
3. **Change theme**: You can change the application's visual theme to blue, dark, or cyborg through the settings menu.
4. **Adjust font size**: For better readability, you can change the font size.
5. **View download statistics**: See the number of active, paused, and completed downloads in the sidebar.

## 🔧 Technologies

- **Python**: Main programming language
- **Tkinter**: For creating the user interface
- **Requests**: For handling HTTP requests
- **Threading**: For implementing multi-threaded downloads
- **Pillow**: For managing images and icons

## 🧩 Project Structure

```
ShetabDaryaft/
├── shetabdaryaft.py     # Main application file
├── requirements.txt     # Project dependencies
├── config.json          # Application settings
├── download_history.json # Download history
├── assets/              # Graphic files
│   ├── logo.png
│   └── icon.ico
├── img/                 # Images
├── font/                # Persian fonts
│   ├── BYekan+.ttf
│   └── BYekan+ Bold.ttf
├── temp/                # Temporary files
└── README.md            # This file
```

## 🔄 Updates

Last update: Spring 2025
- **Redesigned user interface** inspired by modern download managers
- **Added sidebar** for quicker access to features
- **Added Cyborg theme** with a combination of green and dark colors
- **Improved download item display** with hover effects and appropriate coloring
- **Font size adjustment option** for better readability
- **Status icons display** for faster status identification
- **Download statistics display** in sidebar

</div>
