from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template
import pandas as pd

app = Flask(__name__, template_folder = ".")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.static_folder = 'static'
db = SQLAlchemy(app)

class Customer(db.Model):
    id = db.Column('customer_id', db.Integer, primary_key = True)
    name = db.Column(db.String(100))
    balance = db.Column(db.Integer)

    def __init__(self, name, balance):
        self.name = name 
        self.balance = balance

db.create_all()

def setup_bank():
    db.session.add(Customer("Ana", 500))
    db.session.add(Customer("Bo", 200))
    db.session.add(Customer("Elisa", 100))

@app.route("/")
def show_all():
    setup_bank()
    data = pd.read_csv("./static/frontend_log.csv").values.tolist()
    data_lst = []
    
    for d in data:
        data_lst.append({
            "Type": d[1],
            "Sender": d[2],
            "Recipient": d[3],
            "Transaction": d[4],
            "Message": d[5],
            "View": d[6],
            "Num_transaction": d[7],
            "Result": d[8],
        })
    return render_template("index.html", data = data_lst)
