#!/usr/bin/env python3
# -*-coding: utf8 -*-

'''
GitHub API Python3 SDK.

GPLv3 License

Michael Liao (askxuefeng@gmail.com)

https://github.com/michaelliao/githubpy

Usage:

>>> token = os.getenv('GITHUB_TOKEN') # token from env or other source
>>> proxy = os.getenv('HTTPS_PROXY') # proxy for access https, default to None
>>> gh = GitHub(token, proxy=proxy)
>>> L = gh.users('michaelliao').followers.get()
>>> L[0].login # doctest: +ELLIPSIS
'...'
>>> print('rate limit remaining: ', gh.x_ratelimit_remaining) # doctest: +ELLIPSIS
rate limit remaining: ...
>>> x_ratelimit_limit = gh.x_ratelimit_limit
>>> x_ratelimit_reset = gh.x_ratelimit_reset
>>> L = gh.users('michaelliao').following.get()
>>> L[0].url # doctest: +ELLIPSIS
'https://api.github.com/users/...'
>>> L = gh.repos('michaelliao')('githubpy').issues.get(state='closed', sort='created', direction='asc')
>>> L[0].title
'No license'
>>> L[0].number
1
>>> I = gh.repos('michaelliao')('githubpy').issues(1).get()
>>> I.url
'https://api.github.com/repos/michaelliao/githubpy/issues/1'
>>> new_issue = { 'title': 'New issue test', 'body': 'Test create issue with githubpy', 'assignees': ['michaelliao']}
>>> r = gh.repos('michaelliao')('githubpy').issues.post(new_issue)
>>> r.title
'New issue test'
>>> r.state
'open'
>>> exist = gh.repos('michaelliao')('githubpy').contents('test/café.txt').get() # doctest: +ELLIPSIS
{...}
>>> # update exist file:
>>> import base64, datetime
>>> dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
>>> file_content = bytes('Hello world! ' + dt, 'utf-8')
>>> update = { 'message': 'Update file at ' + dt, 'committer': { 'name': 'Michael', 'email': 'askxuefeng@gmail.com' }, 'content': base64.b64encode(file_content).decode('utf-8'), 'sha': exist.sha }
>>> commit = gh.repos('michaelliao')('githubpy').contents('test/café.txt').put(update)
>>> commit.content.url
'https://api.github.com/repos/michaelliao/githubpy/contents/test/caf%C3%A9.txt?ref=master'
>>> gh.repos.thisisabadurl.get()
Traceback (most recent call last):
    ...
ApiNotFoundError: https://api.github.com/repos/thisisabadurl
>>> gh.users('github-not-exist-user').followers.get()
Traceback (most recent call last):
    ...
ApiNotFoundError: https://api.github.com/users/github-not-exist-user/followers
'''

__version__ = '2.0.0'

from urllib.request import build_opener, HTTPSHandler, HTTPError, Request
from urllib.parse import quote
from io import StringIO

import re, os, time, hmac, base64, hashlib, urllib, mimetypes, json
from collections import namedtuple
from collections.abc import Iterable
from datetime import datetime, timedelta, tzinfo

TIMEOUT = 60

_API_VERSION = '2022-11-28'

_URL = 'https://api.github.com'

_METHOD_MAP = dict(
        GET=lambda: 'GET',
        PUT=lambda: 'PUT',
        POST=lambda: 'POST',
        PATCH=lambda: 'PATCH',
        DELETE=lambda: 'DELETE')

DEFAULT_SCOPE = None

RW_SCOPE = 'user,public_repo,repo,repo:status,gist'

AccessToken = namedtuple('AccessToken', ['access_token', 'scope', 'token_type'])


def _encode_path(path):
    '''
    Encode url path.
    '''
    return quote(path, encoding='utf-8')

def _encode_params(kw):
    '''
    Encode parameters.

    >>> kw = { 'a': 'K&R', 'lang': 'Ελληνικά,Français,中文,日本語', 'page': 1 }
    >>> _encode_params(kw)
    'a=K%26R&lang=%CE%95%CE%BB%CE%BB%CE%B7%CE%BD%CE%B9%CE%BA%CE%AC%2CFran%C3%A7ais%2C%E4%B8%AD%E6%96%87%2C%E6%97%A5%E6%9C%AC%E8%AA%9E&page=1'
    '''
    args = []
    for k, v in kw.items():
        q = quote(str(v), encoding='utf-8')
        args.append(f'{k}={q}')
    return '&'.join(args)

