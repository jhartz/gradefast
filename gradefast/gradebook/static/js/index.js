import * as React from "react";
import * as ReactDOM from "react-dom";
import * as ReactRedux from "react-redux";

import {initEventSource, closeEventSource, sendAuthRequest} from "./connection";
import {store, initStore} from "./store";

import GradeBook from "./components/GradeBook";

window.addEventListener("load", (event) => {
    initStore();
    ReactDOM.render(
            <ReactRedux.Provider store={store}>
                <GradeBook />
            </ReactRedux.Provider>,
        document.getElementById("root"));

    // This kicks off the whole process. Once the event stream is established, we'll send a POST
    // request to the _auth endpoint with our client_id, asking for auth keys. Then, if the server
    // is in the mood, it'll send an "auth" message to the event source with our data_key and
    // update_key.
    initEventSource(() => {
        sendAuthRequest();
    });
}, false);

window.addEventListener("unload", (event) => {
    closeEventSource();
}, false);
