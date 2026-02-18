from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

class SlackNotifier:
    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.channel = os.getenv("SLACK_CHANNEL")

    def send_notification(self, message):
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"Error sending message to Slack: {e.response['error']}")
            return False