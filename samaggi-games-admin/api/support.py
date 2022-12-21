from typing import Dict, Any, List
import json


class Arguments:

    def __init__(self, event: Dict[str, Any]):
        self._required_args = None
        self.error = None
        self._arguments = self._get_arguments(event)

    def available(self):
        return self._arguments is not None

    def _get_arguments(self, event: Dict[str, Any]):
        cleaned_body = event["body"].replace("\n", "")
        try:
            return json.loads(cleaned_body)
        except json.decoder.JSONDecodeError as e:
            self.error = "ERROR"
            return None

    def contains(self, expected_parameters: List[str]):
        return all(x in self._arguments for x in expected_parameters)

    def contains_requirements(self):
        return all(x in self._arguments for x in self._required_args)

    def keys(self):
        return self._arguments.keys()

    def require(self, x: List[str]):
        self._required_args = x

    def requirements(self):
        return self._required_args

    def __getitem__(self, item):
        return self._arguments[item]

    def get(self, item):
        return self[item]