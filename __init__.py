from .lsg_manager import LSGManagerPlugin

def classFactory(iface):
    return LSGManagerPlugin(iface)
