"""
Voice input → text

Display the text (for clarity)

Send it to the chatbot

Speak the chatbot's response
"""

import pyaudio #to interact with the mic
import speech_recognition as sr
from dotenv import load_dotenv
import os
import pvporcupine #hotword detection
import struct #to process the raw audio buffer by converting binary data into something useful
import pyttsx3
import threading




load_dotenv()
apikey = os.getenv('porcupine_key')
porcupine = pvporcupine.create(keyword_paths=["Binary.ppn"], access_key=apikey)

engine = pyttsx3.init()
engine.setProperty('rate', 200)
engine.setProperty('volume', 0.9)

def warmupmic():
    """
    Warms up microphone once to avoid delay later.
    Nothing processed or sent."""

    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2) #the first 0.2 s of audio input is used to calibrate according to the ambient noise
            recognizer.listen(source, timeout=2) #waits for 1 second (timeout)
            #phrase time limit sets the max no of seconds to wait while user speaks.
    except:
        pass 

def listentouser():
    """
    listens for INPUT after hotword recognized.
    """
    recogniser = sr.Recognizer()
    with sr.Microphone() as source: #opens mic stream
        recogniser.adjust_for_ambient_noise(source, duration=0.3)
        print("Say something...")
        try:
            audio = recogniser.listen(source, timeout=3, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            print("Timeout")
            return "Listening time out. Try again."
        except sr.UnknownValueError:
            print("Sorry. Nahi samjha. ")
            return None

    try:
        a = recogniser.recognize_google(audio, language='en-IN')
        print("You said: ", a)
        return a
    except sr.UnknownValueError:
        print("Sorry. No value obtained.")
        return None
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        try:
            a = recogniser.recognize_sphinx(audio)
            print("Trying offline: ", a)
            return a
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand that (even offline).")
            return None
        except sr.RequestError as e:
            print("Offline recognition also failed.")
            return None
        except sr.WaitTimeoutError as e:
            return None
    
print("Listening for hotword...")

def detect_hotword():
    """
    Detect the hotword using Porcupine. 
    This function will continuously listen for the hotword and return True when detected.
    """
    p = pyaudio.PyAudio()
    # setting up PyAudio stream
    stream = p.open(rate=porcupine.sample_rate,  # matches sample rate of Porcupine
                    channels=1,  # mono audio stream
                    format=pyaudio.paInt16,  # 16-bit audio format
                    input=True,
                    frames_per_buffer=porcupine.frame_length  # frame size matches as expected by Porcupine
                    )
    try:
        while True:
            # read audio buffer from mic
            audiobuffer = stream.read(porcupine.frame_length)
            # convert audio to int values (bin to readable data)
            audiodata = struct.unpack_from("h" * porcupine.frame_length, audiobuffer)

            # check for hotword
            keywordindex = porcupine.process(audiodata)
            if keywordindex >= 0:
                print("Binary detected! Triggering the chatbot..")
                return True
    except Exception as e:
        print(f"Error during hotword detection: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def speakresponse(text):
    engine.say(text)
    engine.runAndWait()