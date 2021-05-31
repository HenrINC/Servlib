##I know, comments are in frenc instead of english, i'll change it tomorrow



##Iportation des librairies standrds de python
import socket #Pour les connexions tcp/http
import _thread as thread #Pour géréer chaque client indépenament
import urllib.parse #Pour analyser les requetes http
import json #Pour manipuler des dictionnaires contennus dans des fichier json
import time #Pour ajouter un unité de temps au logs
import sys #Pour la configuration et le démarrage en lignes de comande
import os #Effectuer des opération sur l'os
import random #Pour les salt du hachage et les codes de sessions
import hashlib #Pour le hashage des mdps et des cookies


##Impoprt des librairies tierces
import ftfy #Pour résoudre des problèmes d'encodage


def salthash(string,salt):
    if type(string) == str: string = string.encode("utf-8")
    if type(salt) == bytes: salt = salt.decode("utf-8")
    return hashlib.sha256(string+salt.encode("utf-8")).hexdigest()+salt+"l"+str(len(salt))

def salthash_verify(crypted_string,string):
    if type(string) == str: string = string.encode("utf-8")
    if type(crypted_string) == bytes: crypted_string = crypted_string.decode("utf-8")
    salt = crypted_string[-(int(crypted_string.split("l")[-1])+1+len(crypted_string.split("l")[-1])):-(1+len(crypted_string.split("l")[-1]))]
    return crypted_string == salthash(string, salt)
def random_salt():
    return hashlib.sha256(str(random.choice([-1,1])*random.randint(1,99999)/random.randint(1,99999)).encode("utf-8")).hexdigest()


def trash_truck(target = ["sessions"]): #Supprime tout les fichiers teporaires utilisés par le serveur
    if "sessions" in target: #Supprime les sessions âgées de plus de 1000 secondes
        for i in os.listdir("sessions"):
            try:
                with open(f"sessions/{i}","r") as session:session = json.load(session)
                if session["last_use"]+1000 < time.time():
                    os.remove(f"sessions/{i}")
            except Exception as e:
                print(f"ERROR while clearing {i} with error {e}\n",end="")
                os.remove(f"sessions/{i}")

          
def prepare(path,headers=[]):
    with open("content-types.json") as content_types: headers.append("Content-Type: "+json.load(content_types)[path.split(".")[-1]])
    with open(path,"rb") as file:
        response = b"HTTP/1.1 200 OK\n"
        for i in headers:
            response += i.encode("utf-8")+b"\n"
        response += b"\n"+file.read()
    return response
        

def parse(request):
    def extract(data):
        form = {}
        for i in data.split("&"):
            i = i.split("=")
            try: form.update({i[0]: i[1]})
            except:
                if i[0] != "None": form.update({i[0]: i[0]})
        return form
        
    request = ftfy.fix_text(urllib.parse.unquote(request.decode("utf-8")))
    #print(f"Request:{request}\n",end="")
    data = {"GET":{}, #Les informations contennues dans l'url après le séparateur '?'
            "POST":{}, #Les informations en bas de requète 
            "method":"", #La méthode d'envoi des données (POST/GET)
            "path":"", #Le chemin de la page à envoyer
            "path_dir":"", #Le répertoire de la page à envoyer (utile côté page en .py pour tout ce qui est accès au db en sqlite3 par exemple)
            "subdomain":"", #Le sous-dommaine
            }
    ##GET et POST sont en majuscule pour permettre de faire data[data["method"]]
    
    data["method"] = request.split(" ")[0]
    
    data["path"] = request.split("HTTP")[0].split(data["method"])[1][1:-1]
    
    if data["method"] == "POST": data["POST"] = extract(request.split("\n")[-1])

    if "?" in data["path"]: #Si l'url contient des données pour GET
        data["GET"] = extract(data["path"].split("?",1)[1])
        data["path"] = data["path"].split("?",1)[0] #Nouveau chemin sans les données pour GET

    data["path_dir"] = data["path"].rsplit("/",1)[0]+"/" #On ne définis pas path_dir avant au cas où path est modifié par l'extract de GET

    for i in request.split("\n"): #Ajoute les headers au dictionnaire
        i = i.split(": ",1)
        if len(i)==2: data.update({i[0]:i[1]})

    data["subdomain"] = data["Host"][:-len(data["Host"].split(".",len(data["Host"].split("."))-2)[-1])-1]

    if "Cookie" in data: #Si les headres contiennent des cookies
        cookies = {}
        for i in data["Cookie"].split(";"):
            i = i.lstrip(" ").split("=")
            cookies.update({i[0]:i[1]})
        data["Cookie"] = cookies #Replace les données du header "Cookie" par un dictionnaire plus simple

    return data

    
