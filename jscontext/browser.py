import sys, re
import logging
from urllib2 import Request, urlopen, HTTPError
from urlparse import urlparse
from email.utils import formatdate

import PyV8, w3c

import BeautifulSoup

class Navigator(PyV8.JSClass):
    _js_log = logging.getLogger("navigator.base")

    appCodeName = ''
    appName = ''
    appVersion = ''
    cookieEnabled = False
    platform = ''
    javaEnabled = False
    taintEnabled = False

    def __init__(self, win=None, ua='Unknown/Unknown'):
        self._win = win
        self.userAgent = ua

        m = re.match(r'^(\w+)\/(.+)$', ua)

        if(m):
            self.appCodeName = m.group(1)
            self.appVersion = m.group(2)

        if(ua.find("Windows") >= 0):
            self.platform = "Win32"
        elif(ua.find("Mac OS") >= 0):
            self.platform = "MacPPC"
        elif(ua.find("Linux") >= 0):
            self.platform = "Linux"

    @property
    def window(self):
        return self._win

    @property
    def userLanguage(self):
        import locale

        return locale.getdefaultlocale()[0]

    def fetch(self, url):
        self._js_log.debug("fetching HTML from %s", url)
        
        request = Request(url)
        request.add_header('User-Agent', self.userAgent)
        request.add_header('Referer', self._win.url)
        if self._win.doc.cookie:
            request.add_header('Cookie', self._win.doc.cookie)

        response = urlopen(request)

        if response.code != 200:
            self._js_log.warn("fail to fetch HTML from %s, code=%d, msg=%s", url, response.code, response.msg)
            
            raise HTTPError(url, response.code, "fail to fetch HTML", response.info(), 0)

        headers = response.info()
        kwds = { 'referer': self._win.url }

        if headers.has_key('set-cookie'):
            kwds['cookie'] = headers['set-cookie']

        if headers.has_key('last-modified'):
            kwds['lastModified'] = headers['last-modified']

        return response.read(), kwds

class Webkit(Navigator):
    def __init__(self, win=None, ua="Mozilla/5.0 (Windows NT 5.1) AppleWebkit/535.1 (KHTML, like Gecko) Chrome/14.0.825.0 Safari/535.1"):
        super(Webkit, self).__init__(win, ua)
        self.appName = "Netscape"
        self.cookieEnabled = True

class Gecko(Navigator):
    def __init__(self, win=None, ua="Mozilla/5.0 (Windows NT 5.1; rv:8.0.1) Gecko/20100101 Firefox/8.0.1"):
        super(Gecko, self).__init__(win, ua)
        self.appName = "Netscape"
        self.cookieEnabled = True

class Trident(Navigator):
    def __init__(self, win=None, ua="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)"):
        super(Trident, self).__init__(win, ua)
        self.appName = "Microsoft Internet Explorer"
        self.cookieEnabled = True

def matchNavigator(ua):
    if(ua.find("Chrome")):
        return Webkit(ua=ua)
    elif(ua.find("Gecko")):
        return Gecko(ua=ua)
    elif(ua.find("MSIE")):
        return Trident(ua=ua)
    else:
        return Trident()

class Location(PyV8.JSClass):
    def __init__(self, win):
        self.win = win

    @property
    def parts(self):
        return urlparse(self.win.url)

    @property
    def href(self):
        return self.win.url

    @href.setter
    def href(self, url):
        self.win.open(url)

    @property
    def protocol(self):
        return self.parts.scheme

    @property
    def host(self):
        return self.parts.netloc

    @property
    def hostname(self):
        return self.parts.hostname

    @property
    def port(self):
        return self.parts.port

    @property
    def pathname(self):
        return self.parts.path

    @property
    def search(self):
        return self.parts.query

    @property
    def hash(self):
        return self.parts.fragment

    def assign(self, url):
        """Loads a new HTML document."""
        self.win.open(url)

    def reload(self):
        """Reloads the current page."""
        self.win.open(self.win.url)

    def replace(self, url):
        """Replaces the current document by loading another document at the specified URL."""
        self.win.open(url)

class Screen(PyV8.JSClass):
    def __init__(self, width, height, depth=32):
        self._width = width
        self._height = height
        self._depth = depth

    @property
    def availWidth(self):
        return self._width

    @property
    def availHeight(self):
        return self._height

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def colorDepth(self):
        return self._depth

    @property
    def pixelDepth(self):
        return self._depth

