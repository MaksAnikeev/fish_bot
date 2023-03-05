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

# headers = {
#     'Authorization': f'Bearer {access_token}',
#     'Content-Type': 'application/json',
# }
#
# json_data = {
#     'data': {
#         'id': '23d0e2f9-2234-49bc-a132-cf9c3828fec5',
#         'type': 'cart_item',
#         'quantity': 8,
#             }
#         }
#
# response = requests.post('https://api.moltin.com/v2/carts/abc/items', headers=headers, json=json_data)
# pprint(response.json())

import os
import logging
import redis

from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

_database = None


def start(update, context):
    update.message.reply_text(text='Привет!')
    return "ECHO"


def echo(update, context):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id)

    print(user_state)

    states_functions = {
        'START': start,
        'ECHO': echo
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    global _database
    if _database is None:
        database_password = env.str("DATABASE_PASSWORD")
        database_host = env.str("DATABASE_HOST")
        database_port = env.str("DATABASE_PORT")
        _database = redis.StrictRedis(host=database_host,
                                      port=database_port,
                                      password=database_password,
                                      charset="utf-8",
                                      decode_responses=True)
    return _database


if __name__ == '__main__':
    token = env.str("TG_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    updater.start_polling()