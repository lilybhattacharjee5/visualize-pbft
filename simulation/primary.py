from simulation.message_generator import generate_preprepare_msg

def byz_primary(byz_status, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log):
    if byz_status == "no_response":
        return
    elif byz_status == "fake_client_transactions":
        return
        # print("curr transaction", curr_transaction)
        # m_queue.put(True)
        # for q_name, q in queues.items():
        #     if q_name != client_name and q_name != r_name:
        #         prep_msg = generate_preprepare_msg(r_name, q_name, curr_transaction, curr_view, p)
        #         frontend_log.append(prep_msg)
        #         q["to_machine"].put([prep_msg])
        # m_queue.put(r_name + " pre-prepare phase done")
        # visible_log.append("primary has sent the pre-prepare messages")
        # visible_log.append(to_curr_replica["from_main"].get())
    else:
        return # none of the other byzantine behaviors are related to the primary's preprepare phase

## PRIMARY FUNCTIONS
def send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log, frontend_log):
    if byz_status:
        m_queue.put(None)
        byz_primary(byz_status, to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, visible_log, frontend_log)
    else:
        m_queue.put(True)
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                prep_msg = generate_preprepare_msg(r_name, q_name, curr_transaction, curr_view, p)
                frontend_log.append(prep_msg)
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
