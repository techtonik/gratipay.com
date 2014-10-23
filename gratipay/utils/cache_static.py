"""
Handles caching of static resources.
"""
from base64 import b64encode
from hashlib import md5

from aspen import Response


ETAGS = {}


def asset_etag(website, path):
    if path.endswith('.spt'):
        return ''
    if website.cache_static and path in ETAGS:
        h = ETAGS[path]
    else:
        with open(path) as f:
            h = ETAGS[path] = b64encode(md5(f.read()).digest(), '-_').replace('=', '~')
    return h


def inbound(request):
    """Try to serve a 304 for static resources.
    """
    if request.fs.endswith('.spt'):
        # This is a request for a dynamic resource.
        return request

    etag = request.etag = asset_etag(request.website, request.fs)

    headers_etag = request.headers.get('If-None-Match')
    if not headers_etag:
        # This client doesn't want a 304.
        return request

    qs_etag = request.line.uri.querystring.get('etag')
    if qs_etag and qs_etag != etag:
        # Don't serve one version of a file as if it were another.
        raise Response(410)

    if headers_etag != etag:
        # Cache miss, the client sent an old or invalid etag.
        return request

    # Huzzah!
    # =======
    # We can serve a 304! :D

    raise Response(304)


def outbound(request, response):
    """Set caching headers for static resources.
    """
    if request.fs.endswith('.spt'):
        return response

    if response.code != 200:
        return response

    # https://developers.google.com/speed/docs/best-practices/caching
    response.headers['Access-Control-Allow-Origin'] = 'https://gratipay.com'
    response.headers['Vary'] = 'accept-encoding'
    response.headers['Etag'] = request.etag

    if request.line.uri.querystring.get('etag'):
        # We can cache "indefinitely" when the querystring contains the etag.
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    else:
        # Otherwise we cache for 5 seconds
        response.headers['Cache-Control'] = 'public, max-age=5'
