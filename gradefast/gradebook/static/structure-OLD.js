/*
 * GradeFast grade book
 * Copyright (C) 2015, Jake Hartz
 * Licensed under the MIT License
 */

var tabindex = 10;

/**
 * Create and insert the DOM elements for this grading structure.
 *
 * @param {Element} table - The HTML table element that we are inserting
 * rows in to for each grade item
 * @param {Array} grades - The grade items (subset of grade structure)
 * @param {number} depth - How deep we are in the grade structure
 * @param {string} path - The position within the grade structure where we are
 */
function createGradeStructure(table, grades, depth, path) {
    $.each(grades, function (index, grade) {
        var currentPath = path + "." + index;

        var $title = $("<div />");

        // Make the enabled/disabled checkbox
        var $enabled = $(document.createElement("input"));
        $enabled.attr({
            id: "enabled" + currentPath,
            type: "checkbox",
            tabindex: ++tabindex,
            "data-path-start": currentPath
        });
        $enabled.addClass("enabled-input").addClass("bigger");
        $enabled.click(function () {
            post("enabled", {
                path: this.id,
                value: this.checked
            })
        });

        // Add the checkbox and the actual name into $title
        var headerNum = Math.min(depth + 3, 6);
        $title.append(
            $(document.createElement("h" + headerNum)).append(
                $enabled
            ).append(
                $("<label />").attr("for", $enabled.attr("id")).text(grade.name)
            )
        );

        if (grade.grades) {
            // We have sub-grades
            // First, put in the title and grader notes
            var $titleRow = $("<tr />").addClass("topborder highlight");
            if (path) {
                // This title row uses its parent's path so that the title
                // itself isn't hidden if this section is disabled
                $titleRow.addClass("has-path").attr("data-path", path);
                /*
                // But for other ID'ing, we'll specify the "real" path too
                // (allows us to blacken it out)
                $titleRow.attr("data-path-absolut", currentPath);
                */
            }
            if (grade.note || grade.notes) {
                $titleRow.append($("<td />").append($title));
                $titleRow.append($("<td />").append(renderNotes(grade.note || grade.notes)));
            } else {
                $titleRow.append($("<td />").attr("colspan", "2").append($title));
            }
            $(table).append($titleRow);

            // Next, put in the section deductions table
            $(table).append(
                $("<tr />").addClass("has-path highlight").attr("data-path", currentPath).append(
                    $("<td />").attr("colspan", "2")
                               .css("padding-left", (depth * 20) + "px")
                               .append(
                        makeCheckboxTable(grade["section deductions"], "section_deduction", currentPath))
                )
            );

            // Now, put in the sub-items
            createGradeStructure(table, grade.grades, depth + 1, currentPath);
        } else {
            // Just an ordinary grade item
            var $row;
            var $col;

            // Make the comments box
            var $textarea = $(document.createElement("textarea"));
            var defaultCommentValue = "" + (grade["default comments"] || "");
            $textarea.attr({
                id: "comments" + currentPath,
                placeholder: "Comments (Markdown-parsed)",
                rows: "4",
                value: defaultCommentValue,
                "data-default": defaultCommentValue,
                "data-path": currentPath
            });
            $textarea.addClass("comments-input").addClass("has-path").addClass("autoresize-textarea");
            $textarea.change(function () {
                post("comments", {
                    path: this.id,
                    value: this.value
                });
            }).on("input", function () {
                // Auto-resize this textarea if necessary
                var $this = $(this);
                 checkTextareaResize($this, $this.closest(".autoresize-textarea-parent"));
            });
            if (grade["default comments"]) {
                $textarea.val("" + grade["default comments"]);
            }

            // Alrighty, let's add the title+notes+comments row (inner smalltable)
            var $innerTbody = $("<tbody />");
            if (grade.note || grade.notes) {
                $innerTbody.append($("<tr />").append($("<td />").append(
                    renderNotes(grade.note || grade.notes))));
            } else {
                $innerTbody.append($("<tr />").append($("<td />")));
            }
            $innerTbody.append($("<tr />").append(
                $("<td />").addClass("bigboyheftymama").append($textarea)));

            $col = $("<td />").attr("rowspan", "2").addClass("autoresize-textarea-parent");
            $col.append($("<table />").addClass("smalltable").append($innerTbody));
            // $col is appended in below after the title

            $row = $("<tr />");
            // (This title row uses its parent's path due to reasons)
            if (path) $row.addClass("has-path").attr("data-path", path);
            if (index > 0) {
                $row.addClass("topborder");
            }
            $row.append($("<td />").append($title));
            $row.append($col);
            $(table).append($row);

            // Time for the points and point hints
            var $pointsContainer = $("<div />").addClass("has-path")
                                               .attr("data-path", currentPath);

            // Make the points input
            var $input = $(document.createElement("input"));
            var defaultPointsValue = grade.points;
            if (typeof grade["default points"] == "number") {
                defaultPointsValue = grade["default points"];
            }
            $input.attr({
                id: "points" + currentPath,
                type: "number",
                "data-default": "" + defaultPointsValue,
                value: "" + defaultPointsValue,
                tabindex: ++tabindex
            });
            $input.addClass("points-input");
            $input.change(function () {
                post("points", {
                    path: this.id,
                    value: this.value
                });
            });
            $pointsContainer.append($input);

            // Make the points label
            var $label = $(document.createElement("label"));
            $label.text(" / " + grade.points);
            $label.attr("for", $input.attr("id"));
            $label.addClass("noselect");
            $pointsContainer.append($label);

            // Now, do we have any point hints?
            $pointsContainer.append(makeCheckboxTable(grade["point hints"], "point_hint", currentPath, $input));

            // Make a column to hold the container
            $col = $("<td />").addClass("bigboyheftymama");
            $col.css("padding-left", (depth * 20) + "px");
            $col.append($pointsContainer);

            // Finally, we can set the textarea's tabindex
            $textarea.attr("tabindex", "" + (++tabindex));

            // Now, we can add the points row
            $row = $("<tr />");
            $row.append($col);
            $(table).append($row);
        }
    });
}

