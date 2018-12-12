#!/usr/bin/env
import math
import struct
import zlib

class NeoPixel:
    def __init__(self, num_px, filename):
        self.num_px = num_px
        self.filename = filename

        self.bpp = 3
        self.buf = bytearray(self.num_px * self.bpp) # 3 bytes per pixel
        self.last_buf = self.buf[:]

        self.fd = open(self.filename, 'wb')
        self.data = ''

    def __enter__(self):
        return self

    def _set_item(self, index, value):
        if index < 0:
            index += len(self)
        if index >= self.num_px or index < 0:
            raise IndexError
        offset = index * self.bpp
        r = g = b = 0
        if isinstance(value, int):
            if value >> 24:
                raise ValueError("only bits 0->23 valid for integer input")
            r = value >> 16
            g = (value >> 8) & 0xff
            b = value & 0xff
        elif (len(value) == self.bpp):
            r, g, b = value
        else:
            raise ValueError("Color tuple size does not match pixel_order.")
        self.buf[offset] = r
        self.buf[offset + 1] = g
        self.buf[offset + 2] = b

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self.buf) // self.bpp)
            length = stop - start
            if step != 0:
                length = math.ceil(length / step)
            if len(value) != length:
                raise ValueError("Slice and input sequence size do not match.")
            for value_i, index_i in enumerate(range(start, stop, step)):
                self._set_item(index_i, value[value_i])
        else:
            self._set_item(index, value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            out = []
            for index_i in range(*index.indices(len(self.buf) // self.bpp)):
                out.append(tuple(self.buf[index_i * self.bpp + i] for i in range(self.bpp)))
            return out
        if index < 0:
            index += len(self)
        if index >= self.num_px or index < 0:
            raise IndexError
        offset = index * self.bpp
        return tuple(self.buf[offset + i] for i in range(self. bpp))
    
    def commit(self):
        """ Commit pixel state to be sent to LEDs. """
        def get_rgb(index, buf):
            return buf[index * self.bpp], buf[index * self.bpp + 1], buf[index * self.bpp + 2]

        if self.buf[:] == self.last_buf[:]:
            return
        for p in range(self.num_px):
            r, g, b = get_rgb(p, self.buf)
            lr, lg, lb = get_rgb(p, self.last_buf)
            if r == lr and g == lg and b == lb:
                continue
            self.data += struct.pack('>I', (p << 24) + (r << 16) + (g << 8) + b)
        self.last_buf = self.buf[:]

    def fill(self, value):
        """ Colors all pixels with the given color. Fill also commits. """
        # Fill all leds
        for i, _ in enumerate(self):
            self[i] = value
        # Extract RGB value 
        r = g = b = 0
        if isinstance(value, int):
            if value >> 24:
                raise ValueError("only bits 0->23 valid for integer input")
            r = value >> 16
            g = (value >> 8) & 0xff
            b = value & 0xff
        elif (len(value) == self.bpp):
            r, g, b = value
        else:
            raise ValueError("Color tuple size does not match pixel_order.")
        # Commit value
        self.data += struct.pack('>I', (0xF0 << 24) + (r << 16) + (g << 8) + b)
        self.last_buf = self.buf[:]

    def push(self):
        self.fd.write(zlib.compress(self.data, 9))
        self.fd.close()

    def sleep(self, milliseconds):
        """ Sleeps the given number of milliseconds. """
        ms = 0xD0 << 24
        ms += milliseconds % 0xffffff
        self.data += struct.pack('>I', ms)


if __name__ == '__main__':
    pass