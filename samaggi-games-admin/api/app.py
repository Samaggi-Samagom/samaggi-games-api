import csv
import datetime
import json
import uuid
from decimal import Decimal
from typing import Dict, Any, List
import boto3
from DynamoDBInterface import DynamoDB
from support import Arguments, university_names, university_names_simplified, university_city, simplify_university

db: DynamoDB.Database = DynamoDB.Database()


# Adapted from Elias Zamaria's answer on Stack Overflow, dated: 7th Oct 2010, accessed 21st Dec 2021.
# Available at: https://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


class DynamoDBQueryResponse(list):

    def __init__(self, dictionary):
        if "Items" not in dictionary:
            self.is_empty = True
            super().__init__([])
        else:
            self.is_empty = False
            super().__init__(dictionary["Items"])

    def query(self, query_parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        query_result = []
        for result in self:
            if all(result[key] == value for key, value in query_parameters.items()):
                query_result.append(result)
        return query_result

    def item_exists_where(self, conditions: Dict[str, Any]) -> bool:
        for result in self:
            if all(result[key] == value for key, value in conditions.items()):
                return True
        return False

    def where_eq(self, key_1: str, key_2: str, eval_as: str = None):
        valid_types = {
            "NUMBER": int,
            "STRING": str,
            "ARRAY": list
        }
        if eval_as is not None and eval_as not in valid_types.keys():
            raise ValueError("Invalid evaluation type.")
        query_result = []
        for result in self:
            if eval_as is not None:
                result[key_1] = valid_types[eval_as](result[key_1])
                result[key_2] = valid_types[eval_as](result[key_2])
            if result[key_1] == result[key_2]:
                query_result.append(result)
        return query_result

    def first_item_where(self, conditions: Dict[str, Any], raise_if_not_found: bool = True) -> Dict[str, Any]:
        for result in self:
            if all(result[key] == value for key, value in conditions.items()):
                return result
        if raise_if_not_found:
            raise ValueError("No item matches conditions")

    def unique_values_for_key(self, key: str):
        unique_values = []
        for result in self:
            if result[key] not in unique_values:
                unique_values.append(result[key])
        return unique_values


def cors(data: Dict[str, Any]):
    data["headers"] = {
        'Access-Control-Allow-Headers': 'Content-Type,authorisation',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*'
    }
    return data


def get_sports(_, __):
    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Sports Retrieved.",
            "sports": list(x["sport_name"] for x in db.table("SamaggiGamesSportCount").scan().all())
        })
    })


def check_code(event, __):
    arguments = Arguments(event)
    code = arguments["code"].lower().replace(" ", "")

    address_data = db.table("SamaggiGamesAddress").get(code)

    address_name = ""
    address1 = ""
    address2 = ""
    city = ""
    postcode = ""

    if address_data.exists():
        address_name = address_data["addr-name"]
        address1 = address_data["addr1"]
        address2 = address_data["addr2"]
        city = address_data["city"]
        postcode = address_data["postcode"]

    if code in university_names_simplified:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Signed In",
                "valid": True,
                "name": university_names[university_names_simplified.index(code)],
                "addr-name": address_name,
                "addr1": address1,
                "addr2": address2,
                "city": city,
                "postcode": postcode
            })
        })
    else:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "University not found. Check your code and try again.",
                "valid": False,
                "name": ""
            })
        })


def save_address(event, _):
    arguments = Arguments(event)

    db.table("SamaggiGamesAddress").write({
        "code": arguments["code"],
        "addr-name": arguments["addrName"],
        "addr1": arguments["addr1"],
        "addr2": arguments["addr2"],
        "city": arguments["city"],
        "postcode": arguments["postcode"]
    })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Saved Successfully"
        })
    })


def team_exists(event, _):
    try:
        arguments = Arguments(event)
        team_university = arguments["player_university"]
        sport = arguments["sport"]
    except Exception as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "There was an issue getting required parameters.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    team_data = db.table("SamaggiGamesTeams").get(
        "university", equals=team_university,
        is_secondary_index=True
    )

    if any(team["sport"] == sport for team in team_data.all()):
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "exist": True
            })
        })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success",
            "exist": False
        })
    })


