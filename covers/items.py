from scrapy import Field, Item


class Game(Item):
    date = Field()
    location = Field()
    opponent = Field()
    score = Field()
    opponent_score = Field()
    result = Field()
    spread = Field()
    spread_result = Field()
    over_under = Field()
    over_under_result = Field()
    response_url = Field()


class Team(Item):
    city = Field()
    url = Field()
