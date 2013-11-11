from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import LineReceiver

class ChatProtocol(LineReceiver):

    def __init__(self, factory, addr):
        self.factory = factory
        self.addr = addr

    def connectionMade(self):
        print "accepted client at %s" % self.addr
        self.state = "GETNAME"
        self.name = None
        self.chat_commands = {'exit': self.transport.loseConnection, 'listall': self.list_clients}
        self.sendLine("Welcome to chat! Type 'listall' to see everyone in the chat. Type 'private:' followed \nby the name of a user and your message to send a private message to another user. \nType 'exit' to leave the chat.\n")
        self.sendLine("What is your name?")

    def connectionLost(self, reason):
        print "lost connection with client at %s" % self.addr
        self.send_message("%s has left chat" % self.name)
        del self.factory.users[self.name]
        
    def dataReceived(self, data):
        data = data.strip()
        if self.state == "GETNAME":
            if data in self.factory.users:
                self.sendLine("Name is already taken. Please choose a new name.")
            else:
                self.name = data
                self.factory.users[self.name] = self
                self.state = "CHAT"
                self.send_message("%s has entered chat" % self.name)
        elif self.state == "CHAT":
            if data in self.chat_commands:
                self.chat_commands[data]()
            elif data.startswith('private:'):
                user = data.split()[1]
                msg = data[len('private:')+len(user)+1:]
                self.send_private_msg(user, msg)
            else:
                self.send_message(self.name + ": " + data)

    def list_clients(self):
        self.sendLine(", ".join(self.factory.users.keys()))

    def send_message(self, data):
        for user in self.factory.users:
                if user != self.name:
                    self.factory.users[user].sendLine(data)

    def send_private_msg(self, user, data):
        if user in self.factory.users:
            self.factory.users[user].sendLine(self.name + ": **private** " + data)
        else:
            self.sendLine(user + " is not in chat. Cannot send private message.")
            

class ChatFactory(ServerFactory):
    users = {}

    def buildProtocol(self, addr):
        return ChatProtocol(self, addr)

def main(ip, port):
    factory = ChatFactory()
    from twisted.internet import reactor
    reactor.listenTCP(port, factory, interface=ip)
    reactor.run()
    

if __name__ == '__main__':
    main('localhost', 10001)
