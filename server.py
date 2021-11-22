##I know, some comments are in french instead of english, i'll change it tomorrow

##Importing python libraries
import socket #To create a TCP server
import _thread as thread #To process all the request at the same time
import urllib.parse #To help parsing HTTP requests
import json #To parse and dump session's content
import time #To time the logs
import sys #To start and configutre the server using command line AND to edit the path of libs for the .py web pages
import os #To add, remove and list files
import random #To create random salts
import hashlib #To provide extended hashing functions
import sqlite3 #To provide sqlite local db system
from termcolor import colored #To print warnings in yellow
import io #Help making the placeholder input
import traceback #For better error managment

##Importing 3rd party libraries
try: import ftfy #To solve some HTTP encoding issues
except ImportError: sys.stderr.write("[FATAL ERROR] Requierment not satisfied please install ftfy then restart the server\n")
    
def analyze(obj,more = {}):
    globals().update({**obj.__dict__,"MORE":more,"DEBUG":True})
    while globals()["DEBUG"]:
        exec(input("Code: "),{**globals()["__builtins__"]},{**obj.__dict__,"MORE":more})
        
def tree(text,offset=1):
	return "│"*(offset-1) + "├┬" + text.strip()[1:].replace("\n","\n"+"│"*offset)
    
def debug(text):
    sys.stdout.write(f"DEBUG : {text}\n")
    
def format(text, values, tag_name = "format"):
    """
Format a text using html tags like this
server.format("Hello <format username>",{"username":"henri"}) will return "Hello henri"
also work like this
server.format("Welocome into <format 0>",["Crwodsounding"])  will return "Welcome into Crwodsounding"

this is usefull when you have js in your webpage for example 
"function my_func(username){alert("Hello"+username)}; my_func({});".format("Henri") Will not work
"""
    keys = []
    if type(values) == list:
        keys = range(len(list))
    elif type(values) == dict:
        keys = values
    elif type(values) == str:
        return text.replace(f"<{tag_name}>", values)
    else:
        raise ValueError("values must be a dict, a list or a string")
    for i in keys:
        text = text.replace(f"<{tag_name} {i}>", str(values[i]))
    return text
    
 
def load(path):
    with open(path, rb) as file:
        ret = file.read()
    return ret
 
def salthash(string,salt):
    """Generate an hash using a salt in order to make it 'really' hard to crack"""
    if type(string) == str: string = string.encode("utf-8")
    if type(salt) == bytes: salt = salt.decode("utf-8")
    return hashlib.sha256(string+salt.encode("utf-8")).hexdigest()+salt+"l"+str(len(salt))

def salthash_verify(crypted_string,string):
    """Verify if the encrypted string provided have the string provided for origin"""
    if type(string) == str: string = string.encode("utf-8")
    if type(crypted_string) == bytes: crypted_string = crypted_string.decode("utf-8")
    salt = crypted_string[-(int(crypted_string.split("l")[-1])+1+len(crypted_string.split("l")[-1])):-(1+len(crypted_string.split("l")[-1]))]
    return crypted_string == salthash(string, salt)

def random_salt():
    """Generate a random salt which is a random number that had been hashed without salt"""
    return hashlib.sha256(str(random.choice([-1,1])*random.randint(1,99999)/random.randint(1,99999)).encode("utf-8")).hexdigest()


def trash_truck(target = ["sessions"]):
    """Remove all the temporary files that the server don't use anymore"""
    if "sessions" in target: #Remove sessions older than 1000 seconds
        for i in os.listdir("sessions"):
            try:
                with open(f"sessions/{i}","r") as session:session = json.load(session)
                if session["last_use"]+1000 < time.time():
                    os.remove(f"sessions/{i}")
            except Exception as e:
                print(f"ERROR while clearing {i} with error {e}\n",end="")
                os.remove(f"sessions/{i}")

          
