#!/usr/bin/env python

import serialize
import entity
import types


# XXX should move these into serialize, and make them more robust ?
def _get_text(root, name):
    elem = root.find(name)
    if elem == None:
        raise ValueError('No tag "%s" in "%s"' % (name, root.tag))
    if elem.text is None:
        raise ValueError('No text in tag: %s' % name)
    return elem.text.strip()

def _find_text(root, name):
    elem = root.find(name)
    if elem != None and elem.text:
        return elem.text.strip()
    return ''

def _findall_text(root, name):
    rl = []
    for elem in root.findall(name):
        if elem.text and elem.text.strip():
            rl.append(elem.text.strip())
    return rl

class MalformedTransformError(serialize.error): pass

class InputRequirement(serialize.XMLObject):
    """Transform InputRequirement
    name = variable name
    display = Display name for UI client
    type = String / Integer
    optional = input is optional? True/False

    Note:
    The InputRequirement from a transform is not converted into the
    appropriate type. If you require an Integer, it will be stored as a
    string. You *must* convert on your own.
    """
    def __init__(self, name='', display='', type='', optional="False",
            default=None, node=None):
        self.name = name
        self.display = display
        self.type = type
        self.optional = optional
        self.default = default
        super(InputRequirement, self).__init__(node=node)

    def load(self, node):
        super(InputRequirement, self).load(node)

        if node.tag != 'Input':
            raise MalformedTransformError("Not an Input tag: %s" % node.tag)
        try:
            self.name = node.attrib['Name']
            self.display = node.attrib['Display']
            self.type = node.attrib['Type']
            self.optional = node.attrib['Optional']
        except KeyError:
            raise MalformedTransformError("Input missing attributes")

        self.default = node.attrib.get('Default', None)

    # XXX ? Should all of these be wrapped in str() ??
    def tonode(self):
        node = serialize.Node('Input')
        node.attributes['Name'] = self.name
        node.attributes['Display'] = self.display
        node.attributes['Type'] = self.type
        node.attributes['Optional'] = self.optional
        if self.default != None:
            node.attributes['Default'] = self.default
        return node

