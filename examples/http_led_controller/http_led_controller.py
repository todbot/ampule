# http_led_controller.py -- simple HTTP JSON server to control NeoPixels
# 15 Apr 2022 - @todbot / Tod Kurt
#
# Uses todbot fork of Ampule HTTP server library
# - https://github.com/todbot/ampule
# - https://github.com/deckerego/ampule
#
# Installation:
# - Copy this file as "code.py" to CIRCUITPY
# - Copy "ampule.py" to CIRCUITPY 
# - Copy "html" directory to CIRCUITPY 
#
# Has the following API endpoints:
#  /    - show current status
#  /on  - turn LEDs on
#  /off - turn LEDs off
#  /set - set LEDs to particular color hex code with "/set?rgb=FF2288"
#
# Responds with JSON with keys "status", "rgb", and "uptime"
#
# This example uses a Lolin S2 mini board, but any ESP32S2-based will work
# https://circuitpython.org/board/lolin_s2_mini/
#

import board
import wifi
import socketpool
import ampule
import json
import neopixel
import time
import supervisor
import rainbowio
import random

leds = neopixel.NeoPixel(board.IO39, 8, brightness=0.1)

led_data = {
    "status": "online",
    "rgb": "#ff00ff",
    "mode": "cylon", # 'confetti', 'cylon', 'rainbow', 'solid' 
    "uptime": time.monotonic()
}

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16)  for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def animate_leds():
    mode = led_data['mode']
    if mode == 'solid':
        leds.fill( hex_to_rgb( led_data['rgb'] ))
    elif mode == 'rainbow':
        #t = supervisor.ticks_ms() / 10
        t = time.monotonic() / 100
        leds[:] = [rainbowio.colorwheel( t + i*(255/len(leds)) ) for i in range(len(leds))]
    elif mode == 'cylon':
        t = int((time.monotonic() * 10) % (2*len(leds)))
        leds[:] = [[max(i-5,0) for i in l] for l in leds] # dim all by (5,5,5)
        if t > len(leds)-1 : t = 2*len(leds) - t -1
        leds[t] = hex_to_rgb( led_data['rgb'] )
    elif mode == 'confetti':
        if supervisor.ticks_ms() % 100 < 1:
            leds[:] = [[max(i-30,0) for i in l] for l in leds] # dim all by 30
            i = int(random.uniform(0,len(leds)))
            leds[i] = hex_to_rgb( led_data['rgb'] )
    else:
        pass


json_headers = {
    "Content-Type": "application/json; charset=UTF-8",
    "Access-Control-Allow-Origin": '*',
    "Access-Control-Allow-Methods": 'GET, POST',
    "Access-Control-Allow-Headers": 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
}

@ampule.route("/")
def index(request):
    with open('/html/index.html') as file:
        index_html = file.read()
    return (200, {}, index_html)

@ampule.route("/status")
def status(request):
    return (200, json_headers, json.dumps(led_data))

@ampule.route("/mode/<mode>")
def set_mode(request, mode):
    led_data['mode'] = mode
    (r,g,b) = hex_to_rgb(led_data['rgb'])
    if r==0 and g==0 and b==0:
        led_data['rgb'] = "#ff00ff"
    return (200, json_headers, json.dumps(led_data))
    
# @ampule.route("/rainbow")
# def status(request):
#     led_data['mode'] = 'rainbow'
#     return (200, json_headers, json.dumps(led_data))

@ampule.route("/on")
def light_on(request):
    leds.fill(0xffffff)
    led_data['status'] = "on"
    led_data['mode'] = 'solid'
    led_data['rgb'] = "#FFFFFF"
    led_data['uptime'] = time.monotonic()
    return (200, json_headers, json.dumps(led_data))

@ampule.route("/off")
def light_off(request):
    leds.fill(0x000000)
    led_data['status'] = "off"
    led_data['mode'] = 'solid'
    led_data['rgb'] = "#000000"
    led_data['uptime'] = time.monotonic()
    return (200, json_headers, json.dumps(led_data))

@ampule.route("/set")
def light_set(request):
    """ Send /set?rgb=CC0033 to change LEDs to #CC0033 """
    params = request.params
    rgb_str = params.get("rgb",None)
    print("rgb_str:",rgb_str)
    rgb = (0,0,0)
    if rgb_str:
        rgb_str = rgb_str.lstrip("%23") # hacky 
        rgb = hex_to_rgb(rgb_str)
        #led_data['mode'] = 'solid'
        led_data['rgb'] = rgb_to_hex(rgb)
        led_data['status'] = "set"
    else:
        led_data['status'] = "error: no 'rgb' param"

    led_data['uptime'] = time.monotonic()
    return (200, json_headers, json.dumps(led_data))

@ampule.route("/.*")
def filepath(request):
    p = request.path
    print("p:",p)
    p = "/html" + p
    with open(p, 'rb') as file:
        filedata = file.read()
    return (200, {}, filedata)

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets not found in secrets.py")
    raise

try:
    print("Connecting to %s..." % secrets["ssid"])
    wifi.radio.connect(secrets["ssid"], secrets["password"])
except:
    print("Error connecting to WiFi")
    raise

# a little startup lightshow
leds.fill(0xff00ff)
time.sleep(0.5)
leds.fill(0x000000)

# start up the server
port = 80
pool = socketpool.SocketPool(wifi.radio)
socket = pool.socket()
socket.bind(['0.0.0.0', port])
socket.listen(1)

print("Connected to %s. Access at: http://%s:%d/ " % (secrets["ssid"], wifi.radio.ipv4_address, port) )
    

while True:
    animate_leds()
    ampule.listen(socket, timeout=0.1, accept_timeout=0)
