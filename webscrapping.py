# See interactive-debug-session.py for details of scraping

# make code as python 3 compatible as possible
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import collections
import contextlib
import datetime
import itertools
import json
import logging
import pprint
import re
import sys

import http
import lxml.etree
import lxml.html
import lxml.html.clean
import requests
import yaml

from . import mynetdiary
from . import tesco
from . import fitnesspal

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
    items_parser.add_argument('--index', type=int, help='Select this index')
    items_parser.add_argument('--delete', action='store_true', help='Delete items')

    new_food_parser = parsers.add_parser('new-food', help='Create a new food')
    new_food_parser.add_argument('--name', type=str)

    food_parser = parsers.add_parser('ext-food', help='Look up foods from another source')
    food_parser.add_argument('source', type=str, help='Source of food information', choices=('mfp', 'tesco'))
    food_parser.add_argument('name', nargs='*', help='Name of food source')
    food_parser.add_argument('--index', type=int, help='Only show item with this index')
    food_parser.add_argument('--detail', action='store_true', help='Show details about food')
    food_parser.add_argument('--url', type=str, help='Get the food for this url')


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


Amount = collections.namedtuple('Amount', 'number is_grams')

class FoodParser(object):
    "Parse the entry for a type of food."
    def __init__(self, data):
        self.data = data

    def amount_string(self, amount=None):
        amount = amount or self.data['dfSrv']['am']
        amount_name = self.data['dfSrv']['desc']
        return '{} {}'.format(amount, amount_name),

    def bean_id(self):
        return self.data['beanId']

    def food_name(self):
        return lxml_to_text(self.data['descForUi'])

    def dump(self):
        return self.data

    def amount_id(self):
        return self.data['dfSrv']['id']

class HistoryParser(object):
    def __init__(self, data):
        self.data = data

    def bean_id(self):
        raise NotImplementedError()

    def food_name(self):
        raise NotImplementedError()

    def dump(self):
        raise NotImplementedError()

    def amount_id(self):
        raise NotImplementedError()
    def amount_string(self):
        raise NotImplementedError()


@contextlib.contextmanager
def log_on_error(*args):
    "Context manager which logs if an error occures"
    try:
        yield
    except:
        logging.exception(*args)

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
            items = mynetdiary.get_eaten_items(session, args.day)
            if args.raw:
                print(json.dumps(items, indent=4))
            else:
                headers = [header_string.split('<br/>')[0] for header_string in items['nutrColumnHeaders']]

                bean_entries = [x for x in items['beanEntries'] if 'bean' in x]
                for x in bean_entries:
                    pprint.pprint(x)
                    x['amount'], x['amount_string'] = parse_amount(x['amountResolved'])

                if not bean_entries:
                    return

                desc_width = max([len(x['bean']['beanDesc']) for x in bean_entries])
                amount_width = max([len(x['amount_string']) for x in bean_entries])

                columns_printed = False
                for index, entry in enumerate(bean_entries):
                    if args.index and index != args.index:
                        continue

                    if args.delete:
                        mynetdiary.save_item(session, None, entry, items)

                    nutrition = dict(zip(headers, map(float, [x or '-1' for x in entry['nutrValues']])))

                    density = nutrition['Cals'] / entry['amount']

                    energy_calories = nutrition['Cals'] - nutrition['Protein'] * PROTEIN_CALS - nutrition['Fiber'] * FIBER_CALS
                    energy_calories_density = energy_calories / entry['amount']

                    columns = (
                        ('name', entry['bean']['beanDesc'].ljust(desc_width)),
                        ('amount', entry['amount_string'].ljust(amount_width)),
                        ('calories', '{:8.0f}'.format(nutrition['Cals'])),
                        ('non-protein calories', '{:5.1f}'.format(energy_calories)),
                        ('energy_calorie_density', '{:5.1f}'.format(energy_calories_density)),
                        ('carbs', '{:5.1f}'.format(nutrition['Carbs'])),
                        ('fat', '{:5.1f}'.format(nutrition['Fat'])),
                        ('protein', '{:5.1f}'.format(nutrition['Protein'])),
                        ('fiber', '{:5.1f}'.format(nutrition['Fiber'])),
                        ('density', '{:5.1f}'.format(density))
                    )

                    if not columns_printed:
                        print(':'.join([c[0] for c in columns]))
                        columns_printed = True

                    print(':'.join([c[1] for c in columns]))



        elif args.command == 'food':
            food_specifier = ' '.join(args.name)
            food_json = mynetdiary.find_foods(session, food_specifier)
            if args.raw:
                index = 0
                for item in mynetdiary.find_foods(session, food_specifier):
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
                for item in mynetdiary.find_foods(session, food_specifier):
                    if not item["entries"]:
                        break

                    for x in item["entries"]:
                        index += 1
                        if args.index is not None and index != args.index:
                            continue

                        try:
                            if args.add:
                                items = mynetdiary.get_eaten_items(session, datetime.date.today())
                                mynetdiary.save_item(session, Amount(number=args.add, is_grams=True), FoodParser(x), items)
                            else:
                                print(format_food(x, args.detail, args.all))
                        except BrokenPipeError:
                            return
                #print("\n".join(x["recentBeanDesc"] for x in food_json['entries']))

        elif args.command == 'ext-food':
            if args.source == 'mfp':
                if args.url is not None:
                    raise NotImplementedError()
                name = ' '.join(args.name)
                foods = list(fitnesspal.foods(session, name))
            elif args.source == 'tesco':
                if args.url is None:
                    raise Exception('tesco only supports urls')
            else:
                raise ValueError(args.source)

            if args.url:
                details = external_food_from_url(session, args.source, args.url)
                show_external_food(details)
            else:
                if args.index is not None:
                    foods = [foods[args.index]]

                for food in foods:
                    print(food['name'])
                    if args.detail:
                        details = external_fetch_detail(session, food)
                    show_external_food(details)
        else:
            raise ValueError(args.command)

def show_external_food(details):
    for k, v in details.items():
        print('    {}: {}'.format(k, v))


def external_fetch_detail(session, food):
    if food['source'] == 'mfp':
        return fitnesspal.fetch_detail(session, food)
    else:
        raise ValueError(food['source'])

def external_food_from_url(session, source, url):
    if source != 'tesco':
    	raise ValueError(source)

    return tesco.parse_url(url)


def format_food(item, detail, all_nutrients):
    result = []
    result.append(lxml_to_text(item["descForUi"]))
    parser = FoodParser(detail)
    if all_nutrients:
        #print(json.dumps(item, indent=4))

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
