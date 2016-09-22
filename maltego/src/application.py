#!/usr/bin/env python
#
# (c) 2007,2008 the grugq <the.grugq@gmail.com>

import cgi
import httplib
import types
import urllib
import urlparse
import traceback

import entity
import transform
import message
import serialize

import logging
log = logging.getLogger("maltego")


class MaltegoProtocolError(serialize.error): pass

class Application(object):
    def __init__(self, debuglog = None):
        self.transforms = {}
        # TODO replace this with logging.FileHandler
        self.logfile = debuglog and open(debuglog, 'w') or None

    def log(self, data, *args, **kwargs):
        log.debug(data, *args, **kwargs)

        if self.logfile:
            self.logfile.write( "-" * 78 + '\n' )
            self.logfile.write( str(data) + '\n')
            self.logfile.flush()

    @staticmethod
    def _read_message(environ):
        n = environ.get('CONTENT_LENGTH', '0')
        if not n or n == '0':
            return ''
        return environ['wsgi.input'].read(int(n))

    def process_command(self, cgivars, msgdata):
        try:
            cmd = cgivars['Command']
        except KeyError:
            raise MaltegoProtocolError("Missing 'Command' statement!")

        try:
            handler = getattr(self, 'handle' + cmd)
        except AttributeError:
            raise MaltegoProtocolError("Unknown Command: %s" % cmd)

        return handler(cgivars, msgdata)

    def handle_PERFORMANCE(self, cgivars, data):
        self.log("_PERFORMANCE Sending:\n 100")
        return '100'

    def handle_TRANSFORMS(self, cgivars, data):
        msg = message.TransformList()
        msg.transforms.extend( self.transforms.values() )
        self.log("_TRANSFORMS Sending:\n%s" % msg)
        return msg

    def handle_RUN(self, cgivars, data):
        try:
            transname = cgivars['TransformToRun']
        except KeyError:
            raise MaltegoProtocolError("No TransformToRun")

        try:
            trans = self.transforms[transname]
        except KeyError:
            raise MaltegoProtocolError("No such Transform: %s" % transname)

        key = cgivars.get('key', None)

        msg = message.fromstring(data)
        if not isinstance(msg, message.TransformRequest):
            raise MaltegoProtocolError("Not a TransformRequest message")

        self.log('_RUN Received:\n%s' % msg)

        output = trans.transform(msg.entities, key, msg.fields,
                (msg.hardlimit, msg.softlimit))

        respmsg = message.TransformResponse()

        for obj in output:
            if isinstance(obj, entity.Entity):
                respmsg.entities.append( obj )
            elif type(obj) == type((1,)) and len(obj) == 2:
                respmsg.uimessages.setdefault(obj[0], []).append( obj[1] )
            else:
                respmsg.uimessages.setdefault('PartialError', []).append(
                    "Transform returned a bad value: %r" % obj)

        self.log('_RUN Sending:\n%s' % respmsg)
        return respmsg
		

    def __call__(self, environ, start_response):
        cgivars = dict( cgi.parse_qsl(environ['QUERY_STRING']) )
        msgdata = self._read_message(environ)

        try:
            msg = self.process_command(cgivars, msgdata)
        except Exception:
            msg = message.TransformException()
            msg.exceptions.append(traceback.format_exc())

        status = '200 OK'
        headers = [('Content-Type', 'text/plain')]
        start_response(status, headers)

        return [str(msg)]

    def append(self, trans):
        if not isinstance(trans, transform.Transform):
            raise ValueError("Not a Transform: %r" % trans)
        self.transforms[trans.__class__.__name__] = trans
    register = append

    def remove(self, trans):
        if not isinstance(trans, transform.Transform):
            raise ValueError("Not a Transform: %r" % trans)
        try:
            del self.transforms[trans.__class__.__name__]
        except KeyError:
            raise ValueError("Not a registered Transform: %s" %
                    trans.__class__.__name__)
    unregister = remove

    def __iadd__(self, other):
		# if hasattr(other, '__iter__'):
        if type(other) in (types.TupleType, types.ListType):
            for trans in other:
                self.append(trans)
        else:
            self.append(other)
        return self

    def __isub__(self, other):
        if type(other) in (tuple, list):
            for trans in other:
                self.remove(trans)
        else:
            self.remove(trans)
        return self

# Requests to a server are done over a Channel
class Channel(object):
    def __init__(self, url):
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

        if scheme == 'http':
            httpconn = httplib.HTTPConnection
        elif scheme == 'https':
            httpconn = httplib.HTTPSConnection
        else:
            raise ValueError("Only HTTP/HTTPS is supported, not: %s" % scheme)

        self._hostport = netloc.lstrip('//')
        self._conn = httpconn( self._hostport )
        self._path = path or '/'

    def request(self, *args, **kwargs):
        self._conn.request(*args, **kwargs)
        response = self._conn.getresponse()
        data = response.read()
        self._conn.close()
        return data

    def send_command(self, cmd, params={}, msg=''):
        qs = urllib.urlencode([('Command', cmd)] + params.items())

        headers = {'Content-Type':'text/xml', 'User-Agent':'PyMaltego-0.5.1'}

        if msg: msg = str(msg)

        url = self._path + '?' + qs

        data = self.request('POST', url, msg, headers)
        return data

    def get_seeds(self, url="/seed.xml"):
        data = self.request('GET', url)
        msg = message.fromstring( data )
        return msg

    def get_performance(self):
        return self.send_command('_PERFORMANCE')
    def list_transforms(self):
        data = self.send_command('_TRANSFORMS')
        return message.fromstring(data)

    def run_transform(self, transform, entities, key='', fields={},
                                                limits=(None, None)):
        if type(entities) not in (types.ListType, types.TupleType):
            entities = [entities]

        request = message.TransformRequest()
        request.entities.extend( entities )

        request.fields.update(fields)

        request.hardlimit, request.softlimit = limits
        if not request.hardlimit:
            request.hardlimit = '1000'
        if not request.softlimit:
            request.softlimit = '200'

        params = {}
        params['key'] = key != None and str(key) or ''
        params['TransformToRun'] = transform

        data = self.send_command('_RUN', params, str(request))
        resp = message.fromstring(data)

        if isinstance(resp, message.TransformException):
            excp = resp.exceptions[0]
            raise Exception(excp)
        return resp
