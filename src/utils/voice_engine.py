import os
import struct
import pyaudio
import pyttsx3
import json
import speech_recognition as sr
from dotenv import load_dotenv

# Try importing vosk, but don't crash if missing
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

_vosk_model = None
_engine = None

def _get_vosk_model():
    global _vosk_model
    if not VOSK_AVAILABLE:
        return None
        
    if _vosk_model is None:
        # Look for model in assets/models/vosk-model-small-en-us-0.15
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'models', 'vosk-model-small-en-us-0.15')
        
        if os.path.exists(model_path):
            try:
                _vosk_model = Model(model_path)
                print("Vosk Model loaded successfully.")
            except Exception as e:
                print(f"Error loading Vosk model: {e}")
        else:
            print(f"Warning: Vosk model not found at {model_path}.")
            print("Please download it from https://alphacephei.com/vosk/models and extract to assets/models/")
            
    return _vosk_model

def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty('rate', 200)
        _engine.setProperty('volume', 0.9)
    return _engine

def detect_hotword():
    """Detect the hotword using Vosk (Free Alternative)."""
    model = _get_vosk_model()
    if model is None:
        print("Hotword detection disabled (Vosk model missing).")
        return False
        
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()
    
    rec = KaldiRecognizer(model, 16000)
    
    print("Vosk is listening for 'Binary'...")
    try:
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get('text', '')
                if 'binary' in text.lower():
                    print("Binary detected via Vosk!")
                    return True
    except Exception as e:
        print(f"Error during Vosk hotword detection: {e}")
        return False
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def listentouser():
    """Listens for user input after hotword is detected."""
    recogniser = sr.Recognizer()
    with sr.Microphone() as source:
        recogniser.adjust_for_ambient_noise(source, duration=0.3)
        print("Say something...")
        try:
            audio = recogniser.listen(source, timeout=3, phrase_time_limit=5)
            text = recogniser.recognize_google(audio, language='en-IN')
            print(f"You said: {text}")
            return text
        except sr.WaitTimeoutError:
            print("Listening timeout.")
            return "Listening timed out."
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return None
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return None

def speakresponse(text):
    """Speaks the response using TTS engine."""
    engine = _get_engine()
    if engine:
        engine.say(text)
        engine.runAndWait()

def warmupmic():
    """Warms up the microphone."""
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            recognizer.listen(source, timeout=1)
    except:
        pass