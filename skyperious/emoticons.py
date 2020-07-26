"""
Contains Skype emoticon image loaders. Auto-generated.
Skype emoticon images are property of Skype, released under the
Skype Component License 1.0.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     11.06.2013
@modified    26.07.2020
------------------------------------------------------------------------------
"""
import base64
import io
import logging
import os
import zipfile

try: import wx
except ImportError: wx = None

from . import conf

logger = logging.getLogger(__name__)


class ZipLoader(object):
    _file   = None
    _loaded = False

    @staticmethod
    def read(filename):
        if not ZipLoader._loaded:
            ZipLoader._loaded = True
            try:
                path = os.path.join(conf.ResourceDirectory, "emoticons.zip")
                ZipLoader._file = zipfile.ZipFile(path, "r")
            except Exception:
                logger.exception("Error loading emoticons from %s.", path)
        if not ZipLoader._file: return None
        try: return ZipLoader._file.open(filename).read()
        except Exception:
            logger.exception("Error loading emoticon %s.", filename)


class LazyFileImage(object):
    """Loads image data from file on first access."""
    def __init__(self, filename):
        self._filename = filename
        self._loaded, self._data, self._image = False, '', None

    def GetData(self):
        """Returns Base64-encoded image data string."""
        if self._loaded: return self._data
        self._loaded = True
        raw = ZipLoader.read(self._filename)
        if raw:
            self._data = base64.b64encode(raw)
            if wx: self._image = wx.Image(io.BytesIO(raw))
        return self._data
    Data = property(GetData)
    data = property(GetData)

    def GetImage(self):
        """Returns wx.Image."""
        if not self._loaded: self.GetData()
        return self._image
    Image = property(GetImage)


"""Skype emoticon "Angel (angel)"."""
angel = LazyFileImage("0131-angel.gif")

"""Skype emoticon "Angry :@"."""
angry = LazyFileImage("0121-angry.gif")

"""Skype emoticon "Bandit (bandit)"."""
bandit = LazyFileImage("0174-bandit.gif")

"""Skype emoticon "Beer (beer)"."""
beer = LazyFileImage("0167-beer.gif")

"""Skype emoticon "Blush :$"."""
blush = LazyFileImage("0111-blush.gif")

"""Skype emoticon "Bow (bow)"."""
bow = LazyFileImage("0139-bow.gif")

"""Skype emoticon "Broken heart (u)"."""
brokenheart = LazyFileImage("0153-brokenheart.gif")

"""Skype emoticon "Bug (bug)"."""
bug = LazyFileImage("0180-bug.gif")

"""Skype emoticon "Cake (cake)"."""
cake = LazyFileImage("0166-cake.gif")

"""Skype emoticon "Call (call)"."""
call = LazyFileImage("0129-call.gif")

"""Skype emoticon "Cash (cash)"."""
cash = LazyFileImage("0164-cash.gif")

"""Skype emoticon "Clapping (clap)"."""
clap = LazyFileImage("0137-clapping.gif")

"""Skype emoticon "Coffee (coffee)"."""
coffee = LazyFileImage("0162-coffee.gif")

"""Skype emoticon "Cool 8=)"."""
cool = LazyFileImage("0103-cool.gif")

"""Skype emoticon "Crying ;("."""
cry = LazyFileImage("0106-crying.gif")

"""Skype emoticon "Dance (dance)"."""
dance = LazyFileImage("0169-dance.gif")

"""Skype emoticon "Devil (devil)"."""
devil = LazyFileImage("0130-devil.gif")

"""Skype emoticon "Doh! (doh)"."""
doh = LazyFileImage("0120-doh.gif")

"""Skype emoticon "Drink (d)"."""
drink = LazyFileImage("0168-drink.gif")

"""Skype emoticon "Drunk (drunk)"."""
drunk = LazyFileImage("0175-drunk.gif")

"""Skype emoticon "Dull |("."""
dull = LazyFileImage("0114-dull.gif")

"""Skype emoticon "Evil grin ]:)"."""
eg = LazyFileImage("0116-evilgrin.gif")

