# See interactive-debug-session.py for details of scraping

# make code as python 3 compatible as possible
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import collections
import datetime
import itertools
import json
import logging
import re
import sys

import http
import lxml.etree
import lxml.html
import lxml.html.clean
import requests
import yaml

if sys.version_info[0] != 3:
    # FileNotFoundError does not exist in python 2
    raise Exception('Only works with python 3')

LOGGER = logging.getLogger()

# Configuration
CREDENTIALS_FILE = "credentials.yaml"

TODAY = datetime.date.today()

def build_parser():
    PARSER = argparse.ArgumentParser(description='Extract data from mynetdiary')

    PARSER.add_argument('--debug', action='store_true', help='Print debug output')

    parsers = PARSER.add_subparsers(dest='command')


    history_parser = parsers.add_parser('history', help='')
    history_parser.add_argument('--debug', action='store_true', help='Print debug output')
    history_parser.add_argument('--start-date', type=parse_date, default='2012-01-01', help='Fetch information from this date')

    items_parser = parsers.add_parser('items', help='Show what you have eaten today')
    items_parser.add_argument('--day', type=parse_date, help='Show items for this day', default=TODAY)
    items_parser.add_argument('--raw', action='store_true', help='Show raw data')

    new_food_parser = parsers.add_parser('new-food', help='Create a new food')
    new_food_parser.add_argument('--name', type=str)

    food_parser = parsers.add_parser('ext-food', help='Look up foods from another source')
    food_parser.add_argument('source', type=str, help='Source of food information', choices=('mfp',))
    food_parser.add_argument('name', nargs='*', help='Name of food source')
    food_parser.add_argument('--index', type=int, help='Only show item with this index')
    food_parser.add_argument('--detail', action='store_true', help='Show details about food')

    food_parser = parsers.add_parser('food', help='Search foods and add them')
    food_parser.add_argument('name', type=str, help='Substring of the food you want to search', nargs='+')
    food_parser.add_argument('--raw', action='store_true', help='Output raw json')
    food_parser.add_argument('--index', type=int, help='Only show this item')
    food_parser.add_argument('--detail', action='store_true', help='Output information about foods')
    food_parser.add_argument('--add', type=float, help='Add this many units of this food')
    food_parser.add_argument('--all', action='store_true', help='Output all nutritional information')

    GRAM_UNITS = [
        'calories',
        'fat',
        'sodium',
        'fibre',
        'sugar',
        'alcohol',
        'protein',
        'starch',
        ('saturates','saturated fat'),
        ('poly-un', 'polyunsaturated fat'),
        ('mono-un', 'monounsaturated fat'),
        ('trans', 'trans fats'),
        ('chol', 'cholesterol'),
        ('carbs', 'carbohydrate'),
    ]

    def singles_to_pairs(items):
        return [((x, x) if isinstance(x, str) else x)  for x in items]

    GRAM_UNITS = singles_to_pairs(GRAM_UNITS)

    # milligrams
    new_food_parser.add_argument('--caffeine', type=float, default=0, nargs='*', help='Milligrams of caffeine')
    new_food_parser.add_argument('--potassium', type=float, default=0, nargs='*', help='Milligrams of potassium')

    # percent RDA
    PERCENT_VIT = [['A', ' vitamin a'], 'B6', 'B12', ['C', ' vitamin c'], ['D', ''], 'E', 'K']

    PERCENT_MINERALS = [
        'calcium',
        'iron',
        'thiamin',
        'riboflavin',
        'niacin',
        'folate',
        ['pan', ' panthothenic acid'],
        'phosphorus',
        'magneisium',
        'zinc',
        'selenium',
        'copper',
        'manganese']

    PERCENT_VIT = singles_to_pairs(PERCENT_VIT)
    PERCENT_MINERALS = singles_to_pairs(PERCENT_MINERALS)

    for flag, documentation in GRAM_UNITS:
        new_food_parser.add_argument('--' + flag, help='Grams of {}'.format(documentation), type=float)

    for flag, documentation in PERCENT_VIT:
        new_food_parser.add_argument('--' + 'percent-' + flag, help='Percentage RDA of {}'.format(documentation), type=float)

    for flag, documentation in PERCENT_MINERALS:
        new_food_parser.add_argument('--' + 'percent-' + flag, help='Percentage RDA of {}'.format(documentation), type=float)

    return PARSER


