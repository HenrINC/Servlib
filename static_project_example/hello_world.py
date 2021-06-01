import server #Import the servlib framework
def main(data): #The function that will be executed py the server
    response = server.Response() #We create a response object
    response.headers = ["Content-Type: text/html"] #We define the headers of the response
    response.content = """
<html>
    <body>
        <p>Hello world</p>
    </body>
</html>
""" #We define the content of the response
    return response.encode() #Return an encoded version of the response we previously created
