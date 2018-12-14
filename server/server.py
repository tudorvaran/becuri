#!/usr/bin/env python3
import cherrypy
import hashlib
import os
import queue
import threading

from cherrypy.lib import auth_digest

comm = {
    'running': True
}

class Controller(threading.Thread):
    def __init__(self, queue):
        self.queue = queue
        threading.Thread.__init__(self)

    def check_updates(self):
        pass

class Site(object):
    @cherrypy.expose
    def index(self):
        return """
        Test a configuration:
        <form action="uploadfile" method="post" enctype="multipart/form-data">
            filename: <input type="file" name="file" /><br />
            <input type="submit" />
        </form>
        """

    @cherrypy.expose
    def uploadfile(self, file):
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
        name = '%s-%s' % (cherrypy.request.login, hashlib.md5(data).hexdigest())
        path = os.path.join(os.getcwd(), 'temp', name)
        with open(path, 'wb') as out:
            out.write(data)

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
        '/': {
            'tools.auth_digest.on': True,
            'tools.auth_digest.realm': 'Bradut',
            'tools.auth_digest.get_ha1': auth_digest.get_ha1_dict_plain(userpassdict),
            'tools.auth_digest.key': 'randomsecret',
            'tools.auth_digest.accept_charset': 'UTF-8'
        },
        '/log': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(os.getcwd(), 'server.log')
        }
    }
    cherrypy.quickstart(Site(), '/', config)