def prepare(path,headers=[]):
    """Makes your .py web page able to return a file that is on your computer instead of a response object"""
    #headers.append(f"Content-Length: {os.stat(path).st_size}")
    with open("content-types.json") as content_types: headers.append("Content-Type: "+json.load(content_types)[path.split(".")[-1]])
    with open(path,"rb") as file:
        file = file.read()
        response = b"HTTP/1.1 200 OK\n"
        for i in headers:
            response += i.encode("utf-8")+b"\n"
        response += b"\n"+file
    return response
        

def parse(request):
    """The old parser, still used by the request object constructor"""
    def extract(data):
        """Extract data from a form"""
        form = {}
        for i in data.split("&"):
            i = i.split("=")
            try: form.update({i[0]: i[1]})
            except:
                if i[0] != "None": form.update({i[0]: i[0]})
        return form
    
    request = ftfy.fix_text(urllib.parse.unquote(request.decode("utf-8")))
    data = {"GET":{}, #All informations given in the URL afet the separator '?'
            "POST":{}, #All informations given at the and of the HTTP request
            "method":"", #The method used to send the data (GET or POST)
            "path":"", #The path of the web page requested
            "path_dir":"", #The path of the directory where the requested web page is located (usefull for local storage managment)
            "subdomain":"", #The subdomain (need to be improve)
            "headers":{} #All raw headers
            }
    ##GET and POST are in upper case to allow you to do data[data["method"]]
    data["method"] = request.split(" ")[0]
    data["path"] = request.split("HTTP")[0].split(data["method"])[1][1:-1]
    if data["method"] == "POST": data["POST"] = extract(request.split("\n")[-1])
    if "?" in data["path"]: #If URL contains a GET form
        data["GET"] = extract(data["path"].split("?",1)[1])
        data["path"] = data["path"].split("?",1)[0] #New path withot the GET form
    data["path_dir"] = data["path"].rsplit("/",1)[0]+"/"
    for i in request.split("\n"): #Add all the request's headers to the dirctionary
        i = i.split(": ",1)
        if len(i)==2:
            data.update({i[0]:i[1]})
            data["headers"].update({i[0]:i[1]})
    data["subdomain"] = data["Host"][:-len(data["Host"].split(".",len(data["Host"].split("."))-2)[-1])-1]
    if "Cookie" in data: #If there are cookies
        cookies = {}
        for i in data["Cookie"].split(";"):
            i = i.lstrip(" ").split("=")
            cookies.update({i[0]:i[1]})
        data["Cookie"] = cookies #Replace what's inside the Cookie header with a more usable dictionary
    return data


class Pyhp():
    def __init__(self,headers = [], locals_vars = {}, global_vars = {'__builtins__' : __builtins__}):
        self.localvars = {**locals_vars,**{"echo":lambda text: self.echo(text),"headers":headers,"finish": lambda:setattr(self,"finish",True)}}
        self.globalvars = global_vars
        self.finished = False
    def run(self, code):
      
        self.response = ""
        exec(code,self.globalvars,self.localvars)
        #self = ("finish" in self.localvars and self.localvars["php_end_parsing"])
        return self.response
    def save(self,name,value): setattr(self,name,value)
    def load(self,name): getattr(self,name)
    def echo(self,text): self.response+=str(text)


#Some exceptions that will be use with the request and user objects
class UserCookieException(Exception): pass
class UserLoginException(Exception): pass
class UnregisteredUserException(Exception): pass
class UserRegisteringException(Exception): pass

