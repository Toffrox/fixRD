import math
import sys
import time
import random

import json
import urllib
import requests
from PIL import Image
from requests.adapters import HTTPAdapter

# Behold, the dirtiest code I ever wrote
# This hacky hack serves as a bridge for urllib in Python 2 and Python 3
try:
    urllib.urlopen
except:
    urllib.urlopen = urllib.request.urlopen

#img = Image.open(sys.argv[1])
img = None
im = None # urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/dash.png').read()
origin = None # (int(sys.argv[1]), int(sys.argv[2]))
username = sys.argv[1]
password = sys.argv[2]
percent = 0
checked = 0
total = 0
restart_flag = False
ocommitsha = None
version = "0\n"

#print("Template updated!")
#seegit = None urllib.urlopen('https://api.github.com/repos/hithroc/fixRD/git/refs/heads/master').read().decode("utf-8")
#loadgit = json.loads(seegit)
#ocommitsha = loadgit['object']['sha']

def updateImg():
    new_version = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/version.txt').read().decode("utf-8")
    if version != new_version:
        print("!!! NEW VERSION OF THE SCRIPT IS AVALIABLE! PLEASE REDOWNLOAD! !!!")
        sys.exit(0)
    seegit = urllib.urlopen('https://api.github.com/repos/hithroc/fixRD/git/refs/heads/master').read().decode("utf-8")
    loadgit = json.loads(seegit)
    ncommitsha = loadgit['object']['sha']
    global ocommitsha
    global img
    global origin

    if ocommitsha == ncommitsha:
        print('Master branch commit\'s SHA-1 has not changed on the Github repo.')
        return False
    else:
        #img = Image.open('dash.png')
        #img.close()
        im = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/dash_new.png').read()
        with open ('dash_new.png', 'wb') as imgb:
            imgb.write(im)
        img = Image.open('dash_new.png')
        print("Template updated!")
        ocommitsha = ncommitsha
        try:
            new_origin = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/origin.txt').read().decode("utf-8").split(',')
            origin = (int(new_origin[0]), int(new_origin[1]))
            print(origin)
        except:
            print("Failed to fetch new image or the origin!")
        return True

updateImg()

def find_palette(point):
    rgb_code_dictionary = {
        (255, 255, 255): 0,
        (228, 228, 228): 1,
        (136, 136, 136): 2,
        (34, 34, 34): 3,
        (255, 167, 209): 4,
        (229, 0, 0): 5,
        (229, 149, 0): 6,
        (160, 106, 66): 7,
        (229, 217, 0): 8,
        (148, 224, 68): 9,
        (2, 190, 1): 10,
        (0, 211, 211): 11,
        (0, 131, 199): 12,
        (0, 0, 234): 13,
        (207, 110, 228): 14,
        (130, 0, 128): 15
    }

    def distance(c1, c2):
        (r1, g1, b1) = c1
        (r2, g2, b2) = c2
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    colors = list(rgb_code_dictionary.keys())
    closest_colors = sorted(colors, key=lambda color: distance(color, point))
    closest_color = closest_colors[0]
    code = rgb_code_dictionary[closest_color]
    return code


s = requests.Session()
s.mount('https://www.reddit.com', HTTPAdapter(max_retries=5))
s.headers["User-Agent"] = "PlacePlacer"
r = s.post("https://www.reddit.com/api/login/{}".format(username),
           data={"user": username, "passwd": password, "api_type": "json"})
s.headers['x-modhash'] = r.json()["json"]["data"]["modhash"]

def place_pixel(ax, ay, new_color):
    message = "Probing absolute pixel {},{}".format(ax, ay)

    while True:
        try:
            r = s.get("http://reddit.com/api/place/pixel.json?x={}&y={}".format(ax, ay), timeout=5)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except:
            print("Failed to fetch pixel data! Retrying in 5 seconds...")
            time.sleep(5)
            continue
        if r.status_code == 200:
            data = r.json()
            break
        else:
            print("ERROR: ", r, r.text)
        time.sleep(5)

    old_color = data["color"] if "color" in data else 0
    if old_color == new_color:
        print("{}: skipping, color #{} set by {}".format(message, new_color, data["user_name"] if "user_name" in data else "<nobody>"))
    if old_color != new_color:
        if updateImg():
            global restart_flag
            restart_flag = True
            return
        print("{}: Placing color #{}".format(message, new_color, ax, ay))
        try:
            r = s.post("https://www.reddit.com/api/place/draw.json",
                       data={"x": str(ax), "y": str(ay), "color": str(new_color)})
        except:
            print("Pixel post error! Continuing...")
            return

        secs = float(r.json()["wait_seconds"])
        if "error" not in r.json():
            waitTime = int(secs) -78
            message = "Placed color, Starting search for next pixel in {} seconds. {}/{} complete."
            m = message.format(waitTime, checked, total)
            print(m)
            message = "Starting search for next pixel in {} seconds. {}/{} complete."
            while(waitTime > 0):
                if(waitTime > 35):
                    time.sleep(30)
                    waitTime -= 30
                else:
                    time.sleep(1)
                    waitTime -= 1
                m = message.format(waitTime, checked, total)
                print(m)
            print("Probing...")
            return
        else:
            message = "Cooldown already active - waiting {} seconds. {}/{} complete."
        waitTime = int(secs) + 2
        m = message.format(waitTime, checked, total)
        print(m)
        while(waitTime > 0):
            if (waitTime > 35):
                time.sleep(30)
                waitTime -= 30
            else:
                time.sleep(1)
                waitTime -= 1
            m = message.format(waitTime, checked, total)
            print(m)
        print("Probing...")
        if "error" in r.json():
            place_pixel(ax, ay, new_color)


# From: http://stackoverflow.com/questions/27337784/how-do-i-shuffle-a-multidimensional-list-in-python
def shuffle2d(arr2d, rand=random):
    """Shuffes entries of 2-d array arr2d, preserving shape."""
    reshape = []
    data = []
    iend = 0
    for row in arr2d:
        data.extend(row)
        istart, iend = iend, iend+len(row)
        reshape.append((istart, iend))
    rand.shuffle(data)
    return [data[istart:iend] for (istart,iend) in reshape]

while True:
    restart_flag = False
    print("starting image placement for img height: {}, width: {}".format(img.height, img.width))
    arr2d = shuffle2d([[[i,j] for i in range(img.width)] for j in range(img.height)])
    total = img.width * img.height
    checked = 0
    print("Probing...")
    for y in range(img.width ):
        if restart_flag:
            break
        for x in range(img.height ):
            xx = arr2d[x][y]
            pixel = img.getpixel((xx[0], xx[1]))

            if pixel[3] > 0:
                pal = find_palette((pixel[0], pixel[1], pixel[2]))

                ax = xx[0] + origin[0]
                ay = xx[1] + origin[1]

                place_pixel(ax, ay, pal)
                if restart_flag:
                    break
                checked += 1
                percent = ((checked/total) * 100)
    if restart_flag:
        print("Restarting...")
        continue
    message = "All pixels placed, sleeping {}s..."
    waitTime = 10
    while(waitTime > 0):
        m = message.format(waitTime)
        time.sleep(1)
        waitTime -= 1
        print(m)
