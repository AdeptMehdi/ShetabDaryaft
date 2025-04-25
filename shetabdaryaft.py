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
        super().__init__(themename="superhero")
        
        self.title("ShetabDaryaft - دانلودر پرسرعت")
        self.geometry("800x600")
        self.minsize(800, 600)
        
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
        
        title_label = ttk.Label(title_frame, text="ShetabDaryaft", font=("Helvetica", 24, "bold"))
        title_label.pack(anchor=W)
        
        subtitle_label = ttk.Label(title_frame, text="دانلودر پرسرعت و کاربردی", font=("Helvetica", 12))
        subtitle_label.pack(anchor=W)
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)
        
        # URL input
        url_frame = ttk.Frame(content_frame)
        url_frame.pack(fill=X, pady=10)
        
        url_label = ttk.Label(url_frame, text="URL:", font=("Helvetica", 12))
        url_label.pack(side=LEFT, padx=(0, 10))
        
        self.url_entry = ttk.Entry(url_frame, font=("Helvetica", 12))
        self.url_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_url, bootstyle=INFO)
        paste_button.pack(side=LEFT, padx=5)
        
        clear_button = ttk.Button(url_frame, text="Clear", command=self.clear_url, bootstyle=SECONDARY)
        clear_button.pack(side=LEFT)
        
        # Save location
        save_frame = ttk.Frame(content_frame)
        save_frame.pack(fill=X, pady=10)
        
        save_label = ttk.Label(save_frame, text="Save To:", font=("Helvetica", 12))
        save_label.pack(side=LEFT, padx=(0, 10))
        
        self.save_entry = ttk.Entry(save_frame, font=("Helvetica", 12))
        self.save_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        browse_button = ttk.Button(save_frame, text="Browse", command=self.browse_location, bootstyle=INFO)
        browse_button.pack(side=LEFT, padx=5)
        
        # Advanced options - Thread count for multi-threaded download
        advanced_frame = ttk.Labelframe(content_frame, text="Advanced Options", padding=10)
        advanced_frame.pack(fill=X, pady=10)
        
        thread_frame = ttk.Frame(advanced_frame)
        thread_frame.pack(fill=X)
        
        thread_label = ttk.Label(thread_frame, text="Download Threads:", font=("Helvetica", 11))
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
        
        thread_info = ttk.Label(thread_frame, text="(Higher values = faster downloads, but may strain your connection)", font=("Helvetica", 9))
        thread_info.pack(side=LEFT, padx=10)
        
        # Checkbox for using multi-threaded download
        self.use_threaded_var = tk.BooleanVar(value=True)
        threaded_check = ttk.Checkbutton(
            advanced_frame, 
            text="Use multi-threaded download (recommended for faster speeds)", 
            variable=self.use_threaded_var,
            bootstyle="round-toggle"
        )
        threaded_check.pack(fill=X, pady=5)
        
        # Download button
        self.download_button = ttk.Button(
            content_frame, 
            text="Start Download", 
            command=self.start_download, 
            bootstyle=SUCCESS,
            width=20
        )
        self.download_button.pack(pady=15)
        
        # Progress information
        progress_frame = ttk.Labelframe(content_frame, text="Download Progress", padding=15)
        progress_frame.pack(fill=X, pady=10)
        
        # Filename label
        filename_frame = ttk.Frame(progress_frame)
        filename_frame.pack(fill=X, pady=5)
        
        ttk.Label(filename_frame, text="File:", width=12).pack(side=LEFT)
        self.filename_var = tk.StringVar()
        ttk.Label(filename_frame, textvariable=self.filename_var).pack(side=LEFT, fill=X, expand=True)
        
        # Size information
        size_frame = ttk.Frame(progress_frame)
        size_frame.pack(fill=X, pady=5)
        
        ttk.Label(size_frame, text="Size:", width=12).pack(side=LEFT)
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
        
        ttk.Label(status_frame, text="Status:", width=12).pack(side=LEFT)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=LEFT)
        
        self.speed_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.speed_var).pack(side=RIGHT)
        
        # Recent downloads list
        history_frame = ttk.Labelframe(content_frame, text="Recent Downloads", padding=15)
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
            self.download_button.configure(text="Start Download", bootstyle=SUCCESS)
            self.status_var.set("Canceled")
            return
            
        # Get URL and save path
        url = self.url_entry.get().strip()
        save_dir = self.save_entry.get().strip()
        
        # Validate inputs
        if not url:
            messagebox.showerror("Error", "Please enter a URL to download")
            return
            
        if not save_dir or not os.path.isdir(save_dir):
            messagebox.showerror("Error", "Please select a valid save location")
            return
            
        # Reset progress variables
        self.progress_var.set(0)
        self.status_var.set("Connecting...")
        self.size_var.set("")
        self.speed_var.set("")
        self.filename_var.set("")
        
        # Start download in a separate thread
        self.downloading = True
        self.canceled = False
        self.download_button.configure(text="Cancel Download", bootstyle=DANGER)
        
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
            
            # Start download with streaming to track progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size if available
            file_size = int(response.headers.get('content-length', 0))
            if file_size:
                self.size_var.set(f"{file_size / 1024 / 1024:.2f} MB")
            else:
                self.size_var.set("Unknown")
                
            # Variables for progress tracking
            downloaded = 0
            start_time = time.time()
            chunk_size = 8192
            
            # Open file for writing
            with open(save_path, 'wb') as f:
                self.status_var.set("Downloading...")
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.canceled:
                        raise Exception("Download canceled by user")
                        
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
                                
            # Download completed
            self.status_var.set("Completed")
            self.progress_var.set(100)
            
            # Add to history
            current_date = time.strftime("%Y-%m-%d %H:%M")
            size_text = self.size_var.get()
            if not size_text or size_text == "Unknown":
                file_stats = os.stat(save_path)
                size_text = f"{file_stats.st_size / 1024 / 1024:.2f} MB"
                
            self.history_tree.insert("", "end", values=(filename, size_text, current_date, "Completed"))
            
            # Notify user
            messagebox.showinfo("Success", f"File downloaded successfully to:\n{save_path}")
            
        except Exception as e:
            error_msg = str(e)
            self.status_var.set(f"Error: {error_msg}")
            
            if not self.canceled:
                messagebox.showerror("Download Error", f"Failed to download file: {error_msg}")
                
            # Add to history if canceled
            if self.canceled:
                current_date = time.strftime("%Y-%m-%d %H:%M")
                self.history_tree.insert("", "end", values=(filename, self.size_var.get(), current_date, "Canceled"))
                
        finally:
            # Reset button and state
            self.downloading = False
            self.download_button.configure(text="Start Download", bootstyle=SUCCESS)

if __name__ == "__main__":
    app = ShetabDaryaft()
    app.mainloop()
