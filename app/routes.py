from flask import (
    render_template, 
    redirect, 
    url_for, 
    jsonify, 
    request, 
    flash,
    session,
    abort,
    jsonify,
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
)

import os
import secrets
from PIL import Image

from . import app, db
from . import login_manager
from . import email as em
from .forms import (
    RegistrationForm, 
    LoginForm, 
    ResetForm, 
    ResetLinkForm, 
    MyLocationForm, 
    PersonalInfoForm,
    StudentPersonalInfoForm,
    AccountInfoForm,
    MyCourseForm,
    MyExperienceForm,
    MyAchievementForm,
    MyQualificationForm
)
from .models import User, Student, Tutor, Location, Course


def redirect_user(user):
    if user.role == 'student':
        return redirect(url_for('student'))
    elif user.role == 'tutor':
        return redirect(url_for('tutor'))
    elif user.role == 'admin':
        return redirect('/admin')


def is_tutor(user):
    if user.role == 'tutor':
        return True
    elif user.role == 'student':
        return False
    elif user.role == 'admin':
        return False


@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('home'))


@app.route('/home')
def home():
    if current_user.is_authenticated:
        return redirect_user(current_user)
    return render_template('index.html')


@app.route('/about-us')
def about_us():
    """ Render the about us page """
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_user(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect (url_for('login'))
        login_user(user)
        flash('Successfully logged in.', 'success')
        return redirect_user(current_user)
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if current_user.is_authenticated:
        return redirect_user(current_user)
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        if is_tutor(user):
            user.set_tutor()
            user.update_tutor(phone=form.phone.data)
        else:
            user.set_student()
            user.update_student(phone=form.phone.data)
        user.set_location()
        db.session.commit()
        #message = "Welcome to Find Your Tutor"
        #em.send_mail(username, role, message, email)
        flash('Your account was created.\nYou can now Login!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/password-reset', methods=['GET', 'POST'])
def passwordresetlink():
    form = ResetLinkForm()
    email = form.email.data
    if form.validate_on_submit():
        em.send_reset_mail(email)
        return redirect(url_for('login'))
    return render_template('resetlink.html', form=form)


@app.route('/reset', methods=['GET', 'POST'])
def passwordreset():
    form = ResetForm()
    unhashed_password = form.password.data
    return render_template('reset.html', form=form)


@app.route('/hello/<token>')
def hello(token):
    try:
        email = ser.loads(token, salt='email-confirm', max_age=36)
    except :
        return '<h1>The token has expired!<h1>'
    return '<h1>The token is valid!<h1>'


@app.route("/logout")
def logout():
    logout_user()
    flash('You are now logged out. Log in to continue!', 'success')
    return redirect(url_for('login'))


# Utility functions


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125,125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def delete_picture(user_picture):
    f_name, f_ext = os.path.splitext(user_picture)
    location = "/static/profile_pics"
    picture_fn = f_name + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    os.remove(picture_path)


def fetch_default_profile_pic(user_obj):
    if isinstance(user_obj, Tutor):
        return url_for('static', filename='profile_pics/tutor.jpg')
    else:
        return url_for('static', filename='profile_pics/student.jpeg')


def fetch_profile_pic(user_obj):
    try:
        pic_name_from_db = getattr(user_obj, 'profile_pic')
        picture_path = os.path.join(app.root_path, 'static/profile_pics')
        if pic_name_from_db in os.listdir(picture_path):
            profile_pic = url_for('static',filename='profile_pics/' + pic_name_from_db)
            return profile_pic
        return fetch_default_profile_pic(user_obj)
    except:
        return fetch_default_profile_pic(user_obj)


# Student Routes


@app.route('/student/profiles/<username>')
@login_required
def student_profile(username):
   return f"{username}'s profile'"


@app.route('/student/home')
@login_required
def student():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect('/admin')
    user = User.query.filter_by(username=current_user.username).first()
    if user.username == current_user.username and user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        return render_template('student.html', user=user, student=student, profilepic= fetch_profile_pic(student))
    abort(404)


@app.route('/student/mylocation', methods=['POST','GET'])
@login_required
def student_location():
    form = MyLocationForm()
    form.create_travel_distance_choice()
    google_api = app.config.get('GOOGLE_MAP_API_KEY')
    opencage_api = app.config.get('OPENCAGE_GEOCODE_API_KEY')
    user = User.query.filter_by(username=current_user.username).first()
    if form.validate_on_submit():
        user.update_location(
            travel_distance=form.travel_distance.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            place_details=form.place.data
        )
    location = Location.query.filter_by(user_id=user.id).first()
    
    if user.username == current_user.username and not is_tutor(user):
        student=Student.query.filter_by(user_id=user.id).first()
        return render_template("mylocation.html", user=user, student=student, profilepic= fetch_profile_pic(student), form=form, google_api_key=google_api,
            opencage_api_key=opencage_api, location=location)
    elif user.username == current_user.username and is_tutor(user):
        return redirect(url_for('tutor_location'))


@app.route('/student/personal-info', methods=['POST','GET'])
@login_required
def student_personal_info():
    if is_tutor(current_user):
        return redirect(url_for('tutor_personal_info'))
    else:
        user = User.query.filter_by(username=current_user.username).first()
        student=Student.query.filter_by(user_id=user.id).first()
        form = StudentPersonalInfoForm()
        form.create_state_choices()
        form.create_district_choices()
        if form.validate_on_submit():
            if form.profile_pic.data:
                if student.profile_pic:
                    delete_picture(student.profile_pic)
                current_user.update_student(profile_pic = save_picture(form.profile_pic.data))
            current_user.update_student(
                full_name=form.name.data, 
                state=form.state.data,
                district = form.district.data,
                date_of_birth = form.date_of_birth.data,
                municipality = form.municipality.data,
                ward_no = form.ward_no.data,
                phone = form.phone.data ,
                description = form.self_description.data,
                guardian_name = form.guardian_name.data,
                guardian_address = form.guardian_address.data,
                guardian_phone = form.guardian_phone.data
                
            )
        return render_template("personal-info.html", user=user, user_obj=student, profilepic= fetch_profile_pic(student), form=form)


@app.route('/student/account-info', methods=['POST','GET'])
@login_required
def student_account_info():
    form = AccountInfoForm()
    user = User.query.filter_by(username=current_user.username).first()
    if user.username == current_user.username and not is_tutor(user):
        student = Student.query.filter_by(user_id=user.id).first()
        if form.validate_on_submit():
            if not user.check_password(form.old_password.data):
                flash("Wrong password!","danger")
                return redirect(url_for('student_account_info'))
            else:
                user.set_password(form.new_password.data)
                db.session.commit()
                flash("Successfully changed password!", "success")
                return redirect(url_for('student'))
        return render_template("account-info.html", user=user, student=student, profilepic= fetch_profile_pic(student), form=form)
    elif user.username == current_user.username and is_tutor(user):
        return redirect(url_for('tutor_account_info'))


@app.route('/student/my-courses', methods=['POST','GET'])
@login_required
def student_courses():
    form = MyCourseForm()
    form.create_cost_choices()
    
    user = User.query.filter_by(username=current_user.username).first()
    
    if user.username == current_user.username and not is_tutor(user):
        student = Student.query.filter_by(user_id=user.id).first()
        return render_template("my-courses.html", user=user, student=student, profilepic= fetch_profile_pic(student), form=form, values='')
    elif user.username == current_user.username and is_tutor(user):
        return redirect(url_for('tutor'))


@app.route('/student/my-tutors', methods=['POST', 'GET'])
@login_required
def student_followed_tutors():
    user = User.query.filter_by(username=current_user.username).first()

    if user.username == current_user.username and not is_tutor(user):
        student = Student.query.filter_by(user_id=user.id).first()
        return render_template('my-tutors.html', profilepic= fetch_profile_pic(student), user=user)
    elif user.username == current_user.username and is_tutor(user):
        return redirect(url_for('tutor_followers'))
        


# Tutor Routes


@app.route('/tutor/profiles/<username>')
@login_required
def tutor_profile(username):
    return f"{username}'s profile"


@app.route('/tutor/home')
@login_required
def tutor():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect('/admin')
    user = User.query.filter_by(username=current_user.username).first()
    if user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        return render_template("tutor.html", user=user, tutor=tutor, profilepic= fetch_profile_pic(tutor))
    abort(404)


@app.route('/tutor/mylocation', methods=['POST','GET'])
@login_required
def tutor_location():
    form = MyLocationForm()
    form.create_travel_distance_choice()
    google_api = app.config.get('GOOGLE_MAP_API_KEY')
    opencage_api = app.config.get('OPENCAGE_GEOCODE_API_KEY')
    user = User.query.filter_by(username=current_user.username).first()
    if form.validate_on_submit():
        user.update_location(
            travel_distance=form.travel_distance.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            place_details=form.place.data
        )
    location = Location.query.filter_by(user_id=user.id).first()
    
    if user.username == current_user.username and not is_tutor(user):
        return redirect(url_for('student_location'))
    elif user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        return render_template("mylocation.html", user=user, tutor=tutor, profilepic= fetch_profile_pic(tutor), form=form, google_api_key=google_api,
            opencage_api_key=opencage_api, location=location)


@app.route('/tutor/personal-info', methods=['POST' ,'GET'])
@login_required
def tutor_personal_info():
    if is_tutor(current_user):
        user = User.query.filter_by(username=current_user.username).first()
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        form = PersonalInfoForm()
        form.create_state_choices()
        form.create_district_choices()
        if form.validate_on_submit():   
            if form.profile_pic.data:
                if tutor.profile_pic:
                    delete_picture(tutor.profile_pic)
                user.update_tutor(profile_pic = save_picture(form.profile_pic.data))
            user.update_tutor(
                full_name=form.name.data, 
                state=form.state.data,
                district = form.district.data,
                date_of_birth = form.date_of_birth.data,
                municipality = form.municipality.data,
                ward_no = form.ward_no.data,
                phone = form.phone.data,
                description = form.self_description.data
            )
        return render_template("personal-info.html", user=user, user_obj=tutor, profilepic= fetch_profile_pic(tutor), form=form)
    else:
        return redirect(url_for('student_personal_info'))


@app.route('/tutor/account-info', methods=['POST','GET'])
@login_required
def tutor_account_info():
    form = AccountInfoForm()
    user = User.query.filter_by(username=current_user.username).first()
    if user.username == current_user.username and not is_tutor(user):
        return redirect(url_for('student_account_info'))
    elif user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        if form.validate_on_submit():
            if not user.check_password(form.old_password.data):
                flash("Wrong password!","danger")
                return redirect(url_for('tutor_account_info'))
            else:
                user.set_password(form.new_password.data)
                db.session.commit()
                flash("Successfully changed password!", "success")
                return redirect(url_for('tutor'))
        return render_template("account-info.html", user=user, tutor=tutor, profilepic=fetch_profile_pic(tutor), form=form)


@app.route('/tutor/my-courses', methods=['POST', 'GET'])
@login_required
def tutor_courses():
    form = MyCourseForm()
    form.create_cost_choices()
    form.education_level.choices=[('Basic Education(Grade 1-8)','Basic Education(Grade 1-8)'),('Secondary','Secondary'),('Bachelor','Bachelor')]
    form.course.choices=[('Physics','Physics'),('Computer','Computer'),('Health','Health')]
    mock_courses = [('Basic Education(Grade 1-8)','Science','19:00','Rs. 1000 - Rs. 1500'),('Bachelor','Physics','20:00','Rs. 4000 - Rs. 4500')]
    
    user = User.query.filter_by(username=current_user.username).first()
    
    if user.username == current_user.username and not is_tutor(user):
        return redirect(url_for('student'))
    elif user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        return render_template("my-courses.html", user=user, tutor=tutor, profilepic=fetch_profile_pic(tutor), form=form, values=mock_courses)


@app.route('/tutor/my-profile', methods=['POST','GET'])
@login_required
def tutor_educational_profile():
    form_experience = MyExperienceForm()
    form_qualification = MyQualificationForm()
    form_achievement = MyAchievementForm()
    user = User.query.filter_by(username=current_user.username).first()
    
    if user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        return render_template('my-profile.html', profilepic=fetch_profile_pic(tutor), user=user, tutor=tutor,
            form_experience=form_experience, form_qualification=form_qualification, form_achievement=form_achievement)
    elif user.username == current_user.username and not is_tutor(user):
        return redirect(url_for('student'))


@app.route('/tutor/my-followers', methods=['POST', 'GET'])
@login_required
def tutor_followers():
    user = User.query.filter_by(username=current_user.username).first()

    if user.username == current_user.username and not is_tutor(user):
        return redirect(url_for('student_followed_tutors'))
    elif user.username == current_user.username and is_tutor(user):
        tutor=Tutor.query.filter_by(user_id=user.id).first()
        return render_template('my-followers.html', profilepic=fetch_profile_pic(tutor), tutor=tutor, user=user)


@app.route('/courses')
@login_required
def courses():
    user = User.query.filter_by(username=current_user.username).first()
    if is_tutor(user):
        user_obj = Tutor.query.filter_by(user_id=user.id).first()
    else:
        user_obj = Student.query.filter_by(user_id=user.id).first()
    courses = Course.query.all()
    return render_template('courses.html',profilepic=fetch_profile_pic(user_obj), courses=courses,user=user)
    

@app.route('/courses/<int:id>')
def courses_by_id(id):
    course = Course.query.filter_by(id=id).first_or_404()
    return course.course_title
# Error Handlers


@app.errorhandler(404)
def content_not_found_handler(e):
    """ For Handling 404 error """
    return render_template('404.html')


@app.errorhandler(401)
def unauthorized_access_handler(e):
    """ For Handling 401 error """
    flash('You must be logged in to access this page!', 'danger')
    return redirect(url_for('login'))