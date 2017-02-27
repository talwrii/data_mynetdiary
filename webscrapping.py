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

LOGGER = logging.getLogger()

def extract_data(html_string):
    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
    match = pattern.match(html_string)
    return match and match.groups()[0]

# Configuration
CREDENTIALS_FILE = "credentials.yaml"

def parse_date(string):
    return datetime.datetime.strptime(string, '%Y-%m-%d')

PARSER = argparse.ArgumentParser(description='Extract data from mynetdiary')
PARSER.add_argument('--debug', action='store_true', help='Print debug output')
PARSER.add_argument('--start-date', type=parse_date, default='2012-01-01')
args = PARSER.parse_args()



try:
    with open(CREDENTIALS_FILE, "r") as stream:
        try:
            credentials = yaml.load(stream)
            logon_payload = {
                'logonName': credentials['mynetdiary']['username'],
                'password': credentials['mynetdiary']['password']
            }
        except yaml.YAMLError as error:
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
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug('Establishing session')
    with requests.Session() as session:
        response = session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)
        fetch_weights(session, args.start_date)

        with open("nutrition.csv", "w") as nutrition_csv:
            fetch_nutrition(nutrition_csv, session, args.start_date)


#https://www.mynetdiary.com/logonPage.do
#r = requests.get('https://www.mynetdiary.com/dailyDetails.do?date=20161206')
#print(r.status_code)
#print(r.text)

##    print(r.status_code)
#    r = session.get('https://www.mynetdiary.com/dailyDetails.do?date=20161204')
#    soup = BeautifulSoup(r.text, "html.parser")
#    data = soup.find_all('script')[10].text
#    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
#    match = pattern.match(data)
#
#    #print(match.groups()[0])
#    ajson=json.loads(match.groups()[0])
#    print(ajson[0]['measurementId'])
#    print(ajson[0]['currentValue'])
#
##    print(r.status_code)
#    r = session.get('https://www.mynetdiary.com/dailyDetails.do?date=20161205')
#
#    soup = BeautifulSoup(r.text, "html.parser")
#    data = soup.find_all('script')[10].text
#    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
#    match = pattern.match(data)
#
#    #print(match.groups()[0])
#    ajson=json.loads(match.groups()[0])
#    print(ajson[0]['measurementId'])
#    print(ajson[0]['currentValue'])
#
#
#    r = session.get('https://www.mynetdiary.com/dailyDetails.do?date=20161206')
##    print(r.status_code)
#    soup = BeautifulSoup(r.text, "html.parser")
#    data = soup.find_all('script')[10].text
#    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
#    match = pattern.match(data)
#
#    #print(match.groups()[0])
#    ajson=json.loads(match.groups()[0])
#    print(ajson[0]['measurementId'])
#    print(ajson[0]['currentValue'])


