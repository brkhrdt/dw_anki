#!/usr/bin/env python3
from lxml import html
import requests
import os
import json
import base64
import re
import logging
import subprocess #to call lame/convert to resize media
import operator

# Top page for Nicos Weg A1
TOP_URL= 'https://learngerman.dw.com/en/beginners/c-36519789'

DW_URL = 'https://learngerman.dw.com/'
DECK_NAME = 'DW Nicos Weg A1'
IMAGES_DIR = 'images'
AUDIO_DIR = 'audio'
log = logging.getLogger(__name__)

class AnkiCard:
    cardCount = 0
    def __init__(self, deck):
        self.deck = deck
        self.tags = []
        self.english = []
        self.german = []
        self.hasImage = 0
        self.hasAudio = 0
        self.cardNumber = AnkiCard.cardCount
        AnkiCard.cardCount += 1

    def addTag(self, tag):
        (self.tags).append(tag)

    def addEnglish(self, english, imgFilename=None, audioFilename=None):
        audioHTML = ""
        englishHTML = english
        imgHTML = ""
        if audioFilename:
            audioHTML = "[sound:{}]".format(audioFilename)
        if imgFilename:
            imgHTML = '<br><img src="' + imgFilename + '" width="50%" height="50%">'
        (self.english).append(audioHTML + englishHTML + imgHTML)

    def addGerman(self, german, audioFilename=None, imgFilename=None):
        audioHTML = ""
        log.debug("addGerman::german = " + german)
        germanHTML = german
        imgHTML = ""
        if audioFilename:
            audioHTML = "[sound:{}]".format(audioFilename)
        if imgFilename:
            imgHTML = '<img src="' + imgFilename + '" width="50%" height="50%"><br>'
        (self.german).append(audioHTML + germanHTML + imgHTML)
        log.debug("addGerman after: " + ", ".join(self.german))

    def getEnglish(self):
        entries = list(set(self.english)) # remove duplicates
        return "<br><br>".join(entries)

    def getGerman(self):
        entries = list(set(self.german)) # remove duplicates
        return "<br><br>".join(entries)


#
# Interacting with AnkiConnect
#

def request(action, **params):
    return json.dumps({'action': action, 'params': params, 'version': 6})

def invoke(requestJson):
    #requestJson = json.dumps(request(action, **params))
    #response = json.load(urllib2.urlopen(urllib2.Request('http://localhost:8765', requestJson)))
    response = (requests.post('http://localhost:8765', requestJson)).json()
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Warning(response['error'])
    return response['result']

def storeMediaFileJSON(filename, data64):
    request = {
        "action": "storeMediaFile",
        "version": 6,
        "params": {
            "filename": filename,
            "data": data64
        }
    }
    return json.dumps(request)

def createDeckJSON(deck):
    request = {
        "action": "createDeck",
        "version": 6,
        "params": {
            "deck": deck
        }
    }
    return json.dumps(request)

def addNoteJSON(deck, tags, front, back):
    request = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": deck,
                "modelName": "Basic",
                "fields": {
                    "Front": front,
                    "Back": back
                },
                "options": {
                    "allowDuplicate": True
                },
                "tags": tags
            }
        }
    }
    return json.dumps(request)


#
# Parsing data from HTML
#

def getGermanFromRow(reihe):
    try:
        woerter = reihe.xpath('.//strong[@dir="auto"]/text()')
        notizen = reihe.xpath('.//div[1]/div/p/text()')
        notiz = (''.join(notizen)).replace('\n','')
        #//*[@id="html_body"]/div[2]/div/div/div/div[2]/div[3]/div[1]/div/p/text()
        wort = woerter[0]
        if notiz:
            wort = wort + " <br><small><i>" + notiz + "</i></small>"
        return wort
    except:
        log.warning('Failed to find any word on the german side.')
        return None


def getEnglishFromRow(row):
    word = row.xpath('.//div[3]/div/p/text()')
    if not word: # some words randomly in a table
        word = row.xpath('.//div[3]/div/table/tbody/tr/td/text()')
    if word:
        return word[0] #TODO: check that we only got 1?
    log.warning('Failed to find any word on the english side.')
    return None


def getImageURLFromRow(row):
    img_url = row.xpath('.//img[@class="img-responsive"]/@src')
    if not img_url:
        return ""
    #downloadFromURL(DW_URL + img_url[0], os.path.basename(img_url[0]))
    return (DW_URL + img_url[0])


def getAudioURLFromRow(row):
    audio_url = row.xpath('.//source[@type="audio/MP3"]/@src')
    if not audio_url:
        return ""
    return audio_url[0]


def downloadFromURL(url, path):
    if os.path.isfile(path):
        return 1
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in r:
                f.write(chunk)
        return 1
    return 0


def fileToBase64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()

