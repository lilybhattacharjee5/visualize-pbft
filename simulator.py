import multiprocessing as mp
import time
import numpy as np
from datetime import datetime, date
import sys
import json
import copy
from client import send_transaction, replica_ack_primary, recv_inform
from replica import send_view_change, send_new_view, recv_new_view, recv_preprepare, send_prepare, recv_prepare, send_commit, recv_commit, send_inform 
from primary import send_preprepare
from message_generator import generate_new_view_msg

# Possible Byzantine behavior to support
# - insert forged client transactions into the system
# - prevent replication of client transactions from some or all clients
# - send invalid results to client
# - interfere with correct working of distributed system e.g. convince replicas other good replicas are malicious
# - disrupting consensus protocol

# Currently supported
# - Byzantine replica(s) that do not respond to other replicas / client

# sys.stdout = open('run_log.txt', 'w')

# simulator inputs
num_replicas = 12
num_byzantine = 3

np.random.seed(0)

class JSONEncoderWithDictProxy(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, mp.managers.DictProxy):
            return dict(o)
        return json.JSONEncoder.default(self, o)

manager = mp.Manager()
visible_log = manager.list()

print("Run Time:", date.today().strftime("%m/%d/%Y"), datetime.now().strftime("%H:%M%S"))

def clear(q):
    try:
        while True:
            q.get_nowait()
    except:
        pass

def clear_all_queues(q_list):
    for q in q_list:
        for a in q:
            clear(a)

# initialize mock db
bank = {
    "Ana": { "Balance": 500 },
    "Bo": { "Balance": 200 },
    "Elisa": { "Balance": 100 }
}

f = (num_replicas - 1) // 3
g = num_replicas - f - 1 # for primary

print("good", g, "faulty", f)

transactions = [
    ["Ana", "Elisa", 400],
    ["Bo", "Elisa", 100],
    ["Elisa", "Ana", 20],
    ["Bo", "Ana", 2],
    ["Ana", "Bo", 100],
    ["Elisa", "Ana", 1],
    ["Elisa", "Ana", 1]
]
# transactions = [["Ana", "Elisa", 400] for i in range(1000)]

# select the random byzantine replicas
byz_idxes = np.random.choice(np.arange(0, num_replicas), num_byzantine, replace = False)
print("Byzantine replicas", byz_idxes)

# calculations based on inputs
num_transactions = len(transactions)

client_name = "Client"
replica_names = ["Replica_{}".format(r) for r in range(num_replicas)]
byz_replica_names = ["Replica_{}".format(r) for r in byz_idxes]

replica_logs = {}
replica_bank_copies = {}
for r in replica_names:
    replica_logs[r] = manager.list()
    replica_bank_copies[r] = manager.dict()
    for user, data in bank.items():
        replica_bank_copies[r][user] = manager.dict()
        for k, v in data.items():
            replica_bank_copies[r][user][k] = v

## TRANSACTION EXECUTION (TEMPORARY)
def execute_transaction(curr_transaction, r_name):
    sender, receiver, amt = curr_transaction 
    # does sender have at least amt to transfer?
    replica_bank = replica_bank_copies[r_name]
    if replica_bank[sender]["Balance"] >= amt:
        replica_bank[sender]["Balance"], replica_bank[receiver]["Balance"] = replica_bank[sender]["Balance"] - amt, replica_bank[receiver]["Balance"] + amt 
    return { sender: replica_bank[sender]["Balance"], receiver: replica_bank[receiver]["Balance"] }

## MULTIPROCESSING
def client_proc(transactions, queues, t_queue):
    to_client = queues[client_name]

    status = True
    last_view = -1
    while status:
        # get p_index from t_queue
        p_index, primary_name, curr_transaction, curr_view, p = t_queue.get()
        if curr_view <= last_view:
            last_view = curr_view
            continue
        last_view = curr_view
        print("Main sending transaction", curr_transaction)

        curr_transaction_status = True
        while curr_transaction_status:
            # client sends transaction to the primary of the current view
            print("Client sending transaction", curr_transaction)
            send_transaction(queues, client_name, primary_name, curr_transaction, curr_view, p)

            # wait for all replicas to acknowledge that primary has been informed
            replica_ack_primary(to_client, num_replicas, m_queue)

            # client receives f + 1 identical inform messages
            failure_status = recv_inform(to_client, f, visible_log)
            print("failure status", failure_status)
            if failure_status == None:
                curr_view += 1
                p_index += 1
                primary_name = "Replica_{}".format(p_index)
                print("Client", failure_status)
                m_queue.put(None)
                continue
            curr_transaction_status = False
        
        m_queue.put("move to the next transaction")

