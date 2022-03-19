#-*- coding: utf-8 -*-
"""
Simple small script for generating a nicely formatted Python module with
accessible Skype emoticon images and docstrings.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author    Erki Suurjaak
@created   26.01.2014
@modified  22.03.2022
"""
import datetime
import io
import json
import os
import zipfile


"""Target Python script to write."""
PYTARGET = os.path.join("..", "skyperious", "emoticons.py")

"""Target ZIP file to write."""
ZIPTARGET = os.path.join("..", "skyperious", "res", "emoticons.zip")

Q3 = '"""'

# Skype emoticons
EMOTICONS = {
    # Original emoticons
    "angel":                  {"title": "Angel", "file": "0131-angel.gif", "strings": ["(a)", "(angel)", "(A)", "(Angel)"]},
    "angry":                  {"title": "Angry", "file": "0121-angry.gif", "strings": [":@", "(angry)", ":-@", ":=@", "x(", "x-(", "X(", "X-(", "x=(", "X=(", ";@", ";-@", "(Angry)"]},
    "bandit":                 {"title": "Bandit", "file": "0174-bandit.gif", "strings": ["(bandit)", "(Bandit)"]},
    "beer":                   {"title": "Beer", "file": "0167-beer.gif", "strings": ["(beer)", "(bricklayers)", "(B)", "(b)", "(Beer)", "(Bricklayers)"]},
    "blush":                  {"title": "Blushing", "file": "0111-blush.gif", "strings": [":$", ":-$", ":=$", ":\">", "(blush)", "(Blush)"]},
    "bow":                    {"title": "Bowing", "file": "0139-bow.gif", "strings": ["(bow)", "(Bow)"]},
    "brokenheart":            {"title": "Broken heart", "file": "0153-brokenheart.gif", "strings": ["(u)", "(U)", "(brokenheart)", "(Brokenheart)"]},
    "bug":                    {"title": "Bug", "file": "0180-bug.gif", "strings": ["(bug)", "(Bug)"]},
    "cake":                   {"title": "Cake", "file": "0166-cake.gif", "strings": ["(^)", "(cake)", "(Cake)"]},
    "call":                   {"title": "Call", "file": "0129-call.gif", "strings": ["(call)", "(T)", "(t)", "(Call)"]},
    "cash":                   {"title": "Cash", "file": "0164-cash.gif", "strings": ["($)", "(mo)", "(cash)", "(Cash)", "(Mo)"]},
    "clap":                   {"title": "Clapping", "file": "0137-clapping.gif", "strings": ["(clap)", "(Clap)"]},
    "coffee":                 {"title": "Coffee", "file": "0162-coffee.gif", "strings": ["(coffee)", "(c)", "(C)", "(Coffee)"]},
    "cool":                   {"title": "Cool", "file": "0103-cool.gif", "strings": ["8-)", "8=)", "B-)", "B=)", "(cool)", "(Cool)"]},
    "cry":                    {"title": "Crying", "file": "0106-crying.gif", "strings": [";(", ";-(", ";=(", "(cry)", ":'(", "(Cry)"]},
    "dance":                  {"title": "Dancing", "file": "0169-dance.gif", "strings": ["\\o/", "\\:D/", "\\:d/", "(dance)", "(Dance)"]},
    "devil":                  {"title": "Devil", "file": "0130-devil.gif", "strings": ["(devil)", "(6)", "(Devil)"]},
    "doh":                    {"title": "Doh!", "file": "0120-doh.gif", "strings": ["(doh)", "(Doh)"]},
    "drink":                  {"title": "Drink", "file": "0168-drink.gif", "strings": ["(d)", "(D)", "(drink)", "(Drink)"]},
    "drunk":                  {"title": "Drunk", "file": "0175-drunk.gif", "strings": ["(drunk)", "(Drunk)"]},
    "dull":                   {"title": "Dull", "file": "0114-dull.gif", "strings": ["|(", "|-(", "|=(", "(dull)", "(Dull)", "|-()"]},
    "eg":                     {"title": "Evil grin", "file": "0116-evilgrin.gif", "strings": ["]:)", ">:)", "(grin)", "(Grin)", "(evilgrin)", "(Evilgrin)", "(evil)", "(Evil)", "(eg)", "(Eg)"]},
    "emo":                    {"title": "Emo", "file": "0147-emo.gif", "strings": ["(emo)", "(Emo)"]},
    "envy":                   {"title": "Envy", "file": "0132-envy.gif", "strings": ["(envy)", "(V)", "(v)", "(Envy)"]},
    "finger":                 {"title": "Finger", "file": "0173-middlefinger.gif", "strings": ["(finger)", "(Finger)"]},
    "flower":                 {"title": "Flower", "file": "0155-flower.gif", "strings": ["(f)", "(flower)", "(F)", "(Flower)"]},
    "fubar":                  {"title": "FUBAR", "file": "0181-fubar.gif", "strings": ["(fubar)"]},
    "giggle":                 {"title": "Giggle", "file": "0136-giggle.gif", "strings": ["(giggle)", "(chuckle)", "(Chuckle)", "(Giggle)"]},
    "handshake":              {"title": "Handshake", "file": "0150-handshake.gif", "strings": ["(handshake)", "(Handshake)"]},
    "happy":                  {"title": "Happy", "file": "0142-happy.gif", "strings": ["(happy)", "(Happy)"]},
    "headbang":               {"title": "Banging head on wall", "file": "0179-headbang.gif", "strings": ["(headbang)", "(banghead)", "(Headbang)", "(Banghead)"]},
    "heart":                  {"title": "Heart", "file": "0152-heart.gif", "strings": ["<3", "(heart)", "(h)", "(H)", "(l)", "(L)", "(Heart)"]},
    "hi":                     {"title": "Hi", "file": "0128-hi.gif", "strings": ["(hi)", "(wave)", "(bye)", "(BYE)", "(Bye)", "(Hi)", "(HI)", "(Wave)"]},
    "hug":                    {"title": "Hug", "file": "0134-bear.gif", "strings": ["(hug)", "(bear)", "(Hug)", "(Bear)"]},
    "inlove":                 {"title": "In love", "file": "0115-inlove.gif", "strings": [":]", "(inlove)", "(love)", ":-]", "(Inlove)", "(Love)"]},
    "kiss":                   {"title": "Kiss", "file": "0109-kiss.gif", "strings": [":*", "(kiss)", ":-*", ":=*", "(xo)", "(K)", "(k)", "(Kiss)"]},
    "laugh":                  {"title": "Laugh", "file": "0102-bigsmile.gif", "strings": [":D", ":-D", ":=D", ":d", ":-d", ":=d", "(laugh)", ":>", ":->", "(lol)", "(LOL)", "(Laugh)", "(Lol)"]},
    "lipssealed":             {"title": "My lips are sealed", "file": "0127-lipssealed.gif", "strings": [":x", ":-x", ":X", ":-X", ":#", ":-#", ":=x", ":=X", ":=#", "(lipssealed)", "(Lipssealed)"]},
    "mail":                   {"title": "You have mail", "file": "0154-mail.gif", "strings": ["(e)", "(m)", "(mail)", "(E)", "(M)", "(Mail)"]},
    "makeup":                 {"title": "Make-up", "file": "0135-makeup.gif", "strings": ["(makeup)", "(kate)", "(Makeup)", "(Kate)"]},
    "mmm":                    {"title": "Mmmmm...", "file": "0125-mmm.gif", "strings": ["(mm)", "(mmm)", "(mmmm)", "(Mm)", "(Mmm)", "(Mmmm)"]},
    "mooning":                {"title": "Mooning", "file": "0172-mooning.gif", "strings": ["(mooning)", "(Mooning)"]},
    "movie":                  {"title": "Movie", "file": "0160-movie.gif", "strings": ["(~)", "(film)", "(movie)", "(Film)", "(Movie)"]},
    "muscle":                 {"title": "Muscle", "file": "0165-muscle.gif", "strings": ["(flex)", "(muscle)", "(Flex)", "(Muscle)"]},
    "music":                  {"title": "Music", "file": "0159-music.gif", "strings": ["(music)", "(8)", "(Music)"]},
    "nerdy":                  {"title": "Nerdy", "file": "0126-nerd.gif", "strings": ["8|", "B|", "B-|", "8-|", "B=|", "8=|", "(nerd)", "(Nerd)", "(nerdy)", "(Nerdy)"]},
    "ninja":                  {"title": "Ninja", "file": "0170-ninja.gif", "strings": ["(ninja)", "(J)", "(j)", "(Ninja)"]},
    "no":                     {"title": "No", "file": "0149-no.gif", "strings": ["(n)", "(N)", "(no)", "(No)"]},
    "nod":                    {"title": "Nodding", "file": "0144-nod.gif", "strings": ["(nod)", "(Nod)"]},
    "party":                  {"title": "Party", "file": "0123-party.gif", "strings": ["<o)", "(party)", "<O)", "<:o)", "(Party)"]},
    "phone":                  {"title": "Phone", "file": "0161-phone.gif", "strings": ["(mp)", "(ph)", "(phone)", "(Mp)", "(Ph)", "(Phone)"]},
    "pizza":                  {"title": "Pizza", "file": "0163-pizza.gif", "strings": ["(pi)", "(pizza)", "(Pi)", "(Pizza)"]},
    "poolparty":              {"title": "Pool party", "file": "0182-poolparty.gif", "strings": ["(hrv)", "(poolparty)", "(Poolparty)", "(Hrv)"]},
    "puke":                   {"title": "Puke", "file": "0119-puke.gif", "strings": [":&", "(puke)", ":-&", ":=&", "+o(", "(Puke)"]},
    "punch":                  {"title": "Punch", "file": "0146-punch.gif", "strings": ["*|", "(punch)", "*-|", "(Punch)"]},
    "rain":                   {"title": "Rain", "file": "0156-rain.gif", "strings": ["(rain)", "(st)", "(ST)", "(St)", "(london)", "(Rain)", "(London)"]},
    "rock":                   {"title": "Rock", "file": "0178-rock.gif", "strings": ["(rock)", "(Rock)"]},
    "rofl":                   {"title": "Rolling on the floor laughing", "file": "0140-rofl.gif", "strings": ["(rofl)", "(rotfl)", "(Rofl)", "(Rotfl)"]},
    "sad":                    {"title": "Sad", "file": "0101-sadsmile.gif", "strings": [":(", ":-(", ":=(", "(sad)", ":<", ":-<", "(Sad)"]},
    "shake":                  {"title": "Shake", "file": "0145-shake.gif", "strings": ["(shake)", "(Shake)"]},
    "skype":                  {"title": "Skype", "file": "0151-skype.gif", "strings": ["(ss)", "(skype)", "(Skype)", "(Ss)"]},
    "sleepy":                 {"title": "Snooze", "file": "0113-sleepy.gif", "strings": ["I-)", "I=)", "|-)", "(snooze)", "(Snooze)", "(sleepy)", "(Sleepy)"]},
    "smile":                  {"title": "Smile", "file": "0100-smile.gif", "strings": [":)", ":-)", ":=)", "(smile)", "(Smile)"]},
    "smirk":                  {"title": "Smirking", "file": "0143-smirk.gif", "strings": ["(smirk)", "(Smirk)"]},
    "smoke":                  {"title": "Smoking", "file": "0176-smoke.gif", "strings": ["(ci)", "(smoke)", "(smoking)", "(Smoking)", "(Smoke)", "(Ci)"]},
    "speechless":             {"title": "Speechless", "file": "0108-speechless.gif", "strings": [":|", ":-|", ":=|", "(speechless)", "(Speechless)"]},
    "star":                   {"title": "Star", "file": "0171-star.gif", "strings": ["(*)", "(star)", "(Star)"]},
    "sun":                    {"title": "Sun", "file": "0157-sun.gif", "strings": ["(sun)", "(#)", "(Sun)"]},
    "surprised":              {"title": "Surprised", "file": "0104-surprised.gif", "strings": [":O", ":-O", ":=O", ":o", ":-o", ":=o", "(surprised)", "(Surprised)"]},
    "swear":                  {"title": "Swearing", "file": "0183-swear.gif", "strings": ["(swear)", "(Swear)"]},
    "sweat":                  {"title": "Sweating", "file": "0107-sweating.gif", "strings": ["(:|", "(sweat)", "(Sweat)"]},
    "talk":                   {"title": "Talking", "file": "0117-talking.gif", "strings": ["(talk)", "(Talk)"]},
    "think":                  {"title": "Thinking", "file": "0138-thinking.gif", "strings": [":?", "(think)", ":-?", ":=?", "*-)", "(Think)"]},
    "time":                   {"title": "Time", "file": "0158-time.gif", "strings": ["(o)", "(O)", "(time)", "(clock)", "(0)", "(Time)", "(Clock)"]},
    "tmi":                    {"title": "Too much information", "file": "0184-tmi.gif", "strings": ["(tmi)", "(Tmi)"]},
    "toivo":                  {"title": "Toivo", "file": "0177-toivo.gif", "strings": ["(toivo)", "(Toivo)"]},
    "tongueout":              {"title": "Tongue sticking out", "file": "0110-tongueout.gif", "strings": [":P", ":-P", ":=P", ":p", ":-p", ":=p", "(tongueout)", "(Tongueout)"]},
    "wait":                   {"title": "Wait", "file": "0133-wait.gif", "strings": ["(wait)", "(Wait)"]},
    "wasntme":                {"title": "It wasn't me!", "file": "0122-itwasntme.gif", "strings": ["(wm)", "(wasntme)", "(Wasntme)", "(Wm)"]},
    "whew":                   {"title": "Relieved", "file": "0141-whew.gif", "strings": ["(whew)", "(phew)", "(Whew)", "(Phew)"]},
    "wink":                   {"title": "Wink", "file": "0105-wink.gif", "strings": [";)", ";-)", ";=)", "(wink)", "(Wink)"]},
    "wonder":                 {"title": "Wondering", "file": "0112-wondering.gif", "strings": [":^)", "(wonder)", "(Wonder)"]},
    "worry":                  {"title": "Worried", "file": "0124-worried.gif", "strings": [":s", "(worry)", ":S", ":-s", ":-S", ":=s", ":=S", "(Worry)", "(worried)", "(Worried)"]},
    "yawn":                   {"title": "Yawn", "file": "0118-yawn.gif", "strings": ["(yawn)", "(Yawn)"]},
    "yes":                    {"title": "Yes", "file": "0148-yes.gif", "strings": ["(y)", "(Y)", "(yes)", "(Yes)", "(ok)"]},

    # Later emoticons
    "abe":                    {"title": "Hey, you!", "file": "abe.gif", "strings": ["(abe)", "(Abe)", "(abey)", "(Abey)"]},
    "acorn":                  {"title": "Acorn", "file": "acorn.gif", "strings": ["(acorn)", "(Acorn)"]},
    "ambulance":              {"title": "Ambulance", "file": "ambulance.gif", "strings": ["(ambulance)", "(Ambulance)"]},
    "americanfootball":       {"title": "American Football", "file": "americanfootball.gif", "strings": ["(americanfootball)", "(Americanfootball)", "(americanfootballbounce)", "(americanfootballeyes)"]},
    "anger":                  {"title": "Anger", "file": "anger.gif", "strings": ["(anger)", "(Anger)"]},
    "angryface":              {"title": "Angry Face", "file": "angryface.gif", "strings": ["(angryface)"]},
    "apple":                  {"title": "Apple", "file": "apple.gif", "strings": ["(apple)", "(Apple)"]},
    "aubergine":              {"title": "Eggplant", "file": "aubergine.gif", "strings": ["(aubergine)", "(Aubergine)", "(eggplant)", "(Eggplant)"]},
    "auld":                   {"title": "Auld", "file": "auld.gif", "strings": ["(auld)", "(Auld)"]},
    "avocadolove":            {"title": "Avocado Love", "file": "avocadolove.gif", "strings": ["(avocadolove)", "(Avocadolove)"]},
    "banana":                 {"title": "Banana", "file": "banana.gif", "strings": ["(banana)", "(Banana)"]},
    "bartlett":               {"title": "Soccer", "file": "bartlett.gif", "strings": ["(football)", "(Football)", "(bartlett)", "(Bartlett)", "(so)", "(So)", "(soccer)", "(Soccer)"]},
    "baseball":               {"title": "Baseball", "file": "baseball.gif", "strings": ["(baseball)"]},
    "basketball":             {"title": "Basketball", "file": "basketball.gif", "strings": ["(basketball)"]},
    "bee":                    {"title": "Bee", "file": "bee.gif", "strings": ["(bee)", "(Bee)"]},
    "bell":                   {"title": "Bell", "file": "bell.gif", "strings": ["(bell)", "(Bell)", "(ghanta)", "(Ghanta)"]},
    "bhangra":                {"title": "Bhangra", "file": "bhangra.gif", "strings": ["(bhangra)", "(Bhangra)"]},
    "bike":                   {"title": "Bicycle", "file": "bike.gif", "strings": ["(bike)", "(bicycle)", "(sander)", "(Bike)", "(Bicycle)", "(Sander)"]},
    "blankface":              {"title": "Face without mouth", "file": "blankface.gif", "strings": ["(blankface)"]},
    "bollylove":              {"title": "In love pose", "file": "bollylove.gif", "strings": ["(bollylove)", "(Bollylove)"]},
    "bomb":                   {"title": "Bomb", "file": "bomb.gif", "strings": ["(bomb)", "(explosion)", "(explode)", "@=", "(Bomb)", "(Explosion)", "(Explode)"]},
    "bottlefeeding":          {"title": "Bottle feeding", "file": "bottlefeeding.gif", "strings": ["(bottlefeeding)", "(Bottlefeeding)"]},
    "bowled":                 {"title": "Bowled", "file": "bowled.gif", "strings": ["(bowled)", "(Bowled)", "(out)", "(Out)", "(wicket)", "(Wicket)"]},
    "bowlingball":            {"title": "Bowling ball", "file": "bowlingball.gif", "strings": ["(bowlingball)"]},
    "brb":                    {"title": "Be Right Back", "file": "brb.gif", "strings": ["(brb)", "(berightback)", "(Brb)", "(Berightback)"]},
    "breakfastinbed":         {"title": "Breakfast in bed", "file": "breakfastinbed.gif", "strings": ["(breakfastinbed)", "(Breakfastinbed)"]},
    "breastfeeding":          {"title": "Breastfeeding", "file": "breastfeeding.gif", "strings": ["(breastfeeding)", "(Breastfeeding)"]},
    "brokenheartblack":       {"title": "Black broken heart", "file": "brokenheartblack.gif", "strings": ["(brokenheartblack)", "(blackbrokenheart)"]},
    "brokenheartblue":        {"title": "Blue broken heart", "file": "brokenheartblue.gif", "strings": ["(brokenheartblue)", "(bluebrokenheart)"]},
    "brokenheartgreen":       {"title": "Green broken heart", "file": "brokenheartgreen.gif", "strings": ["(brokenheartgreen)", "(greenbrokenheart)"]},
    "brokenheartpurple":      {"title": "Purple broken heart", "file": "brokenheartpurple.gif", "strings": ["(brokenheartpurple)", "(purplebrokenheart)"]},
    "brokenheartyellow":      {"title": "Yellow broken heart", "file": "brokenheartyellow.gif", "strings": ["(brokenheartyellow)", "(yellowbrokenheart)"]},
    "bronzemedal":            {"title": "Bronze medal", "file": "bronzemedal.gif", "strings": ["(bronzemedal)", "(Bronzemedal)"]},
    "bunny":                  {"title": "Bunny", "file": "bunny.gif", "strings": ["(bunny)", "(Bunny)", "(lovebunny)", "(Lovebunny)", "(rabbit)", "(Rabbit)"]},
    "bunnyhug":               {"title": "Bunny hug", "file": "bunnyhug.gif", "strings": ["(bunnyhug)", "(Bunnyhug)"]},
    "burger":                 {"title": "Burger", "file": "burger.gif", "strings": ["(burger)", "(Burger)"]},
    "busyday":                {"title": "Busy Day", "file": "busyday.gif", "strings": ["(busyday)", "(Busyday)"]},
    "butterfly":              {"title": "Butterfly", "file": "butterfly.gif", "strings": ["(butterfly)"]},
    "cactuslove":             {"title": "Cactus Love", "file": "cactuslove.gif", "strings": ["(cactuslove)", "(Cactuslove)"]},
    "cakeslice":              {"title": "Cake slice", "file": "cakeslice.gif", "strings": ["(cakeslice)", "(Cakeslice)"]},
    "cakethrow":              {"title": "Cake Throw", "file": "cakethrow.gif", "strings": ["(cakethrow)", "(Cakethrow)"]},
    "camera":                 {"title": "Camera", "file": "camera.gif", "strings": ["(p)", "(camera)", "(P)", "(Camera)"]},
    "canoe":                  {"title": "Canoe", "file": "canoe.gif", "strings": ["(canoe)", "(1f6f6_canoe)"]},
    "canyoutalk":             {"title": "Can you talk?", "file": "canyoutalk.gif", "strings": ["(!!)", "(canyoutalk)", "(Canyoutalk)"]},
    "car":                    {"title": "Car", "file": "car.gif", "strings": ["(car)", "(au)", "(Car)", "(Au)"]},
    "cat":                    {"title": "Cat", "file": "cat.gif", "strings": [":3", "(cat)", "(@)", "(meow)", "(Cat)", "(Meow)", "(kitty)", "(Kitty)"]},
    "chai":                   {"title": "Tea", "file": "chai.gif", "strings": ["(chai)", "(Chai)", "(tea)", "(Tea)"]},
    "champagne":              {"title": "Champagne", "file": "champagne.gif", "strings": ["(champagne)", "(Champagne)", "(sparkling)", "(Sparkling)"]},
    "chappal":                {"title": "Slipper", "file": "chappal.gif", "strings": ["(chappal)", "(Chappal)", "(slipper)", "(Slipper)"]},
    "cheerleader":            {"title": "Cheerleader", "file": "cheerleader.gif", "strings": ["(cheerleader)", "(Cheerleader)"]},
    "cheers":                 {"title": "Cheers!", "file": "cheers.gif", "strings": ["(cheers)", "(Cheers)"]},
    "cheese":                 {"title": "Cheese", "file": "cheese.gif", "strings": ["(cheese)", "(Cheese)", "(stink)", "(Stink)"]},
    "cherries":               {"title": "Cherries", "file": "cherries.gif", "strings": ["(cherries)", "(Cherries)"]},
    "cherryblossom":          {"title": "Cherry blossom", "file": "cherryblossom.gif", "strings": ["(cherryblossom)", "(Cherryblossom)"]},
    "chickenleg":             {"title": "Chicken leg", "file": "chickenleg.gif", "strings": ["(chickenleg)", "(Chickenleg)"]},
    "chicksegg":              {"title": "Chicks' Egg", "file": "chicksegg.gif", "strings": ["(chicksegg)", "(Chicksegg)"]},
    "computer":               {"title": "Computer", "file": "computer.gif", "strings": ["(pc)", "(computer)", "(co)", "(Computer)", "(Co)", "(Pc)"]},
    "computerrage":           {"title": "Computer rage", "file": "computerrage.gif", "strings": ["(computerrage)", "(Computerrage)", "(typingrage)", "(Typingrage)"]},
    "confidential":           {"title": "Confidential", "file": "confidential.gif", "strings": ["(qt)", "(confidential)", "(QT)", "(Qt)", "(Confidential)"]},
    "confused":               {"title": "Confused", "file": "confused.gif", "strings": ["(confused)", "(Confused)", ":-/", ":-\\", ":/", ":\\"]},
    "cookies":                {"title": "Cookies", "file": "cookies.gif", "strings": ["(cookies)", "(Cookies)"]},
    "coolcat":                {"title": "Cool cat", "file": "coolcat.gif", "strings": ["(coolcat)"]},
    "cooldog":                {"title": "Cool dog", "file": "cooldog.gif", "strings": ["(cooldog)"]},
    "coolkoala":              {"title": "Cool koala", "file": "coolkoala.gif", "strings": ["(coolkoala)"]},
    "coolmonkey":             {"title": "Cool monkey", "file": "coolmonkey.gif", "strings": ["(coolmonkey)"]},
    "coolrobot":              {"title": "Cool robot", "file": "coolrobot.gif", "strings": ["(coolrobot)"]},
    "crab":                   {"title": "Crab", "file": "crab.gif", "strings": ["(crab)", "(1f980_crab)"]},
    "cricket":                {"title": "Cricket", "file": "cricket.gif", "strings": ["(cricket)", "(Cricket)"]},
    "croissant":              {"title": "Croissant", "file": "croissant.gif", "strings": ["(croissant)"]},
    "cupcake":                {"title": "Cupcake", "file": "cupcake.gif", "strings": ["(cupcake)", "(Cupcake)"]},
    "cwl":                    {"title": "Crying with laughter", "file": "cwl.gif", "strings": ["(cwl)", "(Cwl)", "(cryingwithlaughter)", "(Cryingwithlaughter)"]},
    "dadtime":                {"title": "Dad Time", "file": "dadtime.gif", "strings": ["(dadtime)", "(Dadtime)"]},
    "deadyes":                {"title": "Dead Yes", "file": "deadyes.gif", "strings": ["(deadyes)", "(Deadyes)"]},
    "deciduoustree":          {"title": "Deciduous Tree", "file": "deciduoustree.gif", "strings": ["(deciduoustree)", "(treedeciduous)"]},
    "dedmoroz":               {"title": "Frost wizard", "file": "dedmoroz.gif", "strings": ["(dedmoroz)", "(Dedmoroz)", "(frostwizard)", "(Frostwizard)"]},
    "desert":                 {"title": "Desert", "file": "desert.gif", "strings": ["(desert)", "(Desert)"]},
    "dhakkan":                {"title": "Fool", "file": "dhakkan.gif", "strings": ["(dhakkan)", "(Dhakkan)", "(fool)", "(Fool)"]},
    "diamond":                {"title": "Diamond", "file": "diamond.gif", "strings": ["(diamond)"]},
    "disappointed":           {"title": "Disappointed", "file": "disappointed.gif", "strings": ["(disappointed)", "(Disappointed)"]},
    "discodancer":            {"title": "Disco dancer", "file": "discodancer.gif", "strings": ["(disco)", "(Disco)", "(discodancer)", "(Discodancer)"]},
    "disgust":                {"title": "Disgust", "file": "disgust.gif", "strings": ["(disgust)", "(Disgust)"]},
    "diwaliselfie":           {"title": "Diwali Selfie", "file": "diwaliselfie.gif", "strings": ["(diwaliselfie)", "(Diwaliselfie)"]},
    "diya":                   {"title": "Tealight", "file": "diya.gif", "strings": ["(diwali)", "(Diwali)", "(diya)", "(Diya)"]},
    "dog":                    {"title": "Dog", "file": "dog.gif", "strings": ["(&)", "(dog)", ":o3", "(Dog)"]},
    "dolphin":                {"title": "Dolphin", "file": "dolphin.gif", "strings": ["(dolphin)", "(Dolphin)"]},
    "donkey":                 {"title": "Donkey", "file": "donkey.gif", "strings": ["(donkey)", "(Donkey)", "(gadha)", "(Gadha)"]},
    "donttalktome":           {"title": "Don't talk to me", "file": "donttalktome.gif", "strings": ["(donttalk)", "(Donttalk)", "(donttalktome)", "(Donttalktote)", "(Donttalktome)"]},
    "dracula":                {"title": "Hammer Dracula", "file": "dracula.gif", "strings": ["(dracula)", "(Dracula)"]},
    "dream":                  {"title": "Dreaming", "file": "dream.gif", "strings": ["(dream)", "(Dream)"]},
    "dreidel":                {"title": "Dreidel", "file": "dreidel.gif", "strings": ["(dreidel)", "(Dreidel)"]},
    "dropthemic":             {"title": "Drop the mic", "file": "dropthemic.gif", "strings": ["(dropthemic)", "(Dropthemic)"]},
    "eid":                    {"title": "Eid", "file": "eid.gif", "strings": ["(eid)", "(Eid)"]},
    "eightball":              {"title": "Pool eight ball", "file": "eightball.gif", "strings": ["(eightball)"]},
    "elephant":               {"title": "Elephant", "file": "elephant.gif", "strings": ["(elephant)", "(Elephant)"]},
    "evergreentree":          {"title": "Evergreen Tree", "file": "evergreentree.gif", "strings": ["(evergreentree)", "(treeevergreen)"]},
    "expressionless":         {"title": "Expressionless", "file": "expressionless.gif", "strings": ["(expressionless)", "(Expressionless)"]},
    "facepalm":               {"title": "Facepalm", "file": "facepalm.gif", "strings": ["(fail)", "(facepalm)", "(Facepalm)", "(Fail)"]},
    "fallingleaf":            {"title": "Falling leaf", "file": "fallingleaf.gif", "strings": ["(fallingleaf)", "(Fallingleaf)"]},
    "fallinlove":             {"title": "Falling in love", "file": "fallinlove.gif", "strings": ["(fallinlove)", "(Fallinlove)", "(fallinlove)", "(Fallinlove)"]},
    "family":                 {"title": "Family", "file": "family.gif", "strings": ["(family)", "(Family)"]},
    "familytime":             {"title": "Family Time", "file": "familytime.gif", "strings": ["(familytime)", "(Familytime)"]},
    "fearful":                {"title": "Fearful", "file": "fearful.gif", "strings": ["(fearful)"]},
    "festiveparty":           {"title": "Festive party", "file": "festiveparty.gif", "strings": ["(festiveparty)", "(Festiveparty)", "(partyxmas)", "(Partyxmas)"]},
    "fingerscrossed":         {"title": "Fingers crossed", "file": "fingerscrossed.gif", "strings": ["(yn)", "(fingers)", "(crossedfingers)", "(fingerscrossed)", "(Yn)", "(Fingers)", "(Fingerscrossed)", "(Crossedfingers)"]},
    "fire":                   {"title": "Fire", "file": "fire.gif", "strings": ["(fire)", "(Fire)"]},
    "fireworks":              {"title": "Fireworks", "file": "fireworks.gif", "strings": ["(fireworks)", "(Fireworks)"]},
    "fish":                   {"title": "Fish", "file": "fish.gif", "strings": ["(fish)", "(Fish)", "(tropicalfish)", "(fishtropical)"]},
    "fistbump":               {"title": "Good work!", "file": "fistbump.gif", "strings": ["(fistbump)", u"=\u018eE=", "p#d", "(Fistbump)"]},
    "flaginhole":             {"title": "Flag in hole", "file": "flaginhole.gif", "strings": ["(flaginhole)", "(golfball)"]},
    "flushed":                {"title": "Flushed", "file": "flushed.gif", "strings": ["(flushed)", "(Flushed)"]},
    "footballfail":           {"title": "Football fail", "file": "footballfail.gif", "strings": ["(footballfail)", "(Footballfail)"]},
    "foreverlove":            {"title": "Forever love", "file": "foreverlove.gif", "strings": ["(foreverlove)", "(Foreverlove)"]},
    "foxhug":                 {"title": "Fox hug", "file": "foxhug.gif", "strings": ["(foxhug)", "(Foxhug)"]},
    "frankenstein":           {"title": "Hammer Frankenstein", "file": "frankenstein.gif", "strings": ["(frankenstein)", "(Frankenstein)"]},
    "fries":                  {"title": "Fries", "file": "fries.gif", "strings": ["(fries)", "(Fries)"]},
    "games":                  {"title": "Games", "file": "games.gif", "strings": ["(games)", "(ply)", "(PLY)", "(play)", "(Games)", "(Ply)", "(Play)", "(playbox)", "(Playbox)"]},
    "ganesh":                 {"title": "Ganesh", "file": "ganesh.gif", "strings": ["(ganesh)", "(Ganesh)"]},
    "ghost":                  {"title": "Ghost", "file": "ghost.gif", "strings": ["(ghost)", "(Ghost)"]},
    "gift":                   {"title": "Gift", "file": "gift.gif", "strings": ["(g)", "(gift)", "(G)", "(Gift)"]},
    "gingerkeepfit":          {"title": "Ginger keep fit", "file": "gingerkeepfit.gif", "strings": ["(gingerkeepfit)", "(Gingerkeepfit)"]},
    "glassceiling":           {"title": "Glass ceiling", "file": "glassceiling.gif", "strings": ["(glassceiling)", "(Glassceiling)"]},
    "goldmedal":              {"title": "Gold medal", "file": "goldmedal.gif", "strings": ["(goldmedal)", "(Goldmedal)"]},
    "goodluck":               {"title": "Goodluck", "file": "goodluck.gif", "strings": ["(gl)", "(goodluck)", "(GL)", "(Goodluck)", "(Gl)"]},
    "gottarun":               {"title": "Gotta run", "file": "gottarun.gif", "strings": ["(run)", "(gottarun)", "(gtr)", "(GTR)", "(Gottarun)", "(Gtr)", "(Run)"]},
    "gran":                   {"title": "Dancing Gran", "file": "gran.gif", "strings": ["(gran)", "(Gran)"]},
    "grannyscooter":          {"title": "Granny scooter", "file": "grannyscooter.gif", "strings": ["(grannyscooter)", "(Grannyscooter)"]},
    "grapes":                 {"title": "Grapes", "file": "grapes.gif", "strings": ["(grapes)", "(Grapes)"]},
    "greatpear":              {"title": "Great pear", "file": "greatpear.gif", "strings": ["(greatpear)", "(Greatpear)"]},
    "growingheart":           {"title": "Growing heart", "file": "growingheart.gif", "strings": ["(growingheart)"]},
    "handsinair":             {"title": "Hands in air", "file": "handsinair.gif", "strings": ["(handsinair)", "(celebrate)", "(celebration)", "(hia)", "(Celebrate)", "(Celebration)", "(Handsinair)", "(Hia)"]},
    "hanukkah":               {"title": "Hanukkah", "file": "hanukkah.gif", "strings": ["(hanukkah)", "(Hanukkah)", "(menorah)"]},
    "happyeyes":              {"title": "Happy eyes", "file": "happyeyes.gif", "strings": ["(happyeyes)"]},
    "happyface":              {"title": "Happy face", "file": "happyface.gif", "strings": ["(happyface)"]},
    "headphones":             {"title": "Listening to headphones", "file": "headphones.gif", "strings": ["(headphones)", "(Headphones)"]},
    "hearnoevil":             {"title": "Monkey hear no evil", "file": "hearnoevil.gif", "strings": ["(hearnoevil)"]},
    "heartblack":             {"title": "Black heart", "file": "heartblack.gif", "strings": ["(heartblack)", "(blackheart)"]},
    "heartblue":              {"title": "Blue heart", "file": "heartblue.gif", "strings": ["(heartblue)", "(blueheart)"]},
    "hearteyes":              {"title": "Heart Eyes", "file": "hearteyes.gif", "strings": ["(hearteyes)", "(Hearteyes)"]},
    "hearteyescat":           {"title": "Heart eyes cat", "file": "hearteyescat.gif", "strings": ["(hearteyescat)"]},
    "hearteyesdog":           {"title": "Heart eyes dog", "file": "hearteyesdog.gif", "strings": ["(hearteyesdog)"]},
    "hearteyeskoala":         {"title": "Heart eyes koala", "file": "hearteyeskoala.gif", "strings": ["(hearteyeskoala)"]},
    "hearteyesmonkey":        {"title": "Heart eyes monkey", "file": "hearteyesmonkey.gif", "strings": ["(hearteyesmonkey)"]},
    "hearteyesrobot":         {"title": "Heart eyes robot", "file": "hearteyesrobot.gif", "strings": ["(hearteyesrobot)"]},
    "heartgreen":             {"title": "Green heart", "file": "heartgreen.gif", "strings": ["(heartgreen)", "(greenheart)"]},
    "hearthands":             {"title": "Heart Hands", "file": "hearthands.gif", "strings": ["(hearthands)", "(Hearthands)"]},
    "heartpride":             {"title": "Pride heart", "file": "heartpride.gif", "strings": ["(heartpride)", "(prideheart)"]},
    "heartpurple":            {"title": "Purple heart", "file": "heartpurple.gif", "strings": ["(heartpurple)", "(purpleheart)"]},
    "heartyellow":            {"title": "Yellow heart", "file": "heartyellow.gif", "strings": ["(heartyellow)", "(yellowheart)"]},
    "hedgehog":               {"title": "Hedgehog", "file": "hedgehog.gif", "strings": ["(hedgehog)", "(Hedgehog)"]},
    "hedgehoghug":            {"title": "Hedgehog hug", "file": "hedgehoghug.gif", "strings": ["(hedgehoghug)", "(Hedgehoghug)"]},
    "heidy":                  {"title": "Squirrel", "file": "heidy.gif", "strings": ["(heidy)", "(squirrel)", "(Heidy)", "(Squirrel)"]},
    "hendance":               {"title": "Dancing Hen", "file": "hendance.gif", "strings": ["(hendance)", "(Hendance)"]},
    "highfive":               {"title": "High five", "file": "highfive.gif", "strings": ["(h5)", "(hifive)", "(highfive)", "(Highfive)", "(Hifive)", "(H5)"]},
    "holdon":                 {"title": "Hold on", "file": "holdon.gif", "strings": ["(w8)", "(holdon)", "(W8)", "(Holdon)"]},
    "holi":                   {"title": "Holi", "file": "holi.gif", "strings": ["(holi)", "(Holi)", "(rang)", "(Rang)"]},
    "holidayready":           {"title": "Holiday ready", "file": "holidayready.gif", "strings": ["(holidayready)"]},
    "holidayspirit":          {"title": "Holiday spirit", "file": "holidayspirit.gif", "strings": ["(holidayspirit)", "(Holidayspirit)", "(crazyxmas)", "(Crazyxmas)", "(crazychristmas)", "(Crazychristmas)"]},
    "hotchocolate":           {"title": "Hot chocolate", "file": "hotchocolate.gif", "strings": ["(hotchocolate)", "(Hotchocolate)"]},
    "house":                  {"title": "House", "file": "house.gif", "strings": ["(house)", "(House)", "(home)", "(Home)"]},
    "hungover":               {"title": "Morning after party", "file": "hungover.gif", "strings": ["(morningafter)", "(Morningafter)", "(hungover)", "(Hungover)"]},
    "hungrycat":              {"title": "Hungry cat", "file": "hungrycat.gif", "strings": ["(hungrycat)", "(Hungrycat)"]},
    "hysterical":             {"title": "Hysterical", "file": "hysterical.gif", "strings": ["(hysterical)", "(Hysterical)"]},
    "icecream":               {"title": "Ice cream", "file": "icecream.gif", "strings": ["(icecream)", "(Icecream)", "(1f368_icecream)"]},
    "idea":                   {"title": "Idea", "file": "idea.gif", "strings": [":i", "(idea)", ":I", "*-:)", "(Idea)"]},
    "iheartu":                {"title": "I heart You", "file": "iheartu.gif", "strings": ["(iheartu)", "(Iheartu)"]},
    "ill":                    {"title": "Ill", "file": "ill.gif", "strings": ["(ill)", "(Ill)"]},
    "island":                 {"title": "Island", "file": "island.gif", "strings": ["(island)", "(ip)", "(Island)", "(Ip)"]},
    "kaanpakadna":            {"title": "Sorry", "file": "kaanpakadna.gif", "strings": ["(kaanpakadna)", "(KaanPakadna)", "(sorry)", "(Sorry)", "(maafi)", "(Maafi)", "(Kaanpakadna)"]},
    "key":                    {"title": "Key", "file": "key.gif", "strings": ["(key)", "(Key)", "(success)", "(Success)"]},
    "koala":                  {"title": "Koala", "file": "koala.gif", "strings": ["(koala)", "(Koala)"]},
    "kya":                    {"title": "What?!", "file": "kya.gif", "strings": ["(kya)", "(Kya)"]},
    "l337":                   {"title": "L3-37", "file": "l337.gif", "strings": ["(l3-37)", "(L3-37)", "(l337)", "(L337)"]},
    "lacrosse":               {"title": "Lacrosse", "file": "lacrosse.gif", "strings": ["(lacrosse)"]},
    "laddu":                  {"title": "Sweet", "file": "laddu.gif", "strings": ["(laddu)", "(Laddu)"]},
    "ladyvampire":            {"title": "Lady Vampire", "file": "ladyvampire.gif", "strings": ["(ladyvamp)", "(Ladyvamp)", "(ladyvampire)", "(Ladyvampire)"]},
    "lalala":                 {"title": "Not listening", "file": "lalala.gif", "strings": ["(lala)", "(lalala)", "(lalalala)", "(notlistening)", "(Lalala)", "(Lalalala)", "(Lala)", "(Notlistening)"]},
    "lamb":                   {"title": "Spring Lamb", "file": "lamb.gif", "strings": ["(lamb)", "(Lamb)"]},
    "lang":                   {"title": "Lang", "file": "lang.gif", "strings": ["(lang)", "(Lang)"]},
    "laughcat":               {"title": "Laugh cat", "file": "laughcat.gif", "strings": ["(laughcat)"]},
    "laughdog":               {"title": "Laugh dog", "file": "laughdog.gif", "strings": ["(laughdog)"]},
    "laughkoala":             {"title": "Laugh koala", "file": "laughkoala.gif", "strings": ["(laughkoala)"]},
    "laughmonkey":            {"title": "Laugh monkey", "file": "laughmonkey.gif", "strings": ["(laughmonkey)"]},
    "laughrobot":             {"title": "Laugh robot", "file": "laughrobot.gif", "strings": ["(laughrobot)"]},
    "launch":                 {"title": "Rocket launch", "file": "launch.gif", "strings": ["(launch)", "(Launch)", "(rocket)", "(Rocket)", "(shuttle)", "(Shuttle)"]},
    "learn":                  {"title": "Global learning", "file": "learn.gif", "strings": ["(learn)", "(Learn)"]},
    "lemon":                  {"title": "Lemon", "file": "lemon.gif", "strings": ["(lemon)", "(Lemon)"]},
    "letsmeet":               {"title": "Let's meet", "file": "letsmeet.gif", "strings": ["(s+)", "(letsmeet)", "(S+)", "(calendar)", "(Letsmeet)", "(Calendar)"]},
    "like":                   {"title": "Like", "file": "like.gif", "strings": ["(like)", "(Like)"]},
    "lips":                   {"title": "Lips", "file": "lips.gif", "strings": ["(lips)", "(Lips)"]},
    "listening":              {"title": "Listening", "file": "listening.gif", "strings": ["(listening)", "(Listening)"]},
    "lizard":                 {"title": "Lizard", "file": "lizard.gif", "strings": ["(lizard)"]},
    "llsshock":               {"title": "Spoiler Alert", "file": "llsshock.gif", "strings": ["(llsshock)", "(Llsshock)"]},
    "lobster":                {"title": "Lobster", "file": "lobster.gif", "strings": ["(lobster)", "(1f99e_lobster)"]},
    "loudlycrying":           {"title": "Loudly crying", "file": "loudlycrying.gif", "strings": ["(loudlycrying)", "(Loudlycrying)"]},
    "lovebites":              {"title": "Love bites", "file": "lovebites.gif", "strings": ["(lovebites)", "(Lovebites)"]},
    "loveearth":              {"title": "Love Earth", "file": "loveearth.gif", "strings": ["(loveearth)"]},
    "lovegift":               {"title": "Love Gift", "file": "lovegift.gif", "strings": ["(lovegift)", "(Lovegift)"]},
    "loveletter":             {"title": "Love letter", "file": "loveletter.gif", "strings": ["(loveletter)", "(Loveletter)"]},
    "man":                    {"title": "Man", "file": "man.gif", "strings": ["(z)", "(man)", "(boy)", "(Z)", "(male)", "(Man)", "(Male)", "(Boy)"]},
    "manmanheart":            {"title": "Man man heart", "file": "manmanheart.gif", "strings": ["(manmanheart)"]},
    "manmanholdinghands":     {"title": "Man man holding hands", "file": "manmanholdinghands.gif", "strings": ["(manmanholdinghands)"]},
    "manmankiss":             {"title": "Man man kiss", "file": "manmankiss.gif", "strings": ["(manmankiss)", "(manmankissing)"]},
    "manwomanheart":          {"title": "Male woman heart", "file": "manwomanheart.gif", "strings": ["(manwomanheart)"]},
    "manwomanholdinghands":   {"title": "Man woman holding hands", "file": "manwomanholdinghands.gif", "strings": ["(manwomanholdinghands)"]},
    "manwomankiss":           {"title": "Man woman kiss", "file": "manwomankiss.gif", "strings": ["(manwomankiss)"]},
    "mariachilove":           {"title": "Mariachi Love", "file": "mariachilove.gif", "strings": ["(mariachilove)", "(Mariachilove)"]},
    "matreshka":              {"title": "Skiing toy", "file": "matreshka.gif", "strings": ["(matreshka)", "(Matreshka)", "(skiingtoy)", "(Skiingtoy)"]},
    "mishka":                 {"title": "Music bear", "file": "mishka.gif", "strings": ["(mishka)", "(Mishka)", "(musicbear)", "(Musicbear)"]},
    "mistletoe":              {"title": "Mistletoe", "file": "mistletoe.gif", "strings": ["(mistletoe)", "(Mistletoe)"]},
    "monkey":                 {"title": "Monkey", "file": "monkey.gif", "strings": ["(monkey)", "(ape)", ":(|)", "(Monkey)", "(Ape)"]},
    "monkeygiggle":           {"title": "Monkey Giggle", "file": "monkeygiggle.gif", "strings": ["(monkeygiggle)", "(Monkeygiggle)"]},
    "motorbike":              {"title": "Motorbike", "file": "motorbike.gif", "strings": ["(motorbike)"]},
    "movember":               {"title": "Movember", "file": "movember.gif", "strings": ["(movember)", "(mo)", "(november)", "(moustache)", "(mustache)", "(bowman)", ":{", "(Movember)", "(Mo)", "(November)", "(Moustache)", "(Mustache)", "(Bowman)"]},
    "movinghome":             {"title": "Moving Home", "file": "movinghome.gif", "strings": ["(movinghome)", "(Movinghome)"]},
    "mumanddaughter":         {"title": "Mum and daughter", "file": "mumanddaughter.gif", "strings": ["(mumanddaughter)", "(Mumanddaughter)", "(womanandgirl)", "(Womanandgirl)"]},
    "mumheart":               {"title": "Mum heart", "file": "mumheart.gif", "strings": ["(mumheart)", "(Mumheart)", "(momheart)", "(Momheart)"]},
    "mummy":                  {"title": "Hammer Mummy", "file": "mummy.gif", "strings": ["(mummy)", "(Mummy)"]},
    "mummywalk":              {"title": "Mummy Walk", "file": "mummywalk.gif", "strings": ["(mummywalk)", "(Mummywalk)"]},
    "muscleman":              {"title": "Muscle and fat guy", "file": "muscleman.gif", "strings": ["(muscleman)", "(Muscleman)", "(fatguy)", "(Fatguy)"]},
    "nahi":                   {"title": "No!", "file": "nahi.gif", "strings": ["(nahi)", "(Nahi)", "(naa)", "(Naa)"]},
    "naturescall":            {"title": "Nature's call", "file": "naturescall.gif", "strings": ["(ek)", "(Ek)", "(eK)", "(EK)", "(naturescall)", "(NaturesCall)", "(Naturescall)"]},
    "nazar":                  {"title": "Blessing", "file": "nazar.gif", "strings": ["(nazar)", "(Nazar)"]},
    "nestingeggs":            {"title": "Nesting Eggs", "file": "nestingeggs.gif", "strings": ["(nestingeggs)", "(Nestingeggs)"]},
    "noodles":                {"title": "Noodles", "file": "noodles.gif", "strings": ["(noodles)", "(Noodles)"]},
    "noviygod":               {"title": "Red square", "file": "noviygod.gif", "strings": ["(noviygod)", "(Noviygod)", "(redsquare)", "(Redsquare)"]},
    "noworries":              {"title": "No Worries", "file": "noworries.gif", "strings": ["(noworries)", "(Noworries)"]},
    "octopus":                {"title": "Octopus", "file": "octopus.gif", "strings": ["(octopus)", "(Octopus)"]},
    "ok":                     {"title": "OK", "file": "ok.gif", "strings": ["(ok)", "(OK)", "(oK)", "(Ok)", "(okay)", "(Okay)"]},
    "ontheloo":               {"title": "On the loo", "file": "ontheloo.gif", "strings": ["(ontheloo)", "(Ontheloo)", "(onloo)", "(Onloo)", "(nr2)", "(Nr2)", "(twittering)", "(Twittering)", "(verybusy)", "(Verybusy)"]},
    "orange":                 {"title": "Orange", "file": "orange.gif", "strings": ["(orange)", "(Orange)"]},
    "orangutanscratching":    {"title": "Orangutan Scratching", "file": "orangutanscratching.gif", "strings": ["(orangutanscratch)", "(orangutanscratching)"]},
    "orangutanwave":          {"title": "Orangutan Wave", "file": "orangutanwave.gif", "strings": ["(orangutanwave)"]},
    "oye":                    {"title": "Hey!", "file": "oye.gif", "strings": ["(oye)", "(Oye)"]},
    "palmtree":               {"title": "Palm tree", "file": "palmtree.gif", "strings": ["(palmtree)"]},
    "panda":                  {"title": "Panda", "file": "panda.gif", "strings": ["(panda)", "(Panda)"]},
    "parislove":              {"title": "Paris love", "file": "parislove.gif", "strings": ["(parislove)", "(Parislove)"]},
    "peach":                  {"title": "Peach", "file": "peach.gif", "strings": ["(peach)", "(Peach)"]},
    "penguin":                {"title": "Dancing penguin", "file": "penguin.gif", "strings": ["(penguin)", "(Penguin)", "(dancingpenguin)", "(Dancingpenguin)", "(penguindance)", "(Penguindance)", "(linux)", "(Linux)"]},
    "penguinkiss":            {"title": "Penguin Kiss", "file": "penguinkiss.gif", "strings": ["(penguinkiss)", "(Penguinkiss)"]},
    "pensive":                {"title": "Pensive", "file": "pensive.gif", "strings": ["(pensive)", "(Pensive)"]},
    "pie":                    {"title": "Pie", "file": "pie.gif", "strings": ["(pie)", "(Pie)"]},
    "pig":                    {"title": "Silly Pig", "file": "pig.gif", "strings": ["(pig)", "(Pig)"]},
    "piggybank":              {"title": "Piggy Bank", "file": "piggybank.gif", "strings": ["(piggybank)", "(Piggybank)"]},
    "pineapple":              {"title": "Pineapple", "file": "pineapple.gif", "strings": ["(pineapple)", "(Pineapple)"]},
    "plane":                  {"title": "Plane", "file": "plane.gif", "strings": ["(jet)", "(plane)", "(ap)", "(airplane)", "(aeroplane)", "(aircraft)", "(Plane)", "(Ap)", "(Airplane)", "(Aeroplane)", "(Aircraft)", "(Jet)"]},
    "pointdownindex":         {"title": "Backhand Index Pointing Down", "file": "pointdownindex.gif", "strings": ["(pointdownindex)", "(pointdownindexfinger)"]},
    "pointleftindex":         {"title": "Backhand Index Pointing Left", "file": "pointleftindex.gif", "strings": ["(pointleftindex)", "(pointleftindexfinger)"]},
    "pointrightindex":        {"title": "Backhand Index Pointing Right", "file": "pointrightindex.gif", "strings": ["(pointrightindex)", "(pointrightindexfinger)"]},
    "pointupindex":           {"title": "Index Pointing Up", "file": "pointupindex.gif", "strings": ["(pointupindex)", "(pointupindexfinger)"]},
    "poke":                   {"title": "Poke", "file": "poke.gif", "strings": ["(poke)", "(nudge)", "(Poke)", "(Nudge)"]},
    "polarbear":              {"title": "Polar bear", "file": "polarbear.gif", "strings": ["(polarbear)", "(Polarbear)", "(polarbearhug)", "(Polarbearhug)"]},
    "policecar":              {"title": "Police car", "file": "policecar.gif", "strings": ["(policecar)", "(Policecar)"]},
    "praying":                {"title": "Praying", "file": "praying.gif", "strings": ["(praying)", "(pray)", "_/\\_", "(Pray)", "(Praying)", "(namaste)", "(Namaste)"]},
    "promise":                {"title": "Promise", "file": "promise.gif", "strings": ["(promise)", "(Promise)", "(kasamse)", "(Kasamse)"]},
    "pullshot":               {"title": "Pull shot", "file": "pullshot.gif", "strings": ["(pullshot)", "(PullShot)", "(shot)", "(Shot)", "(chauka)", "(Chauka)", "(Pullshot)"]},
    "pumpkin":                {"title": "Pumpkin", "file": "pumpkin.gif", "strings": ["(pumpkin)", "(Pumpkin)", "(halloween)", "(Halloween)"]},
    "pushbike":               {"title": "Push bike", "file": "pushbike.gif", "strings": ["(pushbike)", "(Pushbike)"]},
    "racoon":                 {"title": "Racoon", "file": "racoon.gif", "strings": ["(racoon)", "(Racoon)", "(raccoon)"]},
    "rainbow":                {"title": "Rainbow", "file": "rainbow.gif", "strings": ["(r)", "(rainbow)", "(R)", "(Rainbow)", "(pride)", "(Pride)"]},
    "rainbowsmile":           {"title": "Rainbow Smile", "file": "rainbowsmile.gif", "strings": ["(rainbowsmile)", "(Rainbowsmile)"]},
    "recycle":                {"title": "Recycle", "file": "recycle.gif", "strings": ["(recycle)"]},
    "red":                    {"title": "Angry Red", "file": "red.gif", "strings": ["(red)", "(Red)"]},
    "redwine":                {"title": "Red wine", "file": "redwine.gif", "strings": ["(redwine)", "(Redwine)"]},
    "reindeer":               {"title": "Reindeer", "file": "reindeer.gif", "strings": ["(reindeer)", "(Reindeer)"]},
    "relieved":               {"title": "Relieved", "file": "relieved.gif", "strings": ["(relieved)", "(Relieved)"]},
    "ribbonblack":            {"title": "Black ribbon", "file": "ribbonblack.gif", "strings": ["(ribbonblack)"]},
    "ribbonblue":             {"title": "Blue ribbon", "file": "ribbonblue.gif", "strings": ["(ribbonblue)"]},
    "ribbongreen":            {"title": "Green ribbon", "file": "ribbongreen.gif", "strings": ["(ribbongreen)"]},
    "ribbonpink":             {"title": "Pink ribbon", "file": "ribbonpink.gif", "strings": ["(ribbonpink)"]},
    "ribbonpride":            {"title": "Pride ribbon", "file": "ribbonpride.gif", "strings": ["(ribbonpride)"]},
    "ribbonred":              {"title": "Red ribbon", "file": "ribbonred.gif", "strings": ["(ribbonred)"]},
    "ribbonyellow":           {"title": "Yellow ribbon", "file": "ribbonyellow.gif", "strings": ["(ribbonyellow)"]},
    "rickshaw":               {"title": "Rickshaw", "file": "rickshaw.gif", "strings": ["(rickshaw)", "(Rickshaw)", "(rikshaw)", "(Rikshaw)", "(ricksha)", "(Ricksha)"]},
    "ring":                   {"title": "Engagement ring", "file": "ring.gif", "strings": ["(ring)", "(Ring)", "(engagement)", "(Engagement)"]},
    "rockchick":              {"title": "Rock Chick", "file": "rockchick.gif", "strings": ["(rockchick)", "(Rockchick)"]},
    "rose":                   {"title": "Rose", "file": "rose.gif", "strings": ["(rose)", "(Rose)"]},
    "rudolfidea":             {"title": "Rudolf idea", "file": "rudolfidea.gif", "strings": ["(rudolfidea)", "(Rudolfidea)", "(rudolphidea)", "(Rudolphidea)"]},
    "rudolfsurprise":         {"title": "Surprised Rudolf", "file": "rudolfsurprise.gif", "strings": ["(rudolfsurprise)", "(Rudolfsurprise)", "(rudolphsurprise)", "(Rudolphsurprise)"]},
    "rugbyball":              {"title": "Rugby ball", "file": "rugbyball.gif", "strings": ["(rugbyball)"]},
    "running":                {"title": "Running", "file": "running.gif", "strings": ["(running)", "(Running)"]},
    "sadcat":                 {"title": "Sad cat", "file": "sadcat.gif", "strings": ["(sadcat)"]},
    "saddog":                 {"title": "Sad dog", "file": "saddog.gif", "strings": ["(saddog)"]},
    "sadkoala":               {"title": "Sad koala", "file": "sadkoala.gif", "strings": ["(sadkoala)"]},
    "sadmonkey":              {"title": "Sad monkey", "file": "sadmonkey.gif", "strings": ["(sadmonkey)"]},
    "sadness":                {"title": "Sadness", "file": "sadness.gif", "strings": ["(sadness)", "(Sadness)"]},
    "sadrobot":               {"title": "Sad robot", "file": "sadrobot.gif", "strings": ["(sadrobot)"]},
    "sailboat":               {"title": "Sailboat", "file": "sailboat.gif", "strings": ["(sailboat)", "(yacht)", "(26f5_sailboat)"]},
    "sandcastle":             {"title": "Sandcastle", "file": "sandcastle.gif", "strings": ["(sandcastle)"]},
    "santa":                  {"title": "Santa", "file": "santa.gif", "strings": ["(santa)", "(Santa)", "(xmas)", "(Xmas)", "(christmas)", "(Christmas)"]},
    "santamooning":           {"title": "Santa mooning", "file": "santamooning.gif", "strings": ["(santamooning)", "(Santamooning)", "(mooningsanta)", "(Mooningsanta)"]},
    "sarcastic":              {"title": "Sarcastic", "file": "sarcastic.gif", "strings": ["(sarcastic)", "(Sarcastic)", "(sarcasm)", "(Sarcasm)", "(slowclap)", "(Slowclap)"]},
    "scooter":                {"title": "Scooter", "file": "scooter.gif", "strings": ["(scooter)", "(Scooter)"]},
    "screamingfear":          {"title": "Screaming with fear", "file": "screamingfear.gif", "strings": ["(screamingfear)"]},
    "seal":                   {"title": "Seal", "file": "seal.gif", "strings": ["(seal)", "(Seal)"]},
    "seedling":               {"title": "Seedling", "file": "seedling.gif", "strings": ["(seedling)"]},
    "seenoevil":              {"title": "Monkey see no evil", "file": "seenoevil.gif", "strings": ["(seenoevil)"]},
    "selfie":                 {"title": "Selfie", "file": "selfie.gif", "strings": ["(selfie)", "(Selfie)"]},
    "selfiediwali":           {"title": "Selfie Diwali", "file": "selfiediwali.gif", "strings": ["(selfiediwali)", "(Selfiediwali)"]},
    "shark":                  {"title": "Shark", "file": "shark.gif", "strings": ["(shark)", "(jaws)", "(1f988_shark)"]},
    "sheep":                  {"title": "Sheep", "file": "sheep.gif", "strings": ["(sheep)", "(bah)", "(Sheep)", "(Bah)"]},
    "shivering":              {"title": "Cold shivering", "file": "shivering.gif", "strings": ["(shivering)", "(Shivering)", "(cold)", "(Cold)", "(freezing)", "(Freezing)"]},
    "shock":                  {"title": "Spoiler Alert", "file": "shock.gif", "strings": ["(shock)", "(Shock)"]},
    "shopping":               {"title": "Girl shopping", "file": "shopping.gif", "strings": ["(shopping)", "(Shopping)", "(shopper)", "(Shopper)"]},
    "shrimp":                 {"title": "Shrimp", "file": "shrimp.gif", "strings": ["(shrimp)", "(1f990_shrimp)"]},
    "silvermedal":            {"title": "Silver medal", "file": "silvermedal.gif", "strings": ["(silvermedal)", "(Silvermedal)"]},
    "skate":                  {"title": "Skate", "file": "skate.gif", "strings": ["(skate)", "(Skate)"]},
    "skip":                   {"title": "Keep Fit", "file": "skip.gif", "strings": ["(skip)", "(Skip)", "(skippingrope)", "(Skippingrope)"]},
    "skipping":               {"title": "Skipping", "file": "skipping.gif", "strings": ["(skipping)", "(Skipping)"]},
    "skull":                  {"title": "Skull", "file": "skull.gif", "strings": ["(skull)", "(Skull)"]},
    "slamdunk":               {"title": "Basketball", "file": "slamdunk.gif", "strings": ["(slamdunk)", "(Slamdunk)"]},
    "slap":                   {"title": "Slap", "file": "slap.gif", "strings": ["(slap)", "(Slap)", "(thappad)", "(Thappad)"]},
    "sloth":                  {"title": "Sloth", "file": "sloth.gif", "strings": ["(sloth)", "(Sloth)"]},
    "smilebaby":              {"title": "Smile baby", "file": "smilebaby.gif", "strings": ["(smilebaby)"]},
    "smileboy":               {"title": "Smile boy", "file": "smileboy.gif", "strings": ["(smileboy)"]},
    "smilecat":               {"title": "Smile cat", "file": "smilecat.gif", "strings": ["(smilecat)"]},
    "smiledog":               {"title": "Smile dog", "file": "smiledog.gif", "strings": ["(smiledog)"]},
    "smileeyes":              {"title": "Smile eyes", "file": "smileeyes.gif", "strings": ["(smileeyes)"]},
    "smilegirl":              {"title": "Smile girl", "file": "smilegirl.gif", "strings": ["(smilegirl)"]},
    "smilekoala":             {"title": "Smile koala", "file": "smilekoala.gif", "strings": ["(smilekoala)"]},
    "smileman":               {"title": "Smile man", "file": "smileman.gif", "strings": ["(smileman)"]},
    "smilemonkey":            {"title": "Smile monkey", "file": "smilemonkey.gif", "strings": ["(smilemonkey)"]},
    "smilerobot":             {"title": "Smile robot", "file": "smilerobot.gif", "strings": ["(smilerobot)"]},
    "smilewoman":             {"title": "Smile woman", "file": "smilewoman.gif", "strings": ["(smilewoman)"]},
    "snail":                  {"title": "Snail", "file": "snail.gif", "strings": ["(snail)", "(sn)", "(SN)", "(Snail)", "(Sn)"]},
    "snake":                  {"title": "Snake", "file": "snake.gif", "strings": ["(snake)", "(Snake)"]},
    "snegovik":               {"title": "Snow buddie", "file": "snegovik.gif", "strings": ["(snegovik)", "(Snegovik)", "(snowbuddie)", "(Snowbuddie)"]},
    "snorkler":               {"title": "Snorkler", "file": "snorkler.gif", "strings": ["(snorkler)"]},
    "snowangel":              {"title": "Snow angel", "file": "snowangel.gif", "strings": ["(snowangel)", "(Snowangel)"]},
    "snowflake":              {"title": "Snowflake", "file": "snowflake.gif", "strings": ["(snowflake)", "(Snowflake)"]},
    "soccerball":             {"title": "Soccer ball", "file": "soccerball.gif", "strings": ["(soccerball)"]},
    "sparkler":               {"title": "Sparkler", "file": "sparkler.gif", "strings": ["(sparkler)", "(Sparkler)"]},
    "sparklingheart":         {"title": "Sparkling heart", "file": "sparklingheart.gif", "strings": ["(sparklingheart)"]},
    "speaknoevil":            {"title": "Monkey speak no evil", "file": "speaknoevil.gif", "strings": ["(speaknoevil)"]},
    "speechbubble":           {"title": "Speech bubble", "file": "speechbubble.gif", "strings": ["(speechbubble)", "(Speechbubble)"]},
    "spider":                 {"title": "Spider", "file": "spider.gif", "strings": ["(spider)", "(Spider)"]},
    "squid":                  {"title": "Squid", "file": "squid.gif", "strings": ["(squid)", "(1f991_squid)"]},
    "stareyes":               {"title": "Star eyes", "file": "stareyes.gif", "strings": ["(stareyes)", "(Stareyes)"]},
    "statueofliberty":        {"title": "Statue of Liberty", "file": "statueofliberty.gif", "strings": ["(statueofliberty)", "(Statueofliberty)"]},
    "steamtrain":             {"title": "Steam train", "file": "steamtrain.gif", "strings": ["(steamtrain)", "(Steamtrain)", "(train)", "(Train)"]},
    "stingray":               {"title": "Stingray", "file": "stingray.gif", "strings": ["(stingray)", "(Stingray)"]},
    "stop":                   {"title": "Stop", "file": "stop.gif", "strings": ["(!)", "(stop)", "(Stop)"]},
    "strawberry":             {"title": "Strawberry", "file": "strawberry.gif", "strings": ["(strawberry)", "(Strawberry)"]},
    "sunflower":              {"title": "Sunflower", "file": "sunflower.gif", "strings": ["(sunflower)", "(Sunflower)"]},
    "sunrise":                {"title": "Sunrise", "file": "sunrise.gif", "strings": ["(sunrise)", "(1f305_sunrise)"]},
    "sweatgrinning":          {"title": "Sweat grinning", "file": "sweatgrinning.gif", "strings": ["(sweatgrinning)", "(Sweatgrinning)"]},
    "syne":                   {"title": "Syne", "file": "syne.gif", "strings": ["(syne)", "(Syne)"]},
    "talktothehand":          {"title": "Talk to the hand", "file": "talktothehand.gif", "strings": ["(talktothehand)", "(Talktothehand)"]},
    "tandoorichicken":        {"title": "Tandoori chicken", "file": "tandoorichicken.gif", "strings": ["(tandoori)", "(Tandoori)", "(tandoorichicken)", "(TandooriChicken)", "(Tandoorichicken)"]},
    "target":                 {"title": "Archery", "file": "target.gif", "strings": ["(target)", "(Target)"]},
    "taxi":                   {"title": "Taxi", "file": "taxi.gif", "strings": ["(taxi)", "(Taxi)"]},
    "tennisball":             {"title": "Tennis ball", "file": "tennisball.gif", "strings": ["(tennisball)"]},
    "tennisfail":             {"title": "Tennis fail", "file": "tennisfail.gif", "strings": ["(tennisfail)", "(Tennisfail)"]},
    "thanks":                 {"title": "Thanks", "file": "thanks.gif", "strings": ["(thanks)", "(Thanks)"]},
    "tired":                  {"title": "Tired", "file": "tired.gif", "strings": ["(tired)", "(Tired)"]},
    "tortoise":               {"title": "Tortoise", "file": "tortoise.gif", "strings": ["(tortoise)", "(Tortoise)"]},
    "trophy":                 {"title": "Trophy", "file": "trophy.gif", "strings": ["(trophy)", "(Trophy)"]},
    "truck":                  {"title": "Truck", "file": "truck.gif", "strings": ["(truck)", "(Truck)"]},
    "ttm":                    {"title": "Talking too much", "file": "ttm.gif", "strings": ["(ttm)", "(Ttm)", "(bla)", "(Bla)"]},
    "tubelight":              {"title": "Tubelight", "file": "tubelight.gif", "strings": ["(tubelight)", "(Tubelight)"]},
    "tulip":                  {"title": "Tulip", "file": "tulip.gif", "strings": ["(tulip)", "(Tulip)"]},
    "tumbleweed":             {"title": "Tumbleweed", "file": "tumbleweed.gif", "strings": ["(tumbleweed)", "(Tumbleweed)"]},
    "turkey":                 {"title": "Dancing Thanksgiving turkey", "file": "turkey.gif", "strings": ["(turkey)", "(Turkey)", "(turkeydance)", "(Turkeydance)", "(thanksgiving)", "(Thanksgiving)"]},
    "turtle":                 {"title": "Turtle", "file": "turtle.gif", "strings": ["(turtle)"]},
    "tvbinge":                {"title": "TV binge Zombie", "file": "tvbinge.gif", "strings": ["(tvbinge)", "(Tvbinge)"]},
    "twohearts":              {"title": "Two hearts", "file": "twohearts.gif", "strings": ["(twohearts)"]},
    "umbrella":               {"title": "Umbrella", "file": "umbrella.gif", "strings": ["(um)", "(umbrella)", "(Umbrella)", "(Um)"]},
    "umbrellaonground":       {"title": "Umbrella on ground", "file": "umbrellaonground.gif", "strings": ["(umbrellaonground)", "(26f1_umbrellaonground)"]},
    "unamused":               {"title": "Unamused", "file": "unamused.gif", "strings": ["(unamused)", "(Unamused)"]},
    "unicorn":                {"title": "Unicorn", "file": "unicorn.gif", "strings": ["(unicorn)", "(Unicorn)"]},
    "unicornhead":            {"title": "Unicorn head", "file": "unicornhead.gif", "strings": ["(unicornhead)", "(Unicornhead)"]},
    "unsee":                  {"title": "Can't unsee that", "file": "unsee.gif", "strings": ["(unsee)", "(Unsee)"]},
    "upsidedownface":         {"title": "Upside down face", "file": "upsidedownface.gif", "strings": ["(upsidedownface)"]},
    "vampire":                {"title": "Vampire", "file": "vampire.gif", "strings": ["(vampire)", "(Vampire)"]},
    "veryconfused":           {"title": "Very confused", "file": "veryconfused.gif", "strings": ["(veryconfused)", "(Veryconfused)"]},
    "victory":                {"title": "Victory", "file": "victory.gif", "strings": ["(victory)", "(Victory)"]},
    "vulcansalute":           {"title": "Vulcan salute", "file": "vulcansalute.gif", "strings": ["(vulcansalute)", "(Vulcansalute)"]},
    "waiting":                {"title": "Waiting", "file": "waiting.gif", "strings": ["(waiting)", "(forever)", "(impatience)", "(Waiting)", "(Forever)", "(Impatience)"]},
    "watermelon":             {"title": "Watermelon", "file": "watermelon.gif", "strings": ["(watermelon)", "(Watermelon)"]},
    "waterwave":              {"title": "Water wave", "file": "waterwave.gif", "strings": ["(waterwave)", "(waves)", "(1f30a_waterwave)"]},
    "weary":                  {"title": "Weary", "file": "weary.gif", "strings": ["(weary)", "(Weary)"]},
    "webheart":               {"title": "Web Heart", "file": "webheart.gif", "strings": ["(webheart)", "(Webheart)"]},
    "wfh":                    {"title": "Working from home", "file": "wfh.gif", "strings": ["(@h)", "(wfh)", "(@H)", "(Wfh)"]},
    "whale":                  {"title": "Whale", "file": "whale.gif", "strings": ["(whale)", "(Whale)"]},
    "whatsgoingon":           {"title": "What's going on?", "file": "whatsgoingon.gif", "strings": ["(!!?)", "(whatsgoingon)", "(Whatsgoingon)"]},
    "whistle":                {"title": "Whistle", "file": "whistle.gif", "strings": ["(whistle)", "(Whistle)", "(seeti)", "(Seeti)"]},
    "wiltedflower":           {"title": "Wilted flower", "file": "wiltedflower.gif", "strings": ["(wiltedflower)", "(Wiltedflower)", "(w)", "(W)"]},
    "windturbine":            {"title": "Wind Turbine", "file": "windturbine.gif", "strings": ["(windturbine)"]},
    "winktongueout":          {"title": "Winking tongue out", "file": "winktongueout.gif", "strings": [";p", ";-p", ";=p", ";P", ";-P", ";=P", "(winktongueout)"]},
    "winner":                 {"title": "Podium", "file": "winner.gif", "strings": ["(winner)", "(Winner)"]},
    "witch":                  {"title": "Witch", "file": "witch.gif", "strings": ["(witch)", "(Witch)"]},
    "woman":                  {"title": "Woman", "file": "woman.gif", "strings": ["(x)", "(woman)", "(X)", "(female)", "(girl)", "(Woman)", "(Female)", "(Girl)"]},
    "womanwomanheart":        {"title": "Woman woman heart", "file": "womanwomanheart.gif", "strings": ["(womanwomanheart)"]},
    "womanwomanholdinghands": {"title": "Woman woman holding hands", "file": "womanwomanholdinghands.gif", "strings": ["(womanwomanholdinghands)"]},
    "womanwomankiss":         {"title": "Woman woman kiss", "file": "womanwomankiss.gif", "strings": ["(womanwomankiss)", "(womanwomankissing)"]},
    "woty":                   {"title": "Woman of the year", "file": "woty.gif", "strings": ["(woty)", "(Woty)"]},
    "wtf":                    {"title": "What the...", "file": "wtf.gif", "strings": ["(wtf)", "(Wtf)"]},
    "xd":                     {"title": "XD smiley", "file": "xd.gif", "strings": ["(xd)", "(Xd)"]},
    "xmascar":                {"title": "Xmas car", "file": "xmascar.gif", "strings": ["(xmascar)", "(Xmascar)"]},
    "xmascry":                {"title": "Xmas cry", "file": "xmascry.gif", "strings": ["(xmascry)", "(Xmascry)", "(xmascrying)", "(Xmascrying)"]},
    "xmascwl":                {"title": "Xmas crying with laughter", "file": "xmascwl.gif", "strings": ["(xmascwl)", "(Xmascwl)"]},
    "xmasheart":              {"title": "Xmas heart", "file": "xmasheart.gif", "strings": ["(xmasheart)", "(Xmasheart)"]},
    "xmassarcastic":          {"title": "Xmas sarcastic", "file": "xmassarcastic.gif", "strings": ["(xmassarcastic)", "(Xmassarcastic)"]},
    "xmastree":               {"title": "Xmas tree", "file": "xmastree.gif", "strings": ["(xmastree)", "(Xmastree)", "(christmastree)", "(Christmastree)"]},
    "xmasyes":                {"title": "Xmas yes", "file": "xmasyes.gif", "strings": ["(xmasyes)", "(Xmasyes)"]},
    "yoga":                   {"title": "Yoga", "file": "yoga.gif", "strings": ["(yoga)", "(Yoga)"]},
    "zombie":                 {"title": "Zombie", "file": "zombie.gif", "strings": ["(zombie)", "(Zombie)"]},
    "zombiedrool":            {"title": "Hammer Zombie", "file": "zombiedrool.gif", "strings": ["(zombiedrool)", "(Zombiedrool)"]},
    "zombiewave":             {"title": "Zombie Wave", "file": "zombiewave.gif", "strings": ["(zombiewave)", "(Zombiewave)"]},
}


