#!/usr/bin/env python2.5
#komodoheader v0.5
##############################################################################################
#
# File:         start_maltego_server.py
# Description:  Initialises a Maltego app under CherryPy
# Created_On:   Wed Apr  9 15:36:56 2008
# Created_By:   iodboi
# Modified_On:  Fri Apr 25 11:07:17 2008
# Modified_By:  iodboi
# Language:     Python Version 2.5.2a0 [GCC 4.0.1 (Apple Computer, Inc. build 5250)]
# Encoding:     UTF-8
# Status:       Use at your own risk - I take no liability for software defects or if your
#               girlfriend leaves you as a result of using this software.
#
# Music:        Crystal Castles	- Vanished
#
#
##############################################################################################

##Stdlib imports
import sys, optparse, os, threading, time, Queue, sets

##3rd party imports
import maltego
try:
    ##Start a CherryPy Server
    from cherrypy import wsgiserver
    HAS_CHERRYPY=True
except ImportError:
    try:
        from wsgiref import simple_server
        HAS_CHERRYPY=False
        HAS_BASIC_LAME_WSGI_SERVER=True
    except ImportError:
        print "Some sort of WSGI server is required, either one of:"
        print "1) CherryPy"
        print "2) wsgiref.simple_server"
        sys.exit(-2)

import import_reg_malt_apps as reg_m_a

class discover_maltego_apps:
    """
    Given a directory path import all the modules and then register the maltego transforms
    within those modules with an instance of maltego.Application
    Can also remove and reregister modules and their transforms
    """

    def __init__(self, log="/tmp/log.txt",  name="Pymaltego", subdir="/maltego"):
        """
        Start a instance of a maltego Apllication instance and import and register all our maltego apps
        """
        ##Instantiate a maltego object
        self.maltego_app = maltego.Application(debuglog=log)
        self.subdir=subdir
        self.name=name

        ##Instantiate the auto import & registration object
        self.ma_importer=reg_m_a.reg_maltego_apps(self.maltego_app)

    def __call__(self, path):
        """
        Wrapper for register for initial usage
        """
        self.register(path)

        return [ ( "/", self.seed_xml_construct ), (self.subdir, self.maltego_app) ]

    def register(self, path):
        """
        This imports the modules specified in the directory path, and then registers
        them with the instantiated maletgo.Application object
        """
        ##Now call the registration object with the dir to import and register
        self.ma_importer.register_app(path)

    def unregister(self, path):
        """
        This removes a module and the maltego transforms it contains from the maltego
        server
        """
        self.ma_importer.unregister_app(path)

    def reregister(self, path):
        """
        This updates an existing modules transforms if the modules code has been changed
        CAVEAT: See http://mail.python.org/pipermail/python-list/2001-March/075683.html
        """
        self.ma_importer.reregister_app(path)

    def seed_xml_construct(self, environ, start_response):
        """
        Create the seed xml for the transform discovery process as a crude WSGI app
        """
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)

        #print environ

        seed="""<MaltegoMessage>
<MaltegoTransformDiscoveryMessage source="%s Maltego Application Server">
<TransformApplications>
<TransformApplication name="%s Transforms" URL="http://%s%s/"/>
</TransformApplications>
<OtherSeedServers>
</OtherSeedServers>
</MaltegoTransformDiscoveryMessage>
</MaltegoMessage>"""%(self.name, self.name, environ["HTTP_HOST"], self.subdir)

        return [seed]

