/**
 * شتاب‌دریافت - اسکریپت اصلی
 * مدیریت عملکرد سمت کلاینت برنامه دانلود منیجر فارسی
 */

// متغیرهای سراسری
let currentDownloadId = null;
let statusCheckInterval = null;
let queueItems = [];
let historyItems = [];
let defaultDownloadPath = '';

// تابع اجرا در هنگام بارگذاری صفحه
$(document).ready(function() {
    // بررسی مسیر پیش‌فرض دانلود
    getDefaultDownloadPath();
    
    // بارگیری صف و تاریخچه
    refreshQueueList();
    refreshHistoryList();
    
    // رویدادهای دکمه‌ها
    setupEventListeners();
});

/**
 * تنظیم گوش‌دهندگان رویداد برای تمام المان‌های تعاملی
 */
function setupEventListeners() {
    // دکمه چسباندن URL
    $('#paste-btn').click(function() {
        // در وب نمی‌توان به کلیپ‌بورد دسترسی داشت، پیام راهنما نمایش دهیم
        alert('لطفاً آدرس موردنظر را در فیلد وارد کنید.');
    });
    
    // دکمه پاک کردن URL
    $('#clear-btn').click(function() {
        $('#download-url').val('');
    });
    
    // دکمه انتخاب مسیر
    $('#browse-btn').click(function() {
        // در وب از مودال استفاده می‌کنیم
        $('#modal-folder-path').val($('#save-path').val() || defaultDownloadPath);
        $('#folder-modal').modal('show');
    });
    
    // دکمه تأیید انتخاب پوشه در مودال
    $('#confirm-folder-btn').click(function() {
        const path = $('#modal-folder-path').val();
        $('#save-path').val(path);
        $('#folder-modal').modal('hide');
    });
    
    // دکمه شروع دانلود
    $('#download-btn').click(startDownload);
    
    // دکمه لغو دانلود
    $('#cancel-btn').click(cancelCurrentDownload);
    
    // فعال/غیرفعال کردن تنظیم نخ
    $('#use-threads').change(function() {
        $('#thread-count').prop('disabled', !this.checked);
    });
    
    // دکمه‌های صف دانلود
    $('#add-queue-btn').click(addToQueue);
    $('#remove-queue-btn').click(removeFromQueue);
    $('#process-queue-btn').click(processQueue);
    
    // دکمه‌های تاریخچه
    $('#show-folder-btn').click(showSelectedFolder);
    $('#clear-history-btn').click(clearHistory);
    
    // انتخاب آیتم در صف
    $('#queue-list').on('click', 'li', function() {
        $(this).toggleClass('active').siblings().removeClass('active');
    });
    
    // انتخاب آیتم در تاریخچه
    $('#history-list').on('click', 'tr', function() {
        $(this).toggleClass('table-primary').siblings().removeClass('table-primary');
    });
}

/**
 * دریافت مسیر پیش‌فرض برای دانلود
 */
function getDefaultDownloadPath() {
    $.get('/api/browse_location', function(data) {
        defaultDownloadPath = data.default_path;
        $('#save-path').val(defaultDownloadPath);
    });
}

/**
 * تبدیل بایت به فرمت خوانا (کیلوبایت، مگابایت و...)
 */
function formatFileSize(bytes, decimals = 2) {
    if (bytes === 0) return '0 بایت';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت', 'ترابایت'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * فرمت کردن سرعت دانلود
 */
function formatSpeed(bytesPerSecond) {
    return formatFileSize(bytesPerSecond) + '/ثانیه';
}

/**
 * شروع دانلود فایل جدید
 */
function startDownload() {
    const url = $('#download-url').val();
    const savePath = $('#save-path').val() || defaultDownloadPath;
    const useThreads = $('#use-threads').is(':checked');
    const threadCount = $('#thread-count').val();
    
    if (!url) {
        alert('لطفاً یک آدرس URL وارد کنید.');
        return;
    }
    
    // ارسال درخواست به سرور
    $.ajax({
        url: '/api/start_download',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            url: url,
            save_path: savePath,
            thread_count: threadCount,
            use_threads: useThreads
        }),
        success: function(response) {
            if (response.status === 'success') {
                currentDownloadId = response.download_id;
                showProgressSection();
                startStatusChecking();
            } else {
                alert('خطا: ' + response.message);
            }
        },
        error: function() {
            alert('خطا در ارتباط با سرور.');
        }
    });
}

