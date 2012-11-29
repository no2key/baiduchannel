#coding: utf-8
"""
Baidu Channel
"""
import time
import uuid
import urllib
import urllib2

try:
    import json
except ImportError:
    import simplejson as json

CHANNEL_HOST = 'channel.api.duapp.com'
CHANNEL_DOMAIN = 'https://channel.api.duapp.com/'

HTTP_STATUS_OK = 200
HTTP_GET = 0
HTTP_POST = 1

class ChannelException(Exception):
    pass

class ChannelHttpException(ChannelException):
    """
    Base Exception
    """
    def __init__(self, code, data):
        try:
            _data = json.loads(data)
        except:
            _data = {}
        self.code = code
        self.error = _data.get("error", 'Unknown')
        self.error_description = _data.get("error_description", data)

    def __str__(self):
        return "%s %s(%s)" % (self.code, self.error, self.error_description)

class FancyDict(dict):
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

def assert_list(obj):
    return obj if isinstance(obj, (list, tuple)) else [obj]

def http_request(url, params={}, method=HTTP_GET, ret_type="json"):
    """
    Send a request through urllib2
    """
    data = urllib.urlencode(params) if params else None
    if method == HTTP_GET:
        url = '%s?%s' % (url, urllib.urlencode(params))
        data = None
    try:
        request = urllib2.Request(url, data)
        ret = urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        ret = e

    # Raise Exception if got an error status
    if ret.code != HTTP_STATUS_OK:
        raise ChannelHttpException(ret.code, ret.read())
  
    ret = ret.read()
    if ret_type == "json":
        ret = FancyDict(json.loads(ret))
    return ret

def get_access_token(api_key, api_secret):
    """
    Get access token from baidu, need api_key and api_secret
    """
    url = "https://openapi.baidu.com/oauth/2.0/token"
    ret = http_request(url, params = {
            'grant_type': 'client_credentials',
            'client_id': api_key, 
            'client_secret': api_secret
        })
    return ret

class ChannelClient(object):
    """
    Client
    ======

    Init need at least two arguments: api_key、 api_secret
    """
    access_token = None
    expires_at = time.time()

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def refresh_access_token(self):
        access_token = get_access_token(self.api_key, self.api_secret)
        ChannelClient.access_token = access_token.access_token
        ChannelClient.expires_at = access_token.expires_in + time.time()

    def _call(self, method, channel_id=None, params={}):
        """
        All use post method
        """
        if time.time() + 3600 > self.expires_at:
            print 'Requesting new access token...'
            self.refresh_access_token()

        channel_id  = channel_id or 'channel'
        params.update(
            method = method,
            access_token = ChannelClient.access_token,
        )
        return http_request('%srest/2.0/channel/%s' % (CHANNEL_DOMAIN, channel_id), params = params,
                method=HTTP_POST)

    def create_group(self, name):
        """
        创建广播组
        """
        return self._call('create_group', params={"name": name})

    def destroy_group(self, gid):
        """
        删除广播组
        """
        return self._call('destroy_group', params={"gid": gid})

    def _base_pushmsg(self, method, user_id, messages, channel_id=None):
        """
        Base push messages
        """
        messages = assert_list(messages)
        message_keys = [ uuid.uuid4().hex for x in messages ]
        return self._call(method, channel_id=channel_id, params={
            'user_id': user_id,
            'messages': json.dumps(messages),
            'msg_keys': json.dumps(message_keys),
        })

    def pushmsg(self, user_id, messages, channel_id=None):
        """
        功能：推送单播消息
        """
        return self._base_pushmsg('pushmsg', user_id, messages, channel_id=channel_id)

    def pushmsg_to_user(self, user_id, messages):
        """
        向用户推送消息
        """
        return self._base_pushmsg('pushmsg_to_user', user_id, messages)

    def push_android_msg(self, user_id, messages, channel_id=None):
        """
        推送单播消息
        """
        return self._base_pushmsg('pushmsg_to_user', user_id, messages, channel_id=channel_id)

if __name__ == '__main__':
    API_KEY = "your api key"
    API_SECRET = "your api secret"

    client = ChannelClient(API_KEY, API_SECRET)
    print client.pushmsg_to_user('user_id', 'Hello, channel!')

