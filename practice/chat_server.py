from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import LineReceiver
from spell_checker import SpellChecker
import re

class ChatProtocol(LineReceiver):

    def __init__(self, factory, addr):
        self.factory = factory
        self.addr = addr

    def connectionMade(self):
        print "accepted client at %s" % self.addr
        self.state = "GETNAME"
        self.name = None
        self.chat_commands = {'exit': self.transport.loseConnection, 'listall': self.list_clients, 'private:': self.send_private_msg, 'transform:': self.transform_msg}
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
            if data == '':
                return
            command = data.split()[0]
            if command in self.chat_commands:
                if len(data.split()) == 1:
                    self.chat_commands[command]()
                else:
                    transform = data.split()[1]
                    msg = data[len(command)+len(transform)+2:]
                    self.chat_commands[command](transform, msg)
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

    def transform_msg(self, transform, msg):
        transformed_message = self.factory.transform(transform, msg)
        if transformed_message is None:
            self.sendLine(transform + " is not a valid transform. Your message was sent without a transformation.")
            transformed_message = msg
        self.send_message(self.name + ": " + transformed_message)

class ChatFactory(ServerFactory):
    users = {}

    def __init__(self, service):
        self.service = service

    def buildProtocol(self, addr):
        return ChatProtocol(self, addr)

    def transform(self, name, message):
        func = getattr(self, name, None)
        print func
        if func is None:
            return None
        try:
            return func(message)
        except:
            return None

    def spell_check(self, message):
        return self.service.spell_check(message)

class TransformService(object):
    def __init__(self):
        self.spellChecker = SpellChecker()

    def spell_check(self, message):
        words = re.findall("\w+'*\w+", message)
        for word in words:
            correct, correct_spelling = self.spellChecker.spell_check(word)
            if not correct:
                message = message.replace(word, correct_spelling)
        return message

def main(ip, port):
    service = TransformService()
    factory = ChatFactory(service)
    from twisted.internet import reactor
    reactor.listenTCP(port, factory, interface=ip)
    reactor.run()


if __name__ == '__main__':
    main('localhost', 10001)
