from sqladmin import Admin, ModelView
from fastapi import FastAPI
from app.db.models import Source, User
from app.db.session import engine

class SourceAdmin(ModelView, model=Source):
    column_list = [Source.id, Source.name, Source.url, Source.is_active]
    column_searchable_list = [Source.name]

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.is_active]

async def init_app(app: FastAPI):
    admin = Admin(
        app=app,
        engine=engine,
        title="PingBrief Admin",
    )

    admin.add_view(SourceAdmin)
    admin.add_view(UserAdmin)
