import json
import boto3
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key
from decimal import Decimal


def add_player(event, context):
    pass


def get_player_id(event, context):
    pass


def delete_player(event, _):
    try:
        player_id: str = event["queryStringParameters"]["player_id"]

        if len(player_id) != 36:
            raise ValueError("Invalid player_id length. Expects 36, got " + str(len(player_id)))
        elif not all(player_id[i] == "-" for i in [8, 13, 18, 23]):
            raise ValueError("Invalid player_id. Player ID must be UUID string.")
    except KeyError as e:
        return {
            "statusCode": 400,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an issue getting the player_id for this request.",
                "error": str(e)
            })
        }
    except ValueError as e:
        return {
            "statusCode": 400,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Player_id type invalid or data incomplete.",
                "error": str(e)
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an unexpected error while reading player_id for request.",
                "error": str(e)
            })
        }

    try:
        dynamodb = boto3.resource("dynamodb")
        player_table = dynamodb.Table("SamaggiGamesPlayers")
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an error initialising dynamoDB resource in Boto3.",
                "error": str(e)
            })
        }

    try:
        response: Dict[str, Any] = player_table.get_item(Key={"player_uuid", player_id})
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to create reference to data.",
                "error": str(e)
            })
        }

    # Check if the player exists (the response will not contain key "Item" if the item doesn't exist)
    if "Item" not in response:
        return {
            "statusCode": 404,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "The player with that player ID was not found.",
                "error": "Player not found. (Item not in response)",
                "data": response
            })
        }
    else:
        # Extract the data from the item.
        try:
            data: Dict[str, Any] = response["Item"]

            # player_name = data["player_name"]  # Unused
            # main_uni = data["main_uni"]  # Unused
            player_uni = data["player_uni"]
            sport = data["sport"]
        except KeyError as e:
            return {
                "statusCode": 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                "body": json.dumps({
                    "message": "Player table data invalid or malformed. Some field(s) missing.",
                    "error": str(e),
                    "data": {"player_id": player_id}
                })
            }
        except Exception as e:
            return {
                "statusCode": 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                "body": json.dumps({
                    "message": "There was an error extracting data about the player.",
                    "error": str(e)
                })
            }

    # Delete the item
    try:
        player_table.delete_item(Key={'player_uuid': player_id})
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was a problem while deleting item.",
                "error": str(e)
            })
        }

    # Find all the items with the same sport and university. (If there's none we will remove the team).
    try:
        # Scanning as sport and player_uni is not indexed.
        similar_player_query: Dict[str, Any] = player_table.scan()
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was a problem while querying item with the same sport and (player) university.",
                "error": str(e)
            })
        }

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
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an error parsing similar player data.",
                "error": str(e)
            })
        }

    try:
        teams_table = dynamodb.Table("SamaggiGamesTeams")
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an error initialising the teams table.",
                "error": str(e)
            })
        }

    # Check if there's another player with the same university and sport
    if not similar_player_exists:
        try:
            # Scan the table and find the university team uuid we will be deleting.
            university_sport_query = teams_table.query(IndexName="sport", KeyConditionExpression=Key('sport').eq(sport))
        except Exception as e:
            return {
                "statusCode": 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                "body": json.dumps({
                    "message": "There was an error while querying for sport in the teams table.",
                    "error": str(e)
                })
            }

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
                        return {
                            "statusCode": 500,
                            'headers': {
                                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                                'Access-Control-Allow-Origin': '*',
                                'Access-Control-Allow-Methods': '*'
                            },
                            "body": json.dumps({
                                "message": "There's more than one matching team.",
                                "error": "There's more than one team for the same sport and university. This conflict "
                                         "must be resolved manually before continuing."
                            })
                        }
        else:
            return {
                "statusCode": 404,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                "body": json.dumps({
                    "message": "Unable to find the team item to delete.",
                    "error": "Query for sport returned 0 item.",
                    "data": {"sport": sport}
                })
            }
    else:
        return {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Player successfully deleted.",
                "detail": "No team was deleted as another player with the same sport and university exists."
            })
        }

    # Delete the team
    try:
        teams_table.delete_item(Key={"team_uuid": teams_uuid})
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to delete team.",
                "error": str(e),
                "data": {"team_uuid": teams_uuid, "sport": sport, "uni": player_uni}
            })
        }

    if subtract_team_num:
        return {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Player successfully deleted.",
                "detail": "There was no other player from the same university playing the same sport. The team has "
                          "therefore been deleted. Team number not reduced."
            })
        }

    try:
        sport_count_table = dynamodb.Table("SamaggiGamesSportCount")
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to create reference to SamaggiGamesSportCount.",
                "error": str(e)
            })
        }

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
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to update sport count.",
                "error": str(e)
            })
        }

    return {
        "statusCode": 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type,authorisation',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
        "body": json.dumps({
            "message": "Player successfully deleted.",
            "detail": "There was no other player from the same university playing the same sport. The team has "
                      "therefore been deleted. Team number reduced."
        })
    }


def get_table(event, _):
    try:
        table_name = event["queryStringParameters"]["table_name"]
    except KeyError as e:
        return {
            "statusCode": 400,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to get table_name from request parameters. Parameter not provided.",
                "error": str(e)
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to get table_name from request parameter due to unexpected error.",
                "error": str(e)
            })
        }

    try:
        dynamodb = boto3.resource("dynamodb")
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "There was an error initialising dynamoDB resource in Boto3.",
                "error": str(e)
            })
        }

    try:
        table_ref = dynamodb.Table(table_name)
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to initialise the table.",
                "error": str(e)
            })
        }

    try:
        response = table_ref.scan()
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Unable to scan table.",
                "error": str(e)
            })
        }

    if "Items" not in response:
        return {
            "statusCode": 404,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "The table does not contain any data or the table does not exist.",
                "error": "No data."
            })
        }
    else:
        return {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type,authorisation',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            "body": json.dumps({
                "message": "Success",
                "data": response["Items"]
            })
        }
