from simulation.message_generator import generate_preprepare_msg
import copy

def byz_primary(byz_status, r_signing_key, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log, primary_name):
    if byz_status == "no_response":
        return
    elif byz_status == "fake_client_transactions":
        print("current transaction", curr_transaction, curr_transaction.message)
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                manipulated_transaction = str.encode(str(["Elisa", "Ana", 1000000]))
                manipulated_signed = r_signing_key.sign(manipulated_transaction)
                
                prep_msg = generate_preprepare_msg(r_name, q_name, manipulated_signed, curr_view, p, r_signing_key, primary_name)
                clean_prep_msg = copy.deepcopy(prep_msg)
                clean_prep_msg["Transaction"] = str(clean_prep_msg["Transaction"].message)
                frontend_log.append(clean_prep_msg)
                q["to_machine"].put([prep_msg])
    else:
        return # none of the other byzantine behaviors are related to the primary's preprepare phase

## PRIMARY FUNCTIONS
def send_preprepare(to_curr_replica, r_signing_key, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log, frontend_log, primary_signing_key, primary_name):
    if byz_status in ["no_response", "fake_client_transactions"]:
        m_queue.put(None)
        byz_primary(byz_status, r_signing_key, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log, primary_name)
    else:
        m_queue.put(True)
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                prep_msg = generate_preprepare_msg(r_name, q_name, curr_transaction, curr_view, p, primary_signing_key, primary_name)
                clean_prep_msg = copy.deepcopy(prep_msg)
                clean_prep_msg["Transaction"] = str(clean_prep_msg["Transaction"].message.decode("utf-8"))
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
