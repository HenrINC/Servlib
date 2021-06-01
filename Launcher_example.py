import server

def custom_thread_example(data):
    #Makes what's inside the POST form all caps
    for i in data["POST"]:
        data["POST"][i] = data["POST"][i].upper()

example_server = server.Server("", 2555, "static_project_example", "log.txt") #Create a server object

example_server.custom_thread = custom_thread_example #Makes "cutom_thread_example" the "cutom_thread" of the server

example_server.homepage = "hello_world.py" #Makes the "hello_world.py" the homepage of the website

example_server.subdomains_roots = {"dynamic":"dynamic_project_example"} #Add a subdomain nammed "dynamic" refering to the website whose root is "Dynamic_project_example"

example_server.listen(3) #Start the server with a waiting queue of 3
