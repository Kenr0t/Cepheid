import json
from logging import Logger

from flask import request, Response

from Rules_db import RulesDB, Rule
from config import default_service, default_servicepath

class Cepheid:
    instance = None

    rules = None
    set_de_reglas = None

    def __new__(cls):
        if cls.instance is None:
            cls.rules_db = RulesDB()

            cls.instance = object.__new__(cls)
        return cls.instance


    def ejecutar_reglas(self, evaluate_only=False):
        rules = [r for svc, svcP in self.rules_db.get_services() for r in self.rules_db.get_all(svc, svcP)]

        to_do = Rule.eval if evaluate_only else Rule.execute
        for r in rules:
            print(r.rule, '-->', to_do(r))

    def setup_notifiaciones(self, app):
        @app.route('/notify', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def notify():
            service = request.headers['Fiware-Service']
            servicePath = request.headers['Fiware-ServicePath']
            if request.data and 'subscriptionId' in request.json:
                datos = request.json
                rule = self.rules_db.find_by_subscription_id(datos['subscriptionId'], service, servicePath)
                rule.execute()
                return Response(status=200)
            return Response(status=404)

    def setup_crud(self, app):
        @app.route('/rules', methods=['POST'])
        def insert_rules():
            if not request.is_json:
                return Response(
                    '{"error": "UnsupportedMediaType", "description": "not supported content type: text/plain"}',
                    status=415, headers={"Content-Type": "application/json"})
            if 'Fiware-Service' not in request.headers or 'Fiware-ServicePath' not in request.headers:
                return Response(
                    '{"error": "UnsupportedMediaType", "description": "not supported content type: text/plain"}',
                    status=400, headers={"Content-Type": "application/json"})
            try:
                data = request.json
                data['service'] = request.headers.get('Fiware-Service', default_service)
                data['servicepath'] = request.headers.get('Fiware-ServicePath', default_servicepath)
                r = Rule.from_dict(data)
            except TypeError:
                err = '{"error": "ParseError", "description": "Errors found in incoming JSON buffer"}'
                return Response(json.dumps(err), status=400, content_type='application/json')
            except Exception as e:
                err = {"error": "ParseError", "description": str(e)}
                return Response(json.dumps(err), status=400, content_type='application/json')
            if r not in self.rules_db:
                r.subscribe()
                rule_id = self.rules_db.insert(r)
                if rule_id is None:
                    r.unsubscribe()
                    err = '{"error": "UnknownError", "description": "Something happened while inserting the rule"}'
                    return Response(json.dumps(err), status=500, content_type='application/json')
                return Response(status=200, headers={'Location': f'/rules/{rule_id}'})
            else:
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
                return Response(json.dumps(self.rules_db.get_all(service, servicepath, in_json=True)), status=200,
                                content_type='application/json')
            else:
                rule = self.rules_db.find_by_id(rule_id, service, servicepath, in_json=True)
                if rule:
                    return Response(json.dumps(rule), status=200, content_type='application/json')
                else:
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
                return Response(status=204, content_type='application/json')
            else:
                err_not_found = {
                    "error": "NotFound", "description": "The requested rule has not been found. Check id."
                }
                return Response(json.dumps(err_not_found), status=404, content_type='application/json')
