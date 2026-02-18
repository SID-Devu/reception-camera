from gtts import gTTS
import os
import playsound

class TTS:
    def __init__(self, language='en'):
        self.language = language

    def speak(self, text):
        tts = gTTS(text=text, lang=self.language, slow=False)
        filename = 'temp_audio.mp3'
        tts.save(filename)
        playsound.playsound(filename)
        os.remove(filename)