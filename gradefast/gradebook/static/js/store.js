import * as Redux from "redux";
import thunk from "redux-thunk";

import {app} from "./actions";

export let store;

export function initStore() {
    store = Redux.createStore(app, Redux.applyMiddleware(thunk));
    window.GLOBAL_DEBUG_STORE = store;
    return store;
}