class Request():
    """
The request class
Contain everything that your py web page have to know to respond apropriately:
    - A copy of the server object
    - A copy of the client object -> Usefull to send multiple responses
    - Client's IP
    - The subdomain
    - Raw request
    - Headers
    - GET and POST forms
    - Cookies
    - Some usefull paths to make the automated user connection easyer
    - [IN DEV] A way to directly connect client without using data base on your side
"""
    def __str__(self):
        return str(self.__dict__)
    def __repr__(self):

        #return ""
        headers, get, post, cookies = tuple(["└".join("\n".join(["┌"+i]+[f"├─{ii}: {self.__getattr__(i)[ii]}" for ii in self.__getattr__(i)]).rsplit("├", 1)) for i in ["Headers","Get","Post","Cookies"]])
        r = ["└".join("\n".join(["┌"+i]+[f"├─{ii}: {self.__getattr__(i)[ii]}" for ii in self.__getattr__(i)]).rsplit("├", 1)) for i in ["Headers","Get","Post","Cookies"]]
        return f"""
┌Request
├─IP: {self.address}
├─Subdomain: {self.subdomain}
{tree(headers,1)}
├┬Forms
{tree(get,2)}
{tree(post,2)}
{tree(cookies,1)}
"""
    
    def __init__(self,server,client,address,subdomain,raw,headers,method,get,post,cookies,path,paths): self.__dict__.update({**locals(),"self":None})

    def parse_from_raw(server,client,address,raw):
        parsed = {**{"Cookie":{}},**parse(raw)}
        print(parsed)
        return Request(server,client,address,parsed["subdomain"],raw,parsed["headers"],parsed["method"],parsed["GET"],parsed["POST"],parsed["Cookie"],parsed["path"],
                       {"root":server.root, "local_folder":server.root+parsed["path_dir"]})

    def get_user(self,response):
        return User(self,response)
    
    def __setattr__(self, key, value): self.__dict__.update({key.lower():value})#Makes the programmer able to call request.GET as well as request.get
    
    def __getattr__(self, key): return self.__dict__[key.lower()]


class DictBase():
    """A class created to simplify the edditing of an sqlite3 db in python"""
    def __init__(self,data_base,table):
        self.db = data_base
        self.table = table
        self.cursor = self.db.cursor()
        
    def __repr__(self): return str(self.load())
    def __iter__(self): return self.load()
    def pragma(self):
        return self.cursor.execute(f"PRAGMA table_info({self.table})").fetchall()
    def load(self):
        """Return a dict object containing all the informations in the table"""
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
        """
Return a dict object containing all the informations in the table coresponding to the querry
"""
        return_list = []
        for i in self.load():
            if i[name] == value: return_list.append(i)
        return return_list
    
    def insert(self,data):
        """
Insert data in the table
"""
        names = ""
        values = []
        for i in data:
            names += ","+str(i)
            values.append(data[i])
        self.cursor.execute(f"INSERT INTO {self.table}({names[1:]}) VALUES({(',?'*len(data))[1:]})",tuple(values))
        return self
    
    def primary(self):
        """
Return all the primary keys of the table
"""
        primaries = []
        for i in self.cursor.execute(f"PRAGMA table_info({self.table})").fetchall():
            if i[5] == 1: primaries.append(i[1])
        return primaries
    
    def sort(self,key):
        """
Return all the info in the table but they are sorted. Example :
[{"key1":"value1","key2":"value2"},{"key1":"VALUE1","key2":"VALUIE2"}] -> sorting by "key1" -> {"value1":{"key2":"value2"},"VALUE1":{"key2":"VALUE2"}}
Make SURE the key that you sort with is UNIQUE or you bad things cold happend
"""
        sorted_dict = {}
        for i in self.load():
            sorted_dict.update({i[key]:i})
        return sorted_dict
    
    def update(self,search_key,search_value,replace_key,replace_value):
        self.cursor.execute(f"UPDATE {self.table} SET {replace_key} = ? WHERE {search_key} = ?",(replace_value,search_value))
        return self
    def delete(self,search_key,search_value):
        self.cursor.execute(f"DELETE FROM {self.table} WHERE {search_key}",search_value)
        return self
    def commit(self):
        self.db.commit()
        return self


