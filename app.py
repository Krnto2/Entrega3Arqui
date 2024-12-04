from flask import Flask, request, jsonify
import componente 

app = Flask(__name__)

@app.route('/')
def index():
    return app.send_static_file('index.html') 


@app.route('/generar_gastos', methods=['POST'])
def generar_gastos():
    data = request.json
    año = data.get('año')
    mes = data.get('mes')
    monto = data.get('monto', 50000)
    return jsonify(componente.generar_gastos_comunes(año, mes, monto))

@app.route('/registrar_pago', methods=['POST'])
def registrar_pago():
    data = request.json
    departamento = data.get('departamento')
    año = data.get('año')
    mes = data.get('mes')
    fecha_pago = data.get('fecha_pago')
    return jsonify(componente.registrar_pago(departamento, año, mes, fecha_pago))

@app.route('/listar_pendientes', methods=['GET'])
def listar_pendientes():
    hasta_año = request.args.get('hasta_año', type=int)
    hasta_mes = request.args.get('hasta_mes', type=int)
    return jsonify(componente.listar_pendientes(hasta_año, hasta_mes))

@app.route('/consultar_gastos', methods=['GET'])
def consultar_gastos():
    departamento = request.args.get('departamento')
    return jsonify(componente.consultar_gastos_departamento(departamento))

if __name__ == '__main__':
    app.run(debug=True)
