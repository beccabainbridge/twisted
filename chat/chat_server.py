#!/usr/bin/env python
import re
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet import defer
import sys
sys.path.append('/home/becca/code/spellCheck')
from spell_checker import SpellChecker
sys.path.append('/home/becca/code/lolCat')
from lol_cat_translator import LolCatTranslator

def catchError(err):
    return "An error occurred in the server"

class ChatProtocol(LineReceiver):

    def __init__(self, factory, addr):
        self.factory = factory
        self.addr = addr

    def connectionMade(self):
        print "accepted client at %s" % self.addr
        self.start_chat()

    def connectionLost(self, reason):
        print "lost connection with client at %s" % self.addr
        del self.factory.users[self.name]
        self.send_message("%s has left chat" % self.name)

    def dataReceived(self, data):
        d = defer.succeed(data.strip())
        d.addErrback(catchError)
        if self.state == "GETNAME":
            d.addCallback(self.set_name)
        elif self.state == "CHAT":
            d.addCallback(self.parse_and_send_msg)

    def start_chat(self):
        self.state = "GETNAME"
        self.name = None
        self.chat_commands = {'exit': self.transport.loseConnection,
                              'listall': self.list_clients,
                              'private:': self.send_private_msg,
                              'transform:': self.transform_msg}
        self.sendLine("Welcome to chat! Type 'listall' to see everyone in the" +
                      " chat. Type 'private:' followed \nby the name of a user" +
                      " and your message to send a private message to another " +
                      "user. Type \n'transform:' followed by a transformation " +
                      "(lol_cat, spell_check) and your message to \nend a " +
                      "transformed message. Type 'exit' to leave the chat.\n" +
                      "\nWhat is your name?")

    def set_name(self, name):
        if name in self.factory.users:
            self.sendLine("Name is already taken. Please choose a new name.")
        else:
            self.name = name
            self.factory.users[self.name] = self
            self.state = "CHAT"
            self.send_message("%s has entered chat" % self.name)

    def parse_and_send_msg(self, data):
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
        d = self.factory.transform(transform, msg)
        def transform_error(res):
            self.sendLine(res.getErrorMessage() + " Your message was sent without a transformation.")
            return msg
        d.addErrback(transform_error)
        def transform_send(transformed_message):
            self.send_message(self.name + ": " + transformed_message)
        d.addCallback(transform_send)


class ChatFactory(ServerFactory):
    users = {}

    def __init__(self, service):
        self.service = service

    def buildProtocol(self, addr):
        return ChatProtocol(self, addr)

    def transform(self, name, message):
        func = getattr(self, name, None)
        if func is None:
            return defer.fail(Exception("Invalid transform."))
        try:
            return defer.succeed(func(message))
        except:
            return defer.fail(Exception("Transformation failed."))

    def spell_check(self, message):
        return self.service.spell_check(message)

    def lol_cat(self, message):
        return self.service.lol_cat(message)


class TransformService(object):
    def __init__(self):
        self.spellChecker = SpellChecker()
        self.lolCatTranslator = LolCatTranslator()

    def spell_check(self, message):
        return self.spellChecker.spell_check_message(message)

    def lol_cat(self, message):
        return self.lolCatTranslator.translate_message(message)


service = TransformService()
factory = ChatFactory(service)
from twisted.application import service, internet
application = service.Application("chatserver")
internet.TCPServer(10001, factory).setServiceParent(application)
