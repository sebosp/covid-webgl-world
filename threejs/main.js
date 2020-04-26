if (!Detector.webgl) {
    Detector.addGetWebGLMessage();
} else {
    var current_index = 84;
    // By default focus the region with the max totals
    var current_stat_type = "top_cumulative"
    var autofocus = true;
    var colors = [0xc62828];
    var container = document.getElementById("globe-container");

    var chartWidth = 200
    var chartHeight = 200
    var chartMargin = ({top: 20, right: 20, bottom: 25, left: 50})
    var globe;

    // Add a bit of offset so that we can see the magnitude (z) axis when we use the automatic globe positioning
    // otherwise we are straight on top of the magnitude bar and it's not possible to see the height
    var target_offset = 0.0

    document.addEventListener('DOMContentLoaded', function () {
        var elems = document.querySelectorAll('.datepicker');
        var instances = M.Datepicker.init(elems,
            {
                minDate: new Date("2020-01-22"),
                maxDate: new Date("2020-04-02"),
                onSelect: changeDataFromDatePicker,
                autoClose: true,
            })
    });
    var datasetType = "confirmed"
    changeDataSet();
}

function toggleAutoFocus() {
    autofocus = !autofocus;
    document.getElementById("autofocus").innerHTML = autofocus ? "center_focus_strong" : "center_focus_weak";
}

function toggleStatType() {
    if (current_stat_type == "top_cumulative"){
        current_stat_type = "top_delta"
        document.getElementById("stat_type").innerHTML = "change_history"
    } else {
        current_stat_type = "top_cumulative"
        document.getElementById("stat_type").innerHTML = "present_to_all"
    }
    updateDisplays()
}

function changeDataFromDatePicker(newDate) {
    console.log("changeDataFromDatePicker")
    console.log(newDate)

}

function clearData() {
    var myNode = document.getElementById("globe-container");
    while (myNode.firstChild) {
        myNode.removeChild(myNode.firstChild);
    }
}

function incrementDayBy(offset) {
    current_index = (current_index + offset + window.data["series_stats"].length) % window.data["series_stats"].length;
    updateDisplays();
}

function translateGlobeTargetToLatLng() {
    return {
        lat: ((globe.target.y + target_offset) * 90) / (Math.PI / 2),
        lng: ((globe.target.x - target_offset - ((Math.PI / 2) * 3)) * 180) / Math.PI,
    }
}

function translateLatLngToGlobeTarget(lat, lng) {
    // Translates from Latitude,Longitude to the coordinates of the globe camera
    return {
        x: (Math.PI / 2) * 3 + ((Math.PI * lng) / 180) + target_offset,
        y: (((Math.PI / 2) * lat) / 90) - target_offset,
    }
}

function updateCountryD3Graph(location_idx) {
    // TODO: Use delta here
    console.log("Updating Coutry D3 Graph: ", location_idx);
    var myNode = document.getElementById("region-graph");
    while (myNode.firstChild) {
        myNode.removeChild(myNode.firstChild);
    }
    d3_data = Array()
    columns = window.data["series_stats"].map(d => d.name);
    d3_data = {
        y: "Number of Cases",
        series: [
            {
                name: window.data["locations"][location_idx]["location"],
                values: window.data["locations"][location_idx]["values"].map(d => d["abs"]),
            }
        ],
        dates: columns.map(d3.utcParse("%y-%m-%d"))
    };
    xScale = d3.scaleUtc()
        .domain(d3.extent(d3_data.dates))
        .range([chartMargin.left, chartWidth - chartMargin.right])
    yScale = d3.scaleLinear()
        .domain([0, d3.max(d3_data.series, d => d3.max(d.values))]).nice()
        .range([chartHeight - chartMargin.bottom, chartMargin.top])
    xAxis = g => g
        .attr("transform", `translate(0,${chartHeight - chartMargin.bottom})`)
        .call(d3.axisBottom(xScale).ticks(chartWidth / 80).tickSizeOuter(0))
    yAxis = g => g
        .attr("transform", `translate(${chartMargin.left},0)`)
        .call(d3.axisLeft(yScale))
        .call(g => g.select(".domain").remove())
        .call(g => g.select(".tick:last-of-type text").clone()
            .attr("x", 3)
            .attr("text-anchor", "start")
            .attr("font-weight", "bold")
            .text(d3_data.y))
    line = d3.line()
        .defined(d => !isNaN(d))
        .x((_d, i) => xScale(d3_data.dates[i]))
        .y(d => yScale(d));
    console.log("Creating SVG");
    const svg = d3.select("#region-graph")
        .append("div")
        // Container class to make it responsive.
        .classed("svg-container", true)
        .append("svg")
        // Responsive SVG needs these 2 attributes and no width and height attr.
        //.attr("viewBox", "0 0 600 400")
        // Class to make it responsive.
        .classed("svg-content-responsive", true)
        // Fill with a rectangle for visualization.
        .attr("viewBox", [0, 0, chartWidth, chartHeight])
        .attr("preserveAspectRatio", "xMinYMin meet")
        .style("overflow", "visible");

    svg.append("g")
        .call(xAxis);

    svg.append("g")
        .call(yAxis);

    svg.append("g")
        .attr("fill", "none")
        .attr("stroke", "#" + datasetColor(datasetType).getHexString())
        .attr("stroke-chartWidth", 1.5)
        .attr("stroke-linejoin", "round")
        .attr("stroke-linecap", "round")
        .selectAll("path")
        .data(d3_data.series)
        .join("path")
        .style("mix-blend-mode", "multiply")
        .attr("d", d => line(d.values));

    dayInfo = window.data["series_stats"][current_index]
    cutoffDate = d3.utcParse("%y-%m-%d")(dayInfo["name"])
    svg.append("line")
        .style("stroke", "white")
        .style("stroke-dasharray", "2px")
        .style("stroke-opacity", "0.5")
        .attr("x1", xScale(cutoffDate))
        .attr("x2", xScale(cutoffDate))
        .attr("y1", yScale.range()[0])
        .attr("y2", yScale.range()[1] + yScale.range()[1] / 10);

}