def data_statistics(_, __):
    try:
        dynamodb = boto3.resource("dynamodb")
        player_table = dynamodb.Table("SamaggiGamesPlayers")
        team_table = dynamodb.Table("SamaggiGamesTeams")
        sport_count_table = dynamodb.Table("SamaggiGamesSportCount")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to initialise one or more tables.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        player_data_query = DynamoDBQueryResponse(player_table.scan())
        teams_data_query = DynamoDBQueryResponse(team_table.scan())
        sport_data_query = DynamoDBQueryResponse(sport_count_table.scan())
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to scan tables.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        response = {
            "unique_main_universities": teams_data_query.unique_values_for_key("team_university"),
            "unique_player_universities": teams_data_query.unique_values_for_key("university"),
            "unique_players": player_data_query.unique_values_for_key("name"),
            "full_teams": sport_data_query.where_eq("max_teams", "team_count", eval_as="NUMBER")
        }

        response["num_unique_main_universities"] = len(response["unique_main_universities"])
        response["num_unique_player_universities"] = len(response["unique_player_universities"])
        response["num_unique_player"] = len(response["unique_players"])
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to parse query results.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "data": response,
            "raw_data": {
                "sport_count": sport_data_query,
                "players": player_data_query,
                "teams": teams_data_query
            }
        }, cls=DecimalEncoder)
    })


def sport_clash(event, _):
    arguments = Arguments(event)
    sport = arguments["sport"]
    name = arguments["name"]
    player_university = arguments["player_university"]

    reader = csv.reader(open("timetable.csv", "r"))
    timetable = {}
    for row in reader:
        timetable[row[0]] = {'start_time': row[1], 'end_time': row[2]}

    player_data = db.table("SamaggiGamesPlayers").get(  # get details of the player
        "name", equals=name,
        is_secondary_index=True
    )
    filtered_players = player_data.filter("player_university", player_university)

    for i in range(len(filtered_players)):
        reg_sport = filtered_players[i]["sport"]  # get the sports the player is playing

        start_h1 = int(timetable[reg_sport]['start_time'].split(':')[0])
        start_m1 = int(timetable[reg_sport]['start_time'].split(':')[1])
        start_time1 = datetime.datetime(2023, 3, 4, start_h1, start_m1, 00)

        end_h1 = int(timetable[reg_sport]['end_time'].split(':')[0])
        end_m1 = int(timetable[reg_sport]['end_time'].split(':')[1])
        end_time1 = datetime.datetime(2023, 3, 4, end_h1, end_m1, 00)

        start_h2 = int(timetable[sport]['start_time'].split(':')[0])
        start_m2 = int(timetable[sport]['start_time'].split(':')[1])
        start_time2 = datetime.datetime(2023, 3, 4, start_h2, start_m2, 00)

        end_h2 = int(timetable[sport]['end_time'].split(':')[0])
        end_m2 = int(timetable[sport]['end_time'].split(':')[1])
        end_time2 = datetime.datetime(2023, 3, 4, end_h2, end_m2, 00)

        if not (end_time1 <= start_time2 or end_time2 <= start_time1):
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Success",
                    "clash": True
                })
            })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success",
            "clash": False
        })
    })


