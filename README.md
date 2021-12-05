# visualize-pbft
View a [demo](https://visualize-pbft.herokuapp.com/) deployed on Heroku!

This repo hosts the code for a tool intended to visualize node-to-node communication in the Practical Byzantine Fault Tolerance (pBFT) distributed systems consensus protocol. This work was developed for the final project assignment for ECS 235A: Computer & Information Security.

## Visualization components
Note: This screenshot was last updated on 12/04/2021. See the demo for the latest iteration.

![Visualization Screenshot](https://i.ibb.co/tqLjCj4/Screen-Shot-2021-12-04-at-11-57-18-PM.png)

### Simulation / Backend
During normal operation, after the client sends a transaction to the current primary, pBFT is comprised of 4 stages: pre-prepare, prepare, commit, and inform. However, not all replicas (or primaries) are guaranteed to be 'good' -- some can engage in malicious behavior to disrupt consensus or prevent transactions from executing across all replicas, resulting in eventual state mismatches.

Given the following inputs by the user:
- number of replicas
- number of Byzantine replicas
- number of transactions
- type of Byzantine behavior (this will be imposed upon all of the Byzantine replicas)

the simulation, running in the Python backend, forks n + 1 processes where n is the number of replicas and the last is for the client. The processes, modeling separate nodes, communicate with each other by passing messages through queues and synchronizing at the end of each phase and transaction.

All timeouts associated with processes and workers are 120s maximum (so it might take up to 2 min to load the results of a simulation).

### Frontend
The visualization includes 4 major parts:
- force graph (upper left): displays nodes and the messages they transmit to each other as edges.
- communication log (upper right): traces through the messages transmitted during each phase / chunk of messages with the same type. Clicking on an "Expand" link will toggle a larger view of the message transmitted along the edge.
- options form (lower left): allows user to submit options for the next simulation.
- bank state (lower right): displays changing bank state as the user clicks "Next" through the phases, and the replicated banks reach consensus.

## Getting started locally
To run this simulation locally, take the following steps after git cloning / downloading the folder:

1. Check that your system's Python version is >=3.6.10. Note: I can only guarantee that the simulation will function as expected with version ==3.6.10 -- haven't tested in other environments yet.
2. Verify / install missing project requirements by cd'ing into the project's working directory and running `pip install -r requirements.txt`.
3. Run `gunicorn app:app --timeout=120` in the terminal. You should see something similar to the below as the port begins serving the index page:
```
[2021-12-04 21:13:06 -0800] [30794] [INFO] Starting gunicorn 20.0.4
[2021-12-04 21:13:06 -0800] [30794] [INFO] Listening at: http://127.0.0.1:8000 (30794)
[2021-12-04 21:13:06 -0800] [30794] [INFO] Using worker: sync
[2021-12-04 21:13:06 -0800] [30797] [INFO] Booting worker with pid: 30797
```
4. By default, gunicorn will use port 8000. Navigate to http://127.0.0.1:[port number] (e.g. http://127.0.0.1:8000) in your browser. The visualization (with inputs num_replicas = 4, num_byzantine = 0, num_transactions = 1, behavior = None) should be visible.

## Repository structure
- `simulation/`: contains backend files for running simulation e.g. primary-, replica-, and client-specific functions. 
- `static/`: contains frontend files for processing and displaying simulation results.
- `Procfile`, `requirements.txt`, `runtime.txt`: required for Heroku deployment (+ project requirements).
- `app.py`: manages page serving / form data processing.
- `bank.sqlite3`: bank SQL database fiel.
- `index.html`: main demo page.

## Known todos / Future work
This todo list is in progress. Reach out to me if you find a bug!
- More descriptive error messages for incorrect combinations of input options in the frontend form.
- Add support replica logs so replicas that go out of sync with consensus can recover the correct state.
- Support more varieties of Byzantine behavior: e.g. convincing good replicas that other good replicas are malicious.
- Fix processing for new view requests (currently hardcoded to 1 replica max able to send this type of message until primary resolution).
- Link the consensus bank to the SQL database instead of maintaining separate dictionaries for balance data.

## References
- [Practical Byzantine Fault Tolerance (2012 modified notes)](https://people.csail.mit.edu/alinush/6.824-spring-2015/extra/pbft.html)
- [Practical Byzantine Fault Tolerance (Paper)](https://pmg.csail.mit.edu/papers/osdi99.pdf)
- [Practical Byzantine Fault Tolerance (Slides)](http://www.cs.utah.edu/~stutsman/cs6963/public/pbft.pdf)
- [Digital Signatures](https://pynacl.readthedocs.io/en/latest/signing/)

## License
BSD-3
