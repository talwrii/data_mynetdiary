import  itertools

def initial_digits(string):
    DIGITS = '0123456789.'
    return ''.join(itertools.takewhile(lambda x: x in DIGITS, string))