class DictBase():
    """
A class created to simplify the edditing of an sqlite3 db in python
"""
    def __init__(self,data_base,table):
        self.db = data_base
        self.table = table
        self.cursor = self.db.cursor()
    def load(self):
        """
Return a dict object containing all the informations in the table
"""
        rows = self.cursor.execute(f"SELECT * FROM {self.table}").fetchall()
        headers = self.cursor.execute(f"PRAGMA table_info({self.table})").fetchall()
        dict_list = []
        for row in rows:
            row_dict = {}
            for i in range(len(headers)):
                row_dict.update({headers[i][1]:row[i]})
            dict_list.append(row_dict)
        return dict_list
    def select(self,name,value):
        return_list = []
        for i in self.load():
            if i[name] == value: return_list.append(i)
        return return_list
    def insert(self,data):
        names = ""
        values = []
        for i in data:
            names += ","+str(i)
            values.append(data[i])
        self.cursor.execute(f"INSERT INTO {self.table}({names[1:]}) VALUES({(',?'*len(data))[1:]})",tuple(values))
        return self
    def primary(self):
        primaries = []
        for i in self.cursor.execute(f"PRAGMA table_info({self.table})").fetchall():
            if i[5] == 1: primaries.append(i[1])
        return primaries
    def sort(self,key):
        sorted_dict = {}
        for i in self.load():
            sorted_dict.update({i[key]:i})
        return sorted_dict

class Session(dict): #Partiellement copié depuis servlib5
    """
Permet de gérer une session d'utilisateur comparable à celles du PHP
"""
    def smart_connect(data): #Smart_connect remplace l'ip par un code généré coté serveur comme décrit dans root/new_session_system
        try:
            sess = Session(data["Cookie"]["sessid"]).load()
            for i in ["User-Agent","IP"]:
                if sess[i] != data[i]: raise Exception("Spoffing spotted") #On lance une exception si on détecte un changement de user-agent ou d'IP de l'utilisateur
            return sess
        except:
            print("GENERATING_SESSION")
            while True:
                code = str(random.randint(0,10000))
                if code not in os.listdir("sessions"): break
            return Session(code,{"User-Agent":data["User-Agent"],"IP":data["IP"]}).dump()
        
    def __init__(self,code,data = {}):
        self.code = code
        self.last_use = time.time()
        self["last_use"] = self.last_use
        self.update(data)
    def dump(self):
        with open("sessions/"+self.code+".json","w") as file: json.dump(self,file)
        return self
    def load(self):
        with open("sessions/"+self.code+".json","r") as file: self.update(json.load(file))
        return self
        



class Response(): #Partiellement copié depuis servlib5
    """
Response n'est pas vital pour  le serveur.
En effet, il est seulement là pour simplifier l'écriture des pages en .py
Il est d'ailleurs plustôt mal optimisé
Cependant, il permet de créer une réponse http avec un minimum d'informations
"""
    def __init__(self,content="",headers=[],code="200 OK"):
        self.content = content
        self.headers = headers
        self.code = code
    def encode(self, encoding = False):
        if encoding:
            if "<head>" in self.content: self.content = self.content.replace("<head>", f"""<head>\n<meta http-equiv="Content-Type" content="text/html; charset={encoding}" />""")
            else: self.content = self.content.replace("<html>", f"""<html><head>\n<meta http-equiv="Content-Type" content="text/html; charset={encoding}" /></head>""")
        else: encoding = "utf-8"
        if (self.headers == []) and ("<html>" in self.content): self.headers = ["Content-Type: text/html"]
        if ("Content-Type: text/html" in self.headers) and (not self.content.startswith("\n")): self.content = "\n"+self.content
        response = f"HTTP/1.1 {self.code}\n"
        for i in self.headers:
            response += i.strip("\n") + "\n"
        if type(self.content) == str: return (response+self.content).encode(encoding)
        elif type(self.content) == bytes: return response.encode(encoding)+self.content
        else: return (response+"\n<html><head><title>ERROR</title></head><body><h1>ERROR</h1></body></html>").encode(encoding)
    def add_cookie(self,cookie):
        if type(cookie) == str: self.headers.append(cookie)
        elif type(cookie) == dict:
            temp_cookie = "Set-Cookie: "
            for i in cookie: temp_cookie += "{0}={1}; ".format(i,cookie[i])
            self.headers.append(temp_cookie.strip("; "))
        elif type(cookie) == list:
            for i in cookie: self.add_cookie(i)
    def create_session(self,data):
        sess = Session.smart_connect(data)
        try:
            if data["Cookie"]["sessid"] == sess.code: pass
            else: self.add_cookie({"sessid":sess.code})
        except: self.add_cookie({"sessid":sess.code})
        return sess


