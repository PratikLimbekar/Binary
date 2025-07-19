import keyboard

def pausemusic():
    print("Pausing/Playing")
    keyboard.send('play/pause media')

def nexttrack():
    keyboard.send('next track')
    print("Next")

def prevtrack():
    print("Previous")
    keyboard.send('previous track')