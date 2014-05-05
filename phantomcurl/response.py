"""
The Response class is the result of network request maden with Grab instance.
"""
import re
from copy import copy
import logging
try:
    from urllib2 import Request
except ImportError:
    from urllib.request import Request
import os
import json
try:
    from urlparse import urlsplit, parse_qs
except ImportError:
    from urllib.parse import urlsplit, parse_qs
import tempfile
import webbrowser
import codecs


RE_XML_DECLARATION = re.compile(br'^[^<]{,100}<\?xml[^>]+\?>', re.I)
RE_DECLARATION_ENCODING = re.compile(br'encoding\s*=\s*["\']([^"\']+)["\']')
RE_META_CHARSET = re.compile(br'<meta[^>]+content\s*=\s*[^>]+charset=([-\w]+)',
                             re.I)

# Bom processing logic was copied from
# https://github.com/scrapy/w3lib/blob/master/w3lib/encoding.py
_BOM_TABLE = [
    (codecs.BOM_UTF32_BE, 'utf-32-be'),
    (codecs.BOM_UTF32_LE, 'utf-32-le'),
    (codecs.BOM_UTF16_BE, 'utf-16-be'),
    (codecs.BOM_UTF16_LE, 'utf-16-le'),
    (codecs.BOM_UTF8, 'utf-8')
]

_FIRST_CHARS = set(char[0] for (char, name) in _BOM_TABLE)

def read_bom(data):
    """Read the byte order mark in the text, if present, and 
    return the encoding represented by the BOM and the BOM.

    If no BOM can be detected, (None, None) is returned.
    """
    # common case is no BOM, so this is fast
    if data and data[0] in _FIRST_CHARS:
        for bom, encoding in _BOM_TABLE:
            if data.startswith(bom):
                return encoding, bom
    return None, None


class Response(object):
    """
    HTTP Response.
    """

    def __init__(self):
        self.status = None
        self.code = None
        self.head = None
        self._body = None
        self._runtime_body = None
        #self.runtime_body = None
        self.body_path = None
        self.headers =None
        self.time = None
        self.url = None
        self.cookies = {}
        #self.cookiejar = None
        self.charset = 'utf-8'
        self._unicode_body = None
        self._unicode_runtime_body = None
        self.bom = None
        self.done_time = None


    def process_unicode_body(self, body, bom, charset, ignore_errors, fix_special_entities):
        if isinstance(body, unicode):
            #if charset in ('utf-8', 'utf8'):
            #    return body.strip()
            #else:
            #    body = body.encode('utf-8')
            #
            body = body.encode('utf-8')
        if bom:
            body = body[len(self.bom):]
        if ignore_errors:
            errors = 'ignore'
        else:
            errors = 'strict'
        return body.decode(charset, errors).strip()

    def unicode_body(self, ignore_errors=True, fix_special_entities=True):
        """
        Return response body as unicode string.
        """

        self._check_body()
        if not self._unicode_body:
            self._unicode_body = self.process_unicode_body(
                self._body, self.bom, self.charset,
                ignore_errors, fix_special_entities)
        return self._unicode_body

    def unicode_runtime_body(self, ignore_errors=True, fix_special_entities=True):
        """
        Return response body as unicode string.
        """

        if not self._unicode_runtime_body:
            self._unicode_runtime_body = self.process_unicode_body(
                self.runtime_body, None, self.charset,
                ignore_errors, fix_special_entities)
        return self._unicode_runtime_body



    @property
    def json(self):
        """
        Return response body deserialized into JSON object.
        """

        return json.loads(self.body)

    def url_details(self):
        """
        Return result of urlsplit function applied to response url.
        """

        return urlsplit(self.url) 

    def query_param(self, key):
        """
        Return value of parameter in query string.
        """

        return parse_qs(self.url_details().query)[key][0]


    def _check_body(self):
        if not self._body:
            if self.body_path:
                with open(self.body_path, 'rb') as inp:
                    self._body = inp.read()

    def _read_body(self):
        # py3 hack
        if PY3K:
            return self.unicode_body()

        self._check_body()
        return self._body

    def _write_body(self, body):
        self._body = body
        self._unicode_body = None

    body = property(_read_body, _write_body)

    def _read_runtime_body(self):
        if self._runtime_body is None:
            return self._body
        else:
            return self._runtime_body

    def _write_runtime_body(self, body):
        self._runtime_body = body
        self._unicode_runtime_body = None

    runtime_body = property(_read_runtime_body, _write_runtime_body)

    def body_as_bytes(self, encode=False):
        self._check_body()
        if encode:
            return self.body.encode(self.charset)
        return self._body