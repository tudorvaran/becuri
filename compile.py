import os
import sys
import traceback
import zlib
from importlib import import_module

from neopixel2 import Neopixel
from interpretor import NeoPixelInterpretor

NUM_PX = 100


def main(filename, verbose=True):
    filepath = os.path.join("programs", f"{filename}.leds")
    pixels = Neopixel(NUM_PX, filepath)

    try:
        tree_module = import_module(f"programs.{filename}")
        tree_module.main(pixels)
    except KeyboardInterrupt as e:
        traceback.format_exc(e)
        pixels.fill((0, 0, 0))
    finally:
        pixels.save()

    if verbose:
        interpretor = NeoPixelInterpretor([(0, 0, 0) for _ in range(NUM_PX)])
        interpretor.run(zlib.decompress(open(filepath, 'rb').read()), mock=True, verbose=True)


if len(sys.argv) < 2:
    print(f"Usage python3 {sys.argv[0]} < module")
else:
    main(sys.argv[1])
