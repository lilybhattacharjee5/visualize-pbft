from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import pandas as pd
from simulation.simulator import run_simulation
import configparser
import signal 
from contextlib import contextmanager
import multiprocessing as mp
import time
import json
import ast

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
app.secret_key = "secret_key" #settings['SECRET_KEY']
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

def clean_log_entry(log_entry):
    try:
        if type(log_entry) == dict:
            for k, v in log_entry.items():
                try:
                    v = ast.literal_eval(v)
                except:
                    pass

                temp_v = str(v)
                if type(v) == bytes:
                    try:
                        temp_v = ast.literal_eval(v.decode())
                    except:
                        pass
                elif type(v) == list:
                    try:
                        temp_v = [str(i) for i in v]
                    except:
                        pass
                elif type(v) == dict:
                    try:
                        temp_v = clean_log_entry(v)
                    except:
                        pass
                log_entry[k] = temp_v
    except:
        pass 
    return log_entry

def sim(num_replicas = default_num_replicas, num_byzantine = default_num_byzantine, num_transactions = default_num_transactions, byz_behave = default_byz_behave):
    setup_bank()

    try:
        db.session.query(Customer).delete()
        db.session.commit()
    except:
        db.session.rollback()

    manager = mp.Manager()
    frontend_log = manager.list()
    byz_replica_names = manager.list()
    db_states = manager.dict()
    for r in range(num_replicas):
        r_name = "Replica_{}".format(r)
        db_states[r_name] = manager.list()
    p = mp.Process(target = run_simulation, args = (num_replicas, num_byzantine, num_transactions, byz_behave, frontend_log, db_states, byz_replica_names))
    p.start()
    p.join(timeout = 5) # 20
    
    byz_replica_names = list(byz_replica_names)
    frontend_log = list(frontend_log)
    
    type_data = list(map(lambda x: "" if "Type" not in x else x["Type"], frontend_log))
    sender_data = list(map(lambda x: "" if "Sender" not in x else x["Sender"], frontend_log))
    recipient_data = list(map(lambda x: "" if "Recipient" not in x else x["Recipient"], frontend_log))
    primary_data = list(map(lambda x: "" if "Primary" not in x else x["Primary"], frontend_log))
    transaction_data = list(map(lambda x: "" if "Transaction" not in x else x["Transaction"], frontend_log))
    message_data = list(map(lambda x: "" if "Communication" not in x else x["Communication"], frontend_log))
    view_data = list(map(lambda x: "" if "View" not in x else x["View"], frontend_log))
    num_transaction_data = list(map(lambda x: "" if "Num_transaction" not in x else x["Num_transaction"], frontend_log))
    result_data = list(map(lambda x: "" if "Result" not in x else x["Result"], frontend_log))

    for m in range(len(message_data)):
        message_data[m] = clean_log_entry(message_data[m])

    # interpolate num transactions data
    prev_num_transaction = num_transaction_data[0]
    for t in range(len(num_transaction_data)):
        if num_transaction_data[t] == '':
            num_transaction_data[t] = prev_num_transaction
        else:
            prev_num_transaction = num_transaction_data[t]

    num_transaction_data_inc = []
    for i in num_transaction_data:
        num_transaction_data_inc.append(i + 1)

    bank_lst = []
    consensus_bank = list(db_states["Replica_0"])

    transaction_num = 0
    prev_num = 0
    inform_flag = False
    for t in range(len(num_transaction_data)):
        num = num_transaction_data[t]
        if type_data[t] == "Inform" and not inform_flag:
            transaction_num += 1
            inform_flag = True
        if inform_flag and num != prev_num:
            inform_flag = False
        bank_lst.append(consensus_bank[transaction_num])
        prev_num = num

    frontend_log_data = pd.DataFrame({
        "Type": type_data,
        "Sender": sender_data,
        "Recipient": recipient_data,
        "Primary": primary_data,
        "Transaction": transaction_data,
        "Message": message_data,
        "View": view_data,
        "Visible_num_transaction": num_transaction_data_inc,
        "Result": result_data,
        })

    data = frontend_log_data.values.tolist()

    data_lst = []
    for d in data:
        data_lst.append({
            "Type": d[0],
            "Sender": d[1],
            "Recipient": d[2],
            "Primary": d[3],
            "Transaction": d[4],
            "Message": d[5],
            "View": d[6],
            "Visible_num_transaction": d[7],
            "Result": d[8],
        })

    return data_lst, bank_lst, byz_replica_names

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

    data_lst, bank_lst, byz_replica_names = sim(num_replicas = num_replicas, num_byzantine = num_byzantine, num_transactions = num_transactions, byz_behave = byz_behave)
    return render_template("index.html", num_replicas = num_replicas, num_byzantine = num_byzantine, byz_replica_names = byz_replica_names, num_transactions = num_transactions, byz_behave = byz_behave, log_data = data_lst, bank_data = bank_lst)
