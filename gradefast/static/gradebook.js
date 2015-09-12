/*
 * GradeFast grade book
 * Copyright (C) 2015, Jake Hartz
 * Licensed under the MIT License
 */

// usually /gradefast/gradebook/
var base = location.pathname.substring(0, location.pathname.indexOf("gradebook")) + "gradebook/";

// The ID of the current submission that we are on
var currentSubmissionID = null;

// The main gradebook grading elements
var $main;

/**
 * Send a simple POST request back to the server, adding in the current
 * submission ID.
 */
function post(path, data) {
    data.id = currentSubmissionID;
    $.ajax({
        method: "POST",
        dataType: "json",
        url: base + "_/" + path,
        data: data,
        error: function (xhr, textStatus, error) {
            alert("XHR Error with " + path + " (" + textStatus + "): " + error);
        },
        success: function (data, textStatus, xhr) {
            if (data.status != "Aight") {
                alert("Error with " + path + "): " + JSON.stringify(data));
                return;
            }
            // Update the current total score
            if (typeof data.currentScore == "number") {
                $("#current_score").text(data.currentScore);
            }
        }
    });
}

var tabindex = 10;
function writeGradeItems(table, grades, depth, path) {
    $.each(grades, function (index, grade) {
        var currentPath = path + "." + index;
        
        var headerNum = Math.min(depth + 3, 6);
        var $title = $(document.createElement("h" + headerNum));
        $title.text(grade.name);
        
        if (grade.grades) {
            // We have sub-grades
            // First, put in the title
            $(table).append($("<tr />").addClass("topborder").append($("<td />").attr("colspan", "2").append($title)));
            // Now, put in the sub-items
            writeGradeItems(table, grade.grades, depth + 1, currentPath);
        } else {
            // Just an ordinary grade item
            var $row;
            var $col;
            
            // Make the comments box
            var $textarea = $(document.createElement("textarea"));
            $textarea.attr({
                id: "comments" + currentPath,
                placeholder: "Comments",
                rows: "4"
            });
            $textarea.addClass("comments-input");
            $textarea.change(function () {
                post("comments", {
                    path: this.id,
                    value: this.value
                });
            });
            
            // Alrighty, let's add the title+comments row
            $col = $("<td />").attr("rowspan", "2").addClass("noborder");
            $col.append($textarea);
            $row = $("<tr />");
            if (index > 0) {
                $row.addClass("topborder");
            }
            $row.append($("<td />").append($title));
            $row.append($col);
            $(table).append($row);
            
            // Make the points input
            var $input = $(document.createElement("input"));
            $input.attr({
                id: "points" + currentPath,
                type: "number",
                "data-default": "" + grade.points,
                value: "" + grade.points,
                tabindex: ++tabindex
            });
            $input.addClass("points-input");
            $input.change(function () {
                post("points", {
                    path: this.id,
                    value: this.value
                });
            });
            
            // Make the points label
            var $label = $(document.createElement("label"));
            $label.text(" / " + grade.points);
            $label.attr("for", $input.attr("id"));
            
            // Add the input and label to a column
            $col = $("<td />");
            $col.css("padding-left", (depth * 20) + "px");
            $col.append($input).append($label);
            
            // Now, do we have any deductions to add?
            if (grade.deductions && grade.deductions.length) {
                var $dTable = $("<table />");
                $.each(grade.deductions, function (dIndex, dValue) {
                    var $dRow = $("<tr />");
                    
                    // Make the deduction checkbox
                    var $dInput = $(document.createElement("input"));
                    $dInput.attr({
                        id: "deduction" + currentPath + "." + dIndex,
                        type: "checkbox",
                        tabindex: ++tabindex
                    });
                    $dInput.addClass("deduction-input");
                    $dInput.click(function () {
                        post("deduction", {
                            path: this.id,
                            value: this.checked
                        });
                        
                        // Update the input
                        var oldVal = parseInt($input.val(), 10),
                            defaultVal = parseInt($input.attr("data-default"), 10);
                        if (isNaN(oldVal)) oldVal = defaultVal;
                        if (this.checked) {
                            // Subtract points
                            $input.val(Math.max(oldVal - dValue.minus, 0));
                        } else {
                            // Add points
                            $input.val(Math.min(oldVal + dValue.minus, defaultVal));
                        }
                        $input.change();
                    });
                    $dRow.append($("<td />").append($dInput));
                    
                    // Make the deduction labels
                    var $dLabel = $(document.createElement("label"));
                    $dLabel.attr("for", $dInput.attr("id"));
                    $dLabel.append($("<b />").text(" -" + dValue.minus + ": "));
                    $dRow.append($("<td />").append($dLabel));
                    
                    $dLabel = $(document.createElement("label"));
                    $dLabel.attr("for", $dInput.attr("id"));
                    $dLabel.append($("<i />").text(dValue.name));
                    $dRow.append($("<td />").append($dLabel));
                    
                    // Add the row to the table
                    $dTable.append($dRow);
                });
                $col.append($dTable);
            }
            
            // Finally, we can set the textarea's tabindex
            $textarea.attr("tabindex", "" + (++tabindex));
            
            // Now, we can add the points row
            $row = $("<tr />");
            $row.append($col);
            $(table).append($row);
        }
    });
}

function startSubmission(id, name) {
    currentSubmissionID = id;
    
    // Hide the dammit message
    $("#dammit").hide();

    // Hide the table and "Late" checkbox
    $main.hide();
    
    // Set the name, reset the score, uncheck "Late", and reset the overall
    // comments
    $("#name").text(name);
    $("#current_score").text(maxScore);
    $("#late").prop("checked", false);
    $("#overall_comments").val("").trigger("input");
    
    // Clear all the old grade items
    $(".points-input").each(function () {
        $(this).val($(this).attr("data-default"));
    });
    $(".comments-input").each(function () {
        $(this).val("");
    });
    $(".deduction-input").each(function () {
        $(this).prop("checked", false);
    });
    
    // Show the table and "Late" checkbox again
    $main.show();
    window.scrollTo(0, 0);
}

var evtSource;
$(document).ready(function () {
    $main = $("#score_container, #main, #main_footer");

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
        // reset the height
        this.style.height = "";
        // Calculate new height (min 40px, max 140px)
        var newHeight = Math.max(Math.min(this.scrollHeight + 3, 140), 40);
        this.style.height = newHeight + "px";
        //this.parentNode.style.height = (newHeight + 27) + "px";
    }).trigger("input");
    
    // Load the grade items
    if (isDone) {
        // We're done already!
        $("#done").show();
    } else {
        $("#dammit").show();
        var table = document.createElement("table");
        table.className = "bigtable";
        $("#main").append(table);
        writeGradeItems(table, gradeStructure, 0, "");
    }
    
    // Load the event stream
    evtSource = new EventSource(base + "events");
    
    evtSource.addEventListener("start_submission", function (event) {
        // Parse the JSON data
        var jsonData;
        try {
            jsonData = JSON.parse(event.data);
        } catch (err) {}
        if (jsonData && typeof jsonData.id == "number" && jsonData.name) {
            startSubmission(jsonData.id, jsonData.name);
        }
    }, false);
    
    evtSource.addEventListener("done", function (event) {
        // Hide main table and "Late" checkbox
        $main.hide();
        $("#name").text($("#name").attr("data-orig"));
        
        // Show the "done" container
        $("#done").show();
        
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
});
