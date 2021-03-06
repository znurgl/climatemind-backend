import requests
import json

url = 'http://127.0.0.1:5000/get_user_scores'

with open('sample_user_response.json') as json_file:
    obj = json.load(json_file)

headers = {'content-type' : 'application/json'}
request = requests.post(url, json=obj, headers=headers)

print(json.dumps(request.json(), indent=4))