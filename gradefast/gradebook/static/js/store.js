import * as Redux from "redux";
import thunk from "redux-thunk";

import {actions, app} from "./actions";

export let store;

export function initStore() {
    store = Redux.createStore(app, Redux.applyMiddleware(thunk));
    store.dispatch(actions.setList(initialList));
    store.dispatch(actions.setGradeStructure(initialGradeStructure));
    if (initialSubmissionIndex) {
        store.dispatch(actions.goToSubmission(initialSubmissionIndex));
    }
    return store;
}
