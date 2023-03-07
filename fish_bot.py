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

_database = None


def get_token():
    client_id = env.str("CLIENT_ID")
    client_secret = env.str("CLIENT_SECRET")

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    access_token = response.json()['access_token']
    return access_token


def get_products_params(access_token):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get('https://api.moltin.com/pcm/products', headers=headers)
    return response.json()


def get_product_params(access_token, product_id):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    params = {
        'include': 'prices',
    }
    response = requests.get(f'https://api.moltin.com/pcm/products/{product_id}',
                            headers=headers,
                            params=params)
    return response.json()


def get_product_prices(access_token, price_id):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/pcm/pricebooks/{price_id}/prices',
                            headers=headers)
    return response.json()


def get_product_files(access_token, file_id):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    return response.json()


def get_products_names(products_params):
    keyboard_products = [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
    for product in products_params['data']:
        button_name = product['attributes']['name']
        button_id = product['id']
        button = InlineKeyboardButton(button_name, callback_data=button_id)
        keyboard_products.insert(0, button)
    return keyboard_products


def start(update, context):
    keyboard = [[InlineKeyboardButton("Магазин", callback_data='store'),
                 InlineKeyboardButton("Моя корзина", callback_data='cart')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        update.message.reply_text('Привет! Сделай выбор:', reply_markup=reply_markup)
        return 'MAIN_MENU'
    except:
        query = update.callback_query
        context.bot.edit_message_text(text='Привет! Сделай выбор:',
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      reply_markup=reply_markup)
        return 'MAIN_MENU'


def send_products_keyboard(update, context, products_names):
    query = update.callback_query
    keyboard = list(chunked(products_names, 2))
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        context.bot.edit_message_text(
            text='Выбери товар из магазина:',
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup
        )
        return "STORE"
    except:
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        context.bot.send_message(
            text='Выбери товар из магазина:',
            chat_id=query.message.chat_id,
            reply_markup=reply_markup
        )
        return "STORE"


def button(update, context):
    query = update.callback_query

    if query.data == 'store':
        products_names = dispatcher.bot_data['products_names']
        return send_products_keyboard(update, context, products_names)

    elif query.data == 'cart':
        keyboard = [[InlineKeyboardButton("Главное меню", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_text(
            text="Моя корзина",
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup)
        return 'CART'

    elif query.data == 'main_menu':
        return start(update, context)

    elif query.data == 'back':
        products_names = dispatcher.bot_data['products_names']
        send_products_keyboard(update, context, products_names)
        return "DESCRIPTION"

    else:
        keyboard = [[InlineKeyboardButton("Назад", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        product_id = query.data
        access_token = env.str("ACCESS_TOKEN_BEARER")
        product_params = get_product_params(access_token, product_id)
        if product_params['errors'][0]['status'] == 401:
            access_token = get_token()
            product_params = get_product_params(access_token, product_id)

        # pprint(product_params)

        product_name = product_params['data']['attributes']['name']
        product_description = product_params['data']['attributes']['description']
        product_sku = product_params['data']['attributes']['sku']

        price_id = '5740a00e-5988-45f7-924a-c70f7697d8d4'
        product_prices = get_product_prices(access_token, price_id)
        for price in product_prices['data']:
            if price['attributes']['sku'] == product_sku:
                product_price = float(price['attributes']['currencies']['USD']['amount'])/100

        # print(product_price)

        product_message = dedent(f"""\
                        <b>Вы выбрали продукт:</b>
                        {product_name}
                        <b>Описание:</b>
                        {product_description}
                        <b>Цена в за единицу товара:</b>
                        {product_price}$
                        """).replace("    ", "")
        try:
            product_file_id = product_params['data']['relationships']['main_image']['data']['id']
            product_image_params = get_product_files(access_token,
                                                     file_id=product_file_id)
            product_image_url = product_image_params['data']['link']['href']
            product_image = requests.get(product_image_url)

            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
            query.message.reply_photo(
                product_image.content,
                caption=product_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML)
            return "PRODUCT"

        except:
            context.bot.edit_message_text(
                text=product_message,
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML)
            return "PRODUCT"


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
        'MAIN_MENU': button,
        'STORE': button,
        "PRODUCT": button,
        'CART': button,
        "DESCRIPTION": button,
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
    env = environs.Env()
    env.read_env()
    access_token = env.str("ACCESS_TOKEN_BEARER")
    products_params = get_products_params(access_token)
    if products_params['errors'][0]['status'] == 401:
        access_token = get_token()
        products_params = get_products_params(access_token)

    products_names = get_products_names(products_params)

    token = env.str("TG_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher

    dispatcher.bot_data['products_names'] = products_names

    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))


    updater.start_polling()
    updater.idle()
