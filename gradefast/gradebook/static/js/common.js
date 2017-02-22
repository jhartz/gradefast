/**
 * Report an HTTP request error.
 * @param {boolean} completed - Whether the request actually completed.
 * @param {string} path - The path that the request was going to.
 * @param {string} status - The HTTP status, if any.
 * @param {string} [details] - Any details, such as the response body.
 * @param {Event} [event] - An error or event object to log.
 */
export function reportError(completed, path, status, details, event) {
    let pre;
    if (completed) {
        pre = `Invalid response from ${path} (status: ${status})`;
    } else {
        pre = `Request to ${path} was not successful (status: ${status})`;
    }
    console.log(pre, details, event);
    alert(pre + (details ? `:\n\n${details}` : `.`));
}

const XHR_POST_ENDPOINT = CONFIG.BASE + "_update";

export function post(index, action, onsuccess) {
    console.log("DEBUG: POST request action:", JSON.parse(JSON.stringify(action)));

    const fd = new FormData();
    fd.append("submission_id", index);
    fd.append("action", JSON.stringify(action));

    const xhr = new XMLHttpRequest();

    xhr.addEventListener("load", (event) => {
        // Parse the JSON data
        let jsonData;
        try {
            jsonData = JSON.parse(xhr.responseText);
        } catch (err) {
            reportError(true, path, xhr.statusText, xhr.responseText, event);
            return;
        }
        console.log("DEBUG: POST response:", jsonData);

        // Check the data's status
        if (jsonData && jsonData.status === "Aight") {
            // Woohoo, all good!
            onsuccess(jsonData);
        } else {
            // Bleh, not good :(
            reportError(true, XHR_POST_ENDPOINT, xhr.statusText, JSON.stringify(jsonData, null, 2), event);
        }
    }, false);

    xhr.addEventListener("error", (event) => {
        reportError(false, XHR_POST_ENDPOINT, xhr.statusText, xhr.responseText, event);
    }, false);

    xhr.open("POST", XHR_POST_ENDPOINT, true);
    xhr.send(fd);
}

/**
 * Generate an element ID from a set of keys.
 */
export function id() {
    let str = "";
    for (let i = 0; i < arguments.length; i++) {
        str += "_" + arguments[i];
    }
    return str;
}
