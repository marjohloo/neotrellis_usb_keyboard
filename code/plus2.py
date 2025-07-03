# Imports (built in)
import board
import digitalio
import terminalio

# Imports (bundle)
from adafruit_display_text import label

from adafruit_debouncer import Debouncer # Requires adafruit_ticks

import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# INITIALISE
print("M5Stack StickC PLUS2 v0.0.1")
print("Initialising")
bleEnabled = False
hardware = {}

# Display
print("Initialising display")
display = board.DISPLAY
text = f"bleEnabled={bleEnabled}"
font = terminalio.FONT
color = 0xFF00FF
text_area = label.Label(font, text=text, color=color)
text_area.x = 2
text_area.y = 4
display.root_group = text_area

# Buttons
print("Initialising buttons")
hardware["dioIn"] = {}
hardware["dioIn"]["BTN_A"] = digitalio.DigitalInOut(board.BTN_A)
hardware["dioIn"]["BTN_B"] = digitalio.DigitalInOut(board.BTN_B)
hardware["dioIn"]["BTN_C"] = digitalio.DigitalInOut(board.BTN_C)
hardware["debouncer"] = {}
for key, dioIn in hardware["dioIn"].items():
    dioIn.direction = digitalio.Direction.INPUT
    dioIn.pull = digitalio.Pull.UP
    hardware["debouncer"][key] = Debouncer(dioIn)
    
print("Initialising LEDs")
hardware["dioOut"] = {}
hardware["dioOut"]["LED"] = digitalio.DigitalInOut(board.LED)
hardware["dioOut"]["LED"].direction = digitalio.Direction.OUTPUT
hardware["dioOut"]["LED"].value = False

print("Initialising HID")
hid = HIDService()

print ("Initialising BLE")
device_info = DeviceInfoService(software_revision=adafruit_ble.__version__,
                                manufacturer="Adafruit Industries")
advertisement = ProvideServicesAdvertisement(hid)
# Advertise as "Keyboard" (0x03C1) icon when pairing
# https://www.bluetooth.com/specifications/assigned-numbers/
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"


if bleEnabled:
    ble = adafruit_ble.BLERadio()
    if not ble.connected:
        print("BLE intialise advertising")
        ble.start_advertising(advertisement, scan_response)
    else:
        print("BLE initialise already connected")
        print(ble.connections)

    k = Keyboard(hid.devices)
    kl = KeyboardLayoutUS(k)
    
    while True:
        if bleEnabled:
            print ("BLE not connected loop")
            while not ble.connected:
                pass

            print("BLE connected loop")
            while ble.connected:
                for key, debouncer in hardware["debouncer"].items():
                    debouncer.update()
                    if debouncer.fell:
                        print(f"Debouncer {key} pressed")
                        hardware["dioOut"]["LED"].value = True
                        if key is "BTN_A":                   
                            k.send(Keycode.A)
                        elif key is "BTN_B":
                            k.send(Keycode.B)
                        elif key is "BTN_C":
                            k.send(Keycode.C)                    
                    if debouncer.rose:
                        print(f"Debouncer {key} released")
                        hardware["dioOut"]["LED"].value = False
                      
            print("BLE reconnect advertising")
            ble.start_advertising(advertisement, scan_response)
            
if not bleEnabled:
    print("BLE disabled")
    while True:
        for key, debouncer in hardware["debouncer"].items():
            debouncer.update()
            if debouncer.fell:
                print(f"Debouncer {key} pressed")
                hardware["dioOut"]["LED"].value = True
                if key is "BTN_A":                   
                    pass
                elif key is "BTN_B":
                    pass
                elif key is "BTN_C":
                    pass                   
            if debouncer.rose:
                print(f"Debouncer {key} released")
                hardware["dioOut"]["LED"].value = False
        
    
