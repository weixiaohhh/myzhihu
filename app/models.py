# coding:utf-8
import os
from app import db, login_manager, create_app
from flask.ext.login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash ,check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from datetime import datetime
import hashlib
from markdown import markdown
import bleach
from app.exceptions import ValidationError

class Permission:
    FOLLOW = 0x01              #关注
    COMMENT = 0x02             #评论
    QUESTION = 0x04            #提问
    ANSWER = 0x08              #回答
    MODERATE_COMMENTS = 0x16   #管理评论
    ADMINISTER = 0x80          #管理员权限 管理网站

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod #使用@staticmethod或@classmethod，就可以不需要实例化，直接类名.方法名()来调用。
    def insert_roles():
        #字典类型，key代表各种roles，roles[key][0]代表权限，[1]代表默认值
        #|代表或操作
        roles = {
            'User': (Permission.FOLLOW |            #用户 permissions = 0x00001111
                     Permission.COMMENT |
                     Permission.QUESTION |
                     Permission.ANSWER, True),
            'Moderator': (Permission.FOLLOW |       #协助管理员 permissions = 0x00011111
                          Permission.COMMENT |
                          Permission.QUESTION |
                          Permission.ANSWER |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)   #管理员 permissions = 0xff
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name

class Follow(db.Model):
    __tablename__ =  'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)  #关注者id(粉丝)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)  #被关注者id（大V）
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)     #邮箱
    username = db.Column(db.String(64), unique=True, index=True)  #用户名
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))  #身份
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean,default=False)  #是否认证
    name = db.Column(db.String(64))       #真实姓名
    location = db.Column(db.Text())       #所在地
    about_me = db.Column(db.Text())       #自我介绍
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)  #注册日期
    #可以直接调用datetime.utcnow ,不加(),default可接受函数做默认值,需要生成默认值时，会自动调用指定函数
    last_seen = db.Column(db.DateTime(),default=datetime.utcnow)      #最后访问日期
    avatar_hash = db.Column(db.String(32))
    questions = db.relationship('Question', backref='author', lazy='dynamic')
        #在Question模型里面加了author属性，可通过author属性访问User模型，获取的是模型对象不是外键的值
    answers = db.relationship('Answer', backref='author', lazy='dynamic')
        #在answers模型里面加了author属性，可通过author属性访问User模型，获取的是模型对象不是外键的值
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
        #在Comment模型里面加了author属性，可通过author属性访问User模型，获取的是模型对象不是外键的值
    proves = db.relationship('Prove', backref='prover', lazy='dynamic')
        #在Prove属性里面添加了prover属性，可以通过prover获得 赞者的信息
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan'
                               )
    # followed代表当前用户所关注的用户,user.followed.all()返回已经关注的用户的列表
    # backref 给Follow模型添加了follower属性。Follow模型可以用follower属性查找到当前用户，也就意味着Follow可通过follower（关注自己的用户,即粉丝）找到当前用户，被关注者可以通过 followed 找到关注者
    # cascade "all, delete-orphan" to indicate that related objects should follow along with the parent object in all cases, and be deleted when de-associated.删除对象将指向该纪录的实体也删除
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    #代表关注用户本身的人，自己的粉丝，user.followers.all()返回自己的关注者的列表
    #backref 给 Follow模型添加了followed属性。Follow模型可以用followed属性查找到当前用户，也就意味着Follow可通过followed（已关注的用户，即大v）找到当前用户，关注者可以通过 followed 找到被关注者

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
        #forgery_py.forgery.internet.email_address(user=None)
        #Random e-mail address in a hopefully imaginary domain.
        #If user is None user_name() will be used. Otherwise it will be lowercased and will have spaces replaced with _. Domain name is created using domain_name().
                     username=forgery_py.internet.user_name(True),
        #forgery_py.forgery.internet.user_name(with_num=False): Random user name.
        #Basically it’s lowercased result of first_name() with a number appended if with_num.
                     password=forgery_py.lorem_ipsum.word(),
        #forgery_py.forgery.lorem_ipsum.word(): Random word.
                     confirmed=True,
                     name=forgery_py.name.full_name(),
        #forgery_py.forgery.name.full_name():Random full name. Equivalent of first_name() + ' ' + last_name().
                     location=forgery_py.address.city(),
        # forgery_py.forgery.name.location():Random location name, e.g. MI6 Headquarters.
        # return random.choice(get_dictionary('locations')).strip(),从
                     about_me=forgery_py.lorem_ipsum.sentence(), #random sentence
                     member_since=forgery_py.date.date(True))
        #forgery_py.forgery.date.date(past=False, min_delta=0, max_delta=20)[source]
        #Random datetime.date object. Delta args are days. (if past:delta = delta * -1)

            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASK_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    # 如果邮件地址和FLASKY_ADMIN中的邮箱相同，则成为Role中的Administrator
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise  AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm':self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)          #data是个数组，{'confirm':self.id}
        except:
            return False
        if data.get('confirm') != self.id: #data.get('confirm')得到id，相等则匹配，confirm为True
            return False
        self.confirmed = True  #confirmed属性设置为True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        db.session.commit()
        return True

    def can(self, permissions):
    #检查permissions权限是不是存在，在请求权限permissions和已赋予权限role.permissions之间进行位与操作
    #位与操作返回存在的permissions，相等符合就返回True——所以如果存在该权限则返回True
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):  #检查管理员权限
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar(self, size=128, default='identicon', rating='9'):
        # if request.is_secure:
        #     url = 'https://secure.gravatar.com/avatar'
        # else:
        #     url = 'https://www.gravatar.com/avatar'
        # hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        # return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
        #     url=url, hash=hash, size=size, default=default, rating=rating
        # )
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar/'
        else:
            url = 'https://www.gravatar.com/avatar/'
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return url + hash+ '?s=' + str(size) + '&d=' + str(default) + '&r=' + str(rating)

    def follow(self, user):
        if not self.is_following(user): #是否关注了这个user，如果没有，可以关注
            f = Follow(follower=self, followed=user) #添加一个Follow模型对象，follwer和followed属性设立
            db.session.add(f)
            db.session.commit()

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first() #已经关注了该用户
        if f:
            db.session.delete(f)
            db.session.commit()

    def is_following(self, user): #是否正在关注
        return self.followed.filter_by(followed_id=user.id).first() is not None
    #user.followed.all/filter_by返回的是当前用户所关注的用户的的列表或者一部分列表 ,followed_id=user.id，代表查询的是当前用户是否关注这个id的用户

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None
    #user.followers.filter

    def is_proving(self, answer_id):
        p = db.session.query(Prove).join(User, Prove.prover_id==User.id).filter(Prove.answer_id==answer_id).first()
        return p is not None

    @property
    def followed_questions(self):
        return Question.query.join(Follow, Follow.followed_id == Question.author_id).filter(Follow.follower_id == self.id)
    #获取所关注用户的提问

    @property
    def self_questions(self):
        return Question.query.filter(Question.author_id == self.id)
    #获取自己的提问

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])  #返回对应的用户

    def __repr__(self):
        return '<User %r>' % self.username

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

	#回答者的回答
