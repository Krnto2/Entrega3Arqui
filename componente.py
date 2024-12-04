import mysql.connector
from datetime import datetime
import json
from decimal import Decimal

# Conexión a base de datos por XAMPP
db_config = {
    'host': 'localhost',
    'user': 'root', 
    'password': '', 
    'database': 'gestion_gastos'
}

# Pasar los decimales a float
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Conectar a base datos
def get_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Completar los números
def format_department_id(depto_id):
    return str(depto_id).zfill(3)

# Validar fechas
def validar_fecha(fecha):
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# Generar gastos comunes
def generar_gastos_comunes(año, mes=None, monto_default=50000):
    año = int(año)  # Aseguramos que año es un entero
    conn = get_connection()
    cursor = conn.cursor()
    
    if not mes:  
        for m in range(1, 13):
            _generar_gastos_por_mes(cursor, año, m, monto_default)
    else:
        mes = int(mes)  # Convertir mes a entero si se proporciona
        _generar_gastos_por_mes(cursor, año, mes, monto_default)

    conn.commit()
    cursor.close()
    conn.close()
    return {"estado": "Gastos generados exitosamente"}

def _generar_gastos_por_mes(cursor, año, mes, monto_default):
    cursor.execute("SELECT id FROM departamentos")
    departamentos = cursor.fetchall()
    
    for (depto_id,) in departamentos:
        cursor.execute("""
            INSERT INTO gastos_comunes (departamento_id, año, mes, monto)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE monto = %s
        """, (depto_id, año, mes, monto_default, monto_default))

# Registrar pago
# Registrar pago con verificación de saldo
def registrar_pago(departamento, año, mes, fecha_pago):
    if not validar_fecha(fecha_pago):
        return {"estado": "Error", "mensaje": "Fecha inválida. Formato requerido: YYYY-MM-DD"}

    try:
        # Aseguramos que año y mes son enteros
        año = int(año)
        mes = int(mes)
    except ValueError:
        return {"estado": "Error", "mensaje": "Año o mes inválidos. Deben ser valores enteros."}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    departamento_id = format_department_id(departamento)

    # Consultar gasto y saldo disponible del departamento
    cursor.execute("""
        SELECT gc.id, gc.pagado, gc.monto, d.saldo
        FROM gastos_comunes gc
        JOIN departamentos d ON gc.departamento_id = d.id
        WHERE gc.departamento_id = %s AND gc.año = %s AND gc.mes = %s
    """, (departamento_id, año, mes))
    gasto = cursor.fetchone()

    if not gasto:
        cursor.close()
        conn.close()
        return {"estado": "Error", "mensaje": "Gasto no encontrado"}

    gasto_id, pagado, monto, saldo = gasto["id"], gasto["pagado"], gasto["monto"], gasto["saldo"]

    if pagado:
        cursor.close()
        conn.close()
        return {"estado": "Error", "mensaje": "El gasto ya fue pagado anteriormente."}

    if saldo < monto:
        cursor.close()
        conn.close()
        return {
            "estado": "Error",
            "mensaje": f"Saldo insuficiente. Saldo disponible: ${saldo:.2f}, Monto requerido: ${monto:.2f}."
        }

    # Calcular estado del pago (dentro del plazo o fuera del plazo)
    fecha_limite = datetime(año, mes, 15)
    fecha_pago_dt = datetime.strptime(fecha_pago, "%Y-%m-%d")
    dentro_del_plazo = fecha_pago_dt <= fecha_limite

    estado_pago = "Pago dentro del plazo" if dentro_del_plazo else "Pago fuera del plazo"
    mensaje = "El pago fue realizado correctamente." if dentro_del_plazo else "El pago fue aceptado, pero se realizó fuera del plazo establecido."

    # Actualizar el estado del gasto como pagado y descontar el saldo
    cursor.execute("""
        UPDATE gastos_comunes
        SET pagado = TRUE, mes_pago = %s
        WHERE id = %s
    """, (fecha_pago_dt.month, gasto_id))

    cursor.execute("""
        UPDATE departamentos
        SET saldo = saldo - %s
        WHERE id = %s
    """, (monto, departamento_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "estado": estado_pago,
        "mensaje": mensaje,
        "departamento": departamento_id,
        "fecha_pago": fecha_pago,
        "saldo_restante": saldo - monto
    }


# Listar pendientes
def listar_pendientes(hasta_año, hasta_mes):
    try:
        hasta_año = int(hasta_año)
        hasta_mes = int(hasta_mes)
    except ValueError:
        return {"estado": "Año o mes inválidos. Deben ser valores enteros."}

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Consulta con ORDER BY para orden numérico
    cursor.execute("""
        SELECT d.nombre AS departamento, gc.año, gc.mes, gc.monto
        FROM gastos_comunes gc
        JOIN departamentos d ON gc.departamento_id = d.id
        WHERE gc.pagado = FALSE AND (gc.año < %s OR (gc.año = %s AND gc.mes <= %s))
        ORDER BY gc.año ASC, gc.mes ASC
    """, (hasta_año, hasta_año, hasta_mes))
    pendientes = cursor.fetchall()

    for pendiente in pendientes:
        pendiente["monto"] = float(pendiente["monto"])  # Convertir monto a float

    cursor.close()
    conn.close()

    if not pendientes:
        return {"estado": "Sin montos pendientes"}
    return pendientes


# Consultar gastos de un departamento
def consultar_gastos_departamento(departamento):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    departamento_id = format_department_id(departamento)

    cursor.execute("""
        SELECT año, mes, monto, pagado, mes_pago
        FROM gastos_comunes
        WHERE departamento_id = %s
        ORDER BY año, mes
    """, (departamento_id,))
    gastos = cursor.fetchall()

    # Convertir el valor de 'pagado' a 'Sí' o 'No'
    for gasto in gastos:
        gasto["monto"] = float(gasto["monto"])
        gasto["pagado"] = "Sí" if gasto["pagado"] else "No"

    cursor.close()
    conn.close()

    if not gastos:
        return {"estado": "Sin registros"}
    return gastos

# Menú interactivo
def menu():
    while True:
        print("\n=== Gestión de Gastos Comunes ===")
        print("1. Generar gastos comunes")
        print("2. Registrar pago")
        print("3. Listar gastos pendientes")
        print("4. Consultar resumen de un departamento")
        print("5. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            año = input("Ingrese el año: ")
            mes = input("Ingrese el mes (opcional, presione Enter para todo el año): ")
            monto = input("Ingrese el monto por departamento: ")
            print(json.dumps(generar_gastos_comunes(año, mes, int(monto)), indent=4, cls=DecimalEncoder))
        elif opcion == "2":
            depto = input("Ingrese el número de departamento: ")
            año = input("Ingrese el año: ")
            mes = input("Ingrese el mes: ")
            fecha_pago = input("Ingrese la fecha de pago (YYYY-MM-DD): ")
            print(json.dumps(registrar_pago(depto, año, mes, fecha_pago), indent=4, cls=DecimalEncoder))
        elif opcion == "3":
            año = input("Ingrese el año: ")
            mes = input("Ingrese el mes hasta el cual desea listar pendientes: ")
            print(json.dumps(listar_pendientes(año, mes), indent=4, cls=DecimalEncoder))
        elif opcion == "4":
            depto = input("Ingrese el número de departamento: ")
            print(json.dumps(consultar_gastos_departamento(depto), indent=4, cls=DecimalEncoder))
        elif opcion == "5":
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida. Intente nuevamente.")

if __name__ == "__main__":
    menu()
