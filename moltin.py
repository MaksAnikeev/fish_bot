import environs
import requests
from telegram import InlineKeyboardButton


env = environs.Env()
env.read_env()

def check_token(access_token):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get('https://api.moltin.com/pcm/products',
                            headers=headers)
    return response


def get_token():
    client_id = env.str("CLIENT_ID")
    client_secret = env.str("CLIENT_SECRET")

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post('https://api.moltin.com/oauth/access_token',
                             data=data)
    response.raise_for_status()
    access_token = response.json()['access_token']
    return access_token


def get_products_params(access_token):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get('https://api.moltin.com/pcm/products',
                            headers=headers)
    response.raise_for_status()
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
    response.raise_for_status()
    return response.json()


def get_products_prices(access_token, price_list_id):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/pcm/pricebooks/{price_list_id}/prices',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_files(access_token, file_id):
    headers = {
            'Authorization': f'Bearer {access_token}',
        }
    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def create_client(access_token, client_name, email):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': client_name,
            'email': email,
        },
    }
    response = requests.post('https://api.moltin.com/v2/customers',
                             headers=headers,
                             json=json_data)
    response.raise_for_status()
    return response


def get_products_names(products_params):
    keyboard_products = [InlineKeyboardButton("Главное меню",
                                              callback_data='main_menu')]
    for product in products_params['data']:
        button_name = product['attributes']['name']
        button_id = product['id']
        button = InlineKeyboardButton(button_name, callback_data=button_id)
        keyboard_products.insert(0, button)
    return keyboard_products
