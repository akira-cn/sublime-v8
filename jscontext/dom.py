from BeautifulSoup import BeautifulSoup, Tag, NavigableString, Comment
from PyV8 import JSClass, JSArray

def normalizeNode(node = None):
	if('_Node__wrap' in dir(node)):
		return node._Node__wrap
	if(isinstance(node, BeautifulSoup)): #Document
		return Document(node)
	if(isinstance(node, Tag)):	#ElementNode
		return ElementNode(node)
	elif(isinstance(node, NavigableString)): #TextNode
		return TextNode(node)
	elif(isinstance(node, Comment)): #CommentNode
		return CommentNode(node)
	
	return node	

class DomDocument(JSClass):
	def __init__(self, source):
		if(not isinstance(source, BeautifulSoup)):
			source = BeautifulSoup(source)
		self._soup = source
		self.nodeType = 9
	def getElementById(self, id):
		node = self._soup.find(id=id)
		return normalizeNode(node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	def createElement(self, tagName):
		return normalizeNode(BeautifulSoup(tagName).contents[0])
	@property	
	def body(self):
		return normalizeNode(self._soup.find('body'))

class Node(JSClass, object): #baseclass
	def __init__(self, soup):
		soup.__wrap = self
		self._soup = soup

	@property
	def parentNode(self):
		return normalizeNode(self._soup.parent)

	@property
	def parentElement(self):
		return normalizeNode(self._soup.parent)
	
	@property	
	def ownerDocument(self):
		return normalizeNode(self._soup.findParents()[-1])
	
	@property
	def nextSibling(self):
		return normalizeNode(self._soup.nextSibling)
	
	@property
	def previousSibling(self):
		return normalizeNode(self._soup.previousSibling)

class ElementNode(Node):
	def __init__(self, node):
		self.nodeType = 1
		Node.__init__(self, node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True		
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	
	@property
	def tagName(self):
		return self._soup.name.upper()
	
	@property
	def nodeName(self):
		return self._soup.name.upper()
	
	@property 
	def childNodes(self):
		node = self._soup
		return JSArray([normalizeNode(node) for node in node.contents])
	
	@property
	def firstChild(self):
		node = self._soup
		if(len(node.contents)):
		 	return normalizeNode(node.contents[0])
	
	def lastChild(self):
		node = self._soup
		if(len(node.contents)):
			return normalizeNode(node.contents[-1])

	@property
	def children(self):
		return JSArray(filter(lambda n: n.nodeType == 1, self.childNodes))

	@property
	def innerHTML(self):
		node = self._soup
		return ''.join([unicode(n).encode('utf-8') for n in node.contents])
	@innerHTML.setter
	def innerHTML(self, html):
		self._soup.contents = BeautifulSoup(html).contents
	
	@property
	def outerHTML(self):
		return unicode(self._soup).encode('utf-8')
		
	@property
	def textContent(self):
		return self._soup.getText()

	@property
	def name(self):
		return self._soup['name']
	@name.setter
	def name(self, value):
		self._soup['name'] = value

	@property
	def id(self):
		return self._soup['id']
	@id.setter
	def id(self, value):
		self._soup['id'] = value

	@property
	def value(self):
		return self._soup['value']
	@value.setter
	def value(self, value):
		self._soup['value'] = value
	
	@property
	def className(self):
		return self._soup['class']
	@className.setter
	def className(self, value):
		self._soup['class'] = value
	
	@property
	def selected(self):
		return self._soup['selected'] == 'selected'
	@selected.setter
	def selected(self, value):
		if(value == True):
			value = "selected"
		self._soup['selected'] = value

	@property
	def checked(self):
		return self._soup['checked'] == 'checked'
	@checked.setter
	def checked(self, value):
		if(value == True):
			value = "checked"
		self._soup['checked'] = value

	@property
	def disabled(self):
		return self._soup['disabled'] == 'disabled'
	@disabled.setter
	def disabled(self, value):
		if(value == True):
			value = "disabled"
		self._soup['disabled'] = value

	@property
	def type(self):
		return self._soup['type']
	
	@property
	def readOnly(self):
		pass

	def appendChild(self, node):
		return self._soup.append(node)
	
	def removeChild(self, node):
		return self._soup.contents.remove(node._soup)

	def getAttribute(self, attr):
		return self._soup[attr]
	
	def setAttribute(self, attr, value):
		self._soup[attr] = value
	
	def removeAttribute(self, attr):
		del self._soup[attr]

class TextNode(Node):
	def __init__(self, node):
		self.nodeType = 3
		self.nodeName = "#text"
		Node.__init__(self, node)
	
	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')

class CommentNode(Node):
	def __init__(self, node):
		self.nodeType = 8
		self.nodeName = "#comment"
		self.nodeValue = node.encode('utf-8')
		Node.__init__(self, node)

	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')