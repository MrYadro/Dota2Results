import config
import requests
import os
import sys
import time
import json
import shutil
from PIL import Image, ImageFont, ImageDraw, ImageFilter
import sqlite3

LEAGUE_LIST_URL = 'https://api.steampowered.com/IDOTA2Match_570/GetLeagueListing/v0001/'
LIVE_LEAGUE_MATCH_LIST = 'https://api.steampowered.com/IDOTA2Match_570/GetLiveLeagueGames/v0001/'
MATCH_DETAILS = 'https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v001/'
TEAM_LOGO = 'http://api.steampowered.com/ISteamRemoteStorage/GetUGCFileDetails/v1/'
TEAM_INFO = 'https://api.steampowered.com/IDOTA2Match_570/GetTeamInfoByTeamID/v001/'


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


def compare_live_games(previous, current):

    skip = [4325,4649]

    with open(previous, encoding="utf8") as data_file:
        prev_data = json.load(data_file)

    with open(current, encoding="utf8") as data_file:
        cur_data = json.load(data_file)

    prev_list = []
    cur_list = []

    for item in prev_data['result']['games']:
        if item['league_tier'] == 3 and item['league_id'] not in skip:
            prev_list.append(item['match_id'])

    for item in cur_data['result']['games']:
        if item['league_tier'] == 3 and item['league_id'] not in skip:
            cur_list.append(item['match_id'])

    return set(prev_list).difference(cur_list)


def cur_live_games(current):

    with open(current, encoding="utf8") as data_file:
        cur_data = json.load(data_file)

    cur_list = []

    for item in cur_data['result']['games']:
        if item['league_tier'] == 3:
            cur_list.append(item['match_id'])

    return cur_list


def get_match_data(match_id):

    dire_name = ''
    radiant_name = ''
    dire_vk_group = 'rsltdtk_team'
    radiant_vk_group = 'rsltdtk_team'
    seconds = 0
    dire_score = 0
    radiant_score = 0
    dire_heroes = []
    radiant_heroes = []
    league_name = ''
    league_id = 0
    radiant_win = 0
    league_vk_group = 'rsltdtk_league'
    series_type = 0
    radiant_series_wins = 0
    dire_series_wins = 0
    radiant_logo = 0
    dire_logo = 0
    league_hashtag = ''
    players = []

    download_tmp_file(MATCH_DETAILS + '?key=' + config.STEAM_API_KEY + '&match_id=' + str(match_id), str(match_id) + '.json', 0)

    with open('tmp/' + str(match_id) + '.json', encoding="utf8") as match_data_file:
        match_data = json.load(match_data_file)

    with open('cur_live_games.json', encoding="utf8") as data_file:
        cur_matches_data = json.load(data_file)

    for cur_match in cur_matches_data['result']['games']:
        if cur_match['match_id'] == match_id:
            series_type = cur_match['series_type']
            radiant_series_wins = cur_match['radiant_series_wins']
            dire_series_wins = cur_match['dire_series_wins']
            for player in cur_match['players']:
                players.append((player['account_id'], player['name']))

    if not match_data['result'].get('error'):
        if match_data['result'].get('dire_name'):
            dire_name = match_data['result']['dire_name']
            if len(dire_name) > 18:
                        dire_name = getteamtag(match_data['result']['dire_team_id'])
            dire_vk_group = team_to_vk_group(match_data['result']['dire_team_id'])
        else:
            dire_name = 'Dire'
        if match_data['result'].get('radiant_name'):
            radiant_name = match_data['result']['radiant_name']
            if len(radiant_name) > 18:
                        radiant_name = getteamtag(match_data['result']['radiant_team_id'])
            radiant_vk_group = team_to_vk_group(match_data['result']['radiant_team_id'])
        else:
            radiant_name = 'Radiant'

        radiant_logo = match_data['result'].get('radiant_logo')
        dire_logo = match_data['result'].get('dire_logo')

        seconds = match_data['result']['duration']
        radiant_win = match_data['result']['radiant_win']
        league_vk_group = league_to_vk_group(match_data['result']['leagueid'])
        league_hashtag = get_hashtag(match_data['result']['leagueid'])

        for player in match_data['result']['players']:
            if player['player_slot'] > 99:
                radiant_score += player['deaths']
                dire_heroes.append((player['hero_id'], player['kills'], player['deaths'], player['assists'], player['account_id']))
            else:
                dire_score += player['deaths']
                radiant_heroes.append((player['hero_id'], player['kills'], player['deaths'], player['assists'], player['account_id']))

        with open('tmp/league_list.json', encoding="utf8") as league_data_file:
            league_data = json.load(league_data_file)
        for league in league_data['result']['leagues']:
            if league['leagueid'] == match_data['result']['leagueid']:
                league_name = league['name']

        league_id = match_data['result']['leagueid']

    os.remove('tmp/' + str(match_id) + '.json')

    return match_id, radiant_heroes, dire_heroes, radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, league_name, dire_vk_group, radiant_vk_group, league_vk_group, series_type, radiant_series_wins, dire_series_wins, radiant_logo, dire_logo, league_hashtag, players, league_id


