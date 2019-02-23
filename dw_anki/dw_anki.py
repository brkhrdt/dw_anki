#!/usr/bin/env python3
from lxml import html
import requests
import os
import json
import base64
import re
import logging
import subprocess #to call lame/convert to resize media

# Top page for Nicos Weg A1
TOP_URL= 'https://learngerman.dw.com/en/beginners/c-36519789'
#TOP_URL = 'https://learngerman.dw.com/en/elementary/c-36519797'

DW_URL = 'https://learngerman.dw.com/'
deck = 'DW Nicos Weg A1'
IMAGES_DIR = 'images'
AUDIO_DIR = 'audio'
log = logging.getLogger(__name__)

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

def storeMediaFile(filename, data64):
    request = {
        "action": "storeMediaFile",
        "version": 6,
        "params": {
            "filename": filename,
            "data": data64
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
                    "allowDuplicate": False
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
    worter = reihe.xpath('.//strong[@dir="auto"]/text()')
    notizen = reihe.xpath('.//div[1]/div/p/text()')
    notiz = (''.join(notizen)).replace('\n','')
    #//*[@id="html_body"]/div[2]/div/div/div/div[2]/div[3]/div[1]/div/p/text()
    wort = worter[0]
    if notiz:
        wort = wort + " <br><small><i>" + notiz + "</i></small>"
    return wort


def getEnglishFromRow(row):
    word = row.xpath('.//div[3]/div/p/text()')
    return word[0] #TODO: check that we only got 1?


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
        return
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in r:
                f.write(chunk)


def fileToBase64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()

def reduceImageSize(path):
    backupDir = "{}/{}".format(IMAGES_DIR,"backup")
    if not os.path.isdir(backupDir):
        os.mkdir(backupDir)
    fileName = os.path.basename(path)
    os.system("cp {} {}".format(path, "{}/{}".format(backupDir,fileName)))
    res = subprocess.run(["convert", "-resize", "25%", path, path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        log.error("Failed to reduce image size: " + path)
    return

def reduceAudioSize(path):
    backupDir = "{}/{}".format(AUDIO_DIR,"backup")
    if not os.path.isdir(backupDir):
        os.mkdir(backupDir)
    fileName = os.path.basename(path)
    os.system("cp {} {}".format(path, "{}/{}".format(backupDir,fileName)))
    res = subprocess.run(["lame", "-b", "32", "{}/{}".format(backupDir,fileName), path],
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


def buildAnkiFromURL(vocabURL):
    try:
        lessonName = (re.search('en\/([^\/]+)\/', vocabURL)).group(1)
    except AttributeError:
        log.critical("No lesson name in URL: " + vocabURL)
        raise SystemExit(1)
    page = requests.get(vocabURL)
    tree = html.fromstring(page.content)

    vocab_rows = tree.xpath('//div[@class="row vocabulary "]')
    tags = [lessonName]

    for row in vocab_rows:
        de = getGermanFromRow(row)
        en = getEnglishFromRow(row)
        deHTML = de
        enHTML = en
        imgUrl = getImageURLFromRow(row)
        if imgUrl:
            imgFilename = os.path.basename(imgUrl)
            imgPath = "{}/{}".format(IMAGES_DIR, imgFilename)
            log.info("Downloading image: " + imgUrl)
            downloadFromURL(imgUrl, imgPath)
            reduceImageSize(imgPath)
            img64 = fileToBase64(imgPath)
            enHTML = enHTML + '<br><img src="' + imgFilename+ '" width="50%" height="50%">'
            invoke(storeMediaFile(imgFilename, img64))

        audioUrl = getAudioURLFromRow(row)
        if audioUrl:
            audioFilename = os.path.basename(audioUrl)
            audioPath = "{}/{}".format(AUDIO_DIR, audioFilename)
            log.info("Downloading audio: " + audioUrl)
            downloadFromURL(audioUrl, audioPath)
            reduceAudioSize(audioPath)
            audio64 = fileToBase64(audioPath)
            invoke(storeMediaFile(audioFilename, audio64))
            deHTML = "[sound:{}]".format(audioFilename) + deHTML
        else:
            log.warning("No audio found:" + de)

        req = addNoteJSON(deck, tags, enHTML, deHTML)
        try:
            res = invoke(req)
            if en != enHTML:
                log.info("Added card with image {}: {}".format(res, en))
            else:
                log.info("Added card {}: {}".format(res, en))
        except Warning as err:
            log.warning(err.args[0] + ": " + en)
        except Exception as err:
            log.error(err.args[0] + ": " + en)


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
    log.info("Using lessons from: " + TOP_URL)
    lessonURLs = getLessonURLs(TOP_URL)

    for url in lessonURLs:
        log.info("Building Anki cards from: " + url)
        buildAnkiFromURL(url)
        log.info("Done with lesson: " + url)


if __name__ == '__main__':
    main()