/**
 * نمایش بخش پیشرفت دانلود
 */
function showProgressSection() {
    $('#progress-section').removeClass('d-none');
    $('#download-btn').prop('disabled', true);
    
    // تنظیم مقادیر اولیه
    $('#download-filename span').text('در حال دریافت اطلاعات...');
    $('#download-progress-bar').css('width', '0%').attr('aria-valuenow', 0);
    $('#download-speed').text('0 کیلوبایت/ثانیه');
    $('#downloaded-size').text('0 مگابایت');
    $('#total-size').text('0 مگابایت');
    $('#download-status').text('در حال شروع').removeClass().addClass('status-pending');
}

/**
 * شروع بررسی دوره‌ای وضعیت دانلود
 */
function startStatusChecking() {
    // ابتدا از توقف بررسی قبلی اطمینان حاصل کنیم
    stopStatusChecking();
    
    // بررسی وضعیت هر ثانیه
    statusCheckInterval = setInterval(function() {
        if (!currentDownloadId) {
            stopStatusChecking();
            return;
        }
        
        checkDownloadStatus(currentDownloadId);
    }, 1000);
}

/**
 * توقف بررسی وضعیت دانلود
 */
function stopStatusChecking() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

/**
 * بررسی وضعیت دانلود فعلی
 */
function checkDownloadStatus(downloadId) {
    $.get('/api/download_status/' + downloadId, function(data) {
        if (data.status === 'not_found') {
            stopStatusChecking();
            hideProgressSection();
            return;
        }
        
        // بروزرسانی اطلاعات نمایشی
        $('#download-filename span').text(data.filename);
        $('#download-progress-bar').css('width', data.progress + '%').attr('aria-valuenow', data.progress);
        $('#download-speed').text(formatSpeed(data.speed));
        $('#downloaded-size').text(formatFileSize(data.downloaded_size));
        $('#total-size').text(formatFileSize(data.total_size));
        
        // بروزرسانی وضعیت
        updateStatusDisplay(data.status);
        
        // بررسی اتمام دانلود
        if (['completed', 'error', 'cancelled'].includes(data.status)) {
            downloadCompleted(data.status);
            refreshHistoryList();  // بروزرسانی تاریخچه
        }
    });
}

/**
 * بروزرسانی نمایش وضعیت دانلود
 */
function updateStatusDisplay(status) {
    let statusText = '';
    let statusClass = '';
    
    switch(status) {
        case 'downloading':
            statusText = 'در حال دانلود';
            statusClass = 'status-downloading';
            break;
        case 'completed':
            statusText = 'تکمیل شد';
            statusClass = 'status-success';
            break;
        case 'error':
            statusText = 'خطا';
            statusClass = 'status-error';
            break;
        case 'cancelled':
            statusText = 'لغو شد';
            statusClass = 'status-error';
            break;
        default:
            statusText = 'در انتظار';
            statusClass = 'status-pending';
    }
    
    $('#download-status').text(statusText).removeClass().addClass(statusClass);
}

/**
 * اتمام دانلود (موفق یا ناموفق)
 */
function downloadCompleted(status) {
    stopStatusChecking();
    
    // اگر موفق بود، پس از چند ثانیه بخش پیشرفت را پنهان کنیم
    if (status === 'completed') {
        setTimeout(function() {
            hideProgressSection();
        }, 3000);
    } else {
        // برای خطا یا لغو، دکمه دانلود را فعال کنیم اما بخش پیشرفت را نگه داریم
        $('#download-btn').prop('disabled', false);
    }
    
    currentDownloadId = null;
}

/**
 * مخفی کردن بخش پیشرفت دانلود
 */
function hideProgressSection() {
    $('#progress-section').addClass('d-none');
    $('#download-btn').prop('disabled', false);
}

/**
 * لغو دانلود فعلی
 */
function cancelCurrentDownload() {
    if (!currentDownloadId) return;
    
    $.get('/api/cancel_download/' + currentDownloadId, function() {
        $('#download-status').text('لغو شد').removeClass().addClass('status-error');
    });
}

/**
 * افزودن URL به صف دانلود
 */
