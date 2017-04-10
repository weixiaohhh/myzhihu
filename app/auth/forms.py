# coding:utf-8
from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError
from wtforms.validators import  DataRequired, Length, Email,Required, Regexp, EqualTo
from app.models import User

class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('keep me logged in')
    submit = SubmitField('Log in')

class RegistrationForm(Form):
    email = StringField('Email', validators=[DataRequired(),Length(1,64), Email()])
    username = StringField('Username',validators=[
        DataRequired(), Length(1,64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
        'Usernames must have only letters, numbers, dots or underscores')])
        # '^[A-Za-z][A-Za-z0-9_.]*$':^表示开头，$表示结束，匹配内容是字母开头+任意个字母/数字/小数点
    password = PasswordField('Password',validators=[DataRequired(),
        EqualTo('confirm',message='passwords must match.')])
    confirm = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, field):    #确保邮箱没有使用过
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):   #确定用户名没用过，在某些应用中，不允许重名
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

#class wtforms.validators.Regexp(regex, flags=0, message=None):正则表达式匹配
#regex:The regular expression string to use. Can also be a compiled regular expression pattern.
# flags:旗标The regexp flags to use, for example re.IGNORECASE. Ignored if regex is not a string.
# message:Error message to raise in case of a validation error.

#  class wtforms.validators.EqualTo(fieldname, message=None):比较两个输入值
#fieldname:The name of the other field to compare to.
#message:Error message to raise in case of a validation error.


class ChangePasswordForm(Form):  #改变密码
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[
        DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm new password', validators=[DataRequired()])
    submit = SubmitField('Update Password')

# PasswordResetRequesetForm/PasswordRestForm 重设密码，忘记密码时可以重设
class PasswordResetRequestForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('Reset Password')

class PasswordResetForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('Unknown email address.')

class ChangeEmailForm(Form):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[Required()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

