import json
import logging

from flask import request, Response

from Rules_db import RulesDB, Rule
from config import default_service, default_servicepath, CEP_MONGO_HOST

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)
logger.setLevel(logging.INFO)


class Cepheid:
    instance = None
    rules = None

    def __new__(cls):
        if cls.instance is None:
            logger.info('Connecting to database...')
            cls.rules_db = RulesDB()
            logger.info(f'Conected to MongoDB (Host: {CEP_MONGO_HOST})')
            cls.instance = object.__new__(cls)
        return cls.instance

    def ejecutar_reglas(self, evaluate_only=False):
        rules = [r for svc, svcP in self.rules_db.get_services() for r in self.rules_db.get_all(svc, svcP)]

        to_do = Rule.eval if evaluate_only else Rule.execute
        for r in rules:
            logger.info(f'{r.rule} --> {to_do(r)}')

    def setup_notifiaciones(self, app):
        @app.route('/notify', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def notify():
            service = request.headers['Fiware-Service']
            servicePath = request.headers['Fiware-ServicePath']
            if request.data and 'subscriptionId' in request.json:
                datos = request.json
                logger.info(f'Notification from a Subscription received. Subs. Id: {datos["subscriptionId"]}')
                rule = self.rules_db.find_by_subscription_id(datos['subscriptionId'], service, servicePath)
                rule.execute()
                return Response(status=200)
            elif request.data:
                logger.error(f'No subscriptionId in the request. {json.dumps(request.data, indent=4)}')
            else:
                logger.error(f'No data in the request.')
            return Response(status=404)

    def setup_crud(self, app):
        @app.route('/rules', methods=['POST'])
        def insert_rules():
            if not request.is_json:
                logger.error('Not json data in the content.')
                return Response(
                    '{"error": "UnsupportedMediaType", "description": "Not json data in the content"}',
                    status=415, headers={"Content-Type": "application/json"}
                )
            if 'Fiware-Service' not in request.headers or 'Fiware-ServicePath' not in request.headers:
                logger.error('Not supported content type: text/plain')
                return Response(
                    '{"error": "UnsupportedMediaType", "description": "not supported content type: text/plain"}',
                    status=400, headers={"Content-Type": "application/json"}
                )
            try:
                data = request.json
                data['service'] = request.headers.get('Fiware-Service', default_service)
                data['servicepath'] = request.headers.get('Fiware-ServicePath', default_servicepath)
                r = Rule.from_dict(data)
            except TypeError:
                err = '{"error": "ParseError", "description": "Errors found in incoming JSON buffer"}'
                logger.error('Errors found in incoming JSON buffer.')
                return Response(json.dumps(err), status=400, content_type='application/json')
            except Exception as e:
                logger.error(f'Error: {e}')
                err = {"error": "ParseError", "description": str(e)}
                return Response(json.dumps(err), status=400, content_type='application/json')
            if r not in self.rules_db:

                r.subscribe()
                rule_id = self.rules_db.insert(r)
                if rule_id is None:
                    r.unsubscribe()
                    logger.info(f'Rule cannot be inserted: {json.dumps(r.to_dict(), indent=4)}')
                    err = '{"error": "UnknownError", "description": "Something happened while inserting the rule"}'
                    return Response(json.dumps(err), status=500, content_type='application/json')
                logger.info(f'Rule inserted: {json.dumps(r.to_dict(), indent=4)}')
                return Response(status=200, headers={'Location': f'/rules/{rule_id}'})
            else:
                logger.warning(f'This rule already exists. Rule: {json.dumps(r.to_dict(), indent=4)}')
                err_msg = {
                    "error": "Already Exists",
                    "description": "The rule you are trying to insert already exitsts in the database."
                }
                return Response(json.dumps(err_msg), status=409, headers={"Content-Type": "application/json"})

        @app.route('/rules', methods=['GET'])
        @app.route('/rules/<rule_id>', methods=['GET'])
        def get_rules(rule_id=None):
            service = request.headers.get('Fiware-Service', default_service)
            servicepath = request.headers.get('Fiware-ServicePath', default_servicepath)

            if rule_id is None:  # Return all the rules
                logger.info('Returning all the Rules.')
                return Response(
                    json.dumps(self.rules_db.get_all(service, servicepath, in_json=True)),
                    status=200, content_type='application/json'
                )
            else:
                rule = self.rules_db.find_by_id(rule_id, service, servicepath, in_json=True)
                if rule:
                    logger.info(f'Returning the rule with id: {rule_id}.')
                    return Response(json.dumps(rule), status=200, content_type='application/json')
                else:
                    logger.warning(f'No rule with id {rule_id}.')
                    err_not_found = {
                        "error": "NotFound", "description": "The requested rule has not been found. Check id."
                    }
                    return Response(json.dumps(err_not_found), status=404, content_type='application/json')

        @app.route('/rules/<rule_id>', methods=['DELETE'])
        def delete_rules(rule_id):
            service = request.headers.get('Fiware-Service', default_service)
            servicepath = request.headers.get('Fiware-ServicePath', default_servicepath)

            result = self.rules_db.delete_by_id(rule_id, service, servicepath)
            if result:
                logger.info(f'Deleting the rule with id: {rule_id}.')
                return Response(status=204, content_type='application/json')
            else:
                logger.warning(f'No rule with id {rule_id}.')
                err_not_found = {
                    "error": "NotFound", "description": "The requested rule has not been found. Check id."
                }
                return Response(json.dumps(err_not_found), status=404, content_type='application/json')
