import pygame
import random #shuffle mode

pygame.mixer.init()
playlist = ['maintitle.mp3', 'Oogway Ascends.mp3']
index = 0

is_playing = False
loopmode = False
shufflemode = False

def setvolume(val):
    volume = float(val)/100
    pygame.mixer.music.set_volume(volume)


def playmusic(play):
    global is_playing
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()
    play.config(text="Pause")
    is_playing = True

def pausemusic(play):
    global is_playing
    if is_playing:
        pygame.mixer.music.pause()
        play.config(text="▶️")
        is_playing = False
    else:
        pygame.mixer.music.load(playlist[index])
        pygame.mixer.music.play()
        play.config(text="⏸")
        is_playing = True
    
def nextmusic(play):
    global index
    index = (index + 1) % len(playlist)
    playmusic(play)

def prevmusic(play):
    global index
    index = (index - 1) % len(playlist)
    playmusic(play)


def playrandom():
    global index
    previndex = index
    if len(playlist) > 1:
        while True:
            index = random.randint(0, len(playlist) - 1)
            if index != previndex:
                break
    playmusic()

def check_music_end(root):
    if not pygame.mixer.music.get_busy() and is_playing:
        if loopmode:
            playmusic()
        elif shufflemode:
            playrandom()
        else:
            nextmusic()
    root.after(1000, check_music_end, root)#Tkinter method
    #scheules a function to be called after a certain amount of time
    #here, delay is 1000 ms.


def toggleloop(loop):
    global loopmode
    if loopmode:
        loopmode = False
        loop.config(text="Loop OFF")
    else:
        loopmode = True
        loop.config(text="Loop ON")

def toggleshuffle(shuffle):
    global shufflemode
    if shufflemode:
        shufflemode = False
        shuffle.config(text="Shuffle OFF")
    else:
        shufflemode = True
        shuffle.config(text="Shuffle ON")
