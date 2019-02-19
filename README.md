# dw_anki
Script to grab all of the vocab words from the Deutsche Welle lessons and create Anki flashcards. Flashcards use the audo and images for each word if they exist.

## setup
1. Start Anki and install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon.
2. Edit hardcodes until options are ever added.
- URL for the root of the lesson A1, A2, B1, etc.
- Deck name. This needs to be created in Anki as well
2. python3 setup.py install
3. dw_anki

Downloads all images to $PWD/images and audio to $PWD/audio.
