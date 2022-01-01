import json
import uuid
import boto3
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key
from decimal import Decimal


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

    def first_item_where(self, conditions: Dict[str, Any], raise_if_not_found: bool = True) -> Dict[str, Any]:
        for result in self:
            if all(result[key] == value for key, value in conditions.items()):
                return result
        if raise_if_not_found:
            raise ValueError("No item matches conditions")


def cors(data: Dict[str, Any]):
    data["headers"] = {
        'Access-Control-Allow-Headers': 'Content-Type,authorisation',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*'
    }
    return data


def team_exists(event, _):
    try:
        university = event["queryStringParameters"]["university"]
        sport = event["queryStringParameters"]["sport"]
    except Exception as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "There was an issue getting required parameters.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        dynamodb = boto3.resource("dynamodb")
        teams_table = dynamodb.Table("SamaggiGamesTeams")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an error initialising dynamoDB resource or creating reference to table.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        uni_query_response = teams_table.query(IndexName="uni", KeyConditionExpression=Key('uni').eq(university))
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to get list of teams using university.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                "data": {
                    "university": university
                }
            })
        })

    if "Items" not in uni_query_response:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "The team does not exist.",
                "exists": False
            })
        })
    else:
        data = uni_query_response["Items"]
        if any([x["sport"] == sport for x in data]):
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "The team exists.",
                    "exists": True
                })
            })
        else:
            return cors({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "The team does not exist.",
                    "exists": False
                })
            })


