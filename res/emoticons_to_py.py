#-*- coding: utf-8 -*-
"""
Simple small script for generating a nicely formatted Python module with
embedded Skype emoticon images and docstrings.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author    Erki Suurjaak
@created   26.01.2014
@modified  10.03.2015
"""
import base64
import datetime
import os
import shutil
import sys
import wx.tools.img2py

"""Target Python script to write."""
TARGET = os.path.join("..", "skyperious", "emoticons.py")

Q3 = '"""'

# Skype emoticons
EMOTICONS = {
    "angel": {"title": "Angel", "file": "0131-angel.gif", "strings": ["(angel)"]},
    "angry": {"title": "Angry", "file": "0121-angry.gif", "strings": [":@", ":-@", ":=@", "x(", "x-(", "x=(", "X(", "X-(", "X=("]},
    "bandit": {"title": "Bandit", "file": "0174-bandit.gif", "strings": ["(bandit)"]},
    "beer": {"title": "Beer", "file": "0167-beer.gif", "strings": ["(beer)", "(b)", "(B)"]},
    "blush": {"title": "Blush", "file": "0111-blush.gif", "strings": [":$", "(blush)", ":-$", ":=$"]},
    "bow": {"title": "Bow", "file": "0139-bow.gif", "strings": ["(bow)"]},
    "brokenheart": {"title": "Broken heart", "file": "0153-brokenheart.gif", "strings": ["(u)", "(U)", "(brokenheart)"]},
    "bug": {"title": "Bug", "file": "0180-bug.gif", "strings": ["(bug)"]},
    "cake": {"title": "Cake", "file": "0166-cake.gif", "strings": ["(cake)", "(^)"]},
    "call": {"title": "Call", "file": "0129-call.gif", "strings": ["(call)"]},
    "cash": {"title": "Cash", "file": "0164-cash.gif", "strings": ["(cash)", "(mo)", "($)"]},
    "clap": {"title": "Clapping", "file": "0137-clapping.gif", "strings": ["(clap)"]},
    "coffee": {"title": "Coffee", "file": "0162-coffee.gif", "strings": ["(coffee)"]},
    "cool": {"title": "Cool", "file": "0103-cool.gif", "strings": ["8=)", "8-)", "B=)", "B-)", "(cool)"]},
    "cry": {"title": "Crying", "file": "0106-crying.gif", "strings": [";(", ";-(", ";=("]},
    "dance": {"title": "Dance", "file": "0169-dance.gif", "strings": ["(dance)", "\\o/", "\\:D/", "\\:d/"]},
    "devil": {"title": "Devil", "file": "0130-devil.gif", "strings": ["(devil)"]},
    "doh": {"title": "Doh!", "file": "0120-doh.gif", "strings": ["(doh)"]},
    "drink": {"title": "Drink", "file": "0168-drink.gif", "strings": ["(d)", "(D)"]},
    "drunk": {"title": "Drunk", "file": "0175-drunk.gif", "strings": ["(drunk)"]},
    "dull": {"title": "Dull", "file": "0114-dull.gif", "strings": ["|(", "|-(", "|=(", "|-()"]},
    "eg": {"title": "Evil grin", "file": "0116-evilgrin.gif", "strings": ["]:)", ">:)", "(grin)"]},
    "emo": {"title": "Emo", "file": "0147-emo.gif", "strings": ["(emo)"]},
    "envy": {"title": "Envy", "file": "0132-envy.gif", "strings": ["(envy)"]},
    "finger": {"title": "Finger", "file": "0173-middlefinger.gif", "strings": ["(finger)"]},
    "flower": {"title": "Flower", "file": "0155-flower.gif", "strings": ["(f)", "(F)"]},
    "fubar": {"title": "Fubar", "file": "0181-fubar.gif", "strings": ["(fubar)"]},
    "giggle": {"title": "Giggle", "file": "0136-giggle.gif", "strings": ["(chuckle)", "(giggle)"]},
    "handshake": {"title": "Shaking Hands", "file": "0150-handshake.gif", "strings": ["(handshake)"]},
    "happy": {"title": "Happy", "file": "0142-happy.gif", "strings": ["(happy)"]},
    "headbang": {"title": "Headbang", "file": "0179-headbang.gif", "strings": ["(headbang)", "(banghead)"]},
    "heart": {"title": "Heart", "file": "0152-heart.gif", "strings": ["(h)", "(H)", "(l)", "(L)"]},
    "hi": {"title": "Hi", "file": "0128-hi.gif", "strings": ["(hi)"]},
    "hug": {"title": "Hug", "file": "0134-bear.gif", "strings": ["(hug)", "(bear)"]},
    "inlove": {"title": "In love", "file": "0115-inlove.gif", "strings": ["(inlove)"]},
    "kiss": {"title": "Kiss", "file": "0109-kiss.gif", "strings": [":*", ":=*", ":-*"]},
    "laugh": {"title": "Laugh", "file": "0102-bigsmile.gif", "strings": [":D", ":=D", ":-D", ":d", ":=d", ":-d"]},
    "lipssealed": {"title": "My lips are sealed", "file": "0127-lipssealed.gif", "strings": [":x", ":-x", ":X", ":-X", ":#", ":-#", ":=x", ":=X", ":=#"]},
    "mail": {"title": "Mail", "file": "0154-mail.gif", "strings": ["(e)", "(m)"]},
    "makeup": {"title": "Make-up", "file": "0135-makeup.gif", "strings": ["(makeup)", "(kate)"]},
    "mmm": {"title": "mmmmm..", "file": "0125-mmm.gif", "strings": ["(mm)"]},
    "mooning": {"title": "Mooning", "file": "0172-mooning.gif", "strings": ["(mooning)"]},
    "movie": {"title": "Movie", "file": "0160-movie.gif", "strings": ["(~)", "(film)", "(movie)"]},
    "muscle": {"title": "Muscle", "file": "0165-muscle.gif", "strings": ["(muscle)", "(flex)"]},
    "music": {"title": "Music", "file": "0159-music.gif", "strings": ["(music)"]},
    "nerdy": {"title": "Nerd", "file": "0126-nerd.gif", "strings": ["8-|", "B-|", "8|", "B|", "8=|", "B=|", "(nerd)"]},
    "ninja": {"title": "Ninja", "file": "0170-ninja.gif", "strings": ["(ninja)"]},
    "no": {"title": "No", "file": "0149-no.gif", "strings": ["(n)", "(N)"]},
    "nod": {"title": "Nodding", "file": "0144-nod.gif", "strings": ["(nod)"]},
    "party": {"title": "Party", "file": "0123-party.gif", "strings": ["(party)"]},
    "phone": {"title": "Phone", "file": "0161-phone.gif", "strings": ["(ph)", "(mp)"]},
    "pizza": {"title": "Pizza", "file": "0163-pizza.gif", "strings": ["(pizza)", "(pi)"]},
    "poolparty": {"title": "Poolparty", "file": "0182-poolparty.gif", "strings": ["(poolparty)"]},
    "puke": {"title": "Puking", "file": "0119-puke.gif", "strings": ["(puke)", ":&", ":-&", ":=&"]},
    "punch": {"title": "Punch", "file": "0146-punch.gif", "strings": ["(punch)"]},
    "rain": {"title": "Raining", "file": "0156-rain.gif", "strings": ["(rain)", "(london)", "(st)"]},
    "rock": {"title": "Rock", "file": "0178-rock.gif", "strings": ["(rock)"]},
    "rofl": {"title": "Rolling on the floor laughing", "file": "0140-rofl.gif", "strings": ["(rofl)"]},
    "sad": {"title": "Sad", "file": "0101-sadsmile.gif", "strings": [":(", ":=(", ":-("]},
    "shake": {"title": "Shaking", "file": "0145-shake.gif", "strings": ["(shake)"]},
    "skype": {"title": "Skype", "file": "0151-skype.gif", "strings": ["(skype)", "(ss)"]},
    "sleepy": {"title": "Sleepy", "file": "0113-sleepy.gif", "strings": ["|-)", "I-)", "I=)", "(snooze)"]},
    "smile": {"title": "Smile", "file": "0100-smile.gif", "strings": [":)", ":=)", ":-)"]},
    "smirk": {"title": "Smirking", "file": "0143-smirk.gif", "strings": ["(smirk)"]},
    "smoke": {"title": "Smoking", "file": "0176-smoke.gif", "strings": ["(smoking)", "(smoke)", "(ci)"]},
    "speechless": {"title": "Speechless", "file": "0108-speechless.gif", "strings": [":|", ":=|", ":-|"]},
    "star": {"title": "Star", "file": "0171-star.gif", "strings": ["(*)"]},
    "sun": {"title": "Sun", "file": "0157-sun.gif", "strings": ["(sun)"]},
    "surprised": {"title": "Surprised", "file": "0104-surprised.gif", "strings": [":O", ":=o", ":-o", ":o", ":=O", ":-O"]},
    "swear": {"title": "Swearing", "file": "0183-swear.gif", "strings": ["(swear)"]},
    "sweat": {"title": "Sweating", "file": "0107-sweating.gif", "strings": ["(sweat)", "(:|"]},
    "talk": {"title": "Talking", "file": "0117-talking.gif", "strings": ["(talk)"]},
    "think": {"title": "Thinking", "file": "0138-thinking.gif", "strings": ["(think)", ":?", ":-?", ":=?"]},
    "time": {"title": "Time", "file": "0158-time.gif", "strings": ["(time)"]},
    "tmi": {"title": "Too much information", "file": "0184-tmi.gif", "strings": ["(tmi)"]},
    "toivo": {"title": "Toivo", "file": "0177-toivo.gif", "strings": ["(toivo)"]},
    "tongueout": {"title": "Tongue out", "file": "0110-tongueout.gif", "strings": [":P", ":=P", ":-P", ":p", ":=p", ":-p"]},
    "wait": {"title": "Wait", "file": "0133-wait.gif", "strings": ["(wait)"]},
    "wasntme": {"title": "It wasn't me!", "file": "0122-itwasntme.gif", "strings": ["(wasntme)"]},
    "whew": {"title": "Relieved", "file": "0141-whew.gif", "strings": ["(whew)"]},
    "wink": {"title": "Wink", "file": "0105-wink.gif", "strings": ["(wink)", ";)", ";-)", ";=)"]},
    "wonder": {"title": "Wondering", "file": "0112-wondering.gif", "strings": [":^)"]},
    "worry": {"title": "Worried", "file": "0124-worried.gif", "strings": [":S", ":-S", ":=S", ":s", ":-s", ":=s"]},
    "yawn": {"title": "Yawn", "file": "0118-yawn.gif", "strings": ["(yawn)"]},
    "yes": {"title": "Yes", "file": "0148-yes.gif", "strings": ["(y)", "(Y)", "(ok)"]},
    # The following do not have emoticon images in Skyperious
    "bertlett": {"title": "(bartlett)", "strings": ["(bartlett)"]},
    "facepalm": {"title": "Facepalm", "strings": ["(facepalm)"]},
    "fingerscrossed": {"title": "Fingers crossed", "strings": ["(fingerscrossed)"]},
    "heidy": {"title": "Heidy", "strings": ["(heidy)"]},
    "highfive": {"title": "High five", "strings": ["(highfive)"]},
    "hollest": {"title": "Hollest", "strings": ["(hollest)"]},
    "lalala": {"title": "Lalala", "strings": ["(lalala)"]},
    "oliver": {"title": "(oliver)", "strings": ["(oliver)"]},
    "soccer": {"title": "(soccer)", "strings": ["(soccer)"]},
    "tumbleweed": {"title": "Tumbleweed", "strings": ["(tumbleweed)"]},
    "waiting": {"title": "Waiting", "strings": ["(waiting)"]},
    "wfh": {"title": "Working from home", "strings": ["(wfh)"]},
    "wtf": {"title": "What the...", "strings": ["(wtf)"]},
}


