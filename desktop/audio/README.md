# Audio Files for Binary

Place your ambient audio files here.
Supported formats: `.mp3`, `.wav`

Binary will look for files matching the keyword used in your voice command.
The filename (without extension) must match the sound key.

## Required Files (to match built-in commands)

| Voice Command            | Expected File      |
|--------------------------|--------------------|
| "play rain"              | `rain.mp3`         |
| "play storm / thunder"   | `storm.mp3`        |
| "play cafe"              | `cafe.mp3`         |
| "play forest"            | `forest.mp3`       |
| "play ocean / waves"     | `ocean.mp3`        |
| "play white noise"       | `white_noise.mp3`  |
| "play brown noise"       | `brown_noise.mp3`  |
| "play fireplace"         | `fireplace.mp3`    |


## Tips
- Use stereo `.mp3` files at 128–192 kbps for best quality with low memory.
- Files loop infinitely, so trim silence at start/end for smooth looping.