def team_to_vk_group(team_id):
    with open('assets/team_vk_group.json', encoding="utf8") as team_group_file:
        team_group = json.load(team_group_file)
    group_id = team_group.get(str(team_id))
    if group_id:
        return group_id
    else:
        return 'rsltdtk_team'


def league_to_vk_group(leagueid):
    with open('assets/league_vk_group.json', encoding="utf8") as league_group_file:
        league_group = json.load(league_group_file)
    group_id = league_group.get(str(leagueid))
    if group_id:
        return group_id
    else:
        return 'rsltdtk_league'


def get_hashtag(leagueid):
    hashtag = '#results@rsltdtk #dota2'
    with open('assets/league_hasttag.json', encoding="utf8") as league_group_file:
        league_group = json.load(league_group_file)
    extra = league_group.get(str(leagueid))
    if extra:
        return hashtag + ' ' + extra
    else:
        return hashtag


def create_message(radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, league_name, dire_vk_group, radiant_vk_group, league_vk_group, series_type, radiant_series_wins, dire_series_wins, hashtag):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    timer = '%d:%02d:%02d' % (h, m, s)
    if radiant_win:
        out_string = series_text_maker(series_type, radiant_series_wins + 1, 'radiant') + ' [[' + str(radiant_vk_group) + '|' + str(radiant_name) + ']]' + ' ' + str(radiant_score) + ' - ' + str(dire_score) + ' ' + '[' + str(dire_vk_group) + '|' + str(dire_name) + '] ' + series_text_maker(series_type, dire_series_wins, 'dire') + '\n' + timer + ' @ ' + '[' + str(league_vk_group) + '|' + str(league_name) + ']' + '\n' + hashtag
    else:
        out_string = series_text_maker(series_type, radiant_series_wins, 'radiant') + ' [' + str(radiant_vk_group) + '|' + str(radiant_name) + ']' + ' ' + str(radiant_score) + ' - ' + str(dire_score) + ' ' + '[[' + str(dire_vk_group) + '|' + str(dire_name) + ']] ' + series_text_maker(series_type, dire_series_wins + 1, 'dire') + '\n' + timer + ' @ ' + '[' + str(league_vk_group) + '|' + str(league_name) + ']' + '\n' + hashtag
    return out_string


def series_text_maker(series_type, score, side):
    if series_type == 0:
        text = '⬜'
    if series_type == 1:
        text = '⬜⬜'
    if series_type == 2:
        text = '⬜⬜⬜'
    for i in range(0, score):
        text = text[:i] + '⬛' + text[i+1:]
    if side == 'radiant':
        return text[::-1]
    else:
        return text


