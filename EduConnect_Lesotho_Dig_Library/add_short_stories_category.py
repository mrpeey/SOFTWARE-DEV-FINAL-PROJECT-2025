from app import create_app, db
from app.models.book import Category

app = create_app()
with app.app_context():
    name = "Short Stories, Poems and Essays"
    description = "A collection of short stories, poems, and essays from various authors."
    existing = Category.query.filter_by(name=name).first()
    if existing:
        print(f"Category already exists: {name}")
    else:
        cat = Category(name=name, description=description)
        db.session.add(cat)
        db.session.commit()
        print(f"Added category: {name}")