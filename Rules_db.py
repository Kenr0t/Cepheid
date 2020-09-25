import json

from bson import ObjectId

from Rule import Rule

from pymongo import MongoClient


class RulesDB:
    _client = MongoClient('localhost', 27017)
    _rules_db = _client['cepheid']['rules']

    def get_all(self):
        return [Rule.from_dict(r) for r in self._rules_db.find({}, {'_id': False})]

    def insert(self, rule: Rule):
        """
        Save a rule to the database. If the rule already exist, will do anithing and return None
        :param rule: The rule to persist.
        :return: The ObjectID string if the object has been persisted, None otherwise.
        """
        rules_in_db = [Rule.from_dict(r) for r in self._rules_db.find({"rule": rule.rule}, {'_id': False})]
        if rule not in rules_in_db:
            res = self._rules_db.insert_one(rule.to_dict())
            return str(res.inserted_id)
        return None

    def find_by_id(self, id):
        r = self._rules_db.find_one({'_id': id}, {'_id': False})
        if r:
            return Rule.from_dict(r)
        return None


    def find_by_subscription_id(self, subscription_id):
        r = self._rules_db.find_one({'subsId': subscription_id}, {'_id': False})
        if r:
            return Rule.from_dict(r)
        return None

    def delete_by_id(self, id):
        return self._rules_db.delete_one({'_id': ObjectId(id)}).deleted_count == 1

    def delete(self, rule: Rule):
        ids = []
        rules_in_db = []
        for r in self._rules_db.find({"rule": rule.rule}):
            ids.append(r.pop('_id'))
            rules_in_db.append(Rule.from_dict(r))

        if rule in rules_in_db:
            return self.delete_by_id(ids[rules_in_db.index(rule)])
        return False

