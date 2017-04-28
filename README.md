[预览地址](https://fzhihu.herokuapp.com/)
___

# zhihu(python 2.7)
* 1.flask仿知乎做的web
 * 支持基本功能-注册验证用户
 * 提问，回答，评论，点赞，用户互相关注
 * 支持中文检索（用的是Flask-WhooshAlchemyPlus+jieba(中文分词)）
___
* 2.安装步骤
  * virtutal env
  * pip install -r requirements.txt
___
window 下
* set MAIL_USERNAME="xxx@qq.com"(我用的是QQ SMTP，所以用QQ邮箱）
* set MAIL_PASSWORD="xxxxx" （授权密码）
* set FLASK_ADMIN="XXX@qq.com" (你admin账号）
* python manage.py deploy
* python manage.py runserver