def get_team_logo(logo):
    download_tmp_file(TEAM_LOGO + '?key=' + config.STEAM_API_KEY + '&appid=570' + '&ugcid=' + str(logo), str(logo) + '.json', 3600)

    try:
        with open('tmp/' + str(logo) + '.json', encoding="utf8") as logo_data_file:
            logo_data = json.load(logo_data_file)
    except FileNotFoundError:
        print('File not found')
        return
    except OSError:
        print('File not found')
        return

    download_tmp_file(logo_data['data']['url'], str(logo) + '.png', 0)
    if os.name == 'nt':
        os.replace('tmp/' + str(logo) + '.png', 'images/teams/' + str(logo) + '.png')
    else:
        try:
            os.rename('tmp/' + str(logo) + '.png', 'images/teams/' + str(logo) + '.png')
        except OSError:
            print('File not found')
            return
    logo_image = Image.open('images/teams/' + str(logo) + '.png')
    logo_image.thumbnail((35, 21), Image.ANTIALIAS)
    logo_image.save('images/teams/' + str(logo) + '.png', "PNG")


def create_picture(filename, radiant_heroes, dire_heroes, radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, series_type, radiant_series_wins, dire_series_wins, radiant_logo, dire_logo, league_name, players, league_id):

    imageh = 340
    imagew = 537
    clrwhite = '#FDFDFD'
    clrlghtgray = '#6D8483'
    btfclockgr = '#a7fc83'
    btfclockrd = '#F9483E'

    leaguename = league_name
    radteamname = radiant_name
    direteamname = dire_name

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    time = '%d:%02d:%02d' % (h, m, s)
    radscore = str(radiant_score)
    dirscore = str(dire_score)

    get_team_logo(radiant_logo)
    get_team_logo(dire_logo)

    img = Image.new('RGBA', (imagew, imageh), (0, 0, 0, 255))

    largefont = ImageFont.truetype("assets/mainfont.ttf", 30)
    victoryfont = ImageFont.truetype("assets/victoryfont.ttf", 30)
    #victoryfont = ImageFont.truetype("assets/btf.ttf", 30)
    smallfont = ImageFont.truetype("assets/mainfont.ttf", 17)
    btfsmallfont = ImageFont.truetype("assets/btf.ttf", 17)
    namefontcn = ImageFont.truetype("assets/namefontcn.otf", 17)
    namefont = ImageFont.truetype("assets/namefont.ttf", 17)

    if radiant_win:
        radiant_series_wins += 1
    else:
        dire_series_wins += 1

    if radiant_series_wins > series_type + 1:
        radiant_series_wins -= 1

    if dire_series_wins > series_type + 1:
        dire_series_wins -= 1

    radiant_score_image = Image.open('images/series/' + str(series_type) + '/' + str(radiant_series_wins) + '.png')
    dire_score_image = Image.open('images/series/' + str(series_type) + '/' + str(dire_series_wins) + '.png')
    radiant_score_image = radiant_score_image.transpose(Image.FLIP_LEFT_RIGHT)

    try:
        leagueimage = Image.open('images/leagues/' + str(league_id) + '.png')
    except FileNotFoundError:
        leagueimage = Image.open('images/leagues/noleague.png')

    overlay = Image.open('images/overlay.png')

    leagueimage = leagueimage.resize((537, 356))
    leagueimage = leagueimage.crop((0, 8, 537, 348))
    leagueimage = leagueimage.convert('RGB')
    leagueimage = leagueimage.filter(ImageFilter.GaussianBlur(radius=4))

    leagueimage.paste(overlay, mask=overlay.split()[3])

    img.paste(leagueimage)

    teamw = 240
    teamh = 300

    radteam = Image.new('RGBA', (teamw, teamh))
    radteamheader = Image.new('RGBA', (teamw, 41))

    num = 1

    # DIRE HEROES

    for herodata in radiant_heroes:
        heroid = herodata[0]
        radhero = Image.new('RGBA', (teamw, 41))
        hero = getheroname(heroid)
        heroimage = Image.open('images/heroes/' + str(heroid) + '.png')
        radhero.paste(heroimage, (0, 0))

        player = getplayername(herodata[4], players)

        if 'zh' in getlanguage(player):
            ImageDraw.Draw(radhero).text((45, -3), player, font=namefontcn, fill=clrwhite)
        else:
            ImageDraw.Draw(radhero).text((45, -3), player, font=namefont, fill=clrwhite)

        ImageDraw.Draw(radhero).text((45, 22), hero, font=smallfont, fill=clrlghtgray)

        heroscore = str(herodata[1]) + '/' + str(herodata[2]) + '/' + str(herodata[3])
        w, h = ImageDraw.Draw(radhero).textsize(heroscore, font=smallfont)

        ImageDraw.Draw(radhero).text((teamw - w, 21), heroscore, font=smallfont, fill=clrlghtgray)
        radteam.paste(radhero, (0, 45 * num), mask=radhero.split()[3])
        num += 1

    # RADIANT HEADER

    try:
        radteamimage = Image.open('images/teams/' + str(radiant_logo) + '.png')
    except FileNotFoundError:
        radteamimage = Image.open('images/teams/nologo.png')
    radteamheader.paste(radteamimage, (0, 0))
    radteamheader.paste(radiant_score_image, (23 - 13, 22), mask=radiant_score_image.split()[3])
    ImageDraw.Draw(radteamheader).text((45, 5), radteamname.upper(), font=smallfont, fill=clrlghtgray)

    w, h = ImageDraw.Draw(radteamheader).textsize(radscore, font=largefont)
    ImageDraw.Draw(radteamheader).text((teamw - w, 22 - h), radscore, font=largefont, fill=clrwhite)

    dirteam = Image.new('RGBA', (teamw, teamh))
    dirteamheader = Image.new('RGBA', (teamw, 41))

    num = 1

    for herodata in dire_heroes:
        heroid = herodata[0]
        dirhero = Image.new('RGBA', (teamw, 41))
        hero = getheroname(heroid)
        heroimage = Image.open('images/heroes/' + str(heroid) + '.png')
        dirhero.paste(heroimage, (teamw - 35, 0))

        player = getplayername(herodata[4], players)

        if 'zh' in getlanguage(player):
            w, h = ImageDraw.Draw(dirhero).textsize(player, font=namefontcn)
            ImageDraw.Draw(dirhero).text((teamw - w - 45, -3), player, font=namefontcn, fill=clrwhite)
        else:
            w, h = ImageDraw.Draw(dirhero).textsize(player, font=namefont)
            ImageDraw.Draw(dirhero).text((teamw - w - 45, -3), player, font=namefont, fill=clrwhite)

        w, h = ImageDraw.Draw(dirhero).textsize(hero, font=smallfont)
        ImageDraw.Draw(dirhero).text((teamw - w - 45, 22), hero, font=smallfont, fill=clrlghtgray)

        heroscore = str(herodata[1]) + '/' + str(herodata[2]) + '/' + str(herodata[3])
        w, h = ImageDraw.Draw(dirhero).textsize(heroscore, font=smallfont)
        ImageDraw.Draw(dirhero).text((0, 21), heroscore, font=smallfont, fill=clrlghtgray)
        dirteam.paste(dirhero, (0, 45 * num), mask=dirhero.split()[3])
        num += 1

    # DIRE HEADER

    try:
        dirteamimage = Image.open('images/teams/' + str(dire_logo) + '.png')
    except FileNotFoundError:
        dirteamimage = Image.open('images/teams/nologo.png')

    dirteamheader.paste(dirteamimage, (teamw - 35, 0))
    dirteamheader.paste(dire_score_image, (teamw - 26, 22), mask=dire_score_image.split()[3])

    w, h = ImageDraw.Draw(dirteamheader).textsize(direteamname.upper(), font=smallfont)
    ImageDraw.Draw(dirteamheader).text((teamw - w - 45, 5), direteamname.upper(), font=smallfont, fill=clrlghtgray)

    w, h = ImageDraw.Draw(dirteamheader).textsize(dirscore, font=largefont)
    ImageDraw.Draw(dirteamheader).text((0, 22 - h), dirscore, font=largefont, fill=clrwhite)

    radteam.paste(radteamheader, (0, 0), mask=radteamheader.split()[3])
    dirteam.paste(dirteamheader, (0, 0), mask=dirteamheader.split()[3])

    img.paste(radteam, (10, 64), mask=radteam.split()[3])
    img.paste(dirteam, (imagew - teamw - 10, 64), mask=dirteam.split()[3])

    # LEAGUENAME SCORE

    w, h = ImageDraw.Draw(img).textsize(time, font=smallfont)
    ImageDraw.Draw(img).text((imagew - w - 10, 10), time, font=smallfont, fill=clrwhite)

    # w, h = ImageDraw.Draw(img).textsize(time, font=btfsmallfont)
    # ImageDraw.Draw(img).text((imagew - w - 10, 10), time, font=btfsmallfont, fill=btfclockgr)

    ImageDraw.Draw(img).text((10, 10), leaguename.upper(), font=smallfont, fill=clrwhite)

    # ImageDraw.Draw(img).text((10, 10), leaguename.upper(), font=btfsmallfont, fill=btfclockgr)

    # TEAM VICTORY

    if radiant_win:
        victorytext = radiant_name.upper() + ' VICTORY'
    else:
        victorytext = dire_name.upper() + ' VICTORY'

    w, h = ImageDraw.Draw(img).textsize(victorytext, font=victoryfont)
    ImageDraw.Draw(img).text((((imagew - w)/2), 33), victorytext, font=victoryfont, fill=clrwhite)

    # w, h = ImageDraw.Draw(img).textsize(victorytext, font=victoryfont)
    # ImageDraw.Draw(img).text((((imagew - w)/2), 33), victorytext, font=victoryfont, fill=btfclockrd)

    img.save('tmp/' + str(filename) + '.png', "PNG")

    return 'tmp/' + str(filename) + '.png'


