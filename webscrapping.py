#import urllib2
import sys
import requests

import json
import datetime


from bs4 import BeautifulSoup
import re
def extract_data(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    data = soup.find_all('script')[10].text
    #pattern = re.compile('\n\n.*measurementsPM = (.*);')
    pattern = re.compile('.*measurementsPM = ([^;]*);',re.DOTALL)
    return pattern.match(data)

# Configuration
credentials_file = "credentials.yaml"
startDate = '2012-01-01'

print('Establish session')
#https://www.mynetdiary.com/logonPage.do
#r = requests.get('https://www.mynetdiary.com/dailyDetails.do?date=20161206')
#print(r.status_code)
#print(r.text)

try:
  with open(credentials_file, "r") as stream:
    try:
        credentials = yaml.load(stream)
        logon_payload = {
            'logonName': credentials['mynetdiary']['username'],
            'password': credentials['mynetdiary']['password']
        }
    except yaml.YAMLError as error:
        print('Error reading file: {0}'.format(credentials_file), file=sys.stderr)
        sys.exit(error)
except FileNotFoundError:
    print('Configuration file not found: {0}'.format(credentials_file), file=sys.stderr)
    sys.exit(ex)


count_no_weight = 0
count_pages = 0

with requests.Session() as session:
    response = session.post("https://www.mynetdiary.com/logon.do", data=logon_payload)

    print('Get pages since : ${0}'.format(startDate))
    start = datetime.datetime.strptime(startDate,'%Y-%m-%d')
    end = datetime.datetime.today()
    difference = end-start

    with open("output.csv", "w") as weights_file:
        for i in range(1,difference.days):
            dayDatetime = start+datetime.timedelta(days=i)
            time = dayDatetime.strftime('%Y%m%d')
    
            response = session.get('https://www.mynetdiary.com/dailyDetails.do?date={0}'.format(time))
    
            count_pages+=1
            #with open("a.html", "w") as text_file:
            #  text_file.write(response.text)
            match = extract_data(response.text)
    
            ajson = json.loads(match.groups()[0])
            if ajson[0]['measurementId'] == 40:
                weightValue = ajson[0]['currentValue']
                if weightValue is not None:
                    weights_file.write("{0},{1}\n".format(dayDatetime.strftime('%Y-%m-%d'), re.sub('kg$','', ajson[0]['currentValue'])) )
                else:
                    count_no_weight+=1
            else:
                count_no_weight+=1

print("{0}/{1} pages contained no weight".format(count_no_weight, count_pages))

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
