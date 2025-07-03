# rpico_rgb_keypad_obs v1.0.1
#
# SPDX-FileCopyrightText: 2023 Martin Looker
#
# SPDX-License-Identifier: MIT
#
# DESCRIPTION
#
# This code provides a controller for OBS studio acting as a USB keyboard
#
# Keys are as follows:
#
# Green:
#   11 scene keys, only one scene can be active at a time
# Cyan, Blue:
#   2 general keys
# Red, Yellow, Magenta:
#   3 toggle keys different key combos are sent when toggling on or off, so map these to start/stop
#   hotkeys for start/stop streaming etc
#
# HARDWARE
#
# https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html
# https://shop.pimoroni.com/products/pico-rgb-keypad-base
#
# LIBRARIES
#
# adafruit:
#   https://circuitpython.org/board/raspberry_pi_pico/
#   https://github.com/adafruit/Adafruit_DotStar
#   https://github.com/adafruit/Adafruit_CircuitPython_HID
#
# pimoroni:
#   https://github.com/pimoroni/pmk-circuitpython
#
# SOFTWARE
#
# Inspired by:
#   https://github.com/pimoroni/pmk-circuitpython/blob/main/examples/obs-studio-toggle-and-mutex.py

# Libraries (built-in)
import math
import time
import board
import usb_hid

# Libraries (bundle)
from adafruit_neotrellis.neotrellis import NeoTrellis

import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# When true keycodes are sent
KC_LIVE = True
# When true keycodes are sent over BLE
BLE_LIVE = True

# LED Hues
HUE_SPLIT = (1.0/24.0)
hue = {
    "red"     : (HUE_SPLIT *  0.0),
    "rry"     : (HUE_SPLIT *  1.0),
    "ry"      : (HUE_SPLIT *  2.0),
    "ryy"     : (HUE_SPLIT *  3.0),
    "yellow"  : (HUE_SPLIT *  4.0),
    "yyg"     : (HUE_SPLIT *  5.0),
    "yg"      : (HUE_SPLIT *  6.0),
    "ygg"     : (HUE_SPLIT *  7.0),
    "green"   : (HUE_SPLIT *  8.0),
    "ggc"     : (HUE_SPLIT *  9.0),
    "gc"      : (HUE_SPLIT * 10.0),
    "gcc"     : (HUE_SPLIT * 11.0),
    "cyan"    : (HUE_SPLIT * 12.0),
    "ccb"     : (HUE_SPLIT * 13.0),
    "cb"      : (HUE_SPLIT * 14.0),
    "cbb"     : (HUE_SPLIT * 15.0),
    "blue"    : (HUE_SPLIT * 16.0),
    "bbm"     : (HUE_SPLIT * 17.0),
    "bm"      : (HUE_SPLIT * 18.0),
    "bmm"     : (HUE_SPLIT * 19.0),
    "magenta" : (HUE_SPLIT * 20.0),
    "mmr"     : (HUE_SPLIT * 21.0),
    "mr"      : (HUE_SPLIT * 22.0),
    "mrr"     : (HUE_SPLIT * 23.0),
}

