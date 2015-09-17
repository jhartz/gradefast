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
    var $main = $("#score_container, #main, #main_footer");
    if (sectionToShow) {
        // We showed something other than the main grading interface;
        // hide it all
        $main.hide();
    } else {
        // Show the main grading interface
        $main.show();
    }
}

/**
 * Send a simple POST request back to the server, adding in the current
 * submission ID.
 */
function post(path, data, onsuccess) {
    var id = data.id;
    if (typeof id != "number") {
        id = data.id = currentSubmissionID;
    }
    $.ajax({
        method: "POST",
        dataType: "json",
        url: base + "_/" + path,
        data: data,
        error: function (xhr, textStatus, error) {
            alert("XHR Error with \"" + path + "\" (" + textStatus + "): " + error);
        },
        success: function (data, textStatus, xhr) {
            if (data.status != "Aight") {
                alert("Error with \"" + path + "\":\n" + JSON.stringify(data));
                return;
            }
            // Run onsuccess if necessary
            if (typeof onsuccess == "function") {
                onsuccess(data);
            }
            // Update the grading interface (including the current score)
            startSubmission(id, data.name, data.currentScore, data.is_late, data.overallComments, data.values);
        }
    });
}

var evtSource;
$(document).ready(function () {
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
        this.style.height = "";
        // Calculate new height (min 40px, max 140px)
        var newHeight = Math.max(Math.min(this.scrollHeight + 3, 140), 40);
        this.style.height = newHeight + "px";
        //this.parentNode.style.height = (newHeight + 27) + "px";
    }).trigger("input");
    
    // Load the event stream
    evtSource = new EventSource(base + "events");
    
    evtSource.addEventListener("start_submission", function (event) {
        // Parse the JSON data
        var jsonData;
        try {
            jsonData = JSON.parse(event.data);
        } catch (err) {}
        if (jsonData && typeof jsonData.id == "number") {
            // Show loading message
            section("loading");
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
});
