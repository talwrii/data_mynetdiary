"Food parsing for mynetdiary"

import itertools
import json
import logging

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

    LOGGER.debug('Saving : food_type=%s', parser.dump())

    if amount is None:
        amount_specifier = None
        amount_id = None
    elif amount.is_grams:
        amount_specifier = amount.number
        amount_id = None
    else:
        amount_id = parser.amount_id()
        amount_specifier = parser.amount_string(amount)


    number_of_entries = len(items['beanEntries'])
    entry_number_id = '1{:02}'.format(number_of_entries)

    # Adding gram amounts [reverse.md#Adding Grams]
    response = session.post('http://www.mynetdiary.com/dailyFoodSave.do',
        data=json.dumps(dict(
            mealTypeId=1,
            beanInputString=parser.food_name(),
            beanId=parser.bean_id(),
            beanEntryNo=entry_number_id,
            parent_bean_id=parent_bean_id,
            amountInputString=amount_specifier,
            amountId=amount_id,
            calculateAmount=True)),
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