/**
 * Render some grader notes.
 * @param {string} notes - The newline-separated grader notes.
 * @return {Element} The element containing the notes.
 */
function renderNotes(notes) {
    var $notes = $("<div />");
    $.each(notes.split("\n"), function (index, note) {
        if (index) $notes.append($("<br />"));
        $notes.append($("<em />").text(note));
    });
    return $notes;
}

/**
 * Make a textarea be big enough to see all its contents at once, or big enough
 * to fill its parent, or be its minimum height, whichever is greatest.
 * @param $textarea - The jQuery object representing the testarea.
 * @param $parent - The jQuery object representing the resizable parent.
 */
function checkTextareaResize($textarea, $parent) {
    // First, make sure it's not hidden
    if ($textarea.is(":hidden")) return;

    // Reset the height to its default and collect some base info
    $textarea.css("height", "auto");
    var origHeight = $textarea[0].scrollHeight + 3;
    var origParentHeight = $parent[0].scrollHeight;

    var currentHeight = origHeight;
    if (origHeight < origParentHeight) {
        // Increase this guy's height until its parent feels the bulge, or
        // until we hit a sane max (5x the original)
        while ($parent[0].scrollHeight <= origParentHeight &&
                currentHeight < origHeight * 5) {
            currentHeight += 2;
            $textarea.css("height", currentHeight + "px");
        }
        if (currentHeight == origHeight * 3) {
            console.log("HEIGHT WAS ALMOST TOO BIG: ", $textarea[0]);
        }
        currentHeight -= 2;
    }
    $textarea.css("height", currentHeight + "px");
}

