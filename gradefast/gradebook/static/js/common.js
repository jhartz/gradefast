/**
 * Report an HTTP request error.
 * @param {boolean} completed - Whether the request actually completed.
 * @param {string} path - The path that the request was going to.
 * @param {string} status - The HTTP status, if any.
 * @param {string} [details] - Any details, such as the response body.
 * @param {Event} [event] - An error or event object to log.
 */
export function reportError(completed, path, status, details, event) {
    var pre;
    if (completed) {
        pre = `Invalid response from ${path} (status: ${status})`;
    } else {
        pre = `Request to ${path} was not successful (status: ${status})`;
    }
    console.log(pre, details, event);
    alert(pre + (details ? `:\n\n${details}` : `.`));
}

export function post(index, action, onsuccess) {
    var path = "_update";

    var fd = new FormData();
    fd.append("submission_id", index);
    fd.append("action", JSON.stringify(action));

    var xhr = new XMLHttpRequest();

    xhr.addEventListener("load", (event) => {
        // Parse the JSON data
        var jsonData;
        try {
            jsonData = JSON.parse(xhr.responseText);
        } catch (err) {
            reportError(true, path, xhr.statusText, xhr.responseText, event);
            return;
        }

        // Check the data's status
        if (jsonData && jsonData.status === "Aight") {
            // Woohoo, all good!
            console.log("DEBUG: POST response:", jsonData);
            onsuccess(jsonData);
        } else {
            // Bleh, not good :(
            reportError(true, path, xhr.statusText, JSON.stringify(jsonData, null, 2), event);
        }
    }, false);

    xhr.addEventListener("error", (event) => {
        reportError(false, path, xhr.statusText, xhr.responseText, event);
    }, false);

    xhr.open("POST", base + path, true);
    xhr.send(fd);
}
