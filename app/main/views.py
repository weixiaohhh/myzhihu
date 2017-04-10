# coding:utf-8
import sys  
reload(sys)  
sys.setdefaultencoding('utf8')

from flask import render_template, abort ,flash ,redirect, url_for, request, current_app, make_response,g
from flask_login import login_required, current_user
from . import main
from app.models import User, Role, Permission, Answer, Comment, Question, Prove
from .forms import EditProfileForm, EditProfileAdminForm, CommentForm, QuestionForm, AnswerForm, SearchForm
from .. import db
from ..decorators import admin_required, permission_required

@main.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        db.session.add(g.user)
        db.session.commit()
        g.search_form = SearchForm()
		
		
@main.route('/', methods=['GET','POST'])
def index():

    page = request.args.get('page', 1, type=int)
    #渲染页数从请求的查询字符串(request.args)获取，没有指定默认为1，type=int保证参数无法转换为证书，返回默认值
    show_followed = False
    show_self = False
    #如果show_followed=1则显示用户关注的用户的提问，show_followed=0 and show_self=1
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed'))
        show_self = bool(request.cookies.get('show_self'))
    if show_followed:
        query = current_user.followed_questions  #show_followed=1 显示所关注用户的提问
    elif show_self:
        query = current_user.self_questions       #show_followed=0的情况下，show_self=1，显示自己的问题
    else:
        query = Question.query                    #show_followed=0 and show_self=0 显示所有问题
    pagination = query.order_by(Question.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASK_QUESTIONS_PER_PAGE'],error_out=False
    )
    #Question.query.order_by(Question.timestamp.desc()).all()  #desc（）降序，离现在最近的排在最上面
    #page页数，必须的参数；per_page每页数量，默认20；error_out设为True则页数超过范围返回空
    questions = pagination.items   #items当前页面的记录
    return render_template('index.html', questions=questions, 
							show_followed=show_followed, 
							show_self=show_self,pagination=pagination)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.answers.order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASK_ANSWERS_PER_PAGE'], error_out=False
    )
    answers = pagination.items
    questions = user.questions.all()
    return render_template('user.html', user=user, answers=answers, questions=questions, pagination=pagination)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user',username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>', methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    #get_or_404():Like get() but aborts with 404 if not found instead of returning None.
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data =user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route('/make-question', methods=['GET', 'POST']) #提问功能
def make_question():
    form = QuestionForm()
    if current_user.can(Permission.QUESTION) and form.validate_on_submit():
        question = Question(title=form.title.data, body=form.body.data,
						author=current_user._get_current_object())
        #数据库需要真正对象，而current_user是通过线程内的代理对象实现的，需要使用_get_current_object()
        db.session.add(question)
        flash('你已经成功提问')
        return redirect(url_for('.user', username=current_user.username))
    return render_template('make-question.html', form=form)

@main.route('/question/<int:id>', methods=['GET', 'POST'])  #查看一个问题，可以进行回答
def question(id):
    question = Question.query.get_or_404(id)
    form = AnswerForm()
    if form.validate_on_submit():
        answer = Answer(body=form.body.data, question=question, author=current_user._get_current_object(), question_title = question.title)
        db.session.add(answer)
        flash('回答成功!')
        return redirect(url_for('.question',id=question.id, page=-1)) #page=-1用来请求最后一页
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (question.answers.count() - 1 ) // current_app.config['FLASK_ANSWERS_PER_PAGE'] + 1
    pagination = question.answers.order_by(Answer.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASK_ANSWERS_PER_PAGE'], error_out=False
    )#新答案显示在底部
    answers = pagination.items
    return render_template('question.html', form=form, questions=[question], answers=answers, pagination=pagination)

@main.route('/answer/<int:id>', methods=['GET', 'POST'])
def answer(id):
    answer = Answer.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, answer=answer, author=current_user._get_current_object())
        db.session.add(comment)
        flash('Your comment has been published.')
        return redirect(url_for('.answer', id=answer.id, page=-1)) #page=-1用来请求最后一页
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (answer.comments.count() - 1) // current_app.config['FLASK_COMMENTS_PER_PAGE'] + 1
    pagination = answer.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASK_COMMENTS_PER_PAGE'], error_out=False
    ) #新评论显示在底部
    comments = pagination.items
    return render_template('answer.html', answers=[answer], form=form, comments=comments, pagination=pagination)

@main.route('/prove/<int:id>', methods=['GET', 'POST'])
def prove(id):
    answer = Answer.query.get_or_404(id)
    prove = Prove(prover=current_user._get_current_object() , answer=answer)
    db.session.add(prove)
    flash('你已经赞了该答案.')
    return redirect(url_for('.answer', id=id))

@main.route('/unprove/<int:id>', methods=['GET', 'POST'])
def unprove(id):
    p = db.session.query(Prove).join(User, Prove.prover_id == User.id).filter(Prove.answer_id == id).first()
    db.session.delete(p)
    flash('你已经取消了赞.')
    return redirect(url_for('.answer', id=id))

@main.route('/provelist/<int:id>', methods=['GET', 'POST'])
def provelist(id):
	all_prover = Prove.query.filter_by(answer_id=id).all()
	all_prover_user = []
	for prover in all_prover:
	    all_prover_user.append(User.query.get_or_404(prover.prover_id))
	return render_template('prove_user.html', all_prover_user=all_prover_user)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    answer = Answer.query.get_or_404(id)
    if current_user != answer.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = AnswerForm()
    if form.validate_on_submit():
        answer.body = form.body.data
        db.session.add(answer)
        flash('The answer has been updated.')
        return redirect(url_for('.answer', id=answer.id))
    form.body.data = answer.body
    return render_template('edit_answer.html', form=form)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    #关注某个用户
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('不存在该用户')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('已关注该用户')
        return redirect(url_for('.user', usernmae=username))
    current_user.follow(user)
    flash('成功关注  %s.' % username)
    return redirect(url_for('.user', username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    #取消关注某用户
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('不存在该用户')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('未关注该用户')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('已经取消关注 %s' %username)
    return redirect(url_for('.user', username=username))

@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASK_FOLLOWERS_PER_PAGE'],error_out=False
    )
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)

@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASK_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/all')  #决定首页显示的是否为全部提问
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60) #第12个参数是cookie的名和值，max_age是过期时间
    resp.set_cookie('show_self', '', max_age=30*24*60*60)
    return resp

@main.route('/followed')  #决定首页显示的是否为用户关注的用户的提问
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    resp.set_cookie('show_self', '', max_age=30*24*60*60)
    return resp

@main.route('/self')   #决定首页显示的是否为用户自身的提问
@login_required
def show_self():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    resp.set_cookie('show_self', '1', max_age=30*24*60*60)
    return resp

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASK_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments, pagination=pagination, page=page)

@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))

@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


MAX_SEARCH_RESULTS = 50							
@main.route('/search', methods = ['GET','POST']) 
@login_required							
def search():
    form = SearchForm()
    if form.validate_on_submit():

        info = form.search.data
        results = Question.query.whoosh_search(info, MAX_SEARCH_RESULTS,like=True).all()
        return render_template('search_results.html',
                               info=info,
                               results=results)
    flash(u'输入错误')
    return redirect(url_for('.index'))
