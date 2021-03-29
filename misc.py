from flask import Flask
from database.database import CandyShopDB

db = CandyShopDB()
app = Flask(__name__)
