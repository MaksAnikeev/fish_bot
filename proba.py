import environs
import requests
from pprint import pprint
import os
import logging
import redis

from textwrap import dedent
from telegram import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from more_itertools import chunked
from functools import partial

env = environs.Env()
env.read_env()

# client_id = env.str("CLIENT_ID")
# client_secret = env.str("CLIENT_SECRET")
#
# data = {
#         'client_id': client_id,
#         'client_secret': client_secret,
#         'grant_type': 'client_credentials',
#     }
# response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
# access_token = response.json()['access_token']
# print(access_token)

access_token = 'f2ae30e1c2acfc4cd756259bc8c425dfa8efc078'

# headers = {
#     'Authorization': f'Bearer {access_token}',
#     'Content-Type': 'application/json'
# }
# json_data = {
#     'data': {
#         'type': 'cart_item',
#         'id': '23d0e2f9-2234-49bc-a132-cf9c3828fec5',
#         "quantity": 1,
#     }
# }
# response = requests.post('https://api.moltin.com/v2/carts/abc/items', headers=headers, json=json_data)
#
# pprint(response.json())

headers = {
    'Authorization': f'Bearer {access_token}',
}

response = requests.delete('https://api.moltin.com/v2/carts/704859099', headers=headers)

print(response)

# 704859099