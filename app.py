from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import pandas as pd
from simulation.simulator import run_simulation
import configparser
import signal 
from contextlib import contextmanager
import multiprocessing as mp
import time

default_num_replicas = 4
default_num_byzantine = 0
default_num_transactions = 1
default_byz_behave = "none"

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

def sim(num_replicas = default_num_replicas, num_byzantine = default_num_byzantine, num_transactions = default_num_transactions, byz_behave = default_byz_behave):
    setup_bank()

    try:
        db.session.query(Customer).delete()
        db.session.commit()
    except:
        db.session.rollback()

    manager = mp.Manager()
    frontend_log = manager.list()
    p = mp.Process(target = run_simulation, args = (num_replicas, num_byzantine, num_transactions, byz_behave, frontend_log))
    p.start()
    p.join(timeout = 20)

    frontend_log = list(frontend_log)
    type_data = list(map(lambda x: "" if "Type" not in x else x["Type"], frontend_log))
    sender_data = list(map(lambda x: "" if "Sender" not in x else x["Sender"], frontend_log))
    recipient_data = list(map(lambda x: "" if "Recipient" not in x else x["Recipient"], frontend_log))
    transaction_data = list(map(lambda x: "" if "Transaction" not in x else x["Transaction"], frontend_log))
    message_data = list(map(lambda x: "" if "Message" not in x else x["Message"], frontend_log))
    view_data = list(map(lambda x: "" if "View" not in x else x["View"], frontend_log))
    num_transaction_data = list(map(lambda x: "" if "Num_transaction" not in x else x["Num_transaction"], frontend_log))
    result_data = list(map(lambda x: "" if "Result" not in x else x["Result"], frontend_log))

    frontend_log_data = pd.DataFrame({
        "Type": type_data,
        "Sender": sender_data,
        "Recipient": recipient_data,
        "Transaction": transaction_data,
        "Message": message_data,
        "View": view_data,
        "Num_transaction": num_transaction_data,
        "Result": result_data,
        })

    data = frontend_log_data.values.tolist()

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

@app.route("/", methods = ["POST", "GET"])
def show_all():
    if request.method == "POST":
        data = request.form
        num_replicas = int(data.get('num_replicas'))
        num_byzantine = int(data.get('num_byzantine'))
        num_transactions = int(data.get('num_transactions'))
        byz_behave = data.get('byz_behave')
    else:
        num_replicas = default_num_replicas
        num_byzantine = default_num_byzantine
        num_transactions = default_num_transactions
        byz_behave = default_byz_behave

    if byz_behave == "none": byz_behave = None

    data_lst = sim(num_replicas = num_replicas, num_byzantine = num_byzantine, num_transactions = num_transactions, byz_behave = byz_behave)
    return render_template("index.html", data = data_lst)
