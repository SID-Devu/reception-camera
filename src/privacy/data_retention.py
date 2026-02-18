from datetime import datetime, timedelta
import json
import os

class DataRetentionPolicy:
    def __init__(self, retention_period_days=30):
        self.retention_period = timedelta(days=retention_period_days)

    def should_delete(self, record_date):
        return datetime.now() - record_date > self.retention_period

    def cleanup_old_data(self, data_directory):
        for filename in os.listdir(data_directory):
            file_path = os.path.join(data_directory, filename)
            if os.path.isfile(file_path):
                record_date = self.get_record_date(file_path)
                if self.should_delete(record_date):
                    os.remove(file_path)

    def get_record_date(self, file_path):
        # Assuming the file name contains the date in the format 'YYYY-MM-DD'
        file_name = os.path.basename(file_path)
        date_str = file_name.split('_')[0]  # Example: '2023-10-01_data.json'
        return datetime.strptime(date_str, '%Y-%m-%d')

    def save_policy(self, policy_file):
        with open(policy_file, 'w') as f:
            json.dump({'retention_period_days': self.retention_period.days}, f)

    def load_policy(self, policy_file):
        if os.path.exists(policy_file):
            with open(policy_file, 'r') as f:
                policy_data = json.load(f)
                self.retention_period = timedelta(days=policy_data['retention_period_days'])