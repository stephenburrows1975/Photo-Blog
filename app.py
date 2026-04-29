from unittest import result
from fasthtml.common import *
from dataclasses import dataclass
from datetime import datetime
from helpers import *
from starlette.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import boto3

load_dotenv()

#comment test
@dataclass
class Registration: 
    email:str 
    password:str
    firstname:str 
    surname:str

app, rt = fast_app(
    hdrs=(Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css'),
          Link(rel='stylesheet', href='/static/styles.css')
    )
)
app.mount("/static", StaticFiles(directory="static"), name="static")

db = database('photo_blog.db')
users = db.t.users
photos = db.t.photos
likes = db.t.likes
comments = db.t.comments
if users not in db.t:
    users.create(id=int, username=str, password=str, name=str, pk='id', is_approved=int, is_admin=int)
if photos not in db.t:
    photos.create(id=int, description=str, url=str, pk='id', location=str, date=str)
if likes not in db.t:
    likes.create(id=int, user_id=int, photo_id=int, pk='id')
if comments not in db.t:
    comments.create(id=int, user_id=int, photo_id=int, comment=str, pk='id')


if not photos():
    photos.insert(description="My first photo", url="https://picsum.photos/600/400", location="London", date="2026-03-31")
    
if not users():
    users.insert(username="steve", password=hash_password("testpass123"), name="Steve Burrows", is_admin=1, is_approved=1)

@rt('/')
def get(req: Request):
    if req.cookies.get('user'):
        return RedirectResponse('/photos')
    return Div(
        Title("Steve's Photo Blog"),
        Div(cls="page")(
        Main(Container(
            Header(H1("Steve's photos")),
            Div(
                P("I don't want to use instagram anymore, but I still want to share my photos with the world. So here we are!"),
                Img(src="https://picsum.photos/800/400", alt="Random photo"),
                P(),
                P("Please complete the form below to sign up and view my photos."),
                Form(method="post", action="/")(
                    Fieldset(
                     Input(type="email", name="email", placeholder="Enter your email"), 
                     Input(type="password", name="password", placeholder="Enter your password")),
                     Button("Sign Up", type="submit")
            ))       
            )
        ))
        )

@rt('/', methods=['POST'])
def post(email:str, password:str):
    existing_user = users(where=f"username='{email}'")
    if existing_user:
        if verify_password(password, existing_user[0]['password']):
            # password correct - set cookie and redirect
            response = RedirectResponse('/photos', status_code=303)
            response.set_cookie('user', existing_user[0]['username'])
            return response
        else:
            return "Incorrect password"
    else:
        return RedirectResponse(f'/register?email={email}', status_code=303)

@rt('/admin')
def admin_page(req: Request):
    #refer to helpers.py for code for admin_checker
    admin_checker(users, req)
    awaiting_approval = users(where="is_approved=0")
    active_users = users(where="is_approved=1")   
    unapproved_users = []
    approved_users = []
    for u in awaiting_approval:
        unapproved_users.append(u)
    for u in active_users:
        approved_users.append(u)
    return Div(
        H1("Admin Panel"),
        P("Return to ", A("photo feed", href="/photos")),
        Table(
            Thead(Tr(Th("ID"), Th("Username"), Th("Name"), Th("Approve"), Th("Reject"))),
            Tbody(*[Tr(Td(u['id']), Td(u['username']), Td(u['name']), 
                       Td(Form(method="post", action="/approve")(
                            Button("Approve", type="submit"),
                            Input(type="hidden", name="user_id", value=u['id'])
                        )),
                       Td(Form(method="post", action="/reject")(
                            Button("Reject", type="submit"),
                Input(type="hidden", name="user_id", value=u['id'])
                )
            )) for u in unapproved_users]),
        Table(
            Thead(Tr(Th("ID"), Th("Username"), Th("Name"), Th("Status"), Th("Admin"), Th("Edit?"))),
            Tbody(*[Tr(Td(u['id']), Td(u['username']), Td(u['name']), Td(u['is_approved']), 
                       Td(u['is_admin']), Td(A("Edit", href=f"/admin/edit/{u['id']}"))
            ) for u in approved_users]
            )
        ))
    )