def getlanguage(string):
    url = 'http://ws.detectlanguage.com/0.2/detect'
    payload = {'key': config.DET_LANG_KEY, 'q': string}
    r = requests.get(url, params=payload)
    try:
        lang = r.json().get('data').get('detections')[0].get('language')
    except IndexError:
        lang = 'en'
    return lang


def getteamtag(team):
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetTeamInfoByTeamID/v001/'
    payload = {'key': config.STEAM_API_KEY, 'start_at_team_id': team}
    r = requests.get(url, params=payload)
    tag = r.json().get('result').get('teams')[0].get('tag')
    return tag


def getplayername(steamid, players):
    if not players:
        return getsteamname(steamid)
    for player in players:
        if player[0] == steamid:
            name = player[1]
            if name:
                return name
            else:
                return getsteamname(steamid)


def getsteamname(steamid):
    id64 = steamid + 76561197960265728
    url = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
    payload = {'key': config.STEAM_API_KEY, 'steamids': id64}
    r = requests.get(url, params=payload)
    name = r.json().get('response').get('players')[0].get('personaname')
    if name:
        return name
    else:
        return 'Player'


def getheroname(heroid):
    with open('tmp/heroes.json', encoding="utf8") as heroes_data_file:
        hero_data = json.load(heroes_data_file)
    for hero in hero_data.get('result').get('heroes'):
        if hero.get('id') == heroid:
            return hero.get('localized_name')


