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
            var $titleRow = $("<tr />").addClass("topborder");
            // (This title row uses its parent's path due to reasons)
            if (path) $titleRow.addClass("has-path").attr("data-path", path);
            if (grade.note || grade.notes) {
                $titleRow.append($("<td />").append($title));
                $titleRow.append($("<td />").append($("<em />").text(grade.note || grade.notes)));
            } else {
                $titleRow.append($("<td />").attr("colspan", "2").append($title));
            }
            $(table).append($titleRow);

            // Next, put in the deductions table
            $(table).append(
                $("<tr />").addClass("has-path").attr("data-path", currentPath).append(
                    $("<td />").attr("colspan", "2")
                               .css("padding-left", (depth * 20) + "px")
                               .append(
                        makeCheckboxTable(grade.deductions, "deduction", currentPath))
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
            $textarea.addClass("comments-input").addClass("has-path");
            $textarea.change(function () {
                post("comments", {
                    path: this.id,
                    value: this.value
                });
            });
            if (grade["default comments"]) {
                $textarea.val("" + grade["default comments"]);
            }

            // Alrighty, let's add the title+notes+comments row
            $col = $("<td />").attr("rowspan", "2");
            if (grade.note || grade.notes) {
                $col.append($("<em />").text(grade.note || grade.notes));
            }
            $col.append($textarea);

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
            $col = $("<td />");
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
 * Make a table of checkboxes and labels.
 * @param {Array} items - The list of items to make checkboxes for. Each must
 *        have a `name` and either `value` or `minus`.
 * @param {string} type - What these items are, usually either "deduction" or
 *        "point_hint".
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

                    if (delta < 0) {
                        // Subtract points
                        $input.val("" + Math.max(oldVal + delta, 0));
                    } else {
                        // Add points
                        $input.val("" + Math.min(oldVal + delta, defaultVal));
                    }
                    $input.change();
                }
            });
            $dRow.append($("<td />").append($dInput));

            // Make the deduction labels
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
        var value;

        if ($input) {
            value = Number(prompt("Points to add (or negative number to" +
                " deduct):", "0"));
        } else {
            value = -1 * Number(prompt("Points to deduct:", "0"));
        }
        if (!isNaN(value)) {
            // Show "loading"
            section("loading");
            // Tell the server about this guy
            post("add_" + type, {
                path: currentPath,
                name: name,
                value: value
            }, function () {
                // We need to reload the grading structure
                location.reload();
            });
        }
    });
    $dRow.append($("<td />").attr("colspan", "2").append($a));
    // Add the "New _______" row to the table
    $dTable.append($dRow);
    // Return the table
    return $dTable;
}
