#!/usr/bin/env python3
"""
Script care genereaza secventa pentru luminat becuri
"""

import neopixel
import random

pixels = neopixel.NeoPixel(50, 'pixels2.txt')

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

def rainbow(wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(50):
            pixels[i] = wheel((i + j) & 255)
        pixels.commit()
        pixels.sleep(wait_ms)

def rainbow_cycle(wait_ms=20, iterations=5):
    for j in range(256 * iterations):
        for i in range(50):
            pixels[i] = wheel(((i * 256 // 50) + j) & 255)
        pixels.commit()
        pixels.sleep(wait_ms)

def theater_chase_rainbow(wait_ms=50):
    for j in range(256):
        for q in range(3):
            for i in range(0, 50, 3):
                if i + q >= 50:
                    continue
                pixels[i + q] = wheel((i + j) & 255)
            pixels.commit()
            pixels.sleep(wait_ms)
            for i in range(0, 50, 3):
                if i + q >= 50:
                    continue
                pixels[i + q] = 0

def crazy(wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(50):
            pixels[i] = wheel(random.randint(0, 255))
        pixels.commit()
        pixels.sleep(wait_ms)


def theater_chase(color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, 50, 3):
                if i + q >= 50:
                    continue
                pixels[i + q] = color
            pixels.commit()
            pixels.sleep(wait_ms)
            for i in range(0, 50, 3):
                if i + q >= 50:
                    continue
                pixels[i + q] = color

try: 
    for i in range(1):
        # print ('Color wipe animations.')
        # pixels.fill((255, 0, 0))
        # pixels.commit()
        # pixels.sleep(1)
        # pixels.fill((0, 255, 0))
        # pixels.commit()
        # pixels.sleep(1)
        print ('Theater chase animations.')
        theater_chase((127, 127, 127))
        theater_chase((127, 0, 0))
        theater_chase((0, 0, 127))
        print ('Rainbow animations.')
        rainbow()
        rainbow_cycle()
        theater_chase_rainbow()
        print ('Crazy animation.')
        crazy(wait_ms=20, iterations=10)

except KeyboardInterrupt:
    pixels.fill((0, 0, 0))
    pixels.commit()

pixels.push()