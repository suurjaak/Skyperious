# -*- coding: utf-8 -*-
"""
Contains Skype emoticon image loaders. Auto-generated.
Skype emoticon images are property of Skype, released under the
Skype Component License 1.0.

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     11.06.2013
@modified    22.03.2022
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


"""Skype emoticon "Hey, you! (abe)"."""
abe = LazyFileImage("abe.gif")

"""Skype emoticon "Acorn (acorn)"."""
acorn = LazyFileImage("acorn.gif")

"""Skype emoticon "Ambulance (ambulance)"."""
ambulance = LazyFileImage("ambulance.gif")

"""Skype emoticon "American Football (americanfootball)"."""
americanfootball = LazyFileImage("americanfootball.gif")

"""Skype emoticon "Angel (a)"."""
angel = LazyFileImage("0131-angel.gif")

"""Skype emoticon "Anger (anger)"."""
anger = LazyFileImage("anger.gif")

"""Skype emoticon "Angry :@"."""
angry = LazyFileImage("0121-angry.gif")

"""Skype emoticon "Angry Face (angryface)"."""
angryface = LazyFileImage("angryface.gif")

"""Skype emoticon "Apple (apple)"."""
apple = LazyFileImage("apple.gif")

"""Skype emoticon "Eggplant (aubergine)"."""
aubergine = LazyFileImage("aubergine.gif")

"""Skype emoticon "Auld (auld)"."""
auld = LazyFileImage("auld.gif")

"""Skype emoticon "Avocado Love (avocadolove)"."""
avocadolove = LazyFileImage("avocadolove.gif")

"""Skype emoticon "Banana (banana)"."""
banana = LazyFileImage("banana.gif")

"""Skype emoticon "Bandit (bandit)"."""
bandit = LazyFileImage("0174-bandit.gif")

"""Skype emoticon "Soccer (football)"."""
bartlett = LazyFileImage("bartlett.gif")

"""Skype emoticon "Baseball (baseball)"."""
baseball = LazyFileImage("baseball.gif")

"""Skype emoticon "Basketball (basketball)"."""
basketball = LazyFileImage("basketball.gif")

"""Skype emoticon "Bee (bee)"."""
bee = LazyFileImage("bee.gif")

"""Skype emoticon "Beer (beer)"."""
beer = LazyFileImage("0167-beer.gif")

"""Skype emoticon "Bell (bell)"."""
bell = LazyFileImage("bell.gif")

"""Skype emoticon "Bhangra (bhangra)"."""
bhangra = LazyFileImage("bhangra.gif")

"""Skype emoticon "Bicycle (bike)"."""
bike = LazyFileImage("bike.gif")

"""Skype emoticon "Face without mouth (blankface)"."""
blankface = LazyFileImage("blankface.gif")

"""Skype emoticon "Blushing :$"."""
blush = LazyFileImage("0111-blush.gif")

"""Skype emoticon "In love pose (bollylove)"."""
bollylove = LazyFileImage("bollylove.gif")

"""Skype emoticon "Bomb (bomb)"."""
bomb = LazyFileImage("bomb.gif")

"""Skype emoticon "Bottle feeding (bottlefeeding)"."""
bottlefeeding = LazyFileImage("bottlefeeding.gif")

"""Skype emoticon "Bowing (bow)"."""
bow = LazyFileImage("0139-bow.gif")

"""Skype emoticon "Bowled (bowled)"."""
bowled = LazyFileImage("bowled.gif")

"""Skype emoticon "Bowling ball (bowlingball)"."""
bowlingball = LazyFileImage("bowlingball.gif")

"""Skype emoticon "Be Right Back (brb)"."""
brb = LazyFileImage("brb.gif")

"""Skype emoticon "Breakfast in bed (breakfastinbed)"."""
breakfastinbed = LazyFileImage("breakfastinbed.gif")

"""Skype emoticon "Breastfeeding (breastfeeding)"."""
breastfeeding = LazyFileImage("breastfeeding.gif")

"""Skype emoticon "Broken heart (u)"."""
brokenheart = LazyFileImage("0153-brokenheart.gif")

"""Skype emoticon "Black broken heart (brokenheartblack)"."""
brokenheartblack = LazyFileImage("brokenheartblack.gif")

"""Skype emoticon "Blue broken heart (brokenheartblue)"."""
brokenheartblue = LazyFileImage("brokenheartblue.gif")

"""Skype emoticon "Green broken heart (brokenheartgreen)"."""
brokenheartgreen = LazyFileImage("brokenheartgreen.gif")

"""Skype emoticon "Purple broken heart (brokenheartpurple)"."""
brokenheartpurple = LazyFileImage("brokenheartpurple.gif")

"""Skype emoticon "Yellow broken heart (brokenheartyellow)"."""
brokenheartyellow = LazyFileImage("brokenheartyellow.gif")

"""Skype emoticon "Bronze medal (bronzemedal)"."""
bronzemedal = LazyFileImage("bronzemedal.gif")

"""Skype emoticon "Bug (bug)"."""
bug = LazyFileImage("0180-bug.gif")

"""Skype emoticon "Bunny (bunny)"."""
bunny = LazyFileImage("bunny.gif")

"""Skype emoticon "Bunny hug (bunnyhug)"."""
bunnyhug = LazyFileImage("bunnyhug.gif")

"""Skype emoticon "Burger (burger)"."""
burger = LazyFileImage("burger.gif")

"""Skype emoticon "Busy Day (busyday)"."""
busyday = LazyFileImage("busyday.gif")

"""Skype emoticon "Butterfly (butterfly)"."""
butterfly = LazyFileImage("butterfly.gif")

"""Skype emoticon "Cactus Love (cactuslove)"."""
cactuslove = LazyFileImage("cactuslove.gif")

"""Skype emoticon "Cake (^)"."""
cake = LazyFileImage("0166-cake.gif")

"""Skype emoticon "Cake slice (cakeslice)"."""
cakeslice = LazyFileImage("cakeslice.gif")

"""Skype emoticon "Cake Throw (cakethrow)"."""
cakethrow = LazyFileImage("cakethrow.gif")

"""Skype emoticon "Call (call)"."""
call = LazyFileImage("0129-call.gif")

"""Skype emoticon "Camera (p)"."""
camera = LazyFileImage("camera.gif")

"""Skype emoticon "Canoe (canoe)"."""
canoe = LazyFileImage("canoe.gif")

"""Skype emoticon "Can you talk? (!!)"."""
canyoutalk = LazyFileImage("canyoutalk.gif")

"""Skype emoticon "Car (car)"."""
car = LazyFileImage("car.gif")

"""Skype emoticon "Cash ($)"."""
cash = LazyFileImage("0164-cash.gif")

"""Skype emoticon "Cat :3"."""
cat = LazyFileImage("cat.gif")

"""Skype emoticon "Tea (chai)"."""
chai = LazyFileImage("chai.gif")

"""Skype emoticon "Champagne (champagne)"."""
champagne = LazyFileImage("champagne.gif")

"""Skype emoticon "Slipper (chappal)"."""
chappal = LazyFileImage("chappal.gif")

"""Skype emoticon "Cheerleader (cheerleader)"."""
cheerleader = LazyFileImage("cheerleader.gif")

"""Skype emoticon "Cheers! (cheers)"."""
cheers = LazyFileImage("cheers.gif")

"""Skype emoticon "Cheese (cheese)"."""
cheese = LazyFileImage("cheese.gif")

"""Skype emoticon "Cherries (cherries)"."""
cherries = LazyFileImage("cherries.gif")

"""Skype emoticon "Cherry blossom (cherryblossom)"."""
cherryblossom = LazyFileImage("cherryblossom.gif")

"""Skype emoticon "Chicken leg (chickenleg)"."""
chickenleg = LazyFileImage("chickenleg.gif")

"""Skype emoticon "Chicks' Egg (chicksegg)"."""
chicksegg = LazyFileImage("chicksegg.gif")

"""Skype emoticon "Clapping (clap)"."""
clap = LazyFileImage("0137-clapping.gif")

"""Skype emoticon "Coffee (coffee)"."""
coffee = LazyFileImage("0162-coffee.gif")

"""Skype emoticon "Computer (pc)"."""
computer = LazyFileImage("computer.gif")

"""Skype emoticon "Computer rage (computerrage)"."""
computerrage = LazyFileImage("computerrage.gif")

"""Skype emoticon "Confidential (qt)"."""
confidential = LazyFileImage("confidential.gif")

"""Skype emoticon "Confused (confused)"."""
confused = LazyFileImage("confused.gif")

"""Skype emoticon "Cookies (cookies)"."""
cookies = LazyFileImage("cookies.gif")

"""Skype emoticon "Cool 8-)"."""
cool = LazyFileImage("0103-cool.gif")

"""Skype emoticon "Cool cat (coolcat)"."""
coolcat = LazyFileImage("coolcat.gif")

"""Skype emoticon "Cool dog (cooldog)"."""
cooldog = LazyFileImage("cooldog.gif")

"""Skype emoticon "Cool koala (coolkoala)"."""
coolkoala = LazyFileImage("coolkoala.gif")

"""Skype emoticon "Cool monkey (coolmonkey)"."""
coolmonkey = LazyFileImage("coolmonkey.gif")

"""Skype emoticon "Cool robot (coolrobot)"."""
coolrobot = LazyFileImage("coolrobot.gif")

"""Skype emoticon "Crab (crab)"."""
crab = LazyFileImage("crab.gif")

"""Skype emoticon "Cricket (cricket)"."""
cricket = LazyFileImage("cricket.gif")

"""Skype emoticon "Croissant (croissant)"."""
croissant = LazyFileImage("croissant.gif")

"""Skype emoticon "Crying ;("."""
cry = LazyFileImage("0106-crying.gif")

"""Skype emoticon "Cupcake (cupcake)"."""
cupcake = LazyFileImage("cupcake.gif")

"""Skype emoticon "Crying with laughter (cwl)"."""
cwl = LazyFileImage("cwl.gif")

"""Skype emoticon "Dad Time (dadtime)"."""
dadtime = LazyFileImage("dadtime.gif")

"""Skype emoticon "Dancing \o/"."""
dance = LazyFileImage("0169-dance.gif")

"""Skype emoticon "Dead Yes (deadyes)"."""
deadyes = LazyFileImage("deadyes.gif")

"""Skype emoticon "Deciduous Tree (deciduoustree)"."""
deciduoustree = LazyFileImage("deciduoustree.gif")

"""Skype emoticon "Frost wizard (dedmoroz)"."""
dedmoroz = LazyFileImage("dedmoroz.gif")

"""Skype emoticon "Desert (desert)"."""
desert = LazyFileImage("desert.gif")

"""Skype emoticon "Devil (devil)"."""
devil = LazyFileImage("0130-devil.gif")

"""Skype emoticon "Fool (dhakkan)"."""
dhakkan = LazyFileImage("dhakkan.gif")

"""Skype emoticon "Diamond (diamond)"."""
diamond = LazyFileImage("diamond.gif")

"""Skype emoticon "Disappointed (disappointed)"."""
disappointed = LazyFileImage("disappointed.gif")

"""Skype emoticon "Disco dancer (disco)"."""
discodancer = LazyFileImage("discodancer.gif")

"""Skype emoticon "Disgust (disgust)"."""
disgust = LazyFileImage("disgust.gif")

"""Skype emoticon "Diwali Selfie (diwaliselfie)"."""
diwaliselfie = LazyFileImage("diwaliselfie.gif")

"""Skype emoticon "Tealight (diwali)"."""
diya = LazyFileImage("diya.gif")

"""Skype emoticon "Dog (&)"."""
dog = LazyFileImage("dog.gif")

"""Skype emoticon "Doh! (doh)"."""
doh = LazyFileImage("0120-doh.gif")

"""Skype emoticon "Dolphin (dolphin)"."""
dolphin = LazyFileImage("dolphin.gif")

"""Skype emoticon "Donkey (donkey)"."""
donkey = LazyFileImage("donkey.gif")

"""Skype emoticon "Don't talk to me (donttalk)"."""
donttalktome = LazyFileImage("donttalktome.gif")

"""Skype emoticon "Hammer Dracula (dracula)"."""
dracula = LazyFileImage("dracula.gif")

"""Skype emoticon "Dreaming (dream)"."""
dream = LazyFileImage("dream.gif")

"""Skype emoticon "Dreidel (dreidel)"."""
dreidel = LazyFileImage("dreidel.gif")

"""Skype emoticon "Drink (d)"."""
drink = LazyFileImage("0168-drink.gif")

"""Skype emoticon "Drop the mic (dropthemic)"."""
dropthemic = LazyFileImage("dropthemic.gif")

"""Skype emoticon "Drunk (drunk)"."""
drunk = LazyFileImage("0175-drunk.gif")

"""Skype emoticon "Dull |("."""
dull = LazyFileImage("0114-dull.gif")

"""Skype emoticon "Evil grin ]:)"."""
eg = LazyFileImage("0116-evilgrin.gif")

"""Skype emoticon "Eid (eid)"."""
eid = LazyFileImage("eid.gif")

"""Skype emoticon "Pool eight ball (eightball)"."""
eightball = LazyFileImage("eightball.gif")

"""Skype emoticon "Elephant (elephant)"."""
elephant = LazyFileImage("elephant.gif")

"""Skype emoticon "Emo (emo)"."""
emo = LazyFileImage("0147-emo.gif")

"""Skype emoticon "Envy (envy)"."""
envy = LazyFileImage("0132-envy.gif")

"""Skype emoticon "Evergreen Tree (evergreentree)"."""
evergreentree = LazyFileImage("evergreentree.gif")

"""Skype emoticon "Expressionless (expressionless)"."""
expressionless = LazyFileImage("expressionless.gif")

"""Skype emoticon "Facepalm (fail)"."""
facepalm = LazyFileImage("facepalm.gif")

"""Skype emoticon "Falling leaf (fallingleaf)"."""
fallingleaf = LazyFileImage("fallingleaf.gif")

"""Skype emoticon "Falling in love (fallinlove)"."""
fallinlove = LazyFileImage("fallinlove.gif")

"""Skype emoticon "Family (family)"."""
family = LazyFileImage("family.gif")

"""Skype emoticon "Family Time (familytime)"."""
familytime = LazyFileImage("familytime.gif")

"""Skype emoticon "Fearful (fearful)"."""
fearful = LazyFileImage("fearful.gif")

"""Skype emoticon "Festive party (festiveparty)"."""
festiveparty = LazyFileImage("festiveparty.gif")

"""Skype emoticon "Finger (finger)"."""
finger = LazyFileImage("0173-middlefinger.gif")

"""Skype emoticon "Fingers crossed (yn)"."""
fingerscrossed = LazyFileImage("fingerscrossed.gif")

"""Skype emoticon "Fire (fire)"."""
fire = LazyFileImage("fire.gif")

"""Skype emoticon "Fireworks (fireworks)"."""
fireworks = LazyFileImage("fireworks.gif")

"""Skype emoticon "Fish (fish)"."""
fish = LazyFileImage("fish.gif")

"""Skype emoticon "Good work! (fistbump)"."""
fistbump = LazyFileImage("fistbump.gif")

"""Skype emoticon "Flag in hole (flaginhole)"."""
flaginhole = LazyFileImage("flaginhole.gif")

"""Skype emoticon "Flower (f)"."""
flower = LazyFileImage("0155-flower.gif")

"""Skype emoticon "Flushed (flushed)"."""
flushed = LazyFileImage("flushed.gif")

"""Skype emoticon "Football fail (footballfail)"."""
footballfail = LazyFileImage("footballfail.gif")

"""Skype emoticon "Forever love (foreverlove)"."""
foreverlove = LazyFileImage("foreverlove.gif")

"""Skype emoticon "Fox hug (foxhug)"."""
foxhug = LazyFileImage("foxhug.gif")

"""Skype emoticon "Hammer Frankenstein (frankenstein)"."""
frankenstein = LazyFileImage("frankenstein.gif")

"""Skype emoticon "Fries (fries)"."""
fries = LazyFileImage("fries.gif")

"""Skype emoticon "FUBAR (fubar)"."""
fubar = LazyFileImage("0181-fubar.gif")

"""Skype emoticon "Games (games)"."""
games = LazyFileImage("games.gif")

"""Skype emoticon "Ganesh (ganesh)"."""
ganesh = LazyFileImage("ganesh.gif")

"""Skype emoticon "Ghost (ghost)"."""
ghost = LazyFileImage("ghost.gif")

"""Skype emoticon "Gift (g)"."""
gift = LazyFileImage("gift.gif")

"""Skype emoticon "Giggle (giggle)"."""
giggle = LazyFileImage("0136-giggle.gif")

"""Skype emoticon "Ginger keep fit (gingerkeepfit)"."""
gingerkeepfit = LazyFileImage("gingerkeepfit.gif")

"""Skype emoticon "Glass ceiling (glassceiling)"."""
glassceiling = LazyFileImage("glassceiling.gif")

"""Skype emoticon "Gold medal (goldmedal)"."""
goldmedal = LazyFileImage("goldmedal.gif")

"""Skype emoticon "Goodluck (gl)"."""
goodluck = LazyFileImage("goodluck.gif")

"""Skype emoticon "Gotta run (run)"."""
gottarun = LazyFileImage("gottarun.gif")

"""Skype emoticon "Dancing Gran (gran)"."""
gran = LazyFileImage("gran.gif")

"""Skype emoticon "Granny scooter (grannyscooter)"."""
grannyscooter = LazyFileImage("grannyscooter.gif")

"""Skype emoticon "Grapes (grapes)"."""
grapes = LazyFileImage("grapes.gif")

"""Skype emoticon "Great pear (greatpear)"."""
greatpear = LazyFileImage("greatpear.gif")

"""Skype emoticon "Growing heart (growingheart)"."""
growingheart = LazyFileImage("growingheart.gif")

"""Skype emoticon "Handshake (handshake)"."""
handshake = LazyFileImage("0150-handshake.gif")

"""Skype emoticon "Hands in air (handsinair)"."""
handsinair = LazyFileImage("handsinair.gif")

"""Skype emoticon "Hanukkah (hanukkah)"."""
hanukkah = LazyFileImage("hanukkah.gif")

"""Skype emoticon "Happy (happy)"."""
happy = LazyFileImage("0142-happy.gif")

"""Skype emoticon "Happy eyes (happyeyes)"."""
happyeyes = LazyFileImage("happyeyes.gif")

"""Skype emoticon "Happy face (happyface)"."""
happyface = LazyFileImage("happyface.gif")

"""Skype emoticon "Banging head on wall (headbang)"."""
headbang = LazyFileImage("0179-headbang.gif")

"""Skype emoticon "Listening to headphones (headphones)"."""
headphones = LazyFileImage("headphones.gif")

"""Skype emoticon "Monkey hear no evil (hearnoevil)"."""
hearnoevil = LazyFileImage("hearnoevil.gif")

"""Skype emoticon "Heart <3"."""
heart = LazyFileImage("0152-heart.gif")

"""Skype emoticon "Black heart (heartblack)"."""
heartblack = LazyFileImage("heartblack.gif")

"""Skype emoticon "Blue heart (heartblue)"."""
heartblue = LazyFileImage("heartblue.gif")

"""Skype emoticon "Heart Eyes (hearteyes)"."""
hearteyes = LazyFileImage("hearteyes.gif")

"""Skype emoticon "Heart eyes cat (hearteyescat)"."""
hearteyescat = LazyFileImage("hearteyescat.gif")

"""Skype emoticon "Heart eyes dog (hearteyesdog)"."""
hearteyesdog = LazyFileImage("hearteyesdog.gif")

"""Skype emoticon "Heart eyes koala (hearteyeskoala)"."""
hearteyeskoala = LazyFileImage("hearteyeskoala.gif")

"""Skype emoticon "Heart eyes monkey (hearteyesmonkey)"."""
hearteyesmonkey = LazyFileImage("hearteyesmonkey.gif")

"""Skype emoticon "Heart eyes robot (hearteyesrobot)"."""
hearteyesrobot = LazyFileImage("hearteyesrobot.gif")

"""Skype emoticon "Green heart (heartgreen)"."""
heartgreen = LazyFileImage("heartgreen.gif")

"""Skype emoticon "Heart Hands (hearthands)"."""
hearthands = LazyFileImage("hearthands.gif")

"""Skype emoticon "Pride heart (heartpride)"."""
heartpride = LazyFileImage("heartpride.gif")

"""Skype emoticon "Purple heart (heartpurple)"."""
heartpurple = LazyFileImage("heartpurple.gif")

"""Skype emoticon "Yellow heart (heartyellow)"."""
heartyellow = LazyFileImage("heartyellow.gif")

"""Skype emoticon "Hedgehog (hedgehog)"."""
hedgehog = LazyFileImage("hedgehog.gif")

"""Skype emoticon "Hedgehog hug (hedgehoghug)"."""
hedgehoghug = LazyFileImage("hedgehoghug.gif")

"""Skype emoticon "Squirrel (heidy)"."""
heidy = LazyFileImage("heidy.gif")

"""Skype emoticon "Dancing Hen (hendance)"."""
hendance = LazyFileImage("hendance.gif")

"""Skype emoticon "Hi (hi)"."""
hi = LazyFileImage("0128-hi.gif")

"""Skype emoticon "High five (h5)"."""
highfive = LazyFileImage("highfive.gif")

"""Skype emoticon "Hold on (w8)"."""
holdon = LazyFileImage("holdon.gif")

"""Skype emoticon "Holi (holi)"."""
holi = LazyFileImage("holi.gif")

"""Skype emoticon "Holiday ready (holidayready)"."""
holidayready = LazyFileImage("holidayready.gif")

"""Skype emoticon "Holiday spirit (holidayspirit)"."""
holidayspirit = LazyFileImage("holidayspirit.gif")

"""Skype emoticon "Hot chocolate (hotchocolate)"."""
hotchocolate = LazyFileImage("hotchocolate.gif")

"""Skype emoticon "House (house)"."""
house = LazyFileImage("house.gif")

"""Skype emoticon "Hug (hug)"."""
hug = LazyFileImage("0134-bear.gif")

"""Skype emoticon "Morning after party (morningafter)"."""
hungover = LazyFileImage("hungover.gif")

"""Skype emoticon "Hungry cat (hungrycat)"."""
hungrycat = LazyFileImage("hungrycat.gif")

"""Skype emoticon "Hysterical (hysterical)"."""
hysterical = LazyFileImage("hysterical.gif")

"""Skype emoticon "Ice cream (icecream)"."""
icecream = LazyFileImage("icecream.gif")

"""Skype emoticon "Idea :i"."""
idea = LazyFileImage("idea.gif")

"""Skype emoticon "I heart You (iheartu)"."""
iheartu = LazyFileImage("iheartu.gif")

"""Skype emoticon "Ill (ill)"."""
ill = LazyFileImage("ill.gif")

"""Skype emoticon "In love :]"."""
inlove = LazyFileImage("0115-inlove.gif")

"""Skype emoticon "Island (island)"."""
island = LazyFileImage("island.gif")

"""Skype emoticon "Sorry (kaanpakadna)"."""
kaanpakadna = LazyFileImage("kaanpakadna.gif")

"""Skype emoticon "Key (key)"."""
key = LazyFileImage("key.gif")

"""Skype emoticon "Kiss :*"."""
kiss = LazyFileImage("0109-kiss.gif")

"""Skype emoticon "Koala (koala)"."""
koala = LazyFileImage("koala.gif")

"""Skype emoticon "What?! (kya)"."""
kya = LazyFileImage("kya.gif")

"""Skype emoticon "L3-37 (l3-37)"."""
l337 = LazyFileImage("l337.gif")

"""Skype emoticon "Lacrosse (lacrosse)"."""
lacrosse = LazyFileImage("lacrosse.gif")

"""Skype emoticon "Sweet (laddu)"."""
laddu = LazyFileImage("laddu.gif")

"""Skype emoticon "Lady Vampire (ladyvamp)"."""
ladyvampire = LazyFileImage("ladyvampire.gif")

"""Skype emoticon "Not listening (lala)"."""
lalala = LazyFileImage("lalala.gif")

"""Skype emoticon "Spring Lamb (lamb)"."""
lamb = LazyFileImage("lamb.gif")

"""Skype emoticon "Lang (lang)"."""
lang = LazyFileImage("lang.gif")

"""Skype emoticon "Laugh :D"."""
laugh = LazyFileImage("0102-bigsmile.gif")

"""Skype emoticon "Laugh cat (laughcat)"."""
laughcat = LazyFileImage("laughcat.gif")

"""Skype emoticon "Laugh dog (laughdog)"."""
laughdog = LazyFileImage("laughdog.gif")

"""Skype emoticon "Laugh koala (laughkoala)"."""
laughkoala = LazyFileImage("laughkoala.gif")

"""Skype emoticon "Laugh monkey (laughmonkey)"."""
laughmonkey = LazyFileImage("laughmonkey.gif")

"""Skype emoticon "Laugh robot (laughrobot)"."""
laughrobot = LazyFileImage("laughrobot.gif")

"""Skype emoticon "Rocket launch (launch)"."""
launch = LazyFileImage("launch.gif")

"""Skype emoticon "Global learning (learn)"."""
learn = LazyFileImage("learn.gif")

"""Skype emoticon "Lemon (lemon)"."""
lemon = LazyFileImage("lemon.gif")

"""Skype emoticon "Let's meet (s+)"."""
letsmeet = LazyFileImage("letsmeet.gif")

"""Skype emoticon "Like (like)"."""
like = LazyFileImage("like.gif")

"""Skype emoticon "Lips (lips)"."""
lips = LazyFileImage("lips.gif")

"""Skype emoticon "My lips are sealed :x"."""
lipssealed = LazyFileImage("0127-lipssealed.gif")

"""Skype emoticon "Listening (listening)"."""
listening = LazyFileImage("listening.gif")

"""Skype emoticon "Lizard (lizard)"."""
lizard = LazyFileImage("lizard.gif")

"""Skype emoticon "Spoiler Alert (llsshock)"."""
llsshock = LazyFileImage("llsshock.gif")

"""Skype emoticon "Lobster (lobster)"."""
lobster = LazyFileImage("lobster.gif")

"""Skype emoticon "Loudly crying (loudlycrying)"."""
loudlycrying = LazyFileImage("loudlycrying.gif")

"""Skype emoticon "Love bites (lovebites)"."""
lovebites = LazyFileImage("lovebites.gif")

"""Skype emoticon "Love Earth (loveearth)"."""
loveearth = LazyFileImage("loveearth.gif")

"""Skype emoticon "Love Gift (lovegift)"."""
lovegift = LazyFileImage("lovegift.gif")

"""Skype emoticon "Love letter (loveletter)"."""
loveletter = LazyFileImage("loveletter.gif")

"""Skype emoticon "You have mail (e)"."""
mail = LazyFileImage("0154-mail.gif")

"""Skype emoticon "Make-up (makeup)"."""
makeup = LazyFileImage("0135-makeup.gif")

"""Skype emoticon "Man (z)"."""
man = LazyFileImage("man.gif")

"""Skype emoticon "Man man heart (manmanheart)"."""
manmanheart = LazyFileImage("manmanheart.gif")

"""Skype emoticon "Man man holding hands (manmanholdinghands)"."""
manmanholdinghands = LazyFileImage("manmanholdinghands.gif")

"""Skype emoticon "Man man kiss (manmankiss)"."""
manmankiss = LazyFileImage("manmankiss.gif")

"""Skype emoticon "Male woman heart (manwomanheart)"."""
manwomanheart = LazyFileImage("manwomanheart.gif")

"""Skype emoticon "Man woman holding hands (manwomanholdinghands)"."""
manwomanholdinghands = LazyFileImage("manwomanholdinghands.gif")

"""Skype emoticon "Man woman kiss (manwomankiss)"."""
manwomankiss = LazyFileImage("manwomankiss.gif")

"""Skype emoticon "Mariachi Love (mariachilove)"."""
mariachilove = LazyFileImage("mariachilove.gif")

"""Skype emoticon "Skiing toy (matreshka)"."""
matreshka = LazyFileImage("matreshka.gif")

"""Skype emoticon "Music bear (mishka)"."""
mishka = LazyFileImage("mishka.gif")

"""Skype emoticon "Mistletoe (mistletoe)"."""
mistletoe = LazyFileImage("mistletoe.gif")

"""Skype emoticon "Mmmmm... (mm)"."""
mmm = LazyFileImage("0125-mmm.gif")

"""Skype emoticon "Monkey (monkey)"."""
monkey = LazyFileImage("monkey.gif")

"""Skype emoticon "Monkey Giggle (monkeygiggle)"."""
monkeygiggle = LazyFileImage("monkeygiggle.gif")

"""Skype emoticon "Mooning (mooning)"."""
mooning = LazyFileImage("0172-mooning.gif")

"""Skype emoticon "Motorbike (motorbike)"."""
motorbike = LazyFileImage("motorbike.gif")

"""Skype emoticon "Movember (movember)"."""
movember = LazyFileImage("movember.gif")

"""Skype emoticon "Movie (~)"."""
movie = LazyFileImage("0160-movie.gif")

"""Skype emoticon "Moving Home (movinghome)"."""
movinghome = LazyFileImage("movinghome.gif")

"""Skype emoticon "Mum and daughter (mumanddaughter)"."""
mumanddaughter = LazyFileImage("mumanddaughter.gif")

"""Skype emoticon "Mum heart (mumheart)"."""
mumheart = LazyFileImage("mumheart.gif")

"""Skype emoticon "Hammer Mummy (mummy)"."""
mummy = LazyFileImage("mummy.gif")

"""Skype emoticon "Mummy Walk (mummywalk)"."""
mummywalk = LazyFileImage("mummywalk.gif")

"""Skype emoticon "Muscle (flex)"."""
muscle = LazyFileImage("0165-muscle.gif")

"""Skype emoticon "Muscle and fat guy (muscleman)"."""
muscleman = LazyFileImage("muscleman.gif")

"""Skype emoticon "Music (music)"."""
music = LazyFileImage("0159-music.gif")

"""Skype emoticon "No! (nahi)"."""
nahi = LazyFileImage("nahi.gif")

"""Skype emoticon "Nature's call (ek)"."""
naturescall = LazyFileImage("naturescall.gif")

"""Skype emoticon "Blessing (nazar)"."""
nazar = LazyFileImage("nazar.gif")

"""Skype emoticon "Nerdy 8|"."""
nerdy = LazyFileImage("0126-nerd.gif")

"""Skype emoticon "Nesting Eggs (nestingeggs)"."""
nestingeggs = LazyFileImage("nestingeggs.gif")

"""Skype emoticon "Ninja (ninja)"."""
ninja = LazyFileImage("0170-ninja.gif")

"""Skype emoticon "No (n)"."""
no = LazyFileImage("0149-no.gif")

"""Skype emoticon "Nodding (nod)"."""
nod = LazyFileImage("0144-nod.gif")

"""Skype emoticon "Noodles (noodles)"."""
noodles = LazyFileImage("noodles.gif")

"""Skype emoticon "Red square (noviygod)"."""
noviygod = LazyFileImage("noviygod.gif")

"""Skype emoticon "No Worries (noworries)"."""
noworries = LazyFileImage("noworries.gif")

"""Skype emoticon "Octopus (octopus)"."""
octopus = LazyFileImage("octopus.gif")

"""Skype emoticon "OK (ok)"."""
ok = LazyFileImage("ok.gif")

"""Skype emoticon "On the loo (ontheloo)"."""
ontheloo = LazyFileImage("ontheloo.gif")

"""Skype emoticon "Orange (orange)"."""
orange = LazyFileImage("orange.gif")

"""Skype emoticon "Orangutan Scratching (orangutanscratch)"."""
orangutanscratching = LazyFileImage("orangutanscratching.gif")

"""Skype emoticon "Orangutan Wave (orangutanwave)"."""
orangutanwave = LazyFileImage("orangutanwave.gif")

"""Skype emoticon "Hey! (oye)"."""
oye = LazyFileImage("oye.gif")

"""Skype emoticon "Palm tree (palmtree)"."""
palmtree = LazyFileImage("palmtree.gif")

"""Skype emoticon "Panda (panda)"."""
panda = LazyFileImage("panda.gif")

"""Skype emoticon "Paris love (parislove)"."""
parislove = LazyFileImage("parislove.gif")

"""Skype emoticon "Party <o)"."""
party = LazyFileImage("0123-party.gif")

"""Skype emoticon "Peach (peach)"."""
peach = LazyFileImage("peach.gif")

"""Skype emoticon "Dancing penguin (penguin)"."""
penguin = LazyFileImage("penguin.gif")

"""Skype emoticon "Penguin Kiss (penguinkiss)"."""
penguinkiss = LazyFileImage("penguinkiss.gif")

"""Skype emoticon "Pensive (pensive)"."""
pensive = LazyFileImage("pensive.gif")

"""Skype emoticon "Phone (mp)"."""
phone = LazyFileImage("0161-phone.gif")

"""Skype emoticon "Pie (pie)"."""
pie = LazyFileImage("pie.gif")

"""Skype emoticon "Silly Pig (pig)"."""
pig = LazyFileImage("pig.gif")

"""Skype emoticon "Piggy Bank (piggybank)"."""
piggybank = LazyFileImage("piggybank.gif")

"""Skype emoticon "Pineapple (pineapple)"."""
pineapple = LazyFileImage("pineapple.gif")

"""Skype emoticon "Pizza (pi)"."""
pizza = LazyFileImage("0163-pizza.gif")

"""Skype emoticon "Plane (jet)"."""
plane = LazyFileImage("plane.gif")

"""Skype emoticon "Backhand Index Pointing Down (pointdownindex)"."""
pointdownindex = LazyFileImage("pointdownindex.gif")

"""Skype emoticon "Backhand Index Pointing Left (pointleftindex)"."""
pointleftindex = LazyFileImage("pointleftindex.gif")

"""Skype emoticon "Backhand Index Pointing Right (pointrightindex)"."""
pointrightindex = LazyFileImage("pointrightindex.gif")

"""Skype emoticon "Index Pointing Up (pointupindex)"."""
pointupindex = LazyFileImage("pointupindex.gif")

"""Skype emoticon "Poke (poke)"."""
poke = LazyFileImage("poke.gif")

"""Skype emoticon "Polar bear (polarbear)"."""
polarbear = LazyFileImage("polarbear.gif")

"""Skype emoticon "Police car (policecar)"."""
policecar = LazyFileImage("policecar.gif")

"""Skype emoticon "Pool party (hrv)"."""
poolparty = LazyFileImage("0182-poolparty.gif")

"""Skype emoticon "Praying (praying)"."""
praying = LazyFileImage("praying.gif")

"""Skype emoticon "Promise (promise)"."""
promise = LazyFileImage("promise.gif")

"""Skype emoticon "Puke :&"."""
puke = LazyFileImage("0119-puke.gif")

"""Skype emoticon "Pull shot (pullshot)"."""
pullshot = LazyFileImage("pullshot.gif")

"""Skype emoticon "Pumpkin (pumpkin)"."""
pumpkin = LazyFileImage("pumpkin.gif")

"""Skype emoticon "Punch *|"."""
punch = LazyFileImage("0146-punch.gif")

"""Skype emoticon "Push bike (pushbike)"."""
pushbike = LazyFileImage("pushbike.gif")

"""Skype emoticon "Racoon (racoon)"."""
racoon = LazyFileImage("racoon.gif")

"""Skype emoticon "Rain (rain)"."""
rain = LazyFileImage("0156-rain.gif")

"""Skype emoticon "Rainbow (r)"."""
rainbow = LazyFileImage("rainbow.gif")

"""Skype emoticon "Rainbow Smile (rainbowsmile)"."""
rainbowsmile = LazyFileImage("rainbowsmile.gif")

"""Skype emoticon "Recycle (recycle)"."""
recycle = LazyFileImage("recycle.gif")

"""Skype emoticon "Angry Red (red)"."""
red = LazyFileImage("red.gif")

"""Skype emoticon "Red wine (redwine)"."""
redwine = LazyFileImage("redwine.gif")

"""Skype emoticon "Reindeer (reindeer)"."""
reindeer = LazyFileImage("reindeer.gif")

"""Skype emoticon "Relieved (relieved)"."""
relieved = LazyFileImage("relieved.gif")

"""Skype emoticon "Black ribbon (ribbonblack)"."""
ribbonblack = LazyFileImage("ribbonblack.gif")

"""Skype emoticon "Blue ribbon (ribbonblue)"."""
ribbonblue = LazyFileImage("ribbonblue.gif")

"""Skype emoticon "Green ribbon (ribbongreen)"."""
ribbongreen = LazyFileImage("ribbongreen.gif")

"""Skype emoticon "Pink ribbon (ribbonpink)"."""
ribbonpink = LazyFileImage("ribbonpink.gif")

"""Skype emoticon "Pride ribbon (ribbonpride)"."""
ribbonpride = LazyFileImage("ribbonpride.gif")

"""Skype emoticon "Red ribbon (ribbonred)"."""
ribbonred = LazyFileImage("ribbonred.gif")

"""Skype emoticon "Yellow ribbon (ribbonyellow)"."""
ribbonyellow = LazyFileImage("ribbonyellow.gif")

"""Skype emoticon "Rickshaw (rickshaw)"."""
rickshaw = LazyFileImage("rickshaw.gif")

"""Skype emoticon "Engagement ring (ring)"."""
ring = LazyFileImage("ring.gif")

"""Skype emoticon "Rock (rock)"."""
rock = LazyFileImage("0178-rock.gif")

"""Skype emoticon "Rock Chick (rockchick)"."""
rockchick = LazyFileImage("rockchick.gif")

"""Skype emoticon "Rolling on the floor laughing (rofl)"."""
rofl = LazyFileImage("0140-rofl.gif")

"""Skype emoticon "Rose (rose)"."""
rose = LazyFileImage("rose.gif")

"""Skype emoticon "Rudolf idea (rudolfidea)"."""
rudolfidea = LazyFileImage("rudolfidea.gif")

"""Skype emoticon "Surprised Rudolf (rudolfsurprise)"."""
rudolfsurprise = LazyFileImage("rudolfsurprise.gif")

"""Skype emoticon "Rugby ball (rugbyball)"."""
rugbyball = LazyFileImage("rugbyball.gif")

"""Skype emoticon "Running (running)"."""
running = LazyFileImage("running.gif")

"""Skype emoticon "Sad :("."""
sad = LazyFileImage("0101-sadsmile.gif")

"""Skype emoticon "Sad cat (sadcat)"."""
sadcat = LazyFileImage("sadcat.gif")

"""Skype emoticon "Sad dog (saddog)"."""
saddog = LazyFileImage("saddog.gif")

"""Skype emoticon "Sad koala (sadkoala)"."""
sadkoala = LazyFileImage("sadkoala.gif")

"""Skype emoticon "Sad monkey (sadmonkey)"."""
sadmonkey = LazyFileImage("sadmonkey.gif")

"""Skype emoticon "Sadness (sadness)"."""
sadness = LazyFileImage("sadness.gif")

"""Skype emoticon "Sad robot (sadrobot)"."""
sadrobot = LazyFileImage("sadrobot.gif")

"""Skype emoticon "Sailboat (sailboat)"."""
sailboat = LazyFileImage("sailboat.gif")

"""Skype emoticon "Sandcastle (sandcastle)"."""
sandcastle = LazyFileImage("sandcastle.gif")

"""Skype emoticon "Santa (santa)"."""
santa = LazyFileImage("santa.gif")

"""Skype emoticon "Santa mooning (santamooning)"."""
santamooning = LazyFileImage("santamooning.gif")

"""Skype emoticon "Sarcastic (sarcastic)"."""
sarcastic = LazyFileImage("sarcastic.gif")

"""Skype emoticon "Scooter (scooter)"."""
scooter = LazyFileImage("scooter.gif")

"""Skype emoticon "Screaming with fear (screamingfear)"."""
screamingfear = LazyFileImage("screamingfear.gif")

"""Skype emoticon "Seal (seal)"."""
seal = LazyFileImage("seal.gif")

"""Skype emoticon "Seedling (seedling)"."""
seedling = LazyFileImage("seedling.gif")

"""Skype emoticon "Monkey see no evil (seenoevil)"."""
seenoevil = LazyFileImage("seenoevil.gif")

"""Skype emoticon "Selfie (selfie)"."""
selfie = LazyFileImage("selfie.gif")

"""Skype emoticon "Selfie Diwali (selfiediwali)"."""
selfiediwali = LazyFileImage("selfiediwali.gif")

"""Skype emoticon "Shake (shake)"."""
shake = LazyFileImage("0145-shake.gif")

"""Skype emoticon "Shark (shark)"."""
shark = LazyFileImage("shark.gif")

"""Skype emoticon "Sheep (sheep)"."""
sheep = LazyFileImage("sheep.gif")

"""Skype emoticon "Cold shivering (shivering)"."""
shivering = LazyFileImage("shivering.gif")

"""Skype emoticon "Spoiler Alert (shock)"."""
shock = LazyFileImage("shock.gif")

"""Skype emoticon "Girl shopping (shopping)"."""
shopping = LazyFileImage("shopping.gif")

"""Skype emoticon "Shrimp (shrimp)"."""
shrimp = LazyFileImage("shrimp.gif")

"""Skype emoticon "Silver medal (silvermedal)"."""
silvermedal = LazyFileImage("silvermedal.gif")

"""Skype emoticon "Skate (skate)"."""
skate = LazyFileImage("skate.gif")

"""Skype emoticon "Keep Fit (skip)"."""
skip = LazyFileImage("skip.gif")

"""Skype emoticon "Skipping (skipping)"."""
skipping = LazyFileImage("skipping.gif")

"""Skype emoticon "Skull (skull)"."""
skull = LazyFileImage("skull.gif")

"""Skype emoticon "Skype (ss)"."""
skype = LazyFileImage("0151-skype.gif")

"""Skype emoticon "Basketball (slamdunk)"."""
slamdunk = LazyFileImage("slamdunk.gif")

"""Skype emoticon "Slap (slap)"."""
slap = LazyFileImage("slap.gif")

"""Skype emoticon "Snooze I-)"."""
sleepy = LazyFileImage("0113-sleepy.gif")

"""Skype emoticon "Sloth (sloth)"."""
sloth = LazyFileImage("sloth.gif")

"""Skype emoticon "Smile :)"."""
smile = LazyFileImage("0100-smile.gif")

"""Skype emoticon "Smile baby (smilebaby)"."""
smilebaby = LazyFileImage("smilebaby.gif")

"""Skype emoticon "Smile boy (smileboy)"."""
smileboy = LazyFileImage("smileboy.gif")

"""Skype emoticon "Smile cat (smilecat)"."""
smilecat = LazyFileImage("smilecat.gif")

"""Skype emoticon "Smile dog (smiledog)"."""
smiledog = LazyFileImage("smiledog.gif")

"""Skype emoticon "Smile eyes (smileeyes)"."""
smileeyes = LazyFileImage("smileeyes.gif")

"""Skype emoticon "Smile girl (smilegirl)"."""
smilegirl = LazyFileImage("smilegirl.gif")

"""Skype emoticon "Smile koala (smilekoala)"."""
smilekoala = LazyFileImage("smilekoala.gif")

"""Skype emoticon "Smile man (smileman)"."""
smileman = LazyFileImage("smileman.gif")

"""Skype emoticon "Smile monkey (smilemonkey)"."""
smilemonkey = LazyFileImage("smilemonkey.gif")

"""Skype emoticon "Smile robot (smilerobot)"."""
smilerobot = LazyFileImage("smilerobot.gif")

"""Skype emoticon "Smile woman (smilewoman)"."""
smilewoman = LazyFileImage("smilewoman.gif")

"""Skype emoticon "Smirking (smirk)"."""
smirk = LazyFileImage("0143-smirk.gif")

"""Skype emoticon "Smoking (ci)"."""
smoke = LazyFileImage("0176-smoke.gif")

"""Skype emoticon "Snail (snail)"."""
snail = LazyFileImage("snail.gif")

"""Skype emoticon "Snake (snake)"."""
snake = LazyFileImage("snake.gif")

"""Skype emoticon "Snow buddie (snegovik)"."""
snegovik = LazyFileImage("snegovik.gif")

"""Skype emoticon "Snorkler (snorkler)"."""
snorkler = LazyFileImage("snorkler.gif")

"""Skype emoticon "Snow angel (snowangel)"."""
snowangel = LazyFileImage("snowangel.gif")

"""Skype emoticon "Snowflake (snowflake)"."""
snowflake = LazyFileImage("snowflake.gif")

"""Skype emoticon "Soccer ball (soccerball)"."""
soccerball = LazyFileImage("soccerball.gif")

"""Skype emoticon "Sparkler (sparkler)"."""
sparkler = LazyFileImage("sparkler.gif")

"""Skype emoticon "Sparkling heart (sparklingheart)"."""
sparklingheart = LazyFileImage("sparklingheart.gif")

"""Skype emoticon "Monkey speak no evil (speaknoevil)"."""
speaknoevil = LazyFileImage("speaknoevil.gif")

"""Skype emoticon "Speech bubble (speechbubble)"."""
speechbubble = LazyFileImage("speechbubble.gif")

"""Skype emoticon "Speechless :|"."""
speechless = LazyFileImage("0108-speechless.gif")

"""Skype emoticon "Spider (spider)"."""
spider = LazyFileImage("spider.gif")

"""Skype emoticon "Squid (squid)"."""
squid = LazyFileImage("squid.gif")

"""Skype emoticon "Star (*)"."""
star = LazyFileImage("0171-star.gif")

"""Skype emoticon "Star eyes (stareyes)"."""
stareyes = LazyFileImage("stareyes.gif")

"""Skype emoticon "Statue of Liberty (statueofliberty)"."""
statueofliberty = LazyFileImage("statueofliberty.gif")

"""Skype emoticon "Steam train (steamtrain)"."""
steamtrain = LazyFileImage("steamtrain.gif")

"""Skype emoticon "Stingray (stingray)"."""
stingray = LazyFileImage("stingray.gif")

"""Skype emoticon "Stop (!)"."""
stop = LazyFileImage("stop.gif")

"""Skype emoticon "Strawberry (strawberry)"."""
strawberry = LazyFileImage("strawberry.gif")

"""Skype emoticon "Sun (sun)"."""
sun = LazyFileImage("0157-sun.gif")

"""Skype emoticon "Sunflower (sunflower)"."""
sunflower = LazyFileImage("sunflower.gif")

"""Skype emoticon "Sunrise (sunrise)"."""
sunrise = LazyFileImage("sunrise.gif")

"""Skype emoticon "Surprised :O"."""
surprised = LazyFileImage("0104-surprised.gif")

"""Skype emoticon "Swearing (swear)"."""
swear = LazyFileImage("0183-swear.gif")

"""Skype emoticon "Sweating (:|"."""
sweat = LazyFileImage("0107-sweating.gif")

"""Skype emoticon "Sweat grinning (sweatgrinning)"."""
sweatgrinning = LazyFileImage("sweatgrinning.gif")

"""Skype emoticon "Syne (syne)"."""
syne = LazyFileImage("syne.gif")

"""Skype emoticon "Talking (talk)"."""
talk = LazyFileImage("0117-talking.gif")

"""Skype emoticon "Talk to the hand (talktothehand)"."""
talktothehand = LazyFileImage("talktothehand.gif")

"""Skype emoticon "Tandoori chicken (tandoori)"."""
tandoorichicken = LazyFileImage("tandoorichicken.gif")

"""Skype emoticon "Archery (target)"."""
target = LazyFileImage("target.gif")

"""Skype emoticon "Taxi (taxi)"."""
taxi = LazyFileImage("taxi.gif")

"""Skype emoticon "Tennis ball (tennisball)"."""
tennisball = LazyFileImage("tennisball.gif")

"""Skype emoticon "Tennis fail (tennisfail)"."""
tennisfail = LazyFileImage("tennisfail.gif")

"""Skype emoticon "Thanks (thanks)"."""
thanks = LazyFileImage("thanks.gif")

"""Skype emoticon "Thinking :?"."""
think = LazyFileImage("0138-thinking.gif")

"""Skype emoticon "Time (o)"."""
time = LazyFileImage("0158-time.gif")

"""Skype emoticon "Tired (tired)"."""
tired = LazyFileImage("tired.gif")

"""Skype emoticon "Too much information (tmi)"."""
tmi = LazyFileImage("0184-tmi.gif")

"""Skype emoticon "Toivo (toivo)"."""
toivo = LazyFileImage("0177-toivo.gif")

"""Skype emoticon "Tongue sticking out :P"."""
tongueout = LazyFileImage("0110-tongueout.gif")

"""Skype emoticon "Tortoise (tortoise)"."""
tortoise = LazyFileImage("tortoise.gif")

"""Skype emoticon "Trophy (trophy)"."""
trophy = LazyFileImage("trophy.gif")

"""Skype emoticon "Truck (truck)"."""
truck = LazyFileImage("truck.gif")

"""Skype emoticon "Talking too much (ttm)"."""
ttm = LazyFileImage("ttm.gif")

"""Skype emoticon "Tubelight (tubelight)"."""
tubelight = LazyFileImage("tubelight.gif")

"""Skype emoticon "Tulip (tulip)"."""
tulip = LazyFileImage("tulip.gif")

"""Skype emoticon "Tumbleweed (tumbleweed)"."""
tumbleweed = LazyFileImage("tumbleweed.gif")

"""Skype emoticon "Dancing Thanksgiving turkey (turkey)"."""
turkey = LazyFileImage("turkey.gif")

"""Skype emoticon "Turtle (turtle)"."""
turtle = LazyFileImage("turtle.gif")

"""Skype emoticon "TV binge Zombie (tvbinge)"."""
tvbinge = LazyFileImage("tvbinge.gif")

"""Skype emoticon "Two hearts (twohearts)"."""
twohearts = LazyFileImage("twohearts.gif")

"""Skype emoticon "Umbrella (um)"."""
umbrella = LazyFileImage("umbrella.gif")

"""Skype emoticon "Umbrella on ground (umbrellaonground)"."""
umbrellaonground = LazyFileImage("umbrellaonground.gif")

"""Skype emoticon "Unamused (unamused)"."""
unamused = LazyFileImage("unamused.gif")

"""Skype emoticon "Unicorn (unicorn)"."""
unicorn = LazyFileImage("unicorn.gif")

"""Skype emoticon "Unicorn head (unicornhead)"."""
unicornhead = LazyFileImage("unicornhead.gif")

"""Skype emoticon "Can't unsee that (unsee)"."""
unsee = LazyFileImage("unsee.gif")

"""Skype emoticon "Upside down face (upsidedownface)"."""
upsidedownface = LazyFileImage("upsidedownface.gif")

"""Skype emoticon "Vampire (vampire)"."""
vampire = LazyFileImage("vampire.gif")

"""Skype emoticon "Very confused (veryconfused)"."""
veryconfused = LazyFileImage("veryconfused.gif")

"""Skype emoticon "Victory (victory)"."""
victory = LazyFileImage("victory.gif")

"""Skype emoticon "Vulcan salute (vulcansalute)"."""
vulcansalute = LazyFileImage("vulcansalute.gif")

"""Skype emoticon "Wait (wait)"."""
wait = LazyFileImage("0133-wait.gif")

"""Skype emoticon "Waiting (waiting)"."""
waiting = LazyFileImage("waiting.gif")

"""Skype emoticon "It wasn't me! (wm)"."""
wasntme = LazyFileImage("0122-itwasntme.gif")

"""Skype emoticon "Watermelon (watermelon)"."""
watermelon = LazyFileImage("watermelon.gif")

"""Skype emoticon "Water wave (waterwave)"."""
waterwave = LazyFileImage("waterwave.gif")

"""Skype emoticon "Weary (weary)"."""
weary = LazyFileImage("weary.gif")

"""Skype emoticon "Web Heart (webheart)"."""
webheart = LazyFileImage("webheart.gif")

"""Skype emoticon "Working from home (@h)"."""
wfh = LazyFileImage("wfh.gif")

"""Skype emoticon "Whale (whale)"."""
whale = LazyFileImage("whale.gif")

"""Skype emoticon "What's going on? (!!?)"."""
whatsgoingon = LazyFileImage("whatsgoingon.gif")

"""Skype emoticon "Relieved (whew)"."""
whew = LazyFileImage("0141-whew.gif")

"""Skype emoticon "Whistle (whistle)"."""
whistle = LazyFileImage("whistle.gif")

"""Skype emoticon "Wilted flower (wiltedflower)"."""
wiltedflower = LazyFileImage("wiltedflower.gif")

"""Skype emoticon "Wind Turbine (windturbine)"."""
windturbine = LazyFileImage("windturbine.gif")

"""Skype emoticon "Wink ;)"."""
wink = LazyFileImage("0105-wink.gif")

"""Skype emoticon "Winking tongue out ;p"."""
winktongueout = LazyFileImage("winktongueout.gif")

"""Skype emoticon "Podium (winner)"."""
winner = LazyFileImage("winner.gif")

"""Skype emoticon "Witch (witch)"."""
witch = LazyFileImage("witch.gif")

"""Skype emoticon "Woman (x)"."""
woman = LazyFileImage("woman.gif")

"""Skype emoticon "Woman woman heart (womanwomanheart)"."""
womanwomanheart = LazyFileImage("womanwomanheart.gif")

"""Skype emoticon "Woman woman holding hands (womanwomanholdinghands)"."""
womanwomanholdinghands = LazyFileImage("womanwomanholdinghands.gif")

"""Skype emoticon "Woman woman kiss (womanwomankiss)"."""
womanwomankiss = LazyFileImage("womanwomankiss.gif")

"""Skype emoticon "Wondering :^)"."""
wonder = LazyFileImage("0112-wondering.gif")

"""Skype emoticon "Worried :s"."""
worry = LazyFileImage("0124-worried.gif")

"""Skype emoticon "Woman of the year (woty)"."""
woty = LazyFileImage("woty.gif")

"""Skype emoticon "What the... (wtf)"."""
wtf = LazyFileImage("wtf.gif")

"""Skype emoticon "XD smiley (xd)"."""
xd = LazyFileImage("xd.gif")

"""Skype emoticon "Xmas car (xmascar)"."""
xmascar = LazyFileImage("xmascar.gif")

"""Skype emoticon "Xmas cry (xmascry)"."""
xmascry = LazyFileImage("xmascry.gif")

"""Skype emoticon "Xmas crying with laughter (xmascwl)"."""
xmascwl = LazyFileImage("xmascwl.gif")

"""Skype emoticon "Xmas heart (xmasheart)"."""
xmasheart = LazyFileImage("xmasheart.gif")

"""Skype emoticon "Xmas sarcastic (xmassarcastic)"."""
xmassarcastic = LazyFileImage("xmassarcastic.gif")

"""Skype emoticon "Xmas tree (xmastree)"."""
xmastree = LazyFileImage("xmastree.gif")

"""Skype emoticon "Xmas yes (xmasyes)"."""
xmasyes = LazyFileImage("xmasyes.gif")

"""Skype emoticon "Yawn (yawn)"."""
yawn = LazyFileImage("0118-yawn.gif")

"""Skype emoticon "Yes (y)"."""
yes = LazyFileImage("0148-yes.gif")

"""Skype emoticon "Yoga (yoga)"."""
yoga = LazyFileImage("yoga.gif")

"""Skype emoticon "Zombie (zombie)"."""
zombie = LazyFileImage("zombie.gif")

"""Skype emoticon "Hammer Zombie (zombiedrool)"."""
zombiedrool = LazyFileImage("zombiedrool.gif")

"""Skype emoticon "Zombie Wave (zombiewave)"."""
zombiewave = LazyFileImage("zombiewave.gif")


"""Emoticon metadata: name, strings, title."""
EmoticonData = {
    "abe": {"strings": ["(abe)", "(Abe)", "(abey)", "(Abey)"], "title": "Hey, you!"},
    "acorn": {"strings": ["(acorn)", "(Acorn)"], "title": "Acorn"},
    "ambulance": {"strings": ["(ambulance)", "(Ambulance)"], "title": "Ambulance"},
    "americanfootball": {"strings": ["(americanfootball)", "(Americanfootball)", "(americanfootballbounce)", "(americanfootballeyes)"], "title": "American Football"},
    "angel": {"strings": ["(a)", "(angel)", "(A)", "(Angel)"], "title": "Angel"},
    "anger": {"strings": ["(anger)", "(Anger)"], "title": "Anger"},
    "angry": {"strings": [":@", "(angry)", ":-@", ":=@", "x(", "x-(", "X(", "X-(", "x=(", "X=(", ";@", ";-@", "(Angry)"], "title": "Angry"},
    "angryface": {"strings": ["(angryface)"], "title": "Angry Face"},
    "apple": {"strings": ["(apple)", "(Apple)"], "title": "Apple"},
    "aubergine": {"strings": ["(aubergine)", "(Aubergine)", "(eggplant)", "(Eggplant)"], "title": "Eggplant"},
    "auld": {"strings": ["(auld)", "(Auld)"], "title": "Auld"},
    "avocadolove": {"strings": ["(avocadolove)", "(Avocadolove)"], "title": "Avocado Love"},
    "banana": {"strings": ["(banana)", "(Banana)"], "title": "Banana"},
    "bandit": {"strings": ["(bandit)", "(Bandit)"], "title": "Bandit"},
    "bartlett": {"strings": ["(football)", "(Football)", "(bartlett)", "(Bartlett)", "(so)", "(So)", "(soccer)", "(Soccer)"], "title": "Soccer"},
    "baseball": {"strings": ["(baseball)"], "title": "Baseball"},
    "basketball": {"strings": ["(basketball)"], "title": "Basketball"},
    "bee": {"strings": ["(bee)", "(Bee)"], "title": "Bee"},
    "beer": {"strings": ["(beer)", "(bricklayers)", "(B)", "(b)", "(Beer)", "(Bricklayers)"], "title": "Beer"},
    "bell": {"strings": ["(bell)", "(Bell)", "(ghanta)", "(Ghanta)"], "title": "Bell"},
    "bhangra": {"strings": ["(bhangra)", "(Bhangra)"], "title": "Bhangra"},
    "bike": {"strings": ["(bike)", "(bicycle)", "(sander)", "(Bike)", "(Bicycle)", "(Sander)"], "title": "Bicycle"},
    "blankface": {"strings": ["(blankface)"], "title": "Face without mouth"},
    "blush": {"strings": [":$", ":-$", ":=$", ":\">", "(blush)", "(Blush)"], "title": "Blushing"},
    "bollylove": {"strings": ["(bollylove)", "(Bollylove)"], "title": "In love pose"},
    "bomb": {"strings": ["(bomb)", "(explosion)", "(explode)", "@=", "(Bomb)", "(Explosion)", "(Explode)"], "title": "Bomb"},
    "bottlefeeding": {"strings": ["(bottlefeeding)", "(Bottlefeeding)"], "title": "Bottle feeding"},
    "bow": {"strings": ["(bow)", "(Bow)"], "title": "Bowing"},
    "bowled": {"strings": ["(bowled)", "(Bowled)", "(out)", "(Out)", "(wicket)", "(Wicket)"], "title": "Bowled"},
    "bowlingball": {"strings": ["(bowlingball)"], "title": "Bowling ball"},
    "brb": {"strings": ["(brb)", "(berightback)", "(Brb)", "(Berightback)"], "title": "Be Right Back"},
    "breakfastinbed": {"strings": ["(breakfastinbed)", "(Breakfastinbed)"], "title": "Breakfast in bed"},
    "breastfeeding": {"strings": ["(breastfeeding)", "(Breastfeeding)"], "title": "Breastfeeding"},
    "brokenheart": {"strings": ["(u)", "(U)", "(brokenheart)", "(Brokenheart)"], "title": "Broken heart"},
    "brokenheartblack": {"strings": ["(brokenheartblack)", "(blackbrokenheart)"], "title": "Black broken heart"},
    "brokenheartblue": {"strings": ["(brokenheartblue)", "(bluebrokenheart)"], "title": "Blue broken heart"},
    "brokenheartgreen": {"strings": ["(brokenheartgreen)", "(greenbrokenheart)"], "title": "Green broken heart"},
    "brokenheartpurple": {"strings": ["(brokenheartpurple)", "(purplebrokenheart)"], "title": "Purple broken heart"},
    "brokenheartyellow": {"strings": ["(brokenheartyellow)", "(yellowbrokenheart)"], "title": "Yellow broken heart"},
    "bronzemedal": {"strings": ["(bronzemedal)", "(Bronzemedal)"], "title": "Bronze medal"},
    "bug": {"strings": ["(bug)", "(Bug)"], "title": "Bug"},
    "bunny": {"strings": ["(bunny)", "(Bunny)", "(lovebunny)", "(Lovebunny)", "(rabbit)", "(Rabbit)"], "title": "Bunny"},
    "bunnyhug": {"strings": ["(bunnyhug)", "(Bunnyhug)"], "title": "Bunny hug"},
    "burger": {"strings": ["(burger)", "(Burger)"], "title": "Burger"},
    "busyday": {"strings": ["(busyday)", "(Busyday)"], "title": "Busy Day"},
    "butterfly": {"strings": ["(butterfly)"], "title": "Butterfly"},
    "cactuslove": {"strings": ["(cactuslove)", "(Cactuslove)"], "title": "Cactus Love"},
    "cake": {"strings": ["(^)", "(cake)", "(Cake)"], "title": "Cake"},
    "cakeslice": {"strings": ["(cakeslice)", "(Cakeslice)"], "title": "Cake slice"},
    "cakethrow": {"strings": ["(cakethrow)", "(Cakethrow)"], "title": "Cake Throw"},
    "call": {"strings": ["(call)", "(T)", "(t)", "(Call)"], "title": "Call"},
    "camera": {"strings": ["(p)", "(camera)", "(P)", "(Camera)"], "title": "Camera"},
    "canoe": {"strings": ["(canoe)", "(1f6f6_canoe)"], "title": "Canoe"},
    "canyoutalk": {"strings": ["(!!)", "(canyoutalk)", "(Canyoutalk)"], "title": "Can you talk?"},
    "car": {"strings": ["(car)", "(au)", "(Car)", "(Au)"], "title": "Car"},
    "cash": {"strings": ["($)", "(mo)", "(cash)", "(Cash)", "(Mo)"], "title": "Cash"},
    "cat": {"strings": [":3", "(cat)", "(@)", "(meow)", "(Cat)", "(Meow)", "(kitty)", "(Kitty)"], "title": "Cat"},
    "chai": {"strings": ["(chai)", "(Chai)", "(tea)", "(Tea)"], "title": "Tea"},
    "champagne": {"strings": ["(champagne)", "(Champagne)", "(sparkling)", "(Sparkling)"], "title": "Champagne"},
    "chappal": {"strings": ["(chappal)", "(Chappal)", "(slipper)", "(Slipper)"], "title": "Slipper"},
    "cheerleader": {"strings": ["(cheerleader)", "(Cheerleader)"], "title": "Cheerleader"},
    "cheers": {"strings": ["(cheers)", "(Cheers)"], "title": "Cheers!"},
    "cheese": {"strings": ["(cheese)", "(Cheese)", "(stink)", "(Stink)"], "title": "Cheese"},
    "cherries": {"strings": ["(cherries)", "(Cherries)"], "title": "Cherries"},
    "cherryblossom": {"strings": ["(cherryblossom)", "(Cherryblossom)"], "title": "Cherry blossom"},
    "chickenleg": {"strings": ["(chickenleg)", "(Chickenleg)"], "title": "Chicken leg"},
    "chicksegg": {"strings": ["(chicksegg)", "(Chicksegg)"], "title": "Chicks' Egg"},
    "clap": {"strings": ["(clap)", "(Clap)"], "title": "Clapping"},
    "coffee": {"strings": ["(coffee)", "(c)", "(C)", "(Coffee)"], "title": "Coffee"},
    "computer": {"strings": ["(pc)", "(computer)", "(co)", "(Computer)", "(Co)", "(Pc)"], "title": "Computer"},
    "computerrage": {"strings": ["(computerrage)", "(Computerrage)", "(typingrage)", "(Typingrage)"], "title": "Computer rage"},
    "confidential": {"strings": ["(qt)", "(confidential)", "(QT)", "(Qt)", "(Confidential)"], "title": "Confidential"},
    "confused": {"strings": ["(confused)", "(Confused)", ":-/", ":-\\", ":/", ":\\"], "title": "Confused"},
    "cookies": {"strings": ["(cookies)", "(Cookies)"], "title": "Cookies"},
    "cool": {"strings": ["8-)", "8=)", "B-)", "B=)", "(cool)", "(Cool)"], "title": "Cool"},
    "coolcat": {"strings": ["(coolcat)"], "title": "Cool cat"},
    "cooldog": {"strings": ["(cooldog)"], "title": "Cool dog"},
    "coolkoala": {"strings": ["(coolkoala)"], "title": "Cool koala"},
    "coolmonkey": {"strings": ["(coolmonkey)"], "title": "Cool monkey"},
    "coolrobot": {"strings": ["(coolrobot)"], "title": "Cool robot"},
    "crab": {"strings": ["(crab)", "(1f980_crab)"], "title": "Crab"},
    "cricket": {"strings": ["(cricket)", "(Cricket)"], "title": "Cricket"},
    "croissant": {"strings": ["(croissant)"], "title": "Croissant"},
    "cry": {"strings": [";(", ";-(", ";=(", "(cry)", ":'(", "(Cry)"], "title": "Crying"},
    "cupcake": {"strings": ["(cupcake)", "(Cupcake)"], "title": "Cupcake"},
    "cwl": {"strings": ["(cwl)", "(Cwl)", "(cryingwithlaughter)", "(Cryingwithlaughter)"], "title": "Crying with laughter"},
    "dadtime": {"strings": ["(dadtime)", "(Dadtime)"], "title": "Dad Time"},
    "dance": {"strings": ["\\o/", "\\:D/", "\\:d/", "(dance)", "(Dance)"], "title": "Dancing"},
    "deadyes": {"strings": ["(deadyes)", "(Deadyes)"], "title": "Dead Yes"},
    "deciduoustree": {"strings": ["(deciduoustree)", "(treedeciduous)"], "title": "Deciduous Tree"},
    "dedmoroz": {"strings": ["(dedmoroz)", "(Dedmoroz)", "(frostwizard)", "(Frostwizard)"], "title": "Frost wizard"},
    "desert": {"strings": ["(desert)", "(Desert)"], "title": "Desert"},
    "devil": {"strings": ["(devil)", "(6)", "(Devil)"], "title": "Devil"},
    "dhakkan": {"strings": ["(dhakkan)", "(Dhakkan)", "(fool)", "(Fool)"], "title": "Fool"},
    "diamond": {"strings": ["(diamond)"], "title": "Diamond"},
    "disappointed": {"strings": ["(disappointed)", "(Disappointed)"], "title": "Disappointed"},
    "discodancer": {"strings": ["(disco)", "(Disco)", "(discodancer)", "(Discodancer)"], "title": "Disco dancer"},
    "disgust": {"strings": ["(disgust)", "(Disgust)"], "title": "Disgust"},
    "diwaliselfie": {"strings": ["(diwaliselfie)", "(Diwaliselfie)"], "title": "Diwali Selfie"},
    "diya": {"strings": ["(diwali)", "(Diwali)", "(diya)", "(Diya)"], "title": "Tealight"},
    "dog": {"strings": ["(&)", "(dog)", ":o3", "(Dog)"], "title": "Dog"},
    "doh": {"strings": ["(doh)", "(Doh)"], "title": "Doh!"},
    "dolphin": {"strings": ["(dolphin)", "(Dolphin)"], "title": "Dolphin"},
    "donkey": {"strings": ["(donkey)", "(Donkey)", "(gadha)", "(Gadha)"], "title": "Donkey"},
    "donttalktome": {"strings": ["(donttalk)", "(Donttalk)", "(donttalktome)", "(Donttalktote)", "(Donttalktome)"], "title": "Don't talk to me"},
    "dracula": {"strings": ["(dracula)", "(Dracula)"], "title": "Hammer Dracula"},
    "dream": {"strings": ["(dream)", "(Dream)"], "title": "Dreaming"},
    "dreidel": {"strings": ["(dreidel)", "(Dreidel)"], "title": "Dreidel"},
    "drink": {"strings": ["(d)", "(D)", "(drink)", "(Drink)"], "title": "Drink"},
    "dropthemic": {"strings": ["(dropthemic)", "(Dropthemic)"], "title": "Drop the mic"},
    "drunk": {"strings": ["(drunk)", "(Drunk)"], "title": "Drunk"},
    "dull": {"strings": ["|(", "|-(", "|=(", "(dull)", "(Dull)", "|-()"], "title": "Dull"},
    "eg": {"strings": ["]:)", ">:)", "(grin)", "(Grin)", "(evilgrin)", "(Evilgrin)", "(evil)", "(Evil)", "(eg)", "(Eg)"], "title": "Evil grin"},
    "eid": {"strings": ["(eid)", "(Eid)"], "title": "Eid"},
    "eightball": {"strings": ["(eightball)"], "title": "Pool eight ball"},
    "elephant": {"strings": ["(elephant)", "(Elephant)"], "title": "Elephant"},
    "emo": {"strings": ["(emo)", "(Emo)"], "title": "Emo"},
    "envy": {"strings": ["(envy)", "(V)", "(v)", "(Envy)"], "title": "Envy"},
    "evergreentree": {"strings": ["(evergreentree)", "(treeevergreen)"], "title": "Evergreen Tree"},
    "expressionless": {"strings": ["(expressionless)", "(Expressionless)"], "title": "Expressionless"},
    "facepalm": {"strings": ["(fail)", "(facepalm)", "(Facepalm)", "(Fail)"], "title": "Facepalm"},
    "fallingleaf": {"strings": ["(fallingleaf)", "(Fallingleaf)"], "title": "Falling leaf"},
    "fallinlove": {"strings": ["(fallinlove)", "(Fallinlove)", "(fallinlove)", "(Fallinlove)"], "title": "Falling in love"},
    "family": {"strings": ["(family)", "(Family)"], "title": "Family"},
    "familytime": {"strings": ["(familytime)", "(Familytime)"], "title": "Family Time"},
    "fearful": {"strings": ["(fearful)"], "title": "Fearful"},
    "festiveparty": {"strings": ["(festiveparty)", "(Festiveparty)", "(partyxmas)", "(Partyxmas)"], "title": "Festive party"},
    "finger": {"strings": ["(finger)", "(Finger)"], "title": "Finger"},
    "fingerscrossed": {"strings": ["(yn)", "(fingers)", "(crossedfingers)", "(fingerscrossed)", "(Yn)", "(Fingers)", "(Fingerscrossed)", "(Crossedfingers)"], "title": "Fingers crossed"},
    "fire": {"strings": ["(fire)", "(Fire)"], "title": "Fire"},
    "fireworks": {"strings": ["(fireworks)", "(Fireworks)"], "title": "Fireworks"},
    "fish": {"strings": ["(fish)", "(Fish)", "(tropicalfish)", "(fishtropical)"], "title": "Fish"},
    "fistbump": {"strings": ["(fistbump)", "=\u018eE=", "p#d", "(Fistbump)"], "title": "Good work!"},
    "flaginhole": {"strings": ["(flaginhole)", "(golfball)"], "title": "Flag in hole"},
    "flower": {"strings": ["(f)", "(flower)", "(F)", "(Flower)"], "title": "Flower"},
    "flushed": {"strings": ["(flushed)", "(Flushed)"], "title": "Flushed"},
    "footballfail": {"strings": ["(footballfail)", "(Footballfail)"], "title": "Football fail"},
    "foreverlove": {"strings": ["(foreverlove)", "(Foreverlove)"], "title": "Forever love"},
    "foxhug": {"strings": ["(foxhug)", "(Foxhug)"], "title": "Fox hug"},
    "frankenstein": {"strings": ["(frankenstein)", "(Frankenstein)"], "title": "Hammer Frankenstein"},
    "fries": {"strings": ["(fries)", "(Fries)"], "title": "Fries"},
    "fubar": {"strings": ["(fubar)"], "title": "FUBAR"},
    "games": {"strings": ["(games)", "(ply)", "(PLY)", "(play)", "(Games)", "(Ply)", "(Play)", "(playbox)", "(Playbox)"], "title": "Games"},
    "ganesh": {"strings": ["(ganesh)", "(Ganesh)"], "title": "Ganesh"},
    "ghost": {"strings": ["(ghost)", "(Ghost)"], "title": "Ghost"},
    "gift": {"strings": ["(g)", "(gift)", "(G)", "(Gift)"], "title": "Gift"},
    "giggle": {"strings": ["(giggle)", "(chuckle)", "(Chuckle)", "(Giggle)"], "title": "Giggle"},
    "gingerkeepfit": {"strings": ["(gingerkeepfit)", "(Gingerkeepfit)"], "title": "Ginger keep fit"},
    "glassceiling": {"strings": ["(glassceiling)", "(Glassceiling)"], "title": "Glass ceiling"},
    "goldmedal": {"strings": ["(goldmedal)", "(Goldmedal)"], "title": "Gold medal"},
    "goodluck": {"strings": ["(gl)", "(goodluck)", "(GL)", "(Goodluck)", "(Gl)"], "title": "Goodluck"},
    "gottarun": {"strings": ["(run)", "(gottarun)", "(gtr)", "(GTR)", "(Gottarun)", "(Gtr)", "(Run)"], "title": "Gotta run"},
    "gran": {"strings": ["(gran)", "(Gran)"], "title": "Dancing Gran"},
    "grannyscooter": {"strings": ["(grannyscooter)", "(Grannyscooter)"], "title": "Granny scooter"},
    "grapes": {"strings": ["(grapes)", "(Grapes)"], "title": "Grapes"},
    "greatpear": {"strings": ["(greatpear)", "(Greatpear)"], "title": "Great pear"},
    "growingheart": {"strings": ["(growingheart)"], "title": "Growing heart"},
    "handshake": {"strings": ["(handshake)", "(Handshake)"], "title": "Handshake"},
    "handsinair": {"strings": ["(handsinair)", "(celebrate)", "(celebration)", "(hia)", "(Celebrate)", "(Celebration)", "(Handsinair)", "(Hia)"], "title": "Hands in air"},
    "hanukkah": {"strings": ["(hanukkah)", "(Hanukkah)", "(menorah)"], "title": "Hanukkah"},
    "happy": {"strings": ["(happy)", "(Happy)"], "title": "Happy"},
    "happyeyes": {"strings": ["(happyeyes)"], "title": "Happy eyes"},
    "happyface": {"strings": ["(happyface)"], "title": "Happy face"},
    "headbang": {"strings": ["(headbang)", "(banghead)", "(Headbang)", "(Banghead)"], "title": "Banging head on wall"},
    "headphones": {"strings": ["(headphones)", "(Headphones)"], "title": "Listening to headphones"},
    "hearnoevil": {"strings": ["(hearnoevil)"], "title": "Monkey hear no evil"},
    "heart": {"strings": ["<3", "(heart)", "(h)", "(H)", "(l)", "(L)", "(Heart)"], "title": "Heart"},
    "heartblack": {"strings": ["(heartblack)", "(blackheart)"], "title": "Black heart"},
    "heartblue": {"strings": ["(heartblue)", "(blueheart)"], "title": "Blue heart"},
    "hearteyes": {"strings": ["(hearteyes)", "(Hearteyes)"], "title": "Heart Eyes"},
    "hearteyescat": {"strings": ["(hearteyescat)"], "title": "Heart eyes cat"},
    "hearteyesdog": {"strings": ["(hearteyesdog)"], "title": "Heart eyes dog"},
    "hearteyeskoala": {"strings": ["(hearteyeskoala)"], "title": "Heart eyes koala"},
    "hearteyesmonkey": {"strings": ["(hearteyesmonkey)"], "title": "Heart eyes monkey"},
    "hearteyesrobot": {"strings": ["(hearteyesrobot)"], "title": "Heart eyes robot"},
    "heartgreen": {"strings": ["(heartgreen)", "(greenheart)"], "title": "Green heart"},
    "hearthands": {"strings": ["(hearthands)", "(Hearthands)"], "title": "Heart Hands"},
    "heartpride": {"strings": ["(heartpride)", "(prideheart)"], "title": "Pride heart"},
    "heartpurple": {"strings": ["(heartpurple)", "(purpleheart)"], "title": "Purple heart"},
    "heartyellow": {"strings": ["(heartyellow)", "(yellowheart)"], "title": "Yellow heart"},
    "hedgehog": {"strings": ["(hedgehog)", "(Hedgehog)"], "title": "Hedgehog"},
    "hedgehoghug": {"strings": ["(hedgehoghug)", "(Hedgehoghug)"], "title": "Hedgehog hug"},
    "heidy": {"strings": ["(heidy)", "(squirrel)", "(Heidy)", "(Squirrel)"], "title": "Squirrel"},
    "hendance": {"strings": ["(hendance)", "(Hendance)"], "title": "Dancing Hen"},
    "hi": {"strings": ["(hi)", "(wave)", "(bye)", "(BYE)", "(Bye)", "(Hi)", "(HI)", "(Wave)"], "title": "Hi"},
    "highfive": {"strings": ["(h5)", "(hifive)", "(highfive)", "(Highfive)", "(Hifive)", "(H5)"], "title": "High five"},
    "holdon": {"strings": ["(w8)", "(holdon)", "(W8)", "(Holdon)"], "title": "Hold on"},
    "holi": {"strings": ["(holi)", "(Holi)", "(rang)", "(Rang)"], "title": "Holi"},
    "holidayready": {"strings": ["(holidayready)"], "title": "Holiday ready"},
    "holidayspirit": {"strings": ["(holidayspirit)", "(Holidayspirit)", "(crazyxmas)", "(Crazyxmas)", "(crazychristmas)", "(Crazychristmas)"], "title": "Holiday spirit"},
    "hotchocolate": {"strings": ["(hotchocolate)", "(Hotchocolate)"], "title": "Hot chocolate"},
    "house": {"strings": ["(house)", "(House)", "(home)", "(Home)"], "title": "House"},
    "hug": {"strings": ["(hug)", "(bear)", "(Hug)", "(Bear)"], "title": "Hug"},
    "hungover": {"strings": ["(morningafter)", "(Morningafter)", "(hungover)", "(Hungover)"], "title": "Morning after party"},
    "hungrycat": {"strings": ["(hungrycat)", "(Hungrycat)"], "title": "Hungry cat"},
    "hysterical": {"strings": ["(hysterical)", "(Hysterical)"], "title": "Hysterical"},
    "icecream": {"strings": ["(icecream)", "(Icecream)", "(1f368_icecream)"], "title": "Ice cream"},
    "idea": {"strings": [":i", "(idea)", ":I", "*-:)", "(Idea)"], "title": "Idea"},
    "iheartu": {"strings": ["(iheartu)", "(Iheartu)"], "title": "I heart You"},
    "ill": {"strings": ["(ill)", "(Ill)"], "title": "Ill"},
    "inlove": {"strings": [":]", "(inlove)", "(love)", ":-]", "(Inlove)", "(Love)"], "title": "In love"},
    "island": {"strings": ["(island)", "(ip)", "(Island)", "(Ip)"], "title": "Island"},
    "kaanpakadna": {"strings": ["(kaanpakadna)", "(KaanPakadna)", "(sorry)", "(Sorry)", "(maafi)", "(Maafi)", "(Kaanpakadna)"], "title": "Sorry"},
    "key": {"strings": ["(key)", "(Key)", "(success)", "(Success)"], "title": "Key"},
    "kiss": {"strings": [":*", "(kiss)", ":-*", ":=*", "(xo)", "(K)", "(k)", "(Kiss)"], "title": "Kiss"},
    "koala": {"strings": ["(koala)", "(Koala)"], "title": "Koala"},
    "kya": {"strings": ["(kya)", "(Kya)"], "title": "What?!"},
    "l337": {"strings": ["(l3-37)", "(L3-37)", "(l337)", "(L337)"], "title": "L3-37"},
    "lacrosse": {"strings": ["(lacrosse)"], "title": "Lacrosse"},
    "laddu": {"strings": ["(laddu)", "(Laddu)"], "title": "Sweet"},
    "ladyvampire": {"strings": ["(ladyvamp)", "(Ladyvamp)", "(ladyvampire)", "(Ladyvampire)"], "title": "Lady Vampire"},
    "lalala": {"strings": ["(lala)", "(lalala)", "(lalalala)", "(notlistening)", "(Lalala)", "(Lalalala)", "(Lala)", "(Notlistening)"], "title": "Not listening"},
    "lamb": {"strings": ["(lamb)", "(Lamb)"], "title": "Spring Lamb"},
    "lang": {"strings": ["(lang)", "(Lang)"], "title": "Lang"},
    "laugh": {"strings": [":D", ":-D", ":=D", ":d", ":-d", ":=d", "(laugh)", ":>", ":->", "(lol)", "(LOL)", "(Laugh)", "(Lol)"], "title": "Laugh"},
    "laughcat": {"strings": ["(laughcat)"], "title": "Laugh cat"},
    "laughdog": {"strings": ["(laughdog)"], "title": "Laugh dog"},
    "laughkoala": {"strings": ["(laughkoala)"], "title": "Laugh koala"},
    "laughmonkey": {"strings": ["(laughmonkey)"], "title": "Laugh monkey"},
    "laughrobot": {"strings": ["(laughrobot)"], "title": "Laugh robot"},
    "launch": {"strings": ["(launch)", "(Launch)", "(rocket)", "(Rocket)", "(shuttle)", "(Shuttle)"], "title": "Rocket launch"},
    "learn": {"strings": ["(learn)", "(Learn)"], "title": "Global learning"},
    "lemon": {"strings": ["(lemon)", "(Lemon)"], "title": "Lemon"},
    "letsmeet": {"strings": ["(s+)", "(letsmeet)", "(S+)", "(calendar)", "(Letsmeet)", "(Calendar)"], "title": "Let's meet"},
    "like": {"strings": ["(like)", "(Like)"], "title": "Like"},
    "lips": {"strings": ["(lips)", "(Lips)"], "title": "Lips"},
    "lipssealed": {"strings": [":x", ":-x", ":X", ":-X", ":#", ":-#", ":=x", ":=X", ":=#", "(lipssealed)", "(Lipssealed)"], "title": "My lips are sealed"},
    "listening": {"strings": ["(listening)", "(Listening)"], "title": "Listening"},
    "lizard": {"strings": ["(lizard)"], "title": "Lizard"},
    "llsshock": {"strings": ["(llsshock)", "(Llsshock)"], "title": "Spoiler Alert"},
    "lobster": {"strings": ["(lobster)", "(1f99e_lobster)"], "title": "Lobster"},
    "loudlycrying": {"strings": ["(loudlycrying)", "(Loudlycrying)"], "title": "Loudly crying"},
    "lovebites": {"strings": ["(lovebites)", "(Lovebites)"], "title": "Love bites"},
    "loveearth": {"strings": ["(loveearth)"], "title": "Love Earth"},
    "lovegift": {"strings": ["(lovegift)", "(Lovegift)"], "title": "Love Gift"},
    "loveletter": {"strings": ["(loveletter)", "(Loveletter)"], "title": "Love letter"},
    "mail": {"strings": ["(e)", "(m)", "(mail)", "(E)", "(M)", "(Mail)"], "title": "You have mail"},
    "makeup": {"strings": ["(makeup)", "(kate)", "(Makeup)", "(Kate)"], "title": "Make-up"},
    "man": {"strings": ["(z)", "(man)", "(boy)", "(Z)", "(male)", "(Man)", "(Male)", "(Boy)"], "title": "Man"},
    "manmanheart": {"strings": ["(manmanheart)"], "title": "Man man heart"},
    "manmanholdinghands": {"strings": ["(manmanholdinghands)"], "title": "Man man holding hands"},
    "manmankiss": {"strings": ["(manmankiss)", "(manmankissing)"], "title": "Man man kiss"},
    "manwomanheart": {"strings": ["(manwomanheart)"], "title": "Male woman heart"},
    "manwomanholdinghands": {"strings": ["(manwomanholdinghands)"], "title": "Man woman holding hands"},
    "manwomankiss": {"strings": ["(manwomankiss)"], "title": "Man woman kiss"},
    "mariachilove": {"strings": ["(mariachilove)", "(Mariachilove)"], "title": "Mariachi Love"},
    "matreshka": {"strings": ["(matreshka)", "(Matreshka)", "(skiingtoy)", "(Skiingtoy)"], "title": "Skiing toy"},
    "mishka": {"strings": ["(mishka)", "(Mishka)", "(musicbear)", "(Musicbear)"], "title": "Music bear"},
    "mistletoe": {"strings": ["(mistletoe)", "(Mistletoe)"], "title": "Mistletoe"},
    "mmm": {"strings": ["(mm)", "(mmm)", "(mmmm)", "(Mm)", "(Mmm)", "(Mmmm)"], "title": "Mmmmm..."},
    "monkey": {"strings": ["(monkey)", "(ape)", ":(|)", "(Monkey)", "(Ape)"], "title": "Monkey"},
    "monkeygiggle": {"strings": ["(monkeygiggle)", "(Monkeygiggle)"], "title": "Monkey Giggle"},
    "mooning": {"strings": ["(mooning)", "(Mooning)"], "title": "Mooning"},
    "motorbike": {"strings": ["(motorbike)"], "title": "Motorbike"},
    "movember": {"strings": ["(movember)", "(mo)", "(november)", "(moustache)", "(mustache)", "(bowman)", ":{", "(Movember)", "(Mo)", "(November)", "(Moustache)", "(Mustache)", "(Bowman)"], "title": "Movember"},
    "movie": {"strings": ["(~)", "(film)", "(movie)", "(Film)", "(Movie)"], "title": "Movie"},
    "movinghome": {"strings": ["(movinghome)", "(Movinghome)"], "title": "Moving Home"},
    "mumanddaughter": {"strings": ["(mumanddaughter)", "(Mumanddaughter)", "(womanandgirl)", "(Womanandgirl)"], "title": "Mum and daughter"},
    "mumheart": {"strings": ["(mumheart)", "(Mumheart)", "(momheart)", "(Momheart)"], "title": "Mum heart"},
    "mummy": {"strings": ["(mummy)", "(Mummy)"], "title": "Hammer Mummy"},
    "mummywalk": {"strings": ["(mummywalk)", "(Mummywalk)"], "title": "Mummy Walk"},
    "muscle": {"strings": ["(flex)", "(muscle)", "(Flex)", "(Muscle)"], "title": "Muscle"},
    "muscleman": {"strings": ["(muscleman)", "(Muscleman)", "(fatguy)", "(Fatguy)"], "title": "Muscle and fat guy"},
    "music": {"strings": ["(music)", "(8)", "(Music)"], "title": "Music"},
    "nahi": {"strings": ["(nahi)", "(Nahi)", "(naa)", "(Naa)"], "title": "No!"},
    "naturescall": {"strings": ["(ek)", "(Ek)", "(eK)", "(EK)", "(naturescall)", "(NaturesCall)", "(Naturescall)"], "title": "Nature's call"},
    "nazar": {"strings": ["(nazar)", "(Nazar)"], "title": "Blessing"},
    "nerdy": {"strings": ["8|", "B|", "B-|", "8-|", "B=|", "8=|", "(nerd)", "(Nerd)", "(nerdy)", "(Nerdy)"], "title": "Nerdy"},
    "nestingeggs": {"strings": ["(nestingeggs)", "(Nestingeggs)"], "title": "Nesting Eggs"},
    "ninja": {"strings": ["(ninja)", "(J)", "(j)", "(Ninja)"], "title": "Ninja"},
    "no": {"strings": ["(n)", "(N)", "(no)", "(No)"], "title": "No"},
    "nod": {"strings": ["(nod)", "(Nod)"], "title": "Nodding"},
    "noodles": {"strings": ["(noodles)", "(Noodles)"], "title": "Noodles"},
    "noviygod": {"strings": ["(noviygod)", "(Noviygod)", "(redsquare)", "(Redsquare)"], "title": "Red square"},
    "noworries": {"strings": ["(noworries)", "(Noworries)"], "title": "No Worries"},
    "octopus": {"strings": ["(octopus)", "(Octopus)"], "title": "Octopus"},
    "ok": {"strings": ["(ok)", "(OK)", "(oK)", "(Ok)", "(okay)", "(Okay)"], "title": "OK"},
    "ontheloo": {"strings": ["(ontheloo)", "(Ontheloo)", "(onloo)", "(Onloo)", "(nr2)", "(Nr2)", "(twittering)", "(Twittering)", "(verybusy)", "(Verybusy)"], "title": "On the loo"},
    "orange": {"strings": ["(orange)", "(Orange)"], "title": "Orange"},
    "orangutanscratching": {"strings": ["(orangutanscratch)", "(orangutanscratching)"], "title": "Orangutan Scratching"},
    "orangutanwave": {"strings": ["(orangutanwave)"], "title": "Orangutan Wave"},
    "oye": {"strings": ["(oye)", "(Oye)"], "title": "Hey!"},
    "palmtree": {"strings": ["(palmtree)"], "title": "Palm tree"},
    "panda": {"strings": ["(panda)", "(Panda)"], "title": "Panda"},
    "parislove": {"strings": ["(parislove)", "(Parislove)"], "title": "Paris love"},
    "party": {"strings": ["<o)", "(party)", "<O)", "<:o)", "(Party)"], "title": "Party"},
    "peach": {"strings": ["(peach)", "(Peach)"], "title": "Peach"},
    "penguin": {"strings": ["(penguin)", "(Penguin)", "(dancingpenguin)", "(Dancingpenguin)", "(penguindance)", "(Penguindance)", "(linux)", "(Linux)"], "title": "Dancing penguin"},
    "penguinkiss": {"strings": ["(penguinkiss)", "(Penguinkiss)"], "title": "Penguin Kiss"},
    "pensive": {"strings": ["(pensive)", "(Pensive)"], "title": "Pensive"},
    "phone": {"strings": ["(mp)", "(ph)", "(phone)", "(Mp)", "(Ph)", "(Phone)"], "title": "Phone"},
    "pie": {"strings": ["(pie)", "(Pie)"], "title": "Pie"},
    "pig": {"strings": ["(pig)", "(Pig)"], "title": "Silly Pig"},
    "piggybank": {"strings": ["(piggybank)", "(Piggybank)"], "title": "Piggy Bank"},
    "pineapple": {"strings": ["(pineapple)", "(Pineapple)"], "title": "Pineapple"},
    "pizza": {"strings": ["(pi)", "(pizza)", "(Pi)", "(Pizza)"], "title": "Pizza"},
    "plane": {"strings": ["(jet)", "(plane)", "(ap)", "(airplane)", "(aeroplane)", "(aircraft)", "(Plane)", "(Ap)", "(Airplane)", "(Aeroplane)", "(Aircraft)", "(Jet)"], "title": "Plane"},
    "pointdownindex": {"strings": ["(pointdownindex)", "(pointdownindexfinger)"], "title": "Backhand Index Pointing Down"},
    "pointleftindex": {"strings": ["(pointleftindex)", "(pointleftindexfinger)"], "title": "Backhand Index Pointing Left"},
    "pointrightindex": {"strings": ["(pointrightindex)", "(pointrightindexfinger)"], "title": "Backhand Index Pointing Right"},
    "pointupindex": {"strings": ["(pointupindex)", "(pointupindexfinger)"], "title": "Index Pointing Up"},
    "poke": {"strings": ["(poke)", "(nudge)", "(Poke)", "(Nudge)"], "title": "Poke"},
    "polarbear": {"strings": ["(polarbear)", "(Polarbear)", "(polarbearhug)", "(Polarbearhug)"], "title": "Polar bear"},
    "policecar": {"strings": ["(policecar)", "(Policecar)"], "title": "Police car"},
    "poolparty": {"strings": ["(hrv)", "(poolparty)", "(Poolparty)", "(Hrv)"], "title": "Pool party"},
    "praying": {"strings": ["(praying)", "(pray)", "_/\\_", "(Pray)", "(Praying)", "(namaste)", "(Namaste)"], "title": "Praying"},
    "promise": {"strings": ["(promise)", "(Promise)", "(kasamse)", "(Kasamse)"], "title": "Promise"},
    "puke": {"strings": [":&", "(puke)", ":-&", ":=&", "+o(", "(Puke)"], "title": "Puke"},
    "pullshot": {"strings": ["(pullshot)", "(PullShot)", "(shot)", "(Shot)", "(chauka)", "(Chauka)", "(Pullshot)"], "title": "Pull shot"},
    "pumpkin": {"strings": ["(pumpkin)", "(Pumpkin)", "(halloween)", "(Halloween)"], "title": "Pumpkin"},
    "punch": {"strings": ["*|", "(punch)", "*-|", "(Punch)"], "title": "Punch"},
    "pushbike": {"strings": ["(pushbike)", "(Pushbike)"], "title": "Push bike"},
    "racoon": {"strings": ["(racoon)", "(Racoon)", "(raccoon)"], "title": "Racoon"},
    "rain": {"strings": ["(rain)", "(st)", "(ST)", "(St)", "(london)", "(Rain)", "(London)"], "title": "Rain"},
    "rainbow": {"strings": ["(r)", "(rainbow)", "(R)", "(Rainbow)", "(pride)", "(Pride)"], "title": "Rainbow"},
    "rainbowsmile": {"strings": ["(rainbowsmile)", "(Rainbowsmile)"], "title": "Rainbow Smile"},
    "recycle": {"strings": ["(recycle)"], "title": "Recycle"},
    "red": {"strings": ["(red)", "(Red)"], "title": "Angry Red"},
    "redwine": {"strings": ["(redwine)", "(Redwine)"], "title": "Red wine"},
    "reindeer": {"strings": ["(reindeer)", "(Reindeer)"], "title": "Reindeer"},
    "relieved": {"strings": ["(relieved)", "(Relieved)"], "title": "Relieved"},
    "ribbonblack": {"strings": ["(ribbonblack)"], "title": "Black ribbon"},
    "ribbonblue": {"strings": ["(ribbonblue)"], "title": "Blue ribbon"},
    "ribbongreen": {"strings": ["(ribbongreen)"], "title": "Green ribbon"},
    "ribbonpink": {"strings": ["(ribbonpink)"], "title": "Pink ribbon"},
    "ribbonpride": {"strings": ["(ribbonpride)"], "title": "Pride ribbon"},
    "ribbonred": {"strings": ["(ribbonred)"], "title": "Red ribbon"},
    "ribbonyellow": {"strings": ["(ribbonyellow)"], "title": "Yellow ribbon"},
    "rickshaw": {"strings": ["(rickshaw)", "(Rickshaw)", "(rikshaw)", "(Rikshaw)", "(ricksha)", "(Ricksha)"], "title": "Rickshaw"},
    "ring": {"strings": ["(ring)", "(Ring)", "(engagement)", "(Engagement)"], "title": "Engagement ring"},
    "rock": {"strings": ["(rock)", "(Rock)"], "title": "Rock"},
    "rockchick": {"strings": ["(rockchick)", "(Rockchick)"], "title": "Rock Chick"},
    "rofl": {"strings": ["(rofl)", "(rotfl)", "(Rofl)", "(Rotfl)"], "title": "Rolling on the floor laughing"},
    "rose": {"strings": ["(rose)", "(Rose)"], "title": "Rose"},
    "rudolfidea": {"strings": ["(rudolfidea)", "(Rudolfidea)", "(rudolphidea)", "(Rudolphidea)"], "title": "Rudolf idea"},
    "rudolfsurprise": {"strings": ["(rudolfsurprise)", "(Rudolfsurprise)", "(rudolphsurprise)", "(Rudolphsurprise)"], "title": "Surprised Rudolf"},
    "rugbyball": {"strings": ["(rugbyball)"], "title": "Rugby ball"},
    "running": {"strings": ["(running)", "(Running)"], "title": "Running"},
    "sad": {"strings": [":(", ":-(", ":=(", "(sad)", ":<", ":-<", "(Sad)"], "title": "Sad"},
    "sadcat": {"strings": ["(sadcat)"], "title": "Sad cat"},
    "saddog": {"strings": ["(saddog)"], "title": "Sad dog"},
    "sadkoala": {"strings": ["(sadkoala)"], "title": "Sad koala"},
    "sadmonkey": {"strings": ["(sadmonkey)"], "title": "Sad monkey"},
    "sadness": {"strings": ["(sadness)", "(Sadness)"], "title": "Sadness"},
    "sadrobot": {"strings": ["(sadrobot)"], "title": "Sad robot"},
    "sailboat": {"strings": ["(sailboat)", "(yacht)", "(26f5_sailboat)"], "title": "Sailboat"},
    "sandcastle": {"strings": ["(sandcastle)"], "title": "Sandcastle"},
    "santa": {"strings": ["(santa)", "(Santa)", "(xmas)", "(Xmas)", "(christmas)", "(Christmas)"], "title": "Santa"},
    "santamooning": {"strings": ["(santamooning)", "(Santamooning)", "(mooningsanta)", "(Mooningsanta)"], "title": "Santa mooning"},
    "sarcastic": {"strings": ["(sarcastic)", "(Sarcastic)", "(sarcasm)", "(Sarcasm)", "(slowclap)", "(Slowclap)"], "title": "Sarcastic"},
    "scooter": {"strings": ["(scooter)", "(Scooter)"], "title": "Scooter"},
    "screamingfear": {"strings": ["(screamingfear)"], "title": "Screaming with fear"},
    "seal": {"strings": ["(seal)", "(Seal)"], "title": "Seal"},
    "seedling": {"strings": ["(seedling)"], "title": "Seedling"},
    "seenoevil": {"strings": ["(seenoevil)"], "title": "Monkey see no evil"},
    "selfie": {"strings": ["(selfie)", "(Selfie)"], "title": "Selfie"},
    "selfiediwali": {"strings": ["(selfiediwali)", "(Selfiediwali)"], "title": "Selfie Diwali"},
    "shake": {"strings": ["(shake)", "(Shake)"], "title": "Shake"},
    "shark": {"strings": ["(shark)", "(jaws)", "(1f988_shark)"], "title": "Shark"},
    "sheep": {"strings": ["(sheep)", "(bah)", "(Sheep)", "(Bah)"], "title": "Sheep"},
    "shivering": {"strings": ["(shivering)", "(Shivering)", "(cold)", "(Cold)", "(freezing)", "(Freezing)"], "title": "Cold shivering"},
    "shock": {"strings": ["(shock)", "(Shock)"], "title": "Spoiler Alert"},
    "shopping": {"strings": ["(shopping)", "(Shopping)", "(shopper)", "(Shopper)"], "title": "Girl shopping"},
    "shrimp": {"strings": ["(shrimp)", "(1f990_shrimp)"], "title": "Shrimp"},
    "silvermedal": {"strings": ["(silvermedal)", "(Silvermedal)"], "title": "Silver medal"},
    "skate": {"strings": ["(skate)", "(Skate)"], "title": "Skate"},
    "skip": {"strings": ["(skip)", "(Skip)", "(skippingrope)", "(Skippingrope)"], "title": "Keep Fit"},
    "skipping": {"strings": ["(skipping)", "(Skipping)"], "title": "Skipping"},
    "skull": {"strings": ["(skull)", "(Skull)"], "title": "Skull"},
    "skype": {"strings": ["(ss)", "(skype)", "(Skype)", "(Ss)"], "title": "Skype"},
    "slamdunk": {"strings": ["(slamdunk)", "(Slamdunk)"], "title": "Basketball"},
    "slap": {"strings": ["(slap)", "(Slap)", "(thappad)", "(Thappad)"], "title": "Slap"},
    "sleepy": {"strings": ["I-)", "I=)", "|-)", "(snooze)", "(Snooze)", "(sleepy)", "(Sleepy)"], "title": "Snooze"},
    "sloth": {"strings": ["(sloth)", "(Sloth)"], "title": "Sloth"},
    "smile": {"strings": [":)", ":-)", ":=)", "(smile)", "(Smile)"], "title": "Smile"},
    "smilebaby": {"strings": ["(smilebaby)"], "title": "Smile baby"},
    "smileboy": {"strings": ["(smileboy)"], "title": "Smile boy"},
    "smilecat": {"strings": ["(smilecat)"], "title": "Smile cat"},
    "smiledog": {"strings": ["(smiledog)"], "title": "Smile dog"},
    "smileeyes": {"strings": ["(smileeyes)"], "title": "Smile eyes"},
    "smilegirl": {"strings": ["(smilegirl)"], "title": "Smile girl"},
    "smilekoala": {"strings": ["(smilekoala)"], "title": "Smile koala"},
    "smileman": {"strings": ["(smileman)"], "title": "Smile man"},
    "smilemonkey": {"strings": ["(smilemonkey)"], "title": "Smile monkey"},
    "smilerobot": {"strings": ["(smilerobot)"], "title": "Smile robot"},
    "smilewoman": {"strings": ["(smilewoman)"], "title": "Smile woman"},
    "smirk": {"strings": ["(smirk)", "(Smirk)"], "title": "Smirking"},
    "smoke": {"strings": ["(ci)", "(smoke)", "(smoking)", "(Smoking)", "(Smoke)", "(Ci)"], "title": "Smoking"},
    "snail": {"strings": ["(snail)", "(sn)", "(SN)", "(Snail)", "(Sn)"], "title": "Snail"},
    "snake": {"strings": ["(snake)", "(Snake)"], "title": "Snake"},
    "snegovik": {"strings": ["(snegovik)", "(Snegovik)", "(snowbuddie)", "(Snowbuddie)"], "title": "Snow buddie"},
    "snorkler": {"strings": ["(snorkler)"], "title": "Snorkler"},
    "snowangel": {"strings": ["(snowangel)", "(Snowangel)"], "title": "Snow angel"},
    "snowflake": {"strings": ["(snowflake)", "(Snowflake)"], "title": "Snowflake"},
    "soccerball": {"strings": ["(soccerball)"], "title": "Soccer ball"},
    "sparkler": {"strings": ["(sparkler)", "(Sparkler)"], "title": "Sparkler"},
    "sparklingheart": {"strings": ["(sparklingheart)"], "title": "Sparkling heart"},
    "speaknoevil": {"strings": ["(speaknoevil)"], "title": "Monkey speak no evil"},
    "speechbubble": {"strings": ["(speechbubble)", "(Speechbubble)"], "title": "Speech bubble"},
    "speechless": {"strings": [":|", ":-|", ":=|", "(speechless)", "(Speechless)"], "title": "Speechless"},
    "spider": {"strings": ["(spider)", "(Spider)"], "title": "Spider"},
    "squid": {"strings": ["(squid)", "(1f991_squid)"], "title": "Squid"},
    "star": {"strings": ["(*)", "(star)", "(Star)"], "title": "Star"},
    "stareyes": {"strings": ["(stareyes)", "(Stareyes)"], "title": "Star eyes"},
    "statueofliberty": {"strings": ["(statueofliberty)", "(Statueofliberty)"], "title": "Statue of Liberty"},
    "steamtrain": {"strings": ["(steamtrain)", "(Steamtrain)", "(train)", "(Train)"], "title": "Steam train"},
    "stingray": {"strings": ["(stingray)", "(Stingray)"], "title": "Stingray"},
    "stop": {"strings": ["(!)", "(stop)", "(Stop)"], "title": "Stop"},
    "strawberry": {"strings": ["(strawberry)", "(Strawberry)"], "title": "Strawberry"},
    "sun": {"strings": ["(sun)", "(#)", "(Sun)"], "title": "Sun"},
    "sunflower": {"strings": ["(sunflower)", "(Sunflower)"], "title": "Sunflower"},
    "sunrise": {"strings": ["(sunrise)", "(1f305_sunrise)"], "title": "Sunrise"},
    "surprised": {"strings": [":O", ":-O", ":=O", ":o", ":-o", ":=o", "(surprised)", "(Surprised)"], "title": "Surprised"},
    "swear": {"strings": ["(swear)", "(Swear)"], "title": "Swearing"},
    "sweat": {"strings": ["(:|", "(sweat)", "(Sweat)"], "title": "Sweating"},
    "sweatgrinning": {"strings": ["(sweatgrinning)", "(Sweatgrinning)"], "title": "Sweat grinning"},
    "syne": {"strings": ["(syne)", "(Syne)"], "title": "Syne"},
    "talk": {"strings": ["(talk)", "(Talk)"], "title": "Talking"},
    "talktothehand": {"strings": ["(talktothehand)", "(Talktothehand)"], "title": "Talk to the hand"},
    "tandoorichicken": {"strings": ["(tandoori)", "(Tandoori)", "(tandoorichicken)", "(TandooriChicken)", "(Tandoorichicken)"], "title": "Tandoori chicken"},
    "target": {"strings": ["(target)", "(Target)"], "title": "Archery"},
    "taxi": {"strings": ["(taxi)", "(Taxi)"], "title": "Taxi"},
    "tennisball": {"strings": ["(tennisball)"], "title": "Tennis ball"},
    "tennisfail": {"strings": ["(tennisfail)", "(Tennisfail)"], "title": "Tennis fail"},
    "thanks": {"strings": ["(thanks)", "(Thanks)"], "title": "Thanks"},
    "think": {"strings": [":?", "(think)", ":-?", ":=?", "*-)", "(Think)"], "title": "Thinking"},
    "time": {"strings": ["(o)", "(O)", "(time)", "(clock)", "(0)", "(Time)", "(Clock)"], "title": "Time"},
    "tired": {"strings": ["(tired)", "(Tired)"], "title": "Tired"},
    "tmi": {"strings": ["(tmi)", "(Tmi)"], "title": "Too much information"},
    "toivo": {"strings": ["(toivo)", "(Toivo)"], "title": "Toivo"},
    "tongueout": {"strings": [":P", ":-P", ":=P", ":p", ":-p", ":=p", "(tongueout)", "(Tongueout)"], "title": "Tongue sticking out"},
    "tortoise": {"strings": ["(tortoise)", "(Tortoise)"], "title": "Tortoise"},
    "trophy": {"strings": ["(trophy)", "(Trophy)"], "title": "Trophy"},
    "truck": {"strings": ["(truck)", "(Truck)"], "title": "Truck"},
    "ttm": {"strings": ["(ttm)", "(Ttm)", "(bla)", "(Bla)"], "title": "Talking too much"},
    "tubelight": {"strings": ["(tubelight)", "(Tubelight)"], "title": "Tubelight"},
    "tulip": {"strings": ["(tulip)", "(Tulip)"], "title": "Tulip"},
    "tumbleweed": {"strings": ["(tumbleweed)", "(Tumbleweed)"], "title": "Tumbleweed"},
    "turkey": {"strings": ["(turkey)", "(Turkey)", "(turkeydance)", "(Turkeydance)", "(thanksgiving)", "(Thanksgiving)"], "title": "Dancing Thanksgiving turkey"},
    "turtle": {"strings": ["(turtle)"], "title": "Turtle"},
    "tvbinge": {"strings": ["(tvbinge)", "(Tvbinge)"], "title": "TV binge Zombie"},
    "twohearts": {"strings": ["(twohearts)"], "title": "Two hearts"},
    "umbrella": {"strings": ["(um)", "(umbrella)", "(Umbrella)", "(Um)"], "title": "Umbrella"},
    "umbrellaonground": {"strings": ["(umbrellaonground)", "(26f1_umbrellaonground)"], "title": "Umbrella on ground"},
    "unamused": {"strings": ["(unamused)", "(Unamused)"], "title": "Unamused"},
    "unicorn": {"strings": ["(unicorn)", "(Unicorn)"], "title": "Unicorn"},
    "unicornhead": {"strings": ["(unicornhead)", "(Unicornhead)"], "title": "Unicorn head"},
    "unsee": {"strings": ["(unsee)", "(Unsee)"], "title": "Can't unsee that"},
    "upsidedownface": {"strings": ["(upsidedownface)"], "title": "Upside down face"},
    "vampire": {"strings": ["(vampire)", "(Vampire)"], "title": "Vampire"},
    "veryconfused": {"strings": ["(veryconfused)", "(Veryconfused)"], "title": "Very confused"},
    "victory": {"strings": ["(victory)", "(Victory)"], "title": "Victory"},
    "vulcansalute": {"strings": ["(vulcansalute)", "(Vulcansalute)"], "title": "Vulcan salute"},
    "wait": {"strings": ["(wait)", "(Wait)"], "title": "Wait"},
    "waiting": {"strings": ["(waiting)", "(forever)", "(impatience)", "(Waiting)", "(Forever)", "(Impatience)"], "title": "Waiting"},
    "wasntme": {"strings": ["(wm)", "(wasntme)", "(Wasntme)", "(Wm)"], "title": "It wasn't me!"},
    "watermelon": {"strings": ["(watermelon)", "(Watermelon)"], "title": "Watermelon"},
    "waterwave": {"strings": ["(waterwave)", "(waves)", "(1f30a_waterwave)"], "title": "Water wave"},
    "weary": {"strings": ["(weary)", "(Weary)"], "title": "Weary"},
    "webheart": {"strings": ["(webheart)", "(Webheart)"], "title": "Web Heart"},
    "wfh": {"strings": ["(@h)", "(wfh)", "(@H)", "(Wfh)"], "title": "Working from home"},
    "whale": {"strings": ["(whale)", "(Whale)"], "title": "Whale"},
    "whatsgoingon": {"strings": ["(!!?)", "(whatsgoingon)", "(Whatsgoingon)"], "title": "What's going on?"},
    "whew": {"strings": ["(whew)", "(phew)", "(Whew)", "(Phew)"], "title": "Relieved"},
    "whistle": {"strings": ["(whistle)", "(Whistle)", "(seeti)", "(Seeti)"], "title": "Whistle"},
    "wiltedflower": {"strings": ["(wiltedflower)", "(Wiltedflower)", "(w)", "(W)"], "title": "Wilted flower"},
    "windturbine": {"strings": ["(windturbine)"], "title": "Wind Turbine"},
    "wink": {"strings": [";)", ";-)", ";=)", "(wink)", "(Wink)"], "title": "Wink"},
    "winktongueout": {"strings": [";p", ";-p", ";=p", ";P", ";-P", ";=P", "(winktongueout)"], "title": "Winking tongue out"},
    "winner": {"strings": ["(winner)", "(Winner)"], "title": "Podium"},
    "witch": {"strings": ["(witch)", "(Witch)"], "title": "Witch"},
    "woman": {"strings": ["(x)", "(woman)", "(X)", "(female)", "(girl)", "(Woman)", "(Female)", "(Girl)"], "title": "Woman"},
    "womanwomanheart": {"strings": ["(womanwomanheart)"], "title": "Woman woman heart"},
    "womanwomanholdinghands": {"strings": ["(womanwomanholdinghands)"], "title": "Woman woman holding hands"},
    "womanwomankiss": {"strings": ["(womanwomankiss)", "(womanwomankissing)"], "title": "Woman woman kiss"},
    "wonder": {"strings": [":^)", "(wonder)", "(Wonder)"], "title": "Wondering"},
    "worry": {"strings": [":s", "(worry)", ":S", ":-s", ":-S", ":=s", ":=S", "(Worry)", "(worried)", "(Worried)"], "title": "Worried"},
    "woty": {"strings": ["(woty)", "(Woty)"], "title": "Woman of the year"},
    "wtf": {"strings": ["(wtf)", "(Wtf)"], "title": "What the..."},
    "xd": {"strings": ["(xd)", "(Xd)"], "title": "XD smiley"},
    "xmascar": {"strings": ["(xmascar)", "(Xmascar)"], "title": "Xmas car"},
    "xmascry": {"strings": ["(xmascry)", "(Xmascry)", "(xmascrying)", "(Xmascrying)"], "title": "Xmas cry"},
    "xmascwl": {"strings": ["(xmascwl)", "(Xmascwl)"], "title": "Xmas crying with laughter"},
    "xmasheart": {"strings": ["(xmasheart)", "(Xmasheart)"], "title": "Xmas heart"},
    "xmassarcastic": {"strings": ["(xmassarcastic)", "(Xmassarcastic)"], "title": "Xmas sarcastic"},
    "xmastree": {"strings": ["(xmastree)", "(Xmastree)", "(christmastree)", "(Christmastree)"], "title": "Xmas tree"},
    "xmasyes": {"strings": ["(xmasyes)", "(Xmasyes)"], "title": "Xmas yes"},
    "yawn": {"strings": ["(yawn)", "(Yawn)"], "title": "Yawn"},
    "yes": {"strings": ["(y)", "(Y)", "(yes)", "(Yes)", "(ok)"], "title": "Yes"},
    "yoga": {"strings": ["(yoga)", "(Yoga)"], "title": "Yoga"},
    "zombie": {"strings": ["(zombie)", "(Zombie)"], "title": "Zombie"},
    "zombiedrool": {"strings": ["(zombiedrool)", "(Zombiedrool)"], "title": "Hammer Zombie"},
    "zombiewave": {"strings": ["(zombiewave)", "(Zombiewave)"], "title": "Zombie Wave"},
}


"""Maps emoticon strings to emoticon names."""
EmoticonStrings = dict((s, k) for k, d in EmoticonData.items() for s in d["strings"])
