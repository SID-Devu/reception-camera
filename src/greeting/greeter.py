from tts_engine import TextToSpeech

class Greeter:
    def __init__(self):
        self.tts_engine = TextToSpeech()

    def greet(self, name):
        greeting_message = f"Hello, {name}! Welcome!"
        self.tts_engine.speak(greeting_message)

    def say_goodbye(self, name):
        goodbye_message = f"Goodbye, {name}! Have a great day!"
        self.tts_engine.speak(goodbye_message)

    def greet_or_bye(self, name, is_arrival):
        if is_arrival:
            self.greet(name)
        else:
            self.say_goodbye(name)