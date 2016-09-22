#!/usr/bin/env python
#komodoheader v0.5
##############################################################################################
#
# File:         import_reg_malt_apps.py
# Description:  For a given dir import all maltego apps and register them
# Created_On:   Thu Apr 10 17:45:50 2008
# Created_By:   iodboi
# Modified_On:  Fri Apr 25 11:06:50 2008
# Modified_By:  iodboi
# Language:     Python Version 2.5.2a0 [GCC 4.0.1 (Apple Computer, Inc. build 5250)]
# Encoding:     UTF-8
# Status:       Use at your own risk - I take no liability for software defects or if your
#               girlfriend leaves you as a result of using this software.
#
# Music:        Agaskodo Teliverek - Blood Club
#
#
##############################################################################################
import sys, os, inspect, linecache
import maltego

DEBUG=False

def debug(msg):
    if DEBUG:
        print msg

class reg_maltego_apps:
    """
    Dig through the .py's in a supplied directory and import from those the classes
    which are pymaltego apps, then register them with the overall maltego.Application
    """

    def __init__(self, maltego_obj):

        ##This is an already instantiated maltego.Application() class that all
        ## found maltego apps will be registered to
        self.maltego_obj=maltego_obj

        ##List of module paths & their associated maltego app objects
        self.mod_table={}

        self.skip_list=["__init__"]

    def __call__(self, path):
        """
        Default action is to import and register apps in a dir
        """
        ##Import & register all modules in the dir conatining transforms with the main PyMaltego application object
        self.register_app(path)

    def _load_module_from_path(self, path):
        """
        From a specified path string import the module if it is new to us, or
        reload it if we have seen it before. Also force a linecache update
        """
        try:
            name, ext = os.path.splitext(path)
            name=os.path.split(name)[1]
            if ext == '.py' and name not in self.skip_list:

                ##potentially it is possible for an app that appears new to be an app that was previously registered,
                ##removed, and then added back again - possibly with changes in this case we need to reload it, not import it
                m_obj=self._get_module_obj_from_path(path)

                if m_obj:
                    debug("Seen this module before, reloading NOT importing")
                    m=reload(m_obj)

                    ##Update line cache - see explanation in _checkfor_ghosts - this is to defend against
                    ## a module being 'deleted' and then put back in the dir with class changes - ghosts can show up
                    linecache.checkcache(path)
                else:
                    debug( "Never seen this module before, IMPORTING from scratch")
                    m=__import__(name)


                return m

        #except Exception, err:
        except OSError:
            debug ("Exception in _load_module_from_path: %s"%(err))

        debug ("not importing %s"%(path) )
        return None



    def _find_maltego_app(self, module):
        """
        For a supplied module return a list of class that are pymaltego apps
        (i.e. have a superclass of maltego.transform.Transform )
        """
        app_list=[]
        for memb in inspect.getmembers(module):

            if inspect.isclass(memb[1]):
                try:
                    for sup_cls in inspect.getmro( memb[1] ):

                        if sup_cls ==  maltego.transform.Transform:
                            debug( "%s identified as a maltego transform"%(memb[1]))
                            app_list.append(memb[1])

                except Exception, err:
                    debug( "B0rk, somethings gone screwy: [%s]"%(err))

        return app_list


    def _get_module_obj_from_path(self, path):
        """
        For a specified string path return the associated module object from our
        module table
        """
        for mod_obj in self.mod_table.keys():

            #print "TABLE item",os.path.splitext( inspect.getfile(mod_obj) )[0]
            #print "PATH item",os.path.splitext( os.path.abspath(path) )[0]
            if os.path.splitext( inspect.getfile(mod_obj) )[0] == os.path.splitext( os.path.abspath(path) )[0]:
                return mod_obj

    def _check_for_ghosts(self, transform_list):
        """
        IN:
            List of classes that are maltego transforms
        OUT:
            List of classes which are maltego transform and are NOT memory ghosts from previous import/reloads

        Nasty hacky method to check for 'class ghosts' from modules that have been changed on disk
        and reloaded, if one of their classes has been deleted it still looks to python as its still there
        see: http://mail.python.org/pipermail/python-list/2001-March/075683.html

        What's more to make things even hackier the inspect module has a bug in it (http://bugs.python.org/issue1218234)
        which menas the method we can use to see if the class is really there or a ghost from a previous import
        doesn't work out the box - so we have to force a linecache update before we ask the inspect module to find
        the source lines for each class the module reports it has. Nasty - hopefully this will get fixed in python
        but I'm not hopeful.

        Summary of the solution (some steps outside this method):
            -Reload the module that has changed on disk
            -Find the file that module relates to
            -Force linecache to update its cache of lines for that file
            -For each maltego transform class the module says it has call getsourcelines
            -Classes that have been deleted from the module will throw a IOError
            -Other classes won't so we know these are genuine - throw these to maltego.Application for registration

        It really shouldn't be this difficult! Python Dev's what are you playing at ??
        """
        non_ghost_class=[]
        for t in transform_list:
            try:
                inspect.getsource(t)
                ##No error we got the code so
                non_ghost_class.append(t)
                #debug(inspect.getsource(t))
            except IOError:
                debug("ghost of %s found - removing from list to register with the maletgo app"%t)

        return non_ghost_class


    def import_apps(self, app_path):
        """
        Import all qualifying apps in a supplied path (dir of modules or single module)
        """
        ##List of classes within the modules that are maltego apps
        app_list=[]

        ##Fully qualify the supplied path name
        app_path=os.path.abspath(app_path)

        try:
            ##Attempt to import all python modules in the specified dir
            dir_list=os.listdir(app_path)

        except OSError, err:
            ##ERROR! Looks like a non dir path was passed in for single module import and register
            app_path, mod = os.path.split( app_path )
            dir_list=[mod]

        ##Add the module dir path to our python path
        if app_path not in sys.path:
            debug("Updating python path with %s"%(app_path))
            sys.path=[ app_path ]+sys.path

        for module in dir_list:
            imported_obj=self._load_module_from_path( os.path.join(app_path, module) )
            if imported_obj:
                self.mod_table[ imported_obj ]=[]

        for module in self.mod_table.keys():
            m_apps=self._check_for_ghosts(self._find_maltego_app(module))

            self.mod_table[module]=m_apps
            app_list.extend( m_apps )

        debug("Module table: %s"%(self.mod_table))

        return app_list

    def register_app(self, path):
        """
        From the supplied path (either dir of modules or path to single module)
        import and register with the maltego.Application all the maltego transforms
        that can be found.
        """
        debug( "REG %s"%path )

        ##Import all the maltego apps from the supplied directory
        app_list=self.import_apps(path)

        ##Register each app with the maltego.Application() obj
        for m_app in app_list:
            self.maltego_obj.register(m_app())

    def unregister_app(self, path):
        """
        Remove the association of the app with the maltego.Application() obj
        """
        debug( "UNreg %s"%path)

        ##For the supplied path that has been removed we need to look up the associated module object
        ## & get the transfrom objs associated with it
        m_obj=self._get_module_obj_from_path(path)
        if m_obj:
            ##Remove the transform objects from the maltego Application object's dictionary
            for trns in self.mod_table[m_obj]:
                self.maltego_obj.unregister(trns())
            ##And finally remove the transforms from our module table
            self.mod_table[m_obj]=[]

        else:
            debug("File removed did not contain a maltego transform")

    def reregister_app(self, path):
        """
        If new functionality has been addedd (i.e. a new transform, existing transform altered but its class not renamed)
        to the file this will be updated, HOWEVER if a transform has been deleted/renamed then the old transform
        will remain memory resident :( this is a limitation of reload()
        see: http://mail.python.org/pipermail/python-list/2001-March/075683.html
        """
        debug("REreg %s"%path)

        m_obj=self._get_module_obj_from_path(path)

        ##Remove object from maltego.Application() & from out self.module_table
        self.unregister_app(path)

        ##Reload the module to get changes into memory
        reload(m_obj)

        ##Update line cache - see explanation in _checkfor_ghosts   -----
        linecache.checkcache(path)

        ##NASTY HACK
        m_trns=self._check_for_ghosts(self._find_maltego_app(m_obj))

        ##Add to our tracking table
        self.mod_table[m_obj]=m_trns

        ##Now register the transforms from the reloaded module with the maltego.Application()
        for trans in m_trns:
            self.maltego_obj.register(trans())
