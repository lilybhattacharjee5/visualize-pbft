function onload(numReplicas, numByzantine, numTransactions, byzBehave, logData, bankData) {
    displaySettings(numReplicas, numByzantine, numTransactions, byzBehave);
    displayCurrentTransaction(1);
    displayLog(logData);
    displayBank(bankData[0]);
    generateForceGraph(logData);
}

function displaySettings(numReplicas, numByzantine, numTransactions, byzBehave, currT) {
    let currentSettings = document.getElementById("currentSettings");
    currentSettings.innerHTML = `Number of replicas: <b>${numReplicas}</b> | Number of Byzantine replicas: <b>${numByzantine}</b> | Number of transactions: <b>${numTransactions}</b> | Behavior: <b>${byzBehave}</b>`;
}

function displayCurrentTransaction(currT) {
    let currentTransaction = document.getElementById("currentTransaction");
    currentTransaction.innerHTML = `Transaction <b>${currT}</b>`;
}

function colorNodes(nodeName) {
    let replicaRegex = /Replica.*/
    if (nodeName === "Client") {
        return "blue";
    } else if (nodeName.match(replicaRegex)) {
        return "green";
    } 
    return "red";
}

function validate_inputs(num_replicas_val, num_byzantine_val, num_transactions_val, byz_behave) {
    if (isNaN(num_replicas_val) || isNaN(num_byzantine_val) || isNaN(num_transactions_val)) {
        return false;
    }

    let num_replicas = parseInt(num_replicas_val);
    let num_byzantine = parseInt(num_byzantine_val);
    let num_transactions = parseInt(num_transactions_val);

    if (!(num_replicas > 1) || !(num_replicas <= 8)) {
        return false;
    }

    if (!(num_byzantine >= 0) || !(num_byzantine <= 8)) {
        return false;
    }

    if (!(num_transactions > 0) || !(num_transactions <= 10)) {
        return false;
    }

    if ((num_byzantine > 0) && (byz_behave === "none")) {
        return false;
    }

    return true;
}

$('#submitButton').on('click', function() {
    // validate inputs, else ask user to re-enter
    let num_replicas = document.getElementById('num_replicas').value;
    let num_byzantine = document.getElementById('num_byzantine').value;
    let num_transactions = document.getElementById('num_transactions').value;
    let byz_behave = document.getElementById('byz_behave').value;

    let errors = document.getElementById('errors');

    let validate_result = validate_inputs(num_replicas, num_byzantine, num_transactions, byz_behave);
    
    if (validate_result) {
        errors.innerHTML = ""

        $("#options").submit();
        $('#options').get(0).reset();

    } else {
        // set error div text
        errors.innerHTML = "One / more parameters is invalid. Please check that 1 < num_replicas <= 8, 0 <= num_byzantine <= 10, 0 < num_transactions <= 10."
    }
});

// create the force directed graph
function generateGraphData(data) {
    let names = [];
    for (const elem of data) {
        let sender = elem["Sender"];
        let recipient = elem["Recipient"];

        names.push(sender);
        names.push(recipient);
    }

    names.push("Client");

    let nodes = [];
    let unique_names = [... new Set(names)];
    let name_id_mapper = {};
    let id = 0;
    for (const i of unique_names) {
        nodes.push({
            "id": id,
            "name": i,
        })
        name_id_mapper[i] = id;
        id++;
    }

    let links = [];
    for (const elem of data) {
        let sender = name_id_mapper[elem["Sender"]];
        let recipient = name_id_mapper[elem["Recipient"]];
        let primary = elem["Primary"];
        let type = elem["Type"];
        let visibleNumTransaction = elem["Visible_num_transaction"];
        let transaction = elem["Transaction"];
        let message = elem["Message"];

        links.push({
            "source": sender,
            "target": recipient,
            "primary": primary,
            "value": 1,
            "type": type,
            "visible_num_transaction": visibleNumTransaction,
            "transaction": transaction,
            "message": message
        })
    }

    let graphData = {
        "nodes": nodes,
        "links": links,
    }

    return graphData;
}

function displayLog(data) {
    let log = document.getElementById("log");
    let displayHTML = `<h5>Log</h5>
        <table id = 'logTable' style = 'width: 100%;'>
        <tr>
            <th>Sender</th>
            <th>Recipient</th>
            <th>Phase</th>
            <th>Communication</th>
        </tr>`;
    for (const logEntry of data) {
        let currDisplay = "<tr><td>" + logEntry["Sender"] + "</td><td>" + logEntry["Recipient"] + "</td><td>" + logEntry["Type"] + "</td><td>" + logEntry["Message"] + "</td></tr>";
        displayHTML += currDisplay;
    }
    displayHTML += "</table>";
    log.innerHTML = displayHTML;
}