HEADER = u'''# -*- coding: utf-8 -*-
"""
Contains Skype emoticon image loaders. Auto-generated.
Skype emoticon images are property of Skype, released under the
Skype Component License 1.0.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     11.06.2013
@modified    %s
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
                logger.exception("Error loading emoticons from %%s.", path)
        if not ZipLoader._file: return None
        try: return ZipLoader._file.open(filename).read()
        except Exception:
            logger.exception("Error loading emoticon %%s.", filename)


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
''' % datetime.date.today().strftime("%d.%m.%Y")



def create_py(target):
    global HEADER, EMOTICONS
    f = io.open(target, "w", encoding="utf-8")
    f.write(HEADER)
    for name, data in sorted(EMOTICONS.items()):
        if "file" not in data: continue # for name, data
        f.write(u"\n\n%sSkype emoticon \"%s %s\".%s\n%s = LazyFileImage(\"%s\")" %
                (Q3, data["title"], data["strings"][0], Q3, name, data["file"]))
    f.write(u"\n\n\n%sEmoticon metadata: name, strings, title.%s\n"
            u"EmoticonData = {\n" % (Q3, Q3))
    for name, data in sorted(EMOTICONS.items()):
        data_py = {"strings": data["strings"], "title": data["title"]}
        f.write(u"    \"%s\": %s,\n" % (name, json.dumps(data_py)))
    f.write(u"}\n")
    f.write(u"\n\n%sMaps emoticon strings to emoticon names.%s\n" % (Q3, Q3))
    f.write(u"EmoticonStrings = dict((s, k) for k, d in EmoticonData.items()"
            u" for s in d[\"strings\"])\n")
    f.close()


def create_zip(target):
    with zipfile.ZipFile(target, mode="w") as zf:
        for name, data in sorted(EMOTICONS.items()):
            if not data.get("file"): continue # for name, data
            zi = zipfile.ZipInfo(data["file"])
            zi.compress_type = zipfile.ZIP_DEFLATED
            path = os.path.join("emoticons", data["file"])
            with open(path, "rb") as f: zf.writestr(zi, f.read())


if "__main__" == __name__:
    create_py(PYTARGET)
    create_zip(ZIPTARGET)