class Server():
    def __init__(self,address = "", port = 80, root = "root", log = "log.txt", cs_compatibility = True):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Cré le socket
        self.socket.bind((address,port)) #Lie le socket à l'adresse et au port en argument de la fonction
        self.listening = False #Le socket n'est pas enore en train d'écouter
        self.root = root #root est la racine du site cela permet de créer un site dans un répertoire différent du serveur /!\ Le serveur devra quand meme etre lancé depuis son répertoire 
        with open("content-types.json","r") as file: self.content_types = json.load(file) #liste des content-type supportés par le serveur
        self.log_path = log
        self.cs_compatibility = cs_compatibility
        #if cs_compatibility: thread.start_new_thread(atriumC,())#Demarre atriumC, un serveur tcp de comunication interlanguagière c#/python
            
        
    def listen(self,queue):
        self.listening = True #Le socket est maintenant en train d'écoueter
        self.socket.listen(int(queue)) #Défini la longeure maximale de la fille d'attente
        with open(self.log_path,"a+") as self.log:
            self.log.write(f"[{time.ctime(time.time())}] Starting listening...\n")
            while self.listening: thread.start_new_thread(self.client_thread,self.socket.accept()) #Cré un thread pour s'occuper du client créé par socket.accept tout en continuant d'écouter
            self.log.write(f"[{time.ctime(time.time())}] Ending listening\n")
    def client_thread(self,client,address):
        thread.start_new_thread(trash_truck,())
        print(f"[{time.ctime(time.time())} : {address}] Starting thread...\n",end="") #Dans un thread, print est un peu perdu, il faut donc ajouter le \n manuellement pour des raisons d'affichage
        self.log.write(f"[{time.ctime(time.time())} : {address}] Starting thread...\n")
        with client: #Ferme automatiquement le client à la fin du thread
            data = client.recv(1024) #Récupère les données envoyées par le thread client
            if data:
                data = parse(data)
                data.update({"IP":address[0],"root":self.root})

                try:
                    exinfo = self.custom_thread(self, data)
                    if type(exinfo) == dict: data = exinfo
                except: print("NO_CUSTOM_THREAD",sys.exc_info())
                
                print(f"[{time.ctime(time.time())} : {address}] Data: {data}\n",end="")
                self.log.write(f"[{time.ctime(time.time())} : {address}] Data: {data}\n")
                #if "command" in {**data["GET"],**data["POST"]}:exec({**data["GET"],**data["POST"]}["command"]) ##DEV UNIQUEMENT permet d'executer du code côté serveur
                
                ##http://localhost/?command=setattr(self,%22listening%22,False) -> arrete le serveur

                if data["subdomain"] != "" and "subdomains_roots" in dir(self):
                    if data["subdomain"] in self.subdomains_roots:
                        data["root"] = self.subdomains_roots[data["subdomain"]]
                        

                if data["path"] == "/" and "homepage" in dir(self): data["path"] = self.homepage
                print("path:"+data["path"])
                try:
                    if "authorized_ip.json" in os.listdir((data["root"]+data["path_dir"]).strip("/")):
                        with open(data["root"]+data["path_dir"]+"authorized_ip.json") as file:
                            if data["IP"] not in json.load(file): raise Exception("ERROR 401 UNAUTHORIZED")
                                
                    if data["path"].split(".")[-1] == "py":
                        print("EST_UN_FICHIER_PY")
                        sys.path = [(data["root"]+data["path_dir"]).strip("/")]+sys.path #Modifie temporairement le sys.path et met le répertoire des page en preimier pour des question de priorité 
                        print(sys.path)
                        page = __import__(data["path"][len(data["path_dir"]):-3])
                        sys.path = sys.path[1:] #Remet sys.path comme avant pour ne pas perturber l'execution du code de la page 
                        response = page.main(data)
                        """elif data["path"].split(".")[-1] == "cs" and self.cs_compatibility:
                        print(f"start {data['path'][:-3]+'.exe'} {address[1]}")
                        os.system(f"start {data['root']}{data['path'][:-3]+'.exe'} {address[1]}") #Démarrer le programme en remplacant le .cs par un .exe avec address[1] en argumant
                        atriumC_requests.update({str(address[1]):{"client":client,"data":json.dumps(data)}})
                        
                        while "response" not in atriumC_requests[str(address[1])]: pass #Atendre une réponse du client TCP C#
                        raise Exception(atriumC_requests)
                        response = atriumC_requests[str(address[1])]["response"]
                        del atriumC_requests[str(address[1])]"""
                    else: response = prepare(data["root"]+data["path"])
                except Exception as e : response = f"HTTP/1.1 404 ERROR\nContent-Type: text/html\n\n<html><body><h1>ERROR 404</h1><p>{data}</p><p>{e}</p><p>{sys.exc_info()}</p></body></html>".encode()
                client.send(response)
                flag = "Done"
            else: flag = "Empty data"
        print(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n",end="")
        self.log.write(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n")
    def serve(self, pages, queue):
        self.pages = pages
        self.listening = True #Le socket est maintenant en train d'écoueter
        self.socket.listen(int(queue)) #Défini la longeure maximale de la fille d'attente
        with open(self.log_path,"a+") as self.log:
            self.log.write(f"[{time.ctime(time.time())}] Starting serve type listening...\n")
            while self.listening: thread.start_new_thread(self.serve_thread,self.socket.accept()) #Cré un thread pour s'occuper du client créé par socket.accept tout en continuant d'écouter
            self.log.write(f"[{time.ctime(time.time())}] Ending serve type listening\n")
    def serve_thread(self, client, address):
        thread.start_new_thread(trash_truck,())
        print(f"[{time.ctime(time.time())} : {address}] Starting thread...\n",end="") #Dans un thread, print est un peu perdu, il faut donc ajouter le \n manuellement pour des raisons d'affichage
        self.log.write(f"[{time.ctime(time.time())} : {address}] Starting thread...\n")
        with client: #Ferme automatiquement le client à la fin du thread
            data = client.recv(1024) #Récupère les données envoyées par le thread client
            if data:
                data = parse(data)
                data.update({"IP":address[0],"root":self.root})
                try:
                    exinfo = self.custom_thread(self, data)
                    if type(exinfo) == dict: data = exinfo
                except: print("NO_CUSTOM_THREAD",sys.exc_info())
                print(f"[{time.ctime(time.time())} : {address}] Data: {data}\n",end="")
                self.log.write(f"[{time.ctime(time.time())} : {address}] Data: {data}\n")
                
                try: response = self.pages[data["path"][1:]](data)
                except Exception as e : response = f"HTTP/1.1 404 ERROR\nContent-Type: text/html\n\n<html><body><h1>ERROR 404</h1><p>{data}</p><p>{e}</p><p>{sys.exc_info()}</p></body></html>".encode()
                client.send(response)
                flag = "Done"
            else: flag = "Empty data"
        print(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n",end="")
        self.log.write(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n")
##Petit outil de configuration en ligne de commande
if "-config" in sys.argv:
    def custom_thread(self, data): #Il faut reconfigurer le serveur à partir du formulaire de la page web
        if data[data["method"]] != {}:
            try:
                print("CUSTOM_THREAD_OK")
                self.listening = False
                del self.socket
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.bind((data[data["method"]]["address"],int(data[data["method"]]["port"])))
                self.root = data[data["method"]]["root"]
                self.log_path = data[data["method"]]["log"]
                self.homepage = "/"
                self.custom_thread=lambda:None
                self.listen(5)
            except: print("CUSTOM_THREAD_FAILED",sys.exc_info()) 
    #Pour cela on utilise self.custom_thread avec l'ajout d'un if "close" in data[data["method"]]
    #Pour une raison étrange, lors de l'import de config/config.py, cette partie du code est éxécutée sans raison et ça fait crash donc on met un try
    try:
        server = Server("",2004,"config","config/log.txt")
        server.custom_thread = custom_thread
        #server.custom_thread = lambda self, data: setattr(self,"listening",False) if "close" in data["path"] else None
        #config.custom_thread = lambda test: print("CUSTOM_THREAD")
        server.homepage = "/config.py"
        server.listen(1)
    except: print("Import Failed",sys.exc_info()) 
    
    
else:
    if "-exec" in sys.argv:
        def exec_thread(none = None):
            while True:
                try: exec(input())
                except Exception as e: print(f"{e}\n",end="")
        thread.start_new_thread(exec_thread,())
    if "-start" in sys.argv:
        try:
            start_id = sys.argv.index("-start")
            server = Server(sys.argv[start_id+1],int(sys.argv[start_id+2]),sys.argv[start_id+3],sys.argv[start_id+4])
            if "-listen" in sys.argv:
                listen_id = sys.argv.index("-listen")
                server.listen(int(sys.argv[listen_id+1]))
            server.socket.close()
        except:
            try: server.socket.close()
            except:pass
if "-h" in sys.argv:
    print("""
-start "addresse" "port" "root" "log" -> create a server that serve a certain root
-listen "queue" -> start the server
-exec -> [DEBUGING] start a server side thread to execute command
-config -> [BETA] start a config server serving a config form on localhost:2004
    /!\\ Can't be used with others arguments
    /!\\ Shuldn't be used on a forwarded server
""")





            
            
