import re
import sqlite3
from datetime import datetime


class GamePipeline(object):
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        db = settings.get('DATABASE')
        drop = settings.getbool('DROP')
        return cls(db, drop)

    def __init__(self, db, drop):
        self.db = db
        self.drop = drop
        self.con = None
        self.cur = None

    def open_spider(self, spider):
        if spider.name == 'games' and self.db is not None:
            self.con = sqlite3.connect(self.db)
            self.cur = self.con.cursor()

            if self.drop:
                self.cur.executescript('''
                    DROP TABLE IF EXISTS betting;
                    CREATE TABLE betting(GAME_ID TEXT, HOME_SPREAD REAL, HOME_SPREAD_WL TEXT,
                                         OVER_UNDER REAL, OU_RESULT TEXT);
                    ''')

    def close_spider(self, spider):
        if spider.name == 'games' and self.db is not None:
            self.cur.execute('VACUUM')
            self.con.close()

    def process_item(self, item, spider):
        if spider.name == 'games' and self.db is not None:
            self.store_item(item)

        return item

    def store_item(self, item):
        opponent = item['opponent']
        date = item['date']
        location = item['location']
        response = item['response_url']
        season_start = response.split('/')[9].split('-')[0]
        season_end = response.split('/')[9].split('-')[1]
        #apparently this data is needed to log it to the database?
        if '@' in location:
            location='vs'
        else:
            location='away'
        season_type = 'Regular Season'
        start_of_season = ['Oct', 'Nov', 'Dec']
        end_of_season = ['Jan', 'Feb', 'Mar', 'Apr', 'May']
        if date[0].split()[0] in start_of_season:
            date = date + ' ' + season_start
        elif date[0].split()[0] in end_of_season:
            date = date + ' ' + season_end
        # only store regular season home games to avoid duplicating games
        #if item['season_type'] == 'Regular Season' and location == 'vs':
        if season_type == 'Regular Season' and location == 'vs':
            date = datetime.strptime(date, '%b %d %Y')

            # find team ID by mascot for the two LA teams and by city for all other teams
            pattern = re.compile('L\.?A\.? ')
            pattern2 = re.compile('[A-Z][A-Z][A-Z]')
            #opponent = opponent.strip('@ ')
            opponent = opponent.replace('@ ', '')
            team_abbr = {
                'BK': 'BKN',
                'GS': 'GSW',
                'SA': 'SAS',
                'PHO': 'PHX',
                'NY': 'NYK',
                'NO': 'NOP'
            }

            if opponent in team_abbr:
                opponent = team_abbr[opponent]

            if pattern2.match(opponent):
                self.cur.execute('SELECT ID FROM teams WHERE ABBREVIATION IS "{}"'.format(opponent))
                #self.cur.execute('SELECT ID FROM teams WHERE CITY IS "{}"'.format(opponent))

            elif pattern.match(opponent) is not None:
                opponent = pattern.sub('', opponent)
                self.cur.execute('SELECT ID FROM teams WHERE MASCOT IS "{}"'.format(opponent))
            else:
                #left this in for backwards compatibility
                self.cur.execute('SELECT ID FROM teams WHERE CITY IS "{}"'.format(opponent))

            TEAM_ID = self.cur.fetchone()[0]
            self.cur.execute('SELECT ID FROM games WHERE AWAY_TEAM_ID == {} AND GAME_DATE IS "{}"'
                             .format(TEAM_ID, date.strftime('%Y-%m-%d')))
            game_id = self.cur.fetchone()

            if game_id is None:
                self.cur.execute('SELECT ID FROM games WHERE HOME_TEAM_ID == {} AND GAME_DATE IS "{}"'
                                 .format(TEAM_ID, date.strftime('%Y-%m-%d')))
                game_id = self.cur.fetchone()
                if game_id is None:       
                    raise ValueError('No game found')
#                raise ValueError('No game found',print(opponent))

            values = (game_id[0], item['spread'], item['spread_result'], item['over_under'], item['over_under_result'])
            self.cur.execute('''INSERT INTO betting(GAME_ID, HOME_SPREAD, HOME_SPREAD_WL, OVER_UNDER, OU_RESULT)
                                VALUES(?, ?, ?, ?, ?)''', values)
            self.con.commit()