class User(dict):                           
    """
Making a user class that is programmer-freindly and easy to use (because none want a calass that's not intuitive) wasn't really easy
i had to do basicaly all the programmer's work by creating the db, his table and updating it if needed
i also wanted to keep it versalile making it usable in most of the cases by adding as less info in the table while keeping the possibility of adding more if the programmer want
because request and response are techincaly mutable, the request attrubute of the user object is the same as the request that was given to the __init__ function
"""
    def __init__(self, request, response, username = None, password = None, remember_me = None, session = None, dib = DictBase(sqlite3.connect("users.db"),"users")):
        """
Able to get the user that is connecting to your website
Can also add him if he's connecting for the 1st time but it's not really recomanded, you should instead do it manualy using User.add
"""
        self.types = {dict: "JSON",
                      list: "JSON",
                      str: "TEXT",
                      bytes: "BLOB",
                      bool: "BOOL"} #A kind of traslation table python -> SQL for types
        if not session: self.session = response.create_session(request) #Automaticaly make the session
        if remember_me == None: #In python, not False == not None so i can't do "if not remember_me" which piss me of
            remember_me = True if "remember_me" in {**request.post,**request.get} else False #Automaticaly set the remember_me cookie
        if not username: #Automaticaly set the username
            if "username" in request.post: username = request.post["username"]
            elif "username" in request.get: username = request.get["username"]
        if not password: #Automaticaly set the password
            if "password" in request.post: password = request.post["password"]
            elif "password" in request.get: password = request.get["password"]    
        self.dib = dib
        self.dib.cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {dib.table}(
     username TEXT PRIMARY KEY UNIQUE,
     password TEXT,
     salt TEXT UNIQUE
)
""")#make a table with everything requiered to make the db compatible with the User class
        for i in ["username TEXT UNIQUE","password TEXT","salt TEXT UNIQUE"]:#Add requers rows to the table if requiered
            try: self.dib.cursor.execute(f"ALTER TABLE {table} ADD {i}")
            except KeyboardInterrupt:
                quit()
            except Exception: pass
        self.dib.db.commit()#The table is now set
        #Let's try to connect the user using every info we have
        users = self.dib.sort("username")
        if "username" in session:
            self.username = session["username"]
        elif "username" in request.cookies:
            cookie = request.cookies["username"]
            username = cookie[len(cookie.split("l")[0])+1:len(cookie.split("l")[0])+1+int(cookie.split("l")[0])]
            username_hash = cookie[len(cookie.split("l")[0])+1+int(cookie.split("l")[0]):]
            if username in users:
                salt = users[username]["salt"]
                if salthash_verify(cookie,salthash(username,salt)):
                    self.username = username
                else: raise UserCookieException("This is a fake cookie")
        elif username and password:
            if salthash_verify(users["username"]["password"],password):
                self.username = username
            else: raise UserLoginException("Incorrect username or password")

        if "username" in self.__dir__() and remember_me: #Make the remmeber_me cookie
            cookie = salthash(self.username,self.dib.select("username",self.username)[0]["salt"]) #1st hash makes the cookie dependent of the UNIQUE hash
            cookie = server.salthash(cookie, server.random_salt()) #2nd hash to hide the UNIQUE hash
            cookie = str(len(self.username))+"l"+self.username+cookie #Add the username and his len to the cookie
            response.add_cookie({"username":cookie,"Max-Age":2592000}) #Make a remember_me cookie for 30 days
            
    def load(self, username = False):
        """
Load what's inside the database into the object
"""
        if not username: self.username = username
        self.update(self.dib.sort("username")[self.username])
        
    def dump(self, auto_commit = True):
        """
Dump what's inside the object into the database
add collumns if needed
"""
        headers = self.dib.cursor.execute(f'PRAGMA table_info({dib.table})').fetchall()
        names = [i[1] for i in headers]
        for i in self:
            try:
                if i not in names: self.dib.execute(f"ALTER TABLE {self.dib.table} ADD {i} {self.types[type(self[i])]}")#Add a comumn to the table
                self.dib.update("username",self.username,i,self[i])
            except Exception as e:
                print(colored(f"[WARNING] Can't add {i} with value {self[i]} to the database ({e})","yellow"))
            finally:
                if auto_commit: self.dib.db.commit()
    def add(username,password,data = {},dib = DictBase(sqlite3.connect("users.db"),"users")):
        dib.cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {table}(
     username TEXT PRIMARY KEY UNIQUE,
     password TEXT,
     salt TEXT UNIQUE
)
""")#make a table with everything requiered to make the db compatible with the User class
        for i in ["username TEXT UNIQUE","password TEXT","salt TEXT UNIQUE"]+list(data.keys()):#Add rows to the table if requiered
            try: dib.cursor.execute(f"ALTER TABLE {table} ADD {i}")
            except KeyboardInterrupt:
                quit()
            except Exception: pass
        
        dib.insert({**data,**{"username":username,"password":password,"salt":random_salt()}})
        dib.db.commit()#The table is now set


