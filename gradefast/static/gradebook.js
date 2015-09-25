/*
 * GradeFast grade book
 * Copyright (C) 2015, Jake Hartz
 * Licensed under the MIT License
 */

/**
 * Show a specific section and hide the others.
 *
 * @param {string} [sectionToShow] - The section to show (the ID of a section
 * element), or falsy to show the main grading interface.
 */
function section(sectionToShow) {
    $("section").each(function () {
        if (sectionToShow && this.id == sectionToShow) {
            $(this).show();
        } else {
            $(this).hide();
        }
    });

    // Show/hide all components of the main grading interface
    var $main = $("#name, #score_container, #main, #main_footer");
    var $notmain = $("#title");
    if (sectionToShow) {
        // We showed something other than the main grading interface;
        // hide it all and show the generic title
        $main.hide();
        $notmain.show();
    } else {
        // Show the main grading interface; hide the generic title
        $notmain.hide();
        $main.show();
    }
}

var requestQueue = [];
requestQueue.push = function () {
    // First, push the new guy onto the array
    var length = Array.prototype.push.apply(this, arguments);
    // Next, if this is the only element in the array, then we need to run it.
    // Otherwise, it will be run after the current request completes.
    if (length == 1) {
        // Start the AJAX request
        ajaxRequestQueue();
    }
    // Finally, return the new length of the array
    return length;
};

/**
 * Send a simple POST request back to the server, adding in the current
 * submission ID.
 */
function post(path, data, onsuccess, dontPushState) {
    var id = data.id;
    if (typeof id != "number") {
        id = data.id = currentSubmissionID;
    }

    // Add this to the request queue
    requestQueue.push({
        url: base + "_/" + path,
        data: data,
        onsuccess: function (data) {
            if (!data || data.status != "Aight") {
                alert("Error with \"" + path + "\":\n" + JSON.stringify(data));
            } else {
                // See if there is an "onsuccess" that we should run
                if (typeof onsuccess == "function") {
                    onsuccess(data);
                }
                // Update the grading interface (including the current score)
                startSubmission(id, data.name, data.currentScore, data.maxScore, data.is_late, data.overallComments, data.values, dontPushState);
            }
        }
    });
}

function ajaxRequestQueue() {
    // Function to run the "next" AJAX request, if there's one in the queue
    function next() {
        setTimeout(function () {
            // We're all done with the last one
            requestQueue.shift();
            // Check if we have more POST requests to do
            if (requestQueue.length) {
                // Do the next one
                ajaxRequestQueue();
            }
        }, 10);
    }

    // For THIS request
    var request = requestQueue[0];
    $.ajax({
        method: "POST",
        dataType: "json",
        url: request.url,
        data: request.data || {},
        error: function (xhr, textStatus, error) {
            alert("XHR Error with \"" + url + "\" (" + textStatus + "): " + error);
            next();
        },
        success: function (data, textStatus, xhr) {
            request.onsuccess(data);
            next();
        }
    });
}

var evtSource;
$(document).ready(function () {
    // Make sure we're using the correct submission ID
    if (history.state && typeof history.state.id == "number") {
        currentSubmissionID = history.state.id;
    }

    // Set up the CSV and JSON links (for when we're done)
    $("#csv_link").attr("href", base + "grades.csv");
    $("#json_link").attr("href", base + "grades.json");
    
    // "Name" original text
    $("#name").attr("data-orig", $("#name").text());
    
    // "Late" checkbox
    $("#late").click(function () {
        post("late", {
            is_late: "" + this.checked
        });
    });

    // Overall comments
    $("#overall_comments").change(function () {
        post("overall_comments", {
            value: this.value
        });
    }).on("input", function () {
        // Reset the height
        this.style.height = "auto";
        // Calculate new height (min 40px, max 140px)
        var newHeight = Math.max(Math.min(this.scrollHeight + 3, 140), 40);
        this.style.height = newHeight + "px";
        //this.parentNode.style.height = (newHeight + 27) + "px";
    }).trigger("input");
    
    // Load the event stream
    evtSource = new EventSource(base + "events.stream");
    
    evtSource.addEventListener("start_submission", function (event) {
        // Parse the JSON data
        var jsonData;
        try {
            jsonData = JSON.parse(event.data);
        } catch (err) {}
        if (jsonData && typeof jsonData.id == "number") {
            // Tell the forces at large to start this submission
            goToSubmission(jsonData.id);
        }
    }, false);
    
    evtSource.addEventListener("done", function (event) {
        // All done! Close the event stream
        evtSource.close();

        // Reset the title at the top of the page
        $("#name").text($("#name").attr("data-orig"));
        
        // Show the "done" section
        section("done");
        
        // Parse the JSON data
        var jsonData;
        try {
            jsonData = JSON.parse(event.data);
        } catch (err) {}
        if (jsonData && jsonData.grades && jsonData.grades.length) {
            // Show a summary of the grades
            $.each(jsonData.grades, function (index, value) {
                var $details = $(document.createElement("details"));
                $details.append($(document.createElement("summary")).text(value.name + ": " + value.score));
                $details.append(value.feedback);
                $("#summary").append($details);
            });
        }
    }, false);

    // Load the grade items
    if (isDone) {
        // We're done already!
        section("done");
    } else {
        // Create the grade structure table
        var table = document.createElement("table");
        table.className = "bigtable";
        $("#main").append(table);
        createGradeStructure(table, gradeStructure, 0, "");

        // Start something or show a message
        if (currentSubmissionID !== null) {
            goToSubmission(currentSubmissionID);
        } else {
            // Show the "start a submission" message
            section("dammit");
        }
    }

    // Set up popstate
    window.addEventListener("popstate", function (event) {
        if (event.state && typeof event.state.id == "number") {
            goToSubmission(event.state.id, true);
        }
    }, false);
});
