import mwclient
from datetime import datetime

site = mwclient.Site('lol.fandom.com', path='/')

# response = site.api('cargoquery',
# 	limit = 'max',
# 	tables = "ScoreboardGames=SG",
# 	fields = "SG.Tournament, SG.DateTime_UTC, SG.Team1, SG.Team2",
# 	where = "SG.DateTime_UTC >= '2019-08-01 00:00:00'" #Results after Aug 1, 2019
# )


# print("-------------------------------------")


# response2 = site.api('cargoquery',
# 	limit = 'max',
# 	tables = "Teams",
# 	fields = "Name, Short",
# 	where = "IsDisbanded = False AND Region='North America'" 
# )
# items = None
# for key, value in response2.items():
#     items = value

# for i in items:
#     for key, value in i.items():
#         for k, v in value.items():
#             print(v, end=" ")
#         print()


today = datetime.today().strftime('%Y-%m-%d')
birthday = site.api('cargoquery',
	limit = 'max',
	tables = "Players",
	fields = "ID, Name, Age, Birthdate",
    where = "MONTH(Birthdate) = MONTH('" + today + "') AND DAYOFMONTH(Birthdate) = DAYOFMONTH('" + today + "')",
    order_by = "Birthdate DESC"
)

items = None
for key, value in  birthday.items():
    if key == "cargoquery":
        items = value
        break

for i in items:
    for key, value in i.items():
        for k, v in value.items():
            print(v, end="\t")
        print()