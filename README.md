# dw_anki
Script to grab all of the vocab words from the Deutsche Welle lessons and create Anki flashcards. Flashcards use the audio and images for each word if they exist.

## setup
1. Start Anki and install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon.
2. Edit hardcodes until options are ever added.
- URL for the root of the lesson A1, A2, B1, etc.
- Deck name. This needs to be created in Anki as well
3. python3 -m venv area_name
4. cd area_name
5. git clone git@github.com:brkhrdt/dw_anki.git
6. cd dw_anki
7. python3 setup.py install
8. dw_anki

Downloads all images to $PWD/images and audio to $PWD/audio.

To resize audio/images in linux:
find . -maxdepth 1 -iname "*mp3" | xargs -L1 -I{} lame -b 32 "{}" 32/"{}"
find . -maxdepth 1 -iname "*" | xargs -L1 -I{} convert -resize 25% "{}" resized/"{}"
