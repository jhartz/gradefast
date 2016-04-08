// This should only ever be processed by the middleware (i.e. the remote server)
const GO_TO_SUBMISSION = "GO_TO_SUBMISSION";

// Local state; not propagated to server
const INIT_SUBMISSION = "INIT_SUBMISSION";
const SET_LIST_VISIBILITY = "SET_LIST_VISIBILITY";
const SET_LIST = "SET_LIST";

// These string values are also recognized by the GradeBook server
// (see GradeBook::_parse_action in gradebook.py)

const SET_LATE = "SET_LATE";
const SET_OVERALL_COMMENTS = "SET_OVERALL_COMMENTS";
const SET_GRADE_STRUCTURE = "SET_GRADE_STRUCTURE";

const GRADE_SET_ENABLED = "SET_ENABLED";
const GRADE_SET_POINTS = "SET_POINTS";
const GRADE_SET_COMMENTS = "SET_COMMENTS";
const GRADE_SET_HINT = "SET_HINT";

const GRADE_NOOP = "NOOP";

export const actions = {
    goToSubmission(index) {
        return {
            type: GO_TO_SUBMISSION,
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

    setLate(is_late) {
        return {
            type: SET_LATE,
            is_late
        };
    },

    setOverallComments(overall_comments) {
        return {
            type: SET_OVERALL_COMMENTS,
            overall_comments
        };
    },

    setGradeStructure(grade_structure) {
        return {
            type: SET_GRADE_STRUCTURE,
            grade_structure: Immutable.fromJS(grade_structure)
        };
    },

    setOnGrade(type, path, value, item) {
        // This is a catch-all for
        // GRADE_SET_ENABLED, GRADE_SET_POINTS,
        // GRADE_SET_COMMENTS, and GRADE_SET_HINT
        return {type, path, value, item};
    }
};

/// TODO: DEBUG
window.actions = actions;
///TODO: DEBUG




function cloneGradeChildren(children, action) {
    var path = action.path || Immutable.List(),
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
    enabled: true,
    hints_set: Immutable.Map(),
    children: Immutable.List()
});

function gradeReducer(state, action) {
    if (!state) state = initialGradeState;

    state = state.set("children", cloneGradeChildren(state.children, action));

    if (!action.path || action.path.length == 0) {
        // We've reached the place where we apply this operation
        switch (action.type) {
            case GRADE_SET_ENABLED:
                state = state.set("enabled", action.value);
                break;
            case GRADE_SET_POINTS:
                state = state.set("points", action.value);
                break;
            case GRADE_SET_COMMENTS:
                state = state.set("comments", action.value);
                break;
            case GRADE_SET_HINT:
                state = state.set("hints_set", state.get("hints_set").set(action.item, action.value));
                break;
            case GRADE_NOOP:
                // No-op; we're only here for the cloning
                break;
            default:
                // No idea how we got here
        }
    }
    return state;
}

const initialState = Immutable.Map({
    "list_visible": false,
    "list": Immutable.List(),

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

    var passOnAction = false;
    switch (action.type) {
        case GO_TO_SUBMISSION:
            // We shouldn't ever reach this; it should be caught by middleware
            console.log("WARNING: Found GO_TO_SUBMISSION");
            return state;

        case INIT_SUBMISSION:
            state = state.merge({
                "list_visible": false,

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
