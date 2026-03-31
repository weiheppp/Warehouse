import schedule
import time
import json
from datetime import datetime
from threading import Thread
import os


class PromotionScheduler:
    def schedule_daily_analysis(self, run_ai_analysis):

        #schedule.every(5).minutes.do(run_ai_analysis)
        schedule.every(24).hours.do(run_ai_analysis)
        #schedule.every().day.at("00:00").do(run_ai_analysis)
        #schedule.every().day.at("06:00").do(run_ai_analysis)
        #schedule.every().day.at("12:00").do(run_ai_analysis)
        #schedule.every().day.at("18:00").do(run_ai_analysis)

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # check time every 60s

        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    def load_latest_report(self, latest_report, last_analysis_time):

        try:
            latest_path = 'reports/latest_report.json'
            if os.path.exists(latest_path):
                with open(latest_path, 'r', encoding='utf-8') as f:
                    latest_report = json.load(f)

                file_mtime = os.path.getmtime(latest_path)
                last_analysis_time = datetime.fromtimestamp(file_mtime)

                print(f" Loaded cached report from {last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(" No cached report found, will generate on first request or at 06:00")
        except Exception as e:
            print(f"✗ Error loading cached report: {e}")