/**
 * Make a table of checkboxes and labels.
 * @param {Array} items - The list of items to make checkboxes for. Each must
 *        have a `name` and either `value` or `minus`.
 * @param {string} type - What these items are, usually either
 *        "section_deduction" or "point_hint".
 * @param {string} currentPath - The position within the grade structure where
 *        we are.
 * @param [$input] - The jQuery object representing the element holding the
 *        user's score for this. If not provided, it is assumed that this
 *        checkbox table does not affect a points input, and `minus` is used
 *        instead of `value`.
 */
function makeCheckboxTable(items, type, currentPath, $input) {
    var $dTable = $("<table />");
    if (items) {
        $.each(items, function (dIndex, dValue) {
            var $dRow = $("<tr />");

            // Make the checkbox
            var $dInput = $(document.createElement("input"));
            $dInput.attr({
                id: type + currentPath + "." + dIndex,
                type: "checkbox",
                tabindex: ++tabindex
            });
            $dInput.addClass(type + "-input");
            $dInput.click(function () {
                post(type, {
                    path: this.id,
                    value: this.checked
                });

                if ($input) {
                    // Update the input
                    var oldVal = parseInt($input.val(), 10),
                        defaultVal = parseInt($input.attr("data-default"), 10);
                    if (isNaN(oldVal)) oldVal = defaultVal;

                    var delta = 0;
                    if (this.checked) {
                        // Add the value in
                        delta += dValue.value;
                    } else {
                        // Subtract the value back out
                        delta -= dValue.value;
                    }

                    if (!checkPointHintRange) {
                        // Just apply the point hint, no matter what
                        $input.val("" + (oldVal + delta));
                    } else {
                        // Make sure that applying the point hint doesn't go
                        // out of range
                        if (delta < 0) {
                            // Subtract points
                            $input.val("" + Math.max(oldVal + delta, 0));
                        } else {
                            // Add points
                            $input.val("" + Math.min(oldVal + delta, defaultVal));
                        }
                    }
                    $input.change();
                }
            });
            $dRow.append($("<td />").append($dInput));

            // Make the section deduction labels
            var value = $input ? dValue.value : (-1 * dValue.minus);
            var $dLabel = $(document.createElement("label"));
            $dLabel.attr("for", $dInput.attr("id"));
            $dLabel.append($("<b />").text(" " + value + ": "));
            $dRow.append($("<td />").append($dLabel));

            $dLabel = $(document.createElement("label"));
            $dLabel.attr("for", $dInput.attr("id"));
            $dLabel.append($("<i />").text(dValue.name));
            $dRow.append($("<td />").append($dLabel));

            // Add the row to the table
            $dTable.append($dRow);
        });
    }

    // Make the last row to add another item
    var $dRow = $("<tr />");
    // Make an empty/disabled checkbox
    $dRow.append($("<td />").append($("<input />").attr({
        type: "checkbox",
        disabled: "disabled"
    })));

    // Make the link to do the magic
    var linkTitle = "Add " + ((items && items.length) ? "another" : "a") + " " + type.replace(/_/g, " ");
    var $a = $("<a />").text(linkTitle + "...").attr("href", "#");
    $a.click(function (event) {
        event.preventDefault();
        var name = prompt("Name (Markdown-parsed):");
        if (!name) return;

        var value = prompt("Point delta (positive number to ADD POINTS;" +
            " negative number to DEDUCT POINTS)", "0");
        if (!value) return;
        value = Number(value);
        if (isNaN(value)) return;

        // Show "loading"
        section("loading");
        // Tell the server about this guy
        post("add_" + type, {
            path: currentPath,
            name: name,
            value: Number(value)
        }, function () {
            // We need to reload the grading structure
            location.reload();
        });
    });
    $dRow.append($("<td />").attr("colspan", "2").append($a));
    // Add the "New _______" row to the table
    $dTable.append($dRow);
    // Return the table
    return $dTable;
}
