# See interactive-debug-session.py for details of scraping

# make code as python 3 compatible as possible
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import datetime
import json
import logging
import re
import sys

import lxml.etree
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
    PARSER.add_argument('--start-date', type=parse_date, default='2012-01-01', help='Fetch information from this date')
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
        print('Configuration file not found: {0}'.format(CREDENTIALS_FILE), file=sys.stderr)
        sys.exit(ex)


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

def main():
    args = build_parser().parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug('Establishing session')
    logon_payload = load_credentials(CREDENTIALS_FILE)
    with requests.Session() as session:
        session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)

        fetch_weights(session, args.start_date)

        with open("nutrition.csv", "w") as nutrition_csv:
            fetch_nutrition(nutrition_csv, session, args.start_date)

if __name__ == '__main__':
	main()
