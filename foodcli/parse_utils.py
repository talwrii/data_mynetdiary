import  itertools
import lxml.etree
import lxml.html
import lxml.html.clean

def initial_digits(string):
    DIGITS = '0123456789.'
    return ''.join(itertools.takewhile(lambda x: x in DIGITS, string))

def lxml_to_text(html):
    doc = lxml.html.fromstring(html)
    doc = lxml.html.clean.clean_html(doc)
    return doc.text_content()
