import unittest

from pyramid.testing import cleanUp
from pyramid import testing
from pyramid.compat import text_


class Test_json_renderer_factory(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def _callFUT(self, name):
        from pyramid.renderers import json_renderer_factory
        return json_renderer_factory(name)

    def test_it(self):
        renderer = self._callFUT(None)
        result = renderer({'a':1}, {})
        self.assertEqual(result, '{"a": 1}')

    def test_with_request_content_type_notset(self):
        request = testing.DummyRequest()
        renderer = self._callFUT(None)
        renderer({'a':1}, {'request':request})
        self.assertEqual(request.response.content_type, 'application/json')

    def test_with_request_content_type_set(self):
        request = testing.DummyRequest()
        request.response.content_type = 'text/mishmash'
        renderer = self._callFUT(None)
        renderer({'a':1}, {'request':request})
        self.assertEqual(request.response.content_type, 'text/mishmash')

class Test_string_renderer_factory(unittest.TestCase):
    def _callFUT(self, name):
        from pyramid.renderers import string_renderer_factory
        return string_renderer_factory(name)

    def test_it_unicode(self):
        renderer = self._callFUT(None)
        value = text_('La Pe\xc3\xb1a', 'utf-8')
        result = renderer(value, {})
        self.assertEqual(result, value)
                          
    def test_it_str(self):
        renderer = self._callFUT(None)
        value = 'La Pe\xc3\xb1a'
        result = renderer(value, {})
        self.assertEqual(result, value)

    def test_it_other(self):
        renderer = self._callFUT(None)
        value = None
        result = renderer(value, {})
        self.assertEqual(result, 'None')

    def test_with_request_content_type_notset(self):
        request = testing.DummyRequest()
        renderer = self._callFUT(None)
        renderer('', {'request':request})
        self.assertEqual(request.response.content_type, 'text/plain')

    def test_with_request_content_type_set(self):
        request = testing.DummyRequest()
        request.response.content_type = 'text/mishmash'
        renderer = self._callFUT(None)
        renderer('', {'request':request})
        self.assertEqual(request.response.content_type, 'text/mishmash')


class TestRendererHelper(unittest.TestCase):
    def setUp(self):
        self.config = cleanUp()

    def tearDown(self):
        cleanUp()

    def _makeOne(self, *arg, **kw):
        from pyramid.renderers import RendererHelper
        return RendererHelper(*arg, **kw)

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IRendererInfo
        helper = self._makeOne()
        verifyObject(IRendererInfo, helper)

    def test_settings_registry_settings_is_None(self):
        class Dummy(object):
            settings = None
        helper = self._makeOne(registry=Dummy)
        self.assertEqual(helper.settings, {})

    def test_settings_registry_name_is_None(self):
        class Dummy(object):
            settings = None
        helper = self._makeOne(registry=Dummy)
        self.assertEqual(helper.name, None)
        self.assertEqual(helper.type, '')

    def test_settings_registry_settings_is_not_None(self):
        class Dummy(object):
            settings = {'a':1}
        helper = self._makeOne(registry=Dummy)
        self.assertEqual(helper.settings, {'a':1})

    def _registerRendererFactory(self):
        from pyramid.interfaces import IRendererFactory
        def renderer(*arg):
            def respond(*arg):
                return arg
            return respond
        self.config.registry.registerUtility(renderer, IRendererFactory,
                                             name='.foo')
        return renderer

    def _registerResponseFactory(self):
        from pyramid.interfaces import IResponseFactory
        class ResponseFactory(object):
            pass
        self.config.registry.registerUtility(ResponseFactory, IResponseFactory)

    def test_render_to_response(self):
        self._registerRendererFactory()
        self._registerResponseFactory()
        request = Dummy()
        helper = self._makeOne('loo.foo')
        response = helper.render_to_response('values', {},
                                             request=request)
        self.assertEqual(response.body[0], 'values')
        self.assertEqual(response.body[1], {})

    def test_render_view(self):
        self._registerRendererFactory()
        self._registerResponseFactory()
        request = Dummy()
        helper = self._makeOne('loo.foo')
        view = 'view'
        context = 'context'
        request = testing.DummyRequest()
        response = 'response'
        response = helper.render_view(request, response, view, context)
        self.assertEqual(response.body[0], 'response')
        self.assertEqual(response.body[1],
                          {'renderer_info': helper,
                           'renderer_name': 'loo.foo',
                           'request': request,
                           'context': 'context',
                           'view': 'view',
                           'req': request,}
                         )

    def test_render_explicit_registry(self):
        factory = self._registerRendererFactory()
        class DummyRegistry(object):
            def __init__(self):
                self.responses = [factory, lambda *arg: {}, None]
            def queryUtility(self, iface, name=None):
                self.queried = True
                return self.responses.pop(0)
            def notify(self, event):
                self.event = event
        reg = DummyRegistry()
        helper = self._makeOne('loo.foo', registry=reg)
        result = helper.render('value', {})
        self.assertEqual(result[0], 'value')
        self.assertEqual(result[1], {})
        self.assertTrue(reg.queried)
        self.assertEqual(reg.event, {})
        self.assertEqual(reg.event.__class__.__name__, 'BeforeRender')

    def test_render_system_values_is_None(self):
        self._registerRendererFactory()
        request = Dummy()
        context = Dummy()
        request.context = context
        helper = self._makeOne('loo.foo')
        result = helper.render('values', None, request=request)
        system = {'request':request,
                  'context':context,
                  'renderer_name':'loo.foo',
                  'view':None,
                  'renderer_info':helper,
                  'req':request,
                  }
        self.assertEqual(result[0], 'values')
        self.assertEqual(result[1], system)

    def test_render_renderer_globals_factory_active(self):
        self._registerRendererFactory()
        from pyramid.interfaces import IRendererGlobalsFactory
        def rg(system):
            return {'a':1}
        self.config.registry.registerUtility(rg, IRendererGlobalsFactory)
        helper = self._makeOne('loo.foo')
        result = helper.render('values', None)
        self.assertEqual(result[1]['a'], 1)

    def test__make_response_request_is_None(self):
        request = None
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.body, b'abc')

    def test__make_response_request_is_None_response_factory_exists(self):
        self._registerResponseFactory()
        request = None
        helper = self._makeOne('loo.foo')
        response = helper._make_response(b'abc', request)
        self.assertEqual(response.__class__.__name__, 'ResponseFactory')
        self.assertEqual(response.body, b'abc')

    def test__make_response_result_is_unicode(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        helper = self._makeOne('loo.foo')
        la = text_('/La Pe\xc3\xb1a', 'utf-8')
        response = helper._make_response(la, request)
        self.assertEqual(response.body, la.encode('utf-8'))

    def test__make_response_result_is_str(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        helper = self._makeOne('loo.foo')
        la = text_('/La Pe\xc3\xb1a', 'utf-8')
        response = helper._make_response(la.encode('utf-8'), request)
        self.assertEqual(response.body, la.encode('utf-8'))

    def test__make_response_with_content_type(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        attrs = {'_response_content_type':'text/nonsense'}
        request.__dict__.update(attrs)
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.content_type, 'text/nonsense')
        self.assertEqual(response.body, b'abc')

    def test__make_response_with_headerlist(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        attrs = {'_response_headerlist':[('a', '1'), ('b', '2')]}
        request.__dict__.update(attrs)
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.headerlist,
                         [('Content-Type', 'text/html; charset=UTF-8'),
                          ('Content-Length', '3'),
                          ('a', '1'),
                          ('b', '2')])
        self.assertEqual(response.body, b'abc')

    def test__make_response_with_status(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        attrs = {'_response_status':'406 You Lose'}
        request.__dict__.update(attrs)
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.status, '406 You Lose')
        self.assertEqual(response.body, b'abc')

    def test__make_response_with_charset(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        attrs = {'_response_charset':'UTF-16'}
        request.__dict__.update(attrs)
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.charset, 'UTF-16')

    def test__make_response_with_cache_for(self):
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.response = Response()
        attrs = {'_response_cache_for':100}
        request.__dict__.update(attrs)
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.cache_control.max_age, 100)

    def test_with_alternate_response_factory(self):
        from pyramid.interfaces import IResponseFactory
        class ResponseFactory(object):
            def __init__(self):
                pass
        self.config.registry.registerUtility(ResponseFactory, IResponseFactory)
        request = testing.DummyRequest()
        helper = self._makeOne('loo.foo')
        response = helper._make_response(b'abc', request)
        self.assertEqual(response.__class__, ResponseFactory)
        self.assertEqual(response.body, b'abc')

    def test__make_response_with_real_request(self):
        # functional
        from pyramid.request import Request
        request = Request({})
        request.registry = self.config.registry
        request.response.status = '406 You Lose'
        helper = self._makeOne('loo.foo')
        response = helper._make_response('abc', request)
        self.assertEqual(response.status, '406 You Lose')
        self.assertEqual(response.body, b'abc')

    def test_clone_noargs(self):
        helper = self._makeOne('name', 'package', 'registry')
        cloned_helper = helper.clone()
        self.assertEqual(cloned_helper.name, 'name')
        self.assertEqual(cloned_helper.package, 'package')
        self.assertEqual(cloned_helper.registry, 'registry')
        self.assertFalse(helper is cloned_helper)

    def test_clone_allargs(self):
        helper = self._makeOne('name', 'package', 'registry')
        cloned_helper = helper.clone(name='name2', package='package2',
                                     registry='registry2')
        self.assertEqual(cloned_helper.name, 'name2')
        self.assertEqual(cloned_helper.package, 'package2')
        self.assertEqual(cloned_helper.registry, 'registry2')
        self.assertFalse(helper is cloned_helper)

    def test_renderer_absolute_file(self):
        registry = self.config.registry
        settings = {}
        registry.settings = settings
        from pyramid.interfaces import IRendererFactory
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        fixture = os.path.join(here, 'fixtures/minimal.pt')
        def factory(info, **kw):
            return info
        self.config.registry.registerUtility(
            factory, IRendererFactory, name='.pt')
        result = self._makeOne(fixture).renderer
        self.assertEqual(result.registry, registry)
        self.assertEqual(result.type, '.pt')
        self.assertEqual(result.package, None)
        self.assertEqual(result.name, fixture)
        self.assertEqual(result.settings, settings)

    def test_renderer_with_package(self):
        import pyramid
        registry = self.config.registry
        settings = {}
        registry.settings = settings
        from pyramid.interfaces import IRendererFactory
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        fixture = os.path.join(here, 'fixtures/minimal.pt')
        def factory(info, **kw):
            return info
        self.config.registry.registerUtility(
            factory, IRendererFactory, name='.pt')
        result = self._makeOne(fixture, pyramid).renderer
        self.assertEqual(result.registry, registry)
        self.assertEqual(result.type, '.pt')
        self.assertEqual(result.package, pyramid)
        self.assertEqual(result.name, fixture)
        self.assertEqual(result.settings, settings)

    def test_renderer_missing(self):
        inst = self._makeOne('foo')
        self.assertRaises(ValueError, getattr, inst, 'renderer')

class TestNullRendererHelper(unittest.TestCase):
    def setUp(self):
        self.config = cleanUp()

    def tearDown(self):
        cleanUp()

    def _makeOne(self, *arg, **kw):
        from pyramid.renderers import NullRendererHelper
        return NullRendererHelper(*arg, **kw)

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IRendererInfo
        helper = self._makeOne()
        verifyObject(IRendererInfo, helper)

    def test_render_view(self):
        helper = self._makeOne()
        self.assertEqual(helper.render_view(None, True, None, None), True)

    def test_render(self):
        helper = self._makeOne()
        self.assertEqual(helper.render(True, None, None), True)

    def test_render_to_response(self):
        helper = self._makeOne()
        self.assertEqual(helper.render_to_response(True, None, None), True)

    def test_clone(self):
        helper = self._makeOne()
        self.assertTrue(helper.clone() is helper)

class Test_render(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, renderer_name, value, request=None, package=None):
        from pyramid.renderers import render
        return render(renderer_name, value, request=request, package=package)

    def test_it_no_request(self):
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        result = self._callFUT('abc/def.pt', dict(a=1))
        self.assertEqual(result, 'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=None)
        
    def test_it_with_request(self):
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        request = testing.DummyRequest()
        result = self._callFUT('abc/def.pt',
                               dict(a=1), request=request)
        self.assertEqual(result, 'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=request)

    def test_it_with_package(self):
        import pyramid.tests
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        request = testing.DummyRequest()
        result = self._callFUT('abc/def.pt', dict(a=1), request=request,
                               package=pyramid.tests)
        self.assertEqual(result, 'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=request)

class Test_render_to_response(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, renderer_name, value, request=None, package=None):
        from pyramid.renderers import render_to_response
        return render_to_response(renderer_name, value, request=request,
                                  package=package)

    def test_it_no_request(self):
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        response = self._callFUT('abc/def.pt', dict(a=1))
        self.assertEqual(response.body, b'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=None)
        
    def test_it_with_request(self):
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        request = testing.DummyRequest()
        response = self._callFUT('abc/def.pt',
                                 dict(a=1), request=request)
        self.assertEqual(response.body, b'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=request)

    def test_it_with_package(self):
        import pyramid.tests
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        renderer.string_response = 'abc'
        request = testing.DummyRequest()
        response = self._callFUT('abc/def.pt', dict(a=1), request=request,
                                 package=pyramid.tests)
        self.assertEqual(response.body, b'abc')
        renderer.assert_(a=1)
        renderer.assert_(request=request)

class Test_get_renderer(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, renderer_name, **kw):
        from pyramid.renderers import get_renderer
        return get_renderer(renderer_name, **kw)

    def test_it_no_package(self):
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        result = self._callFUT('abc/def.pt')
        self.assertEqual(result, renderer)

    def test_it_with_package(self):
        import pyramid.tests
        renderer = self.config.testing_add_renderer(
            'pyramid.tests:abc/def.pt')
        result = self._callFUT('abc/def.pt', package=pyramid.tests)
        self.assertEqual(result, renderer)

class TestJSONP(unittest.TestCase):
    def _makeOne(self, param_name='callback'):
        from pyramid.renderers import JSONP
        return JSONP(param_name)

    def test_render_to_jsonp(self):
        renderer_factory = self._makeOne()
        renderer = renderer_factory(None)
        request = testing.DummyRequest()
        request.GET['callback'] = 'callback'
        result = renderer({'a':'1'}, {'request':request})
        self.assertEqual(result, 'callback({"a": "1"})')
        self.assertEqual(request.response.content_type,
                         'application/javascript')

    def test_render_to_json(self):
        renderer_factory = self._makeOne()
        renderer = renderer_factory(None)
        request = testing.DummyRequest()
        result = renderer({'a':'1'}, {'request':request})
        self.assertEqual(result, '{"a": "1"}')
        self.assertEqual(request.response.content_type,
                         'application/json')


class Dummy:
    pass

class DummyResponse:
    status = '200 OK'
    headerlist = ()
    app_iter = ()
    body = ''

class DummyFactory:
    def __init__(self, renderer):
        self.renderer = renderer

    def __call__(self, path, lookup, **kw):
        self.path = path
        self.kw = kw
        return self.renderer
    

class DummyRendererInfo(object):
    def __init__(self, kw):
        self.__dict__.update(kw)
        