# Hue:
#   Set this for the pad color.
#
# Group:
#   Set this to group pads together to operate like radio buttons (good for
#   scene selection). You can have many separate groups of keys as set by the
#   string set for the group
#
# Keycodes On:
#   These are the keyboard codes to be sent for normal, grouped and toggle on
#   pads.
#
# Keycodes Off:
#   These are the keyboard codes to be sent for toggle off pads, setting this
#   makes a toggle button, good for start/stop streaming
#
# Note:
#   Pads configured as toggles will be removed from any groups
#
# New config
config = [
    {"hue": hue["red"],     "group": None,    "keycodes_on": [Keycode.ALT,  Keycode.F13],          "keycodes_off": [Keycode.CONTROL, Keycode.F13]}, # 0 - Rec Start/Stop
    {"hue": hue["mr"],      "group": "scene", "keycodes_on": [Keycode.F13],                        "keycodes_off": None                          }, # 1 - Scene Red
    {"hue": hue["mr"],      "group": "scene", "keycodes_on": [Keycode.F14],                        "keycodes_off": None                          }, # 2 - Scene Red Smith Pres
    {"hue": hue["mr"],      "group": "scene", "keycodes_on": [Keycode.F15],                        "keycodes_off": None                          }, # 3 - Scene Red Smith
    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F16],                        "keycodes_off": None                          }, # 4 - Scene Screen
    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F17],                        "keycodes_off": None                          }, # 5 - Scene Screen Presenter
    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F18],                        "keycodes_off": None                          }, # 6 - Scene Screen Mobile
    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F19],                        "keycodes_off": None                          }, # 7 - Scene Screen Desk
    {"hue": hue["bm"],      "group": "scene", "keycodes_on": [Keycode.F20],                        "keycodes_off": None                          }, # 8 - Scene Desk
    {"hue": hue["bm"],      "group": "scene", "keycodes_on": [Keycode.F21],                        "keycodes_off": None                          }, # 9 - Scene Desk Presenter
    {"hue": hue["bm"],      "group": "scene", "keycodes_on": [Keycode.F22],                        "keycodes_off": None                          }, # A - Scene Desk Mobile
    {"hue": hue["bm"],      "group": "scene", "keycodes_on": [Keycode.F23],                        "keycodes_off": None                          }, # B - Scene Desk Screen
    {"hue": hue["blue"],    "group": None,    "keycodes_on": [Keycode.SHIFT, Keycode.F13],         "keycodes_off": None                          }, # C - Screenshot
    {"hue": hue["cyan"],    "group": None,    "keycodes_on": [Keycode.ALT,   Keycode.LEFT_ARROW],  "keycodes_off": None                          }, # D - Chrome Back
    {"hue": hue["cyan"],    "group": None,    "keycodes_on": [Keycode.ALT,   Keycode.RIGHT_ARROW], "keycodes_off": None                          }, # E - Chrome Forward
    {"hue": hue["green"],   "group": None   , "keycodes_on": [Keycode.ALT,   Keycode.F14],         "keycodes_off": [Keycode.CONTROL, Keycode.F14]}  # F - Virtual Camera Start/Stop
]
# Second config
#config = [
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F13],                  "keycodes_off": None                        }, # 0
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F14],                  "keycodes_off": None                        }, # 1
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F15],                  "keycodes_off": None                        }, # 2
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F16],                  "keycodes_off": None                        }, # 3
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F17],                  "keycodes_off": None                        }, # 4
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F18],                  "keycodes_off": None                        }, # 5
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F19],                  "keycodes_off": None                        }, # 6
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F20],                  "keycodes_off": None                        }, # 7
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F21],                  "keycodes_off": None                        }, # 8
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F22],                  "keycodes_off": None                        }, # 9
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F23],                  "keycodes_off": None                        }, # A
#    {"hue": hue["magenta"], "group": "scene", "keycodes_on": [Keycode.F24],                  "keycodes_off": None                        }, # B
#    {"hue": hue["cyan"]   , "group": None,    "keycodes_on": [Keycode.SHIFT,   Keycode.F13], "keycodes_off": [Keycode.SHIFT, Keycode.F13]}, # C
#    {"hue": hue["cyan"]   , "group": None,    "keycodes_on": [Keycode.SHIFT,   Keycode.F14], "keycodes_off": [Keycode.SHIFT, Keycode.F14]}, # D
#    {"hue": hue["green"]  , "group": None,    "keycodes_on": [Keycode.CONTROL, Keycode.F13], "keycodes_off": [Keycode.ALT,   Keycode.F13]}, # E
#    {"hue": hue["red"]    , "group": None   , "keycodes_on": [Keycode.CONTROL, Keycode.F14], "keycodes_off": [Keycode.ALT,   Keycode.F14]}  # F
#]

