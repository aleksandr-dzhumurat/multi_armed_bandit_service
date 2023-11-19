from fastapi import FastAPI
from pydantic import BaseModel
import names


from src.utils import ContentDB, UserDB

class Action(BaseModel):
    user_token: str
    user_name: str
    item_id: int
    item_tag: str
    action_type: str

class User(BaseModel):
    user_name: str

content_db = ContentDB()
content_db.init_db()
#
users_db = UserDB()
users_db.init_db()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/user_name")
async def root():
    user_name = names.get_full_name().lower().replace(' ', '_')
    return {"user_name": user_name}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = content_db.get_content(item_id)
    return {"item": item}

@app.post("/random")
async def random_item(user: User):
    user_id, user_actions = users_db.get_user_actions(user.user_name)
    return content_db.get_random_content(user_actions)

@app.post("/action")
async def action(action: Action):
    users_db.push_action(action.user_token, action.item_id, action.item_tag, action.action_type)
    return {"result": "ok"}

@app.post("/auth")
async def auth(user: User):
    print(user.dict())
    bearer_token = users_db.create_user(user.user_name)
    return {"Bearer": bearer_token}

@app.post("/recommend")
async def recommend(user: User):
    _, user_actions = users_db.get_user_actions(user.user_name)
    recs_list = content_db.recommend(user_actions)
    return {"recs": recs_list}
