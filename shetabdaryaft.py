#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
شتاب دریافت - دانلود منیجر فارسی
تاریخ ایجاد: ۲۵ آوریل ۲۰۲۵
"""

import os
import sys
import tkinter as tk
import threading
import time
import datetime
import requests
import queue
import urllib.parse
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import re
from io import BytesIO
from urllib.parse import urlparse
import json

# تنظیمات اولیه
APP_NAME = "شتاب دریافت"
APP_VERSION = "1.0.1"
APP_PATH = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_PATH, "assets")
FONT_DIR = os.path.join(APP_PATH, "font")
HISTORY_FILE = os.path.join(APP_PATH, "download_history.json")
CONFIG_FILE = os.path.join(APP_PATH, "config.json")
TEMP_DIR = os.path.join(APP_PATH, "temp")

# فانکشن برای نمایش اطلاعات فونت‌های موجود
def print_font_info():
    """چاپ اطلاعات فونت‌های شناسایی شده"""
    try:
        import tkinter.font as tkfont
        root = tk.Tk()
        root.withdraw()  # پنجره مخفی می‌شود
        
        print("\n===== اطلاعات فونت‌های موجود =====")
        fonts = sorted(list(tkfont.families(root)))
        
        # جستجوی فونت BYekan
        yekan_fonts = [f for f in fonts if "yekan" in f.lower() or "بی یکان" in f.lower()]
        
        print(f"تعداد کل فونت‌ها: {len(fonts)}")
        if yekan_fonts:
            print(f"فونت‌های یکان یافت شده: {yekan_fonts}")
        else:
            print("هیچ فونت یکان یافت نشد")
            
        print("نمونه فونت‌ها:")
        for f in fonts[:10]:  # نمایش 10 فونت اول
            print(f"  - {f}")
            
        root.destroy()
    except Exception as e:
        print(f"خطا در بررسی فونت‌ها: {e}")

# ساخت پوشه‌های مورد نیاز
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# تنظیمات فونت
FONT_NORMAL_PATH = os.path.join(FONT_DIR, "BYekan+.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "BYekan+ Bold.ttf")

# بررسی وجود فونت‌ها
if not (os.path.exists(FONT_NORMAL_PATH) and os.path.exists(FONT_BOLD_PATH)):
    print("خطا: فونت‌های مورد نیاز یافت نشد!")

# تنظیمات پیش‌فرض
DEFAULT_CONFIG = {
    "default_download_path": os.path.expanduser("~/Downloads"),
    "max_concurrent_downloads": 3,
    "max_threads_per_download": 5,
    "use_multithreaded_download": True,
    "chunk_size": 1024 * 1024,  # 1MB
    "theme": "aqua",  # تم اختصاصی آبی
    "language": "fa",
    "rtl": True,
    "check_for_updates": True,
    "auto_start_download": True,
    "tray_icon_enabled": True,
    "minimize_to_tray": True,
    "show_notifications": True,
    "font_size": 14  # افزایش سایز پیش‌فرض فونت
}

# کلاس‌های سفارشی برای ذخیره‌سازی اطلاعات

class DownloadItem:
    """کلاس نگهداری اطلاعات یک دانلود"""
    
    def __init__(self, url, save_path, filename=None):
        self.url = url
        self.save_path = save_path
        self.filename = filename or os.path.basename(urllib.parse.unquote(urlparse(url).path))
        self.full_path = os.path.join(save_path, self.filename)
        self.status = "pending"  # pending, downloading, paused, completed, error, canceled
        self.progress = 0
        self.size = 0
        self.downloaded = 0
        self.speed = 0
        self.start_time = None
        self.end_time = None
        self.threads = []
        self.thread_data = []
        self.error_message = ""
        self.headers = {}
        self.resume_support = False
        self.id = str(time.time()).replace(".", "")
        self.last_updated = time.time()
        self.temp_files = []
        self.stop_event = threading.Event()
        self.ui_element = None
        
    def elapsed_time(self):
        if not self.start_time:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time
    
    def estimated_time(self):
        if self.speed <= 0 or self.size <= 0:
            return None
        remaining_bytes = self.size - self.downloaded
        return remaining_bytes / self.speed if remaining_bytes > 0 else 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "save_path": self.save_path,
            "filename": self.filename,
            "status": self.status,
            "size": self.size,
            "downloaded": self.downloaded,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "resume_support": self.resume_support,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data):
        item = cls(data["url"], data["save_path"], data["filename"])
        item.id = data["id"]
        item.status = data["status"]
        item.size = data["size"]
        item.downloaded = data["downloaded"]
        item.start_time = data["start_time"]
        item.end_time = data["end_time"]
        item.resume_support = data["resume_support"]
        item.error_message = data["error_message"]
        return item


class DownloadManager:
    """کلاس مدیریت دانلود‌ها"""
    
    def __init__(self, config, update_callback=None):
        self.downloads = {}
        self.active_downloads = {}
        self.config = config
        self.update_callback = update_callback
        self.download_queue = queue.Queue()
        self.download_threads = []
        self.history = []
        self.load_history()
        self.lock = threading.RLock()
        
        # راه‌اندازی نخ‌های دانلود کننده
        for i in range(config.get("max_concurrent_downloads", 3)):
            t = threading.Thread(target=self._download_worker, daemon=True, name=f"DownloadWorker-{i}")
            t.start()
            self.download_threads.append(t)
    
    def add_download(self, url, save_path, filename=None, start=True):
        """افزودن یک دانلود جدید"""
        with self.lock:
            item = DownloadItem(url, save_path, filename)
            self.downloads[item.id] = item
            if start and len(self.active_downloads) < self.config.get("max_concurrent_downloads", 3):
                self.start_download(item.id)
            else:
                self.download_queue.put(item.id)
            return item.id
    
    def start_download(self, download_id):
        """شروع دانلود"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            item = self.downloads[download_id]
            if item.status in ["downloading", "completed"]:
                return False
            
            item.status = "downloading"
            item.start_time = item.start_time or time.time()
            item.stop_event.clear()
            
            if self.config.get("use_multithreaded_download", True) and item.size > 5 * 1024 * 1024 and item.resume_support:
                # دانلود چند نخی
                self._start_multithreaded_download(item)
            else:
                # دانلود تک نخی
                self._start_single_threaded_download(item)
            
            self.active_downloads[download_id] = item
            return True
    
    def pause_download(self, download_id):
        """توقف موقت دانلود"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            item = self.downloads[download_id]
            if item.status != "downloading":
                return False
            
            item.status = "paused"
            item.stop_event.set()
            
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
                
            return True
    
    def resume_download(self, download_id):
        """ادامه دانلود متوقف شده"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            item = self.downloads[download_id]
            if item.status != "paused":
                return False
            
            # اگر نخ‌های فعال کمتر از حداکثر مجاز است، بلافاصله شروع کن
            if len(self.active_downloads) < self.config.get("max_concurrent_downloads", 3):
                return self.start_download(download_id)
            else:
                # در غیر این صورت به صف اضافه کن
                self.download_queue.put(download_id)
                return True
    
    def cancel_download(self, download_id):
        """لغو دانلود"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            item = self.downloads[download_id]
            item.status = "canceled"
            item.stop_event.set()
            
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
            
            # پاکسازی فایل‌های موقت
            for temp_file in item.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            return True
    
    def remove_download(self, download_id):
        """حذف دانلود از لیست"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            if self.downloads[download_id].status == "downloading":
                self.cancel_download(download_id)
            
            del self.downloads[download_id]
            return True
    
    def get_download(self, download_id):
        """دریافت اطلاعات یک دانلود"""
        with self.lock:
            return self.downloads.get(download_id)
    
    def get_all_downloads(self):
        """دریافت لیست تمام دانلود‌ها"""
        with self.lock:
            return list(self.downloads.values())
    
    def save_history(self):
        """ذخیره تاریخچه دانلود‌ها"""
        history_data = [item.to_dict() for item in self.history]
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except:
            print("خطا در ذخیره تاریخچه دانلود‌ها")
    
    def load_history(self):
        """بارگذاری تاریخچه دانلود‌ها"""
        if not os.path.exists(HISTORY_FILE):
            return
        
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                self.history = [DownloadItem.from_dict(item) for item in history_data]
        except:
            print("خطا در بارگذاری تاریخچه دانلود‌ها")
    
    def _download_worker(self):
        """نخ کارگر برای دانلود فایل‌ها"""
        while True:
            try:
                download_id = self.download_queue.get()
                if download_id is None:
                    break
                
                with self.lock:
                    if download_id not in self.downloads:
                        self.download_queue.task_done()
                        continue
                    
                    item = self.downloads[download_id]
                
                self.start_download(download_id)
                
                # منتظر اتمام دانلود بمان
                while item.status == "downloading" and not item.stop_event.is_set():
                    time.sleep(0.5)
                
                # فرایند تکمیل شده است
                if item.status == "completed":
                    with self.lock:
                        if download_id in self.active_downloads:
                            del self.active_downloads[download_id]
                        # افزودن به تاریخچه
                        self.history.append(item)
                        self.save_history()
                
                self.download_queue.task_done()
                
                # بررسی وجود دانلود بعدی در صف
                if not self.download_queue.empty():
                    continue
                
                # اگر صف خالی است، آیا دانلود متوقف شده‌ای وجود دارد؟
                with self.lock:
                    for dl_id, dl_item in self.downloads.items():
                        if dl_item.status == "paused":
                            self.download_queue.put(dl_id)
                            break
            
            except Exception as e:
                print(f"خطا در نخ دانلود: {str(e)}")
    
    def _get_file_info(self, url):
        """دریافت اطلاعات فایل قبل از دانلود"""
        try:
            headers = {'User-Agent': 'ShetabDaryaft/1.0'}
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            
            if response.status_code == 200:
                size = int(response.headers.get('Content-Length', 0))
                accept_ranges = response.headers.get('Accept-Ranges', '') == 'bytes'
                filename = None
                
                # تلاش برای استخراج نام فایل از هدر
                cd = response.headers.get('Content-Disposition')
                if cd:
                    filename_match = re.search(r'filename="?([^"]+)"?', cd)
                    if filename_match:
                        filename = filename_match.group(1)
                
                # اگر نام فایل در هدر نبود، از URL استخراج کن
                if not filename:
                    filename = os.path.basename(urllib.parse.unquote(urlparse(url).path))
                    if not filename:
                        filename = "download"
                
                return {
                    'size': size,
                    'accept_ranges': accept_ranges,
                    'filename': filename,
                    'headers': dict(response.headers)
                }
            
            return None
        except Exception as e:
            print(f"خطا در دریافت اطلاعات فایل: {str(e)}")
            return None
    
    def _start_single_threaded_download(self, item):
        """شروع دانلود تک‌نخی"""
        thread = threading.Thread(
            target=self._download_single_threaded,
            args=(item,),
            daemon=True,
            name=f"Download-{item.id}"
        )
        thread.start()
        item.threads.append(thread)
    
    def _start_multithreaded_download(self, item):
        """شروع دانلود چند‌نخی"""
        max_threads = self.config.get("max_threads_per_download", 5)
        chunk_size = item.size // max_threads
        
        # حداقل اندازه هر بخش: 1 مگابایت
        if chunk_size < 1024 * 1024:
            max_threads = max(1, item.size // (1024 * 1024))
            chunk_size = item.size // max_threads
        
        # ایجاد اطلاعات هر نخ
        item.thread_data = []
        for i in range(max_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < max_threads - 1 else item.size - 1
            
            # ایجاد فایل موقت برای این بخش
            temp_file = os.path.join(TEMP_DIR, f"{item.id}_part{i}")
            item.temp_files.append(temp_file)
            
            thread_info = {
                'index': i,
                'start': start,
                'end': end,
                'downloaded': 0,
                'temp_file': temp_file
            }
            
            item.thread_data.append(thread_info)
            
            # راه‌اندازی نخ برای این بخش
            thread = threading.Thread(
                target=self._download_part,
                args=(item, thread_info),
                daemon=True,
                name=f"DownloadPart-{item.id}-{i}"
            )
            thread.start()
            item.threads.append(thread)
        
        # نخ مانیتورینگ و ترکیب نتایج
        monitor_thread = threading.Thread(
            target=self._monitor_multithreaded_download,
            args=(item,),
            daemon=True,
            name=f"DownloadMonitor-{item.id}"
        )
        monitor_thread.start()
        item.threads.append(monitor_thread)
    
    def _download_single_threaded(self, item):
        """انجام دانلود تک‌نخی"""
        try:
            # دریافت اطلاعات فایل
            file_info = self._get_file_info(item.url)
            if not file_info:
                item.status = "error"
                item.error_message = "خطا در دسترسی به فایل"
                return
            
            item.size = file_info['size']
            item.resume_support = file_info['accept_ranges']
            
            # بررسی حالت ادامه دانلود
            file_exists = os.path.exists(item.full_path)
            if file_exists and item.resume_support and item.downloaded > 0:
                headers = {'Range': f'bytes={item.downloaded}-'}
                mode = 'ab'
            else:
                headers = {}
                mode = 'wb'
                item.downloaded = 0
            
            # افزودن User-Agent
            headers['User-Agent'] = 'ShetabDaryaft/1.0'
            
            with requests.get(item.url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()
                chunk_size = self.config.get("chunk_size", 1024 * 1024)
                
                with open(item.full_path, mode) as f:
                    start_time = time.time()
                    speed_calc_time = start_time
                    speed_calc_bytes = item.downloaded
                    
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if item.stop_event.is_set():
                            break
                        
                        if chunk:
                            f.write(chunk)
                            item.downloaded += len(chunk)
                            
                            # محاسبه سرعت هر ثانیه
                            current_time = time.time()
                            if current_time - speed_calc_time >= 1:
                                item.speed = (item.downloaded - speed_calc_bytes) / (current_time - speed_calc_time)
                                speed_calc_time = current_time
                                speed_calc_bytes = item.downloaded
                            
                            # محاسبه پیشرفت
                            if item.size > 0:
                                item.progress = min(100, item.downloaded / item.size * 100)
                            
                            # به‌روزرسانی UI
                            if self.update_callback:
                                self.update_callback(item)
            
            # بررسی وضعیت اتمام
            if not item.stop_event.is_set():
                item.status = "completed"
                item.progress = 100
                item.end_time = time.time()
                print(f"دانلود {item.filename} کامل شد")
            
            # به‌روزرسانی نهایی UI
            if self.update_callback:
                self.update_callback(item)
        
        except Exception as e:
            item.status = "error"
            item.error_message = str(e)
            print(f"خطا در دانلود {item.filename}: {str(e)}")
            
            if self.update_callback:
                self.update_callback(item)
    
    def _download_part(self, item, thread_info):
        """دانلود یک بخش از فایل"""
        try:
            headers = {
                'User-Agent': 'ShetabDaryaft/1.0',
                'Range': f'bytes={thread_info["start"] + thread_info["downloaded"]}-{thread_info["end"]}'
            }
            
            # حالت ادامه دانلود
            mode = 'ab' if os.path.exists(thread_info['temp_file']) and thread_info['downloaded'] > 0 else 'wb'
            
            with requests.get(item.url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()
                chunk_size = min(self.config.get("chunk_size", 1024 * 1024), 1024 * 1024)
                
                with open(thread_info['temp_file'], mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if item.stop_event.is_set():
                            break
                        
                        if chunk:
                            f.write(chunk)
                            size = len(chunk)
                            thread_info['downloaded'] += size
                            
                            with self.lock:
                                item.downloaded += size
                                # محاسبه پیشرفت
                                if item.size > 0:
                                    item.progress = min(100, item.downloaded / item.size * 100)
            
            # بخش با موفقیت دانلود شد
            thread_info['completed'] = True
        
        except Exception as e:
            thread_info['error'] = str(e)
            print(f"خطا در دانلود بخش {thread_info['index']}: {str(e)}")
    
    def _monitor_multithreaded_download(self, item):
        """مانیتور کردن و ترکیب نتایج دانلود چند نخی"""
        start_time = time.time()
        speed_calc_time = start_time
        speed_calc_bytes = item.downloaded
        
        try:
            while item.status == "downloading" and not item.stop_event.is_set():
                all_completed = True
                has_error = False
                
                for thread_info in item.thread_data:
                    if thread_info.get('error'):
                        has_error = True
                        break
                    
                    if not thread_info.get('completed', False):
                        all_completed = False
                
                # محاسبه سرعت هر ثانیه
                current_time = time.time()
                if current_time - speed_calc_time >= 1:
                    item.speed = (item.downloaded - speed_calc_bytes) / (current_time - speed_calc_time)
                    speed_calc_time = current_time
                    speed_calc_bytes = item.downloaded
                
                # به‌روزرسانی UI
                if self.update_callback:
                    self.update_callback(item)
                
                if has_error:
                    item.status = "error"
                    item.error_message = "خطا در دانلود یکی از بخش‌ها"
                    break
                
                if all_completed:
                    # ترکیب تمام بخش‌ها
                    self._combine_parts(item)
                    break
                
                time.sleep(0.5)
            
            # اگر دانلود کنسل یا متوقف شده، خروج
            if item.status in ["paused", "canceled"]:
                return
            
            # به‌روزرسانی نهایی
            if item.status != "error":
                item.status = "completed"
                item.progress = 100
                item.end_time = time.time()
                print(f"دانلود {item.filename} کامل شد")
            
            # به‌روزرسانی نهایی UI
            if self.update_callback:
                self.update_callback(item)
        
        except Exception as e:
            item.status = "error"
            item.error_message = str(e)
            print(f"خطا در مانیتورینگ دانلود {item.filename}: {str(e)}")
            
            if self.update_callback:
                self.update_callback(item)
    
    def _combine_parts(self, item):
        """ترکیب بخش‌های دانلود شده به یک فایل"""
        try:
            with open(item.full_path, 'wb') as output_file:
                for thread_info in sorted(item.thread_data, key=lambda x: x['index']):
                    if os.path.exists(thread_info['temp_file']):
                        with open(thread_info['temp_file'], 'rb') as temp_file:
                            output_file.write(temp_file.read())
            
            # پاکسازی فایل‌های موقت
            for temp_file in item.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            return True
        
        except Exception as e:
            item.status = "error"
            item.error_message = f"خطا در ترکیب بخش‌ها: {str(e)}"
            print(f"خطا در ترکیب بخش‌های دانلود {item.filename}: {str(e)}")
            return False


# توابع کمکی
def format_size(size_bytes):
    """تبدیل سایز به فرمت خوانا"""
    if size_bytes == 0:
        return "0 بایت"
    
    size_names = ["بایت", "کیلوبایت", "مگابایت", "گیگابایت", "ترابایت"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def format_speed(speed_bytes):
    """تبدیل سرعت به فرمت خوانا"""
    if speed_bytes < 1024:
        return f"{speed_bytes:.1f} بایت/ثانیه"
    elif speed_bytes < 1024 * 1024:
        return f"{speed_bytes / 1024:.1f} کیلوبایت/ثانیه"
    else:
        return f"{speed_bytes / (1024 * 1024):.1f} مگابایت/ثانیه"

def format_time(seconds):
    """تبدیل زمان به فرمت خوانا"""
    if seconds is None:
        return "نامشخص"
    
    if seconds < 60:
        return f"{int(seconds)} ثانیه"
    elif seconds < 3600:
        return f"{int(seconds / 60)} دقیقه و {int(seconds % 60)} ثانیه"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} ساعت و {minutes} دقیقه"

def generate_gradient_image(width, height, start_color, end_color):
    """ایجاد تصویر با رنگ گرادیانت"""
    base = Image.new('RGBA', (width, height), start_color)
    top = Image.new('RGBA', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (y / height)))
    
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


class ShetabDaryaftApp:
    """کلاس اصلی برنامه شتاب دریافت"""
    
    def __init__(self, root):
        self.root = root
        
        # بارگذاری مستقیم فونت‌ها در ویندوز در ابتدای کار
        self._load_fonts_directly()
        
        # تنظیمات اولیه پنجره
        self.root.title(APP_NAME)
        self.root.geometry("850x650")
        self.root.minsize(800, 600)
        
        # بارگذاری تنظیمات
        self.config = self._load_config()
        
        # تنظیم رنگ‌های اصلی تم
        self.colors = self._setup_colors()
        
        # تنظیم استایل‌های ttk
        self._setup_styles()
        
        # ایجاد مدیر دانلود
        self.download_manager = DownloadManager(self.config, self._update_download_ui)
        
        # متغیرهای عمومی
        self.selected_download_id = None
        self.download_items_ui = {}
        
        # تنظیم فونت‌ها
        self._register_fonts()
        
        # ایجاد رابط کاربری
        self._create_widgets()
        
        # به‌روزرسانی دوره‌ای
        self._start_periodic_update()
        
        # ذخیره‌سازی تنظیمات هنگام خروج
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_colors(self):
        """تنظیم رنگ‌های مورد استفاده در برنامه"""
        colors = {}
        
        # رنگ‌های پیش‌فرض
        default_colors = {
            "primary": "#00b8d4",       # آبی روشن
            "secondary": "#0288d1",     # آبی متوسط
            "accent": "#00e5ff",        # آبی فیروزه‌ای
            "bg": "#e0f7fa",            # آبی بسیار کم‌رنگ
            "text": "#263238",          # تیره برای متن
            "button_bg": "#00b8d4",     # رنگ دکمه‌ها
            "button_fg": "#ffffff",     # رنگ متن دکمه‌ها
            "button_active": "#0288d1", # رنگ دکمه‌ها در حالت فعال
            "progress_fg": "#00b8d4",   # رنگ نوار پیشرفت
            "progress_bg": "#e0f7fa"    # رنگ پس‌زمینه نوار پیشرفت
        }
        
        # تنظیم رنگ‌ها بر اساس تم انتخاب شده
        theme = self.config.get("theme", "aqua")
        
        if theme == "aqua":
            colors = default_colors
        elif theme == "dark":
            colors = {
                "primary": "#2c3e50",       # تیره
                "secondary": "#34495e",     # تیره‌تر
                "accent": "#3498db",        # آبی
                "bg": "#1a1a1a",            # تیره برای پس‌زمینه
                "text": "#ecf0f1",          # روشن برای متن
                "button_bg": "#3498db",     # آبی برای دکمه‌ها
                "button_fg": "#ffffff",     # سفید برای متن دکمه‌ها
                "button_active": "#2980b9", # آبی تیره‌تر برای دکمه‌های فعال
                "progress_fg": "#3498db",   # آبی برای نوار پیشرفت
                "progress_bg": "#2c3e50"    # تیره برای پس‌زمینه نوار پیشرفت
            }
        elif theme == "cyborg":
            colors = {
                "primary": "#212529",       # تیره برای هدر
                "secondary": "#343a40",     # تیره‌تر برای المان‌های انتخابی
                "accent": "#20c997",        # سبز برای تاکید
                "bg": "#2b3035",            # خاکستری تیره برای پس‌زمینه
                "text": "#f8f9fa",          # روشن برای متن
                "button_bg": "#20c997",     # سبز برای دکمه‌ها
                "button_fg": "#212529",     # تیره برای متن دکمه‌ها
                "button_active": "#1b9e7e", # سبز تیره‌تر برای دکمه‌های فعال
                "progress_fg": "#20c997",   # سبز برای نوار پیشرفت
                "progress_bg": "#343a40",   # تیره برای پس‌زمینه نوار پیشرفت
                "success": "#28a745",       # سبز برای تکمیل
                "warning": "#ffc107",       # زرد برای هشدار
                "danger": "#dc3545",        # قرمز برای خطا
                "info": "#17a2b8",          # آبی برای اطلاعات
                "header_bg": "#212529",     # تیره برای هدر
                "list_item_bg": "#343a40",  # تیره‌تر برای آیتم‌های لیست
                "list_item_hover": "#495057" # خاکستری روشن‌تر برای هاور
            }
        else:
            # استفاده از رنگ‌های پیش‌فرض برای سایر تم‌ها
            colors = default_colors
        
        return colors
    
    def _setup_styles(self):
        """تنظیم استایل‌های ttk"""
        style = ttk.Style()
        
        # تنظیم رنگ پس‌زمینه اصلی
        self.root.configure(background=self.colors["bg"])
        
        # تنظیم استایل‌های ttk
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TButton", background=self.colors["button_bg"], foreground=self.colors["button_fg"])
        style.map("TButton", background=[("active", self.colors["button_active"])])
        style.configure("TLabelframe", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Horizontal.TProgressbar", background=self.colors["progress_fg"], troughcolor=self.colors["progress_bg"])
        style.configure("TEntry", fieldbackground="white", foreground=self.colors["text"])
        style.configure("TCombobox", fieldbackground="white", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Treeview", background=self.colors["bg"], fieldbackground=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Treeview.Heading", background=self.colors["primary"], foreground=self.colors["button_fg"])
        
        # تنظیم استایل برای آیتم انتخاب شده
        style.configure("Selected.TFrame", background=self.colors["secondary"])
        
        # ذخیره استایل برای استفاده در جاهای دیگر
        self.style = style
    
    def _load_fonts_directly(self):
        """بارگذاری مستقیم فونت‌های فارسی در ویندوز"""
        if os.name != "nt":
            return
            
        try:
            import ctypes
            
            # فونت‌های مورد نیاز
            font_files = ["BYekan+.ttf", "BYekan+ Bold.ttf"]
            
            # بارگذاری هر فونت
            for font_file in font_files:
                font_path = os.path.join(FONT_DIR, font_file)
                if not os.path.exists(font_path):
                    continue
                    
                # بارگذاری فونت در ویندوز
                try:
                    result = ctypes.windll.gdi32.AddFontResourceW(font_path)
                    print(f"فونت '{font_file}' با نتیجه {result} بارگذاری شد")
                except Exception as e:
                    print(f"خطا در بارگذاری فونت {font_file}: {e}")
            
            # اعلام تغییر فونت به سیستم
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)  # WM_FONTCHANGE
            
        except Exception as e:
            print(f"خطا در بارگذاری مستقیم فونت: {e}")
    
    def _register_fonts(self):
        """ثبت فونت‌های برنامه"""
        try:
            import tkinter.font as tkfont
            
            # تعیین سایز فونت با اندازه بزرگتر
            font_size = self.config.get("font_size", 15)  # افزایش سایز بیشتر
            
            # فایل‌های فونت
            font_yekan = "BYekan+.ttf"
            font_yekan_bold = "BYekan+ Bold.ttf"
            
            # مسیرهای کامل فونت‌ها
            yekan_path = os.path.join(FONT_DIR, font_yekan)
            yekan_bold_path = os.path.join(FONT_DIR, font_yekan_bold)
            
            # ثبت مستقیم فونت‌ها
            print("در حال ثبت فونت‌ها در سیستم...")
            
            # ثبت اجباری فونت‌ها در ویندوز
            if os.name == "nt":
                try:
                    # ثبت مستقیم فونت‌ها در ویندوز
                    for path in [yekan_path, yekan_bold_path]:
                        if os.path.exists(path):
                            # ثبت فونت در سیستم
                            result = ctypes.windll.gdi32.AddFontResourceW(path)
                            print(f"نتیجه ثبت فونت {os.path.basename(path)}: {result}")
                            
                            # اطلاع‌رسانی تغییر فونت به سیستم
                            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                except Exception as e:
                    print(f"خطا در ثبت سیستمی فونت: {e}")
            
            print("در حال تلاش برای یافتن فونت‌ها در سیستم...")
            available_fonts = sorted(list(tkfont.families()))
            print(f"فونت‌های موجود: {available_fonts[:5]}... (و {len(available_fonts)-5} مورد دیگر)")
            
            # روش مستقیم‌تر - استفاده از فونت با نام کامل
            font_family = "BYekan+"
            font_bold_family = "BYekan+ Bold"
            
            # ساخت فونت‌ها با رویکرد جدید
            print(f"ساخت آبجکت‌های فونت با خانواده {font_family}...")
            try:
                self.font_normal = tkfont.Font(family=font_family, size=font_size, weight="normal")
                self.font_bold = tkfont.Font(family=font_bold_family, size=font_size, weight="bold")
                self.font_header = tkfont.Font(family=font_bold_family, size=font_size+4, weight="bold")
                self.font_big = tkfont.Font(family=font_bold_family, size=font_size+8, weight="bold")
                print("آبجکت‌های فونت با موفقیت ساخته شدند")
            except Exception as e:
                print(f"خطا در ساخت آبجکت‌های فونت: {e}")
                # استفاده از فونت پشتیبان
                print("استفاده از فونت پشتیبان...")
                self.font_normal = tkfont.Font(family="Arial", size=font_size)
                self.font_bold = tkfont.Font(family="Arial", size=font_size, weight="bold")
                self.font_header = tkfont.Font(family="Arial", size=font_size+4, weight="bold")
                self.font_big = tkfont.Font(family="Arial", size=font_size+8, weight="bold")
                font_family = "Arial"  # استفاده از فونت پشتیبان
            
            # تنظیم عمیق فونت برای همه عناصر
            # 1. تنظیم گزینه‌های پایه تکینتر
            print("تنظیم گزینه‌های فونت پایه...")
            for option in ["*Font", "*TButton.font", "*TLabel.font", "*Menu.font", "*Text.font", "*TEntry.font", "*TCombobox.font"]:
                self.root.option_add(option, self.font_normal)
            
            # 2. تنظیم استایل‌های ttk
            print("تنظیم استایل‌های ttk...")
            for style_name in [
                "TButton", "TLabel", "TEntry", "TFrame", "TNotebook", "TNotebook.Tab", 
                "TLabelframe", "TLabelframe.Label", "TCombobox", "Treeview", "Treeview.Heading", 
                "TCheckbutton", "TRadiobutton", "TPanedwindow"]:
                try:
                    self.style.configure(style_name, font=(font_family, font_size))
                except Exception as e:
                    print(f"خطا در تنظیم استایل {style_name}: {e}")
            
            # 3. تنظیم فونت برای همه ویجت‌های موجود
            print("تنظیم فونت برای ویجت‌های موجود...")
            def set_font_for_all_widgets(widget):
                try:
                    widget.configure(font=self.font_normal)
                except:
                    pass
                    
                # بازگشتی برای همه فرزندان
                for child in widget.winfo_children():
                    set_font_for_all_widgets(child)
                    
            # اجرای تابع برای همه ویجت‌ها
            set_font_for_all_widgets(self.root)
            
            print("ثبت فونت‌ها با موفقیت انجام شد")
            
        except Exception as e:
            print(f"خطا در ثبت فونت‌ها: {str(e)}")
    
    def _create_widgets(self):
        """ایجاد المان‌های رابط کاربری"""
        # تنظیم حاشیه اصلی
        self.root.configure(padx=0, pady=0)
        
        # قاب اصلی
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # ایجاد هدر با طراحی مدرن
        header_frame = tk.Frame(self.main_frame, bg=self.colors["primary"], height=60)
        header_frame.pack(fill="x", pady=0, padx=0)
        header_frame.pack_propagate(False)
        
        # لوگو و عنوان در هدر
        app_title = tk.Label(header_frame, text=f"{APP_NAME}", 
                           font=self.font_big, bg=self.colors["primary"], 
                           fg=self.colors["text"], padx=15)
        app_title.pack(side="right", pady=10)
        
        # ساختار اصلی - ترکیب ساید بار و محتوا
        content_frame = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL, 
                                    bg=self.colors["bg"], sashwidth=2,
                                    sashrelief=tk.RIDGE)
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # ساید بار در سمت راست
        sidebar_frame = tk.Frame(content_frame, bg=self.colors["secondary"], width=200)
        sidebar_frame.pack_propagate(False)
        content_frame.add(sidebar_frame)
        
        # پنل اصلی
        main_panel = tk.Frame(content_frame, bg=self.colors["bg"])
        content_frame.add(main_panel)
        content_frame.paneconfigure(sidebar_frame, minsize=180)
        
        # دکمه‌های منو در ساید بار
        sidebar_title = tk.Label(sidebar_frame, text="منو", font=self.font_header,
                              bg=self.colors["secondary"], fg=self.colors["text"],
                              pady=10)
        sidebar_title.pack(fill="x", padx=10)
        
        # استایل دکمه‌های منو
        menu_button_style = {
            "bg": self.colors["secondary"],
            "fg": self.colors["text"],
            "activebackground": self.colors["accent"],
            "activeforeground": self.colors["button_fg"],
            "relief": tk.FLAT,
            "borderwidth": 0,
            "padx": 10,
            "pady": 8,
            "font": self.font_normal,
            "anchor": "w",
            "width": 20,
            "cursor": "hand2"
        }
        
        # دکمه دانلود جدید
        self.new_download_btn = tk.Button(sidebar_frame, text="⬇️ دانلود جدید", 
                                      command=self._show_new_download_dialog,
                                      **menu_button_style)
        self.new_download_btn.pack(fill="x", pady=2)
        
        # دکمه تنظیمات
        settings_btn = tk.Button(sidebar_frame, text="⚙️ تنظیمات", 
                               command=self._show_settings_dialog,
                               **menu_button_style)
        settings_btn.pack(fill="x", pady=2)
        
        # دکمه درباره
        about_btn = tk.Button(sidebar_frame, text="ℹ️ درباره برنامه", 
                           command=self._show_about_dialog,
                           **menu_button_style)
        about_btn.pack(fill="x", pady=2)
        
        # فضای خالی
        tk.Frame(sidebar_frame, height=20, bg=self.colors["secondary"]).pack(fill="x")
        
        # بخش دانلودهای فعال
        active_label = tk.Label(sidebar_frame, text="وضعیت دانلودها", font=self.font_bold,
                              bg=self.colors["secondary"], fg=self.colors["text"],
                              pady=5)
        active_label.pack(fill="x", padx=10)
        
        # ایجاد قاب برای نمایش خلاصه وضعیت
        stats_frame = tk.Frame(sidebar_frame, bg=self.colors["secondary"], padx=10)
        stats_frame.pack(fill="x", pady=5)
        
        # آمار دانلودها
        self.active_count_label = tk.Label(stats_frame, text="در حال دانلود: 0", 
                                       font=self.font_normal, 
                                       bg=self.colors["secondary"], 
                                       fg=self.colors["accent"],
                                       anchor="w")
        self.active_count_label.pack(fill="x", pady=2)
        
        self.completed_count_label = tk.Label(stats_frame, text="تکمیل شده: 0", 
                                          font=self.font_normal, 
                                          bg=self.colors["secondary"], 
                                          fg=self.colors.get("success", self.colors["accent"]),
                                          anchor="w")
        self.completed_count_label.pack(fill="x", pady=2)
        
        self.paused_count_label = tk.Label(stats_frame, text="متوقف شده: 0", 
                                      font=self.font_normal, 
                                      bg=self.colors["secondary"], 
                                      fg=self.colors.get("warning", self.colors["accent"]),
                                      anchor="w")
        self.paused_count_label.pack(fill="x", pady=2)
        
        self.error_count_label = tk.Label(stats_frame, text="خطا: 0", 
                                     font=self.font_normal, 
                                     bg=self.colors["secondary"], 
                                     fg=self.colors.get("danger", self.colors["accent"]),
                                     anchor="w")
        self.error_count_label.pack(fill="x", pady=2)
        
        # در انتهای ساید بار، اطلاعات نسخه
        version_label = tk.Label(sidebar_frame, text=f"نسخه {APP_VERSION}", 
                              font=(self.font_normal[0], 8), 
                              bg=self.colors["secondary"], 
                              fg=self.colors["text"],
                              pady=5)
        version_label.pack(side="bottom", fill="x", pady=5)
        
        # پنل اصلی محتوا
        content_container = tk.PanedWindow(main_panel, orient=tk.VERTICAL, 
                                         bg=self.colors["bg"],
                                         sashwidth=4, sashrelief=tk.SUNKEN)
        content_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # نوار ابزار - دکمه‌های کنترل دانلود
        toolbar_frame = tk.Frame(content_container, bg=self.colors["bg"], height=40)
        toolbar_frame.pack_propagate(False)
        content_container.add(toolbar_frame, height=40)
        
        # استایل دکمه‌های نوار ابزار
        toolbar_btn_style = {
            "bg": self.colors["button_bg"],
            "fg": self.colors["button_fg"],
            "activebackground": self.colors["button_active"],
            "activeforeground": self.colors["button_fg"],
            "font": self.font_normal,
            "bd": 0,
            "padx": 10,
            "pady": 2,
            "width": 8,
            "cursor": "hand2"
        }
        
        # دکمه‌های کنترل دانلود در نوار ابزار
        self.resume_btn = tk.Button(toolbar_frame, text="▶ ادامه", command=self._resume_download, state="disabled", **toolbar_btn_style)
        self.resume_btn.pack(side="right", padx=5, pady=5)
        
        self.pause_btn = tk.Button(toolbar_frame, text="⏸ توقف", command=self._pause_download, state="disabled", **toolbar_btn_style)
        self.pause_btn.pack(side="right", padx=5, pady=5)
        
        self.cancel_btn = tk.Button(toolbar_frame, text="⏹ لغو", command=self._cancel_download, state="disabled", **toolbar_btn_style)
        self.cancel_btn.pack(side="right", padx=5, pady=5)
        
        self.remove_btn = tk.Button(toolbar_frame, text="🗑 حذف", command=self._remove_download, state="disabled", **toolbar_btn_style)
        self.remove_btn.pack(side="right", padx=5, pady=5)
        
        # نمایشگر تعداد دانلودها
        self.download_count_label = tk.Label(toolbar_frame, text="تعداد دانلودها: 0", 
                                        font=self.font_normal, bg=self.colors["bg"],
                                        fg=self.colors["text"])
        self.download_count_label.pack(side="left", padx=5, pady=5)
        
        # ایجاد منوی اصلی
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # منوی فایل
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="فایل", menu=file_menu)
        file_menu.add_command(label="دانلود جدید", command=self._show_new_download_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="تنظیمات", command=self._show_settings_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="خروج", command=self._on_close)
        
        # منوی راهنما
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="راهنما", menu=help_menu)
        help_menu.add_command(label="درباره برنامه", command=self._show_about_dialog)
        
        # فریم لیست دانلودها
        downloads_frame = tk.Frame(content_container, bg=self.colors["bg"], bd=1, relief=tk.SOLID)
        content_container.add(downloads_frame)
        
        # فریم جزئیات
        details_frame = tk.LabelFrame(content_container, text="جزئیات دانلود", 
                                   font=self.font_bold, bg=self.colors["bg"],
                                   fg=self.colors["text"], height=150, pady=5)
        content_container.add(details_frame, height=150)
        details_frame.pack_propagate(False)
        
        # ایجاد اسکرول برای لیست دانلود‌ها
        downloads_canvas = tk.Canvas(downloads_frame, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(downloads_frame, orient="vertical", command=downloads_canvas.yview)
        
        self.downloads_scrollable_frame = tk.Frame(downloads_canvas, bg=self.colors["bg"])
        self.downloads_scrollable_frame.bind(
            "<Configure>",
            lambda e: downloads_canvas.configure(scrollregion=downloads_canvas.bbox("all"))
        )
        
        downloads_canvas.create_window((0, 0), window=self.downloads_scrollable_frame, anchor="nw")
        downloads_canvas.configure(yscrollcommand=scrollbar.set)
        
        # تغییر اندازه بوم با تغییر اندازه پنجره
        downloads_frame.bind("<Configure>", lambda e: downloads_canvas.configure(width=e.width-20))
        
        downloads_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # بخش جزئیات دانلود
        details_inner_frame = tk.Frame(details_frame, bg=self.colors["bg"], padx=10, pady=5)
        details_inner_frame.pack(fill="both", expand=True)
        
        # گرید جزئیات
        details_grid = tk.Frame(details_inner_frame, bg=self.colors["bg"])
        details_grid.pack(fill="both", expand=True)
        
        # استایل برچسب‌های اطلاعات
        info_label_style = {"bg": self.colors["bg"], "fg": self.colors["text"], 
                         "font": self.font_normal, "pady": 2, "anchor": "e"}
        info_value_style = {"bg": self.colors["bg"], "fg": self.colors.get("accent", self.colors["text"]), 
                         "font": self.font_normal, "pady": 2, "anchor": "w"}
        
        # ردیف اول
        tk.Label(details_grid, text="نام فایل:", **info_label_style).grid(row=0, column=3, sticky="e", padx=5)
        self.detail_filename = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_filename.grid(row=0, column=2, sticky="w", padx=5)
        
        tk.Label(details_grid, text="وضعیت:", **info_label_style).grid(row=0, column=1, sticky="e", padx=5)
        self.detail_status = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_status.grid(row=0, column=0, sticky="w", padx=5)
        
        # ردیف دوم
        tk.Label(details_grid, text="مسیر ذخیره:", **info_label_style).grid(row=1, column=3, sticky="e", padx=5)
        self.detail_save_path = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_save_path.grid(row=1, column=2, sticky="w", padx=5)
        
        tk.Label(details_grid, text="سایز:", **info_label_style).grid(row=1, column=1, sticky="e", padx=5)
        self.detail_size = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_size.grid(row=1, column=0, sticky="w", padx=5)
        
        # ردیف سوم
        tk.Label(details_grid, text="لینک:", **info_label_style).grid(row=2, column=3, sticky="e", padx=5)
        self.detail_url = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_url.grid(row=2, column=2, sticky="w", padx=5)
        
        tk.Label(details_grid, text="سرعت:", **info_label_style).grid(row=2, column=1, sticky="e", padx=5)
        self.detail_speed = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_speed.grid(row=2, column=0, sticky="w", padx=5)
        
        # ردیف چهارم
        tk.Label(details_grid, text="دریافت شده:", **info_label_style).grid(row=3, column=3, sticky="e", padx=5)
        self.detail_downloaded = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_downloaded.grid(row=3, column=2, sticky="w", padx=5)
        
        tk.Label(details_grid, text="زمان باقیمانده:", **info_label_style).grid(row=3, column=1, sticky="e", padx=5)
        self.detail_eta = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_eta.grid(row=3, column=0, sticky="w", padx=5)
        
        # زمان سپری شده
        tk.Label(details_grid, text="زمان سپری شده:", **info_label_style).grid(row=4, column=1, sticky="e", padx=5)
        self.detail_elapsed = tk.Label(details_grid, text="-", **info_value_style)
        self.detail_elapsed.grid(row=4, column=0, sticky="w", padx=5)
        
        # تنظیم وزن ستون‌ها
        for i in range(4):
            details_grid.columnconfigure(i, weight=1)
        
        # فوتر وضعیت
        footer_frame = tk.Frame(self.main_frame, bg=self.colors["primary"], height=25)
        footer_frame.pack(fill="x", side="bottom", pady=0)
        footer_frame.pack_propagate(False)
        
        # نمایش اطلاعات وضعیت در فوتر
        self.status_label = tk.Label(footer_frame, text="آماده برای دانلود", 
                                 bg=self.colors["primary"], 
                                 fg=self.colors["text"],
                                 font=(self.font_normal[0], 9))
        self.status_label.pack(side="right", padx=10)
        
        # ذخیره مرجع به لیست دانلودها برای به‌روزرسانی
        self.download_items_ui = {}
        
        # تنظیم اولیه
        self._update_download_items()
        
        # تنظیم RTL برای همه المان‌ها
        for child in details_grid.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(justify="right")
        
        # تابع برای بروزرسانی آمار دانلود‌ها
        self._update_download_stats()
    
    def _load_config(self):
        """بارگذاری تنظیمات از فایل"""
        if not os.path.exists(CONFIG_FILE):
            # اگر فایل تنظیمات وجود ندارد، از تنظیمات پیش‌فرض استفاده کن
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # ادغام تنظیمات جدید از تنظیمات پیش‌فرض
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except:
            # در صورت خطا، از تنظیمات پیش‌فرض استفاده کن
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    
    def _save_config(self, config):
        """ذخیره تنظیمات در فایل"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except:
            print("خطا در ذخیره‌سازی تنظیمات")
            return False
    
    def _start_periodic_update(self):
        """شروع به‌روزرسانی دوره‌ای رابط کاربری"""
        self._update_download_items()
        self._update_details()
        self.root.after(1000, self._start_periodic_update)
    
    def _update_download_items(self):
        """به‌روزرسانی لیست دانلودها"""
        # دریافت لیست دانلودها
        downloads = self.download_manager.get_all_downloads()
        
        # به‌روزرسانی شمارنده دانلودها
        self.download_count_label.config(text=f"تعداد دانلودها: {len(downloads)}")
        
        # یافتن شناسه‌های دانلودهای موجود
        current_ids = set(item.id for item in downloads)
        ui_ids = set(self.download_items_ui.keys())
        
        # حذف دانلودهایی که دیگر وجود ندارند
        for dl_id in ui_ids - current_ids:
            if dl_id in self.download_items_ui:
                for widget in self.download_items_ui[dl_id]['widgets']:
                    widget.destroy()
                del self.download_items_ui[dl_id]
        
        # اضافه کردن دانلودهای جدید
        row = 0
        for item in downloads:
            if item.id not in self.download_items_ui:
                # ایجاد فریم جدید با طراحی مدرن
                item_bg = self.colors.get("list_item_bg", self.colors["bg"])
                
                frame = tk.Frame(self.downloads_scrollable_frame, bg=item_bg, bd=1, 
                              relief=tk.GROOVE, padx=10, pady=10)
                frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5, ipadx=5, ipady=5)
                
                # تنظیم گسترش افقی
                self.downloads_scrollable_frame.columnconfigure(0, weight=1)
                
                # فریم اطلاعات فایل (بالا)
                info_frame = tk.Frame(frame, bg=item_bg)
                info_frame.pack(fill="x", expand=True)
                
                # آیکون وضعیت
                status_icon = self._get_status_icon(item.status)
                status_label = tk.Label(info_frame, text=status_icon, font=(self.font_bold[0], 18), 
                                     bg=item_bg, fg=self._get_status_color(item.status),
                                     padx=5)
                status_label.pack(side="right")
                
                # نام فایل
                filename_label = tk.Label(info_frame, text=item.filename, font=self.font_bold, 
                                       bg=item_bg, fg=self.colors["text"],
                                       anchor="w", padx=5)
                filename_label.pack(side="right", fill="x", expand=True)
                
                # وضعیت
                status_text_label = tk.Label(info_frame, text=self._get_status_text(item.status), 
                                          bg=item_bg, fg=self._get_status_color(item.status),
                                          font=self.font_normal, padx=5)
                status_text_label.pack(side="left")
                
                # نوار پیشرفت
                progress_frame = tk.Frame(frame, bg=item_bg, pady=5)
                progress_frame.pack(fill="x", expand=True)
                
                # استفاده از ttk.Progressbar با استایل سفارشی
                progress_height = 15  # افزایش ارتفاع نوار پیشرفت
                progress_style = f"Custom{item.id}.Horizontal.TProgressbar"
                
                # تنظیم رنگ نوار پیشرفت بر اساس وضعیت
                progress_color = self._get_progress_color(item.status)
                self.style.configure(progress_style, background=progress_color, 
                                 troughcolor=self.colors.get("progress_bg", "#f0f0f0"), 
                                 borderwidth=0, thickness=progress_height)
                
                progress_bar = ttk.Progressbar(progress_frame, style=progress_style, 
                                            value=item.progress, length=400)
                progress_bar.pack(fill="x", expand=True, padx=5)
                
                # فریم اطلاعات اضافی (پایین)
                details_frame = tk.Frame(frame, bg=item_bg)
                details_frame.pack(fill="x", expand=True, pady=(5, 0))
                
                # سایز و سرعت - سمت راست
                file_info = self._get_download_info_text(item)
                info_label = tk.Label(details_frame, text=file_info, 
                                   bg=item_bg, fg=self.colors["text"],
                                   font=self.font_normal, anchor="w")
                info_label.pack(side="right", padx=5)
                
                # افزودن رویدادهای کلیک
                for widget in [frame, info_frame, progress_frame, details_frame, filename_label, 
                            status_label, status_text_label, progress_bar, info_label]:
                    widget.bind("<Button-1>", lambda e, id=item.id: self._select_download(id))
                    # تغییر حالت نشانگر موس به دست
                    widget.bind("<Enter>", lambda e, w=widget, bg=item_bg: self._on_item_enter(w, bg))
                    widget.bind("<Leave>", lambda e, w=widget, bg=item_bg: self._on_item_leave(w, bg))
                
                # ذخیره اشاره‌گرها
                self.download_items_ui[item.id] = {
                    'widgets': [frame, info_frame, progress_frame, details_frame, filename_label, 
                               status_label, status_text_label, progress_bar, info_label],
                    'filename_label': filename_label,
                    'status_label': status_label,
                    'status_text_label': status_text_label,
                    'progress_bar': progress_bar,
                    'info_label': info_label,
                    'frame': frame,
                    'bg_color': item_bg
                }
                
                row += 1
            else:
                # به‌روزرسانی آیتم‌های موجود
                ui_item = self.download_items_ui[item.id]
                
                # به‌روزرسانی آیکون وضعیت
                ui_item['status_label'].config(text=self._get_status_icon(item.status),
                                          fg=self._get_status_color(item.status))
                
                # به‌روزرسانی متن وضعیت
                ui_item['status_text_label'].config(text=self._get_status_text(item.status),
                                               fg=self._get_status_color(item.status))
                
                # به‌روزرسانی نوار پیشرفت
                ui_item['progress_bar'].config(value=item.progress)
                
                # به‌روزرسانی اطلاعات دانلود
                ui_item['info_label'].config(text=self._get_download_info_text(item))
                
                # به‌روزرسانی رنگ نوار پیشرفت
                progress_style = f"Custom{item.id}.Horizontal.TProgressbar"
                progress_color = self._get_progress_color(item.status)
                self.style.configure(progress_style, background=progress_color)
                
                if self.selected_download_id == item.id:
                    # به‌روزرسانی جزئیات اگر این دانلود انتخاب شده است
                    self._update_details()
        
        # به‌روزرسانی آمار دانلودها
        self._update_download_stats()
    
    def _on_item_enter(self, widget, original_bg):
        """رویداد هنگام ورود موس به آیتم دانلود"""
        hover_bg = self.colors.get("list_item_hover", self._lighten_color(original_bg))
        widget.configure(bg=hover_bg)
        
        # تغییر رنگ همه ویجت‌های داخلی که پس‌زمینه دارند
        for child in widget.winfo_children():
            if hasattr(child, 'configure') and 'bg' in child.config():
                child.configure(bg=hover_bg)
    
    def _on_item_leave(self, widget, original_bg):
        """رویداد هنگام خروج موس از آیتم دانلود"""
        widget.configure(bg=original_bg)
        
        # بازگرداندن رنگ همه ویجت‌های داخلی
        for child in widget.winfo_children():
            if hasattr(child, 'configure') and 'bg' in child.config():
                child.configure(bg=original_bg)
    
    def _lighten_color(self, hex_color, factor=0.15):
        """روشن‌تر کردن رنگ برای حالت هاور"""
        # تبدیل رنگ هگز به RGB
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # روشن‌تر کردن
        rgb_new = tuple(min(int(c + (255 - c) * factor), 255) for c in rgb)
        
        # بازگرداندن به هگز
        return f"#{rgb_new[0]:02x}{rgb_new[1]:02x}{rgb_new[2]:02x}"
    
    def _get_status_icon(self, status):
        """آیکون متناسب با وضعیت دانلود"""
        icons = {
            "pending": "⏳",
            "downloading": "⬇️",
            "paused": "⏸️",
            "completed": "✅",
            "error": "❌",
            "canceled": "⛔"
        }
        return icons.get(status, "❓")
    
    def _get_status_color(self, status):
        """رنگ متناسب با وضعیت دانلود"""
        colors = {
            "pending": self.colors.get("warning", "#ffc107"),
            "downloading": self.colors.get("accent", "#00b8d4"),
            "paused": self.colors.get("warning", "#ffc107"),
            "completed": self.colors.get("success", "#28a745"),
            "error": self.colors.get("danger", "#dc3545"),
            "canceled": self.colors.get("danger", "#dc3545")
        }
        return colors.get(status, self.colors["text"])
    
    def _get_progress_color(self, status):
        """رنگ نوار پیشرفت بر اساس وضعیت"""
        colors = {
            "pending": self.colors.get("warning", "#ffc107"),
            "downloading": self.colors.get("accent", "#00b8d4"),
            "paused": self.colors.get("warning", "#ffc107"),
            "completed": self.colors.get("success", "#28a745"),
            "error": self.colors.get("danger", "#dc3545"),
            "canceled": self.colors.get("danger", "#dc3545")
        }
        return colors.get(status, self.colors.get("progress_fg", "#00b8d4"))
    
    def _get_status_text(self, status):
        """تبدیل وضعیت به متن فارسی"""
        status_texts = {
            "pending": "در انتظار",
            "downloading": "در حال دانلود",
            "paused": "متوقف شده",
            "completed": "کامل شده",
            "error": "خطا",
            "canceled": "لغو شده"
        }
        return status_texts.get(status, status)
    
    def _get_download_info_text(self, item):
        """تولید متن اطلاعات دانلود"""
        if item.status == "downloading":
            # در حال دانلود
            return f"{format_size(item.downloaded)} / {format_size(item.size)} - {format_speed(item.speed)}"
        elif item.status == "completed":
            # کامل شده
            return f"{format_size(item.size)} - زمان: {format_time(item.elapsed_time())}"
        elif item.status == "error":
            # خطا
            return f"خطا: {item.error_message[:50]}"
        elif item.status == "paused":
            # متوقف شده
            return f"{format_size(item.downloaded)} / {format_size(item.size)}"
        else:
            # سایر وضعیت‌ها
            if item.size > 0:
                return f"{format_size(item.size)}"
            else:
                return "نامشخص"
    
    def _update_details(self):
        """به‌روزرسانی پنل جزئیات دانلود"""
        if not self.selected_download_id:
            return
        
        item = self.download_manager.get_download(self.selected_download_id)
        if not item:
            # اگر دانلود انتخاب شده دیگر وجود ندارد
            self.selected_download_id = None
            self._clear_details()
            return
        
        # به‌روزرسانی اطلاعات جزئیات
        self.detail_filename.config(text=item.filename)
        self.detail_url.config(text=item.url)
        self.detail_save_path.config(text=item.save_path)
        self.detail_status.config(text=self._get_status_text(item.status))
        self.detail_size.config(text=format_size(item.size))
        self.detail_downloaded.config(text=f"{format_size(item.downloaded)} ({item.progress:.1f}%)")
        self.detail_speed.config(text=format_speed(item.speed) if item.status == "downloading" else "-")
        self.detail_eta.config(text=format_time(item.estimated_time()) if item.status == "downloading" else "-")
        self.detail_elapsed.config(text=format_time(item.elapsed_time()))
        
        # به‌روزرسانی دکمه‌ها
        self.pause_btn.config(state="normal" if item.status == "downloading" else "disabled")
        self.resume_btn.config(state="normal" if item.status == "paused" else "disabled")
        self.cancel_btn.config(state="normal" if item.status in ["downloading", "paused", "pending"] else "disabled")
        self.remove_btn.config(state="normal" if item.status in ["completed", "error", "canceled"] else "disabled")
    
    def _clear_details(self):
        """پاکسازی پنل جزئیات"""
        self.detail_filename.config(text="-")
        self.detail_url.config(text="-")
        self.detail_save_path.config(text="-")
        self.detail_status.config(text="-")
        self.detail_size.config(text="-")
        self.detail_downloaded.config(text="-")
        self.detail_speed.config(text="-")
        self.detail_eta.config(text="-")
        self.detail_elapsed.config(text="-")
        
        # غیرفعال کردن دکمه‌ها
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="disabled")
        self.cancel_btn.config(state="disabled")
        self.remove_btn.config(state="disabled")
    
    def _select_download(self, download_id):
        """انتخاب یک دانلود از لیست"""
        # حذف حالت انتخاب قبلی
        if self.selected_download_id and self.selected_download_id in self.download_items_ui:
            ui_item = self.download_items_ui[self.selected_download_id]
            bg_color = ui_item.get('bg_color', self.colors["bg"])
            
            # بازگرداندن رنگ همه ویجت‌ها به حالت عادی
            for widget in ui_item['widgets']:
                if hasattr(widget, 'configure') and 'bg' in widget.config():
                    widget.configure(bg=bg_color)
            
            # حذف بوردر انتخاب
            ui_item['frame'].configure(relief=tk.GROOVE, bd=1)
        
        # تنظیم دانلود جدید انتخاب شده
        self.selected_download_id = download_id
        
        # تغییر ظاهر آیتم انتخاب شده
        if download_id in self.download_items_ui:
            ui_item = self.download_items_ui[download_id]
            
            # تغییر رنگ پس‌زمینه به رنگ انتخاب
            selected_bg = self.colors.get("secondary", self._lighten_color(ui_item.get('bg_color', self.colors["bg"]), 0.1))
            
            # اعمال رنگ انتخاب به همه ویجت‌ها
            for widget in ui_item['widgets']:
                if hasattr(widget, 'configure') and 'bg' in widget.config():
                    widget.configure(bg=selected_bg)
            
            # افزایش برجستگی بوردر
            ui_item['frame'].configure(relief=tk.RIDGE, bd=2)
        
        # فعال/غیرفعال کردن دکمه‌های کنترل
        self._update_control_buttons()
        
        # به‌روزرسانی پنل جزئیات
        self._update_details()
    
    def _update_control_buttons(self):
        """به‌روزرسانی وضعیت دکمه‌های کنترل بر اساس وضعیت دانلود انتخاب شده"""
        if not self.selected_download_id:
            # غیرفعال کردن همه دکمه‌ها
            self.pause_btn.config(state="disabled")
            self.resume_btn.config(state="disabled")
            self.cancel_btn.config(state="disabled")
            self.remove_btn.config(state="disabled")
            return
            
        # دریافت اطلاعات دانلود انتخاب شده
        item = self.download_manager.get_download(self.selected_download_id)
        if not item:
            # اگر دانلود موجود نیست
            self.selected_download_id = None
            self._clear_details()
            self._update_control_buttons()
            return
            
        # تنظیم وضعیت دکمه‌ها بر اساس وضعیت دانلود
        self.pause_btn.config(state="normal" if item.status == "downloading" else "disabled")
        self.resume_btn.config(state="normal" if item.status == "paused" else "disabled")
        self.cancel_btn.config(state="normal" if item.status in ["downloading", "paused", "pending"] else "disabled")
        self.remove_btn.config(state="normal" if item.status in ["completed", "error", "canceled"] else "disabled")
    
    def _pause_download(self):
        """توقف موقت دانلود انتخاب شده"""
        if self.selected_download_id:
            self.download_manager.pause_download(self.selected_download_id)
            self._update_details()
    
    def _resume_download(self):
        """ادامه دانلود انتخاب شده"""
        if self.selected_download_id:
            self.download_manager.resume_download(self.selected_download_id)
            self._update_details()
    
    def _cancel_download(self):
        """لغو دانلود انتخاب شده"""
        if self.selected_download_id:
            if messagebox.askyesno("لغو دانلود", "آیا مطمئن هستید که می‌خواهید این دانلود را لغو کنید؟"):
                self.download_manager.cancel_download(self.selected_download_id)
                self._update_details()
    
    def _remove_download(self):
        """حذف دانلود از لیست"""
        if self.selected_download_id:
            if messagebox.askyesno("حذف دانلود", "آیا مطمئن هستید که می‌خواهید این دانلود را از لیست حذف کنید؟"):
                self.download_manager.remove_download(self.selected_download_id)
                self.selected_download_id = None
                self._clear_details()
                self._update_download_items()
    
    def _show_new_download_dialog(self):
        """نمایش دیالوگ دانلود جدید"""
        dialog = tk.Toplevel(self.root)
        dialog.title("دانلود جدید")
        dialog.geometry("500x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors["bg"])
        
        # تنظیم فونت و جهت متن
        for child in dialog.winfo_children():
            child.configure(font=("BYekan+", 10))
        
        # فریم اصلی
        main_frame = tk.Frame(dialog, bg=self.colors["bg"], padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # لیبل‌ها و ورودی‌ها
        label_style = {"bg": self.colors["bg"], "fg": self.colors["text"], "font": self.font_normal}
        entry_style = {"bg": "white", "fg": self.colors["text"], "font": self.font_normal, "relief": tk.SUNKEN, "bd": 1}
        
        tk.Label(main_frame, text="آدرس دانلود:", **label_style).grid(row=0, column=1, sticky="e", padx=5, pady=5)
        url_var = tk.StringVar()
        url_entry = tk.Entry(main_frame, textvariable=url_var, width=50, **entry_style)
        url_entry.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        url_entry.focus()
        
        tk.Label(main_frame, text="مسیر ذخیره:", **label_style).grid(row=1, column=1, sticky="e", padx=5, pady=5)
        save_path_var = tk.StringVar(value=self.config.get("default_download_path"))
        save_path_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        save_path_frame.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        save_path_entry = tk.Entry(save_path_frame, textvariable=save_path_var, width=40, **entry_style)
        save_path_entry.pack(side="left")
        
        browse_btn = tk.Button(save_path_frame, text="انتخاب", command=lambda: self._browse_directory(save_path_var),
                              bg=self.colors["button_bg"], fg=self.colors["button_fg"], 
                              activebackground=self.colors["button_active"], font=self.font_normal)
        browse_btn.pack(side="right", padx=5)
        
        tk.Label(main_frame, text="نام فایل (اختیاری):", **label_style).grid(row=2, column=1, sticky="e", padx=5, pady=5)
        filename_var = tk.StringVar()
        filename_entry = tk.Entry(main_frame, textvariable=filename_var, width=50, **entry_style)
        filename_entry.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        # فریم دکمه‌ها
        button_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        # استایل دکمه‌ها
        button_style = {"bg": self.colors["button_bg"], "fg": self.colors["button_fg"], 
                       "activebackground": self.colors["button_active"], "font": self.font_normal,
                       "relief": tk.RAISED, "bd": 1, "padx": 10, "pady": 5}
        
        # دکمه انصراف
        cancel_btn = tk.Button(button_frame, text="انصراف", command=dialog.destroy, **button_style)
        cancel_btn.pack(side="left", padx=5)
        
        # دکمه دانلود
        download_btn = tk.Button(button_frame, text="شروع دانلود", 
                               command=lambda: self._start_new_download(url_var.get(), save_path_var.get(), filename_var.get(), dialog),
                               **button_style)
        download_btn.pack(side="right", padx=5)
        
        # تنظیم جهت‌گیری راست به چپ
        for child in main_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(justify="right")
        
        # برای فشردن دکمه Enter
        dialog.bind("<Return>", lambda e: download_btn.invoke())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _browse_directory(self, path_var):
        """انتخاب دایرکتوری برای ذخیره فایل"""
        directory = filedialog.askdirectory(initialdir=path_var.get())
        if directory:
            path_var.set(directory)
    
    def _start_new_download(self, url, save_path, filename, dialog=None):
        """شروع یک دانلود جدید"""
        # بررسی ورودی‌ها
        if not url or not url.strip():
            messagebox.showerror("خطا", "لطفاً آدرس دانلود را وارد کنید.")
            return
        
        if not save_path or not os.path.isdir(save_path):
            messagebox.showerror("خطا", "مسیر ذخیره نامعتبر است.")
            return
        
        # افزودن پروتکل اگر ندارد
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        try:
            # افزودن دانلود جدید
            download_id = self.download_manager.add_download(url, save_path, filename)
            
            # ذخیره مسیر پیش‌فرض جدید
            self.config["default_download_path"] = save_path
            self._save_config(self.config)
            
            # بستن دیالوگ در صورت وجود
            if dialog:
                dialog.destroy()
            
            # انتخاب دانلود جدید
            self._select_download(download_id)
            
            return download_id
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در شروع دانلود: {str(e)}")
            return None
    
    def _show_settings_dialog(self):
        """نمایش دیالوگ تنظیمات"""
        dialog = tk.Toplevel(self.root)
        dialog.title("تنظیمات")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors["bg"])
        
        # فریم اصلی
        main_frame = tk.Frame(dialog, bg=self.colors["bg"], padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # استایل‌های مشترک
        label_style = {"bg": self.colors["bg"], "fg": self.colors["text"], "font": self.font_normal}
        entry_style = {"bg": "white", "fg": self.colors["text"], "font": self.font_normal, "relief": tk.SUNKEN, "bd": 1}
        button_style = {"bg": self.colors["button_bg"], "fg": self.colors["button_fg"], 
                       "activebackground": self.colors["button_active"], "font": self.font_normal,
                       "relief": tk.RAISED, "bd": 1, "padx": 10, "pady": 5}
        
        # تنظیمات دانلود
        download_frame = tk.LabelFrame(main_frame, text="تنظیمات دانلود", bg=self.colors["bg"], 
                                     fg=self.colors["text"], font=self.font_normal, padx=15, pady=15)
        download_frame.pack(fill="x", pady=10, padx=10, ipady=5)
        
        # مسیر پیش‌فرض دانلود
        tk.Label(download_frame, text="مسیر پیش‌فرض دانلود:", **label_style).grid(row=0, column=1, sticky="e", padx=10, pady=8)
        default_path_var = tk.StringVar(value=self.config.get("default_download_path"))
        default_path_frame = tk.Frame(download_frame, bg=self.colors["bg"])
        default_path_frame.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        
        default_path_entry = tk.Entry(default_path_frame, textvariable=default_path_var, width=40, **entry_style)
        default_path_entry.pack(side="left")
        
        browse_btn = tk.Button(default_path_frame, text="انتخاب", command=lambda: self._browse_directory(default_path_var), **button_style)
        browse_btn.pack(side="right", padx=5)
        
        # تعداد دانلود همزمان
        tk.Label(download_frame, text="تعداد دانلود همزمان:", **label_style).grid(row=1, column=1, sticky="e", padx=5, pady=2)
        concurrent_downloads_var = tk.IntVar(value=self.config.get("max_concurrent_downloads", 3))
        concurrent_downloads_spinbox = tk.Spinbox(download_frame, from_=1, to=10, textvariable=concurrent_downloads_var, width=5, **entry_style)
        concurrent_downloads_spinbox.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        
        # تعداد نخ‌های هر دانلود
        tk.Label(download_frame, text="تعداد نخ‌های هر دانلود:", **label_style).grid(row=2, column=1, sticky="e", padx=5, pady=2)
        threads_per_download_var = tk.IntVar(value=self.config.get("max_threads_per_download", 5))
        threads_per_download_spinbox = tk.Spinbox(download_frame, from_=1, to=16, textvariable=threads_per_download_var, width=5, **entry_style)
        threads_per_download_spinbox.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        
        # استفاده از دانلود چندنخی
        multithreaded_var = tk.BooleanVar(value=self.config.get("use_multithreaded_download", True))
        multithreaded_check = tk.Checkbutton(download_frame, text="استفاده از دانلود چندنخی", variable=multithreaded_var,
                                           bg=self.colors["bg"], fg=self.colors["text"], font=self.font_normal,
                                           activebackground=self.colors["bg"], selectcolor=self.colors["bg"])
        multithreaded_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        # تنظیمات رابط کاربری
        ui_frame = tk.LabelFrame(main_frame, text="تنظیمات رابط کاربری", bg=self.colors["bg"], 
                               fg=self.colors["text"], font=self.font_normal, padx=15, pady=15)
        ui_frame.pack(fill="x", pady=10, padx=10, ipady=5)
        
        # تم برنامه
        tk.Label(ui_frame, text="تم برنامه:", **label_style).grid(row=0, column=1, sticky="e", padx=10, pady=8)
        themes = ["aqua", "dark", "light"]
        theme_var = tk.StringVar(value=self.config.get("theme", "aqua"))
        theme_combobox = ttk.Combobox(ui_frame, textvariable=theme_var, values=themes, width=20, state="readonly")
        theme_combobox.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        
        # شروع خودکار دانلود
        auto_start_var = tk.BooleanVar(value=self.config.get("auto_start_download", True))
        auto_start_check = tk.Checkbutton(ui_frame, text="شروع خودکار دانلود", variable=auto_start_var,
                                         bg=self.colors["bg"], fg=self.colors["text"], font=self.font_normal,
                                         activebackground=self.colors["bg"], selectcolor=self.colors["bg"])
        auto_start_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        # دکمه‌ها
        button_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=15)
        
        cancel_btn = tk.Button(button_frame, text="انصراف", command=dialog.destroy, width=15, **button_style)
        cancel_btn.pack(side="left", padx=15)
        
        save_btn = tk.Button(button_frame, text="ذخیره", width=15, **button_style,
                           command=lambda: self._save_settings(
                               default_path_var.get(),
                               concurrent_downloads_var.get(),
                               threads_per_download_var.get(),
                               multithreaded_var.get(),
                               theme_var.get(),
                               auto_start_var.get(),
                               dialog
                           ))
        save_btn.pack(side="right", padx=5)
        
        # تنظیم جهت‌گیری راست به چپ
        for child in download_frame.winfo_children() + ui_frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(justify="right")
        
        dialog.bind("<Return>", lambda e: save_btn.invoke())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _save_settings(self, default_path, concurrent_downloads, threads_per_download, multithreaded, theme, auto_start, dialog):
        """ذخیره تنظیمات جدید"""
        try:
            # اعتبارسنجی تنظیمات
            if not os.path.isdir(default_path):
                messagebox.showerror("خطا", "مسیر پیش‌فرض نامعتبر است.")
                return
            
            # ذخیره تنظیمات جدید
            self.config["default_download_path"] = default_path
            self.config["max_concurrent_downloads"] = concurrent_downloads
            self.config["max_threads_per_download"] = threads_per_download
            self.config["use_multithreaded_download"] = multithreaded
            self.config["theme"] = theme
            self.config["auto_start_download"] = auto_start
            
            self._save_config(self.config)
            
            # بستن دیالوگ
            dialog.destroy()
            
            # استفاده از تم جدید
            if theme != self.style.theme.name:
                # تغییر تم
                self.style = Style(theme=theme)
            
            # پیام موفقیت
            messagebox.showinfo("اطلاعیه", "تنظیمات با موفقیت ذخیره شدند.")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در ذخیره تنظیمات: {str(e)}")
    
    def _show_about_dialog(self):
        """نمایش دیالوگ درباره برنامه"""
        dialog = tk.Toplevel(self.root)
        dialog.title("درباره برنامه")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors["bg"])
        
        # فریم اصلی
        main_frame = tk.Frame(dialog, bg=self.colors["bg"], padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # عنوان برنامه
        title_label = tk.Label(main_frame, text=APP_NAME, font=self.font_big, 
                              bg=self.colors["bg"], fg=self.colors["text"])
        title_label.pack(pady=10)
        
        # نسخه
        version_label = tk.Label(main_frame, text=f"نسخه {APP_VERSION}", 
                               bg=self.colors["bg"], fg=self.colors["text"])
        version_label.pack()
        
        # توضیحات
        desc_text = """شتاب دریافت یک نرم‌افزار دانلود منیجر فارسی با امکانات دانلود چندنخی است که به شما امکان دانلود سریع‌تر فایل‌ها را می‌دهد.

ویژگی‌ها:
- دانلود چندنخی برای افزایش سرعت
- قابلیت توقف و ادامه دانلود
- مدیریت دانلودها با رابط کاربری ساده و زیبا
- پشتیبانی کامل از زبان فارسی
- نمایش سرعت و پیشرفت دانلود
- تنظیمات سفارشی برای بهینه‌سازی"""
        
        desc_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        desc_frame.pack(fill="both", expand=True, pady=10)
        
        desc_scrollbar = tk.Scrollbar(desc_frame)
        desc_scrollbar.pack(side="right", fill="y")
        
        desc_text_widget = tk.Text(desc_frame, wrap="word", height=8, font=("BYekan+", 9), 
                                 yscrollcommand=desc_scrollbar.set, bg="white", fg=self.colors["text"])
        desc_text_widget.pack(side="left", fill="both", expand=True)
        desc_scrollbar.config(command=desc_text_widget.yview)
        
        desc_text_widget.insert("1.0", desc_text)
        desc_text_widget.config(state="disabled")
        
        # کپی‌رایت
        copyright_label = tk.Label(main_frame, text=f"© {datetime.datetime.now().year} - تمامی حقوق محفوظ است.",
                                 bg=self.colors["bg"], fg=self.colors["text"])
        copyright_label.pack(pady=5)
        
        # دکمه بستن
        button_style = {"bg": self.colors["button_bg"], "fg": self.colors["button_fg"], 
                       "activebackground": self.colors["button_active"], "font": self.font_normal,
                       "relief": tk.RAISED, "bd": 1, "padx": 10, "pady": 5}
        
        close_btn = tk.Button(main_frame, text="بستن", command=dialog.destroy, **button_style)
        close_btn.pack(pady=5)
        
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _update_download_ui(self, item):
        """کالبک برای به‌روزرسانی UI با تغییرات دانلود"""
        # به‌روزرسانی المان‌های UI مربوط به این دانلود
        if item.id in self.download_items_ui:
            ui_item = self.download_items_ui[item.id]
            ui_item['status_label'].config(text=self._get_status_text(item.status))
            ui_item['progress_bar'].config(value=item.progress)
            ui_item['info_label'].config(text=self._get_download_info_text(item))
        
        # به‌روزرسانی پنل جزئیات اگر این دانلود انتخاب شده است
        if self.selected_download_id == item.id:
            self._update_details()
    
    def _on_close(self):
        """اقدامات لازم قبل از بستن برنامه"""
        # پرسیدن برای تایید خروج اگر دانلود فعالی وجود دارد
        active_downloads = [item for item in self.download_manager.get_all_downloads() if item.status == "downloading"]
        if active_downloads and not messagebox.askyesno("خروج", 
                                      f"{len(active_downloads)} دانلود در حال انجام وجود دارد. آیا مایل به خروج هستید؟"):
            return
        
        # ذخیره تاریخچه دانلودها
        self.download_manager.save_history()
        self.root.destroy()
    
    def _update_download_stats(self):
        """به‌روزرسانی آمار دانلودها در ساید بار"""
        downloads = self.download_manager.get_all_downloads()
        
        # شمارش وضعیت‌های مختلف
        active_count = sum(1 for item in downloads if item.status == "downloading")
        completed_count = sum(1 for item in downloads if item.status == "completed")
        paused_count = sum(1 for item in downloads if item.status == "paused")
        error_count = sum(1 for item in downloads if item.status == "error" or item.status == "canceled")
        
        # به‌روزرسانی برچسب‌های آمار
        self.active_count_label.config(text=f"در حال دانلود: {active_count}")
        self.completed_count_label.config(text=f"تکمیل شده: {completed_count}")
        self.paused_count_label.config(text=f"متوقف شده: {paused_count}")
        self.error_count_label.config(text=f"خطا: {error_count}")
        
        # به‌روزرسانی وضعیت در نوار وضعیت
        if active_count > 0:
            self.status_label.config(text=f"در حال دانلود {active_count} فایل")
        elif len(downloads) == 0:
            self.status_label.config(text="آماده برای دانلود")
        else:
            self.status_label.config(text=f"تکمیل شده: {completed_count} | خطا: {error_count}")
        
        # فراخوانی مجدد برای بروزرسانی بعدی بعد از ۲ ثانیه
        self.root.after(2000, self._update_download_stats)


# اجرای اصلی برنامه
if __name__ == "__main__":
    # بارگذاری ماژول مورد نیاز برای فونت
    import tkinter.font as tkfont
    import ctypes
    from ctypes import WinDLL
    
    # تلاش برای بارگذاری فونت‌ها
    if os.name == "nt":
        try:
            # بارگذاری مستقیم فونت‌ها در ویندوز
            FONTS_COUNT = 32
            FR_PRIVATE = 0x10
            gdi32 = WinDLL('gdi32')
            GDI32 = ctypes.WinDLL('gdi32')
            user32 = ctypes.WinDLL('user32')
            
            # فونت‌های مورد نیاز
            font_files = [
                "BYekan+.ttf",
                "BYekan+ Bold.ttf"
            ]
            
            # بارگذاری تک تک فونت‌ها
            for font_file in font_files:
                font_path = os.path.join(FONT_DIR, font_file)
                if os.path.exists(font_path):
                    print(f"بارگذاری فونت {font_file} از مسیر {font_path}...")
                    # سعی با روش اول: استفاده از AddFontResourceW
                    try:
                        res1 = GDI32.AddFontResourceW(font_path)
                        if res1 > 0:
                            print(f"فونت با موفقیت با روش اول بارگذاری شد: {font_file}")
                    except Exception as e1:
                        print(f"خطا در روش اول بارگذاری فونت {font_file}: {e1}")
                        
                    # سعی با روش دوم: استفاده از AddFontResourceExW
                    try:
                        res2 = gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                        if res2 > 0:
                            print(f"فونت با موفقیت با روش دوم بارگذاری شد: {font_file}")
                    except Exception as e2:
                        print(f"خطا در روش دوم بارگذاری فونت {font_file}: {e2}")
                else:
                    print(f"فایل فونت پیدا نشد: {font_path}")
            
            # اعلام تغییر فونت به سیستم
            user32.SendMessageW(0xFFFF, 0x001D, 0, 0)  # WM_FONTCHANGE برای همه پنجره‌ها
            
        except Exception as e:
            print(f"خطا در فرآیند بارگذاری فونت: {str(e)}")
    
    # ایجاد پنجره اصلی
    root = tk.Tk()
    
    # تعیین جهت‌گیری راست به چپ
    root.tk.call('encoding', 'system', 'utf-8')
    
    # تنظیم چگالی و مقیاس نمایش
    try:
        root.tk.call('tk', 'scaling', 1.5)  # تنظیم مقیاس بزرگتر
    except:
        pass
    
    # تنظیم راست-به-چپ بودن المان‌ها برای فارسی
    try:
        # تلاش برای تنظیم RTL در برخی عناصر
        root.tk.call('tcl_setRightToLeftVal', 1)
    except:
        pass
    
    # تلاش برای بارگذاری پکیج tkfontchooser برای اطلاعات بیشتر فونت
    try:
        root.tk.call('package', 'require', 'fontchooser')
    except:
        pass
        
    # تنظیم عنوان و آیکون برنامه
    root.title(APP_NAME)
    
    # بررسی وجود تم Aqua در لیست تم‌های موجود
    aqua_theme_exists = False
    try:
        themes = ttk.Style().theme_names()
        if "aqua" not in themes:
            print("تم Aqua به لیست تم‌ها اضافه می‌شود...")
        else:
            aqua_theme_exists = True
            print("تم Aqua از قبل وجود دارد.")
    except:
        print("خطا در بررسی تم‌های موجود")
    
    # نمایش اطلاعات فونت‌های سیستم
    print_font_info()
    
    # راه‌اندازی برنامه
    app = ShetabDaryaftApp(root)
    
    # نمایش پنجره
    root.mainloop()
    
    # پاکسازی فونت‌ها در ویندوز
    if os.name == "nt":
        try:
            for font_file in os.listdir(FONT_DIR):
                if font_file.endswith('.ttf'):
                    font_path = os.path.join(FONT_DIR, font_file)
                    if os.path.exists(font_path):
                        ctypes.windll.gdi32.RemoveFontResourceW(font_path)
        except:
            pass
