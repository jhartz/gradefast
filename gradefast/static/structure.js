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

        var headerNum = Math.min(depth + 3, 6);
        var $title = $(document.createElement("h" + headerNum));
        $title.html(grade.name);

        if (grade.grades) {
            // We have sub-grades
            // First, put in the title
            $(table).append($("<tr />").addClass("topborder").append($("<td />").attr("colspan", "2").append($title)));
            // Now, put in the sub-items
            createGradeStructure(table, grade.grades, depth + 1, currentPath);
        } else {
            // Just an ordinary grade item
            var $row;
            var $col;

            // Make the comments box
            var $textarea = $(document.createElement("textarea"));
            $textarea.attr({
                id: "comments" + currentPath,
                placeholder: "Comments (HTML Allowed)",
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
            var $dTable = $("<table />");
            if (grade.deductions) {
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
                            $input.val("" + Math.max(oldVal - dValue.minus, 0));
                        } else {
                            // Add points
                            $input.val("" + Math.min(oldVal + dValue.minus, defaultVal));
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
                    $dLabel.append($("<i />").html(dValue.name));
                    $dRow.append($("<td />").append($dLabel));

                    // Add the row to the table
                    $dTable.append($dRow);
                });
            }

            // Add a row to use to add deductions
            var $dRow = $("<tr />");
            // Make an empty/disabled checkbox
            $dRow.append($("<td />").append($("<input />").attr({
                type: "checkbox",
                disabled: "disabled"
            })));
            // Make the link to do the magic
            var $a = $("<a />").text("Add another deduction...").attr("href", "#");
            $a.click(function (event) {
                event.preventDefault();
                var name = prompt("Deduction name (HTML allowed):");
                if (!name) return;
                var minus = Number(prompt("Points to deduct:", "0"));
                if (!isNaN(minus)) {
                    // Show "loading"
                    section("loading");
                    // Tell the server about this guy
                    post("add_deduction", {
                        path: currentPath,
                        name: name,
                        minus: minus
                    }, function () {
                        // We need to reload the grading structure
                        location.reload();
                    });
                }
            });
            $dRow.append($("<td />").attr("colspan", "2").append($a));
            // Add the "New Deduction" row to the deductions table
            $dTable.append($dRow);
            // Add the deductions table to the column
            $col.append($dTable);

            // Finally, we can set the textarea's tabindex
            $textarea.attr("tabindex", "" + (++tabindex));

            // Now, we can add the points row
            $row = $("<tr />");
            $row.append($col);
            $(table).append($row);
        }
    });
}