class Transform(serialize.XMLObject):
    """Transform Base Class

    All Transforms _must_ inherit from this class. They _must_ initialize the
    required elements of the Transform metadata from the Maltego Transform
    Spec.

    Transforms are available via the _RUN command using their class name.

    All transforms must override the 'transform' method. This method is where
    the transform is implemented.

    An example transform:

    class DNSNameToIPAddress(maltego.Transform):
        def __init__(self):
            super(DNSNameToIPAddress, self).__init__(
                displayname="DNS to IP Address",
                author="thegrugq <the.grugq@gmail.com>",
                input=maltego.DNSName,
                output=maltego.IPAddress, # for multiple output, pass in a list
                version='0.8-rc4'
            )
            self.description = "Convert DNS Name to IP Address"
            self.disclaimer = "This only works when there is network access"

        def transfrom(self, entities, key, fields={}, limits=(None,None)):
            ret_entities = []
            for dns in entities:
                if not isinstance(dns, maltego.DNSName):
                    raise MalformedInputEntity("Not a DNSName!")
                ip = socket.gethostbyname(dns.value)
                ret_entities.append( maltego.IPAddress( ipaddr ) )
            return ret_entities
    """

    max_input = None
    max_output = None
    description = ''
    disclaimer = ''
    owner = ''
    location = ''

    def __new__(cls, *args, **kwargs):
        self = super(Transform, cls).__new__(cls, *args, **kwargs)
        self.displayname = ''
        self.name = self.__class__.__name__
        self.author = ''
        self.version = ''
        self.input = ''
        self.description = self.__doc__ or ''
        self.disclaimer = ''
        self.output = []
        self.requirements = {}
        return self

    def __init__(self, displayname=None, author=None, input=None, output=None,
            version='1.0', node=None, **kwargs):

        if node == None:
            if not (displayname and author and input and output and version):
                raise ValueError("Missing MANDATORY information")

            def get_entity_name(ent):
                if issubclass(ent, entity.Entity):
                    return ent.__name__
                elif issubclass(ent, basestring):
                    return ent
                raise ValueError("Not a known Entity: %r" % ent)

            self.displayname = displayname
            self.author = author
            self.version = version

            self.input = get_entity_name( input )

            if type(output) not in (types.TupleType, types.ListType):
                output = [output]

            self.output = [get_entity_name(e) for e in output]

            if not self.description:
                self.description = self.__doc__ or ''

        super(Transform, self).__init__(node=node)

    def tonode(self):
        node = serialize.Node('Transform')
        if hasattr(self, 'name') and self.name:
            name = self.name
        else:
            name = self.__class__.__name__
        node.attributes['TransformName'] = name
        node.attributes['UIDisplayName'] = self.displayname

        node.attributes['Author'] = self.author

        if self.description:
            node.attributes['Description'] = self.description
        if self.disclaimer:
            node.attributes['Disclaimer'] = self.disclaimer
        if self.owner:
            node.attributes['Owner'] = self.owner
        if self.location:
            node.attributes['LocationRelevance'] = self.location

        inreq = serialize.SubNode(node, 'UIInputRequirements')
        for req in self.requirements.values():
            inreq.appendChild( req.tonode() )

        node.attributes['Version'] = self.version
        serialize.SubNode(node, 'InputEntity', self.input)

        outent = serialize.SubNode(node, 'OutputEntities')
        for output in self.output:
            serialize.SubNode(outent, 'OutputEntity', output)

        if self.max_input not in ('', None):
            serialize.SubNode(node, 'MaxInputEntityCount', self.max_input)

        if self.max_output not in ('', None):
            serialize.SubNode(node, 'MaxOutputEntityCount', self.max_output)

        return node

    def load(self, node):
        super(Transform, self).load(node)

        if node.tag != 'Transform':
            raise MalformedTransformError("Not a Transform: %s" % node.tag)

        try:
            self.name = node.attrib['TransformName']
            self.displayname = node.attrib['UIDisplayName']
            self.author = node.attrib['Author']
            self.version = node.attrib['Version']
        except KeyError:
            raise MalformedTransformError("Transform missing attributes!")

        inent = node.find('InputEntity')
        if inent == None:
            raise MalformedTransformError('Missing InputEntity tag!')
        self.input = inent.text and inent.text.strip() or ''

        outent = node.find('OutputEntities')
        if outent == None:
            raise MalformedTransformError("Missing OutputEntities tag!")
        for output in outent.getchildren():
            if output.text:
                self.output.append( output.text.strip() )

        inreq = node.find('UIInputRequirements')
        if inreq:
            for req in [InputRequirement(node=r) for r in inreq.getchildren()]:
                self.requirements[req.name] = req

        self.description = node.attrib.get('Description', '')
        if self.description and not self.__doc__:
            self.__doc__ = self.description

        self.disclaimer = node.attrib.get('Disclaimer', '')
        self.owner = node.attrib.get('Owner', '')
        self.location = node.attrib.get('LocationRelevance', '')

    def transform(self, entities, key=None, fields={}, limit=(None, None)):
        """transform() -> list of Entity objects and/or str tuples

        entities := list of Entity objects
        key := Any Key supplied by the Transform caller (e.g. license)
        fields := dict of name:value pairs from the RequiredInput of the caller
        limit := Hard/Soft limits for transforms

        return: A list of Entity objects. Any UIMessage messages can be embedded
        in the return list as tuples of (Level, Message). e.g. ('Debug', 'None')

        Example transform() provided below:

        def transform(self, entities, key=None, fields={}, limit=(None,None)):
            ret_list = []
            for ent in entities:
                try:
                    ret_ent = self._do_transform(ent)
                    ret_list.append( ret_ent )
                except OSError, e:
                    ret_list.append(("Debug", "Failed for ent: %s" % ent.value))
            return ret_list
        """
        pass

def transform(node=None):
    return Transform(node=node)
