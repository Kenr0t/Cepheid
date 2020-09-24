from datetime import datetime, time
import json
import re

import requests

from Compiler import Lexer, Parser, LexingError
from config import orion_url, cepheid_url


class Rule:
    _lexer = Lexer()
    _parser = Parser()

    def __init__(self, rule: str, service: str, servicepath: str, true: str = None, false: str = None, subsId=None):
        self.headers = {
            'Accept': 'application/json',
            'Fiware-Service': service,
            'Fiware-ServicePath': servicepath
        }
        self.rule = rule
        self.true, self.false = true, false
        self._date_from, self._date_to = datetime(1900, 1, 1), datetime(9999, 12, 31)
        self._start_time, self._end_time = None, None
        self.subscription_id = subsId

    def _check_action(self, action):
        """
        Checks if action is in the entity of the action and the action itself exist and has the correct type.
        :param action: Action in the format <Entity_ID>.<Action>
        :return: The entity type and the input action
        """
        if action is None:
            return None, None
        if re.match(r'[a-zA-Z_]\w+\.[a-zA-Z_]\w+$', action):  # Must tu have the format entity.command
            entity_id, command = action.split('.')

            entity = requests.get(url=f'{orion_url}/v2/entities/{entity_id}', headers=self.headers)

            if not 200 <= entity.status_code < 300:  # If not return anithing...
                raise ValueError(f'The entity "{entity_id}" does not exist.')

            entity = entity.json()
            if command not in entity:
                raise ValueError(f'The command "{command}" does not belong to "{entity_id}"')
            if entity[command]['type'].lower() != 'command':
                raise ValueError(
                    f'The command "{command}" of the entity "{entity_id}" must to be "command" type.'
                    f' It is "{entity[command]["type"]}"'
                )
            return entity['type'], action
        else:
            raise SyntaxError('Action format not supported. Must to be "entity.command".')

    @staticmethod
    def _parse_date(new_date):
        if isinstance(new_date, str):
            groups = re.match('^(\d{2})/(\d{2})/(\d{2}|\d{4})$', new_date)
            if groups is None:
                raise ValueError('The date format must be DD/MM/YYYY or DD/MM/YY')
            day, month, year = map(int, groups.groups())
            if year < 100:
                year += 2000
            new_date = datetime(year, month, day)
        elif not isinstance(new_date, datetime):
            raise ValueError('The date must be str or datetime')
        return new_date

    @staticmethod
    def _parse_time(new_hour):
        if isinstance(new_hour, str):
            if re.match('^\d{2}:\d{2}$', new_hour) is None:
                raise ValueError('The time format must be HH:MM')
            new_hour = datetime.strptime(new_hour, '%H:%M').time()
        elif not isinstance(new_hour, time):
            raise ValueError('The date must be str or time')

        return new_hour

    @property
    def rule(self):
        return self._rule_str

    @rule.setter
    def rule(self, new_rule):
        try:
            self._rule = Rule._parser.parse(Rule._lexer.lex(new_rule), self.headers)
            self._rule.eval()
        except LexingError:
            pass
        self._rule_str = new_rule

    @property
    def true(self):
        return self._true

    @true.setter
    def true(self, action):
        self._true_type, self._true = self._check_action(action)

    @property
    def false(self):
        return self._false

    @false.setter
    def false(self, action):
        self._false_type, self._false = self._check_action(action)

    @property
    def date_from(self):
        return self._date_from

    def set_date_from(self, new_date_from):
        self._date_from = self._parse_date(new_date_from)
        return self

    @property
    def date_to(self):
        return self._date_to

    def set_date_to(self, new_date_to):
        self._date_to = self._parse_date(new_date_to)
        return self

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    def set_schedule(self, start_time, end_time):
        self._start_time = self._parse_time(start_time)
        self._end_time = self._parse_time(end_time)
        return self

    def get_entities(self):
        """
        Gets each entity and attributes involved in the rule.
        :return: Entity ID list.
        """
        return {k: {"type": v["type"], "attrs": sorted(v['attrs'])}for k, v in self._rule.get_entities().items()}

    def eval(self):
        """
        Check if the rule is true or false.
        :return: True or False depending on the rule.
        """
        return self._rule.eval()

    def can_execute(self):
        """
        Check if is in date and in the programmed scheule (if exists).
        :return: True if can be executed, false otherwise.
        """
        assert (self.start_time is not None) == (self.end_time is not None), \
            'Must be informed the two hours, or none'
        now = datetime.now()  # Check if the rule can be executed
        if not (self.date_from <= now <= self.date_to):
            return False  # It would not be within the dates
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:  # it would not be within the established schedule
                if not (now.time() >= self.start_time or now.time() <= self.end_time):
                    return False
            else:
                if not (self.start_time <= now.time() <= self.end_time):
                    return False
        return True

    def execute(self):
        """
        If everithing is OK, evaluate the rule itself and execute the pertinent command
        :return: The result of evaluation if it can be executed, None otherwise.
        """
        if not self.can_execute():
            return None

        if result := self.eval():
            to_execute = self.true
            entity_type = self._true_type
        else:
            to_execute = self.false
            entity_type = self._false_type
        if to_execute is not None:
            entity_id, command = to_execute.split('.')

            payload = {
                "actionType": "update",
                "entities": [
                    {
                        "type": entity_type,
                        "id": entity_id,
                        command: {"type": "command", "value": ""}
                    }
                ]
            }
            post_headers = self.headers.copy()
            post_headers['Content-Type'] = 'application/json'
            res = requests.post(f'{orion_url}/v2/op/update', headers=post_headers, data=json.dumps(payload))
            if res.status_code != 204:
                raise ConnectionError(f'Error running the command. Status code: {res.status_code}')
        return result

    def subscribe(self):
        if self.subscription_id is not None:
            return False
        entities = self.get_entities()
        total_attrs = []
        total_nttys = []
        for entity, attrs in entities.items():
            total_attrs.extend(attrs['attrs'])
            total_nttys.append({'id': entity, 'type': attrs['type']})

        sub = {
            "description": "Subscription for a rule",
            "subject": {
                "entities": total_nttys,
                "condition": {
                    "attrs": total_attrs
                }
            },
            "notification": {
                "http": {
                    "url": f"{cepheid_url}/notify"
                },
                "attrs": total_attrs
            },
            "throttling": 5
        }
        post_headers = self.headers.copy()
        post_headers["Content-Type"] = "application/json"
        response = requests.post(f'{orion_url}/v2/subscriptions', data=json.dumps(sub), headers=post_headers)
        if response.status_code != 201:
            raise ConnectionError('Something went wrong when trying to add a subscription for a rule.')
        self.subscription_id = response.headers['Location'].split('/')[-1]
        return True

    def unsubscribe(self):
        if self.subscription_id is None:
            raise ValueError('Subscription ID is not defined')
        response = requests.delete(f'{orion_url}/v2/subscriptions/{self.subscription_id}', headers=self.headers)
        if response.status_code == 404:
            raise ValueError(f'The subscription {self.subscription_id} does not exists.')

        return response.status_code == 204

    def to_dict(self):
        the_dict = {'rule': self._rule_str, 'service': self.headers['Fiware-Service'], 'servicepath': self.headers['Fiware-ServicePath']}

        if self.true is not None: the_dict['true'] = self.true
        if self.false is not None: the_dict['false'] = self.false

        if self.true is not None: the_dict['true'] = self.true
        if self.false is not None: the_dict['false'] = self.false

        if self.date_from is not None: the_dict['date_from'] = self.date_from.strftime('%d/%m/%Y')
        if self.date_to is not None: the_dict['date_to'] = self.date_to.strftime('%d/%m/%Y')

        if self.start_time is not None: the_dict['start_time'] = self.start_time.strftime('%H:%M')
        if self.end_time is not None: the_dict['end_time'] = self.end_time.strftime('%H:%M')

        return the_dict

    def __str__(self):
        return self.rule

    def __eq__(self, other):
        if self.rule != other.rule: return False
        if self.headers != other.headers: return False

        if self.true != other.true: return False
        if self.false != other.false: return False

        if self.date_from != other.date_from: return False
        if self.date_to != other.date_to: return False

        if self.start_time != other.start_time: return False
        if self.end_time != other.end_time: return False

        return True

    def __hash__(self):
        return hash(str(self.to_dict()))

