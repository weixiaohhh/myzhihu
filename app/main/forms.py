# coding:utf-8
from flask_wtf import Form
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField ,ValidationError
from wtforms.validators import DataRequired, Length, Email, Regexp
from app.models import User, Role
from flask.ext.pagedown.fields import PageDownField

class NameForm(Form):
    name = StringField('请输入您的名字', validators=[DataRequired()])
    submit = SubmitField('提交')

class EditProfileForm(Form):
    name = StringField('真实名字', validators=[Length(0,64)])
    location = StringField('居住地', validators=[Length(0,64)])
    about_me = TextAreaField('一句话介绍')
    # class wtforms.fields.TextAreaField(default field arguments)
    # This field represents an HTML <textarea> and can be used to take multi-line input.
    submit = SubmitField('提交')

class EditProfileAdminForm(Form):
    email = StringField('邮箱', validators=[DataRequired(), Length(1,64), Email()])
    username = StringField('用户名', validators=[DataRequired(), Length(1,64),\
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must have only letters, numbers\
        dots, or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)   #http://wtforms.simplecodes.com/docs/0.6.1/fields.html
        #选择在self.role.choices设定了,choices必须是元祖，[(A,B),(C,D)...]的形式
        #元祖中标示符是role.id，是证书，所以coerce=int
    name = StringField('真实名字', validators=[Length(0, 64)])
    location = StringField('居住地', validators=[Length(0, 64)])
    about_me = TextAreaField('一句话介绍')
    submit = SubmitField('提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已被注册')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('此用户名已被使用')

class AnswerForm(Form):
    # body = TextAreaField("What's on your mind?", validators=[DataRequired()])
    body = PageDownField("请输入你的回答", validators=[DataRequired()])
    submit = SubmitField('提交')

class QuestionForm(Form):
    title = StringField('请输入你想提出问题的标题', validators=[DataRequired()])
    body = PageDownField("请输入你想提出问题的内容", validators=[DataRequired()])
    submit = SubmitField('提交')

class CommentForm(Form):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('提交')

class SearchForm(Form):
    search = StringField('search', validators=[DataRequired()])