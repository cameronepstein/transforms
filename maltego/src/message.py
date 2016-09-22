#!/usr/bin/env python
#
# (c) 2007,2008, the grugq <the.grugq@gmail.com>

import types
import serialize
import entity
import transform

__all__ = ['TransformDiscovery', 'TransformList', 'TransformRequest',
           'TransformResponse', 'TransformException' ]

class MalformedMessageError(serialize.error): pass

class MaltegoMessage(serialize.XMLObject):
    def __init__(self, node=None):
        self.uimessages = {}
        super(MaltegoMessage, self).__init__(node)

    def load(self, node):
        super(MaltegoMessage, self).load(node)

        if not node.tag[:7] == 'Maltego' and not node.tag[-7:] == 'Message':
            raise MalformedMessageError("Not a valid MaltegoMessage Type")

        # check that we are capable of handling this message type
        if node.tag[7:-7] != self.__class__.__name__:
           raise MalformedMessageError("Wrong MaltegoMessage Type")

        uimsgs = node.find('UIMessages')
        if uimsgs != None:
            for uimsg in uimsgs.getchildren():
                mtype = uimsg.attrib['MessageType']
                mtext = uimsg.text and uimsg.text.strip() or ''
                self.uimessages.setdefault(mtype, []).append( mtext )

    def tonode(self):
        node = serialize.Node("Maltego%sMessage" % self.__class__.__name__)

        if self.uimessages:
            uimsgs = serialize.SubNode(node, 'UIMessages')
            for k,v in self.uimessages.iteritems():
                for msg in v:
                    serialize.SubNode(uimsgs, 'UIMessage', msg,
                            {'MessageType' : k} )
        return node

    def toxml(self):
        return '<MaltegoMessage>\n%s</MaltegoMessage>\n' % \
                super(MaltegoMessage, self).toxml()

    def append(self, obj):
        pass
    def __iadd__(self, other):
        if hasattr(other, '__iter__'):
            for o in other:
                self.append(o)
        else:
            self.append(o)
        return self

class TransformDiscovery(MaltegoMessage):
    def __init__(self, applications=None, seeds=None, node=None):
        self.applications = applications or []
        self.seeds = seeds or []
        super(TransformDiscovery, self).__init__(node=node)

    def load(self, node):
        super(TransformDiscovery, self).load(node)

        transapps = node.find('TransformApplications')
        if transapps != None:
            for app in transapps.getchildren():
                try:
                    self.applications.append( app.attrib['URL'] )
                except KeyError:
                    raise MalformedMessageError("No URL attribute in tag!")

        otherseeds = node.find('OtherSeedServers')
        if otherseeds != None:
            for seed in otherseeds.getchildren():
                try:
                    self.seeds.append( seed.attrib['URL'] )
                except KeyError:
                    raise MalformedMessageError("No URL attribute in tag")

    def tonode(self):
        node = super(TransformDiscovery, self).tonode()

        transapps = serialize.SubNode(node, 'TransformApplications')
        for app in self.applications:
            serialize.SubNode(transapps, 'TransformApplication',
                    attribs = {'URL' : app})
        otherseeds = serialize.SubNode(node, 'OtherSeedServers')
        for seed in self.seeds:
            serialize.SubNode(otherseeds, 'OtherSeedServer',
                    attribs = {'URL' : seed })

class TransformList(MaltegoMessage):
    def __init__(self, transforms=None, node=None):
        self.transforms = []
        if transforms:
            if type(transforms) not in (types.ListType, types.TupleType):
                transforms = [transforms]
            self.transforms.extend( transforms )

        super(TransformList, self).__init__(node)

    def load(self, node):
        super(TransformList, self).load(node)

        transforms = node.find('Transforms')
        if transforms == None:
            raise MalformedMessageError("TransformList requires Transforms tag")

        for transnode in transforms.getchildren():
            trans = transform.transform(node=transnode)
            self.transforms.append( trans )

    def tonode(self):
        node = super(TransformList, self).tonode()

        transforms = serialize.SubNode(node, 'Transforms')
        for transform in self.transforms:
            transforms.appendChild( transform.tonode() )

        return node

    def append(self, obj):
        if not issubclass(obj, transform.Transform):
            raise ValueError("Not a Transform")
        self.transforms.append(obj)

