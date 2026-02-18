from notifications.channels.slack import SlackNotifier
from notifications.channels.email import EmailNotifier

class Notifier:
    def __init__(self):
        self.slack_notifier = SlackNotifier()
        self.email_notifier = EmailNotifier()

    def notify_entry(self, person_name):
        message = f"Welcome {person_name}! You have entered the premises."
        self.slack_notifier.send_notification(message)
        self.email_notifier.send_notification(message)

    def notify_exit(self, person_name):
        message = f"Goodbye {person_name}! You have exited the premises."
        self.slack_notifier.send_notification(message)
        self.email_notifier.send_notification(message)