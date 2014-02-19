"""
"""
from random import randint
from threading import Thread
from rpyc.utils.registry import UDPRegistryServer

from webkit_scraper import Node, NodeFactory, WebPageStub

from rpyc.utils.server import ThreadedServer
from rpyc import Service

import logging
logger = logging.getLogger(__name__)

def expose(*names, **kw):
    def decorate(Class):
        methods = dict( (name,getattr(Class,name)) for name in names )
        class Decorated(Class):
            def __init__(self, *args, **kwargs):
                kwargs.update(kw)
                super(Decorated, self).__init__(*args, **kwargs)
        for name,meth in methods.iteritems():
            setattr(Decorated, 'exposed_'+name, meth)
        return Decorated
    return decorate


@expose(
    'is_visible', 'set', 'get_bool_attr', 'drag_to', 'text', 'is_attached', 'eval_script', 'submit', 'path', 'click',
    'select_option', 'value', 'is_multi_select', 'set_attr', 'exec_script', 'is_selected', 'unselect_options',
    'tag_name', 'get_node_factory', 'is_checked', 'get_attr', 'is_disabled', 'xpath',
)
class _ExposedNode(Node):
    pass
class ExposedNode(_ExposedNode): pass

class ExposedNodeFactory(NodeFactory):
    _Node = ExposedNode

@expose(
    'body', 'reset', 'render', 'set_cookie', 'set_proxy', 'status_code', 'set_header', 'clear_proxy', 'url',
     'cookies', 'eval_script', 'wait', 'set_html', 'headers', 'exec_script', 'issue_node_cmd', 'visit', 'set_attribute',
     'source', 'clear_cookies', 'set_viewport_size', 'set_error_tolerant', 'reset_attribute', 'xpath',
    node_factory_class = ExposedNodeFactory
)
class _WebkitService(Service, WebPageStub):
    __name__ = 'MyName'
    def __init__(self, *args, **kwargs):
        node_factory_class = kwargs.pop('node_factory_class')
        Service.__init__(self, *args, **kwargs)
        WebPageStub.__init__(self, node_factory_class=node_factory_class)

    def on_connect(self):
        print('Client conected.')
    def on_disconnect(self):
        print('Client disconected. Stopping Webkit instance.')
        self.stop()
    def exposed_get_answer(self):
        return 42
class WebkitService(_WebkitService): pass

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s',level=logging.INFO)

    import os
    import time
    from multiprocessing import Process

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_NAME = 'WEBKIT'

    class MyProcess(Process):
        def __init__(self, port):
            super(MyProcess, self).__init__()
            self._port= port
        def run(self):
            self.t = ThreadedServer(WebkitService, hostname=DEFAULT_HOST, port=self._port)
            self.t.start()
            os._exit(0)

    class RegistryServerHandler(Thread):
        def __init__(self):
            super(RegistryServerHandler, self).__init__()
            self.server = UDPRegistryServer(port=18811, )
        def run(self):
            self.server.start()
        def add(self, info):
            self.server._add_service(DEFAULT_NAME, info)
        def remove(self, info):
            self.server._remove_service(DEFAULT_NAME, info)
        def count(self):
            return len(self.server.services.get(DEFAULT_NAME,()))

    class MyProcessHandler(Thread):
        def __init__(self, registry):
            super(MyProcessHandler, self).__init__()
            self.daemon = True
            self._registry = registry
        def run(self):
            port = randint(10000,20000)
            proces = MyProcess(port)
            proces.start()
            self._registry.add((DEFAULT_HOST,port))
            proces.join()
            self._registry.remove((DEFAULT_HOST,port))

    registry = RegistryServerHandler()
    registry.start()

    while True:
        try:
            if registry.count()<4:
                handler = MyProcessHandler(registry)
                handler.start()
            time.sleep(0.1)
        except KeyboardInterrupt:
            break

    exit(0)