class Session(dict):
    """
A class containing everyting required to make and use a session on server side
"""
    
    def smart_connect(request):
        """
Return a session object
Try to get the user session and if it can't create an new session
Just make sure to place the code of the session in a cookie nammed "sessid" in order to bind it to the client
Use it if you're a little bit lazy
If you're really lazy, check Response.create_session (it will automaticly set the sessid cookie for you
"""
        try:
            sess = Session(request.cookies["sessid"]).load()
            if request.headers["User-Agent"] != sess["User-Agent"] or request.address != sess["IP"]:
                raise Exception("Spoffing spotted") #Raise an exception if a spoofing is suspected
            return sess
        except:
            while True:
                code = str(random.randint(0,10000))
                if code not in os.listdir("sessions"): break
            return Session(code,{"User-Agent":request.headers["User-Agent"],"IP":request.address}).dump()
        
    def __init__(self,code,data = {}):
        self.code = code
        self.last_use = time.time()
        self["last_use"] = self.last_use
        self.update(data)
        
    def dump(self):
        """
Save the session in his file
"""
        with open("sessions/"+self.code+".json","w") as file: json.dump(self,file)
        return self
    
    def load(self):
        """
Load the session from his file
"""
        with open("sessions/"+self.code+".json","r") as file: self.update(json.load(file))
        return self
    def empty(self):
        self.clear()
        return self


class Response(): #Partiellement copié depuis servlib a5
    """
Response is responsebale of the auto-formating of the HTTP response
It was made with only one objective : make the server respond something that have sense while providing him as less information as possible
And it's in this way that i've included a lot of auto corecting code 
"""
    def __init__(self,content="",headers=[],code="200 OK"):
        self.content = content
        self.headers = headers
        self.code = code
    def __repr__(self):
    
        return str(self.copy().encode())
    def copy(self):
        return type(self)(self.content,self.headers,self.code)
    def encode(self, encoding = False, autocorrect = True):
        """
Return a byte like object which is an HTTP response ready to be sent to the client
""" 
        if autocorrect:
            if encoding:
                if "<head>" in self.content: self.content = self.content.replace("<head>", f"""<head>\n<meta http-equiv="Content-Type" content="text/html; charset={encoding}" />""")
                else: self.content = self.content.replace("<html>", f"""<html><head>\n<meta http-equiv="Content-Type" content="text/html; charset={encoding}" /></head>""")
            else: encoding = "utf-8"
            
                
            if (not True in [("Content-Type" in i )for i in self.headers]) and ("<html>" in self.content): self.headers = ["Content-Type: text/html"]
            if ("Content-Type: text/html" in self.headers) and (not self.content.startswith("\n")): self.content = "\n"+self.content
            if (not True in [("Content-Length" in i )for i in self.headers]):
                #self.headers.append(f"Content-Length: {len(self.content)}")
                pass
            response = f"HTTP/1.1 {self.code}\n"
            for i in self.headers:
                response += i.strip("\n") + "\n"
        if type(self.content) == str: return (response+self.content).encode(encoding)
        elif type(self.content) == bytes: return response.encode(encoding)+self.content
        else: return (response+"\n<html><head><title>ERROR</title></head><body><h1>ERROR</h1></body></html>").encode(encoding)
    def add_cookie(self,cookie):
        """
Add a cookie header to the response
Accept :
    - string (the cookie header EX: "Set-Cookie: username=john; Max-Age=10000")
    - dictionary (filled with the attributes of the header EX: {"sessid":"98546","Max-Age":"10000"})
    - list (have to contain string and/or dict EX: ["Set-Cookie: username=john; Max-Age=10000",{"sessid":"98546","Max-Age":"10000"}])
"""
        if type(cookie) == str: self.headers.append(cookie)
        elif type(cookie) == dict:
            temp_cookie = "Set-Cookie: "
            for i in cookie: temp_cookie += "{0}={1}; ".format(i,cookie[i])
            self.headers.append(temp_cookie.strip("; "))
        elif type(cookie) == list:
            for i in cookie: self.add_cookie(i)
        return self
    def get_session(self,request):
        """
Use the data that the server give to the main function of your .py web page to return a ready for use session
it will automaticaly create the sessid cookie
"""
        sess = Session.smart_connect(request)
        try:
            if request.cookies["sessid"] != sess.code:
                raise Exception("Need to make a cookie")
        except: self.add_cookie({"sessid":sess.code})
        return sess
    def redirect(self, url):
        """
Change the response's content to a script that redirect the user to an other page
"""
        self.headers.append("Content-Type: text/html")
        self.content = f"<html><body><script>document.location.href = '{url}'</script></body></html>"
        return self


