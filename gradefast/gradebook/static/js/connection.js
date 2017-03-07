import {actions} from "./actions";
import {store} from "./store";
import {parseJson, post, reportResponseError} from "./utils";

let eventSource = null;
let client_seq = 0;

export function sendUpdate(submission_id, action = {}) {
    post(CONFIG.BASE + "_update", {
        submission_id: submission_id,
        client_id: CONFIG.CLIENT_ID,
        client_key: CONFIG.CLIENT_KEY,
        client_seq: ++client_seq,
        action: action
    });
}

const updateTypeHandlers = {
    UPDATE_LIST(data) {
        // Update our list of submissions
        store.dispatch(actions.setList(data.list));
    },

    SUBMISSION_START(data) {
        // Tell the forces at large to go to this submission
        store.dispatch(actions.goToSubmission(data.submission_id));
    },

    SUBMISSION_UPDATE(data) {
        // Should we ignore this update?
        // Only if it came from us, and is already outdated
        if (data.originating_client_id === CONFIG.CLIENT_ID) {
            if (data.originating_client_seq < client_seq) {
                // This update is outdated
                // TODO: This is going to log literally all the time...
                console.log("Got outdated update");
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
            data.name,
            data.is_late,
            data.overall_comments,
            data.current_score,
            data.max_score,
            data.grades
        ))
    },

    END_OF_SUBMISSIONS(data) {
        // TODO: Show the user a summary or some shit
    }
};

export function initEventSource() {
    const path = CONFIG.BASE + "_events";
    eventSource = new EventSource(path);

    eventSource.onerror = (event) => {
        console.error("EventSource ERROR:", event);
    };

    eventSource.addEventListener("init", (event) => {
        store.dispatch(actions.setList(CONFIG.INITIAL_LIST));
        if (typeof CONFIG.INITIAL_SUBMISSION_ID === "number") {
            store.dispatch(actions.goToSubmission(CONFIG.INITIAL_SUBMISSION_ID));
        } else {
            store.dispatch(actions.waitingForUserToGetTheirAssMoving());
        }
    });

    eventSource.addEventListener("update", (event) => {
        let jsonData = parseJson(event.data, path, "event: update", event);
        if (!jsonData) return;

        if (jsonData.update_type && updateTypeHandlers.hasOwnProperty(jsonData.update_type)) {
            updateTypeHandlers[jsonData.update_type](jsonData.update_data);
        } else {
            reportResponseError(path, "event: update", "Invalid update_type: " + jsonData.update_type, data);
        }
    });
}

export function closeEventSource() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}
