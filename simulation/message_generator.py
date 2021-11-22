def generate_transaction_msg(sender, recipient, curr_transaction, curr_view, p):
    return {
        "Type": "Transaction",
        "Sender": sender,
        "Recipient": recipient,
        "Transaction": curr_transaction,
        "View": curr_view,
        "Num_transaction": p,
    }

def generate_preprepare_msg(sender, recipient, curr_transaction, curr_view, p):
    return {
        "Type": "Pre-prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Transaction": curr_transaction,
        "View": curr_view,
        "Num_transaction": p,
    }

def generate_prepare_msg(sender, recipient, m):
    return {
        "Type": "Prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Message": m,
    }

def generate_commit_msg(sender, recipient, m):
    return {
        "Type": "Commit",
        "Sender": sender,
        "Recipient": recipient,
        "Message": m,
    }

def generate_inform_msg(sender, recipient, curr_transaction, p, r):
    return {
        "Type": "Inform",
        "Sender": sender,
        "Recipient": recipient,
        "Transaction": curr_transaction,
        "Num_transaction": p,
        "Result": r,
    }

def generate_view_change_msg(sender, recipient):
    return {
        "Type": "View change",
        "Sender": sender,
        "Recipient": recipient,
    }

def generate_new_view_msg(sender, recipient, new_view):
    return {
        "Type": "New view",
        "Sender": sender,
        "Recipient": recipient,
        "View": new_view,
    }