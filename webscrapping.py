# See interactive-debug-session.py for details of scraping

# make code as python 3 compatible as possible
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime
import itertools
import json
import logging
import re
import sys

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

def build_parser():
    PARSER = argparse.ArgumentParser(description='Extract data from mynetdiary')

    PARSER.add_argument('--debug', action='store_true', help='Print debug output')

    parsers = PARSER.add_subparsers(dest='command')


    history_parser = parsers.add_parser('history', help='')
    history_parser.add_argument('--debug', action='store_true', help='Print debug output')
    history_parser.add_argument('--start-date', type=parse_date, default='2012-01-01', help='Fetch information from this date')

    new_food_parser = parsers.add_parser('new-food', help='Create a new food')
    new_food_parser.add_argument('--name', type=str)

    food_parser = parsers.add_parser('food', help='Search food database')
    food_parser.add_argument('name', type=str, help='Substring of the food you want to search', nargs='+')
    food_parser.add_argument('--raw', action='store_true', help='Output raw json')
    food_parser.add_argument('--index', type=int, help='Only show this item')
    food_parser.add_argument('--detail', action='store_true', help='Output information about foods')

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
    new_food_parser.add_argument('--caffeine', type=float, default='serving', nargs='*', help='Milligrams of caffeine')
    new_food_parser.add_argument('--potassium', type=float, default='serving', nargs='*', help='Milligrams of potassium')

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



def main():
    args = build_parser().parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug('Establishing session')
    logon_payload = load_credentials(CREDENTIALS_FILE)
    with requests.Session() as session:
        session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)

        if args.command == 'history':
            fetch_weights(session, args.start_date)

            with open("nutrition.csv", "w") as nutrition_csv:
                fetch_nutrition(nutrition_csv, session, args.start_date)
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
                                break
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
                            print(format_food(x, args.detail))
                        except BrokenPipeError:
                            return
                #print("\n".join(x["recentBeanDesc"] for x in food_json['entries']))
        else:
            raise ValueError(args.command)


def format_food(item, detail):
    result = []
    result.append(lxml_to_text(item["descForUi"]))
    if detail:
        for stat in item["details"]:
            if stat["nutrDesc"] == "Calories":
                result.append("    Calories: {}".format(stat["nutrValue"]))

        if item["isGramless"]:
            result.append("    Amount: {}".format(item["gramlessAmountMeasure"]))



    return '\n'.join(result)

def lxml_to_text(html):
    doc = lxml.html.fromstring(html)
    doc = lxml.html.clean.clean_html(doc)
    return doc.text_content()



if __name__ == '__main__':
	main()
