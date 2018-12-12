import struct
import zlib

data = zlib.decompress(open('pixels.txt', 'rb').read())

offset = 0
while True:
    by = struct.unpack_from('>I', data, offset)[0]
    cmd = by >> 24
    r = by >> 16 & 0xff
    g = by >> 8 & 0xff
    b = by & 0xff
    if cmd == 0xF0:
        print 'pixels.fill((%d, %d, %d))' % (r, g, b)
    elif cmd == 0xD0:
        print 'pixels.sleep(%d)' % ((r << 16) + (g << 8) + b)
    else:
        print 'pixels[%d] = (%d, %d, %d)' % (cmd, r, g, b)

    offset += 4
    if offset >= len(data):
        break
