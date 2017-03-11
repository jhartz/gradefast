import * as Immutable from "immutable";

import {sendUpdate} from "./connection";

// Local state; not propagated to server
const WAITING_FOR_USER_TO_GET_THEIR_ASS_MOVING = "WAIT_FOR_USER_TO_GET_THEIR_ASS_MOVING";
const SET_DATA_KEY = "SET_DATA_KEY";
const LOADING_SUBMISSION = "LOADING_SUBMISSION";
const INIT_SUBMISSION = "INIT_SUBMISSION";
const TOGGLE_LIST_VISIBILITY = "TOGGLE_LIST_VISIBILITY";
const SET_LIST = "SET_LIST";

// These string values are also recognized by the GradeBook server
// (see GradeBook::_parse_action in gradebook.py)

const SET_LATE = "SET_LATE";
const SET_OVERALL_COMMENTS = "SET_OVERALL_COMMENTS";

const GRADE_SET_ENABLED = "SET_ENABLED";
const GRADE_SET_SCORE = "SET_SCORE";
const GRADE_SET_COMMENTS = "SET_COMMENTS";
const GRADE_SET_HINT = "SET_HINT";
// These 2 modify the actual grade structure (server-side)
const GRADE_ADD_HINT = "ADD_HINT";
const GRADE_EDIT_HINT = "EDIT_HINT";

const GRADE_NOOP = "NOOP";

function dispatchActionAndTellServer(action) {
    return (dispatch, getState) => {
        // Propagate the action locally
        dispatch(action);

        // Send the action to the server, too
        const submission_id = getState().get("submission_id");
        sendUpdate(submission_id, action);
    }
}

export const actions = {
    waitingForUserToGetTheirAssMoving() {
        return {
            type: WAITING_FOR_USER_TO_GET_THEIR_ASS_MOVING
        };
    },

    setDataKey(data_key) {
        return {
            type: SET_DATA_KEY,
            data_key
        }
    },

    goToSubmission(submission_id) {
        return function (dispatch) {
            // Inform everyone that the request is starting
            // (and that this is the new submission ID)
            dispatch(actions.loadingSubmission(submission_id));

            // Request the submission data from the server
            sendUpdate(submission_id, {});
        };
    },

    loadingSubmission(submission_id) {
        return {
            type: LOADING_SUBMISSION,
            submission_id
        };
    },

    initSubmission(submission_id, name, is_late, overall_comments, overall_comments_html,
                   current_score, max_score, grades) {
        return {
            type: INIT_SUBMISSION,

            submission_id, name, is_late, overall_comments, overall_comments_html,
            current_score, max_score, grades: Immutable.fromJS(grades)
        }
    },

    toggleListVisibility() {
        return {
            type: TOGGLE_LIST_VISIBILITY
        };
    },

    setList(list) {
        return {
            type: SET_LIST,
            list: Immutable.fromJS(list)
        }
    },

    setLate(is_late) {
        return dispatchActionAndTellServer({
            type: SET_LATE,
            is_late
        });
    },

    setOverallComments(overall_comments) {
        return dispatchActionAndTellServer({
            type: SET_OVERALL_COMMENTS,
            overall_comments
        });
    },

    grade_setEnabled(path, value) {
        return dispatchActionAndTellServer({
            type: GRADE_SET_ENABLED,
            path, value
        });
    },

    grade_setScore(path, value) {
        return dispatchActionAndTellServer({
            type: GRADE_SET_SCORE,
            path, value
        });
    },

    grade_setComments(path, value) {
        return dispatchActionAndTellServer({
            type: GRADE_SET_COMMENTS,
            path, value
        });
    },

    grade_setHint(path, index, value) {
        return dispatchActionAndTellServer({
            type: GRADE_SET_HINT,
            path, index, value
        });
    },

    grade_addHint(path, content) {
        return dispatchActionAndTellServer({
            type: GRADE_ADD_HINT,
            path, content
        });
    },

    grade_editHint(path, index, content) {
        return dispatchActionAndTellServer({
            type: GRADE_EDIT_HINT,
            path, index, content
        });
    }
};


