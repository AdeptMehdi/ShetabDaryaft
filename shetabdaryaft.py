import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import threading
import os
import time
from PIL import Image, ImageTk
from io import BytesIO
import urllib.parse
import sys
import concurrent.futures
import math

class ShetabDaryaft(ttk.Window):
    def __init__(self):
        super().__init__(themename="vapor")
        
        self.title("شتاب‌دریافت - دانلودر پرسرعت")
        self.geometry("850x650")
        self.minsize(850, 650)
        
        # Set application icon
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        try:
            icon_path = os.path.join(application_path, "assets", "icon.ico")
            self.iconbitmap(icon_path)
        except:
            pass  # Icon loading failed, continue without icon
            
        # فعال کردن پشتیبانی از راست به چپ برای زبان فارسی
        self.attributes("-toolwindow", 0)
        
        self.init_ui()
        
    def init_ui(self):
        # Create header frame
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=X, padx=20, pady=10)
        
        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
            logo_img = Image.open(logo_path)
            logo_img = logo_img.resize((80, 80), Image.Resampling.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_img)
            
            logo_label = ttk.Label(header_frame, image=logo_photo)
            logo_label.image = logo_photo
            logo_label.pack(side=LEFT, padx=(0, 10))
        except:
            # If logo loading fails, use text instead
            logo_label = ttk.Label(header_frame, text="ShetabDaryaft", font=("Helvetica", 24, "bold"))
            logo_label.pack(side=LEFT, padx=(0, 10))
            
        # Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=LEFT, fill=Y, expand=True)
        
        title_label = ttk.Label(title_frame, text="شتاب‌دریافت", font=("Helvetica", 24, "bold"))
        title_label.pack(anchor=W)
        
        subtitle_label = ttk.Label(title_frame, text="دانلودر پرسرعت و کاربردی", font=("Helvetica", 12))
        subtitle_label.pack(anchor=W)
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)
        
        # URL input
        url_frame = ttk.Frame(content_frame)
        url_frame.pack(fill=X, pady=10)
        
        url_label = ttk.Label(url_frame, text="آدرس:", font=("Helvetica", 12))
        url_label.pack(side=LEFT, padx=(0, 10))
        
        self.url_entry = ttk.Entry(url_frame, font=("Helvetica", 12))
        self.url_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        paste_button = ttk.Button(url_frame, text="چسباندن", command=self.paste_url, bootstyle=INFO)
        paste_button.pack(side=LEFT, padx=5)
        
        clear_button = ttk.Button(url_frame, text="پاک کردن", command=self.clear_url, bootstyle=SECONDARY)
        clear_button.pack(side=LEFT)
        
        # Save location
        save_frame = ttk.Frame(content_frame)
        save_frame.pack(fill=X, pady=10)
        
        save_label = ttk.Label(save_frame, text="ذخیره در:", font=("Helvetica", 12))
        save_label.pack(side=LEFT, padx=(0, 10))
        
        self.save_entry = ttk.Entry(save_frame, font=("Helvetica", 12))
        self.save_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        browse_button = ttk.Button(save_frame, text="جستجو", command=self.browse_location, bootstyle=INFO)
        browse_button.pack(side=LEFT, padx=5)
        
        # Advanced options - Thread count for multi-threaded download
        advanced_frame = ttk.Labelframe(content_frame, text="گزینه‌های پیشرفته", padding=10)
        advanced_frame.pack(fill=X, pady=10)
        
        thread_frame = ttk.Frame(advanced_frame)
        thread_frame.pack(fill=X)
        
        thread_label = ttk.Label(thread_frame, text="تعداد نخ‌های دانلود:", font=("Helvetica", 11))
        thread_label.pack(side=LEFT, padx=(0, 10))
        
        self.thread_var = tk.IntVar(value=8)  # Default to 8 threads
        thread_spinbox = ttk.Spinbox(
            thread_frame, 
            from_=1, 
            to=32, 
            textvariable=self.thread_var, 
            width=5,
            bootstyle=INFO
        )
        thread_spinbox.pack(side=LEFT)
        
        thread_info = ttk.Label(thread_frame, text="(ارزش‌های بالاتر = سرعت دانلود بالاتر، اما ممکن است باعث فشار به ارتباط شما شود)", font=("Helvetica", 9))
        thread_info.pack(side=LEFT, padx=10)
        
        # Checkbox for using multi-threaded download
        self.use_threaded_var = tk.BooleanVar(value=True)
        threaded_check = ttk.Checkbutton(
            advanced_frame, 
            text="استفاده از دانلود چند نخه (پیشنهاد شده برای سرعت‌های بالاتر)", 
            variable=self.use_threaded_var,
            bootstyle="round-toggle"
        )
        threaded_check.pack(fill=X, pady=5)
        
        # Download button
        self.download_button = ttk.Button(
            content_frame, 
            text="شروع دانلود", 
            command=self.start_download, 
            bootstyle=SUCCESS,
            width=20
        )
        self.download_button.pack(pady=15)
        
        # Progress information
        progress_frame = ttk.Labelframe(content_frame, text="پیشرفت دانلود", padding=15)
        progress_frame.pack(fill=X, pady=10)
        
        # Filename label
        filename_frame = ttk.Frame(progress_frame)
        filename_frame.pack(fill=X, pady=5)
        
        ttk.Label(filename_frame, text="فایل:", width=12).pack(side=LEFT)
        self.filename_var = tk.StringVar()
        ttk.Label(filename_frame, textvariable=self.filename_var).pack(side=LEFT, fill=X, expand=True)
        
        # Size information
        size_frame = ttk.Frame(progress_frame)
        size_frame.pack(fill=X, pady=5)
        
        ttk.Label(size_frame, text="اندازه:", width=12).pack(side=LEFT)
        self.size_var = tk.StringVar()
        ttk.Label(size_frame, textvariable=self.size_var).pack(side=LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            bootstyle=SUCCESS
        )
        self.progress_bar.pack(fill=X, pady=10)
        
        # Status and speed information
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=X, pady=5)
        
        ttk.Label(status_frame, text="وضعیت:", width=12).pack(side=LEFT)
        self.status_var = tk.StringVar(value="آماده")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=LEFT)
        
        self.speed_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.speed_var).pack(side=RIGHT)
        
        # Recent downloads list
        history_frame = ttk.Labelframe(content_frame, text="دانلود‌های اخیر", padding=15)
        history_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # Create treeview for download history
        columns = ("Filename", "Size", "Date", "Status")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        
        # Define headings
        for col in columns:
            self.history_tree.heading(col, text=col)
            
        # Set column widths
        self.history_tree.column("Filename", width=250)
        self.history_tree.column("Size", width=100)
        self.history_tree.column("Date", width=150)
        self.history_tree.column("Status", width=100)
        
        self.history_tree.pack(fill=BOTH, expand=True)
        
        # Footer
        footer_frame = ttk.Frame(self)
        footer_frame.pack(fill=X, padx=20, pady=10)
        
        # Add the current time
        self.time_var = tk.StringVar()
        self.update_time()
        time_label = ttk.Label(footer_frame, textvariable=self.time_var)
        time_label.pack(side=RIGHT)
        
        # Set default download location
        self.save_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        
        # Initialize download variables
        self.downloading = False
        self.canceled = False
        
    def update_time(self):
        """Update the current time displayed in the footer"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.after(1000, self.update_time)
        
    def paste_url(self):
        """Paste clipboard content to URL entry"""
        try:
            clipboard_text = self.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_text)
        except:
            pass
            
    def clear_url(self):
        """Clear URL entry field"""
        self.url_entry.delete(0, tk.END)
        
    def browse_location(self):
        """Open file dialog to select save location"""
        download_dir = filedialog.askdirectory(initialdir=self.save_entry.get())
        if download_dir:
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, download_dir)
            
    def start_download(self):
        """Initiate the download process"""
        if self.downloading:
            self.canceled = True
            self.download_button.configure(text="شروع دانلود", bootstyle=SUCCESS)
            self.status_var.set("لغو شد")
            return
            
        # Get URL and save path
        url = self.url_entry.get().strip()
        save_dir = self.save_entry.get().strip()
        
        # Validate inputs
        if not url:
            messagebox.showerror("خطا", "لطفا آدرس را وارد کنید")
            return
            
        if not save_dir or not os.path.isdir(save_dir):
            messagebox.showerror("خطا", "لطفا مسیر ذخیره را انتخاب کنید")
            return
            
        # Reset progress variables
        self.progress_var.set(0)
        self.status_var.set("در حال اتصال...")
        self.size_var.set("")
        self.speed_var.set("")
        self.filename_var.set("")
        
        # Start download in a separate thread
        self.downloading = True
        self.canceled = False
        self.download_button.configure(text="لغو دانلود", bootstyle=DANGER)
        
        download_thread = threading.Thread(target=self.download_file, args=(url, save_dir))
        download_thread.daemon = True
        download_thread.start()
        
    def download_file(self, url, save_dir):
        """Download file from URL to specified directory"""
        try:
            # Get filename from URL
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename:
                filename = "download_" + time.strftime("%Y%m%d_%H%M%S")
                
            # Update filename display
            self.filename_var.set(filename)
            
            # Full path for saving
            save_path = os.path.join(save_dir, filename)
            
            # Check if multi-threaded download is enabled
            if self.use_threaded_var.get() and self.thread_var.get() > 1:
                self.download_file_threaded(url, save_path)
            else:
                self.download_file_single(url, save_path)
                
        except Exception as e:
            error_msg = str(e)
            self.status_var.set(f"خطا: {error_msg}")
            
            if not self.canceled:
                messagebox.showerror("خطای دانلود", f"دانلود فایل با خطا مواجه شد: {error_msg}")

    def download_file_single(self, url, save_path):
        """Download file with a single thread (original method)"""
        try:
            # Start download with streaming to track progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size if available
            file_size = int(response.headers.get('content-length', 0))
            if file_size:
                self.size_var.set(f"{file_size / 1024 / 1024:.2f} MB")
            else:
                self.size_var.set("نامشخص")
                
            # Variables for progress tracking
            downloaded = 0
            start_time = time.time()
            chunk_size = 8192
            
            # Open file for writing
            with open(save_path, 'wb') as f:
                self.status_var.set("در حال دانلود...")
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.canceled:
                        raise Exception("دانلود لغو شد توسط کاربر")
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress bar
                        if file_size:
                            progress = (downloaded / file_size) * 100
                            self.progress_var.set(progress)
                            
                        # Calculate and show speed
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0:
                            speed = downloaded / elapsed_time / 1024  # KB/s
                            if speed > 1024:
                                self.speed_var.set(f"{speed / 1024:.2f} MB/s")
                            else:
                                self.speed_var.set(f"{speed:.2f} KB/s")
            
            self.download_complete(save_path)
                
        except Exception as e:
            if not self.canceled:
                raise e
            
    def download_file_threaded(self, url, save_path):
        """Download file using multiple threads for higher speed"""
        try:
            # Get file info to check if it supports range requests
            response = requests.head(url, timeout=10)
            response.raise_for_status()
            
            # Check if server supports range requests
            if 'accept-ranges' not in response.headers or response.headers['accept-ranges'] != 'bytes':
                self.status_var.set("سرور از دانلود چند نخه پشتیبانی نمی‌کند، از روش تک نخه استفاده می‌شود")
                self.download_file_single(url, save_path)
                return
                
            # Get total file size
            try:
                file_size = int(response.headers.get('content-length', 0))
                if not file_size:
                    raise ValueError("اندازه فایل نامشخص")
            except (ValueError, TypeError):
                self.status_var.set("اندازه فایل نامشخص، از روش تک نخه استفاده می‌شود")
                self.download_file_single(url, save_path)
                return
                
            # Update size display
            self.size_var.set(f"{file_size / 1024 / 1024:.2f} MB")
            
            # Determine number of segments based on file size
            num_threads = min(self.thread_var.get(), 32)  # Maximum 32 threads
            
            # For very small files, reduce thread count to avoid overhead
            if file_size < 1024 * 1024:  # Less than 1 MB
                num_threads = 1
            elif file_size < 5 * 1024 * 1024:  # Less than 5 MB
                num_threads = min(4, num_threads)
                
            # Calculate segment size
            segment_size = math.ceil(file_size / num_threads)
            
            # Create empty file with correct size
            with open(save_path, 'wb') as f:
                f.seek(file_size - 1)
                f.write(b'\0')
                
            # Set up variables for progress tracking
            self.downloaded_bytes = 0
            self.start_time = time.time()
            self.lock = threading.Lock()
            
            # Create segments
            segments = []
            for i in range(num_threads):
                start_byte = i * segment_size
                end_byte = min(start_byte + segment_size - 1, file_size - 1)
                
                # Skip empty segments (shouldn't happen, but just in case)
                if start_byte >= file_size:
                    continue
                    
                segments.append({
                    'id': i,
                    'start': start_byte,
                    'end': end_byte,
                    'url': url,
                    'path': save_path
                })
                
            # Start status update thread
            self.status_updater = threading.Thread(target=self.update_download_status, args=(file_size,))
            self.status_updater.daemon = True
            self.status_updater.start()
            
            # Status message
            self.status_var.set(f"دانلود با {len(segments)} نخ...")
            
            # Download all segments using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(self.download_segment, segment) for segment in segments]
                
                # Wait for all downloads to complete or for cancellation
                for future in concurrent.futures.as_completed(futures):
                    if self.canceled:
                        # Cancel all future tasks if canceled
                        for f in futures:
                            f.cancel()
                        raise Exception("دانلود لغو شد توسط کاربر")
                    
                    # Get result of completed future, will raise exception if it failed
                    result = future.result()
            
            # Download completed
            self.download_complete(save_path)
            
        except Exception as e:
            if not self.canceled:
                if os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except:
                        pass
                raise e
    
    def download_segment(self, segment):
        """Download a specific segment of the file"""
        if self.canceled:
            return
            
        try:
            headers = {'Range': f'bytes={segment["start"]}-{segment["end"]}'}
            response = requests.get(segment["url"], headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Open file in rb+ mode (read-write binary)
            with open(segment["path"], 'rb+') as f:
                # Seek to the correct position
                f.seek(segment["start"])
                
                # Write the segment data
                for chunk in response.iter_content(chunk_size=8192):
                    if self.canceled:
                        return
                        
                    if chunk:
                        f.write(chunk)
                        
                        # Update progress
                        with self.lock:
                            self.downloaded_bytes += len(chunk)
                            
            return True
            
        except Exception as e:
            if not self.canceled:
                raise Exception(f"خطا در نخ {segment['id']}: {str(e)}")
    
    def update_download_status(self, total_size):
        """Update the download progress and speed in a separate thread"""
        last_update_time = time.time()
        last_bytes = 0
        
        while not self.canceled and self.downloading:
            try:
                current_time = time.time()
                elapsed = current_time - last_update_time
                
                if elapsed >= 0.5:  # Update every half second
                    # Calculate instantaneous speed based on recent progress
                    with self.lock:
                        current_bytes = self.downloaded_bytes
                        
                    bytes_diff = current_bytes - last_bytes
                    speed = bytes_diff / elapsed / 1024  # KB/s
                    
                    # Update progress
                    progress = (current_bytes / total_size) * 100
                    self.progress_var.set(progress)
                    
                    # Update speed display
                    if speed > 1024:
                        self.speed_var.set(f"{speed / 1024:.2f} MB/s")
                    else:
                        self.speed_var.set(f"{speed:.2f} KB/s")
                        
                    # Reset for next update
                    last_update_time = current_time
                    last_bytes = current_bytes
                    
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
                
            except Exception:
                # If there's an error, just try again on the next loop
                time.sleep(0.5)
                
        return
        
    def download_complete(self, save_path):
        """Handle operations after a successful download"""
        # Download completed
        self.status_var.set("کامل شد")
        self.progress_var.set(100)
        
        # Add to history
        current_date = time.strftime("%Y-%m-%d %H:%M")
        size_text = self.size_var.get()
        if not size_text or size_text == "Unknown":
            file_stats = os.stat(save_path)
            size_text = f"{file_stats.st_size / 1024 / 1024:.2f} MB"
            
        self.history_tree.insert("", "end", values=(os.path.basename(save_path), size_text, current_date, "کامل شد"))
        
        # Notify user
        messagebox.showinfo("موفقیت", f"فایل با موفقیت دانلود شد به:\n{save_path}")
        
        # Reset button and state
        self.downloading = False
        self.download_button.configure(text="شروع دانلود", bootstyle=SUCCESS)

if __name__ == "__main__":
    app = ShetabDaryaft()
    app.mainloop()
