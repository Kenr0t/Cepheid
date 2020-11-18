from bson import ObjectId
from pymongo import MongoClient

from Rule import Rule
from config import CEP_MONGO_HOST, CEP_MONGO_PORT, CEP_MONGO_DB


class RulesDB:
    instance = None

    _client = MongoClient(CEP_MONGO_HOST, int(CEP_MONGO_PORT))
    _rules_db = _client[CEP_MONGO_DB]['rules']

    def __new__(cls):
        if cls.instance is None:
            cls.instance = object.__new__(cls)
            if not any('subsId' in idx['name'] for idx in cls._rules_db.list_indexes()):
                cls._rules_db.create_index('subsId')
        return cls.instance

    def get_all(self, service: str, servicepath: str, in_json=False):
        if in_json:
            rules = []
            for r in self._rules_db.find({'service': service, 'servicepath': servicepath}):
                r['id'] = str(r.pop('_id'))
                rules.append(r)
            return rules
        else:
            return [Rule.from_dict(r) for r in self._rules_db.find({'service': service, 'servicepath': servicepath}, {'_id': False})]

    def insert(self, rule: Rule):
        """
        Save a rule to the database
        :param rule: The rule to persist.
        :return: The ObjectID string.
        """
        res = self._rules_db.insert_one(rule.to_dict())
        return str(res.inserted_id)

    def find_by_id(self, id, service: str, servicepath: str, in_json=False):
        rule = self._rules_db.find_one({'_id': ObjectId(id), 'service': service, 'servicepath': servicepath})
        if rule is None:
            return None
        if in_json:
            rule['id'] = str(rule.pop('_id'))
            return rule
        else:
            rule.pop('_id')
            return Rule.from_dict(rule)

    def find_by_subscription_id(self, subscription_id, service: str, servicepath: str):
        r = self._rules_db.find_one({'subsId': subscription_id, 'service': service, 'servicepath': servicepath}, {'_id': False})
        if r:
            return Rule.from_dict(r)
        return None

    def delete_by_id(self, id, service: str, servicepath: str):
        rule = self.find_by_id(id, service, servicepath)
        if not rule:
            return False
        rule.unsubscribe()
        return self._rules_db.delete_one({'_id': ObjectId(id), 'service': service, 'servicepath': servicepath}).deleted_count == 1

    def delete(self, rule: Rule):
        ids = []
        rules_in_db = []
        for r in self._rules_db.find({"rule": rule.rule}):
            ids.append(r.pop('_id'))
            rules_in_db.append(Rule.from_dict(r))

        if rule in rules_in_db:
            return self.delete_by_id(ids[rules_in_db.index(rule)], rule.headers['Fiware-Service'], rule.headers['Fiware-ServicePath'])
        return False

    def get_services(self):
        return [
            (service_pair['_id']['service'], service_pair['_id']['servicepath'])  # Tuple Service-ServicePath
            for service_pair in self._rules_db.aggregate(
                [{'$group': {'_id': {'service': '$service', 'servicepath': '$servicepath'}}}]
            )
        ]

    def __contains__(self, rule):
        rules_in_db = [Rule.from_dict(r) for r in self._rules_db.find({"rule": rule.rule}, {'_id': False})]
        return rule in rules_in_db