function addToQueue() {
    const url = $('#download-url').val();
    
    if (!url) {
        alert('لطفاً یک آدرس URL وارد کنید.');
        return;
    }
    
    $.ajax({
        url: '/api/add_to_queue',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ url: url }),
        success: function(response) {
            if (response.status === 'success') {
                refreshQueueList();
            } else {
                alert('خطا: ' + response.message);
            }
        }
    });
}

/**
 * حذف URL از صف دانلود
 */
function removeFromQueue() {
    const selectedItem = $('#queue-list li.active');
    
    if (selectedItem.length === 0) {
        alert('لطفاً یک آیتم از صف را انتخاب کنید.');
        return;
    }
    
    const index = selectedItem.index();
    
    $.ajax({
        url: '/api/remove_from_queue',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ index: index }),
        success: function(response) {
            if (response.status === 'success') {
                refreshQueueList();
            } else {
                alert('خطا: ' + response.message);
            }
        }
    });
}

/**
 * بروزرسانی لیست صف دانلود
 */
function refreshQueueList() {
    $.get('/api/get_queue', function(data) {
        queueItems = data.queue;
        
        const queueList = $('#queue-list');
        queueList.empty();
        
        if (queueItems.length === 0) {
            queueList.append('<li class="list-group-item text-center">صف دانلود خالی است</li>');
        } else {
            queueItems.forEach(function(url, index) {
                queueList.append(`<li class="list-group-item">${url}</li>`);
            });
        }
    });
}

/**
 * شروع پردازش صف دانلود
 */
function processQueue() {
    const savePath = $('#save-path').val() || defaultDownloadPath;
    const useThreads = $('#use-threads').is(':checked');
    const threadCount = $('#thread-count').val();
    
    $.ajax({
        url: '/api/process_queue',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            save_path: savePath,
            thread_count: threadCount,
            use_threads: useThreads
        }),
        success: function(response) {
            if (response.status === 'success') {
                alert(response.message);
            } else {
                alert('خطا: ' + response.message);
            }
        }
    });
}

/**
 * بروزرسانی لیست تاریخچه دانلود
 */
function refreshHistoryList() {
    $.get('/api/get_history', function(data) {
        historyItems = data.history;
        
        const historyList = $('#history-list');
        historyList.empty();
        
        if (historyItems.length === 0) {
            historyList.append('<tr><td colspan="5" class="text-center">تاریخچه دانلود خالی است</td></tr>');
        } else {
            historyItems.forEach(function(item) {
                // تعیین کلاس وضعیت
                let statusClass = '';
                let statusText = '';
                
                switch(item.status) {
                    case 'completed':
                        statusClass = 'status-success';
                        statusText = 'تکمیل شد';
                        break;
                    case 'error':
                        statusClass = 'status-error';
                        statusText = 'خطا';
                        break;
                    case 'cancelled':
                        statusClass = 'status-error';
                        statusText = 'لغو شد';
                        break;
                    default:
                        statusText = item.status;
                }
                
                historyList.append(`
                    <tr data-path="${item.save_path}">
                        <td>${item.filename}</td>
                        <td>${formatFileSize(item.total_size)}</td>
                        <td>${item.date}</td>
                        <td><span class="${statusClass}">${statusText}</span></td>
                        <td>${item.save_path}</td>
                    </tr>
                `);
            });
        }
    });
}

/**
 * نمایش پوشه انتخاب شده در تاریخچه
 */
function showSelectedFolder() {
    const selectedRow = $('#history-list tr.table-primary');
    
    if (selectedRow.length === 0) {
        alert('لطفاً یک آیتم از تاریخچه را انتخاب کنید.');
        return;
    }
    
    const folderPath = selectedRow.data('path');
    
    $.get('/api/show_folder/' + encodeURIComponent(folderPath), function() {
        alert('در نسخه وب، مستقیماً نمی‌توان پوشه را باز کرد.\nمسیر پوشه: ' + folderPath);
    });
}

/**
 * پاک کردن تاریخچه دانلود
 */
function clearHistory() {
    if (confirm('آیا از پاک کردن کامل تاریخچه دانلود اطمینان دارید؟')) {
        $.get('/api/clear_history', function(response) {
            if (response.status === 'success') {
                refreshHistoryList();
            }
        });
    }
}
