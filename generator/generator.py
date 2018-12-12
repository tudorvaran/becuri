#!/usr/bin/env python
"""
Script care genereaza secventa pentru luminat becuri
"""

import neopixel

pixels = neopixel.NeoPixel(50, 'pixels.txt')

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos*3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos*3)
        g = 0
        b = int(pos*3)
    else:
        pos -= 170
        r = 0
        g = int(pos*3)
        b = int(255 - pos*3)
    return (r, g, b)

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(50):
            pixel_index = (i * 256 // 50) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.commit()
        pixels.sleep(wait)


for i in range(100):
    pixels.fill((0x10, 0x20, 0x30))
    pixels.sleep(4000)
rainbow_cycle(1000)
pixels.push()