import os.path as op

from flask import abort, Markup, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from flask_admin.menu import MenuLink
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask_admin.contrib.fileadmin import FileAdmin

from . import db, login_manager
from . import app, Admin, ModelView, AdminIndexView


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    hash_password = db.Column(db.String(120))
    role = db.Column(db.String(7), index=True)
    confirmed_account = db.Column(db.Boolean, default=False)
    student = db.relationship('Student', backref='base', uselist=False, cascade="all, delete")
    tutor = db.relationship('Tutor', backref='base', uselist=False, cascade="all, delete")
    location = db.relationship('Location', backref='User', uselist=False, cascade="all, delete")
    mycourse = db.relationship('Mycourse', backref='User', cascade="all, delete")
    followed = db.relationship(
        'User',secondary=followers,
        primaryjoin=(followers.c.follower_id==id),
        secondaryjoin=(followers.c.followed_id==id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )

    def __repr__(self):
        return '<Email {}>'.format(self.email)

    def set_password(self, password):
        self.hash_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hash_password, password)

    def set_location(self):
        self.location = Location(User=self)

    def update_location(self, **kwargs):
        for column,value in kwargs.items():
            location = self.location
            setattr(location,column,value)
        db.session.commit()

    def set_tutor(self):
        self.teacher = Tutor(base=self)

    def update_tutor(self, **kwargs):
        for column,value in kwargs.items():
            tutor = self.tutor
            setattr(tutor,column,value)
        db.session.commit()

    def set_student(self):
        self.student = Student(base=self)

    def update_student(self, **kwargs):
        for column,value in kwargs.items():
            student = self.student
            setattr(student,column,value)
        db.session.commit()

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0


    def get_reset_token(self,expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'],expires_sec)
        return s.dumps({'user_id':self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    # For confirmation through mail

    def get_confirmation_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'],expires_sec)
        return s.dumps({'user_id':self.id}).decode('utf-8')

    @staticmethod
    def verify_confirmation_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)


class Student(db.Model):
    phone = db.Column(db.String(10))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key = True,)
    full_name = db.Column(db.String(64))
    guardian_name = db.Column(db.String(64))
    guardian_address = db.Column(db.String(64))
    guardian_phone = db.Column(db.Integer)
    state = db.Column(db.String(64))
    district = db.Column(db.String(64))
    municipality = db.Column(db.String(64))
    ward_no = db.Column(db.Integer)
    date_of_birth = db.Column(db.String(64))
    profile_pic = db.Column(db.String(255))
    description = db.Column(db.String(250))

    def __repr__(self):
        student = User.query.filter_by(id = self.user_id ).first()
        return '<Email {}>'.format(student.email)


class Tutor(db.Model):
    phone = db.Column(db.String(10))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key = True,)
    full_name = db.Column(db.String(64))
    state = db.Column(db.String(64))
    district = db.Column(db.String(64))
    municipality = db.Column(db.String(64))
    ward_no = db.Column(db.Integer)
    date_of_birth = db.Column(db.String(64))
    profile_pic = db.Column(db.String(255))
    description = db.Column(db.String(250))
    account_verification_status = db.Column(db.Boolean, default=False)
    experience = db.relationship('Experience', backref='Tutor', uselist=True ,cascade="all, delete")
    qualification = db.relationship('Qualification', backref='Tutor', uselist=True ,cascade="all, delete")
    achievement = db.relationship('Achievement', backref='Tutor', uselist=True ,cascade="all, delete")

    def __repr__(self):
        tutor = User.query.filter_by(id = self.user_id ).first()
        return '<Email {}>'.format(tutor.email)


class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.user_id'))
    title = db.Column(db.String(255))
    institution = db.Column(db.String(255))
    experience = db.Column(db.String(255))
    experience_file = db.Column(db.String(255))


class Qualification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.user_id'))
    qualification = db.Column(db.String(255))
    institution = db.Column(db.String(255))
    qualification_date = db.Column(db.String(6))
    qualification_file = db.Column(db.String(255))


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.user_id'))
    achievement = db.Column(db.String(255))
    awarded_by = db.Column(db.String(255))
    awarded_date = db.Column(db.String(255))
    achievement_file = db.Column(db.String(255))


