
import datetime
import json
import time
import urllib

import aredis
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.httpclient

from django.conf import settings
# https://stackoverflow.com/questions/32761566/django-1-9-importerror-for-import-module
# from django.utils.importlib import import_module
from importlib import import_module

session_engine = import_module(settings.SESSION_ENGINE)

from django.contrib.auth.models import User

from privatemessages.models import Thread

c = aredis.StrictRedis(host='127.0.0.1', port=6379, db=0)
# c.connect()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/plain')
        self.write('Hello. :)')


class MessagesHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessagesHandler, self).__init__(*args, **kwargs)
        self.client = aredis.StrictRedis(host='127.0.0.1', port=6379, db=0)
        #self.client.connect()

    def check_origin(self, origin):
        return True

    def open(self, thread_id):
        session_key = self.get_cookie(settings.SESSION_COOKIE_NAME)
        session = session_engine.SessionStore(session_key)
        try:
            self.user_id = session["_auth_user_id"]
            self.sender_name = User.objects.get(id=self.user_id).username
        except (KeyError, User.DoesNotExist):
            self.close()
            return
        if not Thread.objects.filter(
            id=thread_id,
            participants__id=self.user_id
        ).exists():
            self.close()
            return
        self.channel = "".join(['thread_', thread_id,'_messages'])
        self.pub_sub = self.client.pubsub()
        # self.client.subscribe(self.channel)
        self.pub_sub.subscribe(self.channel)
        self.thread_id = thread_id
        # self.client.listen(self.show_new_message)
        # self.pub_sub.listen(self.show_new_message)
        self.pub_sub.listen()

    def handle_request(self, response):
        pass

    def on_message(self, message):
        if not message:
            return
        if len(message) > 10000:
            return
        c.publish(self.channel, json.dumps({
            "timestamp": int(time.time()),
            "sender": self.sender_name,
            "text": message,
        }))
        http_client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(
            "".join([
                        settings.SEND_MESSAGE_API_URL,
                        "/",
                        self.thread_id,
                        "/"
                    ]),
            method="POST",
            #https://stackoverflow.com/questions/28906859/module-has-no-attribute-urlencode
            body=urllib.parse.urlencode({
                "message": message.encode("utf-8"),
                "api_key": settings.API_KEY,
                "sender_id": self.user_id,
            })
        )
        http_client.fetch(request, self.handle_request)

    def show_new_message(self, result):
        self.write_message(str(result.body))

    def on_close(self):
        try:
            self.client.unsubscribe(self.channel)
        except AttributeError:
            pass
        def check():
            # if self.client.connection.in_progress:
            if self.client.connection_pool.get_connection():
                tornado.ioloop.IOLoop.instance().add_timeout(
                    datetime.timedelta(0.00001),
                    check
                )
            else:
                # self.client.disconnect()
                self.client.connection_pool.get_connection().disconnect()
        tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(0.00001),
            check
        )

application = tornado.web.Application([
    (r"/", MainHandler),
    (r'/(?P<thread_id>\d+)/', MessagesHandler),
])
