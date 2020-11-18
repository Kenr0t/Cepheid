from Cepheid import Cepheid
from flask import Flask, Response

app = Flask(__name__)
cep = Cepheid()


@app.route('/version', methods=['GET'])
def version():
    return Response('Version 1.0', status=200)


cep.setup_notifiaciones(app)
cep.setup_crud(app)
# cep.ejecutar_reglas()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4013)

