// ==UserScript==
// @name         GradeFast to myCourses
// @namespace    https://mycourses.rit.edu/
// @version      0.3
// @description  Gets grades from GradeFast and puts them into a myCourses grade book
// @author       Jake Hartz
// @include      https://mycourses.rit.edu/d2l/lms/grades/admin/enter/grade_item_edit.d2l?*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      *
// ==/UserScript==

/*
 * This userscript gets grade and feedback data from GradeFast and injects it into an RIT myCourses
 * grade book. This requires that the GradeFast server be running (it sends a request to the server
 * to get the JSON grade data).
 *
 * To use this userscript, install either GreaseMonkey (in Firefox) or TamperMonkey (in Chrome).
 * Then, on myCourses grade entry pages, you should see a new button in the bottom-right of the
 * page titled "Import Grades from GradeFast". Click this to begin.
 *
 * When you click the "Import Grades from GradeFast" button, it'll prompt you for the URL to the
 * GradeFast server's JSON export. You can copy-paste this from the GradeFast grade book page
 * (see the "JSON" link in the top-right of that page). The key on the end of this URL changes for
 * each GradeFast session.
 *
 * After it enters each grade and the corresponding feedback, you should look it over, then click
 * Save. Then, click "Insert next GradeFast grade" to continue on to the next.
 *
 * DISCLAIMER: This is quite some hacky JavaScript that I'm sure won't continue working. Basically,
 * it just uses the GradeFast JSON export API to get a JSON file containing the grades, and then
 * dissects the myCourses grade book DOM to figure out where to stick the data. It will likely
 * break with some future myCourses update.
 *
 * For updates, grab the latest version from the GradeFast git repo at:
 * https://github.com/jhartz/gradefast/tree/master/utilities
 *
 * If you have any improvements, feel free to create a pull request!
 */

var grades = [];
var gotGrades = false;
var $a;

var FEEDBACK_REPLACEMENTS = [
    [/\+0:/g, "-"]
];

console.log("GRADEFAST USERSCRIPT RUNNING");

window.addEventListener("load", function (event) {
    setTimeout(function () {
        console.log("INSERTING GRADEFAST BUTTON");
        $a = $('<button id="GRADEFAST_IMPORT" style="position: fixed; right: 10px; bottom: 10px; font-size: 200%; font-weight: bold; z-index: 9999;">Import Grades from GradeFast</button>');
        $("body").append($a);

        $a.click(function () {
            if (gotGrades) {
                // "Enter Next Grade"
                enterGrades();
                return;
            }

            if (!confirm("Are grades ordered by LAST name? (This is required)")) return;

            var jsonUrl = prompt(
                "GradeFast JSON URL:\n(for more info, read the documentation at the top of the userscript)",
                "http://127.0.0.1:8051/gradefast/grades.json?.....");
            if (!jsonUrl) return;

            // Get the JSON grade data
            var xhr = GM_xmlhttpRequest({
                method: "GET",
                url: jsonUrl,
                onload: function (response) {
                    if (response.status != 200) {
                        alert("Request failed: " + response.status + " (" + response.statusText + "):\n" +
                            response.responseText);
                        return;
                    }

                    var jsonGrades;
                    try {
                        jsonGrades = JSON.parse(response.responseText);
                    } catch (err) {
                        alert("Error parsing JSON: " + err.message);
                    }
                    if (jsonGrades) {
                        if (!jsonGrades.length) {
                            alert("No grades :(");
                        } else {
                            matchRowsAndGrades(jsonGrades);
                            gotGrades = true;
                            $a.html("<i>Insert next GradeFast grade</i>");
                        }
                    }
                },
                onerror: function (response) {
                    alert("Request failed: " + response.status + " (" + response.statusText + ")\n" +
                        response.responseText);
                }
            });
        });
    }, 2000);
}, false);

function click($el) {
    if ($el.length) {
        var evt = document.createEvent("Event");
        evt.initEvent("click", true, false);
        $el[0].dispatchEvent(evt);
        return true;
    }
}

