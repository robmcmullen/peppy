#   Copyright (c) 2006-2007 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import httplib, copy, base64, StringIO, re
import urllib

from peppy.vfs.utils import get_authentication_callback
from itools.uri import Path, Reference
from peppy.debug import dprint

try:
    from xml.etree import ElementTree
except:
    from elementtree import ElementTree

__all__ = ['DAVClient']

def object_to_etree(parent, obj, namespace=''):
    """This function takes in a python object, traverses it, and adds it to an existing etree object"""
    
    if type(obj) is int or type(obj) is float or type(obj) is str:
        # If object is a string, int, or float just add it
        obj = str(obj)
        if obj.startswith('{') is False:
            ElementTree.SubElement(parent, '{%s}%s' % (namespace, obj))
        else:
            ElementTree.SubElement(parent, obj)
        
    elif type(obj) is dict:
        # If the object is a dictionary we'll need to parse it and send it back recusively
        for key, value in obj.items():
            if key.startswith('{') is False:
                key_etree = ElementTree.SubElement(parent, '{%s}%s' % (namespace, key))
                object_to_etree(key_etree, value, namespace=namespace)
            else:
                key_etree = ElementTree.SubElement(parent, key)
                object_to_etree(key_etree, value, namespace=namespace)
            
    elif type(obj) is list:
        # If the object is a list parse it and send it back recursively
        for item in obj:
            object_to_etree(parent, item, namespace=namespace)
            
    else:
        # If it's none of previous types then raise
        raise TypeError, '%s is an unsupported type' % type(obj)
        


class DAVClient(object):
    credentials = {}
    
    def __init__(self, ref):
        """Initialization
        
        @param ref: uri Reference object
        """
        
        self._ref = ref
        self._url = ref.authority.host
        if ref.authority.port:
            self._url += ":" + ref.authority.port
        
        self.headers = {'Host':self._url, 
                        'User-Agent': 'python.davclient.DAVClient/0.1'}
        
        if ref.authority.userinfo:
            if ":" in ref.authority.userinfo:
                username, passwd = ref.authority.userinfo.split(":")
            else:
                username = ref.authority.userinfo
                passwd = ""
            self.set_basic_auth(username, passwd)
        elif self._url in self.credentials:
            username, passwd = self.credentials[self._url]
            self._set_basic_auth(username, passwd)
        else:
            self._username = self._password = None
    
    scheme_map = {
        'http': httplib.HTTPConnection,
        'webdav': httplib.HTTPConnection,
        'https': httplib.HTTPSConnection,
        'webdavs': httplib.HTTPSConnection,
        }
    
    def _request(self, method, path='', body=None, headers=None):
        """Internal request method"""
        retry = True
        while retry:
            self.response = None
            
            connection_headers = copy.copy(self.headers)
            if headers:
                connection_headers.update(headers)
            
            try:
                self._connection = self.scheme_map[self._ref.scheme](self._url, strict=0)
            except KeyError:
                raise Exception, 'Unsupported scheme'
            
#            dprint(method)
#            dprint(path)
#            dprint(body)
#            dprint(connection_headers)
            self._connection.request(method, path, body, connection_headers)
            
            self.response = self._connection.getresponse()
            if self.response.status == 401:
                scheme, realm = self.get_realm_from_response(self.response)
                if realm:
                    retry = self.request_auth_from_user(scheme, realm)
                else:
                    retry = False
            else:
                self.response.body = self.response.read()
                
                # Try to parse and get an etree
                try:
                    self._get_response_tree()
                    #dprint(self.response.tree)
                except:
                    #dprint("Failed converting to etree")
                    #dprint(self.response.body)
                    #raise
                    pass
                return
            
    def _get_response_tree(self):
        """Parse the response body into an elementree object"""
        self.response.tree = ElementTree.fromstring(self.response.body)
        return self.response.tree
        
    def _set_basic_auth(self, username, password):
        """Private method to set header information for basic authentication"""
        auth = 'Basic %s' % base64.encodestring('%s:%s' % (username, password)).strip()
        self._username = username
        self._password = password
        self.headers['Authorization'] = auth
        
    def set_basic_auth(self, username, password):
        """Public method to cache basic authentication"""
        self._set_basic_auth(username, password)
        self.credentials[self._url] = (username, password)
    
    def get_realm_from_response(self, response):
