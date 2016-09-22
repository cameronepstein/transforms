#!/usr/bin/env python
#
# (c) 2007,2008 the grugq <the.grugq@gmail.com>

import serialize

__all__ = [ 'DNSName', 'Domain', 'Document', 'EmailAddress', 'IPAddress',
            'Location', 'Netblock', 'Person', 'Phrase', 'PhoneNumber',
            'Website', 'Affiliation' ]

class UnknownEntityError(serialize.error): pass
class MalformedEntityError(serialize.error): pass

class _MetaEntity(type):
    def __new__(cls, name, bases, cdict):
        obj = type.__new__(cls, name, bases, cdict)
        if hasattr(obj, '__fields__'):
            obj._displaynames = {}
            for name, displayname in obj.__fields__:
                obj._displaynames[name] = displayname
                setattr(obj, name, _field_access(name))
        return obj

def _field_access(doc):
    def fget(self): return self.fields[doc].value
    def fset(self, value):
        if doc not in self.fields:
            self.fields[doc] = Field(name=doc)
        self.fields[doc].value = value
    def fdel(self): del(self.fields[doc])
    return property(**locals())

class Label(serialize.XMLObject):
    def __init__(self, name='', value='', mimetype="text/html", node=None):
        self.name = name
        self.value = value
        self.mimetype = mimetype
        super(Label, self).__init__(node)

    def load(self, node):
        super(Label, self).load(node)

        if node.tag != 'Label':
            raise MalformedEntityError("Not a Label! '%s'" % node.tag)
        self.name = node.attrib['Name']
        self.mimetype = node.attrib['Type']
        self.value = node.text and node.text.strip() or ''

    def tonode(self):
        node = serialize.Node('Label')
        node.attributes['Name'] = self.name
        node.attributes['Type'] = self.mimetype
        node.appendChild( serialize.CData( self.value ) )
        return node

class Field(serialize.XMLObject):
    def __init__(self, name='', value='', displayname='', matchingrule='',
                 node=None):
        self.name = name
        self.value = value
        self.displayname = displayname
        self.matchingrule = matchingrule
        super(Field, self).__init__(node)

    def load(self, node):
        super(Field, self).load(node)

        if node.tag != 'Field':
            raise MalformedEntityError("Not a Field tag: %s" % node.tag)
        self.name = node.attrib['Name']
        self.value = node.text and node.text.strip() or ''
        self.displayname = node.attrib['DisplayName']
        if 'MatchingRule' in node.attrib:
            self.matchingrule = node.attrib['MatchingRule']

    def tonode(self):
        node = serialize.Node('Field', self.value)
        node.attributes['Name'] = self.name
        node.attributes['DisplayName'] = self.displayname
        if self.matchingrule:
            node.attributes['MatchingRule'] = self.matchingrule
        return node

class Entity(serialize.XMLObject):
    __metaclass__ = _MetaEntity
    __fields__ = [] 
    def __init__(self, value='', *args, **kwargs):
        ll = [n for n,nd in self.__fields__] + ['node', 'iconurl', 'weight',
                'value']
        for kw in kwargs.keys():
            if kw not in ll:
                raise ValueError("Illegal keyword argument: %s" % kw)

        self.value = value
        self.weight = kwargs.get('weight', None)
        self.iconurl = kwargs.get('iconurl', '')
        self.fields = {}
        self.displayinfo = {}

        node = kwargs.get('node', None)

        # to avoid duplicate Field() object creation,
        # only build the self.fields dict if we're not unpacking an XML node
        if not node:
            namelist = [n for n,dn in self.__fields__]

            if args:
                for name,value in zip(namelist, args):
                    if value:
                        setattr(self, name, value)
            if kwargs:
                for name in kwargs.keys():
                    if name in namelist:
                        setattr(self, name, kwargs[name])

            for name in namelist:
                if name not in self.fields:
                    setattr(self, name, '')

            for name,disname in self.__fields__:
                if not self.fields[name].displayname:
                    self.fields[name].displayname = disname

        super(Entity, self).__init__(node)

    def load(self, node):
        super(Entity, self).load(node)

        if node.tag != 'Entity':
            raise MalformedEntityError("Not an Entity XML node")
        if 'Type' not in node.attrib:
            raise MalformedEntityError("No Entity.Type attribute")

        etype = node.attrib['Type']
        if etype != self.__class__.__name__:
            raise UnknownEntityError('Unknown Entity Type: "%s"' % etype)

        v = node.find('Value')
        if v == None:
            raise MalformedEntityError("Missing Value Tag!")
        self.value = v.text and v.text.strip() or ''

        weight = node.find('Weight')
        if weight != None:
            self.weight = weight.text and weight.text.strip() or ''

        addfields = node.find('AdditionalFields')
        if addfields != None:
            for fnode in addfields.getchildren():
                field = Field(node=fnode)
                self.fields[field.name] = field

        dinfo = node.find('DisplayInformation')
        if dinfo != None:
            for dnode in dinfo.getchildren():
                label = Label(node=dnode)
                self.displayinfo[label.name] = label

        iconurl = node.find('IconURL')
        if iconurl != None:
            self.iconurl = iconurl.text and iconurl.strip() or ''

    def tonode(self):
        node = serialize.Node('Entity')
        node.attributes['Type'] = self.__class__.__name__

        serialize.SubNode(node, 'Value', self.value)
        if self.weight != None:
            serialize.SubNode(node, 'Weight', self.weight)

        fields = serialize.SubNode(node, 'AdditionalFields')
        for field in self.fields.values():
            if field.value:
                fields.appendChild( field.tonode() )

        displayinfo = serialize.SubNode(node, 'DisplayInformation')
        for dinfo in self.displayinfo.values():
            displayinfo.appendChild( dinfo.tonode() )

        if self.iconurl:
            serialize.SubNode(node, 'IconURL', self.iconurl)
        return node

