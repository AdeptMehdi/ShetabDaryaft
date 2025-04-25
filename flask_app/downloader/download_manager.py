import os
import requests
import threading
import time
import uuid
from datetime import datetime
import logging
from pathlib import Path

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloadThread:
    """کلاس مدیریت یک نخ دانلود"""
    
    def __init__(self, url, start_byte, end_byte, save_path, filename, callback=None):
        self.url = url
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.save_path = save_path
        self.filename = filename
        self.callback = callback
        self.completed = False
        self.cancelled = False
        self.thread = None
        self.downloaded_size = 0
        self.speed = 0
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
    
    def download(self):
        """شروع دانلود قسمت مشخص شده از فایل"""
        headers = {'Range': f'bytes={self.start_byte}-{self.end_byte}'}
        
        try:
            with requests.get(self.url, headers=headers, stream=True) as r:
                r.raise_for_status()
                
                temp_filename = f"{self.filename}.part{self.start_byte}"
                temp_path = os.path.join(self.save_path, temp_filename)
                
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.cancelled:
                            break
                        if chunk:
                            f.write(chunk)
                            self.downloaded_size += len(chunk)
                            
                            # محاسبه سرعت دانلود
                            current_time = time.time()
                            if current_time - self.last_update_time >= 1:  # بروزرسانی هر ثانیه
                                self.speed = (self.downloaded_size - self.last_downloaded_size) / (current_time - self.last_update_time)
                                self.last_update_time = current_time
                                self.last_downloaded_size = self.downloaded_size
                
                if not self.cancelled:
                    self.completed = True
                    
                    if self.callback:
                        self.callback(self)
                        
        except Exception as e:
            logger.error(f"خطا در دانلود بخش {self.start_byte}-{self.end_byte}: {str(e)}")
            if self.callback:
                self.callback(self, error=str(e))
    
    def start(self):
        """شروع نخ دانلود"""
        self.thread = threading.Thread(target=self.download)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """توقف نخ دانلود"""
        self.cancelled = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