class Location(db.Model):
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    place_details = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_title = db.Column(db.String(100), nullable=False)
    course_level = db.Column(db.String(100), nullable=False)
    course_description = db.Column(db.String(1000))
    mycourse = db.relationship('Mycourse', backref='Course', cascade="all, delete")


class Mycourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    time = db.Column(db.Time)
    endtime = db.Column(db.Time)
    cost = db.Column(db.Integer)



@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


# Admin Panel


class AdminView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        abort(401)


admin = Admin(app, name='FYT Admin', template_mode='bootstrap3', index_view=AdminView())


class AdminAccountActivitiesView(AdminView):
    def __init__(self, *args, **kwargs):
        self._default_view = True
        super(AdminAccountActivitiesView, self).__init__(*args, **kwargs)
        self.admin = admin


class CustomView(ModelView):
    can_export = True
    can_create = False
    can_edit = True

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        abort(401)


class CannotDeleteView(CustomView):
    can_delete = False


class StudentView(CannotDeleteView):
    def _user_formatter(view, context, model, name):
        if model.profile_pic:
           markupstring = f"<a href='{url_for('static', filename='profile_pics/' + model.profile_pic)}'>{model.profile_pic}</a>"
           return Markup(markupstring)
        else:
           return ""

    column_formatters = {
        'profile_pic': _user_formatter
    }


class TutorView(StudentView):
    can_edit = True
    form_edit_rules = ['account_verification_status']


class ShowLinkView(CustomView):
    def _experience_formatter(view, context, model, name):
        if model.experience_file:
           markupstring = f"<a href='{url_for('static', filename='docs/experience/' + model.experience_file)}'>{model.experience_file}</a>"
           return Markup(markupstring)
        else:
           return ""

    def _qualification_formatter(view, context, model, name):
        if model.qualification_file:
           markupstring = f"<a href='{url_for('static', filename='docs/qualification/' + model.qualification_file)}'>{model.qualification_file}</a>"
           return Markup(markupstring)
        else:
           return ""

    def _achievement_formatter(view, context, model, name):
        if model.achievement_file:
           markupstring = f"<a href='{url_for('static', filename='docs/achievement/' + model.achievement_file)}'>{model.achievement_file}</a>"
           return Markup(markupstring)
        else:
           return ""

    column_formatters = {
        'experience_file': _experience_formatter,
        'achievement_file': _achievement_formatter,
        'qualification_file': _qualification_formatter
    }


class UserView(CustomView):
    column_exclude_list = ['hash_password',]
    column_searchable_list = ['username', 'email']
    column_filters = ['role']


class CourseView(ModelView):
    form_choices = {
        'course_level': [
            ('Basic Education(Grade 1-8)','Basic Education(Grade 1-8)'),
            ('Secondary Education(Grade 9-12)','Secondary Education(Grade 9-12)'),
            ('Bachelor Level','Bachelor Level'),
            ('Master Level','Master Level')
        ]
    }
    form_create_rules = ('course_title', 'course_level', 'course_description')
    form_edit_rules = ('course_title', 'course_level', 'course_description')


class LoggedInMenuLink(MenuLink):
    def is_accessible(self):
        return current_user.is_authenticated


# For general models, admin.add_view(ModelView(User, db.session))
admin.add_view(UserView(User, db.session, category='Users'))
admin.add_view(StudentView(Student, db.session, category='Users'))
admin.add_view(TutorView(Tutor, db.session, category='Users'))

admin.add_view(CannotDeleteView(Location, db.session))
admin.add_view(CourseView(Course, db.session))
admin.add_view(CustomView(Mycourse, db.session))

admin.add_view(ShowLinkView(Experience, db.session))
admin.add_view(ShowLinkView(Achievement, db.session))
admin.add_view(ShowLinkView(Qualification, db.session))

path = op.join(op.dirname(__file__), 'static/docs/')
admin.add_view(FileAdmin(path, '/static/docs/', name='Documents'))

admin.add_link(LoggedInMenuLink(name='Account Activities', category='Settings', url="/admin/account-activities"))
admin.add_link(LoggedInMenuLink(name='Logout', category='Settings', url="/logout"))
