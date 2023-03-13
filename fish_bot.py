import argparse
from textwrap import dedent

import environs
import redis
import requests
from more_itertools import chunked
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)

from moltin import (check_token, get_token, get_product_params,
                    get_products_prices, get_product_files, create_client,
                    get_products_names, get_products_params)


_database = None


def start(update, context):
    if not update.callback_query:
        context.user_data['tg_id'] = update.message.from_user.id

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


def send_products_keyboard(update, context):
    query = update.callback_query
    products_names = dispatcher.bot_data['products_names']
    keyboard = list(chunked(products_names, 2))
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        context.bot.edit_message_text(
            text='Выбери товар из магазина:',
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup
        )
        return "PRODUCT"
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
        return "PRODUCT"


def send_product_description(update, context):
    query = update.callback_query
    if query.data == 'main_menu':
        return start(update, context)

    keyboard = [[InlineKeyboardButton("1кг", callback_data='1kg'),
                 InlineKeyboardButton("5кг", callback_data='5kg'),
                 InlineKeyboardButton("10кг", callback_data='10kg')],
                [InlineKeyboardButton("Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    product_id = query.data
    context.user_data['product_id'] = product_id

    access_token = context.user_data['access_token']
    product_params = get_product_params(access_token, product_id)
    product_name = product_params['data']['attributes']['name']
    product_description = product_params['data']['attributes']['description']
    product_sku = product_params['data']['attributes']['sku']

    context.user_data['product_name'] = product_name

    products_prices = dispatcher.bot_data['products_prices']
    for price in products_prices['data']:
        if price['attributes']['sku'] == product_sku:
            product_price = "%.2f" % (price['attributes']['currencies']['USD']['amount']/100)

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
        access_token = context.user_data['access_token']
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
        return "ADD_CART"

    except:
        context.bot.edit_message_text(
            text=product_message,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML)
        return "ADD_CART"


def add_product_to_cart(update, context):
    query = update.callback_query
    if query.data == 'back':
        return send_products_keyboard(update, context)

    tg_id = context.user_data['tg_id']
    access_token = context.user_data['access_token']
    product_id = context.user_data['product_id']
    product_quantity = int(query.data.replace('kg', ''))

    keyboard = [[InlineKeyboardButton("Назад", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    json_data = {
        'data': {
            'type': 'cart_item',
            'id': product_id,
            "quantity": product_quantity,
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/carts/{tg_id}/items',
                             headers=headers,
                             json=json_data)

    if response.ok:
        product_name = context.user_data['product_name']
        add_cart_message = dedent(
            f"""\
            <b>Выбранный вами продукт:</b>
            {product_name}
             <b>В количестве:</b>
            {product_quantity}кг
            <b>Успешно добавлен в вашу корзину</b>
            """).replace("    ", "")
        try:
            context.bot.edit_message_text(
                text=add_cart_message,
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return "STORE"
        except:
            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
            context.bot.send_message(
                text=add_cart_message,
                chat_id=query.message.chat_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return "STORE"


def show_cart(update, context):
    query = update.callback_query

    tg_id = context.user_data['tg_id']
    access_token = context.user_data['access_token']

    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/v2/carts/{tg_id}/items',
                            headers=headers)
    products_in_cart_params = response.json()

    products_in_cart_list = [
        f'{count + 1}. {product["name"]}\n'\
        f'ЦЕНА ЗА ЕДИНИЦУ: {"%.2f" % (product["unit_price"]["amount"]/100)} {product["unit_price"]["currency"]} \n'\
        f'КОЛИЧЕСТВО: {product["quantity"]} кг \n'\
        f'СУММА: {"%.2f" % (product["value"]["amount"]/100)} {product["value"]["currency"]}\n\n'
        for count, product in enumerate(products_in_cart_params['data'])
    ]

    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{tg_id}',
                            headers=headers)
    cart_params = response.json()
    cart_sum = f'ИТОГО {cart_params["data"]["meta"]["display_price"]["with_tax"]["formatted"]}'
    context.user_data['cart_sum'] = cart_sum
    products_in_cart_list.append(cart_sum)

    products_in_cart = ' '.join(products_in_cart_list)

    keyboard = [
        [InlineKeyboardButton("Оплатить", callback_data='paiment')],
        [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
    ]
    for product in products_in_cart_params['data']:
        button_name = f'Убрать из корзины {product["name"]}'
        button_id = product['id']
        button = [InlineKeyboardButton(button_name,
                                       callback_data=f'delete {button_id}')]
        keyboard.insert(0, button)
    reply_markup = InlineKeyboardMarkup(keyboard)


    context.bot.edit_message_text(
        text=products_in_cart,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup)
    return 'CART'


def delete_product_from_cart(update, context):
    product_id = context.user_data['delete_product_id']
    access_token = context.user_data['access_token']
    tg_id = context.user_data['tg_id']

    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    requests.delete(f'https://api.moltin.com/v2/carts/{tg_id}/items/{product_id}',
                    headers=headers)

    return show_cart(update, context)


def ask_email(update, context):
    query = update.callback_query
    cart_sum = context.user_data['cart_sum']
    paiment_message = f'Сумма заказа составляет {cart_sum}\n'\
                      f'Напишите ваш емейл. ' \
                      f'С вами свяжется наш специалист для уточнения вопроса оплаты'

    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        text=paiment_message,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup)
    return 'GET_EMAIL'


def get_email(update, context):
    query = update.callback_query
    if query and query.data == 'back_to_cart':
        return show_cart(update, context)

    access_token = context.user_data['access_token']

    email = update.message.text
    keyboard = [[InlineKeyboardButton("Назад к корзине",
                                      callback_data='back_to_cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user_fullname = str(update.message.from_user['first_name']) + ' ' + str(
        update.message.from_user['last_name'])
    response = create_client(
        access_token=access_token,
        client_name=user_fullname,
        email=email
    )
    if response.ok:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Вы нам прислали {email}\n'
                 f'В ближайшее время с вами свяжется наш специалист',
            reply_markup=reply_markup
        )
        return 'CART'
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Вы ввели некорректный e-mail, попробуйте еще раз',
            reply_markup=reply_markup
        )


def button(update, context):
    query = update.callback_query

    if query.data == 'store':
        return send_products_keyboard(update, context)

    elif query.data == 'cart':
        return show_cart(update, context)

    elif query.data == 'main_menu':
        return start(update, context)

    elif query.data == 'back_to_cart':
        return show_cart(update, context)

    elif 'delete' in query.data:
        product_id = query.data.replace('delete ', '')
        context.user_data['delete_product_id'] = product_id
        return delete_product_from_cart(update, context)

    elif 'paiment' in query.data:
        return ask_email(update, context)


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
        access_token = get_token()
        context.user_data['access_token'] = access_token
    else:
        user_state = db.get(chat_id)

    access_token = context.user_data['access_token']
    check = check_token(access_token)
    if not check.ok:
        access_token = get_token()
        context.user_data['access_token'] = access_token

    states_functions = {
        'START': start,
        'MAIN_MENU': button,
        'STORE': send_products_keyboard,
        "PRODUCT": send_product_description,
        'CART': button,
        "ADD_CART": add_product_to_cart,
        'GET_EMAIL': get_email,
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'price_list_id',
        type=str,
        help='ИД прайс листа в elasticpath',
    )
    args = parser.parse_args()

    env = environs.Env()
    env.read_env()

    access_token = env.str("ACCESS_TOKEN_BEARER")
    check = check_token(access_token)
    if not check.ok:
        access_token = get_token()

    token = env.str("TG_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher

    products_params = get_products_params(access_token)
    products_names = get_products_names(products_params)
    dispatcher.bot_data['products_names'] = products_names

    dispatcher.bot_data['products_prices'] = get_products_prices(access_token,
                                                                 price_list_id=args.price_list_id)

    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()
