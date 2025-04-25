import os
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
import threading
import time
import json
from datetime import datetime
import logging
from pathlib import Path

from downloader.download_manager import DownloadManager

# تنظیم لاگ برنامه
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'ShetabDaryaftSecretKey'  # کلید رمزنگاری سشن

# مسیر پیش‌فرض برای ذخیره فایل‌های دانلود شده
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)

# مدیریت دانلود
download_manager = DownloadManager()

@app.route('/')
def index():
    """نمایش صفحه اصلی"""
    return render_template('index.html')

@app.route('/api/start_download', methods=['POST'])
def start_download():
    """شروع دانلود فایل"""
    data = request.json
    url = data.get('url')
    save_path = data.get('save_path') or DEFAULT_DOWNLOAD_DIR
    thread_count = int(data.get('thread_count') or 1)
    use_threads = data.get('use_threads', True)
    
    if not url:
        return jsonify({'status': 'error', 'message': 'آدرس URL وارد نشده است'})
    
    try:
        download_id = download_manager.start_download(url, save_path, thread_count, use_threads)
        return jsonify({
            'status': 'success', 
            'message': 'دانلود شروع شد', 
            'download_id': download_id
        })
    except Exception as e:
        logger.error(f"خطا در شروع دانلود: {str(e)}")
        return jsonify({'status': 'error', 'message': f'خطا در شروع دانلود: {str(e)}'})

@app.route('/api/download_status/<download_id>')
def download_status(download_id):
    """دریافت وضعیت دانلود"""
    status = download_manager.get_download_status(download_id)
    return jsonify(status)

@app.route('/api/cancel_download/<download_id>')
def cancel_download(download_id):
    """لغو دانلود در حال انجام"""
    download_manager.cancel_download(download_id)
    return jsonify({'status': 'success', 'message': 'دانلود لغو شد'})

@app.route('/api/add_to_queue', methods=['POST'])
def add_to_queue():
    """افزودن URL به صف دانلود"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'status': 'error', 'message': 'آدرس URL وارد نشده است'})
    
    download_manager.add_to_queue(url)
    return jsonify({'status': 'success', 'message': 'به صف دانلود اضافه شد'})

@app.route('/api/remove_from_queue', methods=['POST'])
def remove_from_queue():
    """حذف URL از صف دانلود"""
    data = request.json
    index = data.get('index')
    
    if index is None:
        return jsonify({'status': 'error', 'message': 'شماره آیتم صف مشخص نشده است'})
    
    download_manager.remove_from_queue(int(index))
    return jsonify({'status': 'success', 'message': 'از صف دانلود حذف شد'})

@app.route('/api/get_queue')
def get_queue():
    """دریافت لیست صف دانلود"""
    return jsonify({'queue': download_manager.get_queue()})

@app.route('/api/process_queue', methods=['POST'])
def process_queue():
    """پردازش صف دانلود"""
    data = request.json
    save_path = data.get('save_path') or DEFAULT_DOWNLOAD_DIR
    thread_count = int(data.get('thread_count') or 1)
    use_threads = data.get('use_threads', True)
    
    download_manager.process_queue(save_path, thread_count, use_threads)
    return jsonify({'status': 'success', 'message': 'پردازش صف دانلود شروع شد'})

@app.route('/api/get_history')
def get_history():
    """دریافت تاریخچه دانلود"""
    return jsonify({'history': download_manager.get_history()})

@app.route('/api/clear_history')
def clear_history():
    """پاک کردن تاریخچه دانلود"""
    download_manager.clear_history()
    return jsonify({'status': 'success', 'message': 'تاریخچه دانلود پاک شد'})

@app.route('/api/browse_location')
def browse_location():
    """انتخاب مسیر ذخیره‌سازی"""
    # در نسخه وب، کاربر باید پوشه را در فرم مشخص کند
    # برای اجرا در دسکتاپ، نیاز به پیاده‌سازی بیشتر است
    return jsonify({'default_path': DEFAULT_DOWNLOAD_DIR})

@app.route('/api/show_folder/<path:folder_path>')
def show_folder(folder_path):
    """نمایش پوشه در فایل منیجر"""
    # در نسخه وب، یک لینک به پوشه نمایش داده می‌شود
    # برای اجرا در دسکتاپ، نیاز به پیاده‌سازی بیشتر است
    return jsonify({'folder_path': folder_path})

if __name__ == '__main__':
    app.run(debug=True)