function centerLatLongWithMax() {
    if (!autofocus) {
        return
    }
    // {"locations": [{
    //     "lat": 10,
    //     "lon": 4.9,
    //     "location": "China - Hubei",
    //     "values": [
    //         { "scl": 0.0, "abs": 0},
    //         { "scl": 5.5, "abs": 25},
    //     ]
    //     }]
    // },
    // "series_stats": [{
    //     "name": "20-01-22",
    //     "top_cumulative": {
    //         "location_idx": 0,
    //         "value": 444
    //     },
    //     "total": 555
    // }]}
    dayStats = window.data["series_stats"][current_index]
    location_idx = dayStats[current_stat_type]["location_idx"]
    lat = window.data["locations"][location_idx]["lat"]
    lon = window.data["locations"][location_idx]["lon"]
    location_name = window.data["locations"][location_idx]["location"]
    document.getElementById("focus-region").innerHTML = location_name + ' - ' + window.data["locations"][location_idx]["values"][current_index]["abs"] + ' cases'
    globe_center_x_y = translateLatLngToGlobeTarget(lat, lon);
    globe.target.x = globe_center_x_y.x;
    globe.target.y = globe_center_x_y.y;
    updateCountryD3Graph(location_idx);

}
function datasetColor(datasetType) {
    barColor = 0x00ff00;
    if (datasetType == "deaths") {
        barColor = 0xb71c1c;
    } else if (datasetType == "confirmed") {
        barColor = 0xe65100;
    } else {
        barColor = 0xc6ff00;
    }
    return new THREE.Color(barColor);
}
function loadGlobeDataForDay() {
    console.log("loadGlobeDataForDay" + current_index);
    var subgeo = new THREE.Geometry();
    // By default, let's show the color based on the dataset type
    color = datasetColor(datasetType)
    for (i = 0; i < window.data["locations"].length; i++) {
        if ("hide" in window.data["locations"][i]["values"][current_index]){
            continue;
        }
        lat = window.data["locations"][i]["lat"];
        lon = window.data["locations"][i]["lon"];
        magnitude = 0
        dayStats = window.data["series_stats"][current_index]
        focus_stat_max_value = dayStats[current_stat_type]["value"]
        if (current_stat_type == "top_cumulative"){
            magnitude = window.data["locations"][i]["values"][current_index]["abs"] / focus_stat_max_value;
        } else {
            delta = window.data["locations"][i]["values"][current_index]["dlt"];
            magnitude = delta / focus_stat_max_value;
            if (delta > 0) {
                if (datasetType == "recovered"){
                    // More recovered = green
                    color = 0xc6ff00;
                } else {
                    // More confirmed/deaths = red
                    color = 0xb71c1c;
                }
            } else {
                if (datasetType == "recovered"){
                    // Less recovered = red
                    color = 0xb71c1c;
                } else {
                    // Less confirmed/deaths = green
                    color = 0xc6ff00;
                }
            }
            color = new THREE.Color(color)
        }
        if (magnitude > 1){
            console.log(focus_stat_max_value, dayStats, focus_stat_max_value, magnitude);
        }
        if (magnitude > 0) {
            magnitude = magnitude * 200;
            globe.addPoint(lat, lon, magnitude, color, subgeo);
        }
    }
    globe.setBaseGeometry(subgeo)
}
function updateDisplays(i) {
    console.log("updateDisplays for index:" + current_index);
    if (window.data) {
        if (i) {
            current_index = i % window.data["series_stats"].length;
        }
        dayInfo = window.data["series_stats"][current_index]
        document.getElementById("current-day").innerHTML = dayInfo["name"]
        if (current_stat_type == "top_cumulative"){
            console.log("this is top cummulative");
            stat_display = dayInfo["cumulative_global"] + " Global cumulative";
        } else {
            console.log("this is NOT top cummulative");
            stat_display = dayInfo["delta_global"] + " Delta Total";
        }
        document.getElementById("current-stats").innerHTML = stat_display
        globe.resetData();
        loadGlobeDataForDay()
        globe.createPoints();
        centerLatLongWithMax();
    }
}

function animate() {
    requestAnimationFrame(animate);
    globe.render();
}
function loadData(url) {
    document.body.style.backgroundImage = "url('images/loading.gif')";
    clearData();
    var xhr;
    globe = new DAT.Globe(container, datasetColor);
    animate();
    TWEEN.start();
    xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.onreadystatechange = function (e) {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                window.data = JSON.parse(xhr.responseText);
                document.body.style.backgroundImage = "none"; // remove loading
                updateDisplays();
            }
        }
    };
    xhr.send(null);
}
function changeDataSet() {
    select = document.getElementById("datasetSelection")
    datasetType = select.options[select.selectedIndex].value
    loadData('data/' + datasetType + '.json');
}