def add_food(args):
    if args.serving is None:
        serving_name = 'Serving'
        serving_grams = 100
    else:
        serving_name, serving_grams = args.serving

    ('customfoodname', args.name)

# serving1name=amount
# serving1weight=100
# ('foodgroupid', '1000005')
# calories=100.0
# totalFatG=
# satFatG=
# polyUnsatFatG=
# monoUnsatFatG=
# transFatG=
# cholMg=
# sodiumMg=
# totalCarbsG=
# dietaryFiberG=
# sugarsG=
# sugarAlcoholG=
# proteinG=
# vitaminAPercent=
# vitaminCPercent=
# calciumPercent=
# ironPercent=
# caffeineMg=
# waterG=
# alcoholEthylG=
# starchG=
# potassiumMg=
# vitaminDPercent=
# vitaminB6Percent=
# vitaminB12Percent=
# vitaminEPercent=
# vitaminKPercent=
# thiaminPercent=
# riboflavinPercent=
# niacinPercent=
# folatePercent=
# panthothenicAcidPercent=
# phosphorusPercent=
# magnesiumPercent=
# zincPercent=
# seleniumPercent=
# cooperPercent=
# manganesePercent=
# customFoodId=0
# contributed=false
# sourceFoodId='
    return PARSER


def parse_date(string):
    return datetime.datetime.strptime(string, '%Y-%m-%d')

def extract_data(html_string):
    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
    match = pattern.match(html_string)
    return match and match.groups()[0]

def load_credentials(credentials_file):
    try:
        with open(credentials_file, "r") as stream:
            try:
                credentials = yaml.load(stream)
                logon_payload = {
                    'logonName': credentials['mynetdiary']['username'],
                    'password': credentials['mynetdiary']['password']
                }
                return logon_payload
            except yaml.YAMLError:
                raise Exception('Error reading file: {0}'.format(CREDENTIALS_FILE))
    except FileNotFoundError:
        raise Exception('Configuration file not found: {0}'.format(CREDENTIALS_FILE))


def day_series(start, end):
    difference = end - start.date()
    for i in range(1, difference.days):
        yield start + datetime.timedelta(days=i)

def info(message):
    print(message, file=sys.stderr)

def fetch_weights(session, start_date):
    info('Get pages since : ${0}'.format(start_date))

    count_no_weight = 0
    count_pages = 0

    with open("output.csv", "w") as weights_file:
        for day in day_series(start_date, datetime.date.today()):
            date_string = day.strftime('%Y%m%d')

            LOGGER.debug('Fetching for %r', date_string)

            response = session.get('https://www.mynetdiary.com/dailyDetails.do?date={0}'.format(date_string))

            count_pages+=1

            #with open("a.html", "w") as text_file:
            #  text_file.write(response.text)
            raw_data = extract_data(response.text)
            ajson = json.loads(raw_data)
            if ajson[0]['measurementId'] == 40:
                weightValue = ajson[0]['currentValue']
                if weightValue is not None:
                    weights_file.write("{0},{1}\n".format(day.strftime('%Y-%m-%d'), re.sub('kg$','', ajson[0]['currentValue'])) )
                else:
                    count_no_weight+=1
            else:
                count_no_weight+=1

    info("{0}/{1} pages contained no weight".format(count_no_weight, count_pages))