function displayBank(bankData) {
    if (!bankData) {
        return;
    }

    let bank = document.getElementById("bankDisplay");
    let displayHTML = `<h5>Bank</h5>
        <table id = 'bankTable' style = 'width: 100%;'>
        <tr>
            <th>Customer</th>
            <th>Balance</th>
        </tr>`;
    for (const [customer, balanceValue] of Object.entries(bankData)) {
        let currDisplay = "<tr><td>" + customer + "</td><td>" + balanceValue["Balance"] + "</td></tr>";
        displayHTML += currDisplay;
    }
    displayHTML += "</table>";
    bank.innerHTML = displayHTML;
}

function findCurrLinks(sequentialLinks, i) {
    let visibleLinks = [];
    let currLink = sequentialLinks[i];
    let startPhase = currLink["type"];
    let currPhase = startPhase;
    while (currPhase === startPhase) {
        if (i >= sequentialLinks.length) {
            break;
        }
        currLink = sequentialLinks[i++]
        currPhase = currLink["type"];
        if (currPhase !== startPhase) {
            break;
        }
        visibleLinks.push(currLink);
    }
    return visibleLinks;
}

function generateForceGraph(data) {
    let width = 640;
    let height = 400;
    let idx = 0;

    let graphData = generateGraphData(data);
    let nodes = graphData["nodes"];
    let sequentialLinks = graphData["links"]
    let visibleLinks = findCurrLinks(sequentialLinks, idx);
    let currPrimary = "Replica_0";

    const forceNode = d3.forceManyBody();
    const forceLink = d3.forceLink(visibleLinks).strength(0);

    const simulation = d3.forceSimulation(nodes)
        .force("link", forceLink)
        .force("charge", forceNode)
        .force("center", d3.forceCenter())
        .on("tick", ticked);

    let svg = d3.select("#visualization")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [-width / 2, -height / 2, width, height])
        .attr("style", "max-width: 100%; height: auto; height: intrinsic;")

    let link = svg.append("g")
        .attr("stroke", "black")
        .attr("stroke-opacity", 0.5)
        .attr("stroke-width", 5)
    .selectAll("path")
    .data(visibleLinks)
    .join("path")
    .attr("marker-end","url(#end-arrow)");

    svg.append("svg:defs").append("svg:marker")
        .attr("id", "end-arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 15)
        .attr("markerWidth", 3)
        .attr("markerHeight", 3)
        .attr("orient", "auto")
        .append("svg:path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "black")
        .attr("opacity", 0.5);

    let node = svg.append("g")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
        .attr("r", 10)
        .attr("stroke", "black")
        .attr("fill", function (d) {
            return colorNodes(d.name);
        });

    let text = svg.selectAll("text")
        .data(nodes)
        .enter()
        .append("text")

    let textLabels = text
        .attr("x", d => d.x + 10)
        .attr("y", d => d.y + 10)
        .text(d => d.name)

    linkArc = d =>`M${d.source.x},${d.source.y}A0,0 0 0,1 ${d.target.x},${d.target.y}`

    let log = document.getElementById("logTable");
    let logRows = log.querySelectorAll("tr");

    let currRow = logRows[idx + 1];
    for (let i = 1; i < visibleLinks.length + 1; i++) {
        let loopRow = logRows[idx + i];
        loopRow.style["font-weight"] = "bold";
        loopRow.style["background"] = "beige";
    }
    prevIdx = idx + 1;
    let currT = 0;

    function ticked() {
        link.attr("d", linkArc);

        node 
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        textLabels
            .attr("dx", d => d.x + 10)
            .attr("dy", d => d.y + 10);
    }

    function update() {
        let prevVisibleLinks = visibleLinks.length;
        idx += prevVisibleLinks;
        if (idx >= sequentialLinks.length) {
            return;
        }

        visibleLinks = findCurrLinks(sequentialLinks, idx);
        console.log(visibleLinks);
        let probablePrimary = visibleLinks[0].primary;
        if (probablePrimary !== "") {
            currPrimary = probablePrimary;
        }

        currT = parseInt(visibleLinks[0].visible_num_transaction);

        link = link
            .data(visibleLinks)
            .join("path")
            .attr("marker-end","url(#end-arrow)");

        node = node.attr("fill", function(d) {
            if (d.name === currPrimary) {
                return colorNodes("Primary")
            }
            return colorNodes(d.name);
        });

        simulation.force("link").links(visibleLinks);
        simulation.restart();

        for (let i = prevIdx; i < prevIdx + prevVisibleLinks; i++) {
            let loopRow = logRows[i];
            loopRow.style["font-weight"] = "";
            loopRow.style["background"] = "";
        }
        
        currRow = logRows[idx + 1];

        for (let i = idx + 1; i < idx + 1 + visibleLinks.length; i++) {
            let loopRow = logRows[i];
            loopRow.style["font-weight"] = "bold";
            loopRow.style["background"] = "beige";
        }

        prevIdx = idx + 1;

        displayCurrentTransaction(currT);

        displayBank(bankData[idx]);
    }

    const next = d3.select("#nextButton")
        .on("click", update);
}
 