def vk_post(msg, pic, match_id):
    # conn = sqlite3.connect('data.db')
    # c = conn.cursor()

    url = 'https://api.vk.com/method/'
    payload = {'group_id': config.VK_GROUP_ID, 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'photos.getWallUploadServer', params=payload)
#    print(r.json())
    upload_url = r.json()['response']['upload_url']
    picture_to_upload = {'photo': open(pic, 'rb')}
    r = requests.post(upload_url, files=picture_to_upload)
    server = r.json()['server']
    photo = r.json()['photo']
    photo_hash = r.json()['hash']
    payload = {'group_id': config.VK_GROUP_ID, 'photo': photo, 'server': server, 'hash': photo_hash, 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'photos.saveWallPhoto', params=payload)
    photo_id = r.json()['response'][0]['id']
    payload = {'owner_id': config.VK_GROUP_NEGID, 'from_group': 1, 'message': msg, 'attachments': photo_id + ',https://yasp.co/matches/' + str(match_id), 'access_token': config.VK_API_KEY}
    # c.execute('select result from issend where match_id={0}'.format(match_id))
    # issend = c.fetchone()
    # if not issend:
    r = requests.get(url + 'wall.post', params=payload)
    # c.execute('update issend set result = 1 where match_id = {0}'.format(match_id))
    # conn.commit()
    # conn.close()

    # print(r.text)