def _encode_json(obj):
    '''
    Encode object as json str.
    '''
    def _dump_obj(obj):
        if isinstance(obj, dict):
            return obj
        d = dict()
        for k in dir(obj):
            if not k.startswith('_'):
                d[k] = getattr(obj, k)
        return d
    return json.dumps(obj)

def _parse_json(jsonstr):
    def _obj_hook(pairs):
        o = JsonObject()
        for k, v in pairs.items():
            o[str(k)] = v
        return o
    return json.loads(jsonstr, object_hook=_obj_hook)

class _Get(object):

    def __init__(self, _gh, _path):
        self._gh = _gh
        self._path = _path

    def __call__(self, **kw):
        return self._gh._http('GET', self._path, None, **kw)

    def __str__(self):
        return f'GET {self._path}'

    __repr__ = __str__

class _Executable(object):

    def __init__(self, _gh, _method, _path):
        self._gh = _gh
        self._method = _method
        self._path = _path

    def __call__(self, data=None):
        return self._gh._http(self._method, self._path, data)

    def __str__(self):
        return '_Executable (%s %s)' % (self._method, self._path)

    __repr__ = __str__

class _Callable(object):

    def __init__(self, _gh, _name):
        self._gh = _gh
        self._name = _name

    def __call__(self, *args):
        n = len(args)
        if n == 0:
            return self
        if n == 1:
            return _Callable(self._gh, self._name + '/' + _encode_path(str(args[0])))
        return _Callable(self._gh, self._name + '/' + '/'.join([_encode_path(str(arg)) for arg in args]))

    def __getattr__(self, attr):
        if attr == 'get':
            return _Get(self._gh, self._name)
        if attr == 'put':
            return _Executable(self._gh, 'PUT', self._name)
        if attr == 'post':
            return _Executable(self._gh, 'POST', self._name)
        if attr == 'patch':
            return _Executable(self._gh, 'PATCH', self._name)
        if attr == 'delete':
            return _Executable(self._gh, 'DELETE', self._name)
        return _Callable(self._gh, f'{self._name}/{attr}')

    def __str__(self):
        return '_Callable (%s)' % self._name

    __repr__ = __str__