class directory_monitor(threading.Thread):
    """
    Watch a directory of PyMaltego apps for filesystem changes new modules, deleted modules
    or changes to a module* and cause the changes to be reflected in the already spawned
    maltego.Application without having to restart the server etc
    """
    def __init__(self, path, reg_app, res=5):

        threading.Thread.__init__(self)

        self.path=os.path.abspath(path)
        self.ma_reg_app=reg_app
        self.resolution=res

        ##Initialise the dictionary of the all files in the dir m_times
        self.m_time_dict={}
        for f in os.listdir(self.path):
            if os.path.splitext(f)[1] == ".py":
                self.m_time_dict[f]=os.stat("%s%s%s"%(self.path, os.sep,f) ).st_mtime

    def run(self):

        print "Starting FS monitor thread for %s....."%(self.path)

        dir_contents_last_round=sets.Set( self.m_time_dict.keys() )

        while 1:

            dir_contents_this_round=sets.Set( os.listdir(self.path) )

            ##Have we got any files deleted?
            files_deleted_this_round=dir_contents_last_round.difference(dir_contents_this_round)

            for fd in files_deleted_this_round:
                ##This means if we make it here a file has been deleted
                print "File %s deleted"%(os.path.join(self.path, fd))
                self.ma_reg_app.unregister(os.path.join(self.path, fd))

                if os.path.splitext(fd)[1] == ".py":
                    del self.m_time_dict[fd]

            for f in dir_contents_this_round:
                ##skip non python stuff
                if os.path.splitext(f)[1] != ".py":
                    continue

                try:
                    ##Look for files that have been updated
                    file_m_time=os.stat("%s"%(os.path.join(self.path, f))).st_mtime
                    if file_m_time != self.m_time_dict[f]:
                        ##Module changed so need to reload the module and apps
                        print "File '%s' changed"%(os.path.join(self.path, f))
                        self.ma_reg_app.reregister(os.path.join(self.path, f))
                        self.m_time_dict[f]=file_m_time
                        continue

                    else:
                        ##Mtime the same so this module ain't changed
                        #print "No change %s"%(os.path.join(self.path, f))
                        continue

                except KeyError:
                    ##This means a new file has been created - import the module and check for maltego apps
                    print "New file created: %s"%(os.path.join(self.path, f))
                    self.ma_reg_app.register(os.path.join(self.path, f))
                    self.m_time_dict[f]=file_m_time

                    continue

            dir_contents_last_round=dir_contents_this_round
            time.sleep(self.resolution)

def parse_cli():

    parser=optparse.OptionParser()

    parser.add_option('-i', '--ip', dest="ip", help="Host IP/DNS Name to bind the server to",
            default='127.0.0.1')

    parser.add_option('-p', '--port', dest="port", type="int", help="TCP port number to bind the server to",
            default='9876')

    parser.add_option('-d', '--app-dir', dest="dir", help="Directory to scan for maltego apps to import and register",
            default="")

    parser.add_option('-m', '--monitor', dest="monitor", action='store_true', help="Do we monitor the directory to see if new apps have been dropped in?",
            default=False)

    parser.add_option('-n', '--name', dest="name", help="Name to christen our server with",
            default='Pymaltego')

    parser.add_option('-l', '--log', dest="log", help="Location to log to",
            default='/tmp/pymaltego.log')

    parser.add_option('-s', '--subdir', dest="subdir", help="subdir to serve the maltego application from",
            default='/maltego')

    options, args = parser.parse_args()

    return options, args


if __name__ == "__main__":

    wsgi_apps=[]

    options, args=parse_cli()

    ##If no app dir has been specified on the CLI has the environmental var PYMALTEGO_APPS been set?
    if not options.dir:
        try:
            options.dir=os.environ["PYMALTEGO_APPS"]

        except KeyError:
            print "No maltego application directory supplied via '-d' or by the PYMALTEGO_APPS env var."
            print "Nohing more to be done. Exiting!\n"
            sys.exit(-1)

    ##Search the app dir for maltego transforms & register them with a maletgo.Application instance
    disc_obj=discover_maltego_apps(options.log ,options.name ,options.subdir)
    wsgi_apps.extend( disc_obj(options.dir) )

    ##Do we spawn a thraed to watch the specified directory for new maltego apps being
    ## dropped in to register/unregister them automatically?
    if options.monitor:
        dir_mon_thread=directory_monitor(options.dir, disc_obj)
        dir_mon_thread.start()

    print "Initialising PyMaltego WSGI server...."
    try:
        if HAS_CHERRYPY:
            wsgi_server= wsgiserver.CherryPyWSGIServer( (options.ip, options.port), wsgi_apps )
            wsgi_server.start()
        else: # HAS_BASIC_LAME_WSGI_SERVER
            wsgi_server = simple_server.make_server(options.ip, options.port, wsgi_apps)
            wsgi_server.serve_forever()
    except KeyboardInterrupt:
        print "\nCrtl-C caught! Shutting down"
    except Exception, err:
        print "Unhandled exception: %s"%(err)
        print "Shutting down server()"

    if HAS_CHERRYPY:
        wsgi_server.stop()
    else:
        wsgi_server.server_close()

    print "Done."
    ##Kill the fs monitoring thread
    os._exit(0)