def fetch_nutrition(stream, session, start_date):
    headings = None
    for date in day_series(start_date, datetime.date.today()):
        LOGGER.debug('Fetching nutritional information for %r', date)

        date_string = date.strftime('%Y-%m-%d')
        page = session.post('http://www.mynetdiary.com/reportRefresh.do', dict(personUserId='', period='periodCustom', periodFake='period7d', details='allFoods', nutrients='allNutrients', navigation='blah', startDate=date_string, endDate=date_string))
        tree = lxml.etree.HTML(page.text)
        table, = tree.xpath('//table[@class="report"]')
        new_headings = ['date', 'food', 'serving', 'amount'] + [x.replace(' column', '') for x in table.xpath('.//thead/tr/td/@title')]

        if not headings:
            headings = new_headings
            print(','.join(headings), file=stream)

        if headings != new_headings:
            raise Exception('Inconsistent headings across pages %r', (headings, new_headings))

        for row in table.xpath('.//tr'):
            NON_BREAKING_SPACE = '\xa0'
            values = [v.replace(NON_BREAKING_SPACE, '').strip() for v in row.xpath('.//td/text()')]

            if len(values) in (1, 2):
                continue

            if len(values) == len(headings) - 3:
                if 'over' in values[0] and 'period' in values[0]:
                    # Averages over the period,2250,1,54,330,111,,22,3,3,,1296,301,29,99,,191,,,,,,,,,,,,,,,,,,,,,,,2,,,,,,,,,320
                    print('averaging', file=stream)
                    values = ['DAILY_SUM', '', ''] + values[1:]
                elif 'percentage' in values[0]:
                    # Calories percentage,,,22%,59%,20%,0%,9%,1%,1%,,,,0%,18%,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
                    values = ['DAILY_PERCENT', '', ''] + values[1:]
                else:
                    raise ValueError((values, headings))

            values.insert(0, date.date().isoformat())

            if len(headings) != len(values):
                raise ValueError((len(headings), len(values), headings, values))

            print(','.join(values), file=stream)


def find_foods(session, name):
    # Original request (from firefox)
    # curl 'http://www.mynetdiary.com/findFoods.do' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/javascript, text/html, application/xml, text/xml, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'X-Requested-With: XMLHttpRequest' -H 'X-Prototype-Version: 1.5.0' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496379979.1496382923.23; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=XXXXXX; JSESSIONID=XXXXXXXX; __utmc=190183351; WHICHSERVER=SRV118002; __utmb=190183351.2.10.1496382923; __utmt=1' -H 'Connection: keep-alive' --data 'beanInputString=bla&pageSize=15&pageNumber=1&highlightedTermClassName=sughtrm&detailsExpected=true'
    page_number = 1
    for page in itertools.count(1):
        constant_data = [('pageSize', '100'), ('highlightedTermClassName', 'sughtrm'), ('detailsExpected', 'true')]
        data = session.post('http://www.mynetdiary.com/findFoods.do', data=[("beanInputString", name), ('pageNumber', str(page))] + constant_data)
        data = data.content.decode('utf8')
        if data[:12] ==  "OK `+`json":
            raise Exception('Request format wrong')
        yield json.loads(data[11:])


Amount = collections.namedtuple('Amount', 'number is_grams')

class FoodParser(object):
    def __init__(self, data):
        self.data = data

    def amount_string(self, amount=None):
        amount = amount or details['dfSrv']['am']
        amount_name = details['dfSrv']['desc']
        return '{} {}'.format(amount, amount_name),


def save_item(session, amount, details, parentBeanId):
    # curl 'http://www.mynetdiary.com/dailyFoodSave.do' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/javascript, text/html, application/xml, text/xml, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'X-Requested-With: XMLHttpRequest' -H 'X-Prototype-Version: 1.5.0' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496386317.1496517505.25; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=rkTD82GiHepAyy42; JSESSIONID=fBfrKjhhIKqQ; WHICHSERVER=SRV118002; __utmb=190183351.1.10.1496517505; __utmc=190183351; __utmt=1' -H 'Connection: keep-alive' --data '{"parentBeanId":139410013,"beanEntryNo":101,"beanId":2156966,"beanInputString":"Fever tree tonic","amountInputString":"bottle","amountId":"1","mealTypeId":1,"calculateAmount":true}'

    # TODO: parentbeanid is contained within the food grid
    #   it identifies which day items are added to


    #print(json.dumps(details, indent=4))


    food_name = lxml_to_text(details['descForUi'])
    parser = FoodParser(details)

    if amount.is_grams:
        amount_specifier = amount.number
        amount_id = None
    else:
        amount_id = details['dfSrv']['id']
        amount_specifier = parser.amount_string(amount)

    # Adding gram amounts [reverse.md#Adding Grams]
    response = session.post('http://www.mynetdiary.com/dailyFoodSave.do',
        data=json.dumps(dict(
            mealTypeId=1,
            beanInputString=food_name,
            beanId=details['beanId'],
            beanEntryNo=101,
            parentBeanId=parentBeanId,
            amountInputString=amount_specifier,
            amountId=amount_id,
            calculateAmount=True)),
            headers={'Content-Type': "application/x-www-form-urlencoded" })
    response.raise_for_status()
    print(response.status_code)
    print(response.content)