function matchRowsAndGrades(jsonGrades) {
    // A list of objects with: "score", "feedback", "$gradeInput", "$feedbackBtn"
    var gradesToEnter = [];

    // Loop through each table row
    $(".dsh_c").each(function () {
        try {
            var $row = $(this).closest("tr");
            if ($row.length === 0) {
                console.log("Found container whose ancestor was not a table row: ", this, $row);
                return;
            }

            var $gradeInput = $(this).find("input.d_edt");
            if ($gradeInput.length === 0) {
                console.log("Found container without a grade input inside: ", this);
                return;
            }

            var $feedbackBtn = $row.find("a[id^='ICN_Feedback']");
            if ($feedbackBtn.length === 0) {
                console.log("Found table row without a feedback button: ", $row);
                return;
            }

            var name = $row[0].getElementsByTagName("th")[0].textContent.trim();
            console.log("Found table row with name: " + name);

            // Find a grade that matches this name
            var grade;
            for (var i = 0; i < jsonGrades.length; i++) {
                // See if the name of this grade matches the beginning of name
                if (jsonGrades[i].name == name.substring(0, jsonGrades[i].name.length)) {
                    // Found it!
                    console.log("Matches grade: " + jsonGrades[i].name);
                    grade = jsonGrades[i];
                    break;
                }
            }

            // Did we find a matching grade?
            if (!grade) {
                console.log("No matching grade found");
            } else {
                // Woohoo!
                gradesToEnter.push({
                    score: grade.score,
                    feedback: grade.feedback,
                    $gradeInput: $gradeInput,
                    $feedbackBtn: $feedbackBtn
                });
            }
        } catch (err) {
            console.log("Error doing table row", err);
            alert("Error doing table row\nSee error console");
        }
    });

    // Start entering the grades!
    grades = gradesToEnter;
    enterGrades();
}

function enterGrades() {
    if (grades.length === 0) {
        // All done
        alert("Done entering grades");
        gotGrades = false;
        $a.html("<i>Import Grades from GradeFast</i>");
        return;
    }

    // Enter the first grade
    var grade = grades.shift();
    grade.$gradeInput.val("" + grade.score).change();
    setTimeout(function () {
        // Open the feedback iframe
        if (!click(grade.$feedbackBtn)) {
            console.log("Couldn't click Feedback button for grade", grade);
            alert("Couldn't click Feedback button!");
            return;
        }

        setTimeout(function () {
            // Get the Feedback iframe
            var $feedbackIframe = $("iframe").not("[id^='overallComments']");
            if ($feedbackIframe.length === 0) {
                console.log("Couldn't find Feedback iframe for grade", grade);
                alert("Couldn't find Feedback iframe!");
                return;
            }

            // Click the "Toggle Fullscreen" button
            click($feedbackIframe.contents().find("a[title='Toggle Fullscreen']"));

            // Click the "Edit HTML" button
            if (!click($feedbackIframe.contents().find("a[title='HTML Source Editor']"))) {
                console.log("Couldn't click Edit HTML button for grade", grade);
                alert("Couldn't click Edit HTML button!");
                return;
            }

            setTimeout(function () {
                // Get the Edit HTML iframe
                var $htmlIframe = $("iframe.d2l-dialog-frame[src*='blank']");
                if ($htmlIframe.length != 1) {
                    console.log("Couldn't find Edit HTML iframe for grade", grade, $htmlIframe);
                    alert("Couldn't find Edit HTML iframe!");
                    return;
                }

                // Do any replacements necessary in the feedback contents
                var fb = FEEDBACK_REPLACEMENTS.reduce(function (fb, replacement, index) {
                    return fb.replace(replacement[0], replacement[1]);
                }, "" + grade.feedback);
                // There should only be one textarea
                $htmlIframe.contents().find("textarea").val(fb).change();

                // Click the save button
                if (!click($htmlIframe.contents().find("button[primary]"))) {
                    alert("Couldn't click Save button!");
                    return;
                }

                /*
                setTimeout(function () {
                // Recurse to do the rest
                    enterGrades(grades);
                }, 200);
                */
            }, 2500);
        }, 3000);
    }, 500);
}



