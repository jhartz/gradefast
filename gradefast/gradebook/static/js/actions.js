import * as Immutable from "immutable";

import {post} from "./common";

// Local state; not propagated to server
const LOADING_SUBMISSION = "LOADING_SUBMISSION";
const INIT_SUBMISSION = "INIT_SUBMISSION";
const SET_LIST_VISIBILITY = "SET_LIST_VISIBILITY";
const SET_LIST = "SET_LIST";

const SET_GRADE_STRUCTURE = "SET_GRADE_STRUCTURE";

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
        const index = getState().get("submission_index");
        post(index, action, function (jsonData) {
            // Update locally with anything new from the server
            dispatch(actions.initSubmission(
                index,
                jsonData.name,
                jsonData.is_late,
                jsonData.overall_comments,
                jsonData.current_score,
                jsonData.max_score,
                jsonData.grades
            ));
        });
    }
}

export const actions = {
    goToSubmission(index) {
        return function (dispatch) {
            // Inform everyone that the request is starting
            dispatch(actions.loadingSubmission(index));

            // Request the submission data from the server
            post(index, {}, function (jsonData) {
                dispatch(actions.initSubmission(
                    index,
                    jsonData.name,
                    jsonData.is_late,
                    jsonData.overall_comments,
                    jsonData.current_score,
                    jsonData.max_score,
                    jsonData.grades
                ));
            });
        };
    },

    loadingSubmission(index) {
        return {
            type: LOADING_SUBMISSION,
            index
        };
    },

    initSubmission(index, name, is_late, overall_comments, current_score, max_score, grades) {
        return {
            type: INIT_SUBMISSION,
            index, name, is_late, overall_comments, current_score, max_score,
            grades: Immutable.fromJS(grades)
        }
    },

    setListVisibility(visible) {
        return {
            type: SET_LIST_VISIBILITY,
            visible
        };
    },

    setList(list) {
        return {
            type: SET_LIST,
            list: Immutable.fromJS(list)
        }
    },

    setGradeStructure(grade_structure) {
        return {
            type: SET_GRADE_STRUCTURE,
            grade_structure: Immutable.fromJS(grade_structure)
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

    setOnGrade(type, path, value, item) {
        // This is a catch-all for...
        // GRADE_SET_ENABLED, GRADE_SET_SCORE,
        // GRADE_SET_COMMENTS, GRADE_SET_HINT,
        // GRADE_ADD_HINT, GRADE_EDIT_HINT
        // The hint ones use "item"; the others don't
        return dispatchActionAndTellServer({type, path, value, item});
    }
};

/// TODO: DEBUG
window.actions = actions;
///TODO: DEBUG




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
    enabled: true

    // We could also have the following things...
    //hints: Immutable.List()
    //hints_set: Immutable.Map()
    //note: string

    // If it's a GradeScore...
    //score: number
    //points: number
    //comments: string

    // If it's a GradeSection...
    //children: Immutable.List()
});

function gradeReducer(state, action) {
    if (!state) state = initialGradeState;

    if (state.children) {
        state = state.set("children", cloneGradeChildren(state.children, action));
    }

    if (!action.path || action.path.length == 0) {
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
                state = state.set("hints_set", state.get("hints_set").set(action.item, action.value));
                break;
            case GRADE_ADD_HINT:
            case GRADE_EDIT_HINT:
                // We'll ignore this for now; the server will send the new
                // grade structure eventually
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
    "list_visible": false,
    "list": Immutable.List(),

    "submission_is_loading": false,
    "submission_index": null,
    "submission_name": "",
    "submission_is_late": false,
    "submission_overall_comments": "",
    "submission_current_score": 0,
    "submission_max_score": 0,
    "submission_grades": Immutable.List(),

    "grade_structure": Immutable.List()
});

export function app(state, action) {
    if (!state) state = initialState;

    let passOnAction = false;
    switch (action.type) {
        case LOADING_SUBMISSION:
            state = state.set("submission_is_loading", true);
            break;

        case INIT_SUBMISSION:
            state = state.merge({
                "list_visible": false,

                "submission_is_loading": false,
                "submission_index": action.index,
                "submission_name": action.name,
                "submission_is_late": action.is_late,
                "submission_overall_comments": action.overall_comments,
                "submission_current_score": action.current_score,
                "submission_max_score": action.max_score,
                "submission_grades": action.grades
            });
            break;
        case SET_LIST_VISIBILITY:
            state = state.set("list_visible", action.visible);
            break;
        case SET_LIST:
            state = state.set("list", action.list);
            break;

        case SET_LATE:
            state = state.set("is_late", action.is_late);
            break;
        case SET_OVERALL_COMMENTS:
            state = state.set("overall_comments", action.overall_comments);
            break;
        case SET_GRADE_STRUCTURE:
            state = state.set("grade_structure", action.grade_structure);
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
