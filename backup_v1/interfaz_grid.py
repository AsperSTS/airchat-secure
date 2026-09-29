import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import client_functions as cli
import datetime
import threading
import json


class ChatGui:

    def __init__(self):
        # Recibimos el nombre de usuario mediante un argumento en la ejecucion
        self.username_arg = None
        # Variable para guardar el chat actual
        self.actual_chat = None
        # Variable para almacenar el protocolo seleccionado
        self.protocol_selected = None

        # Guardamos el socket en un socket que nos servira para usarlo en la funcion
        self.cli_socket = None

        # Creamos un hilo para la funcion de escucha del cliente

        # Creamos la ventana principal o root
        self.root = tk.Tk()

        # Le ponemos titulo a la ventana
        self.root.title("Chat TCP/UDP")

        # Definimos el tamano de la venta en un formato de 1
        self.root.geometry("1062x600")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Crear un tema personalizado
        style = ttk.Style()

        # Establecer el color de fondo y de selección para los botones de radio
        style.map('TRadiobutton', background=[('selected', '#25D366'), ('!selected', '#3E3E3E')], foreground=[('selected', '#3E3E3E'), ('!selected', '#F8F8F8')])

        self.root_frame = tk.Frame(self.root)
        self.root_frame.grid(sticky="NSEW")

        # Definir la cantidad de columnas
        self.root_frame.columnconfigure(0, weight=1)
        self.root_frame.columnconfigure(1, weight=2)
        self.root_frame.rowconfigure(0, weight=1)

        # Crear el marco de la lista de chats
        self.chat_frame = tk.Frame(self.root_frame, bg="#F8F8F8")
        self.chat_frame.grid(column=0, columnspan=1, sticky="NSEW")

        # Definir la cantidad de columnas
        self.chat_frame.columnconfigure(0, weight=1)
        # Definir la cantidad de filas
        self.chat_frame.rowconfigure(0, weight=1)
        self.chat_frame.rowconfigure(1, weight=1)
        self.chat_frame.rowconfigure(2, weight=1)
        self.chat_frame.rowconfigure(3, weight=1)
        self.chat_frame.rowconfigure(4, weight=1)
        self.chat_frame.rowconfigure(5, weight=1)

        # Crear el marco para la entrada de usuarios
        self.user_input_frame = tk.Frame(self.chat_frame, bg="#7F7E7E")
        self.user_input_frame.grid(column=0, row=0, sticky="NSEW")

        self.user_input = tk.Entry(self.user_input_frame, bg="#3E3E3E", bd=3, font=("Courier New", 12), fg="#F8F8F8")
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=0)

        # Crear el marco para la entrada de usuarios
        self.protocol_frame = tk.Frame(self.chat_frame, bg="#7F7E7E")
        self.protocol_frame.grid(column=0, row=1, sticky="NSEW")

        # Definir la cantidad de columnas
        self.protocol_frame.columnconfigure(0, weight=1)
        self.protocol_frame.columnconfigure(1, weight=1)
        self.protocol_frame.columnconfigure(2, weight=1)
        self.protocol_frame.columnconfigure(3, weight=1)

        self.protocol_frame.rowconfigure(0, weight=1)
        self.protocol_frame.rowconfigure(1, weight=1)

        # Crear el radio button TCP
        self.protocolo = tk.StringVar()
        self.tcp_radio = ttk.Radiobutton(self.protocol_frame, text="TCP", variable=self.protocolo, value="tcp")
        self.tcp_radio.grid(column=0, row=0, sticky="NSEW")

        # Crear el radio button UDP
        self.udp_radio = ttk.Radiobutton(self.protocol_frame, text="UDP", variable=self.protocolo, value="udp")
        self.udp_radio.grid(column=1, row=0, sticky="NSEW")

        # Crea un boton para iniciar
        self.init_socket_button = tk.Button(self.protocol_frame, text="Iniciar", bg="#3E3E3E",  fg="white",
                                            font=("Courier New", 12), bd=0,command=self.validate_init_button)
        self.init_socket_button.grid(column=2, row=0, sticky="NSEW")

        # Crea un boton para refrescar la lista de usuarios
        self.refresh_list_button = tk.Button(self.protocol_frame, text="Actualizar lista", bg="#3E3E3E",
                                             fg="white",
                                             font=("Courier New", 12), bd=0, command=self.request_update_list)
        self.refresh_list_button.grid(columnspan=4, row=1, sticky="NSEW")
        self.refresh_list_button.config(state=tk.DISABLED)

        # Etiqueta para el chat
        self.chatlist_header = tk.Label(self.chat_frame, text="Lista de chats", font=("Courier New", 13),
                                        bg="#3E3E3E", padx=10, fg="#F8F8F8", pady=10)
        self.chatlist_header.grid(column=0, row=2, sticky="NSEW")
        self.chatlist_header.configure(justify="right")

        # Crear la lista de chats
        # #F8F8F8 es un color blanco ligero para la vista
        self.active_chat_list = tk.Listbox(self.chat_frame, bg="#292929", fg="#F8F8F8", bd=0, selectmode=tk.SINGLE,
                                           font=("Courier New", 13))
        self.active_chat_list.grid(column=0, row=3, sticky="NSEW")

        # Asociar la función on_chat_click() al evento <<ListboxSelect>>
        self.active_chat_list.bind("<<ListboxSelect>>", lambda event: self.on_chat_click(
            self.active_chat_list.get(self.active_chat_list.curselection())) if self.active_chat_list.curselection() else None)

        # Crear el encabezado para la lista de chats
        self.user_conn_header = tk.Label(self.chat_frame, text="Usuarios conectados",
                                         font=("Courier New", 13),
                                         bg="#3E3E3E", padx=10, fg="#F8F8F8", pady=10)
        self.user_conn_header.grid(column=0, row=4, sticky="NSEW")
        self.user_conn_header.configure(justify="right")

        # Crea la lista para ver los usuarios conectados
        self.connected_user_list = tk.Listbox(self.chat_frame, bg="#292929", fg="#F8F8F8", bd=0,
                                              selectmode=tk.SINGLE,
                                              font=("Courier New", 13))

        self.connected_user_list.grid(column=0, row=5, sticky="NSEW")

        self.connected_user_list.bind("<<ListboxSelect>>", lambda event: self.on_user_list_click(
            self.connected_user_list.get(
                self.connected_user_list.curselection())) if self.connected_user_list.curselection() else None)

        # Crear el marco de la ventana de mensajes
        self.message_frame = tk.Frame(self.root_frame, bg="#898888")
        self.message_frame.grid(column=1, row=0, sticky="NSEW")

        self.message_frame.columnconfigure(0,weight=1)

        # Definir la cantidad de filas
        self.message_frame.rowconfigure(0, weight=1)
        self.message_frame.rowconfigure(1, weight=3)
        self.message_frame.rowconfigure(2, weight=1)

        # Crear el encabezado del chat
        self.chat_history_header = tk.Label(self.message_frame, font=("Courier New", 13),
                                            bg="#3E3E3E", fg="#F8F8F8")

        self.chat_history_header.grid(row=0, sticky="NSEW", column=0)
        self.chat_history_header.configure(justify="center")

        # Crear el marco del historial de mensajes
        # , bg="#898888"
        self.message_history_frame = tk.Frame(self.message_frame)
        self.message_history_frame.grid(row=1, sticky="NSEW")

        # Crear un Scrollbar para el chat
        self.chat_scrollbar = tk.Scrollbar(self.message_history_frame)
        self.chat_scrollbar.pack(side="right", fill="y")

        # Crear un Canvas
        self.chat_canvas = tk.Canvas(self.message_history_frame)
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        # Creamos un widget Text para mostrar los mensajes
        self.message_history_text = tk.Text(self.chat_canvas, bg="#898888", font=("Courier New", 14), state="disabled")
        self.message_history_text.pack(fill="both", expand=True)
        # Configuramos el widget para mostrar de un lado los mensajes enviados, y de  otro los recibidos
        self.message_history_text.tag_configure("received", justify="left", background="lightgray")
        self.message_history_text.tag_configure("sent", justify="right", background="#3E3E3E", foreground="#F8F8F8")

        # Conectar el Scrollbar con el widget de texto
        self.chat_scrollbar.config(command=self.message_history_text.yview)
        self.message_history_text.config(yscrollcommand=self.chat_scrollbar.set)

        # Crear el marco de la entrada de texto y el botón de envío
        self.input_frame = tk.Frame(self.message_frame, bg="#7F7E7E")
        self.input_frame.grid(row=2, column=0, sticky="NSEW")

        # Crear la entrada de texto para escribir nuevos mensajes
        self.message_input = tk.Entry(self.input_frame, bg="#3E3E3E", bd=3, font=("Courier New", 13), fg="#F8F8F8")
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=0)

        # Crear el botón de envío para enviar nuevos mensajes
        self.send_button = tk.Button(self.input_frame, text="Enviar", bg="#3E3E3E", fg="white",
                                     font=("Courier New", 13), bd=0, command=self.validate_message_field)
        self.send_button.pack(side=tk.RIGHT)
        self.send_button.config(state=tk.DISABLED)

        # Agregamos el chat grupal
        self.connected_user_list.insert(tk.END, "Chat grupal")

        # Creamos un protocolo para cuando se cierre la ventana del programa
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.mainloop()

    def start_tcp_socket(self):
        self.protocol_selected = 'tcp'
        self.cli_socket = cli.init_client_tcp(self.username_arg)
        threading.Thread(target=self.listen_from_server_tcp, args=(self.cli_socket,)).start()
        self.refresh_list_button.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)

        # Deshabilitamos los botones que ya no utilizaremos
        self.udp_radio.configure(state='disabled')
        self.init_socket_button.config(state=tk.DISABLED)

        self.root.after(5000, self.request_update_list)

    def start_udp_socket(self):
        self.protocol_selected = 'udp'
        self.cli_socket = cli.init_client_udp(self.username_arg)
        threading.Thread(target=self.listen_from_server_udp, args=(self.cli_socket,)).start()

        self.refresh_list_button.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)

        # Deshabilitamos los botones que ya no utilizaremos
        self.tcp_radio.configure(state='disabled')
        self.init_socket_button.config(state=tk.DISABLED)
        self.root.after(5000, self.request_update_list)

    # Funcion para agregar usuarios conectados a la lista de chats
    def on_user_list_click(self, chat_name):
        # Validamos que no las tengamos en nuestra lista de chats
        if chat_name in [self.active_chat_list.get(idx) for idx in range(self.active_chat_list.size())]:
            # Mostramos un error si se intenta agregar dos veces un usuario
            messagebox.showerror("Error", "El usuario ya se encuentra en su lista de contactos")
        else:
            # Agregamos el usuario disponible a la lista de chats
            self.active_chat_list.insert(tk.END, chat_name)

    # Funcion para chatear con el usuario seleccionado
    def on_chat_click(self, chat_name):
        # Cambia el titulo del chat por el nombre del usuario seleccionado de la lista de chats
        self.chat_history_header.config(text=chat_name)
        # Cambiamos el valor del chat actual por el argumento chat_name
        self.actual_chat = chat_name

    def display_messages(self, from_user, message, timestamp):
        # Cambiamos el estado del historial de mensajes
        self.message_history_text.configure(state="normal")
        # Mostramos el mensaje recibido
        self.message_history_text.insert(tk.END, f"{from_user}: {message}\n",
                                         "received")
        # Mostramos la hora de envio
        self.message_history_text.insert(tk.END, f" {timestamp}\n", "received")
        # Configuramos el estado del historial de texto
        self.message_history_text.configure(state="disabled")

    # Funcion para actualizar los usuarios conectados en la interfaz
    def update_user_list(self, user_list):
        # Usamos excepciones para manejar los errores
        try:
            # Borramos la lista de usuarios conectados
            self.connected_user_list.delete(0, tk.END)
            # Insertamos siempre un chat grupal donde todos los conectados pueden hablar
            self.connected_user_list.insert(tk.END, "Chat grupal")
            # Recorremos la lista recibida del server
            for user in user_list:
                # Si el usuario de la lista no coincide con el del cliente
                if user != self.username_arg:
                    # Agregamos el usuario a la lista de usuarios conectados
                    self.connected_user_list.insert(tk.END, user)
        # Si hay excepcion, la imprimimos en terminal
        except ValueError as e:
            print(f"Error: {e}")

    # Funcion para agregar un usuario a la lista de chats
    def add_chat(self, nombre_usuario):
        # Insertamos un nuevo chat a la lista de chats
        self.active_chat_list.insert(tk.END, nombre_usuario)

    def close_socket(self, client_socket):
        client_socket.close()

    # Mapeo de protocolos a funciones de manejo
    protocol_handlers = {
        'tcp': start_tcp_socket,
        'udp': start_udp_socket

    }
    list_resquest_functions = {
        'tcp': cli.request_list_tcp,
        'udp': cli.request_list_udp
    }
    message_request_functions = {
        'tcp': cli.send_message_tcp,
        'udp': cli.send_message_udp
    }
    client_functions = {
        "user_list": update_user_list,
        "recv_message": display_messages,
        "quit": close_socket
    }
    on_closing_functions = {
        'tcp': cli.quit_conn_tcp,
        'udp': cli.quit_conn_udp
    }
    # Funcion para validad el tipo de socket seleccionado
    def validate_init_button(self):
        texto = self.user_input.get()
        if len(texto) > 0 and self.protocolo.get():
            self.username_arg = texto
            self.protocol_handlers[self.protocolo.get()](self)
            self.root.title(f"Usuario: {self.username_arg}")
            self.chat_history_header.configure(text=f"Bienvenido {self.username_arg}, selecciona un chat")
        else:
            messagebox.showerror("Error", "Ingresa un nombre de usuario valido")
    # Funcion para validar que exista un texto para enviar y que se haya seleccionado un chat
    def validate_message_field(self):
        # Obtenemos el mensaje a enviar
        text = self.message_input.get()
        # Verificamos que exista texto para enviar y que se haya seleccionado un chat
        if len(text) > 0 and self.actual_chat != '':
            # Si esta correcto, ejecutamos la funcion enviar mensaje y le pasamos sus parametros
            self.send_message_gui(text, self.actual_chat)

    # Funcion que solicita otra funcion del archivo cliente
    def request_update_list(self):
        # Solicita una lista de usuarios
        self.list_resquest_functions[self.protocol_selected](self.cli_socket)


    # Funcion que se ejecuta al cerrar la ventana de la intefaz
    def on_closing(self):
        # Destruimos la interfaz grafica
        self.root.after(0, self.root.destroy)
        """ Cerramos la conexion con el servidor, le pasamos los parametros necesarios
        @param self.cli socket es el objeto socket
        @param username_arg es el nombre del usuario
        """
        if self.protocol_selected  is not None:
            self.on_closing_functions[self.protocol_selected](self.cli_socket, self.username_arg)


    # Funcion para mandar mensajes
    def send_message_gui(self, text, actual_chat):

        # Eliminamos el mensaje del input
        self.message_input.delete(0, tk.END)
        """ Enviamos el mensaje al servidor
        @param self.cli_socket es el objeto socket
        @param self.actual_chat es el chat actual
        @param message es el contenido del mensaje
        """
        timestamp = datetime.datetime.now().strftime("%H:%M")
        self.message_request_functions[self.protocol_selected](self.cli_socket, actual_chat, text, timestamp, self.username_arg)

        # Configuramos el estado del historial de mensajes como normal
        self.message_history_text.configure(state="normal")
        # Mostramos el mensaje
        self.message_history_text.insert(tk.END, f"Yo: {text}\n", "sent")
        # Mostramos la hora de envio
        self.message_history_text.insert(tk.END, f" {timestamp}\n", "sent")
        # Desactivamos el historial de mensajes
        self.message_history_text.configure(state="disabled")

    def listen_from_server_udp(self, client_socket_udp):
        try:
            while True:
                message, _ = client_socket_udp.recvfrom(1024)
                data = json.loads(message.decode())
                if data["function"] == "user_list":
                    # Actualizamos la lista de usuarios conectados
                    self.client_functions[data["function"]](self, data["users"])

                elif data["function"] == "recv_message":
                    self.client_functions[data["function"]](self, data["from_user"], data["message"], data["timestamp"])

                elif data["function"] == "quit":
                    self.client_functions[data["function"]](self, client_socket_udp)
                    print("Sesion finalizada")
                    break
        except ValueError as e:
            print(f"Error: {e}")
            pass

    # Funcion para escuchar activamente los mensajes del servidor
    def listen_from_server_tcp(self, client_socket_tcp):
        # try para manejar la excepciones
        try:
            # Activamente escuchamos los mensajes del servidor
            while True:
                # Guardamos en data lo recibido
                data = client_socket_tcp.recv(1024).decode()
                # Invertimos la serializacion
                data = json.loads(data)
                # Validamos que nos devolvio el servidor
                if data["function"] == "user_list":
                    # Actualizamos la lista de usuarios conectados
                    self.client_functions[data["function"]](self, data["users"])

                elif data["function"] == "recv_message":
                    self.client_functions[data["function"]](self, data["from_user"], data["message"], data["timestamp"])

                elif data["function"] == "quit":
                    self.client_functions[data["function"]](self, client_socket_tcp)
                    print("Sesion finalizada")
                    break
        except ValueError as e:
            print(f"Error: {e}")
            pass

def main():

    # Crear un objeto ChatGui y le pasamos como parametro el objeto socket
    ChatGui()


if __name__ == '__main__':
    main()
