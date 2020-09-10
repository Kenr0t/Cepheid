from datetime import datetime, time
from typing import Union
import json
import re

import requests

from Compiler import Lexer, Parser, LexingError
from config import orion_url, get_headers, post_headers, iota_url


class Rule:
    _lexer = Lexer()
    _parser = Parser()

    def __init__(
        self, rule: str, true: str = None, false: str = None,
        date_from: Union[datetime, str] = datetime.min, date_to: Union[datetime, str] = datetime.max,
        start_time: Union[time, str] = None, end_time: Union[time, str] = None
    ):
        self.rule = rule
        self.true, self.false = true, false
        self.date_from, self.date_to = date_from, date_to
        if start_time is not None and end_time is not None:
            self.start_time, self.end_time = start_time, end_time
        elif not (start_time is None and end_time is None):
            raise ValueError('Must be informed the two hours, or none')
        else:
            self._start_time, self._end_time = None, None

    @staticmethod
    def _check_action(action):
        if action is None:
            return None, None
        if re.match(r'[a-zA-Z_]\w+\.[a-zA-Z_]\w+$', action):  # Must tu have the format entity.command
            entity_id, command = action.split('.')

            entity = requests.get(url=f'{orion_url}/v2/entities/{entity_id}', headers=get_headers)

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
        return self.rule_str

    @rule.setter
    def rule(self, new_rule):
        try:
            self._rule = Rule._parser.parse(Rule._lexer.lex(new_rule))
            self._rule.eval()
        except LexingError:
            pass
        self.rule_str = new_rule

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

    @date_from.setter
    def date_from(self, new_date_from):
        self._date_from = self._parse_date(new_date_from)

    @property
    def date_to(self):
        return self._date_to

    @date_to.setter
    def date_to(self, new_date_to):
        self._date_to = self._parse_date(new_date_to)

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, new_start_time):
        self._start_time = self._parse_time(new_start_time)

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, new_end_time):
        self._end_time = self._parse_time(new_end_time)

    def get_entities(self):
        return self._rule.get_entities()

    def eval(self):
        return self._rule.eval()

    def execute(self):
        assert (self.start_time is not None) == (self.end_time is not None), \
            'Must be informed the two hours, or none'
        now = datetime.now()  # Check if the rule can be executed
        if not (self.date_from <= now <= self.date_to):
            return  # It would not be within the dates
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:  # it would not be within the established schedule
                if not (now.time() >= self.start_time or now.time() <= self.end_time):
                    return
            else:
                if not (self.start_time <= now.time() <= self.end_time):
                    return

        if result := self.eval():  # At this point, we can check the rule itself
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
            res = requests.post(f'{orion_url}/v2/op/update', headers=post_headers, data=json.dumps(payload))
            if res.status_code != 204:
                raise ConnectionError(f'Error running the command. Status code: {res.status_code}')
        return result

    def to_dict(self):
        the_dict = {'rule': self.rule_str}
        if self.true is not None: the_dict['true'] = self.true
        if self.false is not None: the_dict['false'] = self.false

        if self.date_from is not None: the_dict['date_from'] = self.date_from.strftime('%d/%m/%Y')
        if self.date_to is not None: the_dict['date_to'] = self.date_to.strftime('%d/%m/%Y')

        if self.start_time is not None: the_dict['start_time'] = self.start_time.strftime('%H:%M')
        if self.end_time is not None: the_dict['end_time'] = self.end_time.strftime('%H:%M')

        return the_dict

    def __str__(self):
        return self.rule
