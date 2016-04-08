import {reportError} from './common'
import GradeBook from './GradeBook.jsx'
import * as s from './store'

var Container = React.createClass({
    render() {
        return (
            <GradeBook />
        );
    },

    closeEventSource() {
        if (this.state.evtSource) {
            this.state.evtSource.close();
            this.setState({evtSource: null});
        }
    },

    componentDidMount() {
        var evtSource = new EventSource(base + "events.stream");
        this.setState({evtSource});

        evtSource.addEventListener("update", (event) => {
            // Parse the JSON data
            var jsonData;
            try {
                jsonData = JSON.parse(event.data);
            } catch (err) {
                reportError(true, "event.stream", "update", event.data, event);
                return;
            }

            if (!jsonData) return;
            console.log("EVENT (update):", jsonData);

            if (jsonData.list) {
                // Update our list of submissions
                store.dispatch(s.actions.setList(jsonData.list));
            }
            if (jsonData.grade_structure) {
                // Update our grade structure with a new one
                store.dispatch(s.actions.setGradeStructure(jsonData.grade_structure));
            }
            if (jsonData.submission_index) {
                // Tell the forces at large to go to this submission
                store.dispatch(s.actions.goToSubmission(jsonData.submission_index));
            }
        });

        evtSource.addEventListener("done", (event) => {
            // All done! Close the event source
            console.log("EVENT: Closing event source");
            this.closeEventSource();
        });
    },

    componentWillUnmount() {
        this.closeEventSource();
    }
});

window.addEventListener("load", (event) => {
    store = Redux.createStore(s.app);
    store.dispatch(s.actions.setList(initialList));
    store.dispatch(s.actions.setGradeStructure(initialGradeStructure));
    if (initialSubmissionIndex) {
        store.dispatch(s.actions.goToSubmission(initialSubmissionIndex));
    }
    ReactDOM.render(
            <ReactRedux.Provider store={store}>
                <Container />
            </ReactRedux.Provider>,
        document.getElementById("container"));
}, false);