"""Skype emoticon "Emo (emo)"."""
emo = LazyFileImage("0147-emo.gif")

"""Skype emoticon "Envy (envy)"."""
envy = LazyFileImage("0132-envy.gif")

"""Skype emoticon "Finger (finger)"."""
finger = LazyFileImage("0173-middlefinger.gif")

"""Skype emoticon "Flower (f)"."""
flower = LazyFileImage("0155-flower.gif")

"""Skype emoticon "Fubar (fubar)"."""
fubar = LazyFileImage("0181-fubar.gif")

"""Skype emoticon "Giggle (chuckle)"."""
giggle = LazyFileImage("0136-giggle.gif")

"""Skype emoticon "Shaking Hands (handshake)"."""
handshake = LazyFileImage("0150-handshake.gif")

"""Skype emoticon "Happy (happy)"."""
happy = LazyFileImage("0142-happy.gif")

"""Skype emoticon "Headbang (headbang)"."""
headbang = LazyFileImage("0179-headbang.gif")

"""Skype emoticon "Heart (h)"."""
heart = LazyFileImage("0152-heart.gif")

"""Skype emoticon "Hi (hi)"."""
hi = LazyFileImage("0128-hi.gif")

"""Skype emoticon "Hug (hug)"."""
hug = LazyFileImage("0134-bear.gif")

"""Skype emoticon "In love (inlove)"."""
inlove = LazyFileImage("0115-inlove.gif")

"""Skype emoticon "Kiss :*"."""
kiss = LazyFileImage("0109-kiss.gif")

"""Skype emoticon "Laugh :D"."""
laugh = LazyFileImage("0102-bigsmile.gif")

"""Skype emoticon "My lips are sealed :x"."""
lipssealed = LazyFileImage("0127-lipssealed.gif")

"""Skype emoticon "Mail (e)"."""
mail = LazyFileImage("0154-mail.gif")

"""Skype emoticon "Make-up (makeup)"."""
makeup = LazyFileImage("0135-makeup.gif")

"""Skype emoticon "mmmmm.. (mm)"."""
mmm = LazyFileImage("0125-mmm.gif")

"""Skype emoticon "Mooning (mooning)"."""
mooning = LazyFileImage("0172-mooning.gif")

"""Skype emoticon "Movie (~)"."""
movie = LazyFileImage("0160-movie.gif")

"""Skype emoticon "Muscle (muscle)"."""
muscle = LazyFileImage("0165-muscle.gif")

"""Skype emoticon "Music (music)"."""
music = LazyFileImage("0159-music.gif")

"""Skype emoticon "Nerd 8-|"."""
nerdy = LazyFileImage("0126-nerd.gif")

"""Skype emoticon "Ninja (ninja)"."""
ninja = LazyFileImage("0170-ninja.gif")

"""Skype emoticon "No (n)"."""
no = LazyFileImage("0149-no.gif")

"""Skype emoticon "Nodding (nod)"."""
nod = LazyFileImage("0144-nod.gif")

"""Skype emoticon "Party (party)"."""
party = LazyFileImage("0123-party.gif")

"""Skype emoticon "Phone (ph)"."""
phone = LazyFileImage("0161-phone.gif")

"""Skype emoticon "Pizza (pizza)"."""
pizza = LazyFileImage("0163-pizza.gif")

"""Skype emoticon "Poolparty (poolparty)"."""
poolparty = LazyFileImage("0182-poolparty.gif")

"""Skype emoticon "Puking (puke)"."""
puke = LazyFileImage("0119-puke.gif")

"""Skype emoticon "Punch (punch)"."""
punch = LazyFileImage("0146-punch.gif")

"""Skype emoticon "Raining (rain)"."""
rain = LazyFileImage("0156-rain.gif")

"""Skype emoticon "Rock (rock)"."""
rock = LazyFileImage("0178-rock.gif")

"""Skype emoticon "Rolling on the floor laughing (rofl)"."""
rofl = LazyFileImage("0140-rofl.gif")

"""Skype emoticon "Sad :("."""
sad = LazyFileImage("0101-sadsmile.gif")

