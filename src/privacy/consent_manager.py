from datetime import datetime
import json
import os

class ConsentManager:
    def __init__(self, consent_file='consent.json'):
        self.consent_file = consent_file
        self.consent_data = self.load_consent_data()

    def load_consent_data(self):
        if os.path.exists(self.consent_file):
            with open(self.consent_file, 'r') as file:
                return json.load(file)
        return {}

    def save_consent_data(self):
        with open(self.consent_file, 'w') as file:
            json.dump(self.consent_data, file)

    def give_consent(self, user_id):
        self.consent_data[user_id] = {
            'consent_given': True,
            'timestamp': datetime.now().isoformat()
        }
        self.save_consent_data()

    def revoke_consent(self, user_id):
        if user_id in self.consent_data:
            self.consent_data[user_id]['consent_given'] = False
            self.save_consent_data()

    def check_consent(self, user_id):
        return self.consent_data.get(user_id, {}).get('consent_given', False)

    def get_consent_info(self, user_id):
        return self.consent_data.get(user_id, None)