class TransformRequest(MaltegoMessage):
    def __init__(self, entities=None, fields=None, softlimit='200', 
            hardlimit='1000', node=None):
        self.entities = []
        self.fields = {}
        self.softlimit = softlimit
        self.hardlimit = hardlimit
        if entities:
            if type(entities) not in (types.ListType, types.TupleType):
                entities = [entities]
            self.entities.extend(entities)
        if fields:
            self.fields.update( fields )
        super(TransformRequest, self).__init__(node)

    def load(self, node):
        super(TransformRequest, self).load(node)

        entities = node.find('Entities')
        if entities == None:
            raise MalformedMessageError('Request requires Entities tag')

        for ent in entities.getchildren():
            self.entities.append( entity.entity( node=ent ) )

        fields = node.find('TransformFields')
        if fields != None:
            for field in fields.getchildren():
                if 'Name' not in field.attrib:
                    raise MalformedMessageError("No Name attribute in Field")
                name = field.attrib['Name']
                value = field.text and field.text.strip() or ''
                self.fields[name] = value

        limit = node.find('Limits')
        if limit != None:
            self.softlimit = limit.attrib.get('SoftLimit', None)
            self.hardlimit = limit.attrib.get('HardLimit', None)

    def tonode(self):
        node = super(TransformRequest, self).tonode()

        entities = serialize.SubNode(node, 'Entities')
        for ent in self.entities:
            entities.appendChild( ent.tonode() )

        if self.fields:
            fields = serialize.SubNode(node, 'TransformFields')
            for name, value in self.fields.iteritems():
                field = serialize.SubNode(fields, 'Field', value)
                field.attributes['Name'] = name

        limit = serialize.SubNode(node, 'Limits')
        if self.softlimit:
            limit.attributes['SoftLimit'] = str(self.softlimit)
        if self.hardlimit:
            limit.attributes['HardLimit'] = str(self.hardlimit)
        return node

    def append(self, other):
        if isinstance(other, entity.Entity):
            self.entities.append(other)

class TransformResponse(MaltegoMessage):
    def __init__(self, entities=None, node=None):
        self.entities = []
        if entities:
            if type(entities) not in (types.ListType, types.TupleType):
                entities = [entities]
        super(TransformResponse, self).__init__(node)

    def load(self, node):
        super(TransformResponse, self).load(node)

        entities = node.find('Entities')
        if entities == None:
            raise MalformedMessageError("Response requires Entities tag")

        for ent in entities.getchildren():
            self.entities.append( entity.entity( node=ent ) )

    def tonode(self):
        node = super(TransformResponse, self).tonode()

        entities = serialize.SubNode(node, 'Entities')
        for ent in self.entities:
            entities.appendChild( ent.tonode() )
        return node


class TransformException(MaltegoMessage):
    def __init__(self, exceptions=None, node=None):
        self.exceptions = []
        if exceptions:
            if type(exceptions) not in (types.ListType, types.TupleType):
                exceptions = [exceptions]
            self.exceptions.extend(exceptions)

        super(TransformException, self).__init__(node)

    def load(self, node):
        super(TransformException, self).load(node)

        exceptions = node.find('Exceptions')
        if exceptions == None:
            raise MalformedMessageError("Exception requires Exceptions tag")

        for excep in exceptions.getchildren():
            etext = excep.text and excep.text.strip() or ''
            self.exceptions.append( etext )

    def tonode(self):
        node = super(TransformException, self).tonode()

        exceptions = serialize.SubNode(node, 'Exceptions')
        for excp in self.exceptions:
            serialize.SubNode(exceptions, 'Exception', excp)
        return node

#
def message(node):
    if not serialize.iselement(node):
        raise ValueError("Not an ElementTree Element")

    if node.tag != 'MaltegoMessage':
        raise MalformedMessageError("Not a MaltegoMessage")

    try:
        node = node.getchildren()[0]
        msgtype = node.tag[7:-7]
    except IndexError:
        raise MalformedMessageError("No embedded message!")

    mclss = dict([(sc.__name__,sc) for sc in MaltegoMessage.__subclasses__()])

    try:
        klas = mclss[msgtype]
    except KeyError:
        raise MalformedMessageError('Unknown MaltegoMessage/Type ="%s"'%msgtype)

    return klas(node=node)

def fromstring(text):
    node = serialize.fromstring(text)
    return message(node)
