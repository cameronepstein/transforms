#!/usr/bin/env python

import sys
import os

import maltego

# If you have transform files, put them here..
# import mymodule.mytransform
# 

class MyTransform(maltego.Transform):
    def __init__(self):
        super(MyTransform, self).__init__(
                displayname="My Transform",
                author="me <myself@_I_.com>",
                input=maltego.DNSName,
                output=maltego.DNSName,
                )
    def transform(self, entities, key=None, fields={}, limits=(None,None)):
        return entities # ECHO test 

application = maltego.Application()
application.register( MyTransform() )

def main(argv):
    """transform_app QUERY_STRING,
    POST_DATA is read from STDIN"""
    def start_response(status, headers):
        pass

    qs = argv[0]

    environ = {'QUERY_STRING' : qs }

    postdata = os.tmpfile()
    postdata.write( sys.stdin.read() )
    environ['CONTENT_LENGTH'] =  str(postdata.tell())

    postdata.seek(0)
    environ['wsgi.input'] = postdata

    data = application(environ, start_response)

    for s in data:
        print s

if __name__ == "__main__":
    main(sys.argv[1:])
