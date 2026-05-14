import pygame
import os
from src.core.event_bus import bus

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class AudioService:
    def __init__(self, audio_dir=None):
        self.audio_dir = audio_dir or os.path.join(_BASE_DIR, 'audio')
        pygame.mixer.init()
        self.active_channels = {}
        self.sounds = {}
        os.makedirs(self.audio_dir, exist_ok=True)

    def play_ambient(self, sound_name, volume=0.5, fade_ms=2000):
        # sound_name should be the filename without extension if possible
        file_path = os.path.join(self.audio_dir, f"{sound_name}.mp3")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.audio_dir, f"{sound_name}.wav")
        
        if not os.path.exists(file_path):
            return f"Sound file for {sound_name} not found in {self.audio_dir}."

        if sound_name in self.active_channels:
            return f"{sound_name} is already playing."

        sound = pygame.mixer.Sound(file_path)
        channel = pygame.mixer.find_channel()
        if channel:
            from src.modes.ambient_ui import AmbientUI
            bus.publish("ui.add_tab", "Ambient", lambda p: AmbientUI(p, self))
            
            channel.set_volume(volume)
            channel.play(sound, loops=-1, fade_ms=fade_ms)
            self.active_channels[sound_name] = channel
            self.sounds[sound_name] = sound
            return f"Playing {sound_name}."
        return "No available audio channels."

    def stop_ambient(self, sound_name, fade_ms=2000):
        if sound_name in self.active_channels:
            self.active_channels[sound_name].fadeout(fade_ms)
            del self.active_channels[sound_name]
            return f"Stopped {sound_name}."
        return f"{sound_name} is not playing."

    def set_volume(self, sound_name, volume):
        if sound_name in self.active_channels:
            self.active_channels[sound_name].set_volume(volume)
            return f"Volume for {sound_name} set to {int(volume*100)}%."
        return f"{sound_name} is not playing."

    def stop_all(self):
        pygame.mixer.fadeout(2000)
        self.active_channels.clear()
        return "All audio stopped."

# Global instance
audio_service = AudioService()
