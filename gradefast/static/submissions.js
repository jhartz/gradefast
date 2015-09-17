/*
 * GradeFast grade book
 * Copyright (C) 2015, Jake Hartz
 * Licensed under the MIT License
 */

/**
 * Tell the server that we want to edit this submission.
 *
 * @param {number} id - The ID of the submission that we want to edit.
 */
function goToSubmission(id) {
    post("get...or is it POST?haha", {
        id: id
    });
}

/**
 * Update the grading interface for a new submission.
 *
 * @param {number} id - The ID of the submission.
 * @param {string} name - The name associated with the submission.
 * @param {number} [currentScore] - The current score of the submission.
 * @param {boolean} [is_late] - Whether the submission is marked as late.
 * @param {string} [overallComments] - The overall comments for the submission.
 * @param {Object} [values] - The values for points, deductions, and comments
 * for individual grading items.
 */
function startSubmission(id, name, currentScore, is_late, overallComments, values) {
    var isDifferent = currentSubmissionID != id;
    currentSubmissionID = id;

    // Set the name, reset the score, uncheck "Late", and reset the overall
    // comments
    $("#name").html(name);
    $("#current_score").text(typeof currentScore == "number" ? currentScore : maxScore);
    $("#late").prop("checked", !!is_late);
    $("#overall_comments").val(typeof overallComments == "string" ? overallComments : "")
                          .trigger("input");

    // Set (or reset) all the grade items
    if (!values) values = {};

    $(".points-input").each(function () {
        $(this).val("" + values[this.id] || $(this).attr("data-default"));
    });
    $(".comments-input").each(function () {
        $(this).val(values[this.id] || "");
    });
    $(".deduction-input").each(function () {
        $(this).prop("checked", !!values[this.id]);
    });

    // Show the grading interface (if necessary)
    section();

    if (isDifferent) {
        // Scroll to the top of the grading interface
        setTimeout(function () {
            $("#main")[0].scrollTop = 0;
        }, 1);
    }
}