def reduceImageSize(path):
    backupDir = "{}/{}".format(IMAGES_DIR,"backup")
    if not os.path.isdir(backupDir):
        os.mkdir(backupDir)
    fileName = os.path.basename(path)
    backupFilePath = "{}/{}".format(backupDir,fileName)
    # We'll use the backup copy to generate reduced file.
    # If it exists don't copy b/c repeat runs will shrink more
    if not os.path.isfile(backupFilePath):
        os.system("cp {} {}".format(path, backupFilePath))
    res = subprocess.run(["convert", "-resize", "25%", backupFilePath, path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        log.error("Failed to reduce image size: " + path)
    return

def reduceAudioSize(path):
    backupDir = "{}/{}".format(AUDIO_DIR,"backup")
    if not os.path.isdir(backupDir):
        os.mkdir(backupDir)
    fileName = os.path.basename(path)
    backupFilePath = "{}/{}".format(backupDir,fileName)
    # We'll use the backup copy to generate reduced file.
    # If it exists don't copy b/c repeat runs will shrink more
    if not os.path.isfile(backupFilePath):
        os.system("cp {} {}".format(path, backupFilePath))
    res = subprocess.run(["lame", "-b", "32", backupFilePath, path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        log.error("Failed to reduce audio size: " + path)
        log.error(res.stderr)
    return

def getVocabRows(tree):
    rows = tree.xpath('//div[@class="row vocabulary "]')
    if not len(rows) > 0:
        log.error("No rows found with vocabulary")
    return rows

def getLessonURLs(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)

    lessonURLs = tree.xpath('//a[@data-lesson-id]/@href')
    # Prepend with DW and append 'lv' for vocab page
    lessonURLs = list(map((lambda url: DW_URL + url + '/lv'), lessonURLs))
    return lessonURLs

def storeImage(imgURL):
    if not imgURL:
        return None
    imgFilename = re.sub(r'\s+', '_', os.path.basename(imgURL))
    imgPath = "{}/{}".format(IMAGES_DIR, imgFilename)
    log.info("Downloading image: " + imgURL)
    dlSuccess = downloadFromURL(imgURL, imgPath)
    if dlSuccess:
        reduceImageSize(imgPath)
        img64 = fileToBase64(imgPath)
        log.info("Storing image in Anki: " + imgFilename)
        res = invoke(storeMediaFileJSON(imgFilename, img64))
        if res == None:
            return imgFilename
    return None

def storeAudio(audioURL):
    if not audioURL:
        return None
    audioFilename = re.sub(r'\s+', '_', os.path.basename(audioURL))
    audioPath = "{}/{}".format(AUDIO_DIR, audioFilename)
    log.info("Downloading audio: " + audioURL)
    dlSuccess = downloadFromURL(audioURL, audioPath)
    if dlSuccess:
        reduceAudioSize(audioPath)
        audio64 = fileToBase64(audioPath)
        log.info("Storing audio in Anki: " + audioFilename)
        res = invoke(storeMediaFileJSON(audioFilename, audio64))
        if res == None:
            return audioFilename
    log.warning("No audio available:" + de)
    return None

def buildAnkiFromURL(cards, vocabURL):
    try:
        lessonName = (re.search('en\/([^\/]+)\/', vocabURL)).group(1)
    except AttributeError:
        log.critical("No lesson name in URL: " + vocabURL)
        raise SystemExit(1)
    page = requests.get(vocabURL)
    tree = html.fromstring(page.content)

    vocab_rows = tree.xpath("//div[contains(@class, 'row vocabulary')]")
    tag = lessonName

    for row in vocab_rows:
        de = getGermanFromRow(row)
        en = getEnglishFromRow(row)
        if en == None or de == None:
            log.info('Could not find english and/or german word from row. Possibly the last row is empty div.')
            continue
        log.debug("de = " + de)
        log.debug("en = " + en)

        log.info("Processing card for {} -> {}".format(en,de))
        card = AnkiCard(DECK_NAME)
        card.addTag(tag)

        # Handle image on english side of card
        imgUrl = getImageURLFromRow(row)
        imgFilename = storeImage(imgUrl)
        card.addEnglish(en, imgFilename)

        audioUrl = getAudioURLFromRow(row)
        audioFilename = storeAudio(audioUrl)
        card.addGerman(de, audioFilename)

        if en in cards:
            log.info(en + " is a duplicate. Appending German entry to previous card.")
            (cards[en]).addGerman(card.getGerman())
        else:
            cards[en] = card

def storeCards(cards):
    for card in sorted(cards.values(), key = operator.attrgetter('cardNumber')):
        req = addNoteJSON(card.deck,
                          card.tags,
                          card.getEnglish(),
                          card.getGerman())
        try:
            res = invoke(req)
            if card.hasImage:
                log.info("Added card with image {}: {}".format(res, card.english))
            else:
                log.info("Added card {}: {}".format(res, card.english))
        except Warning as err:
            log.warning(err.args[0] + ": " + card.english)
        except Exception as err:
            log.error(err.args[0] + ": " + card.english)


def main():
    # Initialize directories needed, relative to CWD
    if not os.path.isdir(IMAGES_DIR):
        os.mkdir(IMAGES_DIR);
    if not os.path.isdir(AUDIO_DIR):
        os.mkdir(AUDIO_DIR);

    # Configure logging
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            logging.FileHandler("run.log"),
                            logging.StreamHandler()
                        ])


    log.info("Starting...")

    log.info("Creating deck if it does not exist: " + DECK_NAME)
    invoke(createDeckJSON(DECK_NAME))

    log.info("Using lessons from: " + TOP_URL)
    lessonURLs = getLessonURLs(TOP_URL)

    cards = {} # For duplicates we'll append the german values
    for url in lessonURLs:
        log.info("Building Anki cards from: " + url)
        buildAnkiFromURL(cards, url)
        log.info("Done with lesson: " + url)

    log.info("Creating all cards in Anki now...")
    storeCards(cards)
    log.info("Done!")


if __name__ == '__main__':
    main()

