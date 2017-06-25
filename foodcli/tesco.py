import lxml.etree

def parse_url(url):
    data = session.get(url).content
    tree = lxml.etree.HTML(data)
    _header, *rows, _reference = tree.xpath('//table[caption/text()="Nutrition"]/descendant::tr')
    result = dict()

    title_string, *_ = tree.xpath('//span[@data-title="true"]/text()')
    name, amount_string = title_string.rsplit(' ', 1)

    result['name'] = name
    result['amount'] = initial_digits(amount_string)

    for row in rows:
        nutrient, = row.xpath('th/text()')
        per_hundred_grams, _serving  = row.xpath('td/text()')

        if nutrient == 'Energy':
            value_string = re.search(r"\(([0-9.]+)kcal\)", per_hundred_grams).group(1)
        elif per_hundred_grams.startswith('<'):
            value_string = '0'
        else:
            value_string = per_hundred_grams


        result[nutrient] = float(initial_digits(value_string))
    return result


