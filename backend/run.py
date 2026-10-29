from app.config import settings
from app import create_app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.FLASK_DEBUG
    )
