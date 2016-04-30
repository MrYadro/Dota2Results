import config
import requests
import json
from PIL import Image, ImageFont, ImageDraw, ImageFilter
import time
import os
import sqlite3

TEAM_LOGO = 'http://api.steampowered.com/ISteamRemoteStorage/GetUGCFileDetails/v1/'


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


def getheroname(heroid):
    with open('tmp/heroes.json', encoding="utf8") as heroes_data_file:
        hero_data = json.load(heroes_data_file)
    for hero in hero_data.get('result').get('heroes'):
        if hero.get('id') == heroid:
            return hero.get('localized_name')


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


def get_hashtag(leagueid):
    hashtag = '#picks@rsltdtk #dota2'
    with open('assets/league_hasttag.json', encoding="utf8") as league_group_file:
        league_group = json.load(league_group_file)
    extra = league_group.get(str(leagueid))
    if extra:
        return hashtag + ' ' + extra
    else:
        return hashtag


def makemessage(series, radwins, dirwins, radname, dirname, radgroup, dirgroup, leaguename, leaguegroup, leagueid):
    radteamtext = series_text_maker(series, radwins, 'radiant') + ' [' + radgroup + '|' + radname + ']'
    dirteamtext = '[' + dirgroup + '|' + dirname + '] ' + series_text_maker(series, dirwins, 'dire')
    if series == 0:
        sertext = 'bo1'
    if series == 1:
        sertext = 'bo3'
    if series == 2:
        sertext = 'bo5'
    leaguetext = '[' + leaguegroup + '|' + leaguename + ']'
    result = radteamtext + ' - ' + dirteamtext + '\n' + sertext + ' @ ' + leaguetext + '\n' + get_hashtag(leagueid)
    print(result)
    return result


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


def getteamtag(team):
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetTeamInfoByTeamID/v001/'
    payload = {'key': config.STEAM_API_KEY, 'start_at_team_id': team}
    r = requests.get(url, params=payload)
    tag = r.json().get('result').get('teams')[0].get('tag')
    return tag


def getmatchesdata():
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetLiveLeagueGames/v0001/'
    radpick = []
    radban = []
    dirpick = []
    dirban = []
    leagueid = 0
    radteamid = 0
    dirteamid = 0

    skip = []

    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    r = requests.get(url,
                     params={'key': config.STEAM_API_KEY}
                     )
    data = r.json().get('result').get('games')
    for match in data:
        tier = match.get('league_tier')
        leagueid = match.get('league_id')
        if tier == 3 and leagueid not in skip:
            matchid = match.get('match_id')
            c.execute('select pickban from issend where match_id={0}'.format(matchid))
            issend = c.fetchone()
            try:
                timer = int(match.get('scoreboard').get('duration'))
            except AttributeError:
                print('Time is not set')
            else:
                if timer > 0 and not issend:
                    rpjson = match.get('scoreboard').get('radiant').get('picks')
                    rbjson = match.get('scoreboard').get('radiant').get('bans')
                    dpjson = match.get('scoreboard').get('dire').get('picks')
                    dbjson = match.get('scoreboard').get('dire').get('bans')
                    if rpjson and rbjson and dpjson and dbjson:
                        for hero in rpjson:
                            radpick.append(hero.get('hero_id'))
                        for hero in rbjson:
                            radban.append(hero.get('hero_id'))
                        for hero in dpjson:
                            dirpick.append(hero.get('hero_id'))
                        for hero in dbjson:
                            dirban.append(hero.get('hero_id'))
                        leagueid = match.get('league_id')
                        radteamname = match.get('radiant_team').get('team_name')
                        dirteamname = match.get('dire_team').get('team_name')
                        radwins = match.get('radiant_series_wins')
                        dirwins = match.get('dire_series_wins')
                        series = match.get('series_type')
                        radlogo = match.get('radiant_team').get('team_logo')
                        dirlogo = match.get('dire_team').get('team_logo')
                        radteamid = match.get('radiant_team').get('team_id')
                        dirteamid = match.get('dire_team').get('team_id')
                        longradteamname = radteamname
                        longdirteamname = dirteamname

                        makeimage(leagueid, radteamname, dirteamname, radwins, dirwins, radlogo, dirlogo, series, radpick, radban, dirpick, dirban, radteamid, dirteamid)
                        leaguevk = league_to_vk_group(leagueid)
                        leaguename = getleaguename(leagueid)
                        if len(radteamname) > 18:
                            radteamname = getteamtag(radteamid)
                        if len(dirteamname) > 18:
                            dirteamname = getteamtag(dirteamid)
                        message = makemessage(series, radwins, dirwins, radteamname, dirteamname, team_to_vk_group(radteamid), team_to_vk_group(dirteamid), leaguename, leaguevk, leagueid)
                        vk_post(longradteamname, longdirteamname, message)
                        c.execute('insert into issend (match_id, pickban) values ({0}, 1)'.format(matchid))
                        conn.commit()
    conn.close()


def getleaguename(leagueid):
    with open('tmp/league_list.json', encoding="utf8") as league_data_file:
        league_data = json.load(league_data_file)
    for league in league_data['result']['leagues']:
        if league['leagueid'] == leagueid:
            league_name = league['name']

    return league_name


