import {actions} from "./actions";
import {store} from "./store";

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

export function post(index, action) {
    //console.log("DEBUG: POST request action:", JSON.parse(JSON.stringify(action)));

    const fd = new FormData();
    fd.append("submission_id", index);
    fd.append("client_id", "" + CONFIG.CLIENT_ID);
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
        //console.log("DEBUG: POST response:", jsonData);

        // Check the data's status
        if (jsonData && jsonData.status === "Aight") {
            // Woohoo, all good!
            // TODO: This should be handled by the server in a server-sent event
            if (jsonData.submission_update) {
                store.dispatch(actions.initSubmission(
                    jsonData.originating_client_id,
                    jsonData.submission_update.index,
                    jsonData.submission_update.name,
                    jsonData.submission_update.is_late,
                    jsonData.submission_update.overall_comments,
                    jsonData.submission_update.current_score,
                    jsonData.submission_update.max_score,
                    jsonData.submission_update.grades
                ))
            }
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
    let str = "id";
    for (let i = 0; i < arguments.length; i++) {
        str += "_" + arguments[i];
    }
    return str;
}
