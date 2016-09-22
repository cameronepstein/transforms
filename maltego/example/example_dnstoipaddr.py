#!/usr/bin/env python

from wsgiref.simple_server import make_server
import sys
import socket

import maltego

class DNSToIPAddress(maltego.Transform):
    def __init__(self):
        super(DNSToIPAddress, self).__init__(
                displayname = "DNS to IP Address",
                author = "thegrugq <thegrugq@gmail.com>",
                input = maltego.DNSName,
                output = maltego.IPAddress,
                version = "1.0.1a build 53b"
                )

    def transform(self, entities, key=None, fields={}, limits=(None,None)):
        retlist = []
        for dns in entities:
            ip = socket.gethostbyname(dns.value)
            retlist.append( maltego.IPAddress( ip ) )
        return retlist
        # the one line list comprehension version:
        #return [maltego.IPAddress(socket.gethostbyname(d.value)) for d in entities]

def main(argv):
    app = maltego.Application(debuglog="/tmp/log.txt")

    app += DNSToIPAddress()

    server = make_server('', 9999, app)

    server.serve_forever()
    #server.handle_request()

if __name__ == '__main__':
    main(sys.argv[1:])