@rt('/admin/edit/{user_id}', methods=['GET'])
def edit_user_page(user_id: int, req: Request):
    #refer to helpers.py for code for admin_checker
    admin_checker(users, req)
    user_to_edit = users(where=f"id={user_id}")
    if not user_to_edit:
        return "User not found"
    user_to_edit = user_to_edit[0]
    return Div(
        H1(f"Edit User: {user_to_edit['username']}"),
        Form(method="post", action=f"/admin/edit/{user_id}")(
            Fieldset(
                Input(type="email", name="email", placeholder="Enter email", value=user_to_edit['username']),
                Input(type="text", name="name", placeholder="Enter name", value=user_to_edit['name']),
                Select(name="is_approved")(
                    Option("Approved", value="1", selected=user_to_edit['is_approved'] == 1),
                    Option("Not Approved", value="0", selected=user_to_edit['is_approved'] == 0)
                ),
                Select(name="is_admin")(
                    Option("Admin", value="1", selected=user_to_edit['is_admin'] == 1),
                    Option("User", value="0", selected=user_to_edit['is_admin'] == 0)
                ),
                Button("Save Changes", type="submit")
            )
        )
    )

@app.post('/admin/edit/{user_id}')
def edit_user(user_id: int, email:str, name:str, is_approved:int, is_admin:int):
    user = users(where=f"id={user_id}")
    if not user:
        return "User not found"
    user = user[0]
    user['username'] = email
    user['name'] = name
    user['is_approved'] = is_approved
    user['is_admin'] = is_admin
    users.update(user)
    return RedirectResponse('/admin', status_code=303)

@rt('/logout')
def logout():
    response = RedirectResponse('/', status_code=303)
    response.delete_cookie('user')
    return response
    
@rt('/register', methods=['GET'])
def register(email:str='', password:str=''):
    return Div(
        Titled("Register"),
        Form(method="post", action="/register")(
            Fieldset(
                Input(type="email", name="email", placeholder="Enter your email", value=email),
                Input(type="password", name="password", placeholder="Enter your password"),
                Input(type="text", name="firstname", placeholder="Enter your first name"),
                Input(type="text", name="surname", placeholder="Enter your surname"),
                Input(type="text", name="website", style="display:none", tabindex="-1", autocomplete="off"),  # Honeypot field
                Button("Register", type="submit")
            )
        )
    )

@app.post('/approve')
def approve_user(user_id: int):
    user = users[user_id]
    user['is_approved'] = 1  
    users.update(user)
    return RedirectResponse('/admin', status_code=303)

@app.post('/reject')
def reject_user(user_id: int):
    users.delete(user_id)
    return RedirectResponse('/admin', status_code=303)

@rt('/upload', methods=['GET'])
def upload_page(req: Request):
    if not req.cookies.get('user'):
        return RedirectResponse('/')
    user = users(where=f"username='{req.cookies.get('user')}'")
    if not user or not user[0]['is_admin']:
        return "Access denied"
    return Div(
        H1("Upload Photo"),
        P("This is where you would upload a photo. (Not implemented yet)"),
        Form(method="post", action="/upload", enctype="multipart/form-data")(
            Fieldset(
                Input(type="file", name="photo"),
                Input(type="text", name="description", placeholder="Enter a description"),
                Input(type="text", name="location", placeholder="Enter the location"),
                Button("Upload", type="submit")
            )
        )
    )   

@app.post('/upload')
async def photo_uploader(req: Request, photo: UploadFile, description:str, location:str):
    result = admin_checker(users, req)
    if not isinstance(result, int): return result
    
    s3 = boto3.client('s3',
        endpoint_url=os.getenv('S3_ENDPOINT'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )
    
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    filebuffer = await photo.read()
    
    # Resize/compress with Pillow
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(filebuffer))
    img = img.convert('RGB')
    if img.width > 1200:
        ratio = 1200 / img.width
        img = img.resize((1200, int(img.height * ratio)))
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    filebuffer = output.getvalue()

    if len(filebuffer) > 2 * 1024 * 1024:
        return "File too large even after compression - please use a smaller image"
        
    s3.put_object(
        Bucket=os.getenv('S3_BUCKET'),
        Key=filename,
        Body=filebuffer,
        ContentType='image/jpeg'
    )
    
    url = f"/image/{filename}"
    photos.insert(description=description, url=url, location=location, date=datetime.now().strftime('%Y-%m-%d'))
    return RedirectResponse('/photos', status_code=303)

