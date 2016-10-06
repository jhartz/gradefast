// ==UserScript==
// @name         GradeFast to myCourses
// @namespace    https://mycourses.rit.edu/
// @version      0.2
// @description  Gets grades from GradeFast and puts them into a myCourses grade book
// @author       Jake Hartz
// @include      https://mycourses.rit.edu/d2l/lms/grades/admin/enter/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

var grades = [];
var gotGrades = false;
var $a;

var FEEDBACK_REPLACEMENTS = [
    [/\+0:/g, "-"]
];

window.addEventListener("load", function (event) {
    setTimeout(function () {
        var $btnContainer = $(".d2l-page-buttons-float").not(".d2l-page-buttons-spacer");
        $a = $('<a class="vui-button d2l-button d2l-left" id="GRADEFAST_IMPORT" role="button"><i>Import Grades from GradeFast</i></a>');
        $btnContainer.find(".clear").before($a);

        $a.click(function () {
            if (gotGrades) {
                // "Enter Next Grade"
                enterGrades();
                return;
            }

            if (!confirm("Are grades ordered by LAST name? (This is required)")) return;

            var server = prompt("GradeFast server:", "http://127.0.0.1:8051");
            if (!server) return;

            // Get the JSON grade data
            var xhr = GM_xmlhttpRequest({
                method: "GET",
                url: server + "/gradefast/grades.json",
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

            var $gradeInput = $(this).find("input");
            if ($gradeInput.length === 0) {
                console.log("Found container without an input inside: ", this);
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
                if (!click($htmlIframe.contents().find("a.vui-button-primary"))) {
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
        }, 2500);
    }, 500);
}