class Server():
    """
A real mess ! Wait for the PyHP new server system, it will be more understandable
"""
    def __init__(self,address = "", port = 80, root = "root", log = "log.txt", internal_pages = {}, parser = parse):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Cré le socket
        self.socket.bind((address,port)) #Lie le socket à l'adresse et au port en argument de la fonction
        self.listening = False #Le socket n'est pas enore en train d'écouter
        self.root = root #root est la racine du site cela permet de créer un site dans un répertoire différent du serveur /!\ Le serveur devra quand meme etre lancé depuis son répertoire 
        with open("content-types.json","r") as file: self.content_types = json.load(file) #liste des content-type supportés par le serveur
        self.log_path = log
        self.internal_pages = internal_pages
        self.parser = parser
        
    def listen(self,queue):
        self.listening = True #Le socket est maintenant en train d'écoueter
        self.socket.listen(int(queue)) #Défini la longeure maximale de la fille d'attente
        with open(self.log_path,"a+") as self.log:
            self.log.write(f"[{time.ctime(time.time())}] Starting listening...\n")
            while self.listening: thread.start_new_thread(self.client_thread,self.socket.accept()) #Cré un thread pour s'occuper du client créé par socket.accept tout en continuant d'écouter
            self.log.write(f"[{time.ctime(time.time())}] Ending listening\n")
    def client_thread(self,client,address):
        sys.stdout.write(f"[{time.ctime(time.time())} : {address}] Starting thread...\n") #Print is sometimes broken in thread, we use stdout.write instaed
        self.log.write(f"[{time.ctime(time.time())} : {address}] Starting thread...\n")    
        with client: #Automaticaly close the client at the end
            raw = client.recv(1024)
            if raw: #If raw request is not empty (empty mean the connection has been closed)
                request = Request.parse_from_raw(self,client,address[0],raw)
                if "custom_thread" in self.__dir__():#If a custom thread is define
                    try: self.custom_thread(self, request) #Custom thread don't need to return anything anymore because of the classes mutability
                    except Exception as e: sys.stderr.write("An error occured, can't update the request using the custom thread")


                sys.stdout.write("\n".join(["    "+i for i in f'[{time.ctime(time.time())} : {address}] Request:\n{str(request)}\n'.split("\n")]).strip("    "))
                self.log.write(f"[{time.ctime(time.time())} : {address}] Request: {str(request)}\n")


                if request.subdomain != "" and "subdomains_roots" in self.__dir__():
                    if request.subdomain in self.subdomains_roots:
                        request.paths["root"] = self.subdomains_roots[request.subdomain]
                if request.path == "/" and "homepage" in self.__dir__(): request.path = self.homepage
                try:
                    print(request.path)
                    print(request.paths)
                    flag = "ERROR"
                    if "authorized_ip.json" in os.listdir(request.paths["local_folder"].strip("/")):
                        with open(request.paths["local_folder"]+"authorized_ip.json") as file:
                            if request.addess not in json.load(file): raise Exception("401")
                    
                    if "." not in request.path: #If a dir is requested
                        #print("DIR")
                        response = f"HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><body><h1>Direcctory of {request.paths['root']}{request.path}</h1><ul>"
                        print(os.listdir(request.paths["root"]+request.path))
                        for i in [".."] + os.listdir(request.paths["root"]+request.path):
                            response += f"<li><a href='/{i}'>{i}</a></li>"
                        response = response.encode() + b"</ul></body></html>"
                    elif request.path.split(".")[-2] == "restricted": raise Exception("401")#Permet de créer des fichiers uniquement utilisables par le serveur
                    elif request.path.split(".")[-2] == "aspy": request.path.split(".")[:-2] + ".py"
                    elif request.path.split(".")[-2] == "aspyhp": request.path.split(".")[:-2] + ".pyhp"
                    elif request.path.split(".")[-1] == "py": #If a pyton webscript is requested
                        sys.path = [request.paths["local_folder"].strip("/")]+sys.path #Modifie temporairement le sys.path et met le répertoire des page en preimier pour des question de priorité 
                        if request.path in self.internal_pages:
                            page = self.internal_pages[request.path]
                        else:
                            page = __import__(request.path.split("/")[1][:-3])
                        sys.path = sys.path[1:] #Rollback sys.path to avoid import perturbations
                        response = page.main(request)
                    elif request.path.split(".")[-1] == "pyhp": #If a python webpage is requested
                        with open(os.path.join(request.paths["root"]+request.path),"r") as file: file = file.read()
                        pyhp = Pyhp(["Content-Type: text/html"],{"request":request},globals().copy())
                        html = []
                        for i in file.split("<?"): html += i.rsplit("?>",1)
                        for i in range(len(html)):
                            if html[i].strip("\n").strip(" ").split("\n",1)[0].split(" ",1)[0].lower() == "pyhp":
                                html[i] = pyhp.run(html[i].split("pyhp",1)[1].strip())
                            if pyhp.finished:
                                break
                        response = Response("".join(html[:i]),pyhp.localvars["headers"]).encode()
                    else:
                        response = prepare(request.paths["root"]+request.path)
                    if response == None: raise Exception("Web page sent no response")
                    flag = "Done"
                except (ImportError, FileNotFoundError):
                    print("Error 404 with :",request)
                    response = f"HTTP/1.1 404 ERROR\nContent-Type: text/html\n\n<html><body><h1>ERROR 404</h1><p>{request}</p><p>{sys.exc_info()}</code></body></html>".encode()
                except Exception as e:
                    try:
                        if e.args[0] == "401":
                            print("Error 401 with :",request)
                            response = b"HTTP/1.1 401 Unauthorized\nContent-Type: text/html\n\n<html><body><h1>ERROR 401 UNAUTHORIZED</h1></body></html>"
                        else:
                            exception_type, exception_object, exception_traceback = sys.exc_info()
                            error_info = {
                                "type":exception_type,
                                "object":exception_object,
                                "traceback":exception_traceback,
                                "filename":exception_traceback.tb_frame.f_code.co_filename,
                                "line":exception_traceback.tb_lineno}
                            sys.stdout.write(f"ERROR {error_info}\n")
                        raise e
                    except:
                        print("Error 500 with :",request)
                        exception_type, exception_object, exception_traceback = sys.exc_info()
                        error_info = {
                            "type":exception_type,
                            "object":exception_object,
                            "traceback":exception_traceback,
                            "filename":exception_traceback.tb_frame.f_code.co_filename,
                            "line":exception_traceback.tb_lineno}
                            
                        response = f"HTTP/1.1  500 ERROR\nContent-Type: text/html\n\n<html><body><h1>ERROR 500</h1><p><code><xmp>{request}</xmp></code></p><p><code><xmp>{traceback.format_exc()}</xmp></code></p></body></html>".encode()
                finally: client.send(response)
            else: flag = "Empty data"
        print(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n",end="")
        self.log.write(f"[{time.ctime(time.time())} : {address}] Ending thread with flag: {flag}\n")


if __name__ == "__main__":
    s = Server(input("Address : "),
               int(input("Port : ")),
               input("Root directory : "),
               input("Log output file : "))
    s.listen(int(input("Max witing queue : ")))
            