def makeimage(leagueid, radteamname, dirteamname, radwins, dirwins, radlogo, dirlogo, series, radpick, radban, dirpick, dirban, radteamid, dirteamid):

    imageh = 340
    imagew = 537
    clrwhite = '#FDFDFD'
    clrlghtgray = '#6D8483'

    img = Image.new('RGBA', (imagew, imageh), (0, 0, 0, 255))

    largefont = ImageFont.truetype("assets/mainfont.ttf", 30)
    victoryfont = ImageFont.truetype("assets/victoryfont.ttf", 30)
    smallfont = ImageFont.truetype("assets/mainfont.ttf", 17)
    namefontcn = ImageFont.truetype("assets/namefontcn.otf", 17)
    namefont = ImageFont.truetype("assets/namefont.ttf", 17)

    radiant_score_image = Image.open('images/series/' + str(series) + '/' + str(radwins) + '.png')
    dire_score_image = Image.open('images/series/' + str(series) + '/' + str(dirwins) + '.png')
    radiant_score_image = radiant_score_image.transpose(Image.FLIP_LEFT_RIGHT)

    try:
        leagueimage = Image.open('images/leagues/' + str(leagueid) + '.png')
    except FileNotFoundError:
        leagueimage = Image.open('images/leagues/noleague.png')

    overlay = Image.open('images/overlay_pick.png')

    leaguename = getleaguename(leagueid)

    leagueimage = leagueimage.resize((537, 356))
    leagueimage = leagueimage.crop((0, 8, 537, 348))
    leagueimage = leagueimage.convert('RGB')
    leagueimage = leagueimage.filter(ImageFilter.GaussianBlur(radius=4))

    leagueimage.paste(overlay, mask=overlay.split()[3])

    img.paste(leagueimage)

    radiant_score_image = Image.open('images/series/' + str(series) + '/' + str(radwins) + '.png')
    dire_score_image = Image.open('images/series/' + str(series) + '/' + str(dirwins) + '.png')
    radiant_score_image = radiant_score_image.transpose(Image.FLIP_LEFT_RIGHT)

    teamw = 240
    teamh = 150

    radteam = Image.new('RGBA', (teamw, teamh))

    # RADIANT HEROES

    num = 0

    for heroid in radpick:
        pickimage = Image.open('images/heroes/' + str(heroid) + '_pick.png')
        radteam.paste(pickimage, (48 * num, 6))
        num += 1

    num = 0

    for heroid in radban:
        banimage = Image.open('images/heroes/' + str(heroid) + '.png')
        radteam.paste(banimage, (32 + 35 * num, 64))
        num += 1

    w, h = ImageDraw.Draw(radteam).textsize(radteamname, font=smallfont)
    ImageDraw.Draw(radteam).text((((teamw - w)/2), 110), radteamname, font=smallfont, fill=clrwhite)

    radteam.paste(radiant_score_image, (int((teamw - 16)/2), 0), mask=radiant_score_image.split()[3])

    dirteam = Image.new('RGBA', (teamw, teamh))

    #DIRE HEROES

    num = 0

    for heroid in dirpick:
        pickimage = Image.open('images/heroes/' + str(heroid) + '_pick.png')
        dirteam.paste(pickimage, (48 * num, 6))
        num += 1

    num = 0

    for heroid in dirban:
        banimage = Image.open('images/heroes/' + str(heroid) + '.png')
        dirteam.paste(banimage, (32 + 35 * num, 64))
        num += 1

    w, h = ImageDraw.Draw(dirteam).textsize(dirteamname, font=smallfont)
    ImageDraw.Draw(dirteam).text((((teamw - w)/2), 110), dirteamname, font=smallfont, fill=clrwhite)

    dirteam.paste(dire_score_image, (int((teamw - 16)/2), 0), mask=dire_score_image.split()[3])

    img.paste(radteam, (10, 95), mask=radteam.split()[3])
    img.paste(dirteam, (imagew - teamw - 10, 95), mask=dirteam.split()[3])

    # LEAGUENAME SCORE

    if series == 0:
        tiretext = 'Best of 1'
    if series == 1:
        tiretext = 'Best of 3'
    if series == 2:
        tiretext = 'Best of 5'

    w, h = ImageDraw.Draw(img).textsize(tiretext, font=smallfont)
    ImageDraw.Draw(img).text((((imagew - w)/2), 95 + 64 + 20), tiretext, font=smallfont, fill=clrwhite)

    w, h = ImageDraw.Draw(img).textsize('VS', font=smallfont)
    ImageDraw.Draw(img).text((((imagew - w)/2), 95 + 64), 'VS', font=smallfont, fill=clrwhite)

    w, h = ImageDraw.Draw(img).textsize(leaguename, font=smallfont)
    ImageDraw.Draw(img).text((((imagew - w)/2), 95 + 64 + 67), leaguename, font=smallfont, fill=clrwhite)

    img.save('tmp/pickban.png', "PNG")


def vk_post(radteamname, dirteamname, message):
    url = 'https://api.vk.com/method/'
    payload = {'group_id': config.VK_GROUP_ID, 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'photos.getWallUploadServer', params=payload)
    upload_url = r.json()['response']['upload_url']
    picture_to_upload = {'photo': open('tmp/pickban.png', 'rb')}
    r = requests.post(upload_url, files=picture_to_upload)
    server = r.json()['server']
    photo = r.json()['photo']
    photo_hash = r.json()['hash']
    payload = {'group_id': config.VK_GROUP_ID, 'photo': photo, 'server': server, 'hash': photo_hash, 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'photos.saveWallPhoto', params=payload)
    photo_id = r.json()['response'][0]['id']

    payload = {'owner_id': config.VK_GROUP_NEGID, 'question': 'Please vote for the winner', 'add_answers': '["' + radteamname + '", "' + dirteamname + '"]', 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'polls.create', params=payload)
    pollid = r.json().get('response').get('poll_id')
    polltext = 'poll' + config.VK_GROUP_NEGID + '_' + str(pollid)

    payload = {'owner_id': config.VK_GROUP_NEGID, 'from_group': 1, 'message': message, 'attachments': photo_id +',' + polltext, 'access_token': config.VK_API_KEY}
    r = requests.get(url + 'wall.post', params=payload)


getmatchesdata()

