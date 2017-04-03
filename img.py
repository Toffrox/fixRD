import math
import sys
import time
import random
import io

import json
import urllib
import requests
from PIL import Image
from PIL import ImageChops
from requests.adapters import HTTPAdapter

# Behold, the dirtiest code I ever wrote
# This hacky hack serves as a bridge for urllib in Python 2 and Python 3
try:
    urllib.urlopen
except:
    urllib.urlopen = urllib.request.urlopen

img = None
origin = None # (int(sys.argv[1]), int(sys.argv[2]))
username = sys.argv[1]
password = sys.argv[2]
percent = 0
checked = 0
total = 0
restart_flag = False
ocommitsha = None
version = "1\n"

def updateImg():
    try:
        global img
        global ocommitsha
        global origin

        new_version = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/version.txt').read().decode("utf-8")
        if version != new_version:
            print("!!! NEW VERSION OF THE SCRIPT IS AVALIABLE! PLEASE REDOWNLOAD! !!!")
            sys.exit(0)
        im = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/dash1.png').read()
        new_img = Image.open(io.BytesIO(im))
        if img is not None and ImageChops.difference(img, new_img).getbbox() is None:
            print("Image hasn't been updated")
            return False
        img = new_img
        print("Template updated!")
        new_origin = urllib.urlopen('https://raw.githubusercontent.com/hithroc/fixRD/master/origin.txt').read().decode("utf-8").split(',')
        origin = (int(new_origin[0]), int(new_origin[1]))
        print(origin)
        return True
    except SystemExit:
        raise SystemExit
    #except:
    #    print("Failed to fetch new image or the origin! Will try next time! Waiting 5 seconds and trying again...")

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

def fetch_canvas():
    print("Fetching canvas...")

    width = 1000
    pixels = [list() for _ in range(width)]
    content = None

    try:
        response = s.get('https://www.reddit.com/api/place/board-bitmap')
        response.raise_for_status()
        content = response.content[4:]
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        print("Failed to fetch canvas! Retrying in 10 seconds...")
        time.sleep(10)
        return fetch_canvas() #Yes, this should be a loop and not recursive, but I'm lazy

    for i, b in enumerate(content):
        x = (i * 2) % width
        pixels[x].append(ord(b) >> 4)
        pixels[x+1].append(ord(b) & 0x0F)

    return pixels

def place_pixel(ax, ay, new_color):
    print("Placing pixel at {},{} with color #{}".format(ax, ay, new_color))

    try:
        r = s.post("https://www.reddit.com/api/place/draw.json",
                   data={"x": str(ax), "y": str(ay), "color": str(new_color)})
    except:
        print("Pixel post error! Pausing for 10 seconds...")
        sleep(10)
        return

    secs = float(r.json()["wait_seconds"])
    waitTime = int(secs) + 2
    if "error" not in r.json():
        message = "Placed color sucessfully. Starting search for next pixel in {} seconds."
    else:
        message = "Cooldown already active! Waiting for {} seconds."
    while(waitTime > 0):
        print(message.format(waitTime))
        if(waitTime > 35):
            time.sleep(30)
            waitTime -= 30
        elif(waitTime > 15):
            time.sleep(10)
            waitTime -= 10
        else:
            time.sleep(1)
            waitTime -= 1


while True:
    updateImg()
    canvas = fetch_canvas()

    print("Searching for corruption in image with height: {}, width: {}".format(img.height, img.width))
    
    total = img.width * img.height
    points = range(total)
    random.shuffle(points)

    for i in range(total):
        point = points[i]
        xy = [point % img.width, point / img.width]
        pixel = img.getpixel((xy[0], xy[1]))

        if pixel[3] > 0:
            pal = find_palette((pixel[0], pixel[1], pixel[2]))

            ax = xy[0] + origin[0]
            ay = xy[1] + origin[1]

            #print("{}: Checking point {},{}. Expected: {}. Found: {}".format(i, ax, ay, pal, canvas[ax][ay]))
            if(canvas[ax][ay] != pal):
                print("Found corruption after {} pixels at {},{}. Expected: {}, Found: {}".format(i, ax, ay, pal, canvas[ax][ay]))
                place_pixel(ax, ay, pal)
                break
    print('')
