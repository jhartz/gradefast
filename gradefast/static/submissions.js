/*
 * GradeFast grade book
 * Copyright (C) 2015, Jake Hartz
 * Licensed under the MIT License
 */

/**
 * Tell the server that we want to edit this submission.
 *
 * @param {number} id - The ID of the submission that we want to edit.
 * @param {boolean} [dontPushState] - Whether to skip the history pushstate
 *        (i.e. if we're coming from a popstate).
 */
function goToSubmission(id, dontPushState) {
    // Show loading message
    section("loading");
    // Reset the document title
    document.title = docTitle;

    // Make the request
    post("get a submission...or is it POST a submission?haha", {
        id: id
    }, undefined, dontPushState);
}

/**
 * Update the grading interface for a new submission.
 *
 * @param {number} id - The ID of the submission.
 * @param {string} name - The name associated with the submission.
 * @param {number} [currentScore] - The current score of the submission.
 * @param {number} [maxScore] - The maximum score for the submission.
 * @param {boolean} [is_late] - Whether the submission is marked as late.
 * @param {string} [overallComments] - The overall comments for the submission.
 * @param {Object} [values] - The values for points, point hints,
 *        section deductions, and comments for individual grading items.
 * @param {boolean} [dontPushState] - Whether to skip the history pushstate
 *        (i.e. if we're coming from a popstate).
 */
function startSubmission(id, name, currentScore, maxScore, is_late, overallComments, values, dontPushState) {
    var isDifferent = currentSubmissionID !== id;
    currentSubmissionID = id;

    // Change the title and the current URL if necessary
    document.title = name + " - " + docTitle;
    if (!dontPushState && isDifferent) {
        history.pushState({
            id: id
        }, "", base + "gradebook/" + id);
    }

    // Set the name, reset the score, uncheck "Late", and reset the overall
    // comments
    $("#name").text(name);
    $("#current_score").text(typeof currentScore == "number" ? currentScore : maxScore);
    $("#max_score").text(maxScore);
    $("#late").prop("checked", !!is_late);
    $("#overall_comments").val(typeof overallComments == "string" ? overallComments : "")
                          .trigger("input");

    // Set (or reset) all the grade items
    if (!values) values = {};

    // Reset text or number inputs
    $(".points-input, .comments-input").each(function () {
        var val = values[this.id];
        if (typeof val == "undefined") val = $(this).attr("data-default");
        $(this).val("" + val);
    });
    // Reset boolean inputs (checkboxes)
    $(".point_hint-input, .section_deduction-input, .enabled-input").each(function () {
        $(this).prop("checked", !!values[this.id]);
    });

    // Make sure that enabled things are shown and disabled things are hidden
    var shownPaths = [];
    $(".enabled-input").each(function () {
        if (this.checked) {
            shownPaths.push($(this).attr("data-path-start"));
        }
    });

    $(".has-path").each(function () {
        if (shownPaths.indexOf($(this).attr("data-path")) != -1) {
            // It should be shown
            $(this).show();
        } else {
            // It should be hidden
            $(this).hide();
        }
    });

    // Show the grading interface (if necessary)
    section();

    // Resize textareas if necessary
    setTimeout(function () {
        $(".autoresize-textarea").trigger("input");

        if (isDifferent) {
            // Scroll to the top of the grading interface
            setTimeout(function () {
                $("#main")[0].scrollTop = 0;
            }, 1);
        }
    }, 1);
}
