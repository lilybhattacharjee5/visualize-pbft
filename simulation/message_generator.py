def generate_transaction_msg(sender, recipient, curr_transaction, curr_view, p, client_signing_key):
    signed_msg = {
        "Type": "Transaction",
        "Sender": sender,
        "Recipient": recipient,
        "Transaction": client_signing_key.sign(str.encode(str(curr_transaction))),
        "View": curr_view,
        "Num_transaction": p,
    }
    return signed_msg

def generate_preprepare_msg(sender, recipient, curr_transaction, curr_view, p, primary_signing_key, primary):
    msg = {
        "Type": "Pre-prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Transaction": curr_transaction, # already signed by client
        "View": curr_view,
        "Num_transaction": p,
    }
    return msg

def generate_prepare_msg(sender, recipient, m, primary):
    return {
        "Type": "Prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Message": m,
    }

def generate_commit_msg(sender, recipient, m, primary):
    return {
        "Type": "Commit",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Message": m,
    }

def generate_inform_msg(sender, recipient, curr_transaction, p, r, primary):
    return {
        "Type": "Inform",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Transaction": curr_transaction,
        "Num_transaction": p,
        "Result": r,
    }

def generate_view_change_msg(sender, recipient, primary):
    return {
        "Type": "View change",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
    }

def generate_new_view_msg(sender, recipient, new_view, primary):
    return {
        "Type": "New view",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "View": new_view,
    }