#a='[{"sortOrder":14099,"targetValue":"79kg","measurementDesc":"Body Weight","shortDesc":"Weight","measurementId":40,"initialValue":null,"longDesc":"This is a common body weight measurement. For consistency, it is recommended to take measurements approximately at the same time of the day.","selected":true,"currentValue":"81.2kg","isAutomatic":false},{"sortOrder":14500,"targetValue":"1726kcal","measurementDesc":"Basal Metabolic Rate (BMR)","shortDesc":"BMR","measurementId":84,"initialValue":null,"longDesc":"BMR is the number of calories you would burn if you stayed in bed all day, i.e. the energy needed to sustain your body.  BMR is estimated using your gender, height, weight, and age (Mifflin formula).","selected":true,"currentValue":"1748kcal","isAutomatic":true},{"sortOrder":14599,"targetValue":"24.1","measurementDesc":"Body Mass Index (BMI)","shortDesc":"BMI","measurementId":80,"initialValue":null,"longDesc":"Body mass index. For adults over 20 years old, BMI less than 18.5 indicates underweight, 18.5-24.9 - normal weight, 25.0-29.9 - overweight, and above that - obese.","selected":true,"currentValue":"24.8","isAutomatic":true},{"sortOrder":14600,"targetValue":null,"measurementDesc":"Blood pressure systolic/diastolic","shortDesc":"Blood press.","measurementId":49,"initialValue":null,"selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":14700,"targetValue":null,"measurementDesc":"Resting Pulse Rate","shortDesc":"Pulse","measurementId":60,"initialValue":null,"longDesc":"Resting pulse rate. After 5 minutes of rest, count for 30 seconds, and then multiply by 2.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":20100,"targetValue":null,"measurementDesc":"Hip Size","shortDesc":"Hips","measurementId":46,"initialValue":null,"selected":true,"currentValue":null,"isAutomatic":false},{"sortOrder":20200,"targetValue":null,"measurementDesc":"Waist size","shortDesc":"Waist","measurementId":55,"initialValue":null,"selected":true,"currentValue":null,"isAutomatic":false},{"sortOrder":20300,"targetValue":null,"measurementDesc":"Chest size","shortDesc":"Chest","measurementId":56,"initialValue":null,"selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":20400,"targetValue":null,"measurementDesc":"Thigh size","shortDesc":"Thigh","measurementId":57,"initialValue":null,"selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":20500,"targetValue":null,"measurementDesc":"Calf size","shortDesc":"Calf","measurementId":58,"initialValue":null,"selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":20600,"targetValue":null,"measurementDesc":"Bicep size","shortDesc":"Bicep","measurementId":59,"initialValue":null,"longDesc":"You can enter bicep size in english or metric units, such as \'15 in\' or \'38.1 cm\'","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":20700,"targetValue":null,"measurementDesc":"Neck circumference","shortDesc":"Neck circumf.","measurementId":63,"initialValue":null,"selected":true,"currentValue":null,"isAutomatic":false},{"sortOrder":30100,"targetValue":null,"measurementDesc":"Body fat percentage","shortDesc":"Body fat","measurementId":50,"initialValue":null,"longDesc":"Total body fat percentage consists of essential fat and storage fat. MyNetDiary can keep track of it, if you use a scale calculating body fat percentage.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":30200,"targetValue":null,"measurementDesc":"Bone weight","shortDesc":"Bone weight","measurementId":51,"initialValue":null,"longDesc":"Weight of all bones in your body.  MyNetDiary can keep track of that weight, if you use a scale that estimates bone weight.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":30300,"targetValue":null,"measurementDesc":"H2O percentage","shortDesc":"H2O","measurementId":52,"initialValue":null,"longDesc":"Percent of water (H2O) in your body.  MyNetDiary can keep track of this percentage, if you use a scale that estimates water percentage in your body.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":30400,"targetValue":null,"measurementDesc":"Lean muscle percentage","shortDesc":"Muscle percentage","measurementId":53,"initialValue":null,"longDesc":"Percentage of lean muscle mass in your body.  MyNetDiary can keep track of this percentage, if you use a scale that estimates lean muscle mass percentage.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":30500,"targetValue":null,"measurementDesc":"Lean muscle mass","shortDesc":"Muscle mass","measurementId":62,"initialValue":null,"longDesc":"Weight of lean muscle mass in your body.  MyNetDiary can keep track of this weight, if you use a scale that estimates lean muscle mass.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":40100,"targetValue":null,"measurementDesc":"Total hours of sleep","shortDesc":"Sleep","measurementId":54,"initialValue":null,"longDesc":"Total hours of sleep you\'ve got in 24 hours.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":40110,"targetValue":null,"measurementDesc":"Total hours of Deep sleep","shortDesc":"Deep Sleep","measurementId":111,"initialValue":null,"longDesc":"Total hours of deep sleep you\'ve got in 24 hours.","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40120,"targetValue":null,"measurementDesc":"Total hours of Light sleep","shortDesc":"Light Sleep","measurementId":112,"initialValue":null,"longDesc":"Total hours of light sleep you\'ve got in 24 hours.","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40130,"targetValue":null,"measurementDesc":"Total hours of Awakes","shortDesc":"Awakes","measurementId":113,"initialValue":null,"longDesc":"Total hours of awakes while sleep you\'ve got in 24 hours.","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40140,"targetValue":null,"measurementDesc":"Total hours of REM sleep","shortDesc":"REM Sleep","measurementId":115,"initialValue":null,"longDesc":"Total hours of REM sleep you\'ve got in 24 hours.","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40200,"targetValue":null,"measurementDesc":"Total hours of work","shortDesc":"Hours of work","measurementId":64,"initialValue":null,"longDesc":"Total hours of work you\'ve done in 24 hours.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":40300,"targetValue":null,"measurementDesc":"Daily Steps Count","shortDesc":"Daily Steps","measurementId":61,"initialValue":null,"longDesc":"Daily Step Count measurement helps you keep track of the number of walking steps, which could be counted with a pedometer.","selected":false,"currentValue":null,"isAutomatic":false},{"sortOrder":40310,"targetValue":null,"measurementDesc":"Total distance covered","shortDesc":"Distance","measurementId":114,"initialValue":null,"longDesc":"Total distance you\'ve covered in 24 hours.","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40400,"targetValue":null,"measurementDesc":"Wearable Tracker Calories Out","shortDesc":"Calories Out","measurementId":101,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40500,"targetValue":null,"measurementDesc":"Wearable Tracker Floors","shortDesc":"Floors","measurementId":102,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40600,"targetValue":null,"measurementDesc":"Wearable Tracker Activity Calories","shortDesc":"Activity Calories","measurementId":103,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40700,"targetValue":null,"measurementDesc":"Wearable Tracker Very Active Minutes","shortDesc":"Very Active Minutes","measurementId":104,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40800,"targetValue":null,"measurementDesc":"Wearable Tracker Fairly Active Minutes","shortDesc":"Fairly Active Minutes","measurementId":105,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":40900,"targetValue":null,"measurementDesc":"Wearable Tracker Lightly Active Minutes","shortDesc":"Lightly Active Minutes","measurementId":106,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":41000,"targetValue":null,"measurementDesc":"Wearable Tracker Total Active Minutes","shortDesc":"Active Minutes","measurementId":107,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":41100,"targetValue":null,"measurementDesc":"Wearable Tracker Activity BMR","shortDesc":"Activity BMR","measurementId":108,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true},{"sortOrder":41200,"targetValue":null,"measurementDesc":"Wearable Tracker Sedentary Minutes","shortDesc":"Sedentary Minutes","measurementId":109,"initialValue":null,"longDesc":"--","selected":false,"currentValue":null,"isAutomatic":true}]'
#ajson=json.loads(a)
#print(ajson[0]['measurementId'])
#print(ajson[0]['currentValue'])
#

if __name__ == '__main__':
	main()
