def parse_information(data):
    "Load food from a file."
    output = dict(data)
    if 'weight' in output:
        output['serving1Weight'] = output.pop('weight')
        output['serving1Name'] = output.pop('unit')

    if 'fat' in output:
        output['totalFatG'] = output.pop('fat')

    if 'carb' in output:
        output['totalCarbsG'] = output.pop('carb')

    if 'sugar' in output:
        output['sugarsG'] = output.pop('sugar')

    if 'protein' in output:
        output['proteinG'] = output.pop('protein')

    if 'sat' in output:
        output['satFatG'] = output.pop('sat')

    if 'salt' in output:
        output['sodiumMg'] = str(float(output.pop('salt')) / 2.5)

    if 'name' in output:
        output['customFoodName'] = output.pop('name')

    if 'per' in output:
        weight = float(output['serving1Weight'])
        per = output.pop('per')
        for x in output:
            if output[x].isdigit():
                output[x] = str(float(output[x]) * weight / float(per))
    return output