def is_player_valid(event, _):  # get player_university, team_university, sport
    arguments = Arguments(event)
    team_uni = arguments["team_university"]
    player_uni = arguments["player_university"]
    sport = arguments["sport"]

    team_sport_players = db.table("SamaggiGamesPlayers").get(
        "team_university", equals=team_uni,
        is_secondary_index=True
    ).filter("sport", sport)

    from DynamoDBInterface.DynamoDB import FilterType

    if sport == "Football":
        team_support_players = team_sport_players.filter("player_city", university_city(simplify_university(team_uni)),
                                                         filter_type=FilterType.NOT_EQUAL)
        if university_city(simplify_university(player_uni)) != university_city(simplify_university(team_uni)) and\
                (len(team_support_players) + 1)/(len(team_sport_players) + 1) > 0.5 and player_uni != team_uni:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"At least 50% of the player in the team must be from the city of the Thai Society "
                               f"forming the team.",
                    "valid": False
                })
            })
    else:
        team_support_players = team_sport_players.filter("player_university",
                                                         team_uni,
                                                         filter_type=FilterType.NOT_EQUAL)
        if (len(team_support_players) + 1)/(len(team_sport_players) + 1) > 0.5 and player_uni != team_uni:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"At least 50% of the player in the team must be from the Thai Society forming the "
                               f"team.",
                    "valid": False
                })
            })

    similar_players = db.table("SamaggiGamesPlayers").get(  # all players that play for this uni
        "player_university", equals=player_uni,
        is_secondary_index=True
    ).filter("sport", sport)

    similar_players_uni = list(similar_players.unique("team_university"))
    if len(similar_players_uni) > 0 and similar_players_uni[0] != team_uni:
        if similar_players_uni == player_uni:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"{player_uni} already has a team for {sport}.",
                    "valid": False
                })
            })
        else:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"{player_uni} already playing for another team for {sport}.",
                    "valid": False
                })
            })

    allied_unis = []
    player_data = db.table("SamaggiGamesPlayers").get(  # all players that play for this uni
        "team_university", equals=team_uni,
        is_secondary_index=True
    )
    filtered_players = player_data.filter("sport", sport)  # all players that play this sport for this uni
    city_unis = []

    if sport == "Football":
        [allied_unis.append(
            f"{filtered_players[j]['player_university']} "
            f"({university_city(simplify_university(filtered_players[j]['player_university']))})")
            for j in range(len(filtered_players))
            if filtered_players[j]["player_university"] not in allied_unis
            and filtered_players[j]["player_city"] != university_city(simplify_university(team_uni))]
        [city_unis.append(filtered_players[k]['player_university']) for k in range(len(filtered_players))
            if filtered_players[k]["player_university"] not in city_unis and
            university_city(simplify_university(filtered_players[k]["player_university"])) ==
         university_city(simplify_university(team_uni))]
    else:
        [allied_unis.append(filtered_players[j]["player_university"]) for j in range(len(filtered_players)) if
         filtered_players[j]["player_university"] not in allied_unis]

    if sport == "Football":
        if f"{player_uni} ({university_city(simplify_university(player_uni))})" not in allied_unis and \
                len(allied_unis) == 3:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"The city of {university_city(simplify_university(team_uni))} ({', '.join(city_unis)}) "
                               f"{sport} team already has three supporting universities not from the city: "
                               f"{', '.join(allied_unis)}",
                    "valid": False
                })
            })
    else:
        if player_uni not in allied_unis and len(allied_unis) == 3:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"{team_uni} {sport} team already has three supporting universities: "
                               f"{', '.join(allied_unis)}",
                    "valid": False
                })
            })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success",
            "valid": True
        })
    })