# ;--------------------------------------------------------------------
# ;-  Entity Definitions below
# ;--------------------------------------------------------------------

class DNSName(Entity): pass

class Document(Entity):
    __fields__ = [
        ('metainfo', 'Document MetaInfo'),
        ('link', 'Link to Document'),
    ]

class Domain(Entity):
    __fields__ = [
        ('whois', 'Whois Information'),
    ]

class EmailAddress(Entity): pass

class IPAddress(Entity):
    __fields__ = [
        ('whois', 'WhoisInformation'),
    ]

class Location(Entity):
    __fields__ = [
        ('long', 'Longitude'),
        ('lat', 'Latitude'),
        ('country', 'Country'),
        ('city', 'City'),
        ('area', 'Area'),
        ('countrysc', 'Country Short Code'),
    ]

class Netblock(Entity):
    __fields__ = [
        ('startIP', 'Start of block'),
        ('endIP', 'End of block'),
        ('ASNumber', 'AS Number'),
    ]

class Person(Entity):
    __fields__ = [
        ('firstname', 'First Name'),
        ('lastname', 'Last Name'),
        ('additional', 'Additional Search Term'),
        ('countrysc', 'Country Short Code'),
    ]

class Phrase(Entity): pass

class PhoneNumber(Entity):
    __fields__ = [
        ('countrycode', 'Country Dial Code'),
        ('citycode', 'City Code'),
        ('areacode', 'Area Code'),
        ('lastnumbers', 'Last Numbers'),
        ('additional', 'Additional search terms'),
        ('additionalcountry', 'Additional Country Code'),
        ('type', 'Mobile or Landline'),
    ]

class Website(Entity):
    __fields__ = [
        ('http', 'HTTP Port(s)'),
        ('https', 'HTTPS Port(s)'),
        ('servertype', 'Running Server Version'),
    ]

class Affiliation(Entity):
    __fields__ = [
        ('uid', 'Unique Identifier'),
        ('key', 'Network Key'),
    ]

# to create generic objects, I need to create a class() of Entity/Type... 

# Factory method
def entity(node=None, name=None, *args, **kwargs):
    '''convert an ElementTree node into an Entity of the appropriate type'''
    entities = dict([(sc.__name__, sc) for sc in Entity.__subclasses__()])

    if node and name:
        raise ValueError("Only one of 'node' or 'name'")

    if name:
        try:
            ent = entities[name]
        except KeyError:
            raise UnknownEntityError("Not a known Entity: %s" % name)
    elif node:
        if not serialize.iselement(node):
            raise ValueError("Not an ElementTree node!")

        if node.tag != 'Entity':
            raise MalformedEntityError("Not an Entity node")
        if 'Type' not in node.attrib:
            raise MalformedEntityError("No Entity/Type in node")
        entype = node.attrib['Type']
    
        try:
            ent = entities[entype]
        except KeyError:
            raise UnknownEntityError("Unknown Entity: %s" % entype)
    else:
        raise ValueError("Either 'node' or 'name' required!")

    return ent(node=node, *args, **kwargs)
