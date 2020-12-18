import os
import sys
import traceback
from importlib import import_module

from neopixel2 import Neopixel

NUM_PX = 100


def main(filename, verbose=False):
    filepath = os.path.join("programs", f"{filename}.leds")
    pixels = Neopixel(NUM_PX, filepath, verbose)
    found_module = False

    try:
        tree_module = import_module(f"programs.{filename}")
        found_module = True
        tree_module.main(pixels)
    except KeyboardInterrupt:
        pixels.fill((0, 0, 0))
    except ModuleNotFoundError as e:
        print(f"Python program module {filename} does not exist!")
    finally:
        if found_module:
            pixels.save()


if len(sys.argv) < 2:
    print(f"Usage python3 {sys.argv[0]} <module> [-v]")
else:
    main(*sys.argv[1:])
