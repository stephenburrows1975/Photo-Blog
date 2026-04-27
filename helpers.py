from fasthtml.common import *
from datetime import datetime
import bcrypt
#comment test
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
def build_card(p, comments, likes, users, is_admin=False):
    comment_items = []
    for c in comments(where=f"photo_id={p['id']}"):
        commenter = users(where=f"id={c['user_id']}")
        name = commenter[0]['name'] if commenter else 'Unknown'
        comment_items.append(P(cls="comment")(f"{name}: {c['comment']}"))
    likes_count = len(likes(where=f"photo_id={p['id']}"))
    day = str(int(p['date'].split('-')[2]))  # removes leading zero cross-platform
    return Div(cls="photo-card")(
        H2(p['location'], " - ", datetime.strptime(p['date'], '%Y-%m-%d').strftime(f'%B, {day}, %Y')),
        Img(src=p['url'], alt=p['description']),
        Div(cls="card-actions")(
            P(f"{likes_count} like{'s' if likes_count != 1 else ''}"),
            Div(cls="push-right")(
                A("✏️", href=f"/photos/edit/{p['id']}") if is_admin else None,
                Form(method="post", action="/like")(
                    Button("🙂", type="submit"),
                    Input(type="hidden", name="photo_id", value=p['id'])
                ),
                Form(method="post", action="/comment")(
                    Button("💬", type="button", hx_get=f"/comment-form/{p['id']}", 
                        hx_target=f"#comment-form-{p['id']}", hx_swap="innerHTML"),
                    Input(type="hidden", name="photo_id", value=p['id']),
                )
            )
        ),
        Div(id=f"comment-form-{p['id']}"),
        P(p['description']),
        P(cls="bold-text")("Comments:"),
        *comment_items,
        )

def user_checker(users, req):
    user = users(where=f"username='{req.cookies.get('user')}'")
    if not req.cookies.get('user'):
        print("No user cookie found")
        return RedirectResponse('/', status_code=303)
    if not user:
        print("User not found in database")
        return RedirectResponse('/', status_code=303)
    user_id = user[0]['id']
    return user_id

def admin_checker(users, req):
    if not req.cookies.get('user'):
        return RedirectResponse('/')
    user = users(where=f"username='{req.cookies.get('user')}'")
    if not user or not user[0]['is_admin']:
        return "Access denied"
    return user[0]['id']