complete_matches = []

try:
    download_tmp_file('https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/?key=' + config.STEAM_API_KEY + '&language=en_us', 'heroes.json', 3600)
    download_tmp_file(LEAGUE_LIST_URL + '?key=' + config.STEAM_API_KEY + '&language=en_us', 'league_list.json', 3600)
    download_tmp_file(LIVE_LEAGUE_MATCH_LIST + '?key=' + config.STEAM_API_KEY, 'live_games.json', 0)
    download_tmp_file('https://raw.githubusercontent.com/dotabuff/d2vpkr/master/dota/scripts/items/items_game.json', 'items_game.json', 3600)

except ConnectionError:
    print('Connection Error')

else:
    if not os.path.isfile('cur_live_games.json'):
        shutil.copy('tmp/live_games.json', 'cur_live_games.json')

    if len(sys.argv) == 1:
        complete_matches = compare_live_games('cur_live_games.json', 'tmp/live_games.json')

    else:
        for elem in sys.argv[1:]:
            complete_matches.append(elem)

    # complete_matches = [1825135893]
    complete_matches = list(set(complete_matches))

    for match_id in complete_matches:
        match_id, radiant_heroes, dire_heroes, radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, league_name, dire_vk_group, radiant_vk_group, league_vk_group, series_type, radiant_series_wins, dire_series_wins, radiant_logo, dire_logo, hashtag, players, league_id = get_match_data(match_id)
        if not (seconds == 0):
            try:
                msg = create_message(radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, league_name, dire_vk_group, radiant_vk_group, league_vk_group, series_type, radiant_series_wins, dire_series_wins, hashtag)
                picture = create_picture(match_id, radiant_heroes, dire_heroes, radiant_name, dire_name, seconds, radiant_win, radiant_score, dire_score, series_type, radiant_series_wins, dire_series_wins, radiant_logo, dire_logo, league_name, players, league_id)
            except UnboundLocalError:
                print('Error!')
            else:
                if os.name == 'nt':
                    print('Done!')
                else:
#                    print(msg)
                    vk_post(msg, picture, match_id)
                    os.remove(picture)

    if len(sys.argv) == 1:
        try:
            os.rename('cur_live_games.json', 'cur_live_games_tmp.json')
        except IOError:
            print('IO error')
        else:
            try:
                os.rename('tmp/live_games.json', 'cur_live_games.json')
            except IOError:
                print('IO error')
                os.rename('cur_live_games_tmp.json', 'cur_live_games.json')
                os.remove('cur_live_games_tmp.json')
            else:
                os.remove('cur_live_games_tmp.json')