#        dprint(response.getheaders())
        header = response.getheader('www-authenticate')
        if header:
            matches = re.findall('[ \t]*([^ \t]+)[ \t]+realm="([^"]*)"', header)
            for scheme, realm in matches:
#                print("scheme=%s, realm=%s" % (scheme, realm))
                if scheme == "Basic":
                    return scheme, realm
        return None, None
    
    def request_auth_from_user(self, scheme, realm):
#        dprint("Requesting auth from user for realm %s" % realm)
        callback = get_authentication_callback()
        
        username, passwd = callback(self._url, scheme, realm, self._username)
#        dprint("username=%s password=%s" % (username, passwd))
        if username is not None:
            self.set_basic_auth(username, passwd)
            return True
        return False
        
    ## HTTP DAV methods ##
        
    def get(self, path, headers=None):
        """Simple get request"""
        self._request('GET', path, headers=headers)
        return self.response.body
        
    def head(self, path, headers=None):
        """Basic HEAD request"""
        self._request('HEAD', path, headers=headers)
        
    def put(self, path, body=None, f=None, headers=None):
        """Put resource with body"""
        if f is not None:
            body = f.read()
            
        self._request('PUT', path, body=body, headers=headers)
        
    def post(self, path, body=None, headers=None):
        """POST resource with body"""

        self._request('POST', path, body=body, headers=headers)
        
    def mkcol(self, path, headers=None):
        """Make DAV collection"""
        self._request('MKCOL', path=path, headers=headers)
        
    make_collection = mkcol
        
    def delete(self, path, headers=None):
        """Delete DAV resource"""
        self._request('DELETE', path=path, headers=headers)
        
    def copy(self, source, destination, body=None, depth='infinity', overwrite=True, headers=None):
        """Copy DAV resource"""
        # Set all proper headers
        if headers is None:
            headers = {'Destination':destination}
        else:
            headers['Destination'] = self._ref.resolve2(destination)
        if overwrite is False:
            headers['Overwrite'] = 'F'
        headers['Depth'] = depth
            
        self._request('COPY', source, body=body, headers=headers)
        
        
    def copy_collection(self, source, destination, depth='infinity', overwrite=True, headers=None):
        """Copy DAV collection"""
        body = '<?xml version="1.0" encoding="utf-8" ?><d:propertybehavior xmlns:d="DAV:"><d:keepalive>*</d:keepalive></d:propertybehavior>'
        
        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        self.copy(source, destination, body=unicode(body, 'utf-8'), depth=depth, overwrite=overwrite, headers=headers)
        
        
    def move(self, source, destination, body=None, depth='infinity', overwrite=True, headers=None):
        """Move DAV resource"""
        # Set all proper headers
        if headers is None:
            headers = {'Destination':destination}
        else:
            headers['Destination'] = self._ref.resolve2(destination)
        if overwrite is False:
            headers['Overwrite'] = 'F'
        headers['Depth'] = depth
            
        self._request('MOVE', source, body=body, headers=headers)
        
        
    def move_collection(self, source, destination, depth='infinity', overwrite=True, headers=None):
        """Move DAV collection and copy all properties"""
        body = '<?xml version="1.0" encoding="utf-8" ?><d:propertybehavior xmlns:d="DAV:"><d:keepalive>*</d:keepalive></d:propertybehavior>'
        
        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'

        self.move(source, destination, unicode(body, 'utf-8'), depth=depth, overwrite=overwrite, headers=headers)
        
        
    def propfind(self, path, properties='allprop', namespace='DAV:', depth=None, headers=None):
        """Property find. If properties arg is unspecified it defaults to 'allprop'"""
        # Build propfind xml
        root = ElementTree.Element('{DAV:}propfind')
        if type(properties) is str:
            ElementTree.SubElement(root, '{DAV:}%s' % properties)
        else:
            props = ElementTree.SubElement(root, '{DAV:}prop')
            object_to_etree(props, properties, namespace=namespace)
        tree = ElementTree.ElementTree(root)
        
        # Etree won't just return a normal string, so we have to do this
        body = StringIO.StringIO()
        tree.write(body)
        body = body.getvalue()
                
        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers['Depth'] = depth
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        # Body encoding must be utf-8, 207 is proper response
        self._request('PROPFIND', path, body=unicode('<?xml version="1.0" encoding="utf-8" ?>\n'+body, 'utf-8'), headers=headers)
        
        if self.response is not None and hasattr(self.response, 'tree') is True:
            property_responses = {}
            for response in self.response.tree._children:
                property_href = response.find('{DAV:}href')
                property_stat = response.find('{DAV:}propstat')
                
                def parse_props(props):
                    property_dict = {}
                    for prop in props:
                        if prop.tag.find('{DAV:}') is not -1:
                            name = prop.tag.split('}')[-1]
                        else:
                            name = prop.tag
                        if len(prop._children) is not 0:
                            property_dict[name] = parse_props(prop._children)
                        else:
                            property_dict[name] = prop.text
                    return property_dict
                
                if property_href is not None and property_stat is not None:
                    property_dict = parse_props(property_stat.find('{DAV:}prop')._children)
                    property_responses[property_href.text] = property_dict
            return property_responses
        
    def proppatch(self, path, set_props=None, remove_props=None, namespace='DAV:', headers=None):
        """Patch properties on a DAV resource. If namespace is not specified the DAV namespace is used for all properties"""
        root = ElementTree.Element('{DAV:}propertyupdate')
        
        if set_props is not None:
            prop_set = ElementTree.SubElement(root, '{DAV:}set')
            object_to_etree(prop_set, set_props, namespace=namespace)
        if remove_props is not None:
            prop_remove = ElementTree.SubElement(root, '{DAV:}remove')
            object_to_etree(prop_remove, remove_props, namespace=namespace)
        
        tree = ElementTree.ElementTree(root)
        
        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        self._request('PROPPATCH', path, body=unicode('<?xml version="1.0" encoding="utf-8" ?>\n'+body, 'utf-8'), headers=headers)
        
        
    def set_lock(self, path, owner, locktype='write', lockscope='exclusive', depth=None, headers=None):
        """Set a lock on a dav resource"""
        body = """<D:lockinfo xmlns:D='DAV:'>
     <D:lockscope><D:%s/></D:lockscope>
     <D:locktype><D:%s/></D:locktype>
     <D:owner>
          <D:href>%s</D:href>
     </D:owner>
   </D:lockinfo>""" % (lockscope, locktype, owner)
        
        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers['Depth'] = depth
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        headers['Timeout'] = 'Infinite, Second-4100000000'
        
        self._request('LOCK', path, body=unicode('<?xml version="1.0" encoding="utf-8" ?>\n'+body, 'utf-8'), headers=headers)
        
        locks = self.response.tree.findall('.//{DAV:}locktoken')
        lock_list = []
        for lock in locks:
            lock_list.append(lock.getchildren()[0].text.strip().strip('\n'))
        return lock_list
        

    def refresh_lock(self, path, token, headers=None):
        """Refresh lock with token"""
        
        if headers is None:
            headers = {}
        headers['If'] = '(<%s>)' % token
        headers['Timeout'] = 'Infinite, Second-4100000000'
        
        self._request('LOCK', path, body=None, headers=headers)
        
        
    def unlock(self, path, token, headers=None):
        """Unlock DAV resource with token"""
        if headers is None:
            headers = {}
        headers['Lock-Tocken'] = '<%s>' % token
        
        self._request('UNLOCK', path, body=None, headers=headers)
        





