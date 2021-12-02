from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for, session
import pandas as pd
from simulation.simulator import run_simulation
import configparser

default_num_replicas = 4
default_num_byzantine = 1
default_num_transactions = 1

config = configparser.ConfigParser()
config.read("app_settings.ini")
settings = config["DEFAULT"]

app = Flask(__name__, template_folder = ".")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = settings['SECRET_KEY']
app.config['SESSION_TYPE'] = 'filesystem'
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
    try:
        db.session.add(Customer("Ana", 500))
        db.session.add(Customer("Bo", 200))
        db.session.add(Customer("Elisa", 100))
        db.session.commit()
    except:
        db.session.rollback()

def sim(num_replicas = default_num_replicas, num_byzantine = default_num_byzantine, num_transactions = default_num_transactions):
    setup_bank()

    try:
        db.session.query(Customer).delete()
        db.session.commit()
    except:
        db.session.rollback()

    data = run_simulation(num_replicas = num_replicas, num_byzantine = num_byzantine, num_transactions = num_transactions).values.tolist()

    data_lst = []
    for d in data:
        data_lst.append({
            "Type": d[0],
            "Sender": d[1],
            "Recipient": d[2],
            "Transaction": d[3],
            "Message": d[4],
            "View": d[5],
            "Num_transaction": d[6],
            "Result": d[7],
        })
    return data_lst

@app.route("/")
def show_all():
    try:
        messages = session['messages']

        if "num_replicas" in messages and "num_byzantine" in messages and "num_transactions" in messages:
            num_replicas = messages["num_replicas"]
            num_byzantine = messages["num_byzantine"]
            num_transactions = messages["num_transactions"]
        else:
            num_replicas = default_num_replicas
            num_byzantine = default_num_byzantine
            num_transactions = default_num_transactions

        session["messages"] = {}
    except:
        num_replicas = default_num_replicas
        num_byzantine = default_num_byzantine
        num_transactions = default_num_transactions

    data_lst = sim(num_replicas = num_replicas, num_byzantine = num_byzantine, num_transactions = num_transactions)
    return render_template("index.html", data = data_lst)

@app.route('/restart_pbft', methods = ['POST', 'GET'])
def restart_pbft():
    num_replicas = int(request.headers['Num_replicas'])
    num_byzantine = int(request.headers['Num_byzantine'])
    num_transactions = int(request.headers['Num_transactions'])
    
    session['messages'] = {
        "num_replicas": num_replicas,
        "num_byzantine": num_byzantine,
        "num_transactions": num_transactions,
    }

    return redirect(request.referrer)
