
#!/usr/bin/env python3
"""
مانیتورینگ سیستم برای ربات تلگرام
"""

import psutil
import time
import logging
import json
from datetime import datetime

def monitor_system():
    """مانیتورینگ منابع سیستم"""
    while True:
        try:
            # بررسی CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # بررسی RAM
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # بررسی فضای دیسک
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # لاگ کردن اگر منابع زیاد استفاده شده
            if cpu_percent > 80:
                logging.warning(f"High CPU usage: {cpu_percent}%")
                
            if memory_percent > 80:
                logging.warning(f"High memory usage: {memory_percent}%")
                
            if disk_percent > 85:
                logging.warning(f"High disk usage: {disk_percent}%")
            
            # ذخیره آمار
            stats = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            }
            
            with open("system_stats.json", "w") as f:
                json.dump(stats, f, indent=2)
                
            time.sleep(60)  # هر دقیقه بررسی کن
            
        except Exception as e:
            logging.error(f"System monitoring error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor_system()
