import socket
import threading
import queue
import json
import datetime

# dirección IP y puerto de escucha del servidor
host = '127.0.0.1'
port_tcp = 55558
port_udp = 55233

messages = queue.Queue()

# diccionario para almacenar los clientes conectados
tcp_clients = {}
udp_clients = {}

def receive_udp(server):
    while True:
        try:
            message, addr = server.recvfrom(1024)
            messages.put((message,addr))
        except:
            pass
def return_list(socket_udp,addr):
    usernames_list_cli = []
    # Iteramos sobre las claves del diccionario de los clientes
    for client in udp_clients:
        # Rellenamos la lista con los clientes
        usernames_list_cli.append(client)
    # Diccionario que corresponde a una lista de clientes conectados
    response_data = {
        "function": "user_list",
        "users": usernames_list_cli
    }
    # Enviamos los datos serializados y codificados al cliente
    socket_udp.sendto(json.dumps(response_data).encode(),addr)

# Funcion para devolver una lista de uusarios conectados
def return_list_tcp(conn):
    usernames_list_cli = []
    # Iteramos sobre las claves del diccionario de los clientes
    for client in tcp_clients:
        # Rellenamos la lista con los clientes
        usernames_list_cli.append(client)
    # Diccionario que corresponde a una lista de clientes conectados
    response_data = {
        "function": "user_list",
        "users": usernames_list_cli
    }
    # Enviamos los datos serializados y codificados al cliente
    conn.sendall(json.dumps(response_data).encode())
# Funcion para cerrar conexion con un usuario

def quit_conn_udp(socket_udp, addr,username):
    # Diccionario que corresponde a un mensaje de salida para el cliente
    response_data = {
        "function": "quit"}
    # Serializamos el diccionario
    response_data_json = json.dumps(response_data)
    # Enviamos el diccionario codificado al cliente
    socket_udp.sendto(response_data_json.encode(),addr)
    del udp_clients[username]
def quit_conn_tcp(conn, username):
    # Diccionario que corresponde a un mensaje de salida para el cliente
    response_data = {
        "function": "quit"}
    # Serializamos el diccionario
    response_data_json = json.dumps(response_data)
    # Enviamos el diccionario codificado al cliente
    conn.sendall(response_data_json.encode())
    # Cerramos la conexion con el cliente
    conn.close()
    # Eliminamos al cliente del diccionario de conexiones
    del tcp_clients[username]

def send_message_udp(socket_udp,_message,from_user,to_user,addr,timestamp):
    for name, user_address in udp_clients.items():
        if name == to_user:
            data_to = {
                "function": "recv_message",
                "to_user": to_user,
                "from_user": from_user,
                "message": _message,
                "timestamp": timestamp
            }
            data_to_json = json.dumps(data_to)
            time_text = datetime.datetime.now().strftime("%H:%M:%S")
            socket_udp.sendto(data_to_json.encode(), user_address)
            print(f"[{time_text}] : {addr[0]}:{addr[1]}: to {user_address[0]} : {user_address[1]} : {_message}")
            break

# Funcion para enviar mensajes entre clientes
def send_message_tcp( _message, to_user, from_user,timestamp):
    # Diccionario con la informacion sobre un mensaje para un usuario
    response_data = {
        "function": "recv_message",
        "to_user": to_user,
        "from_user": from_user,
        "message": _message,
        "timestamp": timestamp
    }
    # Buscamos el cliente destino en la lista de clientes conectados
    if  to_user in tcp_clients:
        # Guardamos la conexion del cliente en @to_conn
        to_conn = tcp_clients[ to_user]
        # Serializamos el diccionario
        response_data_json = json.dumps(response_data)
        # Enviamos un diccionario al cliente destino, codificado
        to_conn.sendall(response_data_json.encode())

def send_grupal_udp(socket_udp, _message, from_user,timestamp):
    data_to = {
        "function": "recv_message",
        "from_user": "(Grupal) : "+from_user,
        "message": _message,
        "timestamp": timestamp
    }
    data_to_json = json.dumps(data_to)
    for name, user_address in udp_clients.items():
        socket_udp.sendto(data_to_json.encode(), user_address)

# Funcion para enviar mensajes a todos los usuarios conectados
def send_grupal_tcp(conn, _message, from_user,timestamp):
    # Diccionario con la informacion sobre un mensaje para todos los usuarios
    response_data = {
        "function": "recv_message",
        "from_user": "(Grupal) : "+from_user,
        "message": _message,
        "timestamp": timestamp
    }
    # Serializamos el diccionario
    response_data_json = json.dumps(response_data)
    # Recorremos el diccionario de conexiones
    for client in tcp_clients.values():
        # Si su conexion existe
        if client != conn:
            # Le enviamos el mensaje recibido, codificado
            client.sendall(response_data_json .encode())
# Diccionario que contiene las funciones del servidor

