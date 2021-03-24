from flask import Flask
from database import candy_shop_db

db = candy_shop_db()
app = Flask(__name__)
