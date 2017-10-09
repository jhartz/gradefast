import {actions} from "./actions";
import {store} from "./store";
import {parseJson, post, reportResponseError} from "./utils";

let eventSource = null;
let client_seq = 0;
let update_key = null;

export function sendAuthRequest() {
    let device = navigator.userAgent;
    if (device.startsWith("Mozilla/")) {
        device = device.substring(device.indexOf(" ") + 1);
    }
    post(CONFIG.BASE + "_auth", {
        client_id: CONFIG.CLIENT_ID,
        device
    });
}

function authKeysReceived(new_data_key, new_update_key, initial_submission_list, initial_submission_id, is_done) {
    console.log("Received auth keys");
    update_key = new_update_key;
    store.dispatch(actions.setDataKey(new_data_key));

    // Now that we are authenticated, move on from the "Loading" screen
    store.dispatch(actions.setSubmissions(initial_submission_list));
    if (is_done) {
        // Show the submission list and statistics
        store.dispatch(actions.showSubmissions());
    } else if (typeof initial_submission_id === "number") {
        store.dispatch(actions.goToSubmission(initial_submission_id));
    } else {
        store.dispatch(actions.waitingForUserToGetTheirAssMoving());
    }
}

export function sendUpdate(submission_id, action = {}) {
    post(CONFIG.BASE + "_update", {
        submission_id: submission_id,
        client_id: CONFIG.CLIENT_ID,
        update_key: update_key,
        client_seq: ++client_seq,
        action: action
    });
}

export function sendRefreshStatsRequest() {
    post(CONFIG.BASE + "_refresh_stats", {
        client_id: CONFIG.CLIENT_ID
    });
}

const updateTypeHandlers = {
    NEW_SUBMISSIONS(data) {
        // Update our list of submissions
        store.dispatch(actions.setSubmissions(data.submissions));
    },

    SUBMISSION_STARTED(data) {
        // Tell the forces at large to go to this submission
        store.dispatch(actions.goToSubmission(data.submission_id));
    },

    SUBMISSION_UPDATED(data) {
        // Should we ignore this update?
        // Only if it came from us, and is already outdated
        if (data.originating_client_id === CONFIG.CLIENT_ID) {
            if (data.originating_client_seq < client_seq) {
                // This update is outdated
                return;
            } else if (data.originating_client_seq > client_seq) {
                // Umm, somehow someone has been sending events as us...
                // (or it's our future selves -- BUT WHERE ARE ALL THE TIME TRAVELLERS)
                reportResponseError(
                    "SubmissionUpdate",
                    "BAD BAD BAD",
                    "originating_client_seq[" + data.originating_client_seq + "] > client_seq[" + client_seq + "]");
                return;
            }
        }

        store.dispatch(actions.initSubmission(
            data.submission_id,
            data.is_late,
            data.overall_comments,
            data.overall_comments_html,
            data.points_earned,
            data.points_possible,
            data.grades
        ));
    },

    END_OF_SUBMISSIONS(data) {
        // Show the submission list and statistics
        store.dispatch(actions.showSubmissions());
    },

    UPDATED_STATS(data) {
        store.dispatch(actions.setStats(data.grading_stats, data.timing_stats));
    }
};

export function initEventSource(onReady) {
    const params = {
        //client_id: CONFIG.CLIENT_ID,
        events_key: CONFIG.EVENTS_KEY
    };
    const path = CONFIG.BASE + "_events?" +
        Object.keys(params).map((key) => encodeURIComponent(key) + "=" + params[key]).join("&");

    console.log("EventSource connecting to", path);
    eventSource = new EventSource(path);

    eventSource.onerror = (event) => {
        console.error("EventSource ERROR:", event);
    };

    eventSource.onopen = (event) => {
        console.log("EventSource ready");
        onReady();
    };

    eventSource.addEventListener("auth", (event) => {
        let jsonData = parseJson(event.data, path, "event: auth", event);
        if (!jsonData) return;

        if (jsonData.data_key && jsonData.update_key) {
            //console.log("AUTH EVENT:", jsonData);
            authKeysReceived(
                jsonData.data_key,
                jsonData.update_key,
                jsonData.initial_submission_list,
                jsonData.initial_submission_id,
                jsonData.is_done);
        } else {
            reportResponseError(path, "event: auth", "Missing keys", jsonData)
        }
    });

    eventSource.addEventListener("update", (event) => {
        let jsonData = parseJson(event.data, path, "event: update", event);
        if (!jsonData) return;

        if (jsonData.update_type && updateTypeHandlers.hasOwnProperty(jsonData.update_type)) {
            //console.log("UPDATE EVENT:", jsonData);
            updateTypeHandlers[jsonData.update_type](jsonData.update_data);
        } else {
            reportResponseError(path, "event: update", "Invalid update_type: " + jsonData.update_type, jsonData);
        }
    });
}

export function closeEventSource() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}
