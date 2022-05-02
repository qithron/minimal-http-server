ENC = 'utf-8'
HTML_DOC = bytes('<!doctype html>'
'<html><head>'
    '<meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<link rel="icon" type="image/png" href="data:image/png;base64,'
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAA'
        'ACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg==">'
    '<style>'
        'body{'
            'color:#000000;background-color:#79b94e;'
            'font-family:monospace;'
            'margin:0;padding:0;}'
    '</style>'
    '<title>%s</title>' # HTML_TITLE
    '%s' # HTML_HEAD
'</head>'
'<body>%s</body>' # HTML_BODY
'</html>', encoding=ENC)

def _get_all():
    import os
    l = [f[:-3] for f in os.listdir(os.path.dirname(__file__))
        if not f.startswith('_') and f.endswith('.py')]
    return __import__('data', fromlist=l), l