class History(PyV8.JSClass):
    def __init__(self, win):
        self._win = win
        self.urls = []
        self.pos = None

    @property
    def window(self):
        return self._win

    @property
    def length(self):
        """the number of URLs in the history list"""
        return len(self.urls)

    def back(self):
        """Loads the previous URL in the history list"""
        return self.go(-1)

    def forward(self):
        """Loads the next URL in the history list"""
        return self.go(1)

    def go(self, num_or_url):
        """Loads a specific URL from the history list"""
        try:
            off = int(num_or_url)

            self.pos += off
            self.pos = min(max(0, self.pos), len(self.urls)-1)

            self._win.open(self.urls[self.pos])
        except ValueError:
            self._win.open(num_or_url)

    def update(self, url, replace=False):
        if self.pos is None:
            self.urls.append(url)
            self.pos = 0
        elif replace:
            self.urls[self.pos] = url
        elif self.urls[self.pos] != url:
            self.urls = self.urls[:self.pos+1]
            self.urls.append(url)
            self.pos += 1

class HtmlWindow(PyV8.JSClass):
    _js_log = logging.getLogger("html.window")

    class Timer(object):
        def __init__(self, code, repeat, lang='JavaScript'):
            self.code = code
            self.repeat = repeat
            self.lang = lang

    _js_timers = []

    def __init__(self, url, dom_or_doc, navigator_or_class=Trident, name="", target='_blank',
                 parent=None, opener=None, replace=False, screen=None, width=800, height=600, left=0, top=0, **kwds):
        self.url = url
        self.doc = w3c.getDOMImplementation(dom_or_doc, **kwds) if isinstance(dom_or_doc, BeautifulSoup.BeautifulSoup) else dom_or_doc
        self.doc.window = self

        self._navigator = navigator_or_class(self) if type(navigator_or_class) == type else navigator_or_class
        self._location = Location(self)
        self._history = History(self)

        self._history.update(url, replace)

        self._target = target
        self._parent = parent
        self._opener = opener
        self._screen = screen or Screen(width, height, 32)
        self._closed = False

        self.name = name
        self.defaultStatus = ""
        self.status = ""
        self._left = left
        self._top = top
        self.innerWidth = width
        self.innerHeight = height
        self.outerWidth = width
        self.outerHeight = height

    @property
    def closed(self):
        """whether a window has been closed or not"""
        return self._closed

    def close(self):
        """Closes the current window"""
        self._closed = True

    @property
    def window(self):
        return self

    @property
    def document(self):
        return self.doc

    def _findAll(self, tags):
        return self.doc.doc.findAll(tags, recursive=True)

    @property
    def frames(self):
        """an array of all the frames (including iframes) in the current window"""
        return w3c.HTMLCollection(self.doc, [self.doc.createHTMLElement(self.doc, f) for f in self._findAll(['frame', 'iframe'])])

    @property
    def length(self):
        """the number of frames (including iframes) in a window"""
        return len(self._findAll(['frame', 'iframe']))

    @property
    def history(self):
        """the History object for the window"""
        return self._history

    @property
    def location(self):
        """the Location object for the window"""
        return self._location

    @property
    def navigator(self):
        """the Navigator object for the window"""
        return self._navigator

    @property
    def opener(self):
        """a reference to the window that created the window"""
        return self._opener

    @property
    def pageXOffset(self):
        return 0

    @property
    def pageYOffset(self):
        return 0

    @property
    def parent(self):
        return self._parent

    @property
    def screen(self):
        return self._screen

    @property
    def screenLeft(self):
        return self._left

    @property
    def screenTop(self):
        return self._top

    @property
    def screenX(self):
        return self._left

    @property
    def screenY(self):
        return self._top

    @property
    def self(self):
        return self

    @property
    def top(self):
        return self

    def alert(self, msg):
        """Displays an alert box with a message and an OK button"""
        print "ALERT: ", str(msg).decode('utf-8')

    def confirm(self, msg):
        """Displays a dialog box with a message and an OK and a Cancel button"""
        ret = raw_input("CONFIRM: %s [Y/n] " % msg)

        return ret in ['', 'y', 'Y', 't', 'T']

    def focus(self):
        """Sets focus to the current window"""
        pass

    def blur(self):
        """Removes focus from the current window"""
        pass

    def moveBy(self, x, y):
        """Moves a window relative to its current position"""
        pass

    def moveTo(self, x, y):
        """Moves a window to the specified position"""
        pass

    def resizeBy(self, w, h):
        """Resizes the window by the specified pixels"""
        pass

    def resizeTo(self, w, h):
        """Resizes the window to the specified width and height"""
        pass

    def scrollBy(self, xnum, ynum):
        """Scrolls the content by the specified number of pixels"""
        pass

    def scrollTo(self, xpos, ypos):
        """Scrolls the content to the specified coordinates"""
        pass

    def setTimeout(self, code, interval, lang="JavaScript"):
        timer = HtmlWindow.Timer(code, False, lang)
        self._js_timers.append((interval, timer))

        return len(self._js_timers)-1

    def clearTimeout(self, idx):
        self._js_timers[idx] = None

    def setInterval(self, code, interval, lang="JavaScript"):
        timer = HtmlWindow.Timer(code, True, lang)
        self._js_timers.append((interval, timer))

        return len(self._js_timers)-1

    def clearInterval(self, idx):
        self._js_timers[idx] = None

    def createPopup(self):
        raise NotImplementedError()

    def open(self, url=None, name='_blank', specs='', replace=False):
        self._js_log.info("window.open(url='%s', name='%s', specs='%s')", url, name, specs)
        
        if url:
            html, kwds = self._navigator.fetch(url)
        else:
            url = 'about:blank'
            html = ''
            kwds = {}

        dom = BeautifulSoup.BeautifulSoup(html)

        for spec in specs.split(','):
            spec = [s.strip() for s in spec.split('=')]

            if len(spec) == 2:
                if spec[0] in ['width', 'height', 'left', 'top']:
                    kwds[spec[0]] = int(spec[1])

        if name in ['_blank', '_parent', '_self', '_top']:
            kwds['target'] = name
            name = ''
        else:
            kwds['target'] = '_blank'

        return HtmlWindow(url, dom, self._navigator, name, parent=self, opener=self, replace=replace, **kwds)

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = PyV8.JSContext(self)

        return self._context

    def evalScript(self, script, tag=None):
        if isinstance(script, unicode):
            script = script.encode('utf-8')

        if tag:
            self.doc.current = tag
        else:
            body = self.doc.body

            self.doc.current = body.tag.contents[-1] if body else self.doc.doc.contents[-1]

        self._js_log.debug("executing script: %s", script)

        with self.context as ctxt:
            ctxt.eval(script)

    def fireOnloadEvents(self):
        for tag in self._findAll('script'):
            self.evalScript(tag.string, tag=tag)

        body = self.doc.body

        if body and body.tag.has_key('onload'):
            self.evalScript(body.tag['onload'], tag=body.tag.contents[-1])

        if hasattr(self, 'onload'):
            self.evalScript(self.onload)

    def fireExpiredTimer(self):
        pass

    def Image(self):
        return self.doc.createElement('img')

