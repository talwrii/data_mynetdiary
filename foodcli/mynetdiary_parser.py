from . import parse_utils

class ItemsParser(object):
    def __init__(self, data):
        self.data = data

    def headers(self):
        return [header_string.split('<br/>')[0] for header_string in self.data['nutrColumnHeaders']]

    def entries(self):
        return [HistoryParser(self.headers(), x) for x in self.data['beanEntries'] if 'bean' in x]

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

    def amount(self):
        amount, _amount_string = parse_amount(self.data['amountResolved'])
        return amount

    def amount_string(self):
        _amount, amount_string = parse_amount(self.data['amountResolved'])
        return amount_string

    def nutrition(self):
         return dict(zip(self.headers, map(comma_float, [x or '-1' for x in self.data['nutrValues']])))

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