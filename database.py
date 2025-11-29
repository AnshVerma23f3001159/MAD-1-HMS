def init_db():
    from app import create_app
    from models import db, User

    app = create_app()
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@hospital.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created default admin: admin / admin123")
        else:
            print("Admin already exists")

if __name__ == "__main__":
    init_db()
