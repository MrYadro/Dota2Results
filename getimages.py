import json, requests, time, os, config
from PIL import Image


def download_tmp_file(url, filename, timeout=0):
    local_filename = 'tmp/' + filename
    if os.path.isfile(local_filename):
        delta_time = time.time() - os.path.getmtime(local_filename)
        if delta_time > timeout or timeout == 0:
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                print('Downloading ' + filename)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            f.flush()
            else:
                print('Error accessing ' + filename + '. Status code: ' + str(r.status_code))
        else:
            print('Skipping ' + filename)
    else:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(local_filename, 'wb') as f:
                print('Downloading ' + filename)
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
        else:
            print('Error accessing' + filename + '. Status code: ' + str(r.status_code))

    return local_filename

def getleaguelogo():
    download_tmp_file('https://raw.githubusercontent.com/dotabuff/d2vpkr/master/dota/scripts/items/items_game.json', 'items_game.json', 0)
    leagues = requests.get('https://api.steampowered.com/IDOTA2Match_570/GetLeagueListing/v0001/?key=' + config.STEAM_API_KEY + '&language=en_us').json()
    with open('tmp/items_game.json', encoding="utf8") as items_data_file:
        items_data = json.load(items_data_file)
    for league in leagues.get('result').get('leagues'):
        leagueid = league.get('leagueid')
        itemid = league.get('itemdef')
        if itemid and not os.path.isfile('images/leagues/' + str(leagueid) + '.png'):
            url = items_data.get('items_game').get('items').get(str(itemid)).get('image_inventory')
            url = url.split('/')[-1]
            url = 'https://api.steampowered.com/IEconDOTA2_570/GetItemIconPath/v1/?key=' + config.STEAM_API_KEY + '&iconname=' + url
            r = requests.get(url)
            path = r.json().get('result').get('path')
            if path:
                file = 'http://cdn.dota2.com/apps/570/' + path
                download_tmp_file(file, str(leagueid) + '.png', 0)
                if os.name == 'nt':
                    os.replace('tmp/' + str(leagueid) + '.png', 'images/leagues/' + str(leagueid) + '.png')
                else:
                    try:
                        os.rename('tmp/' + str(leagueid) + '.png', 'images/leagues/' + str(leagueid) + '.png')
                    except OSError:
                        print('File not found')


def getheroespics():
    url = 'https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/'
    payload = {'key': config.STEAM_API_KEY, 'language': 'en_us'}
    r = requests.get(url, params=payload)
    for hero in r.json().get('result').get('heroes'):
        heroid = str(hero.get('id'))
        download_tmp_file('http://cdn.dota2.com/apps/dota2/images/heroes/' + hero.get('name')[14:] + '_vert.jpg', heroid + '.jpg', 0)
        if os.name == 'nt':
            os.replace('tmp/' + heroid + '.jpg', 'images/heroes/' + heroid + '.jpg')
        else:
            try:
                os.rename('tmp/' + heroid + '.jpg', 'images/heroes/' + heroid + '.jpg')
            except OSError:
                print('File not found')
                return
        #results
        logo_image = Image.open('images/heroes/' + heroid + '.jpg')
        logo_image.thumbnail((35, 41), Image.ANTIALIAS)
        logo_image.save('images/heroes/' + heroid + '.png', "PNG")
        #pick
        logo_image = Image.open('images/heroes/' + heroid + '.jpg')
        logo_image.thumbnail((48, 56), Image.ANTIALIAS)
        logo_image.save('images/heroes/' + heroid + '_pick.png', "PNG")


getheroespics()
getleaguelogo()
