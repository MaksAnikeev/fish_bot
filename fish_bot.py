import environs
import requests
from pprint import pprint

env = environs.Env()
env.read_env()

client_id = env.str("CLIENT_ID")
client_secret = env.str("CLIENT_SECRET")

# data = {
#     'client_id': client_id,
#     'client_secret': client_secret,
#     'grant_type': 'client_credentials',
# }
#
# response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
#
# pprint(response.json())

access_token = env.str("ACCESS_TOKEN_BEARER")

headers = {
    'Authorization': f'Bearer {access_token}',
}

product_id = '34f47762-385c-48fb-b985-915d565a3229'

response = requests.get(f'https://api.moltin.com/pcm/products/{product_id}', headers=headers)
product_data = response.json()

name = product_data['data']['attributes']['name']
sku = product_data['data']['attributes']['sku']
description = product_data['data']['attributes']['description']

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

# json_data = {
#     'data': {
#         'type': 'cart_item',
#         # 'name': name,
#         'sku': sku,
#         # 'description': description,
#         'quantity': 3,
#         # "price": {
#         #   "amount": 30
#         # }
#     },
# }

json_data = {
    'data': {
        'id': '23d0e2f9-2234-49bc-a132-cf9c3828fec5',
        'type': 'cart_item',
        'quantity': 8,
        'custom_inputs': {
              "name": {
                "T-Shirt Front": "Jane",
                "T-Shirt Back": "Jane Doe's Dance Academy"
               }
            }
    }
}

response = requests.post('https://api.moltin.com/v2/carts/abc/items', headers=headers, json=json_data)

# headers = {
#     'Authorization': f'Bearer {access_token}',
# }
# response = requests.get('https://api.moltin.com/v2/carts/abc/items', headers=headers)
pprint(response.json())


