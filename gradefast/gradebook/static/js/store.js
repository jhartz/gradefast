import * as Redux from "redux";
import thunk from "redux-thunk";

import {actions, app} from "./actions";

export let store;

export function initStore() {
    store = Redux.createStore(app, Redux.applyMiddleware(thunk));
    store.dispatch(actions.setList(CONFIG.INITIAL_LIST));
    store.dispatch(actions.setGradeStructure(CONFIG.INITIAL_GRADE_STRUCTURE));
    if (typeof CONFIG.INITIAL_SUBMISSION_INDEX == "number") {
        store.dispatch(actions.goToSubmission(CONFIG.INITIAL_SUBMISSION_INDEX));
    }
    return store;
}
