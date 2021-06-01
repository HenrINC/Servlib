import server #Import the servlib framework
import time #Import the python's time library
def main(data): #The function that will be executed py the server
    response = server.Response() #We create a response object
    response.headers = ["Content-Type: text/html"] #We define the headers of the response
    response.content = f"""
<html>
    <body>
        <p>It's {time.strftime("%H:%M:%S", time.localtime())}</p>
    </body>
</html>
""" #We define the content of the response
    return response.encode() #Return an encoded version of the response we previously created