def broadcast_udp(socket_udp):
    while True:
        while not messages.empty():
            message, addr = messages.get()
            time_text = datetime.datetime.now().strftime("%H:%M:%S")

            print(f"[{time_text}] :  {addr[0]} : {addr[0]}.")

            if addr not in udp_clients.values():
                data = json.loads(message.decode())
                name = data['name']
                udp_clients[name] = addr
                print(f"[{time_text}] : [{name}] joined! [{addr[0]}] : [{addr[1]}]")
            else:
                data = json.loads(message.decode())
                if data["function"] == "return_list":
                    return_list(socket_udp, addr)
                    time_text = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{time_text}] : [LIST] ")
                elif data["function"] == "send_message":
                    if data["to_user"] == "Chat grupal":
                        # Obtenemos el mensaje
                        cli_message = data["message"]
                        from_user = data["from_user"]

                        timestamp = data["timestamp"]
                        # Enviamos mensajes a todos los usuarios conectados
                        send_grupal_udp(socket_udp, cli_message, from_user,timestamp)
                        # Imprimimos en la consola del servidor
                        print(f"[{time_text}] : [{from_user}] : [GRUPAL] : [ENVIADO]")
                    # Si el cliente quiere enviar un mensaje privado
                    else:
                        _message = data["message"]
                        from_user = data["from_user"]
                        to_user = data["to_user"]
                        timestamp = data["timestamp"]
                        send_message_udp(socket_udp,_message,from_user,to_user,addr,timestamp)

                elif data["function"] == "quit_conn":
                    user_from = data["user"]
                    quit_conn_udp(socket_udp,addr,user_from)
                    time_text = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{time_text}] : [{user_from}] : [QUIT]")
                    # Rompemos el ciclo



# Funcion para manejar un hilo de un cliente
def handle_client_tcp(conn, addr):
    # Recibe el nombre de usuario de un cliente
    username = conn.recv(1024).decode()
    # Obtenemos la fecha de la conexion
    time_text = datetime.datetime.now().strftime("%H:%M:%S")
    # Imprimimos en el servidor
    print(f"[{time_text}] : [NUEVA CONEXIÓN] {username} : {addr} conectado al servidor.")

    # Añade al cliente a la lista de clientes conectados
    if username != '':
        tcp_clients[username] = conn
        # Continuamente esperamos mensajes del cliente
        while True:
            # try para manejar excepciones
            try:
                # Espera a recibir un mensaje del cliente
                json_message = conn.recv(1024).decode()
                # Invierte la serializacion del mensaje
                data = json.loads(json_message)
                # Revisamos que es lo que necesita el cliente

                if(data["function"] == "return_list"):
                    # Devolvemos una lista de usuarios conectados al cliente
                    return_list_tcp(conn)
                    # Obtenemos el momento de la peticion
                    time_text = datetime.datetime.now().strftime("%H:%M:%S")
                    # Imprimimos en la consola del servidor
                    print(f"[{time_text}] : [{username}]    : [LIST]")

                elif(data["function"] == "quit_conn"):
                    # Cerramos la conexion con el cliente que lo solicita
                    quit_conn_tcp(conn, username)
                    # Guardamos el usuario del cliente que solicita la desconexion
                    username = data["user"]
                    # Obtenemos el momento de la peticion
                    time_text = datetime.datetime.now().strftime("%H:%M:%S")
                    # imprimimos en la consola del servidor
                    print(f"[{time_text}] : [{username}] : [QUIT]")
                    # Rompemos el ciclo
                    break

                elif(data["function"] == "send_message"):
                    # Si el cliente esta en el chat grupal
                    if data["to_user"] == "Chat grupal":
                        # Obtenemos el mensaje
                        cli_message = data["message"]
                        timestamp = data["timestamp"]
                        # Enviamos mensajes a todos los usuarios conectados
                        send_grupal_tcp(conn, cli_message, username,timestamp)
                        # Imprimimos en la consola del servidor
                        print(f"[{time_text}] : [{username}] : [GRUPAL] : [ENVIADO]")
                        # Si el cliente quiere enviar un mensaje privado
                    else:
                        # Obtenemos el usuario destino
                        to_user = data["to_user"]
                        # Obtenemos el mensaje
                        cli_message = data["message"]
                        # Obtenemos el momento de la peticion
                        timestamp = data["timestamp"]
                        # Enviamos el mensaje al cliente destino
                        send_message_tcp(cli_message, to_user, username, timestamp)
                        # Imprimimos en el servidor la peticion
                        time_text = datetime.datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] : [{username}] : [{to_user}] : [ENVIADO]\n")
            # Excepcion que imprime el error
            except ValueError as e:
                print(f"Error: {e}")
                # si hay un error de conexión, cierra la conexión y elimina al cliente de la lista de clientes conectados
                conn.close()
                # Elimina al usuario de la lista de clientes
                del tcp_clients[username]
                # Imprime en el la consola del servidor
                print(f"[DESCONEXIÓN] {username} ha abandonado la sala de chat.")
                # Rompemos el ciclo
                break

# Funcion para iniciar el servidor
def start_server_tcp():
    """Inicia el servidor."""
    # crea el socket del servidor y lo pone en modo de escucha
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host,port_tcp))
    # Escuchamos activamente en el puerto y la direccion dadas
    server.listen()
    # Obtenemos el momento de la inicializacion
    time_text = datetime.datetime.now().strftime("%H:%M:%S")
    #
    print(f"[{time_text}] : [SERVIDOR TCP INICIADO] El servidor está escuchando en {host}:{port_tcp}.")
    # Activamente aceptamos nuevas conexiones
    while True:
        # Acepta una nueva conexión
        conn, addr = server.accept()

        # Crea un hilo para manejar la conexión del cliente
        threading.Thread(target=handle_client_tcp, args=(conn, addr)).start()
def start_server_udp():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        server.bind((host, port_udp))
    except ValueError as e:
        print(f"Error: {e}")

    # Obtenemos el momento de la inicializacion
    time_text = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{time_text}] : [SERVIDOR UDP INICIADO] El servidor está escuchando en {host}:{port_udp}.")

    threading.Thread(target=receive_udp, args=(server,)).start()
    threading.Thread(target=broadcast_udp, args=(server,)).start()



if __name__ == '__main__':
    # inicia el servidor
    threading.Thread(target=start_server_tcp).start()
    threading.Thread(target=start_server_udp).start()