from html.parser import HTMLParser
from html.entities import name2codepoint


class HTMLToText(HTMLParser):
    """HTMLToText is a very rudimentary and naive HTML to plaintext parser"""
    def __init__(self):
        HTMLParser.__init__(self)
        self._buf = []

    def text(self):
        return "".join(self._buf)

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self._buf.append('\n')

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self._buf.append('\n')

    def handle_endtag(self, tag):
        if tag == 'p':
            self._buf.append('\n')

    def handle_data(self, data):
        self._buf.append(data)

    def handle_entityref(self, name):
        if name in name2codepoint:
            c = chr(name2codepoint[name])
            self._buf.append(c)

    def handle_charref(self, name):
        n = int(name[1:], 16) if name.startswith('x') else int(name)
        self._buf.append(chr(n))


def html_to_text(html: str) -> str:
    """
    Convert the given HTML to plaintext.

    This is a very rudimentary parser, but it relies only on the Python stdlib.
    It should be more than adequate for the HTML that is output by Markdown rendering.
    """
    parser = HTMLToText()
    parser.feed(html)
    parser.close()
    return parser.text()