class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html =  db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    #utcnow，时间越靠现在，数字越大，所以如果要按照离现在的远近来排列的话，用降序
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    question_title = db.Column(db.String(64))
    comments = db.relationship('Comment', backref='answer', lazy='dynamic')
    #Comment模型添加answer属性，直接获取Answer模型对象
    proves = db.relationship('Prove', backref='answer', lazy='dynamic')
    #Prove模型中添加proved_answer属性，直接获取Answer模型对象

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Answer(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):  #在服务器使Markdown文本转换为html文本
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li',
                        'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True)
        )
        #markdown把Markdown文本转化为HTML
        #bleach.clean删除不在白名单的标签,第一个参数是待处理的html文本
        #The tags kwarg is a whitelist of allowed HTML tags. It should be a list, tuple, or other iterable. Any other HTML tags will be escaped or stripped from the text.
        #If you would rather Bleach stripped this markup entirely, you can pass strip=True:
        #最后用bleach.linkify把url转换成<a>链接，linkify() searches text for links, URLs, and email addresses and lets you control how and when those links are rendered:
db.event.listen(Answer.body, 'set', Answer.on_changed_body)
#set监听Answer.body，只要body设置新值，on_changed_body函数自动调用

#对回复的评论
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html =  db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'))


    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True)
        )
db.event.listen(Comment.body, 'set', Comment.on_changed_body)

#对回复的赞
class Prove(db.Model):
    __tablename__ = 'proves'
    id = db.Column(db.Integer, primary_key=True)
    disabled = db.Column(db.Boolean)
    prover_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'))
	
import sys
# whooshalchemy 只支持Python3 版本以下
if sys.version_info >= (3, 0):
    enable_search = False
else:
    enable_search = True
    import flask_whooshalchemyplus as whooshalchemyplus
from jieba.analyse import ChineseAnalyzer

#提问者提问的问题
class Question(db.Model):
    __tablename__ = 'questions'
    __searchable__ = ['title']
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    answers = db.relationship('Answer', backref='question', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):  #在服务器使Markdown文本转换为html文本
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li',
                        'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True)
        )
db.event.listen(Question.body, 'set', Question.on_changed_body)


myapp = create_app( 'default' or os.getenv('FLASK_CONFIG'))
if enable_search:
    whooshalchemyplus.whoosh_index(myapp, Question)
	


