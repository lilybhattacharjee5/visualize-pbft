from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, url_for, session
import pandas as pd
from simulation.simulator import run_simulation

default_num_replicas = 4
default_num_byzantine = 1

app = Flask(__name__, template_folder = ".")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super secret key'
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

def sim(num_replicas = default_num_replicas, num_byzantine = default_num_byzantine):
    setup_bank()

    try:
        db.session.query(Customer).delete()
        db.session.commit()
    except:
        db.session.rollback()

    data = run_simulation(num_replicas = num_replicas, num_byzantine = num_byzantine).values.tolist()
    # data = pd.read_csv("./static/display/frontend_log.csv").values.tolist()

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

        if "num_replicas" in messages and "num_byzantine" in messages:
            num_replicas = messages["num_replicas"]
            num_byzantine = messages["num_byzantine"]
        else:
            num_replicas = default_num_replicas
            num_byzantine = default_num_byzantine

        session["messages"] = {}
    except:
        num_replicas = default_num_replicas
        num_byzantine = default_num_byzantine

    data_lst = sim(num_replicas = num_replicas, num_byzantine = num_byzantine)
    return render_template("index.html", data = data_lst)

@app.route('/restart_pbft', methods = ['POST', 'GET'])
def restart_pbft():
    num_replicas = int(request.headers['Num_replicas'])
    num_byzantine = int(request.headers['Num_byzantine'])
    
    session['messages'] = {
        "num_replicas": num_replicas,
        "num_byzantine": num_byzantine,
    }

    return redirect(request.referrer)
