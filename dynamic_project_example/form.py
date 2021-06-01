import server
def main(data):
    response = server.Response(headers = ["Content-Type: text/html"])
    if data["method"] == "POST": #User compleated the form
        name = data["POST"]["name"] #data["POST"] is a dict type object containing what has been sent to the server through the request
        response.content = f"""
<html>
    <body>
        <p>Hello {name}</p>
    </body>
</html>
"""
    else:
        response.content = """
<html>
    <body>
        <h1>Compleate this form</h1>
        <form method="POST">
            <label>What's your name ? <input type="text" name="name"/></label>
            <input type="submit">
        </form>
    </body>
</html>
"""
    return response.encode()
        