def add_player(event, _):
    details = {}

    try:
        university = event["queryStringParameters"]["university"]
        sport = event["queryStringParameters"]["sport"]
        name = event["queryStringParameters"]["name"]
        main_university = event["queryStringParameters"]["main_university"]
    except Exception as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Function call requires university, sport, name, main_university.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    player_uuid = str(uuid.uuid4())

    try:
        dynamodb = boto3.resource("dynamodb")
        player_table = dynamodb.Table("SamaggiGamesPlayers")
        teams_table = dynamodb.Table("SamaggiGamesTeams")
        sport_count_table = dynamodb.Table("SamaggiGamesSportCount")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to initialise tables.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        uni_query_response = DynamoDBQueryResponse(
            teams_table.query(IndexName="uni", KeyConditionExpression=Key('uni').eq(university)))
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to get list of teams using the player's university.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                "data": {
                    "university": university
                }
            })
        })

    if uni_query_response.is_empty or (not uni_query_response.item_exists_where({"sport": sport})):
        details["willCreateTeam"] = True
        try:
            team_captain = event["queryStringParameters"]["captainName"]
            captain_contact = event["queryStringParameters"]["captainContact"]
            team_id = str(uuid.uuid4())
        except Exception as e:
            return cors({
                "statusCode": 400,
                "body": json.dumps({
                    "message": "Missing captain details for creating player with a new team.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                    "data": {
                        "queryStringParameters": event["queryStringParameters"],
                        "items": uni_query_response,
                        "sport": sport,
                        "debug_1": uni_query_response.is_empty,
                        "debug_2": not uni_query_response.item_exists_where({"sport": sport})
                    }
                })
            })

        try:
            teams_table.put_item(
                Item={
                    "team_uuid": team_id,
                    "captain": team_captain,
                    "contact": captain_contact,
                    "main_uni": main_university,
                    "sport": sport,
                    "uni": university
                }
            )
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Unable to save new team.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })
        else:
            details["didCreateTeam"] = True

        if main_university == university:
            details["willUpdateTeamCount"] = True
            try:
                sport_count_table.update_item(
                    Key={
                        "sport_name": sport
                    },
                    UpdateExpression="set team_count= team_count + :v",
                    ExpressionAttributeValues={
                        ":v": Decimal(1)
                    },
                    ReturnValues="UPDATED_NEW"
                )
            except Exception as e:
                return cors({
                    "statusCode": 500,
                    "body": json.dumps({
                        "message": "Unable to increment team count.",
                        "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                    })
                })
            else:
                details["didUpdateTeamCount"] = True

    try:
        player_table.put_item(
            Item={
                "player_uuid": player_uuid,
                "main_uni": main_university,
                "player_name": name,
                "player_uni": university,
                "sport": sport
            }
        )
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to save player to player table.",
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
    try:
        player_id: str = event["queryStringParameters"]["player_id"]

        if len(player_id) != 36:
            raise ValueError("Invalid player_id length. Expects 36, got " + str(len(player_id)))
        elif not all(player_id[i] == "-" for i in [8, 13, 18, 23]):
            raise ValueError("Invalid player_id. Player ID must be UUID string.")
    except KeyError as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "There was an issue getting the player_id for this request.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })
    except ValueError as e:
        return cors({
            "statusCode": 400,
            "body": json.dumps({
                "message": "Player_id type invalid or data incomplete.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an unexpected error while reading player_id for request.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        dynamodb = boto3.resource("dynamodb")
        player_table = dynamodb.Table("SamaggiGamesPlayers")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an error initialising dynamoDB resource in Boto3.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        response: Dict[str, Any] = player_table.get_item(Key={"player_uuid": player_id})
    except Exception as e:
        return cors({
            "statusCode": 500,

            "body": json.dumps({
                "message": "Unable to create reference to data.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    # Check if the player exists (the response will not contain key "Item" if the item doesn't exist)
    if "Item" not in response:
        return cors({
            "statusCode": 404,
            "body": json.dumps({
                "message": "The player with that player ID was not found.",
                "error": "Player not found. (Item not in response)",
                "data": response
            })
        })
    else:
        # Extract the data from the item.
        try:
            data: Dict[str, Any] = response["Item"]

            # player_name = data["player_name"]  # Unused
            # main_uni = data["main_uni"]  # Unused
            player_uni = data["player_uni"]
            sport = data["sport"]
        except KeyError as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Player table data invalid or malformed. Some field(s) missing.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                    "data": {"player_id": player_id}
                })
            })
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": "There was an error extracting data about the player.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })

    # Delete the item
    try:
        player_table.delete_item(Key={'player_uuid': player_id})
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was a problem while deleting item.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    # Find all the items with the same sport and university. (If there's none we will remove the team).
    try:
        # Scanning as sport and player_uni is not indexed.
        similar_player_query: Dict[str, Any] = player_table.scan()
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was a problem while querying item with the same sport and (player) university.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        if "Items" in similar_player_query:
            similar_player_data: List[Dict[str, Any]] = similar_player_query["Items"]
            if any(x["player_uni"] == player_uni for x in similar_player_data):
                similar_player_exists = True
            else:
                similar_player_exists = False
        else:
            similar_player_exists = False
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an error parsing similar player data.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        teams_table = dynamodb.Table("SamaggiGamesTeams")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "There was an error initialising the teams table.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    # Check if there's another player with the same university and sport
    if not similar_player_exists:
        try:
            # Scan the table and find the university team uuid we will be deleting.
            university_sport_query = teams_table.query(IndexName="sport", KeyConditionExpression=Key('sport').eq(sport))
        except Exception as e:
            return cors({
                "statusCode": 500,
                "body": json.dumps({
                    "message": "There was an error while querying for sport in the teams table.",
                    "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
                })
            })

        teams_uuid = None
        subtract_team_num = False

        if "Items" in university_sport_query and len(university_sport_query["Items"]) > 0:
            sport_items: List[Dict[str, Any]] = university_sport_query["Items"]
            for item in sport_items:
                if item["uni"] == player_uni:
                    if teams_uuid is None:
                        teams_uuid = item["team_uuid"]
                        if item["uni"] == item["main_uni"]:
                            subtract_team_num = True
                    else:
                        return cors({
                            "statusCode": 500,
                            "body": json.dumps({
                                "message": "There's more than one matching team.",
                                "error": "There's more than one team for the same sport and university. This conflict "
                                         "must be resolved manually before continuing."
                            })
                        })
        else:
            return cors({
                "statusCode": 404,
                "body": json.dumps({
                    "message": "Unable to find the team item to delete.",
                    "error": "Query for sport returned 0 item.",
                    "data": {"sport": sport}
                })
            })
    else:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Player successfully deleted.",
                "detail": "No team was deleted as another player with the same sport and university exists."
            })
        })

    # Delete the team
    try:
        teams_table.delete_item(Key={"team_uuid": teams_uuid})
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to delete team.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args)),
                "data": {"team_uuid": teams_uuid, "sport": sport, "uni": player_uni}
            })
        })

    if not subtract_team_num:
        return cors({
            "statusCode": 200,
            "body": json.dumps({
                "message": "Player successfully deleted.",
                "detail": "There was no other player from the same university playing the same sport. The team has "
                          "therefore been deleted. Team number not reduced."
            })
        })

    try:
        sport_count_table = dynamodb.Table("SamaggiGamesSportCount")
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to create reference to SamaggiGamesSportCount.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    try:
        sport_count_table.update_item(
            Key={
                "sport_name": sport
            },
            UpdateExpression="set team_count= team_count - :v",
            ExpressionAttributeValues={
                ":v": Decimal(1)
            },
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        return cors({
            "statusCode": 500,
            "body": json.dumps({
                "message": "Unable to update sport count.",
                "error": "Type: {}, Error Args: {}".format(str(type(e)), str(e.args))
            })
        })

    return cors({
        "statusCode": 200,
        "body": json.dumps({
            "message": "Player successfully deleted.",
            "detail": "There was no other player from the same university playing the same sport. The team has "
                      "therefore been deleted. Team number reduced."
        })
    })


def get_table(event, _):
    try:
        table_name = event["queryStringParameters"]["table_name"]
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