def replica_proc(r_name, queues, byz_status):
    to_client = queues[client_name]["to_machine"]
    to_curr_replica = queues[r_name]
    
    status = True
    while status:
        primary_status = False

        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) > 1 and (queue_elem[0] == None or queue_elem[0]["Type"] == "Transaction"):
                received = True 

        transaction, primary_name  = queue_elem 

        visible_log.append("{} {}".format(transaction, primary_name))
        if transaction:
            primary_status = True
            curr_transaction, curr_view, p = transaction["Transaction"], transaction["View"], transaction["Num_transaction"]
        else:
            # must be a regular replica
            primary_status = False
        
        visible_log.append("primary status {} {}".format(mp.current_process().name, primary_status))

        # send signal to client that primary has been informed
        to_client.put([primary_status])
        primary_informed = to_curr_replica["from_main"].get()
        print("Primary informed", primary_informed)
        visible_log.append(primary_informed)

        if primary_status:
            # primary broadcasts pre-prepare message to all other replicas
            m = send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log)
        else:
            # replicas receive pre-prepare message
            m = recv_preprepare(to_curr_replica, client_name, queues, r_name, m_queue, g, visible_log)
            if m == None:
                print("{} exit prematurely, restart the transaction".format(r_name))
                continue
            curr_transaction, p = m["Transaction"], m["Num_transaction"]

        # prepare phase
        send_prepare(queues, client_name, r_name, byz_status, m, visible_log)

        m = recv_prepare(to_curr_replica, r_name, m_queue, byz_status, g, visible_log)
        if m == None:
            print("{} exit prematurely, restart the transaction".format(r_name))
            # induce client to resend transaction
            to_client.put([generate_new_view_msg(r_name, client_name, curr_view + 1)])
            continue

        # commit phase
        send_commit(queues, client_name, r_name, m_queue, byz_status, m, visible_log)

        recv_commit(to_curr_replica, r_name, m_queue, byz_status, m, g, visible_log)

        # append transaction to replica log
        replica_logs[r_name].append(curr_transaction)

        # execute transaction, generate optional result
        print("Executing transaction {} {}".format(curr_transaction, r_name))
        result = execute_transaction(curr_transaction, r_name)

        send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, result, visible_log) # all replicas send an inform message to the client  

all_machine_names = [client_name] + replica_names
machine_queues = {}
for a in range(len(all_machine_names)):
    a_machine_name = all_machine_names[a]
    curr_queue_to_a = mp.Queue()
    curr_queue_to_a_from_main = mp.Queue()
    machine_queues[a_machine_name] = {
        "to_machine": curr_queue_to_a,
        "from_main": curr_queue_to_a_from_main
    }

# spawn client and replica processes
t_queue = mp.Queue()
m_queue = mp.Queue()
client = mp.Process(name = client_name, target = client_proc, args = (transactions, machine_queues, t_queue, ))
replicas = [mp.Process(name = r_name, target = replica_proc, args = (r_name, machine_queues, r_name in byz_replica_names, )) for r_name in replica_names]

client.start()
for r in replicas:
    r.start()

# iteratively execute all transactions
curr_view = 0
p = 0
for t in range(len(transactions)):
    transaction_status = True
    print(t, transactions[t], "main value")
    while transaction_status:
        visible_log.append("Transaction {} {}".format(t, transactions[t]))

        visible_log.append("PRIMARY ELECTION")
            
        # elect primary
        p_index = curr_view % num_replicas
        primary_name = replica_names[p_index]
        visible_log.append("Primary selected {}".format(p_index))

        # send primary index, name, current view, and transaction to client
        t_queue.put((p_index, primary_name, transactions[t], curr_view, p))

        # replica inform done
        visible_log.append(m_queue.get())

        clear_all_queues(machine_queues.values())
        clear(m_queue)

        visible_log.append("PRE-PREPARE PHASE")
        
        for q_name, q in machine_queues.items():
            q["from_main"].put("start pre-prepare phase")

        # pre-prepare phase done
        client_response = m_queue.get()
        print("Client response", client_response)
        if client_response == None:
            continue
        for i in range(num_replicas):
            visible_log.append("Main {}".format(m_queue.get()))

        clear_all_queues(machine_queues.values())
        clear(m_queue)

        visible_log.append("PREPARE PHASE")
        
        for q_name, q in machine_queues.items():
            if q_name != client_name:
                q["from_main"].put("start prepare phase")

        # prepare phase done
        for i in range(num_replicas):
            visible_log.append("Main {}".format(m_queue.get()))

        clear_all_queues(machine_queues.values())
        clear(m_queue)

        visible_log.append("COMMIT PHASE")
        
        for q_name, q in machine_queues.items():
            if q_name != client_name:
                q["from_main"].put("start commit phase")

        # commit phase done
        for i in range(num_replicas):
            visible_log.append("Main {}".format(m_queue.get()))

        clear_all_queues(machine_queues.values())
        clear(m_queue)

        visible_log.append("INFORM CLIENT")
        
        for q_name, q in machine_queues.items():
            if q_name != client_name:
                q["from_main"].put("send inform messages")

        # inform client done: client sends a message to move to the next transaction
        inform_client_status = m_queue.get()
        print("inform client done", inform_client_status)
        visible_log.append("Main {}".format(inform_client_status))

        clear_all_queues(machine_queues.values())
        clear(m_queue)
        clear(t_queue)

        print("cleared queues")

        p += 1
        curr_view += 1
        transaction_status = False

        print("Move to next transaction in loop")
        
        # time.sleep(5) # artificial latency to view text output between transactions

# terminate all subprocesses
client.terminate()
for r in replicas:
    r.terminate()

# # print the visible log
# for i in visible_log:
#     print(i)

# print()

# # print the logs of each replica
# for r in replica_names:
#     print(r, "log")
#     for log_entry in replica_logs[r]:
#         print(log_entry)
#     print()

# states of replica banks
for r_name, bank_copy in replica_bank_copies.items():
    print(r_name, json.dumps(bank_copy, cls=JSONEncoderWithDictProxy))

# sys.stdout.close()