HEADER = """%s
Contains embedded Skype emoticon image resources. Auto-generated.
Skype emoticon images are property of Skype, released under the
Skype Component License 1.0.

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@created     11.06.2013
@modified    %s
------------------------------------------------------------------------------
%s
try:
    import wx
    from wx.lib.embeddedimage import PyEmbeddedImage
except ImportError:
    class PyEmbeddedImage(object):
        \"\"\"Data stand-in for wx.lib.embeddedimage.PyEmbeddedImage.\"\"\"
        def __init__(self, data):
            self.data = data
""" % (Q3, datetime.date.today().strftime("%d.%m.%Y"), Q3)



def create_py(target):
    global HEADER, EMOTICONS
    f = open(target, "w")
    f.write(HEADER)
    for name, data in sorted(EMOTICONS.items()):
        if "file" not in data: continue # continue for name, data in ..            
        f.write("\n\n%sSkype emoticon \"%s %s\".%s\n%s = PyEmbeddedImage(\n" %
                (Q3, data["title"], data["strings"][0], Q3, name))
        filename = os.path.join("emoticons", data["file"])
        raw = base64.b64encode(open(filename, "rb").read())
        while raw:
            f.write("    \"%s\"\n" % raw[:72])
            raw = raw[72:]
        f.write(")\n")
    f.write("\n\n%sEmoticon metadata: name, strings, title.%s\n"
            "EmoticonData = {\n" % (Q3, Q3))
    for name, data in sorted(EMOTICONS.items()):
        data_py = {"title": data["title"], "strings": data["strings"]}
        f.write("    \"%s\": %s,\n" % (name, data_py))
    f.write("}\n")
    f.write("\n\n%sMaps emoticon strings to emoticon names.%s\n" % (Q3, Q3))
    f.write("EmoticonStrings = dict((s, k) for k, d in EmoticonData.items()"
            " for s in d[\"strings\"])\n")
    f.close()


if "__main__" == __name__:
    create_py(TARGET)
