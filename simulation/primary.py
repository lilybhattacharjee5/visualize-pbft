from message_generator import generate_preprepare_msg

## PRIMARY FUNCTIONS
def send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log, frontend_log):
    if byz_status:
        m_queue.put(None)
    else:
        m_queue.put(True)

    if not byz_status:
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
