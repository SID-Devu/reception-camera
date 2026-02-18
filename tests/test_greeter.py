from src.greeting.greeter import Greeter
from unittest import TestCase
from unittest.mock import patch

class TestGreeter(TestCase):
    @patch('src.greeting.greeter.TTS')
    def test_greet_person(self, mock_tts):
        greeter = Greeter()
        name = "Alice"
        greeting_message = greeter.greet(name)
        
        self.assertEqual(greeting_message, "Hello, Alice! Welcome!")
        mock_tts.speak.assert_called_once_with(greeting_message)

    @patch('src.greeting.greeter.TTS')
    def test_farewell_person(self, mock_tts):
        greeter = Greeter()
        name = "Bob"
        farewell_message = greeter.farewell(name)
        
        self.assertEqual(farewell_message, "Goodbye, Bob! Have a great day!")
        mock_tts.speak.assert_called_once_with(farewell_message)

    def test_greet_empty_name(self):
        greeter = Greeter()
        greeting_message = greeter.greet("")
        
        self.assertEqual(greeting_message, "Hello! Welcome!")
        
    def test_farewell_empty_name(self):
        greeter = Greeter()
        farewell_message = greeter.farewell("")
        
        self.assertEqual(farewell_message, "Goodbye! Have a great day!")