def main():
    args = build_parser().parse_args()

    if args.debug:
        log_http()
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug('Establishing session')
    logon_payload = load_credentials(CREDENTIALS_FILE)
    with requests.Session() as session:
        session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)

        if args.command == 'history':
            fetch_weights(session, args.start_date)

            with open("nutrition.csv", "w") as nutrition_csv:
                fetch_nutrition(nutrition_csv, session, args.start_date)
        elif args.command == 'items':
            items = get_items(session, args.day)
            if args.raw:
                print(json.dumps(items, indent=4))
            else:
                headers = [header_string.split('<br/>')[0] for header_string in items['nutrColumnHeaders']]

                bean_entries = [x for x in items['beanEntries'] if 'bean' in x]

                for x in bean_entries:
                    x['amount'], x['amount_string'] = parse_amount(x['amountResolved'])

                if not bean_entries:
                    return

                desc_width = max([len(x['bean']['beanDesc']) for x in bean_entries])
                amount_width = max([len(x['amount_string']) for x in bean_entries])

                for entry in bean_entries:
                    nutrition = dict(zip(headers, map(float, [x or '-1' for x in entry['nutrValues']])))

                    density = nutrition['Cals'] / entry['amount']

                    energy_calories = nutrition['Cals'] - nutrition['Protein'] * PROTEIN_CALS - nutrition['Fiber'] * FIBER_CALS
                    energy_calories_density = energy_calories / entry['amount']

                    columns = (
                        ('name', entry['bean']['beanDesc'].ljust(desc_width)),
                        ('amount', entry['amount_string'].ljust(amount_width)),
                        ('non-protein calories', '{:5.1f}'.format(energy_calories)),
                        ('energy_calorie_density', '{:5.1f}'.format(energy_calories_density)),
                        ('calories', '{:8.0f}'.format(nutrition['Cals'])),
                        ('carbs', '{:5.1f}'.format(nutrition['Carbs'])),
                        ('fat', '{:5.1f}'.format(nutrition['Fat'])),
                        ('protein', '{:5.1f}'.format(nutrition['Protein'])),
                        ('fiber', '{:5.1f}'.format(nutrition['Fiber'])),
                        ('density', '{:5.1f}'.format(density))
                    )
                    print(':'.join([c[0] for c in columns]))
                    print(':'.join([c[1] for c in columns]))

        elif args.command == 'food':
            food_specifier = ' '.join(args.name)
            food_json = find_foods(session, food_specifier)
            if args.raw:
                index = 0
                for item in find_foods(session, food_specifier):
                    if args.index is None:
                        print(json.dumps(item, indent=4))
                        break
                    else:
                        if not item['entries']:
                            break

                        for food_item in item['entries']:
                            if index == args.index:
                                print(json.dumps(food_item, indent=4))
                            index += 1
            else:
                index = -1
                for item in find_foods(session, food_specifier):
                    if not item["entries"]:
                        break

                    for x in item["entries"]:
                        index += 1
                        if args.index is not None and index != args.index:
                            continue

                        try:
                            if args.add:

                                items = get_items(session, datetime.date.today())

                                save_item(session, Amount(number=args.add, is_grams=True), x, items["parentBeanId"])
                            else:
                                print(format_food(x, args.detail, args.all))
                        except BrokenPipeError:
                            return
                #print("\n".join(x["recentBeanDesc"] for x in food_json['entries']))

        elif args.command == 'ext-food':
            if args.source == 'mfp':
                name = ' '.join(args.name)
                foods = list(mfp_foods(session, name))
            else:
                raise ValueError(args.source)

            if args.index is not None:
                foods = [foods[args.index]]

            for food in foods:
                print(food['name'])
                if args.detail:
                    details = external_fetch_detail(session, food)
                    for k, v in details.items():
                        print('    {}: {}'.format(k, v))


        else:
            raise ValueError(args.command)