class GitHub(object):

    '''
    GitHub client.
    '''

    def __init__(self, token=None, proxy=None, debug=False):
        self.x_ratelimit_remaining = -1
        self.x_ratelimit_limit = -1
        self.x_ratelimit_reset = -1
        self._authorization = f'Bearer {token}' if token else None
        self._debug = debug

    @classmethod
    def authorize_url(cls, client_id, redirect_uri, scope=None, state=None, **kw):
        '''
        Generate authorize_url.

        scope: A space-delimited list of scopes. Default to None (no scope, read-only access to public information). See https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps
        state: An unguessable random string. It is used to protect against cross-site request forgery attacks. Default to None (do not use state).

        >>> GitHub.authorize_url(client_id='3ebf94c5776d565bcf75', redirect_uri='https://example.com/callback', scope='public_repo, user', allow_signup='false')
        'https://github.com/login/oauth/authorize?allow_signup=false&client_id=3ebf94c5776d565bcf75&redirect_uri=https%3A//example.com/callback&scope=public_repo%2C%20user'
        '''
        if not client_id:
            raise ValueError('Bad argument of client_id.')
        if not redirect_uri:
            raise ValueError('Bad argument of redirect_uri.')
        kw['client_id'] = client_id
        kw['redirect_uri'] = redirect_uri
        if scope:
            kw['scope'] = scope
        if state:
            kw['state'] = state
        params = _encode_params(kw)
        return f'https://github.com/login/oauth/authorize?{params}'

    @classmethod
    def get_access_token(cls, client_id, client_secret, code, redirect_uri=None, state=None):
        '''
        In callback url: http://host/callback?code=123&state=xyz

        use code and state to get an access token.
        '''
        kw = dict(client_id=client_id, client_secret=client_secret, code=code)
        if redirect_uri:
            kw['redirect_uri'] = redirect_uri
        if state:
            kw['state'] = state
        url = 'https://github.com/login/oauth/access_token'
        opener = build_opener(HTTPSHandler)
        request = Request(url, data=_encode_params(kw))
        request.get_method = _METHOD_MAP['POST']
        request.add_header('Accept', 'application/json')
        try:
            response = opener.open(request, timeout=TIMEOUT)
            r = _parse_json(response.read())
            if 'error' in r:
                raise ApiAuthError(400, url, r.error)
            return AccessToken(r.access_token, r.scope, r.token_type)
        except HTTPError as e:
            raise ApiAuthError(e.code, url, 'HTTPError when get access token')

    def __getattr__(self, attr):
        path = _encode_path(attr)
        return _Callable(self, f'/{path}')

    def _http(self, _method, _path, _data=None, **kw):
        data = None
        params = None
        if _method=='GET' and kw:
            _path = '%s?%s' % (_path, _encode_params(kw))
        if _method in ['POST', 'PATCH', 'PUT', 'DELETE']:
            data = bytes(_encode_json(_data), 'utf-8')
        url = f'{_URL}{_path}'
        headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': _API_VERSION
        }
        if self._authorization:
            headers['Authorization'] = self._authorization
        if _method in ['POST', 'PATCH', 'PUT']:
            headers['Content-Type'] = 'application/json'
        opener = build_opener(HTTPSHandler)
        request = Request(url, data=data)
        request.get_method = _METHOD_MAP[_method]
        for k, v in headers.items():
            request.add_header(k, v)
        if self._debug:
            curl = ['curl -v', f'  -X {_method}']
            for k, v in headers.items():
                curl.append(f'  -H "{k}: {v}"')
            curl.append(f'  "{url}"')
            if data:
                curl.append(f'  -d \'{_encode_json(_data)}\'')
            print(' \\\n'.join(curl))
        try:
            response = opener.open(request, timeout=TIMEOUT)
            is_json = self._process_resp(response.headers)
            if is_json:
                return _parse_json(response.read().decode('utf-8'))
        except HTTPError as e:
            is_json = self._process_resp(e.headers)
            if is_json:
                json = _parse_json(e.read().decode('utf-8'))
            else:
                json = e.read().decode('utf-8')
            if e.code == 404:
                raise ApiNotFoundError(url)
            if e.code == 403:
                raise ApiForbiddenError(url)
            if e.code == 409:
                raise ApiConflictError(url)
            raise ApiError(e.code, url)

    def _process_resp(self, headers):
        is_json = False
        if headers:
            for h in headers:
                hl = h.lower()
                if hl == 'x-ratelimit-remaining':
                    self.x_ratelimit_remaining = int(headers[h])
                elif hl == 'x-ratelimit-limit':
                    self.x_ratelimit_limit = int(headers[h])
                elif hl == 'x-ratelimit-reset':
                    self.x_ratelimit_reset = int(headers[h])
                elif hl == 'content-type':
                    is_json = headers[h].startswith('application/json')
        return is_json


class JsonObject(dict):
    '''
    general json object that can bind any fields but also act as a dict.
    '''
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f'\'Dict\' object has no attribute \'{key}\'')

    def __setattr__(self, attr, value):
        self[attr] = value


class ApiError(Exception):

    def __init__(self, code, url, message=None):
        super(ApiError, self).__init__(message if message else f'{code}: {url}')
        self.code = code
        self.url = url


class ApiAuthError(ApiError):

    def __init__(self, code, url, message=None):
        super(ApiAuthError, self).__init__(code, url, message)


class ApiForbiddenError(ApiError):
    ' 403 Error '

    def __init__(self, url):
        super(ApiForbiddenError, self).__init__(403, url)


class ApiNotFoundError(ApiError):
    ' 404 Error '

    def __init__(self, url):
        super(ApiNotFoundError, self).__init__(404, url)


class ApiConflictError(ApiError):
    ' 409 Error '

    def __init__(self, url):
        super(ApiConflictError, self).__init__(409, url)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
