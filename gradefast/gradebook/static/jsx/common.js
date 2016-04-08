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

function post(path, data, onsuccess) {
    var fd = new FormData();
    if (data) {
        Object.keys(data).forEach((key) => {
            fd.append(key, data[key]);
        });
    }

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
            // Woohoo, all good! Update the things
            alert("TODO");
        } else {
            // Bleh, not good :(
            reportError(true, path, xhr.statusText, JSON.stringify(jsonData, null, 2), event);
        }
    }, false);

    xhr.addEventListener("error", (event) => {
        reportError(false, path, xhr.statusText, xhr.responseText, event);
    }, false);

    xhr.open("GET", base + "_/" + path, true);
    xhr.send(fd);
}
