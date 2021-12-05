from simulation.message_generator import generate_preprepare_msg
import copy
import json
import ast

def byz_primary(byz_status, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log, primary_name, primary_session_keys, m_auth, replica_names):
    if byz_status == "no_response":
        return
    elif byz_status == "fake_client_transactions":
        print("current transaction", curr_transaction)
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                manipulated_transaction = ["Elisa", "Ana", 1000000]
                curr_transaction_msg = json.loads(curr_transaction["Message"])
                curr_transaction_msg["Operation"] = manipulated_transaction
                curr_transaction["Message"] = str(curr_transaction_msg).replace("'", "\"").encode("utf-8")
                
                prep_msg = generate_preprepare_msg(r_name, q_name, curr_transaction, m_auth, curr_view, p, primary_name, primary_session_keys, replica_names)
                clean_prep_msg = copy.deepcopy(prep_msg)
                frontend_log.append(clean_prep_msg)
                q["to_machine"].put([prep_msg])
    else:
        return # none of the other byzantine behaviors are related to the primary's preprepare phase

## PRIMARY FUNCTIONS
def send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log, frontend_log, primary_name, primary_session_keys, m_auth, replica_names):
    if byz_status in ["no_response", "fake_client_transactions"]:
        m_queue.put(None)
        byz_primary(byz_status, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log, primary_name, primary_session_keys, m_auth, replica_names)
    else:
        m_queue.put(True)
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                prep_msg = generate_preprepare_msg(r_name, q_name, curr_transaction, m_auth, curr_view, p, primary_name, primary_session_keys, replica_names)
                clean_prep_msg = copy.deepcopy(prep_msg)
                # comm = clean_prep_msg["Communication"]
                # comm["Authenticator"] = ["" if a == None else str(a) for a in comm["Authenticator"]]
                frontend_log.append(clean_prep_msg)
                q["to_machine"].put([prep_msg])
        m_queue.put(r_name + " pre-prepare phase done")
        visible_log.append("primary has sent the pre-prepare messages")
        visible_log.append(to_curr_replica["from_main"].get())
    
    m = {
        "Transaction": curr_transaction,
        "View": curr_view,
        "Num_transaction": p,
    }
    
    return m