@app.get('/image/{filename}')
def serve_image(filename: str, req: Request):
    if not req.cookies.get('user'):
        return RedirectResponse('/')
    s3 = boto3.client('s3',
        endpoint_url=os.getenv('S3_ENDPOINT'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )
    obj = s3.get_object(Bucket=os.getenv('S3_BUCKET'), Key=filename)
    return Response(content=obj['Body'].read(), media_type='image/jpeg')

@app.post('/register')
def register_post(reg: Registration, website:str=''):
    #honeypot check    
    if website:
        print("Thanks for registering!")
        return RedirectResponse('/', status_code=303)
    else:
        try:
            users.insert(username=reg.email, password=hash_password(reg.password), name=f"{reg.firstname} {reg.surname}", is_approved=0, is_admin=0)
            response = RedirectResponse('/photos', status_code=303)
            response.set_cookie('user', reg.email)
            return response
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return f"Error registering user: {str(e)}"

@rt('/photos')
def photos_page(req: Request):
    if not req.cookies.get('user'):
        return RedirectResponse('/')
    user = users(where=f"username='{req.cookies.get('user')}'")
    if not user[0]['is_approved']:
        return "Your account is awaiting approval by an admin. Please check back later."
    admin_nav = None
    if user[0]['is_admin']:
        admin_link = A("Admin Panel", href="/admin")
        post_link = A("Upload Photo", href="/upload")
        logout_link = A("Logout", href="/logout")
        admin_nav = Nav(admin_link, " | ", post_link, " | ", logout_link)
    all_photos = photos(order_by="id DESC", limit=5)  # Get all photos ordered by most recent
    cards = []
    for p in all_photos:
        #code in helpers.py needs to be updated to pass in comments, likes and users
        cards.append(build_card(p, comments, likes, users, is_admin=user[0]['is_admin']))
    return Div(
        Title("Photos"),
        Div(cls="feed")(admin_nav if user[0]['is_admin'] else None, *cards),
        Div(hx_get="/photos/more/2", hx_trigger="revealed", hx_swap="outerHTML", style="display:none")
    )

@rt('/photos/more/{page}')
def photos_more(page: int, req: Request):
    user = users(where=f"username='{req.cookies.get('user')}'")
    photos_per_page = 5
    offset = (page - 1) * photos_per_page
    more_photos = photos(order_by="id DESC", limit=photos_per_page, offset=offset)
    photo_items = []
    for p in more_photos:
        #code in helpers.py needs to be updated to pass in comments, likes and users
        photo_items.append(build_card(p, comments, likes, users, is_admin=user[0]['is_admin']))
    trigger = Div(hx_get=f"/photos/more/{page + 1}", hx_trigger="revealed", hx_swap="outerHTML") if len(more_photos) == 5 else None
    return Div(cls="feed")(*photo_items, trigger)

@rt('/comment-form/{photo_id}')
def comment_form(photo_id: int):
    return Form(method="post", action="/comment")(
        Input(type="text", name="comment", placeholder="Add a comment"),
        Input(type="hidden", name="photo_id", value=photo_id),
        Button("Comment", type="submit")
    )
    
@app.get('/photos/edit/{photo_id}')
def edit_photo_page(photo_id: int, req: Request):
    if not req.cookies.get('user'):
        return RedirectResponse('/')
    user = users(where=f"username='{req.cookies.get('user')}'")
    if not user or not user[0]['is_admin']:
        return "Access denied"
    photo = photos(where=f"id={photo_id}")
    if not photo:
        return "Photo not found"
    photo = photo[0]
    return Div(
        H1("Edit Photo"),
        Form(method="post", action=f"/photos/edit/{photo_id}")(
            Input(type="text", name="description", placeholder="Enter description", value=photo['description']),
            Input(type="text", name="location", placeholder="Enter location", value=photo['location']),
            Button("Save Changes", type="submit"),
            Button("Delete Photo", type="submit", formaction=f"/photos/delete/{photo_id}", formmethod="post")
        )
    )

@app.post('/photos/edit/{photo_id}')
def edit_photo(photo_id: int, description:str, location:str):
    photo = photos(where=f"id={photo_id}")
    if not photo:
        return "Photo not found"
    photo = photo[0]
    photo['description'] = description
    photo['location'] = location
    photos.update(photo)
    return RedirectResponse('/photos', status_code=303)

@app.post('/photos/delete/{photo_id}')
def delete_photo(photo_id: int, req: Request):
    #refer to helpers.py for code for admin_checker
    result = admin_checker(users, req)
    if not isinstance(result, int): return result
    photo = photos(where=f"id={photo_id}")
    if not photo:
        return "Photo not found"
    photos.delete(photo[0]['id'])
    return RedirectResponse('/photos', status_code=303)

@app.post('/like')
def like_photo(req: Request, photo_id: int):
    user_id = user_checker(users, req)
    if isinstance(user_id, RedirectResponse):
        return user_id
    # Check if the like already exists
    existing_like = likes(where=f"user_id={user_id} AND photo_id={photo_id}")
    if existing_like:
        return "You have already liked this photo."
    else:
        likes.insert(user_id=user_id, photo_id=photo_id)
        print("redirecting to /photos")
        return RedirectResponse('/photos', status_code=303)

@app.post('/comment')
def comment_photo(req: Request, photo_id: int, comment: str):
    user_id = user_checker(users, req)
    if isinstance(user_id, RedirectResponse):
        return user_id
    comments.insert(user_id=user_id, photo_id=photo_id, comment=comment)
    return RedirectResponse('/photos', status_code=303)

serve()