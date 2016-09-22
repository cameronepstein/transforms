#!/usr/bin/env python
#
# (c) 2007,2008 the grugq <the.grugq@gmail.com>


import application

class TransformProxy(object):
    def __init__(self, channel, trans):
        self._channel = channel
        self._trans = trans
    def transform(self, entities, key=None, fields={}, limits=(None, None)):
        msg = self._channel.run_transform(self._trans.name, entities, key,
                fields, limits)
        return msg.entities
    def __getattr__(self, name):
        return getattr(self._trans, name)

class Client(object):
    """Maltego Transform Client

    Client makes the transforms hosted on a transform application appear local
    Something like a Transform Proxy container
    """
    def __init__(self, *args):
        self.transforms = {}
        for url in args:
            self.connect(url)

    def load_transforms(self, channel):
        msg = channel.list_transforms()
        for trans in msg.transforms:
            trproxy = TransformProxy(channel, trans)
            self.transforms[trproxy.name] = trproxy
    def connect(self, url):
        '''Connect to a Transform Application and load the list of transforms
        
        Can be called multiple times with different URLs, each new channel
        will be exposed via a TransformProxy '''
        chan = application.Channel(url)
        self.load_transforms(chan)
    def list_transforms(self):
        return self.transforms.keys()
    def __getattr__(self, name):
        try:
            return self.transforms[name]
        except KeyError:
            raise AttributeError("No such attribute: %s" % name)
