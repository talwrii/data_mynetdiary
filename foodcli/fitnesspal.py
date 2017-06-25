import lxml.etree
from . import parse_utils

def foods(session, name):
    #curl 'http://www.myfitnesspal.com/food/search' -H 'Host: www.myfitnesspal.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'Referer: http://www.myfitnesspal.com/food/search' -H 'Cookie: tracker=id%3D%3E%7Cuser_id%3D%3E%7Csource%3D%3E%7Csource_domain%3D%3E%7Ckeywords%3D%3E%7Cclicked_at%3D%3E2017-02-08+23%3A40%3A43+%2B0000%7Clanding_page%3D%3Ehttps%3A%2F%2Fwww.myfitnesspal.com%2Faccount%2Fcreate%7Csearch_engine%3D%3E%7Clp_category%3D%3E%7Clp_subcategory%3D%3E%7Ccp%3D%3E%7Ccr%3D%3E%7Cs1%3D%3E%7Cs2%3D%3E%7Ckw%3D%3E%7Cmt%3D%3E; premium_logged_out_homepage=ddf5b4973e1f43353b3fb9529df6d52e; premium_upsell_comparison=ddf5b4973e1f43353b3fb9529df6d52e; __utma=213187976.1307283245.1486597244.1486610496.1496602026.3; __utmz=213187976.1486610496.2.2.utmcsr=community.myfitnesspal.com|utmccn=(referral)|utmcmd=referral|utmcct=/en/discussion/10484608/im-nervous-about-my-first-free-meal-help/p2; _ga=GA1.2.1307283245.1486597244; p=qvI4BNZKfVK5d1MVXBNDMmQ3; known_user=124439094; __utmv=213187976.member|1=status=logged_in=1; _dy_soct=94589.128722.1496602026*47418.60107.1496603065; ki_t=1486597271294%3B1496602026487%3B1496603067855%3B2%3B17; ki_r=; _session_id=BAh7CEkiD3Nlc3Npb25faWQGOgZFVEkiJTZhNGZjOGE2ZTQzZDBiZmFhMWQ4ZDFiNmUyMDc1MzgyBjsAVEkiEGV4cGlyeV90aW1lBjsARlU6IEFjdGl2ZVN1cHBvcnQ6OlRpbWVXaXRoWm9uZVsISXU6CVRpbWUNlVQdwM29iREJOg1uYW5vX251bWkCfwE6DW5hbm9fZGVuaQY6DXN1Ym1pY3JvIgc4MDoJem9uZUkiCFVUQwY7AEZJIh9FYXN0ZXJuIFRpbWUgKFVTICYgQ2FuYWRhKQY7AFRJdTsHDZFUHcDNvYkRCTsIaQJ%2FATsJaQY7CiIHODA7C0kiCFVUQwY7AEZJIhBfY3NyZl90b2tlbgY7AEZJIjFkS1JReTBJZUpYRUttdlVLeGhoNHgvdHBiM2JJcGU5UDJ3bXdNNzFsYUV3PQY7AEY%3D--55cdb9d95d99618749761af717c38b56c90c4d1b; __utmb=213187976.18.10.1496602026; __utmc=213187976; _dy_csc_ses=t; _dy_ses_load_seq=21629%3A1496603065654; _dy_c_exps=; mobile_seo_test_guid=f870467b-8f6d-a68a-c755-9276a4aff19f; _gid=GA1.2.86490987.1496602027; _dycst=dk.l.f.ms.frv4.tos.; _dyus_8766792=174%7C0%7C0%7C0%7C0%7C0.0.1486597271157.1496603067772.10005796.0%7C154%7C23%7C5%7C117%7C16%7C0%7C0%7C0%7C0%7C0%7C0%7C16%7C0%7C0%7C0%7C0%7C0%7C16%7C0%7C0%7C0%7C1%7C0; _dy_geo=GB.EU.GB_.GB__; _dy_df_geo=United%20Kingdom..; _dy_toffset=0; _gat_UA-273418-97=1; __utmt=1; _dc_gtm_UA-273418-97=1' -H 'Connection: keep-alive' -H 'Cache-Control: max-age=0' --data 'utf8=%E2%9C%93&authenticity_token=dKRQy0IeJXEKmvUKxhh4x%2Ftpb3bIpe9P2wmwM71laEw%3D&search=marks+and+spencers+goats+cheese+square&commit=Search'
    response = session.post('http://www.myfitnesspal.com/food/search',
                     data=dict(search=name, commit='Search'))
    tree = lxml.etree.HTML(response.content.decode('utf8'))
    for xml_item in tree.xpath('//div[@class="food_info"]'):
        link, = xml_item.xpath('div[@class="food_description"]/a[position()=1]')
        brand, = xml_item.xpath('div[@class="food_description"]/a[position()=2]/text()')
        name, = link.xpath('text()')
        url, = link.xpath('@href')
        url = 'http://www.myfitnesspal.com' + url
        item = dict(name=name + ':' + brand, url=url, source='mfp')
        yield item


def fetch_detail(session, food):
    url = food['url']
    response = session.get(food['url'])
    tree = lxml.etree.HTML(response.content)
    table, = tree.xpath('//table[@id="nutrition-facts"]')
    pairs = []
    for row in table.xpath('/descendant::tr'):
        cells = row.xpath('td/text()')
        pairs.extend(list(zip(cells[0::2], cells[1::2])))

    pairs = [(name, float(parse_utils.initial_digits(amount))) for name, amount in pairs if name.strip()]
    pairs.append(('url', url))
    return dict(pairs)