"""Skype emoticon "Shaking (shake)"."""
shake = LazyFileImage("0145-shake.gif")

"""Skype emoticon "Skype (skype)"."""
skype = LazyFileImage("0151-skype.gif")

"""Skype emoticon "Sleepy |-)"."""
sleepy = LazyFileImage("0113-sleepy.gif")

"""Skype emoticon "Smile :)"."""
smile = LazyFileImage("0100-smile.gif")

"""Skype emoticon "Smirking (smirk)"."""
smirk = LazyFileImage("0143-smirk.gif")

"""Skype emoticon "Smoking (smoking)"."""
smoke = LazyFileImage("0176-smoke.gif")

"""Skype emoticon "Speechless :|"."""
speechless = LazyFileImage("0108-speechless.gif")

"""Skype emoticon "Star (*)"."""
star = LazyFileImage("0171-star.gif")

"""Skype emoticon "Sun (sun)"."""
sun = LazyFileImage("0157-sun.gif")

"""Skype emoticon "Surprised :O"."""
surprised = LazyFileImage("0104-surprised.gif")

"""Skype emoticon "Swearing (swear)"."""
swear = LazyFileImage("0183-swear.gif")

"""Skype emoticon "Sweating (sweat)"."""
sweat = LazyFileImage("0107-sweating.gif")

"""Skype emoticon "Talking (talk)"."""
talk = LazyFileImage("0117-talking.gif")

"""Skype emoticon "Thinking (think)"."""
think = LazyFileImage("0138-thinking.gif")

"""Skype emoticon "Time (time)"."""
time = LazyFileImage("0158-time.gif")

"""Skype emoticon "Too much information (tmi)"."""
tmi = LazyFileImage("0184-tmi.gif")

"""Skype emoticon "Toivo (toivo)"."""
toivo = LazyFileImage("0177-toivo.gif")

"""Skype emoticon "Tongue out :P"."""
tongueout = LazyFileImage("0110-tongueout.gif")

"""Skype emoticon "Wait (wait)"."""
wait = LazyFileImage("0133-wait.gif")

"""Skype emoticon "It wasn't me! (wasntme)"."""
wasntme = LazyFileImage("0122-itwasntme.gif")

"""Skype emoticon "Relieved (whew)"."""
whew = LazyFileImage("0141-whew.gif")

"""Skype emoticon "Wink (wink)"."""
wink = LazyFileImage("0105-wink.gif")

"""Skype emoticon "Wondering :^)"."""
wonder = LazyFileImage("0112-wondering.gif")

"""Skype emoticon "Worried :S"."""
worry = LazyFileImage("0124-worried.gif")

"""Skype emoticon "Yawn (yawn)"."""
yawn = LazyFileImage("0118-yawn.gif")

"""Skype emoticon "Yes (y)"."""
yes = LazyFileImage("0148-yes.gif")