def add_player(event, _):
    details = {}
    # get the players' team_university and sport
    try:
        arguments = Arguments(event)
        team_university = arguments["team_university"]
        sport = arguments["sport"]
    except Exception as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "There was an issue getting required parameters.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    team_data = db.table("SamaggiGamesTeams").get(
        "team_university", equals=team_university,
        is_secondary_index=True
    )

    if not any(team["sport"] == sport for team in team_data.all()):  # if team not already in SamaggiGamesTeams table
        try:
            count_data = db.table("SamaggiGamesSportCount").get(
                "sport_name", equals=sport
            )
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": f"Unable to get the number of teams for {sport}.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                    "data": {
                        "university": sport
                    }
                })
            })

        team_count = int(count_data["team_count"])
        max_team = int(count_data["max_teams"])

        if len(team_data) >= count_data["max_size"]:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"This team already has the maximum number of players"
                })
            })

        if team_count >= max_team:  # check if team slot for the sport is full
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"{sport} already has the maximum number of teams"
                })
            })

        details["willCreateTeam"] = True
        try:
            captain_name = arguments["captain_name"]
            captain_contact = arguments["captain_contact"]
            team_id = str(uuid.uuid4())
        except Exception as e:
            return cors({
                "statusCode": 400,
                "body": json.dumps({
                    "message": "There was an issue getting required parameters (captain details).",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                })
            })

        try:  # add team to SamaggiGamesTeams table
            db.table("SamaggiGamesTeams").write(
                {
                    "team_uuid": team_id,
                    "sport": sport,
                    "team_university": team_university,
                    "captain": captain_name,
                    "contact": captain_contact,
                    "university": team_university
                }
            )
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": f"Unable to save team {team_university} to team table.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })
        else:
            details["didCreateTeam"] = True

        details["willUpdateTeamCount"] = True  # increment team count
        try:
            db.table("SamaggiGamesSportCount").increment(
                "sport_name", equals=sport,
                value_key="team_count", by=1
            )
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": f"Unable to increment team_count for {sport}. Error: {e.args}",
                })
            })
        else:
            details["didUpdateTeamCount"] = True

    for i in range(len(arguments["players"])):
        try:  # get each player name and player_university
            name = arguments["players"][i]["name"]
            nickname = arguments["players"][i]["nickname"]
            player_university = arguments["players"][i]["player_university"]
            player_uuid = str(uuid.uuid4())
        except Exception as e:
            return cors({
                "statusCode": 400,
                "body": json.dumps({
                    "message": "Function call requires playerFirstName, playerLastName and player_university.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })

        sport_teams = db.table("SamaggiGamesTeams").get(
            "sport", equals=sport,
            is_secondary_index=True
        )
        uni_in_table = sport_teams.filter("team_university", team_university).filter("university", player_university)

        if not uni_in_table:
            try:
                captain_name = arguments["captain_name"]
                captain_contact = arguments["captain_contact"]
                team_id = str(uuid.uuid4())
            except Exception as e:
                return cors({
                    "statusCode": 400,
                    "body": json.dumps({
                        "message": "There was an issue getting required parameters (captain details).",
                        "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                    })
                })

            try:  # add team to SamaggiGamesTeams table
                db.table("SamaggiGamesTeams").write(
                    {
                        "team_uuid": team_id,
                        "sport": sport,
                        "team_university": team_university,
                        "captain": captain_name,
                        "contact": captain_contact,
                        "university": player_university
                    }
                )
            except Exception as e:
                return cors({
                    "statusCode": 500,
                    "body": json.dumps({
                        "message": f"Unable to save team {team_university} to team table.",
                        "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                    })
                })

        try:  # add player to SamaggiGamesPlayers table
            db.table("SamaggiGamesPlayers").write(
                {
                    "player_uuid": player_uuid,
                    "sport": sport,
                    "team_university": team_university,
                    "name": name,
                    "nickname": nickname,
                    "player_university": player_university,
                    "image": arguments["image"],
                    "player_city": university_city(simplify_university(player_university))
                }
            )
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": f"Unable to save player {name} to player table.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success",
            "details": details
        })
    })


def delete_player(event, _):
    details = {}

    arguments = Arguments(event)
    player_id: str = arguments["player_uuid"]

    deleting_player = db.table("SamaggiGamesPlayers").get(
        "player_uuid", equals=player_id
    )

    if not deleting_player.exists():  # if player do not exist
        return cors({
            "statusCode": 404,
            "body": json.dumps({
                "message": "Cannot find player in the player table.",
                "error": True
            })
        })

    team_university = deleting_player["team_university"]
    player_university = deleting_player["player_university"]
    sport = deleting_player["sport"]

    sport_players = db.table("SamaggiGamesPlayers").get(
        "sport", equals=sport,
        is_secondary_index=True
    )

    sport_players_same_team = sport_players.filter("team_university", team_university)
    sport_players_same_uni = sport_players.filter("player_university", player_university)

    if team_university == player_university:
        if len(sport_players_same_team) != 1 and \
                (len(sport_players_same_uni) - 1)/(len(sport_players_same_team) - 1) < 0.5:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "At least 50% of the player in the team must be from the Thai Society forming the team.",
                    "error": True
                })
            })

    db.table("SamaggiGamesPlayers").delete("player_uuid", equals=player_id)

    if sport_players_same_uni.length() == 1:
        details["deleteTeam"] = True
        team = db.table("SamaggiGamesTeams").get(
            "sport", equals=sport,
            is_secondary_index=True
        ).filter("university", player_university)

        if team.exists():
            details["deleteTeamExist"] = True
            team_id = team["team_uuid"]
            db.table("SamaggiGamesTeams").delete("team_uuid", team_id)

        if team_university == player_university:
            details["decrementTeamCount"] = True
            db.table("SamaggiGamesSportCount").decrement(
                "sport_name", equals=sport,
                value_key="team_count", by=1
            )

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Player successfully deleted.",
            "detail": details
        })
    })