class DownloadManager:
    """کلاس مدیریت دانلود‌ها"""
    
    def __init__(self):
        self.downloads = {}  # دیکشنری از دانلود‌های در حال انجام
        self.download_queue = []  # صف دانلود
        self.download_history = []  # تاریخچه دانلود
        self.queue_processing = False  # وضعیت پردازش صف
    
    def start_download(self, url, save_path, thread_count=1, use_threads=True):
        """شروع دانلود یک فایل"""
        download_id = str(uuid.uuid4())
        
        # ایجاد پوشه ذخیره‌سازی اگر وجود ندارد
        os.makedirs(save_path, exist_ok=True)
        
        # گرفتن اطلاعات اولیه فایل
        try:
            response = requests.head(url)
            response.raise_for_status()
            
            # بررسی پشتیبانی از دانلود چند‌بخشی
            supports_range = 'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'
            content_length = int(response.headers.get('content-length', 0))
            
            # تعیین نام فایل از URL
            filename = os.path.basename(url.split('?')[0])
            if not filename:
                if 'content-disposition' in response.headers:
                    import re
                    match = re.search(r'filename="?([^"]+)"?', response.headers['content-disposition'])
                    if match:
                        filename = match.group(1)
                if not filename:
                    filename = f"download_{download_id}"
            
            file_path = os.path.join(save_path, filename)
            
            download_info = {
                'id': download_id,
                'url': url,
                'filename': filename,
                'file_path': file_path,
                'save_path': save_path,
                'total_size': content_length,
                'downloaded_size': 0,
                'speed': 0,
                'status': 'starting',
                'threads': [],
                'start_time': time.time(),
                'completed': False,
                'error': None
            }
            
            self.downloads[download_id] = download_info
            
            # شروع دانلود
            if use_threads and supports_range and content_length > 0 and thread_count > 1:
                # دانلود چند‌نخی
                chunk_size = content_length // thread_count
                for i in range(thread_count):
                    start_byte = i * chunk_size
                    end_byte = (i + 1) * chunk_size - 1 if i < thread_count - 1 else content_length - 1
                    
                    thread = DownloadThread(
                        url=url,
                        start_byte=start_byte,
                        end_byte=end_byte,
                        save_path=save_path,
                        filename=f"{filename}.part{i}",
                        callback=lambda t, error=None, dl_id=download_id: self._thread_callback(t, dl_id, error)
                    )
                    download_info['threads'].append(thread)
                    thread.start()
                
                # نخ برای بررسی وضعیت کلی دانلود
                monitor_thread = threading.Thread(
                    target=self._monitor_download,
                    args=(download_id,)
                )
                monitor_thread.daemon = True
                monitor_thread.start()
                
            else:
                # دانلود تک‌نخی
                thread = threading.Thread(
                    target=self._single_thread_download,
                    args=(download_id, url, file_path)
                )
                thread.daemon = True
                thread.start()
            
            download_info['status'] = 'downloading'
            return download_id
            
        except Exception as e:
            logger.error(f"خطا در شروع دانلود: {str(e)}")
            if download_id in self.downloads:
                self.downloads[download_id]['status'] = 'error'
                self.downloads[download_id]['error'] = str(e)
            raise
    
    def _single_thread_download(self, download_id, url, file_path):
        """دانلود با یک نخ"""
        download_info = self.downloads[download_id]
        
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                download_info['total_size'] = total_size
                
                with open(file_path, 'wb') as f:
                    start_time = time.time()
                    last_update_time = start_time
                    downloaded_size = 0
                    
                    for chunk in r.iter_content(chunk_size=8192):
                        if download_info.get('cancelled', False):
                            download_info['status'] = 'cancelled'
                            return
                            
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            download_info['downloaded_size'] = downloaded_size
                            
                            # بروزرسانی سرعت دانلود
                            current_time = time.time()
                            if current_time - last_update_time >= 1:
                                speed = (downloaded_size - download_info.get('last_size', 0)) / (current_time - last_update_time)
                                download_info['speed'] = speed
                                download_info['last_size'] = downloaded_size
                                last_update_time = current_time
                
                # اتمام دانلود
                download_info['status'] = 'completed'
                download_info['completed'] = True
                download_info['end_time'] = time.time()
                
                # اضافه کردن به تاریخچه
                self._add_to_history(download_info)
                
        except Exception as e:
            logger.error(f"خطا در دانلود: {str(e)}")
            download_info['status'] = 'error'
            download_info['error'] = str(e)
            
            # اضافه کردن به تاریخچه
            self._add_to_history(download_info)
    
    def _thread_callback(self, thread, download_id, error=None):
        """فراخوانی پس از اتمام یک نخ"""
        download_info = self.downloads.get(download_id)
        if not download_info:
            return
            
        if error:
            download_info['status'] = 'error'
            download_info['error'] = error
    
    def _monitor_download(self, download_id):
        """نظارت بر وضعیت کلی دانلود چند‌نخی"""
        download_info = self.downloads.get(download_id)
        if not download_info:
            return
            
        # بررسی وضعیت نخ‌ها
        while True:
            if download_info.get('cancelled', False):
                download_info['status'] = 'cancelled'
                return
                
            all_completed = all(t.completed for t in download_info['threads'])
            any_error = any(hasattr(t, 'error') and t.error for t in download_info['threads'])
            
            if all_completed or any_error:
                break
                
            # بروزرسانی پیشرفت کلی
            total_downloaded = sum(t.downloaded_size for t in download_info['threads'])
            total_speed = sum(t.speed for t in download_info['threads'])
            
            download_info['downloaded_size'] = total_downloaded
            download_info['speed'] = total_speed
            
            time.sleep(0.5)
        
        if any_error:
            download_info['status'] = 'error'
            download_info['error'] = "خطا در دانلود چند‌نخی"
            # اضافه کردن به تاریخچه
            self._add_to_history(download_info)
            return
            
        # ادغام قطعات دانلود شده
        try:
            self._merge_parts(download_info)
            download_info['status'] = 'completed'
            download_info['completed'] = True
            download_info['end_time'] = time.time()
            # اضافه کردن به تاریخچه
            self._add_to_history(download_info)
        except Exception as e:
            logger.error(f"خطا در ادغام قطعات دانلود: {str(e)}")
            download_info['status'] = 'error'
            download_info['error'] = f"خطا در ادغام قطعات دانلود: {str(e)}"
            # اضافه کردن به تاریخچه
            self._add_to_history(download_info)
    
    def _merge_parts(self, download_info):
        """ادغام قطعات دانلود شده در فایل نهایی"""
        file_path = download_info['file_path']
        save_path = download_info['save_path']
        filename = download_info['filename']
        
        with open(file_path, 'wb') as output_file:
            for i, thread in enumerate(download_info['threads']):
                part_filename = f"{filename}.part{i}"
                part_path = os.path.join(save_path, part_filename)
                
                with open(part_path, 'rb') as part_file:
                    output_file.write(part_file.read())
                
                # حذف فایل بخشی
                os.remove(part_path)
    
    def get_download_status(self, download_id):
        """دریافت وضعیت دانلود"""
        if download_id not in self.downloads:
            return {'status': 'not_found'}
            
        download_info = self.downloads[download_id]
        status_info = {
            'id': download_id,
            'status': download_info['status'],
            'filename': download_info['filename'],
            'downloaded_size': download_info['downloaded_size'],
            'total_size': download_info['total_size'],
            'speed': download_info['speed'],
            'progress': 0 if download_info['total_size'] == 0 else 
                        (download_info['downloaded_size'] / download_info['total_size']) * 100
        }
        
        return status_info
    
    def cancel_download(self, download_id):
        """لغو دانلود در حال انجام"""
        if download_id not in self.downloads:
            return False
            
        download_info = self.downloads[download_id]
        download_info['cancelled'] = True
        
        # توقف نخ‌ها
        for thread in download_info.get('threads', []):
            thread.stop()
        
        download_info['status'] = 'cancelled'
        
        return True
    
    def add_to_queue(self, url):
        """افزودن URL به صف دانلود"""
        if url not in self.download_queue:
            self.download_queue.append(url)
        return len(self.download_queue)
    
    def remove_from_queue(self, index):
        """حذف URL از صف دانلود"""
        if 0 <= index < len(self.download_queue):
            del self.download_queue[index]
        return len(self.download_queue)
    
    def get_queue(self):
        """دریافت لیست صف دانلود"""
        return self.download_queue
    
    def process_queue(self, save_path, thread_count=1, use_threads=True):
        """پردازش صف دانلود"""
        if self.queue_processing or not self.download_queue:
            return False
            
        self.queue_processing = True
        
        def process_thread():
            while self.download_queue and self.queue_processing:
                url = self.download_queue[0]
                try:
                    download_id = self.start_download(url, save_path, thread_count, use_threads)
                    
                    # انتظار تا اتمام دانلود
                    while download_id in self.downloads:
                        status = self.get_download_status(download_id)
                        if status['status'] in ['completed', 'error', 'cancelled']:
                            break
                        time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"خطا در پردازش صف دانلود: {str(e)}")
                
                # حذف از صف
                if self.download_queue:
                    self.download_queue.pop(0)
            
            self.queue_processing = False
        
        queue_thread = threading.Thread(target=process_thread)
        queue_thread.daemon = True
        queue_thread.start()
        
        return True
    
    def _add_to_history(self, download_info):
        """افزودن دانلود به تاریخچه"""
        history_item = {
            'id': download_info['id'],
            'url': download_info['url'],
            'filename': download_info['filename'],
            'file_path': download_info['file_path'],
            'save_path': download_info['save_path'],
            'total_size': download_info['total_size'],
            'status': download_info['status'],
            'start_time': download_info.get('start_time'),
            'end_time': download_info.get('end_time'),
            'duration': download_info.get('end_time', time.time()) - download_info.get('start_time', time.time()),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.download_history.append(history_item)
        return history_item
    
    def get_history(self):
        """دریافت تاریخچه دانلود"""
        return self.download_history
    
    def clear_history(self):
        """پاک کردن تاریخچه دانلود"""
        self.download_history = []
        return True
