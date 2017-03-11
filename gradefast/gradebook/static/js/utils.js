/**
 * Report an error in an HTTP request (i.e. no response was received).
 * @param {string} path - The path that the request was going to.
 * @param {string} status - The HTTP status, if any.
 * @param {string} [details] - Details about what went wrong, if applicable. This is included in
 *      the alert message to the user.
 * @param [objects] - An errors or objects to log, if applicable.
 */
export function reportRequestError(path, status, details, ...objects) {
    reportError(`Request to ${path} was not successful (status: ${status})`, details, objects);
}

/**
 * Report an error from an HTTP response (i.e. an error received from the server).
 * @param {string} path - The path that the request was going to.
 * @param {string} status - The HTTP status.
 * @param {string} [details] - Details about what went wrong, such as the response body. This is
 *      included in the alert message to the user.
 * @param [objects] - Any errors or objects to log.
 */
export function reportResponseError(path, status, details, ...objects) {
    reportError(`Error response from ${path} (HTTP status: ${status})`, details, objects);
}

function reportError(message, details, objects) {
    console.log.apply(console, [message, details, ...objects]);
    alert(message + (details ? `:\n\n${details}` : `.`));
}

/**
 * Parse a string as JSON data, reporting an error if it cannot be parsed.
 * @param {string} str - The string containing the JSON data.
 * @param {string} errorPath - The path to use for an error message.
 * @param {string} errorStatus - The status to use for an error message.
 * @param [errorObjects] - Any objects to log with an error message.
 */
export function parseJson(str, errorPath, errorStatus, ...errorObjects) {
    let jsonData;
    try {
        jsonData = JSON.parse(str);
    } catch (err) {
        reportResponseError.apply(undefined, [errorPath, errorStatus, str, err, ...errorObjects]);
    }
    return jsonData;
}

/**
 * Send a POST request to the server.
 * @param {string} path - The path to send the request to.
 * @param {Object} data - An object representing the POST data. If any value is not a string, it is
 *      run through JSON.stringify.
 */
export function post(path, data) {
    const fd = new FormData();
    Object.keys(data).forEach((key) => {
        fd.append(key, typeof data[key] === "string" ? data[key] : JSON.stringify(data[key]));
    });

    const xhr = new XMLHttpRequest();
    xhr.addEventListener("load", (event) => {
        let jsonData = parseJson(xhr.responseText, path, xhr.statusText, event);
        if (jsonData && jsonData.status === "Aight") {
            // All good!
        } else {
            reportResponseError(path, xhr.statusText, JSON.stringify(jsonData, null, 2), event, jsonData);
        }
    }, false);

    xhr.addEventListener("error", (event) => {
        reportRequestError(path, xhr.statusText, xhr.responseText, event);
    }, false);

    xhr.open("POST", path, true);
    xhr.send(fd);
}

/**
 * Generate an element ID from a set of keys.
 */
export function id(...keys) {
    return "id_" + keys.join("_");
}
