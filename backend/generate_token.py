from datetime import datetime, timedelta, timezone
from jose import jwt
import uuid

user_id = '22990f55-31ce-4cb6-a513-8be6fff76aab'
jwt_secret = 'test-jwt-secret-at-least-32-characters-long'
expire = datetime.now(timezone.utc) + timedelta(days=30)
to_encode = {'sub': user_id, 'exp': expire, 'type': 'access'}
token = jwt.encode(to_encode, jwt_secret, algorithm='HS256')
print("localStorage.setItem('cognita_token', '" + token + "');")
