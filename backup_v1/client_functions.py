import json
import socket
import random

# dirección IP y puerto del servidor

server_host = '127.0.0.1'
server_tcp_port = 55558
server_udp_port = 55233

def request_list_udp(client_socket):

    # Si el socket no existe, es que se desconecto el cliente
    if not client_socket:
        # Imprimimos mensaje de error
        print("El socket se ha cerrado inesperadamente")
    else:
        # Diccionario que enviamos al servidor para solicitar la lista
        data = {"function": "return_list"}
        # Serializamos el diccionario con la funcion dumps de json
        data_json = json.dumps(data)
        # Enviamos todos los datos al server, codificados
        client_socket.sendto(data_json.encode(), (server_host, server_udp_port))


#Funcion para solicitar una lista de usuarios conectados al server
def request_list_tcp(client_socket):

    # Si el socket no existe, es que se desconecto el cliente
    if not client_socket:
        # Imprimimos mensaje de error
        print("El socket se ha cerrado inesperadamente")
    else:
        # Diccionario que enviamos al servidor para solicitar la lista
        data = {"function": "return_list"}
        # Serializamos el diccionario con la funcion dumps de json
        data_json = json.dumps(data)
        # Enviamos todos los datos al server, codificados
        client_socket.sendall(data_json.encode())

def quit_conn_udp(client_socket, username):
    # Usamos una excepcion para manejar los posibles errores
    try:
        # Enviamos un diccionario al server para que identifique que usuario quiere desconectarse
        data = {"function": "quit_conn",
                "user": username}
        # Serializamos los datos con la funcion dumps de json
        data_json = json.dumps(data)
        # Enviamos los datos, codificados
        client_socket.sendto(data_json.encode(), (server_host, server_udp_port))
    # Excepcion para imprimir el mensaje de error
    except ValueError as e:
        print(f"Error: {e}")


# Funcion para cerrar conexion con el cliente
def quit_conn_tcp(client_socket, username):
    # Si no existe el socket, entonces se cerro inesperadamente
    if not client_socket:
        # Imprimimos mensaje de error
        print("El socket se ha cerrado inesperadamente")
    else:
        # Usamos una excepcion para manejar los posibles errores
        try:
            # Enviamos un diccionario al server para que identifique que usuario quiere desconectarse
            data = {"function": "quit_conn",
                    "user": username}
            # Serializamos los datos con la funcion dumps de json
            data_json = json.dumps(data)
            # Enviamos los datos, codificados
            client_socket.sendall(data_json.encode())
        # Excepcion para imprimir el mensaje de error
        except ValueError as e:
            print(f"Error: {e}")

def send_message_udp(client_socket, to_user,message ,timestamp,from_user):
    data_ = {
        "function": "send_message",
        "to_user": to_user,
        "message": message,
        "from_user": from_user,
        "timestamp": timestamp
    }
    data_json_ = json.dumps(data_)
    client_socket.sendto(data_json_.encode(), (server_host, server_udp_port))

# Funcion para enviar mensajes al usuario deseado
def send_message_tcp(client_socket, to_user, _message,timestamp,from_user):

    # Usamos una excepcion para manejar posibles errores
    try:
        # Diccionario que contiene la funcion deseada, el usuario destino y el mensaje
        data = {
            "function": "send_message",
            "to_user": to_user,
            "message": _message,
            "from_user": from_user,
            "timestamp": timestamp
        }
        # Serializamos los datos con la funcion dumps de json
        data_json = json.dumps(data)
        # Enviamos el mensaje al servidor para que se lo envie al usuario destino
        client_socket.sendall(data_json.encode())
    # Excepcion, imprime el error
    except ValueError as e:
        print(f"Error: {e}")
        client_socket.close()

# Funcion para iniciar el cliente TCP
def init_client_tcp(username_arg):
    # Creacion del socket con protocolo TCP
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Usamos try para manejar las excepciones
    try:
        # Se conecta al server con el host y puerto especificados
        client.connect((server_host, server_tcp_port))
        # Imprimimos mensaje en consola que se conecto correctamente
        print("Successfully connected to server")
    # Excepcion que imprime el error
    except ValueError as e:
        print(f"Error: {e}")

    # Valida que el parametro usuario no este vacio
    if username_arg != '':

        # Envia al servidor el usuario
        client.sendall(username_arg.encode())
    # Devolvemos un objeto socket para usarlo en la interfaz y hacer peticiones
    return client

# Funcion para inicializar el cliente UDP
def init_client_udp(username_arg):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    host_client_udp = "127.0.0.1"
    port_client_udp = random.randint(8000, 9000)
    try:
        # Se conecta al server con el host y puerto especificados
        client.bind((host_client_udp, port_client_udp))
        # Imprimimos mensaje en consola que se conecto correctamente
        print("Successfully connected to server")

    # Excepcion que imprime el error
    except ValueError as e:
        print(f"Error: {e}")
    if username_arg != '':

        data = {
            "name":username_arg
        }
        data_json = json.dumps(data)
        client.sendto(data_json.encode(), (server_host, server_udp_port))

    return client



