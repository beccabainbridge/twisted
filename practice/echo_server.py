from twisted.application import internet
from twisted.internet.protocol import ServerFactory, Protocol

class EchoProtocol(Protocol):
    def connectionMade(self):
        print "connection made"

    def connectionLost(self, reason):
        print "connection lost"
        
    def dataReceived(self, data):
        if data == "exit\n":
            self.transport.loseConnection()
        else:
            self.transport.write(data)

class EchoFactory(ServerFactory):
    protocol = EchoProtocol

def main():
    factory = EchoFactory()
    from twisted.internet import reactor
    reactor.listenTCP(10001, factory)
    reactor.run()
    

if __name__ == '__main__':
    main()
