import itertools

from . import parse_utils, types


class ItemsParser(object):
    def __init__(self, data):
        self.data = data

    def headers(self):
        return [header_string.split('<br/>')[0] for header_string in self.data['nutrColumnHeaders']]

    def entries(self):
        return [HistoryParser(self.headers(), x) for x in self.data['beanEntries'] if 'bean' in x]

    def total(self):
        return Totals(self.headers(), self.data['beanGridTotals'])


class FoodParser(object):
    "Parse the entry for a type of food."
    def __init__(self, data):
        self.data = data

    def amount_string(self, amount=None):
        amount = amount or self.data['dfSrv']['am']
        amount_name = self.amount_name()
        return '{} {}'.format(amount, amount_name),

    def amount_name(self):
        return self.data['dfSrv']['desc']

    def bean_id(self):
        return self.data['beanId']

    def food_name(self):
        return parse_utils.lxml_to_text(self.data['descForUi'])

    def dump(self):
        return self.data

    def amount_id(self):
        return self.data['dfSrv']['id']

class HistoryParser(object):
    def __init__(self, headers, data):
        self.headers = headers
        self.data = data

    def bean_id(self):
        return self.data['bean']['beanId']

    def food_name(self):
        return self.data['bean']['beanDesc']

    def dump(self):
        return self.data

    def amount_id(self):
        raise NotImplementedError()

    def entry_number_id(self):
        return self.data['beanEntryKey']['beanEntryNo']

    def amount_value(self):
        amount, _amount_string = parse_amount(self.data['amountResolved'])
        return amount

    def amount(self):
        is_grams = not self.data.get('isGramless')
        return types.Amount(number=self.amount_value(), is_grams=is_grams)

    def amount_string(self):
        _amount, amount_string = parse_amount(self.data['amountResolved'])
        return amount_string

    def nutrition(self):
        return dict(zip(self.headers, map(comma_float, [x or '-1' for x in self.data['nutrValues']])))

    def amount_name(self):
        return ''.join(reversed(
            list(itertools.takewhile(lambda x: x not in '01234567890', reversed(self.data['amountResolved'])))))

class Totals(object):
    def __init__(self, headers, data):
        self.data = data
        self.headers = headers

    def nutrition(self):
        return dict(zip(self.headers, map(comma_float, [x or '-1' for x in self.data['totalNutrValues']])))

    @staticmethod
    def food_name():
        return 'Total'

    @staticmethod
    def amount_string():
        return ''

    @staticmethod
    def amount_value():
        return 1.0

    @staticmethod
    def amount_name():
        return 'g'


def parse_amount(string):
    number = parse_utils.initial_digits(string)

    unit = string[len(number):]
    factor, new_unit = CONVERSIONS.get(unit, (1, 'unit'))
    new_number = float(number) * factor
    return new_number, '{:.1f}'.format(new_number) + ' ' + new_unit


def comma_float(x):
    return float(x.replace(',', ''))

CONVERSIONS = {
    'tbsp': (14.7868, 'ml'),
    'g': (1, 'g'),
}