"""Emoticon metadata: name, strings, title."""
EmoticonData = {
    "angel": {'strings': ['(angel)'], 'title': 'Angel'},
    "angry": {'strings': [':@', ':-@', ':=@', 'x(', 'x-(', 'x=(', 'X(', 'X-(', 'X=('], 'title': 'Angry'},
    "bandit": {'strings': ['(bandit)'], 'title': 'Bandit'},
    "beer": {'strings': ['(beer)', '(b)', '(B)'], 'title': 'Beer'},
    "bertlett": {'strings': ['(bartlett)'], 'title': '(bartlett)'},
    "blush": {'strings': [':$', '(blush)', ':-$', ':=$'], 'title': 'Blush'},
    "bow": {'strings': ['(bow)'], 'title': 'Bow'},
    "brokenheart": {'strings': ['(u)', '(U)', '(brokenheart)'], 'title': 'Broken heart'},
    "bug": {'strings': ['(bug)'], 'title': 'Bug'},
    "cake": {'strings': ['(cake)', '(^)'], 'title': 'Cake'},
    "call": {'strings': ['(call)'], 'title': 'Call'},
    "cash": {'strings': ['(cash)', '(mo)', '($)'], 'title': 'Cash'},
    "clap": {'strings': ['(clap)'], 'title': 'Clapping'},
    "coffee": {'strings': ['(coffee)'], 'title': 'Coffee'},
    "cool": {'strings': ['8=)', '8-)', 'B=)', 'B-)', '(cool)'], 'title': 'Cool'},
    "cry": {'strings': [';(', ';-(', ';=('], 'title': 'Crying'},
    "dance": {'strings': ['(dance)', '\\o/', '\\:D/', '\\:d/'], 'title': 'Dance'},
    "devil": {'strings': ['(devil)'], 'title': 'Devil'},
    "doh": {'strings': ['(doh)'], 'title': 'Doh!'},
    "drink": {'strings': ['(d)', '(D)'], 'title': 'Drink'},
    "drunk": {'strings': ['(drunk)'], 'title': 'Drunk'},
    "dull": {'strings': ['|(', '|-(', '|=(', '|-()'], 'title': 'Dull'},
    "eg": {'strings': [']:)', '>:)', '(grin)'], 'title': 'Evil grin'},
    "emo": {'strings': ['(emo)'], 'title': 'Emo'},
    "envy": {'strings': ['(envy)'], 'title': 'Envy'},
    "facepalm": {'strings': ['(facepalm)'], 'title': 'Facepalm'},
    "finger": {'strings': ['(finger)'], 'title': 'Finger'},
    "fingerscrossed": {'strings': ['(fingerscrossed)'], 'title': 'Fingers crossed'},
    "flower": {'strings': ['(f)', '(F)'], 'title': 'Flower'},
    "fubar": {'strings': ['(fubar)'], 'title': 'Fubar'},
    "giggle": {'strings': ['(chuckle)', '(giggle)'], 'title': 'Giggle'},
    "handshake": {'strings': ['(handshake)'], 'title': 'Shaking Hands'},
    "happy": {'strings': ['(happy)'], 'title': 'Happy'},
    "headbang": {'strings': ['(headbang)', '(banghead)'], 'title': 'Headbang'},
    "heart": {'strings': ['(h)', '(H)', '(l)', '(L)'], 'title': 'Heart'},
    "heidy": {'strings': ['(heidy)'], 'title': 'Heidy'},
    "hi": {'strings': ['(hi)'], 'title': 'Hi'},
    "highfive": {'strings': ['(highfive)'], 'title': 'High five'},
    "hollest": {'strings': ['(hollest)'], 'title': 'Hollest'},
    "hug": {'strings': ['(hug)', '(bear)'], 'title': 'Hug'},
    "inlove": {'strings': ['(inlove)'], 'title': 'In love'},
    "kiss": {'strings': [':*', ':=*', ':-*'], 'title': 'Kiss'},
    "lalala": {'strings': ['(lalala)'], 'title': 'Lalala'},
    "laugh": {'strings': [':D', ':=D', ':-D', ':d', ':=d', ':-d'], 'title': 'Laugh'},
    "lipssealed": {'strings': [':x', ':-x', ':X', ':-X', ':#', ':-#', ':=x', ':=X', ':=#'], 'title': 'My lips are sealed'},
    "mail": {'strings': ['(e)', '(m)'], 'title': 'Mail'},
    "makeup": {'strings': ['(makeup)', '(kate)'], 'title': 'Make-up'},
    "mmm": {'strings': ['(mm)'], 'title': 'mmmmm..'},
    "mooning": {'strings': ['(mooning)'], 'title': 'Mooning'},
    "movie": {'strings': ['(~)', '(film)', '(movie)'], 'title': 'Movie'},
    "muscle": {'strings': ['(muscle)', '(flex)'], 'title': 'Muscle'},
    "music": {'strings': ['(music)'], 'title': 'Music'},
    "nerdy": {'strings': ['8-|', 'B-|', '8|', 'B|', '8=|', 'B=|', '(nerd)'], 'title': 'Nerd'},
    "ninja": {'strings': ['(ninja)'], 'title': 'Ninja'},
    "no": {'strings': ['(n)', '(N)'], 'title': 'No'},
    "nod": {'strings': ['(nod)'], 'title': 'Nodding'},
    "oliver": {'strings': ['(oliver)'], 'title': '(oliver)'},
    "party": {'strings': ['(party)'], 'title': 'Party'},
    "phone": {'strings': ['(ph)', '(mp)'], 'title': 'Phone'},
    "pizza": {'strings': ['(pizza)', '(pi)'], 'title': 'Pizza'},
    "poolparty": {'strings': ['(poolparty)'], 'title': 'Poolparty'},
    "puke": {'strings': ['(puke)', ':&', ':-&', ':=&'], 'title': 'Puking'},
    "punch": {'strings': ['(punch)'], 'title': 'Punch'},
    "rain": {'strings': ['(rain)', '(london)', '(st)'], 'title': 'Raining'},
    "rock": {'strings': ['(rock)'], 'title': 'Rock'},
    "rofl": {'strings': ['(rofl)'], 'title': 'Rolling on the floor laughing'},
    "sad": {'strings': [':(', ':=(', ':-('], 'title': 'Sad'},
    "shake": {'strings': ['(shake)'], 'title': 'Shaking'},
    "skype": {'strings': ['(skype)', '(ss)'], 'title': 'Skype'},
    "sleepy": {'strings': ['|-)', 'I-)', 'I=)', '(snooze)'], 'title': 'Sleepy'},
    "smile": {'strings': [':)', ':=)', ':-)'], 'title': 'Smile'},
    "smirk": {'strings': ['(smirk)'], 'title': 'Smirking'},
    "smoke": {'strings': ['(smoking)', '(smoke)', '(ci)'], 'title': 'Smoking'},
    "soccer": {'strings': ['(soccer)'], 'title': '(soccer)'},
    "speechless": {'strings': [':|', ':=|', ':-|'], 'title': 'Speechless'},
    "star": {'strings': ['(*)'], 'title': 'Star'},
    "sun": {'strings': ['(sun)'], 'title': 'Sun'},
    "surprised": {'strings': [':O', ':=o', ':-o', ':o', ':=O', ':-O'], 'title': 'Surprised'},
    "swear": {'strings': ['(swear)'], 'title': 'Swearing'},
    "sweat": {'strings': ['(sweat)', '(:|'], 'title': 'Sweating'},
    "talk": {'strings': ['(talk)'], 'title': 'Talking'},
    "think": {'strings': ['(think)', ':?', ':-?', ':=?'], 'title': 'Thinking'},
    "time": {'strings': ['(time)'], 'title': 'Time'},
    "tmi": {'strings': ['(tmi)'], 'title': 'Too much information'},
    "toivo": {'strings': ['(toivo)'], 'title': 'Toivo'},
    "tongueout": {'strings': [':P', ':=P', ':-P', ':p', ':=p', ':-p'], 'title': 'Tongue out'},
    "tumbleweed": {'strings': ['(tumbleweed)'], 'title': 'Tumbleweed'},
    "wait": {'strings': ['(wait)'], 'title': 'Wait'},
    "waiting": {'strings': ['(waiting)'], 'title': 'Waiting'},
    "wasntme": {'strings': ['(wasntme)'], 'title': "It wasn't me!"},
    "wfh": {'strings': ['(wfh)'], 'title': 'Working from home'},
    "whew": {'strings': ['(whew)'], 'title': 'Relieved'},
    "wink": {'strings': ['(wink)', ';)', ';-)', ';=)'], 'title': 'Wink'},
    "wonder": {'strings': [':^)'], 'title': 'Wondering'},
    "worry": {'strings': [':S', ':-S', ':=S', ':s', ':-s', ':=s'], 'title': 'Worried'},
    "wtf": {'strings': ['(wtf)'], 'title': 'What the...'},
    "yawn": {'strings': ['(yawn)'], 'title': 'Yawn'},
    "yes": {'strings': ['(y)', '(Y)', '(ok)'], 'title': 'Yes'},
}


"""Maps emoticon strings to emoticon names."""
EmoticonStrings = dict((s, k) for k, d in EmoticonData.items() for s in d["strings"])
