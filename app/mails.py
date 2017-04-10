# coding:utf-8
from threading import Thread
from flask import render_template, current_app
from flask.ext.mail import Message
from app.__init__ import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

 # send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
# 永远尝试选择一个合适的发送端。如果你有一个发出信号的类，把 self 作为发送端。如果你从一个随机的函数发出信号，把 current_app._get_current_object() 作为发送端。
# 永远不要向信号传递 current_app 作为发送端，使用 current_app._get_current_object() 作为替代。这样的原因是， current_app 是一个代理，而不是真正的应用对象。
    msg = Message(app.config['FLASK_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASK_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
#'[Flasky] Confirm Your Account',


