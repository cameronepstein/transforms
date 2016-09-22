#!/usr/bin/env python
#
# (c) 2007,2008 the grugq <the.grugq@gmail.com>

# TODO
# The serialization needs to be redone so that it is possible to just 
# construct an Entity based on incoming XML (and to serialize arbitrary
# objects to valid Maltego XML). 


from xml.dom import minidom

try: 
    import xml.etree.ElementTree as ET # in python >=2.5
except ImportError:
    try:
        import cElementTree as ET # effbot's C module
    except ImportError:
        try:
            import elementtree.ElementTree as ET #effbot's pure Python module
        except ImportError:
            try:
                import lxml.etree as ET # ElementTree API using libxml2
            except ImportError:
                raise ImportError("could not import ElementTree "
                              "(http://effbot.org/zone/element-index.htm)")

# XXX this might be a terrible long term memory leak. minidom is evil.
__doc = minidom.Document()

class error(Exception): pass

def Node(tag, text=None, attribs={}):
    node = __doc.createElement(tag)
    if text:
        node.appendChild( Text(text) )
    if attribs:
        for k,v in attribs.iteritems():
            node.attributes[k] = v
    return node

def SubNode(node, tag, *args, **kwargs):
    subnode = Node(tag, *args, **kwargs)
    node.appendChild( subnode )
    return subnode

def CData(text): return __doc.createCDATASection(str(text))

def Text(text): return __doc.createTextNode(str(text))

class XMLObject(object):
    def __init__(self, node=None):
        if node != None:
            self.load(node)
    def load(self, node):
        if not ET.iselement(node):
            raise ValueError("Is not an ElementTree Element!")
    def tonode(self):
        pass
    def toxml(self):
        #return self.tonode().toprettyxml(indent='')
        return self.tonode().toxml()
    def __str__(self):
        return self.toxml()
    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(["%s=%r"%(k,v) 
            for k,v in self.__dict__.iteritems() 
                if not k.startswith('_') and not callable(v)]))

iselement = ET.iselement
def fromstring(str):
    return ET.fromstring(str)
    #if not ET:
        # load the dom, then convert to ET type nodes, a la python recipe
    #return dom.parseString(str)
