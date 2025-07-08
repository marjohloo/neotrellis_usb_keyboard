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
from analogio import AnalogIn

# Libraries (bundle)
from adafruit_neotrellis.neotrellis import NeoTrellis # requires adafruit_seesaw/

import neopixel # requires adafruit_pixelbuf.mpy

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

# LED Values (brightness)
VAL_SPLIT = (1.0/32.0)
VAL_MIN   = (VAL_SPLIT *  0.0)
VAL_OFF   = (VAL_SPLIT *  2.0)
VAL_ON    = (VAL_SPLIT * 30.0)
VAL_MAX   = (VAL_SPLIT * 32.0)
VAL_STEP  = 0.00005

# Voltage colors
VOLTAGE_RED     = 3.2
VOLTAGE_GREEN   = 4.2

# Battery settings
VOLTAGE_PERIOD = 10.0 # in seconds

# Key configuration data
#
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

# Presses a list of keycodes
def press_keycodes(kcs):
    print(f'press_keycodes({kcs}), KC_LIVE={KC_LIVE}, ble.connected={ble.connected}')
    if KC_LIVE and ble.connected:
        if len(kcs) == 1:
            keyboard.press(kcs[0])
        elif len(kcs) == 2:
            keyboard.press(kcs[0], kcs[1])
        elif len(kcs) == 3:
            keyboard.press(kcs[0], kcs[1], kcs[2])

# Releases a list of keycodes
def release_keycodes(kcs):
    print(f'release_keycodes({kcs}), KC_LIVE={KC_LIVE}, ble.connected={ble.connected}')
    if KC_LIVE and ble.connected:
        if len(kcs) == 1:
            keyboard.release(kcs[0])
        elif len(kcs) == 2:
            keyboard.release(kcs[0], kcs[1])
        elif len(kcs) == 3:
            keyboard.release(kcs[0], kcs[1], kcs[2])

# Keypad event callback
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

# Convert HSV to RGB
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

def linear_scale(source_value, source_min, source_max, target_min, target_max):
    """
    Linearly scale a value from one range to another.

    Args:
        source_value (float): The value to be scaled.
        source_min (float): The minimum value of the source range.
        source_max (float): The maximum value of the source range.
        target_min (float): The minimum value of the target range.
        target_max (float): The maximum value of the target range.

    Returns:
        float: The scaled value in the target range.
    """
    return (source_value - source_min) * (target_max - target_min) / (source_max - source_min) + target_min

def get_voltage():
    # Get pin value
    value = voltage_pin.value
    # Calculate voltage
    voltage = (value * 3.3) / 65536 * 2
    # Calculate voltage hue and percentage
    if voltage <= VOLTAGE_RED:
        voltage_hue = hue["red"]
        voltage_percent = 0
    elif voltage <= VOLTAGE_GREEN:
        voltage_hue = linear_scale(voltage, VOLTAGE_RED, VOLTAGE_GREEN, hue["red"], hue["green"])
        voltage_percent = int(linear_scale(voltage, VOLTAGE_RED, VOLTAGE_GREEN, 0, 100))
    else:
         voltage_hue = hue["green"]
         voltage_percent = 100
    # Convert the hue to RGB values.
    r, g, b = hsv_to_rgb(voltage_hue, 1.0, 1.0)
    # Finally set the LED
    neopixel[0] = (r, g, b)
    # Calculate coltage percentage
    print(f'value={value}, voltage={voltage}, voltage_percent={voltage_percent}, voltage_hue={voltage_hue}')
    # Set timer
    return time.monotonic() + VOLTAGE_PERIOD

# BLE disonnected pixel loops
ble_not_advertising_pixels = [5, 6, 9, 10] # Inner 4
ble_advertising_pixels = [0, 1, 2, 3, 7, 11, 15, 14, 13, 12, 8, 4] # Outer 12
ble_advertising_pixel_index = 0

# Set up I2C for neotrellis
i2c_bus = board.I2C()  # uses board.SCL and board.SDA
# Set up neotrellis
trellis = NeoTrellis(i2c_bus)
trellis.brightness = 1.0
# Turn on start up pixel
r, g, b = hsv_to_rgb(hue["red"], 1.0, VAL_OFF)
trellis.pixels[ble_advertising_pixels[0]] = (r, g, b)
time.sleep(0.05)

# Setup on-board neopixel
neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=(VAL_OFF/2), auto_write=True)
neopixel[0] = (255, 255, 255)
trellis.pixels[ble_advertising_pixels[1]] = (r, g, b)
time.sleep(0.05)