import unittest

TEST_URL = 'http://localhost:8080/path?query=key#frag'
TEST_HTML = """
<html>
<head>
    <title></title>
</head>
<body onload='load()'>
    <frame src="#"/>
    <iframe src="#"/>
    <script>
    function load()
    {
        alert('onload');
    }
    document.write("<p id='hello'>world</p>");
    </script>
</body>
</html>
"""

class HtmlWindowTest(unittest.TestCase):
    def setUp(self):
        self.doc = w3c.parseString(TEST_HTML)
        self.win = HtmlWindow(TEST_URL, self.doc)

    def testWindow(self):
        self.assertEquals(self.doc, self.win.document)
        self.assertEquals(self.win, self.win.window)
        self.assertEquals(self.win, self.win.self)

        self.assertFalse(self.win.closed)
        self.win.close()
        self.assert_(self.win.closed)

        self.assertEquals(2, self.win.frames.length)
        self.assertEquals(2, self.win.length)
        
        self.assertEquals(1, self.win.history.length)

        loc = self.win.location

        self.assert_(loc)
        self.assertEquals("frag", loc.hash)
        self.assertEquals("localhost:8080", loc.host)
        self.assertEquals("localhost", loc.hostname)
        self.assertEquals(TEST_URL, loc.href)
        self.assertEquals("/path", loc.pathname)
        self.assertEquals(8080, loc.port)
        self.assertEquals("http", loc.protocol)
        self.assertEquals("query=key", loc.search)

    def testOpen(self):
        url = 'http://www.google.com'
        win = self.win.open(url, specs="width=640, height=480")
        self.assertEquals(url, win.url)

        self.assert_(win.document)
        self.assertEquals(url, win.document.URL)
        self.assertEquals('www.google.com', win.document.domain)
        self.assertEquals(640, win.innerWidth)
        self.assertEquals(480, win.innerHeight)

    def testScript(self):
        self.win.fireOnloadEvents()

        tag = self.doc.getElementById('hello')

        self.assertEquals(u'P', tag.nodeName)

    def testTimer(self):
        pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')

    unittest.main()