"Food parsing for mynetdiary"

import itertools
import json
import logging
import pprint

LOGGER = logging.getLogger(__name__)

def get_eaten_items(session, dt):
    LOGGER.debug('Fetching data for %r', dt)
    # Why would this be json?!
    #curl 'http://www.mynetdiary.com/daily.do?date=20170601' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496382923.1496386317.24; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=rkTD82GiHepAyy42; JSESSIONID=ePQrD6nXbP0u; __utmc=190183351; WHICHSERVER=SRV128001; __utmb=190183351.2.10.1496386317; __utmt=1' -H 'Connection: keep-alive'
    date_string = dt.strftime('%Y%m%d')
    response = session.get('http://www.mynetdiary.com/daily.do?date={}'.format(date_string))
    data = response.content.decode('utf8')
    line, = [l for l in data.splitlines() if 'initialFoodGridPM' in l]
    json_string = line.split('=')[1][1:-1]
    return json.loads(json_string)


def save_item(session, amount, parser, items):
    # curl 'http://www.mynetdiary.com/dailyFoodSave.do' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/javascript, text/html, application/xml, text/xml, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'X-Requested-With: XMLHttpRequest' -H 'X-Prototype-Version: 1.5.0' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496386317.1496517505.25; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=rkTD82GiHepAyy42; JSESSIONID=fBfrKjhhIKqQ; WHICHSERVER=SRV118002; __utmb=190183351.1.10.1496517505; __utmc=190183351; __utmt=1' -H 'Connection: keep-alive' --data '{"parentBeanId":139410013,"beanEntryNo":101,"beanId":2156966,"beanInputString":"Fever tree tonic","amountInputString":"bottle","amountId":"1","mealTypeId":1,"calculateAmount":true}'

    # TODO: parentbeanid is contained within the food grid
    #   it identifies which day items are added to

    parent_bean_id = items["parentBeanId"]

    #print(json.dumps(details, indent=4))

    LOGGER.debug('Saving : food_type=%s', pprint.pformat(parser.dump()))

    if amount is None:
        amount_specifier = None
        amount_id = None
    elif amount.is_grams:
        amount_specifier = str(amount.number)
        amount_id = None
    else:
        amount_id = parser.amount_id()
        amount_specifier = parser.amount_string(amount)

#    for x in items['beanEntries']:
#        if 'bean' in x:
#            print(x['bean'].keys())

    currents_ids = set([x['beanEntryKey']['beanEntryNo'] for x in items['beanEntries'] if 'bean' in x])
    #print(pprint.pformat(items['beanEntries']))

    if amount is not None:
        for i in range(1, 100):
            entry_number_id = int('1{:02}'.format(i))
            if entry_number_id not in currents_ids:
                break
        else:
            raise Exception('Could not find exception')
    else:
        entry_number_id = parser.entry_number_id()

    post_data = dict(
            mealTypeId=1,
            beanInputString=parser.food_name(),
            beanId=amount and parser.bean_id(),
            beanEntryNo=entry_number_id,
            parentBeanId=parent_bean_id,
            amountInputString=amount_specifier,
            amountId=amount and amount_id,
            calculateAmount=True)

    if amount is None:
        post_data['amountResolved'] = None


    LOGGER.debug('Post data: %s', pprint.pformat(post_data))
    # Adding gram amounts [reverse.md#Adding Grams]
    response = session.post('http://www.mynetdiary.com/dailyFoodSave.do',
        data=json.dumps(post_data),
            headers={'Content-Type': "application/x-www-form-urlencoded" })
    response.raise_for_status()

    #print(response.status_code)
    #print(response.content)


def find_foods(session, name):
    # Original request (from firefox)
    # curl 'http://www.mynetdiary.com/findFoods.do' -H 'Host: www.mynetdiary.com' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' -H 'Accept: text/javascript, text/html, application/xml, text/xml, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'DNT: 1' -H 'X-Requested-With: XMLHttpRequest' -H 'X-Prototype-Version: 1.5.0' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'Referer: http://www.mynetdiary.com/daily.do' -H 'Cookie: __utma=190183351.107001975.1486834740.1496379979.1496382923.23; __utmz=190183351.1488146888.3.3.utmcsr=duckduckgo.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __unam=596c074-15a2e43c3ca-4e397692-4; partnerId=0; _ga=GA1.2.107001975.1486834740; rememberMe=XXXXXX; JSESSIONID=XXXXXXXX; __utmc=190183351; WHICHSERVER=SRV118002; __utmb=190183351.2.10.1496382923; __utmt=1' -H 'Connection: keep-alive' --data 'beanInputString=bla&pageSize=15&pageNumber=1&highlightedTermClassName=sughtrm&detailsExpected=true'
    for page in itertools.count(1):
        constant_data = [('pageSize', '100'), ('highlightedTermClassName', 'sughtrm'), ('detailsExpected', 'true')]
        data = session.post('http://www.mynetdiary.com/findFoods.do', data=[("beanInputString", name), ('pageNumber', str(page))] + constant_data)
        data = data.content.decode('utf8')
        if data[:12] ==  "OK `+`json":
            raise Exception('Request format wrong')
        yield json.loads(data[11:])


def create_food(session, information):
    required_keys = set(['customFoodName'])

    allowed_keys = ['customFoodName', 'serving1Name', 'serving1Weight', 'foodGroupId', 'calories', 'totalFatG', 'satFatG', 'polyUnsatFatG', 'monoUnsatFatG', 'transFatG', 'cholMg', 'sodiumMg', 'totalCarbsG', 'dietaryFiberG', 'sugarsG', 'sugarAlcoholG', 'proteinG', 'vitaminAPercent', 'vitaminCPercent', 'calciumPercent', 'ironPercent', 'caffeineMg', 'waterG', 'alcoholEthylG', 'starchG', 'potassiumMg', 'vitaminDPercent', 'vitaminB6Percent', 'vitaminB12Percent', 'vitaminEPercent', 'vitaminKPercent', 'thiaminPercent', 'riboflavinPercent', 'niacinPercent', 'folatePercent', 'panthothenicAcidPercent', 'phosphorusPercent', 'magnesiumPercent', 'zincPercent', 'seleniumPercent', 'cooperPercent', 'manganesePercent', 'customFoodId', 'contributed', 'sorceFoodId']

    missing_keys = set(required_keys) - set(information.keys())
    if missing_keys:
        raise Exception('information need keys: {}'.format(missing_keys))

    unknown_keys = set(information.keys()) - set(allowed_keys)
    if unknown_keys:
        raise Exception('Information contains unknown keys: {}'.format(unknown_keys))

    for key in allowed_keys:
        if key not in information:
            information[key] = ''

    response = session.post('http://www.mynetdiary.com/customFoodUpdate.do', data=information)
    #print(response.content)

def delete_food(session, bean_id):
    session.post('http://www.mynetdiary.com/retireUserFood.do', data=[('value', bean_id)])

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