def external_fetch_detail(session, food):
    if food['source'] == 'mfp':
        return mfp_fetch_detail(session, food)
    else:
        raise ValueError(food['source'])



def format_food(item, detail, all_nutrients):
    result = []
    result.append(lxml_to_text(item["descForUi"]))
    parser = FoodParser(detail)
    if all_nutrients:
        print(json.dumps(item, indent=4))

        for item in sorted(item['details'], key=lambda x: float(x['nutrValue']), reverse=True):
            result.append('    {} {}{}'.format(item['nutrDesc'], item['nutrValue'], item['units']))

    elif detail:
        gramless = item.get("isGramless")
        for stat in item["details"]:
            if stat["nutrDesc"] == "Calories":
                if gramless:
                    result.append("    Calories: {} / {}".format(stat["nutrValue"], item["gramlessAmountMeasure"]))
                else:
                    result.append("    Calories: {} / 100 g".format(stat["nutrValue"]))

        LOGGER.debug('Formatting food: %s', json.dumps(item, indent=4))

            # unit = item["dfSrv"]
            # unit_name = unit["desc"]
            # unit_number = unit["am"]
            # unit_grams = unit["gmWgt"]
            # result.append("    Amount: ({}/100 grams)".format(unit_number, unit_name, unit_grams))


    return '\n'.join(result)

def lxml_to_text(html):
    doc = lxml.html.fromstring(html)
    doc = lxml.html.clean.clean_html(doc)
    return doc.text_content()

def get_items(session, dt):
    LOGGER.debug('Fetching data for %r', dt)
    # Why would this be json?!
    #curl 'http://www.mynetdiary.com/daily.do?date=20170601' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496382923.1496386317.24; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=rkTD82GiHepAyy42; JSESSIONID=ePQrD6nXbP0u; __utmc=190183351; WHICHSERVER=SRV128001; __utmb=190183351.2.10.1496386317; __utmt=1' -H 'Connection: keep-alive'
    date_string = dt.strftime('%Y%m%d')
    response = session.get('http://www.mynetdiary.com/daily.do?date={}'.format(date_string))
    data = response.content.decode('utf8')
    line, = [l for l in data.splitlines() if 'initialFoodGridPM' in l]
    json_string = line.split('=')[1][1:-1]
    return json.loads(json_string)

