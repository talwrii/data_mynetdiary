# See interactive-debug-session.py for details of scraping

# make code as python 3 compatible as possible
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import contextlib
import datetime
import json
import logging
import os
import pprint
import re
import sys

import http
import requests
import yaml

from . import fitnesspal, mynetdiary, load, parse_utils, mynetdiary_parser, types

if sys.version_info[0] != 3:
    # FileNotFoundError does not exist in python 2
    raise Exception('Only works with python 3')

LOGGER = logging.getLogger()

# Configuration
TODAY = datetime.date.today()


DEFAULT_CONFIG_DIR =  os.path.join(os.environ['HOME'], '.config', 'foodcli')
if not os.path.isdir(DEFAULT_CONFIG_DIR):
   os.mkdir(DEFAULT_CONFIG_DIR)


def build_parser():
    PARSER = argparse.ArgumentParser(description='Extract data from mynetdiary')

    PARSER.add_argument('--debug', action='store_true', help='Print debug output')
    PARSER.add_argument('--config-dir', type=str, help='Configuration directory', default=DEFAULT_CONFIG_DIR)

    parsers = PARSER.add_subparsers(dest='command')

    history_parser = parsers.add_parser('history', help='')
    history_parser.add_argument('--debug', action='store_true', help='Print debug output')
    history_parser.add_argument('--start-date', type=parse_date, default='2012-01-01', help='Fetch information from this date')

    items_parser = parsers.add_parser('items', help='Show what you have eaten today')
    items_parser.add_argument('--day', type=parse_date, help='Show items for this day', default=TODAY)
    items_parser.add_argument('--raw', action='store_true', help='Show raw data')
    items_parser.add_argument('--index', type=int, help='Select this index')
    items_parser.add_argument('--amount', type=float, help='Amount of this item to add. Default to the item amount.')
    items_parser.add_argument('--json', action='store_true', help='Output json data.')

    items_action = items_parser.add_mutually_exclusive_group()
    items_action.add_argument('--delete', action='store_true', help='Delete items')
    items_action.add_argument('--add', action='store_true', help='Add this item to todays food')
    items_parser.add_argument('search', type=str, help='Only show foods matching all these search terms', nargs='*')

    ext_food = parsers.add_parser('ext-food', help='Look up foods from another source')
    ext_food.add_argument('source', type=str, help='Source of food information', choices=('mfp', 'tesco'))
    ext_food.add_argument('name', nargs='*', help='Name of food source')
    ext_food.add_argument('--index', type=int, help='Only show item with this index')
    ext_food.add_argument('--detail', action='store_true', help='Show details about food')
    ext_food.add_argument('--url', type=str, help='Get the food for this url')
    ext_food.add_argument('--create', action='store_true', help='Create a new food form this item')

    food_parser = parsers.add_parser('food', help='Search foods and add them')
    food_parser.add_argument('name', type=str, help='Substring of the food you want to search', nargs='+')
    food_parser.add_argument('--raw', action='store_true', help='Output raw json')
    food_parser.add_argument('--delete', action='store_true', help='Delete this food')
    food_parser.add_argument('--index', type=int, help='Only show this item')
    food_parser.add_argument('--add', type=float, help='Add this many units of this food')
    food_parser.add_argument('--day', type=parse_date, help='Day to add food')

    food_parser_unit = food_parser.add_mutually_exclusive_group()
    food_parser_unit.add_argument('--detail', action='store_true', help='Output information about foods')
    food_parser_unit.add_argument('--all', action='store_true', help='Output all nutritional information')
    food_parser_unit.add_argument('--json', action='store_true', help='Output data as json')

    total_parser = parsers.add_parser('total', help='Search foods and add them')

    new_food_parser = parsers.add_parser('new', help='Create a new food')
    new_food_parser.add_argument('--name', type=str)
    new_food_parser.add_argument('--file', type=str, help='Read food information from this file')
    new_food_parser.add_argument('--expand', '-x', action='store_true', help='Expanded output')
    new_food_parser.add_argument('--grams', type=float, help='Serving size in grams')
    new_food_parser.add_argument('--salt', dest='sodium', type=salt_to_sodium, help='Serving size in grams')

    GRAM_UNITS = [
        'calories',
        'fat',
        'sodium',
        'fiber',
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
    PERCENT_VIT = [['A', ' vitamin a'], 'B6', 'B12', ['C', ' vitamin c'], ['D', 'vitamin d'], 'E', 'K']

    PERCENT_MINERALS = [
        'calcium',
        'iron',
        'thiamin',
        'riboflavin',
        'niacin',
        'folate',
        ['pan', ' panthothenic acid'],
        'phosphorus',
        'magnesium',
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


MYNETDIARY_NUTR  = dict(
    alcohol='alcoholEthylG',
    sugar='sugarsG',
    mono_un='monoUnsatFatG',
    carbs='totalCarbsG',
    chol='cholMg',
    grams='vitaminCPercent',


    percent_C='vitaminCPercent',
    percent_A='vitaminAPercent',
    percent_D='vitaminDPercent',
    percent_E='vitaminEPercent',
    percent_B6='vitaminB6Percent',
    percent_K='vitaminKPercent',
    percent_phosphorus='phosphorusPercent',
    percent_niacin='niacinPercent',
    percent_copper='copperPercent',
    percent_iron='ironPercent',
    percent_folate='folatePercent',
    percent_selenium='seleniumPercent',
    percent_calcium='calciumPercent',
    percent_zinc='zincPercent',
    percent_riboflavin='riboflavinPercent',
    percent_thiamin='thiaminPercent',
    percent_manganese='manganesePercent',
    percent_magnesium='magnesiumPercent',
    fat='totalFatG',
    starch='starchG',
    percent_B12='vitaminB12Percent',
    sodium='sodiumMg',
    protein='proteinG',
    caffeine='caffeineMg',
    fiber='dietaryFiberG',
    saturates='satFatG',
    potassium='potassiumMg',
    trans='transFatG',
    poly_un='polyUnsatFatG',
    percent_pan='panthothenicAcidPercent',
    )

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
                raise Exception('Error reading file: {0}'.format(credentials_file))
    except FileNotFoundError:
        raise Exception('Configuration file not found: {0}'.format(credentials_file))


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

    credentials = os.path.join(args.config_dir, 'credentials.yaml')

    LOGGER.debug('Establishing session')
    logon_payload = load_credentials(credentials)
    with requests.Session() as session:
        session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)

        if args.command == 'new':
            if args.file:
                with open(args.file) as stream:
                    raw_information = json.load(stream)

                food_information = load.parse_information(raw_information)
            else:
                food_information = dict(args._get_kwargs())
                food_information.pop('file')
                food_information.pop('command')
                food_information.pop('config_dir')
                food_information.pop('debug')
                food_information.pop('expand')


                name = food_information.pop('name', None)
                food_information['customFoodName'] = name

                for key, value in list(food_information.items()):
                    if key in MYNETDIARY_NUTR:
                        food_information[MYNETDIARY_NUTR[key]] = food_information.pop(key)

                if args.grams:
                    food_information['serving1Name'] = 'serving'
                    food_information['serving1Weight'] = 100



            mynetdiary.create_food(session, food_information)
        elif args.command == 'history':
            fetch_weights(session, args.start_date)
            with open("nutrition.csv", "w") as nutrition_csv:
                mynetdiary.fetch_nutrition(nutrition_csv, session, args.start_date)
        elif args.command == 'items':
            items = mynetdiary.get_eaten_items(session, args.day)
            parser = mynetdiary_parser.ItemsParser(items)
            with log_on_error('Raw items: %s', pprint.pformat(items)):
                if args.raw:
                    print(json.dumps(items, indent=4))
                else:
                    if not parser.entries():
                        return

                    formatter = EntryFormatter(parser.entries())

                    index = -1
                    for entry in parser.entries():

                        if args.search:
                            if any(not re.search(s, entry.food_name()) for s in args.search):
                                continue

                        index += 1

                        if args.index and index != args.index:
                            continue

                        if args.delete:
                            mynetdiary.save_item(session, None, entry, items)
                        elif args.add:
                            todays_items = mynetdiary.get_eaten_items(session, datetime.date.today())
                            amount = entry.amount()
                            if args.amount is not None:
                                amount = amount._replace(number=args.amount)
                            mynetdiary.save_item(session, amount, entry, todays_items)


                        if args.json:
                            output = dict(name=entry.food_name())
                            output.update(entry.nutrition())
                            output['amount'] = entry.amount()
                            print(json.dumps(output))
                        else:
                            print(formatter.format_column(entry))


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
                finished = False
                for item in mynetdiary.find_foods(session, food_specifier):
                    if not item["entries"]:
                        break

                    if finished:
                        break

                    for x in item["entries"]:
                        index += 1
                        if args.index is not None and index < args.index:
                            continue
                        elif args.index is not None and index > args.index:
                            finished = True
                            break

                        try:
                            if args.delete:
                                items = mynetdiary.delete_food(session, x['beanId'])
                            elif args.add:
                                items = mynetdiary.get_eaten_items(session, args.day)
                                mynetdiary.save_item(session, types.Amount(number=args.add, is_grams=True), mynetdiary_parser.FoodParser(x), items)

                            else:
                                print(format_food(x, args.detail, args.all, args.json))
                        except BrokenPipeError:
                            return
                #print("\n".join(x["recentBeanDesc"] for x in food_json['entries']))

        elif args.command == 'total':
            today = datetime.date.today()
            items = mynetdiary.get_eaten_items(session, today)
            parser = mynetdiary_parser.ItemsParser(items)
            formatter = EntryFormatter([parser.total()], True)
            total_grams = 0
            for x in parser.entries():
                amount = x.amount()
                if amount.is_grams:
                    total_grams += amount.number
            print(formatter.format_column(parser.total(), amount=total_grams))
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
                details = external.food_from_url(session, args.source, args.url)
                show_external_food(details)
            else:
                if args.index is not None:
                    foods = [foods[args.index]]

                for food in foods:
                    print(food['name'])
                    if args.detail:
                        details = external.fetch_detail(session, food)
                        show_external_food(details)

            if args.create:
                details = external_create_food(session, details)
        else:
            raise ValueError(args.command)

def show_external_food(details):
    for k, v in details.items():
        print('    {}: {}'.format(k, v))

def format_food(item, detail, all_nutrients, is_json):
    result = []

    gramless = item.get("isGramless")
    if gramless:
        amount_string = item["gramlessAmountMeasure"]
        mutliplier = 1
    else:
        multiplier = 1
        amount_string = '100 grams'

    if 'dfSrv' in item:
        if not gramless:
            serving_string = '{}: {}g'.format(item['dfSrv']['desc'], item['dfSrv']['gmWgt'])
        else:
            serving_string = '{}'.format(item['dfSrv']['desc'])
    else:
        serving_string = ''


    name = parse_utils.lxml_to_text(item["descForUi"])
    parser = mynetdiary_parser.FoodParser(item)
    if is_json:
        data = dict(name=name, nutrients_per=amount_string, serving_size=serving_string)

        for item in sorted(item['details'], key=lambda x: float(x['nutrValue']), reverse=True):
            data[item['nutrDesc']] = dict(value=item['nutrValue'], unit=item['units'])

        return json.dumps(data, indent=4)
    else:
        result.append('{} (per {}) (serving {})'.format(name, amount_string, serving_string))
        if all_nutrients:
            #print(json.dumps(item, indent=4))

            for item in sorted(item['details'], key=lambda x: float(x['nutrValue']), reverse=True):
                result.append('    {} {}{}'.format(item['nutrDesc'], item['nutrValue'], item['units']))

        elif detail:
            for stat in item["details"]:
                if stat["nutrDesc"] == "Calories":
                    result.append("    Calories: {}".format(stat["nutrValue"]))

            LOGGER.debug('Formatting food: %s', json.dumps(item, indent=4))
        return '\n'.join(result)

def log_http():
    http.client.HTTPConnection.debuglevel = 1

    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class EntryFormatter(object):
    def __init__(self, entries, expand=False):
        self.desc_width = max([len(x.food_name()) for x in entries])
        self.amount_width = max([len(x.amount_string()) for x in entries])
        self.columns_printed = False
        self.expand = expand

    def format_column(self, entry, amount=None):
        nutrition = entry.nutrition()
        density = nutrition['Cals'] / entry.amount_value()

        if amount is not None:
            amount_value = amount
            amount = '{} {}'.format(amount, entry.amount_name())
        else:
            amount_value = entry.amount_value()
            amount = '{} {}'.format(amount_value, entry.amount_name())


        energy_calories = nutrition['Cals'] - nutrition['Protein'] * PROTEIN_CALS - nutrition['Fiber'] * FIBER_CALS
        energy_calories_density = energy_calories / amount_value


        columns = (
            ('name', entry.food_name().ljust(self.desc_width)),
            ('amount', amount.ljust(self.amount_width)),
            ('calories', '{:8.0f}'.format(nutrition['Cals'])),
            ('non-protein calories', '{:5.1f}'.format(energy_calories)),
            ('energy_calorie_density', '{:5.1f}'.format(energy_calories_density)),
            ('carbs', '{:5.1f}'.format(nutrition['Carbs'])),
            ('fat', '{:5.1f}'.format(nutrition['Fat'])),
            ('protein', '{:5.1f}'.format(nutrition['Protein'])),
            ('fiber', '{:5.1f}'.format(nutrition['Fiber'])),
            ('density', '{:5.1f}'.format(density))
        )
        result = []

        if self.expand:
            for k, v in columns:
                result.append('{} {}'.format(k, v))
        else:
            if not self.columns_printed:
                result.append(':'.join([c[0] for c in columns]))
                self.columns_printed = True

            result.append(':'.join([c[1] for c in columns]))
        return '\n'.join(result)

def salt_to_sodium(amount):
    return float(amount) / 2.5


PROTEIN_CALS = 4
FIBER_CALS = 2




if __name__ == '__main__':
	main()