function cloneGradeChildren(children, action) {
    const path = action.path || Immutable.List(),
          current = path.get(0, null),
          restOfPath = path.slice(1);

    return children.map((childState, index) => {
        return gradeReducer(childState, Object.assign({}, action, {
            path: restOfPath,
            type: current === index ? action.type : GRADE_NOOP
        }));
    });
}

const initialGradeState = Immutable.Map({
    name: null,
    name_html: "",
    enabled: true

    // We could also have the following things...
    //hints: Immutable.List()
    //hints_set: Immutable.Map()
    //note: string
    //note_html: string

    // If it's a GradeScore...
    //score: number
    //points: number
    //comments: string
    //comments_html: string

    // If it's a GradeSection...
    //children: Immutable.List()
});

function gradeReducer(state, action) {
    if (!state) state = initialGradeState;

    if (state.has("children")) {
        state = state.set("children", cloneGradeChildren(state.get("children"), action));
    }

    if (action.path.size == 0) {
        // We've reached the place where we apply this operation
        switch (action.type) {
            case GRADE_SET_ENABLED:
                state = state.set("enabled", action.value);
                break;
            case GRADE_SET_SCORE:
                state = state.set("score", action.value);
                break;
            case GRADE_SET_COMMENTS:
                state = state.set("comments", action.value);
                break;
            case GRADE_SET_HINT:
                state = state.set("hints_set", state.get("hints_set").set("" + action.index, action.value));
                break;
            case GRADE_ADD_HINT:
                state = state.set("hints", state.get("hints").push(Immutable.fromJS(action.content)));
                break;
            case GRADE_EDIT_HINT:
                state = state.set("hints", state.get("hints").set(action.index, Immutable.fromJS(action.content)));
                break;
            case GRADE_NOOP:
                // No-op; we're only here for the cloning
                break;
            default:
                // No idea how we got here
                console.warn("Unknown grade action type:", action.type);
        }
    }
    return state;
}

const initialState = Immutable.Map({
    "loading": true,
    "data_key": null,

    "list_visible": false,
    "list": Immutable.List(),

    "submission_id": null,
    "submission_name": "",
    "submission_is_late": false,
    "submission_overall_comments": "",
    "submission_overall_comments_html": "",
    "submission_current_score": 0,
    "submission_max_score": 0,
    "submission_grades": Immutable.List()
});

export function app(state, action) {
    if (!state) state = initialState;

    let passOnAction = false;
    switch (action.type) {
        case WAITING_FOR_USER_TO_GET_THEIR_ASS_MOVING:
            state = state.merge({
                "loading": false
            });
            break;

        case SET_DATA_KEY:
            state = state.merge({
                "data_key": action.data_key
            });
            break;

        case LOADING_SUBMISSION:
            state = state.merge({
                "loading": true,
                "submission_id": action.submission_id
            });
            break;

        case INIT_SUBMISSION:
            if (action.submission_id === state.get("submission_id")) {
                state = state.merge({
                    "loading": false,
                    "list_visible": false,

                    "submission_name": action.name,
                    "submission_is_late": action.is_late,
                    "submission_overall_comments": action.overall_comments,
                    "submission_overall_comments_html": action.overall_comments_html,
                    "submission_current_score": action.current_score,
                    "submission_max_score": action.max_score,
                    "submission_grades": action.grades
                });
            }
            break;
        case TOGGLE_LIST_VISIBILITY:
            state = state.set("list_visible", !state.get("list_visible"));
            break;
        case SET_LIST:
            state = state.set("list", action.list);
            break;

        case SET_LATE:
            state = state.set("submission_is_late", action.is_late);
            break;
        case SET_OVERALL_COMMENTS:
            state = state.set("submission_overall_comments", action.overall_comments);
            break;

        default:
            // Pass on action to gradeReducer
            passOnAction = true;
    }

    return state.set("submission_grades", cloneGradeChildren(state.get("submission_grades"),
        passOnAction ? action : {
            type: GRADE_NOOP,
            path: Immutable.List()
        }
    ));
}