def mfp_foods(session, name):
    #curl 'http://www.myfitnesspal.com/food/search' -H 'Host: www.myfitnesspal.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'Referer: http://www.myfitnesspal.com/food/search' -H 'Cookie: tracker=id%3D%3E%7Cuser_id%3D%3E%7Csource%3D%3E%7Csource_domain%3D%3E%7Ckeywords%3D%3E%7Cclicked_at%3D%3E2017-02-08+23%3A40%3A43+%2B0000%7Clanding_page%3D%3Ehttps%3A%2F%2Fwww.myfitnesspal.com%2Faccount%2Fcreate%7Csearch_engine%3D%3E%7Clp_category%3D%3E%7Clp_subcategory%3D%3E%7Ccp%3D%3E%7Ccr%3D%3E%7Cs1%3D%3E%7Cs2%3D%3E%7Ckw%3D%3E%7Cmt%3D%3E; premium_logged_out_homepage=ddf5b4973e1f43353b3fb9529df6d52e; premium_upsell_comparison=ddf5b4973e1f43353b3fb9529df6d52e; __utma=213187976.1307283245.1486597244.1486610496.1496602026.3; __utmz=213187976.1486610496.2.2.utmcsr=community.myfitnesspal.com|utmccn=(referral)|utmcmd=referral|utmcct=/en/discussion/10484608/im-nervous-about-my-first-free-meal-help/p2; _ga=GA1.2.1307283245.1486597244; p=qvI4BNZKfVK5d1MVXBNDMmQ3; known_user=124439094; __utmv=213187976.member|1=status=logged_in=1; _dy_soct=94589.128722.1496602026*47418.60107.1496603065; ki_t=1486597271294%3B1496602026487%3B1496603067855%3B2%3B17; ki_r=; _session_id=BAh7CEkiD3Nlc3Npb25faWQGOgZFVEkiJTZhNGZjOGE2ZTQzZDBiZmFhMWQ4ZDFiNmUyMDc1MzgyBjsAVEkiEGV4cGlyeV90aW1lBjsARlU6IEFjdGl2ZVN1cHBvcnQ6OlRpbWVXaXRoWm9uZVsISXU6CVRpbWUNlVQdwM29iREJOg1uYW5vX251bWkCfwE6DW5hbm9fZGVuaQY6DXN1Ym1pY3JvIgc4MDoJem9uZUkiCFVUQwY7AEZJIh9FYXN0ZXJuIFRpbWUgKFVTICYgQ2FuYWRhKQY7AFRJdTsHDZFUHcDNvYkRCTsIaQJ%2FATsJaQY7CiIHODA7C0kiCFVUQwY7AEZJIhBfY3NyZl90b2tlbgY7AEZJIjFkS1JReTBJZUpYRUttdlVLeGhoNHgvdHBiM2JJcGU5UDJ3bXdNNzFsYUV3PQY7AEY%3D--55cdb9d95d99618749761af717c38b56c90c4d1b; __utmb=213187976.18.10.1496602026; __utmc=213187976; _dy_csc_ses=t; _dy_ses_load_seq=21629%3A1496603065654; _dy_c_exps=; mobile_seo_test_guid=f870467b-8f6d-a68a-c755-9276a4aff19f; _gid=GA1.2.86490987.1496602027; _dycst=dk.l.f.ms.frv4.tos.; _dyus_8766792=174%7C0%7C0%7C0%7C0%7C0.0.1486597271157.1496603067772.10005796.0%7C154%7C23%7C5%7C117%7C16%7C0%7C0%7C0%7C0%7C0%7C0%7C16%7C0%7C0%7C0%7C0%7C0%7C16%7C0%7C0%7C0%7C1%7C0; _dy_geo=GB.EU.GB_.GB__; _dy_df_geo=United%20Kingdom..; _dy_toffset=0; _gat_UA-273418-97=1; __utmt=1; _dc_gtm_UA-273418-97=1' -H 'Connection: keep-alive' -H 'Cache-Control: max-age=0' --data 'utf8=%E2%9C%93&authenticity_token=dKRQy0IeJXEKmvUKxhh4x%2Ftpb3bIpe9P2wmwM71laEw%3D&search=marks+and+spencers+goats+cheese+square&commit=Search'
    response = session.post('http://www.myfitnesspal.com/food/search',
                     data=dict(search=name, commit='Search'))
    tree = lxml.etree.HTML(response.content.decode('utf8'))
    items = []
    for xml_item in tree.xpath('//div[@class="food_info"]'):
        link, = xml_item.xpath('div[@class="food_description"]/a[position()=1]')
        brand, = xml_item.xpath('div[@class="food_description"]/a[position()=2]/text()')
        name, = link.xpath('text()')
        url, = link.xpath('@href')
        url = 'http://www.myfitnesspal.com' + url
        item = dict(name=name + ':' + brand, url=url, source='mfp')
        yield item

def mfp_fetch_detail(session, food):
    url = food['url']
    response = session.get(food['url'])
    tree = lxml.etree.HTML(response.content)
    table, = tree.xpath('//table[@id="nutrition-facts"]')
    pairs = []
    for row in table.xpath('/descendant::tr'):
        cells = row.xpath('td/text()')
        pairs.extend(list(zip(cells[0::2], cells[1::2])))

    pairs = [(name, float(initial_digits(amount))) for name, amount in pairs if name.strip()]
    return dict(pairs)




def log_http():
    http.client.HTTPConnection.debuglevel = 1

    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def parse_amount(string):

    number = initial_digits(string)

    unit = string[len(number):]
    factor, new_unit = CONVERSIONS[unit]
    new_number = float(number) * factor
    return new_number, '{:.1f}'.format(new_number) + ' ' + new_unit

def initial_digits(string):
    DIGITS = '0123456789.'
    return ''.join(itertools.takewhile(lambda x: x in DIGITS, string))


CONVERSIONS = {
    'tbsp': (14.7868, 'ml'),
    'g': (1, 'g'),
}

PROTEIN_CALS = 4
FIBER_CALS = 2


if __name__ == '__main__':
	main()