# Initial battery measurement
voltage_pin = AnalogIn(board.VOLTAGE_MONITOR)
voltage_timer = get_voltage()
trellis.pixels[ble_advertising_pixels[2]] = (r, g, b)
time.sleep(0.05)

# Setup the BLE keyboard and layout
ble_connected = None
hid = HIDService()
trellis.pixels[ble_advertising_pixels[3]] = (r, g, b)
time.sleep(0.05)
device_info = DeviceInfoService(
    manufacturer="Adafruit",
    software_revision=adafruit_ble.__version__,
    model_number="NeoTrellis nRF52840",
    serial_number="20250704",
    firmware_revision="0.0.5",
    hardware_revision="0.0.1")
trellis.pixels[ble_advertising_pixels[4]] = (r, g, b)
time.sleep(0.05)
advertisement = ProvideServicesAdvertisement(hid)
# Advertise as "Keyboard" (0x03C1) icon when pairing
# https://www.bluetooth.com/specifications/assigned-numbers/
advertisement.appearance = 961
trellis.pixels[ble_advertising_pixels[5]] = (r, g, b)
time.sleep(0.05)
scan_response = Advertisement()
scan_response.shortname = "NeoTrellisSN"
scan_response.complete_name = "NeoTrellisCN"
trellis.pixels[ble_advertising_pixels[6]] = (r, g, b)
time.sleep(0.05)
ble = adafruit_ble.BLERadio()
print(f'init: ble.connected={ble.connected}, ble.advertising={ble.advertising}')
ble.stop_advertising()
ble.name = "NeoTrellisN"
trellis.pixels[ble_advertising_pixels[7]] = (r, g, b)
time.sleep(0.05)
keyboard = Keyboard(hid.devices)
trellis.pixels[ble_advertising_pixels[8]] = (r, g, b)
time.sleep(0.05)
layout = KeyboardLayoutUS(keyboard)
trellis.pixels[ble_advertising_pixels[9]] = (r, g, b)
time.sleep(0.05)

# Add runtime data to config
for p in range(16):
    # Defaults
    # Mode is none
    config[p]["mode"] = None
    # Set LED value to max
    config[p]["val"] = VAL_MAX
    # Not down
    config[p]["down"] = False
    # Not on
    config[p]["on"] = False
    # This is a toggle pad ?
    if config[p]["keycodes_off"] != None and config[p]["keycodes_on"] != None and len(config[p]["keycodes_off"]) and len(config[p]["keycodes_on"]):
        # Mode is toggle
        config[p]["mode"] = "toggle"
        # Can't be in a group
        config[p]["group"] = None
    # This is a grouped pad ?
    if config[p]["group"] != None and len(config[p]["keycodes_on"]):
        # Mode is group
        config[p]["mode"] = "group"
    # This is a key pad ?
    if config[p]["mode"] == None and len(config[p]["keycodes_on"]):
        # Mode is key
        config[p]["mode"] = "key"
    # This key has not got a mode ?
    if config[p]["mode"] == None:
        # Set LED value to min (not lit)
        config[p]["val"] = VAL_MIN
    print(f'key={p}, mode={config[p]["mode"]}')
trellis.pixels[ble_advertising_pixels[10]] = (r, g, b)
time.sleep(0.05)

