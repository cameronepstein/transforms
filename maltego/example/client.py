#!/usr/bin/env python

import maltego
import sys
import optparse

class Client(object):
    def __init__(self, url):
        self.client = maltego.Client()
        self.client.connect( url )

    def do_list(self):
        for k,v in self.client.transforms.items():
            print "    %s (%s) -> %s" % (k, v.input, v.output)
    def do_transform(self, tname, *args):
        trans = self.client.transforms[tname]
        name = trans.input

        entities = []

        for val in args:
            ent = maltego.Entity(name=name, value=val)
            entities.append( ent )

        entities = trans.transform(entities)

        for ent in entities:
            print ent.value

def main(argv):
    parser = optparse.OptionParser()

    parser.add_option('-u', '--url', dest="url", help="Transform URL",
            default='http://localhost:9999')
    parser.add_option('-l', '--list', dest="cmd", action="store_const",
            const="list", default="list", help="List available Transforms")
    parser.add_option('-t', '--transform', dest="cmd", action="store_const",
            const="transform", help="Run Transform: <TransformToRun> <Value>")
    options, args = parser.parse_args(argv)

    if len(argv) == 1:
        options.url = argv[0]
    # need posistional arguements... wtf!

    client = Client(options.url)

    if options.cmd == 'list':
        client.do_list()
    elif options.cmd == 'transform':
        if len(args) < 2:
            print "transform requires TransformToRun <Value 1>[... <Value n>]"
            return
        tr_name = args[0]
        vals = args[1:]
        client.do_transform(tr_name, *vals)

if __name__ == '__main__':
    main(sys.argv[1:])
