function onload(data) {
    displayLog(data);
    generateForceGraph(data);
}

$('#submitButton').on('click', function() {
    console.log($('#num_replicas').text);
    $.ajax({
        url: '/restart_pbft',
        type: 'GET',
        dataType: 'json',
        success: function() { 
        },
        error: function(e) { 
        },
        beforeSend: setHeader
    });
});

function setHeader(xhr) {
    let num_replicas = document.getElementById('num_replicas').value;
    let num_byzantine = document.getElementById('num_byzantine').value;
    let num_transactions = document.getElementById('num_transactions').value;
    
    xhr.setRequestHeader("num_replicas", num_replicas);
    xhr.setRequestHeader("num_byzantine", num_byzantine);
    xhr.setRequestHeader("num_transactions", num_transactions);
}

// create the force directed graph
function generateGraphData(data) {
    let names = [];
    for (const elem of data) {
        let sender = elem["Sender"];
        let recipient = elem["Recipient"];

        names.push(sender);
        names.push(recipient);
    }

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
        let type = elem["Type"];

        links.push({
            "source": sender,
            "target": recipient,
            "value": 1,
            "type": type,
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
        </tr>`;
    for (const logEntry of data) {
        let currDisplay = "<tr><td>" + logEntry["Sender"] + "</td><td>" + logEntry["Recipient"] + "</td><td>" + logEntry["Type"] + "</td></tr>";
        displayHTML += currDisplay;
    }
    displayHTML += "</table>";
    log.innerHTML = displayHTML;
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
        .attr("stroke-opacity", 0.6)
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
        .attr("fill", "black");

    let node = svg.append("g")
        .attr("fill", "red")
        .attr("stroke", "black")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
        .attr("r", 10);

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
    currRow.style["font-weight"] = "bold";

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
        idx += visibleLinks.length;
        if (idx >= sequentialLinks.length) {
            return;
        }

        visibleLinks = findCurrLinks(sequentialLinks, idx);

        link = link
            .data(visibleLinks)
            .join("path")
            .attr("marker-end","url(#end-arrow)");

        simulation.force("link").links(visibleLinks);
        simulation.restart();

        currRow.style["font-weight"] = "";
        currRow = logRows[idx + 1];
        currRow.style["font-weight"] = "bold";
    }

    const next = d3.select("#nextButton")
        .on("click", update);
}
 