# Setup Neotrellis key callbacks
for p in range(16):
    # activate rising edge events on key
    trellis.activate_key(p, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all key
    trellis.activate_key(p, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the callback
    trellis.callbacks[p] = key_event
trellis.pixels[ble_advertising_pixels[11]] = (r, g, b)
time.sleep(0.05)

# Main loop
while True:

    # Time to measure battery ?
    now = time.monotonic()
    if now >= voltage_timer:
        voltage_timer = get_voltage()
        print(f'timer: ble.connected={ble.connected}, ble.advertising={ble.advertising}')

    # Connection debugging
    if ble_connected != ble.connected:
        ble_connected = ble.connected
        print(f'conchange: ble.connected={ble.connected}, ble.advertising={ble.advertising}')

    # BLE is connected? Update advertising
    if ble.connected:
        # BLE is advertising ?
        if ble.advertising:
            print(f'ble.stop_advertising()')
            ble.stop_advertising()
    # BLE is not connected ? Update advertising
    else:
        # BLE is advertising ?
        if ble.advertising:
            pass
        # BLE not advertising ?
        else:
            # Start advertising ?
            print(f'ble.start_advertising()')
            ble.start_advertising(advertisement, scan_response)

    # call the sync function call any triggered callbacks
    trellis.sync()
    # the trellis can only be read every 17 millisecons or so
    time.sleep(0.02)

    # BLE connected? Update Neotrellis LEDs
    if ble.connected:
        # Normal operation
        if True:
            # Loop through pads
            for p in range(16):
                # Start with LED off
                h = 0.0
                s = 0.0
                v = 0.0
                # No mode ?
                if config[p]["mode"] == None:
                    # Turn off LED
                    trellis.pixels[i] = (0, 0, 0)
                # Pad has a mode ?
                else:
                    # Pad is down ?
                    if config[p]["down"]:
                        print(f'key {p} is down, mode is {config[p]["mode"]}, on is {config[p]["on"]}')
                        # Normal or grouped pad
                        if config[p]["mode"] == "key" or config[p]["mode"] == "group":
                            # Go to full brightness
                            config[p]["val"] = v = VAL_MAX
                        # Toggle pad?
                        elif config[p]["mode"] == "toggle":
                            print("toggle down")
                            # Toggled on ?
                            if config[p]["on"]:
                                # Go to full brightness
                                config[p]["val"] = v = VAL_MAX
                                print("toggle down max")
                            # Toggled off ?
                            else:
                                # Go to min brightness
                                config[p]["val"] = v = VAL_MIN
                                print("toggle down min")
                    # Pad is not down
                    else:
                        # Pad is on
                        if config[p]["on"]:
                            # Set target on brightness
                            v = VAL_ON
                        # Pad is off ?
                        else:
                            # Set target off brightness
                            v = VAL_OFF
                    # Step by eighths
                    if True:
                        # Target value above current value ?
                        if v > config[p]["val"]:
                            step = (v - config[p]["val"]) / 16
                            # Move towards target
                            if step > VAL_STEP:
                                config[p]["val"] += step
                            else:
                                config[p]["val"] = v
                        # Target value below current value
                        elif v < config[p]["val"]:
                            step = (config[p]["val"] - v) / 16
                            # Move towards target
                            if step > VAL_STEP:
                                config[p]["val"] -= step
                            else:
                                config[p]["val"] = v
                    # Step by fixed amount
                    else:
                        # Target value above current value ?
                        if v > config[p]["val"]:
                            # Move towards target
                            if v - config[p]["val"] > VAL_STEP:
                                config[p]["val"] += VAL_STEP
                            else:
                                config[p]["val"] = v
                        # Target value below current value
                        elif v < config[p]["val"]:
                            # Move towards target
                            if config[p]["val"] - v > VAL_STEP:
                                config[p]["val"] -= VAL_STEP
                            else:
                                config[p]["val"] = v
                    # Pad has a hue ?
                    if config[p]["hue"] is not None:
                        # Set full saturation
                        s = 1.0
                        # Set hue
                        h = config[p]["hue"]
                    else:
                        s = 0.0
                        h = 0.0
                    # Convert the hue to RGB values.
                    r, g, b = hsv_to_rgb(h, s, config[p]["val"])
                    # Finally set the LED
                    trellis.pixels[p] = (r, g, b)
        # Test operation
        else:
            # Cycle BLE advertising pixels dim red
            if ble_advertising_pixel_index >= len(ble_advertising_pixels):
                ble_advertising_pixel_index = 0
            r, g, b = hsv_to_rgb(hue["red"], 1.0, VAL_OFF)
            for p in range(16):
                if p == ble_advertising_pixels[ble_advertising_pixel_index]:
                    trellis.pixels[p] = (r, g, b)
                else:
                    trellis.pixels[p] = (0, 0, 0)
            ble_advertising_pixel_index += 1
    # BLE not connected? Update Neotrellis LEDs
    else:
        # Advertising
        if ble.advertising:
            # Cycle BLE advertising pixels
            if ble_advertising_pixel_index >= len(ble_advertising_pixels):
                ble_advertising_pixel_index = 0
            r, g, b = hsv_to_rgb(hue["blue"], 1.0, VAL_OFF)
            for p in range(16):
                if p == ble_advertising_pixels[ble_advertising_pixel_index]:
                    trellis.pixels[p] = (r, g, b)
                else:
                    trellis.pixels[p] = (0, 0, 0)
            ble_advertising_pixel_index += 1
        # Not advertising
        else:
            # Cycle BLE not advertising pixels
            if ble_advertising_pixel_index >= len(ble_not_advertising_pixels):
                ble_advertising_pixel_index = 0
            r, g, b = hsv_to_rgb(hue["blue"], 1.0, VAL_OFF)
            for p in range(16):
                if p == ble_not_advertising_pixels[ble_advertising_pixel_index]:
                    trellis.pixels[p] = (r, g, b)
                else:
                    trellis.pixels[p] = (0, 0, 0)
            ble_advertising_pixel_index += 1