# Original config
#config = [
#    {"hue": hue["yg"]     , "group": "scene", "keycodes_on": [Keycode.F13],                  "keycodes_off": None                      }, # 0
#    {"hue": hue["yellow"] , "group": "scene", "keycodes_on": [Keycode.F14],                  "keycodes_off": None                      }, # 1
#    {"hue": hue["yg"]     , "group": "scene", "keycodes_on": [Keycode.F15],                  "keycodes_off": None                      }, # 2
#    {"hue": hue["red"]    , "group": None   , "keycodes_on": [Keycode.CONTROL, Keycode.F13], "keycodes_off": [Keycode.ALT, Keycode.F13]}, # 3
#    {"hue": hue["gc"]     , "group": "scene", "keycodes_on": [Keycode.F16],                  "keycodes_off": None                      }, # 4
#    {"hue": hue["green"]  , "group": "scene", "keycodes_on": [Keycode.F17],                  "keycodes_off": None                      }, # 5
#    {"hue": hue["gc"]     , "group": "scene", "keycodes_on": [Keycode.F18],                  "keycodes_off": None                      }, # 6
#    {"hue": hue["rry"]    , "group": None   , "keycodes_on": [Keycode.CONTROL, Keycode.F14], "keycodes_off": [Keycode.ALT, Keycode.F14]}, # 7
#    {"hue": hue["cb"]     , "group": "scene", "keycodes_on": [Keycode.F19],                  "keycodes_off": None                      }, # 8
#    {"hue": hue["cyan"]   , "group": "scene", "keycodes_on": [Keycode.F20],                  "keycodes_off": None                      }, # 9
#    {"hue": hue["cb"]     , "group": "scene", "keycodes_on": [Keycode.F21],                  "keycodes_off": None                      }, # A
#    {"hue": hue["ry"]     , "group": None,    "keycodes_on": [Keycode.SHIFT, Keycode.F13]  , "keycodes_off": None                      }, # B
#    {"hue": hue["bm"]     , "group": "scene", "keycodes_on": [Keycode.F22],                  "keycodes_off": None                      }, # C
#    {"hue": hue["blue"]   , "group": "scene", "keycodes_on": [Keycode.F23],                  "keycodes_off": None                      }, # D
#    {"hue": hue["bm"]     , "group": "scene", "keycodes_on": [Keycode.F24],                  "keycodes_off": None                      }, # E
#    {"hue": hue["ryy"]    , "group": None   , "keycodes_on": [Keycode.CONTROL, Keycode.F16], "keycodes_off": [Keycode.ALT, Keycode.F16]}  # F
#]

# LED Values (brightness)
VAL_SPLIT = (1.0/32.0)
VAL_MIN   = (VAL_SPLIT *  0.0)
VAL_OFF   = (VAL_SPLIT *  2.0)
VAL_ON    = (VAL_SPLIT * 30.0)
VAL_MAX   = (VAL_SPLIT * 32.0)
VAL_STEP  = 0.01

