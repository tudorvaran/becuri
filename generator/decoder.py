import struct
import sys
import zlib

if len(sys.argv) != 2:
    print('Usage: %s' % sys.argv[0])

data = zlib.decompress(open(sys.argv[1], 'rb').read())

PIXEL_NUM = 50
offset = 0
while True:
    bdata = struct.unpack_from('>I', data, offset)[0]
    cmd = bdata >> 24
    if bdata == 0xdeadbeef:
        print('pixels.commit()')
    elif cmd == 0xd0:
        print('pixels.sleep(%d)' % (1000 if (bdata & 0xffffff) > 1000 else (bdata & 0xffffff)))
    else:
        r = bdata >> 16 & 0xff
        g = bdata >> 8 & 0xff
        b = bdata & 0xff
        if cmd == 0xf0:
            print('pixels.fill((%d, %d, %d))' % (r, g, b))
        elif cmd < PIXEL_NUM:
            print('pixels[%d] = (%d, %d, %d)' % (cmd, r, g, b))

    offset += 4
    if offset >= len(data):
        break
