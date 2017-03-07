import * as React from "react";
import * as ReactDOM from "react-dom";
import * as ReactRedux from "react-redux";

import {initEventSource, closeEventSource} from "./connection";
import {store, initStore} from "./store";

import GradeBook from "./components/GradeBook";

window.addEventListener("load", (event) => {
    initStore();
    ReactDOM.render(
            <ReactRedux.Provider store={store}>
                <GradeBook />
            </ReactRedux.Provider>,
        document.getElementById("root"));

    // Once the EventSource connection is created, the server will respond with an initial "init"
    // message, and that's when we'll kick things off for real.
    // (Right now, we're just in a "Loading" state.)
    initEventSource();
}, false);

window.addEventListener("unload", (event) => {
    closeEventSource();
}, false);
