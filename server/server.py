#!/usr/bin/env python3
import cherrypy
import hashlib
import os
import queue
import struct
import threading
import time
import zlib

from cherrypy.lib import auth_digest

import neopixel
import board

comm_sem = threading.Semaphore()
comm = {
    'running': True,
    'shutdown': True,
    'test': {
        'testing': False,
        'filename': ''
    }
}

class Controller(threading.Thread):
    def __init__(self):
        # Pixels variables
        self.npx = 50
        self.pixels = neopixel.NeoPixel(board.D18, self.npx, brightness=1.0, auto_write=False, pixel_order=neopixel.RGB)

        # Main animations variables
        self.anim_data = zlib.decompress(open(os.path.join(os.getcwd(), 'animations', 'None-9102dc52ecd6d3377fc3e7a7fe535401'), 'rb').read())

        # Testing animations variables
        self.tmp_fd = None

        # Other variables
        self.conf = None
        
        self.anim_startup()

        threading.Thread.__init__(self)

    def run(self):
        while True:
            comm_sem.acquire()
            global comm
            self.conf = comm.copy()
            comm_sem.release()

            # Check if we should show anything
            if not self.conf['running']:
                time.sleep(1)
                continue

            # Check if we should shutdown
            if self.conf['shutdown']:
                self.anim_shutdown()
                return

        offset = 0
        while True:
            bdata = struct.unpack_from('>I', self.anim_data, offset)[0]
            cmd = bdata >> 24
            if bdata == 0xdeadbeef:
                self.pixels.show()
            elif cmd == 0xd0:
                # print('sleep')
                time.sleep((bdata & 0xffffff) / 1000)
            else:
                r = bdata >> 16 & 0xff
                g = bdata >> 8 & 0xff
                b = bdata & 0xff
                if cmd == 0xf0:
                    # print('pixels.fill((%d, %d, %d))' % (r, g, b))
                    self.pixels.fill((r, g, b))
                elif cmd < self.npx:
                    # print('pixels[%d] = (%d, %d, %d)' % (cmd, r, g, b))
                    self.pixels[cmd] = (r, g, b)
            offset += 4
            # print(offset)
            if offset >= len(self.anim_data):
                offset = 0

    def check_updates(self):
        pass

    ##############
    # ANIMATIONS #
    ##############
    def anim_startup(self):
        def pushpx(i):
            self.pixels.fill((0, 0, 0))
            for j in range(i):
                self.pixels[j] = (0, 255, 0)
            self.pixels.show()
            time.sleep(0.05)
        for i in range(self.npx):
            pushpx(i)
        for i in range(self.npx, 0, -1):
            pushpx(i)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def anim_shutdown(self):
        self.pixels.fill((255, 0, 0))
        self.pixels.show()
        time.sleep(0.5)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
        time.sleep(0.5)
        self.pixels.fill((255, 0, 0))
        self.pixels.show()
        time.sleep(0.5)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
        time.sleep(0.5)
        self.pixels.fill((255, 0, 0))
        self.pixels.show()
        time.sleep(1)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

            

class Site(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/index.html')

    def writefile(self, file, out_dir):
        data = b''
        size = 0
        while True:
            d = file.file.read(8192)
            size += len(d)
            data += d
            if size > 50*1024*1024: # 50MB limit
                break # TODO: implement error handling
            if not d:
                break
        path = os.path.join(os.getcwd(), out_dir, '%s-%s' % (cherrypy.request.login, hashlib.md5(data).hexdigest()))
        with open(path, 'wb') as out:
            out.write(data)
        return path

    @cherrypy.expose
    def uploadfile(self, file, mode):
        path = None
        if mode == 'test':
            path = self.writefile(file, 'temp')
        elif mode == 'animation':
            path = self.writefile(file, 'animations')
        else:
            # TODO: error message
            return

    @cherrypy.expose
    def testanimation(self):
        pass

    @cherrypy.expose
    def uploadanimation(self):
        pass

if __name__ == "__main__":
    userpassdict = {'rbasaraba': '1234'}
    config = {
        'global': {
            'server.socket_host': '127.0.0.1',
            'server.socket_port': 8080,
            'server.thread_pool': 8
        },
        '/index.html': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(os.getcwd(), 'index.html')
        },
        '/script.js': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(os.getcwd(), 'script.js')
        },
        '/log': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(os.getcwd(), 'server.log')
        },
        '/manage': {
            'tools.auth_digest.on': True,
            'tools.auth_digest.realm': 'Bradut',
            'tools.auth_digest.get_ha1': auth_digest.get_ha1_dict_plain(userpassdict),
            'tools.auth_digest.key': 'randomsecret',
            'tools.auth_digest.accept_charset': 'UTF-8'
        },
    }
    ctrl = Controller()
    ctrl.start()
    cherrypy.quickstart(Site(), '/', config)