def edit_player(event, _):
    arguments = Arguments(event)
    player_id: str = arguments["player_uuid"]

    player_in_table = db.table("SamaggiGamesPlayers").there_exists(  # find player in SamaggiGamesPlayers table
        player_id, at_column="player_uuid"
    )

    if not player_in_table:  # if player do not exist
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Cannot find player in the player table."
            })
        })

    db.table("SamaggiGamesPlayers").delete("player_uuid", player_id)  # delete

    # get the new players' details
    try:
        team_university = arguments["team_university"]
        sport = arguments["sport"]
        name = arguments["name"]
        player_university = arguments["player_university"]
        player_uuid = str(uuid.uuid4())
    except Exception as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Function call requires team_university, sport, playerFirstName, playerLastName and "
                           "player_university",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:  # add player to SamaggiGamesPlayers table
        db.table("SamaggiGamesPlayers").write(
            {
                "player_uuid": player_uuid,
                "sport": sport,
                "team_university": team_university,
                "name": name,
                "player_university": player_university
            }
        )
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": f"Unable to save player {name} to player table.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success"
        })
    })


def get_table_v2(event, _):
    arguments = Arguments(event)

    table_name = arguments["tableName"]
    filters = arguments["filters"]

    scan_result = db.table(table_name).scan()

    res = scan_result
    for f in filters:
        res = res.filter(f["key"], f["value"])

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Table Retrieved.",
            "tableData": res.all()
        })
    })


def get_table(event, _):
    try:
        arguments = Arguments(event)
        table_name = arguments["table_name"]
    except KeyError as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Unable to get table_name from request parameters. Parameter not provided.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to get table_name from request parameter due to unexpected error.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        dynamodb = boto3.resource("dynamodb")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an error initialising dynamoDB resource in Boto3.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        table_ref = dynamodb.Table(table_name)
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to initialise the table.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        response = table_ref.scan()
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to scan table.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    if "Items" not in response:
        return cors({
            "statusCode": 404,
            "body": json.dumps({
                "message": "The table does not contain any data or the table does not exist.",
                "error": "No data."
            })
        })
    else:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "data": response["Items"]
            }, cls=DecimalEncoder)
        })


def write_spectator(event, __):
    arguments = Arguments(event)
    arguments.require(["formData", "paymentVerification", "amount"])

    if not arguments.available():
        return arguments.error
    if not arguments.contains_requirements():
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Missing Arguments",
                "data": {
                    "expects": arguments.requirements(),
                    "got": arguments.keys()
                }
            }, cls=DecimalEncoder)
        })

    spectators = db.table("SamaggiGamesSpectator").scan()
    payments = db.table("SamaggiGamesPayment").scan()

    spector_payments = spectators.join(payments, "payment-id")

    used_payments = spector_payments.unique("payment-verification")

    if arguments.get("paymentVerification") in used_payments:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Payment Verification Already Used",
                "data": {}
            }, cls=DecimalEncoder)
        })

    payment_data = payments.get_where("payment-verification", arguments.get("paymentVerification"))

    db.table("SamaggiGamesPayment").update(
        payment_data["payment-id"],
        data_to_update={
            "amount": arguments.get("amount")
        }
    )

    if payment_data == {}:
        return cors({
            "statusCode": 404,
            "body": json.dumps({
                "message": "Payment Code Not Found",
                "data": {}
            }, cls=DecimalEncoder)
        })

    data = arguments.get("formData")
    data.update({
        "spectator-id": str(uuid.uuid4()),
        "payment-id": payment_data["payment-id"]
    })

    db.table("SamaggiGamesSpectator").write(data)

    # return cors({
    #         "statusCode": 200,
    #         "body": json.dumps({
    #             "message": "Success",
    #             "data": {
    #                 "success": True
    #             }
    #         }, cls=DecimalEncoder)
    #     })

    return cors({
        "statusCode": 400,
        "body": json.dumps({
            "message": "Form Closed. Please buy your ticket at the event.",
            "data": {}
        })
    })


def get_payment_code(_, __):
    verifications = db.table("SamaggiGamesPayment").scan().unique("payment-verification")

    verification = str(uuid.uuid4())[:8]
    while verification in verifications:
        verification = str(uuid.uuid4())[:8]

    db.table("SamaggiGamesPayment").write({
        "payment-id": str(uuid.uuid4()),
        "payment-verification": verification,
        "paid": False,
        "notified": False,
        "amount": -1
    })

    return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "data": {
                    "verification": verification
                }
            }, cls=DecimalEncoder)
        })
