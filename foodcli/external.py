
from . import fitnesspal, tesco

def food_from_url(session, source, url):
    if source != 'tesco':
    	raise ValueError(source)

    return tesco.parse_url(url)

def fetch_detail(session, food):
    if food['source'] == 'mfp':
        return fitnesspal.fetch_detail(session, food)
    else:
        raise ValueError(food['source'])




