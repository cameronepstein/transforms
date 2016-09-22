#!/usr/bin/env python

# NOTE: Requires Python >= 2.5 for the wsgiref module!

from wsgiref.simple_server import make_server
import sys
import maltego

def main(argv):
    host = ''
    port = 9999

    if argv:
        host, port = argv[0], int(argv[1])

    app = maltego.Application()

    server = make_server(host, port, app)

    #server.server_forever()
    server.handle_request()

if __name__ == '__main__':
    main(sys.argv[1:])
