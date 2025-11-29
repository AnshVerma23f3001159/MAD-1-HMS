from flask import Flask, render_template, redirect, url_for, request, flash
from config import Config
from models import db, User, Doctor, Patient, Appointment, Treatment
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from utils import role_required

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/register', methods=['GET','POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            name = request.form.get('name') or username
            contact = request.form.get('contact') or ''
            if User.query.filter_by(username=username).first():
                flash('That username is already taken. Please choose another.', 'warning')
                return redirect(url_for('register'))
            user = User(username=username, email=email, role='patient')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            patient = Patient(user_id=user.id, name=name, contact=contact)
            db.session.add(patient)
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
        return render_template('auth/register.html')

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Welcome back!', 'success')
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                if user.role == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                return redirect(url_for('patient_dashboard'))
            flash('Invalid username or password.', 'danger')
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/admin/dashboard')
    @login_required
    @role_required('admin')
    def admin_dashboard():
        total_doctors = Doctor.query.count()
        total_patients = Patient.query.count()
        total_appointments = Appointment.query.count()
        doctors = Doctor.query.all()
        return render_template(
            'admin/dashboard.html',
            total_doctors=total_doctors,
            total_patients=total_patients,
            total_appointments=total_appointments,
            doctors=doctors
        )

    @app.route('/admin/doctors')
    @login_required
    @role_required('admin')
    def admin_doctors():
        doctors = Doctor.query.all()
        return render_template('admin/doctors.html', doctors=doctors)

    @app.route('/admin/doctor/add', methods=['GET','POST'])
    @login_required
    @role_required('admin')
    def admin_add_doctor():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form.get('email') or f"{username}@hospital.com"
            password = request.form.get('password') or 'doctor123'
            name = request.form['name']
            specialization = request.form['specialization']
            availability = request.form.get('availability','')
            if User.query.filter_by(username=username).first():
                flash('That username already exists. Try another.', 'warning')
                return redirect(url_for('admin_add_doctor'))
            user = User(username=username, email=email, role='doctor')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            doctor = Doctor(user_id=user.id, name=name, specialization=specialization, availability=availability)
            db.session.add(doctor)
            db.session.commit()
            flash('Doctor added successfully.', 'success')
            return redirect(url_for('admin_doctors'))
        return render_template('admin/doctor_form.html', action='Add')

    @app.route('/admin/doctor/<int:doc_id>/edit', methods=['GET','POST'])
    @login_required
    @role_required('admin')
    def admin_edit_doctor(doc_id):
        doctor = Doctor.query.get_or_404(doc_id)
        if request.method == 'POST':
            doctor.name = request.form['name']
            doctor.specialization = request.form['specialization']
            doctor.availability = request.form.get('availability','')
            db.session.commit()
            flash('Doctor profile updated.', 'success')
            return redirect(url_for('admin_doctors'))
        return render_template('admin/doctor_form.html', action='Edit', doctor=doctor)

    @app.route('/admin/doctor/<int:doc_id>/delete', methods=['POST'])
    @login_required
    @role_required('admin')
    def admin_delete_doctor(doc_id):
        doctor = Doctor.query.get_or_404(doc_id)
        user = doctor.user
        db.session.delete(doctor)
        if user:
            db.session.delete(user)
        db.session.commit()
        flash('Doctor removed from the system.', 'info')
        return redirect(url_for('admin_doctors'))

    @app.route('/doctor/dashboard')
    @login_required
    @role_required('doctor')
    def doctor_dashboard():
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if not doctor:
            flash('Doctor profile not found.', 'warning')
            return redirect(url_for('index'))
        upcoming = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.date.asc()).all()
        return render_template('doctor/dashboard.html', doctor=doctor, appointments=upcoming)

    @app.route('/doctor/appointment/<int:app_id>/complete', methods=['POST'])
    @login_required
    @role_required('doctor')
    def doctor_mark_complete(app_id):
        appointment = Appointment.query.get_or_404(app_id)
        appointment.status = 'Completed'
        diagnosis = request.form.get('diagnosis','')
        prescription = request.form.get('prescription','')
        notes = request.form.get('notes','')
        if appointment.treatment:
            appointment.treatment.diagnosis = diagnosis
            appointment.treatment.prescription = prescription
            appointment.treatment.notes = notes
        else:
            tr = Treatment(appointment_id=appointment.id, diagnosis=diagnosis, prescription=prescription, notes=notes)
            db.session.add(tr)
        db.session.commit()
        flash('Appointment completed and treatment saved.', 'success')
        return redirect(url_for('doctor_dashboard'))

    @app.route('/patient/dashboard')
    @login_required
    @role_required('patient')
    def patient_dashboard():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        doctors = Doctor.query.all()
        upcoming = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date.asc()).all()
        return render_template('patient/dashboard.html', patient=patient, doctors=doctors, appointments=upcoming)

    @app.route('/patient/book/<int:doc_id>', methods=['GET','POST'])
    @login_required
    @role_required('patient')
    def patient_book(doc_id):
        doctor = Doctor.query.get_or_404(doc_id)
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if request.method == 'POST':
            date_str = request.form['date']
            time = request.form['time']
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            conflict = Appointment.query.filter_by(doctor_id=doctor.id, date=date_obj, time=time, status='Booked').first()
            if conflict:
                flash('Sorry, that time slot is already taken. Please choose another.', 'danger')
                return redirect(url_for('patient_book', doc_id=doc_id))
            appt = Appointment(patient_id=patient.id, doctor_id=doctor.id, date=date_obj, time=time, status='Booked')
            db.session.add(appt)
            db.session.commit()
            flash('Your appointment has been booked.', 'success')
            return redirect(url_for('patient_dashboard'))
        return render_template('patient/book.html', doctor=doctor)

    @app.route('/patient/appointment/<int:app_id>/cancel', methods=['POST'])
    @login_required
    @role_required('patient')
    def patient_cancel(app_id):
        appt = Appointment.query.get_or_404(app_id)
        appt.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled.', 'info')
        return redirect(url_for('patient_dashboard'))

    @app.route('/patient/history')
    @login_required
    @role_required('patient')
    def patient_history():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.date.desc()).all()
        return render_template('patient/history.html', appointments=appointments)

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        from models import User
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@hospital.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created default admin: admin/admin123")
    app.run(debug=True)