# this will be called when button events are received
def key_event(event):
    # key pressed when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        print(f'keypad press {event.number}')
        # Pad is now down
        config[event.number]["down"] = True
        # Normal pad ?
        if config[event.number]["mode"] == "key":
            # Press the on keycodes
            press_keycodes(config[event.number]["keycodes_on"])
        # Toggle pad ?
        elif config[event.number]["mode"] == "toggle":
            # Toggle is currently on ?
            if config[event.number]["on"]:
                # Turn off
                config[event.number]["on"] = False
                # Press the off keycodes
                press_keycodes(config[event.number]["keycodes_off"])
            # Toggle is currently off ?
            else:
                # Turn on
                config[event.number]["on"] = True
                # Press the on keycodes
                press_keycodes(config[event.number]["keycodes_on"])
        # Grouped pad ?
        elif config[event.number]["mode"] == "group":
            # Turn on the pressed pad
            config[event.number]["on"] = True
            # Press the on keycodes
            press_keycodes(config[event.number]["keycodes_on"])
            # Loop through pads
            for i in range(16):
                # Not the pad that has just been pressed ?
                if i != event.number:
                    # This pad is in the same group as the pad that has just been pressed ?
                    if config[i]["mode"] == "group" and config[i]["group"] == config[event.number]["group"]:
                        # The pad is on ?
                        if config[i]["on"]:
                            # Turn it off
                            config[i]["on"] = False
                            # Set val to minimum
                            config[i]["val"] = VAL_MIN
    # key released when a falling edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        print(f'keypad release {event.number}')
        # Pad is not down
        config[event.number]["down"] = False
        # Normal pad ?
        if config[event.number]["mode"] == "key":
            # Release on keycodes
            release_keycodes(config[event.number]["keycodes_on"])
        # Toggle pad ?
        elif config[event.number]["mode"] == "toggle":
            # Pad has been toggled on ?
            if config[event.number]["on"]:
                # Release on keycodes
                release_keycodes(config[event.number]["keycodes_on"])
            # Pad has just been turned off ?
            else:
                # Release off keycodes
                release_keycodes(config[event.number]["keycodes_off"])
        # Grouped pad
        elif config[event.number]["mode"] == "group":
            # Release on keycodes
            release_keycodes(config[event.number]["keycodes_on"])

# Presses a list of keycodes
def press_keycodes(kcs):
    send = "Disabled"
    if KC_LIVE:
        if BLE_LIVE:
            if ble.connected:
                send = "BLE"
            else:
                send = "BLE disconnected"
        else:
            send = "USB"
    print(f'keycode press {kcs} {send}')
    if send == "BLE" or send == "USB":
        if len(kcs) == 1:
            keyboard.press(kcs[0])
        elif len(kcs) == 2:
            keyboard.press(kcs[0], kcs[1])
        elif len(kcs) == 3:
            keyboard.press(kcs[0], kcs[1], kcs[2])

# Releases a list of keycodes
def release_keycodes(kcs):
    send = "Disabled"
    if KC_LIVE:
        if BLE_LIVE:
            if ble.connected:
                send = "BLE"
            else:
                send = "BLE disconnected"
        else:
            send = "USB"
    print(f'keycode release {kcs} {send}')
    if send == "BLE" or send == "USB":
        if len(kcs) == 1:
            keyboard.release(kcs[0])
        elif len(kcs) == 2:
            keyboard.release(kcs[0], kcs[1])
        elif len(kcs) == 3:
            keyboard.release(kcs[0], kcs[1], kcs[2])

def hsv_to_rgb(h, s, v):
    # Convert an HSV (0.0-1.0) colour to RGB (0-255)
    if s == 0.0:
        rgb = [v, v, v]

    i = int(h * 6.0)

    f = (h*6.)-i; p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f)); i%=6

    if i == 0:
        rgb = [v, t, p]
    if i == 1:
        rgb = [q, v, p]
    if i == 2:
        rgb = [p, v, t]
    if i == 3:
        rgb = [p, q, v]
    if i == 4:
        rgb = [t, p, v]
    if i == 5:
        rgb = [v, p, q]

    rgb = tuple(int(c * 255) for c in rgb)

    return rgb

# Set up neotrellis
i2c_bus = board.I2C()  # uses board.SCL and board.SDA
# i2c_bus = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
trellis = NeoTrellis(i2c_bus)
trellis.brightness = 0.5

# Add runtime data to config
for i in range(16):
    trellis.pixels[i] = (0x00, 0x00, 0x7F)
    # activate rising edge events on key
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all key
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the callback
    trellis.callbacks[i] = key_event
    # Defaults
    # Mode is toggle
    config[i]["mode"] = None
    # Set LED value to max
    config[i]["val"] = VAL_MAX
    # Not down
    config[i]["down"] = False
    # Not on
    config[i]["on"] = False
    # This is a toggle pad ?
    if config[i]["keycodes_off"] != None and len(config[i]["keycodes_off"]) and len(config[i]["keycodes_on"]):
        # Mode is toggle
        config[i]["mode"] = "toggle"
        # Can't be in a group
        config[i]["group"] = None
    # This is a grouped pad ?
    if config[i]["group"] != None and len(config[i]["keycodes_on"]):
        # Mode is group
        config[i]["mode"] = "group"
    # This is a key pad ?
    if config[i]["mode"] == None and len(config[i]["keycodes_on"]):
        # Mode is key
        config[i]["mode"] = "key"
    # This key has not got a mode ?
    if config[i]["mode"] == None:
        # Set LED value to min (not lit)
        config[i]["val"] = VAL_MIN

if not BLE_LIVE:
    # Set up the USB keyboard and layout
    keyboard = Keyboard(usb_hid.devices)
    layout = KeyboardLayoutUS(keyboard)

else:
    # Setup the BLE keyboard and layout
    hid = HIDService()
    device_info = DeviceInfoService(software_revision=adafruit_ble.__version__,
                                    manufacturer="marjohloo")
    advertisement = ProvideServicesAdvertisement(hid)
    # Advertise as "Keyboard" (0x03C1) icon when pairing
    # https://www.bluetooth.com/specifications/assigned-numbers/
    advertisement.appearance = 961
    scan_response = Advertisement()
    scan_response.complete_name = "Neotrellis BLE Keyboard"
    ble = adafruit_ble.BLERadio()
    if not ble.connected:
        print("BLE intialise advertising")
        ble.start_advertising(advertisement, scan_response)
    else:
        print("BLE initialise already connected")
        print(ble.connections)
    keyboard = Keyboard(hid.devices)
    layout = KeyboardLayoutUS(keyboard)

# Main loop
while True:
    # call the sync function call any triggered callbacks
    trellis.sync()
    # the trellis can only be read every 17 millisecons or so
    time.sleep(0.02)
    # Loop through pads
    for i in range(16):
        # Start with LED off
        h = 0.0
        s = 0.0
        v = 0.0
        # No mode ?
        if config[i]["mode"] == None:
            # Turn off LED
            trellis.pixels[i] = (0, 0, 0)
        # Pad has a mode ?
        else:
            # Pad is down ?
            if config[i]["down"]:
                # Normal or grouped pad
                if config[i]["mode"] == "key" or config[i]["mode"] == "group":
                    # Go to full brightness
                    config[i]["val"] = v = VAL_MAX
                # Toggle pad?
                elif config[i]["mode"] == "toggle":
                    # Toggled on ?
                    if config[i]["on"]:
                        # Go to full brightness
                        config[i]["val"] = v = VAL_MAX
                    # Toggled off ?
                    else:
                        # Go to min brightness
                        config[i]["val"] = v = VAL_MIN
            # Pad is not down
            else:
                # Pad is on
                if config[i]["on"]:
                    # Set target on brightness
                    v = VAL_ON
                # Pad is off ?
                else:
                    # Set target off brightness
                    v = VAL_OFF
            # Target value above current value ?
            if v > config[i]["val"]:
                # Move towards target
                if v - config[i]["val"] > VAL_STEP:
                    config[i]["val"] += VAL_STEP
                else:
                    config[i]["val"] = v
            # Target value below current value
            elif v < config[i]["val"]:
                # Move towards target
                if config[i]["val"] - v > VAL_STEP:
                    config[i]["val"] -= VAL_STEP
                else:
                    config[i]["val"] = v
            # Pad has a hue ?
            if config[i]["hue"] is not None:
                # Set full saturation
                s = 1.0
                # Set hue
                h = config[i]["hue"]
            else:
                s = 0.0
                h = 0.0
            # Convert the hue to RGB values.
            r, g, b = hsv_to_rgb(h, s, config[i]["val"])
            # Finally set the LED
            trellis.pixels[i] = (r, g, b)

    if BLE_LIVE:
        if not ble.connected:
            if not ble.advertising:
                print("BLE reconnect advertising")
                ble.start_advertising(advertisement, scan_response)