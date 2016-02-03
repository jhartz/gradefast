var GradeBook = React.createClass({
    getInitialState() {
        return {
            showList: false,
            currentSubmission: null,
            submissions: [
                /*
                {
                    name: "",
                }
                */
            ],
            evtSource: null
        };
    },

    onShowList() {
        this.setState({
            showList: true,
            currentSubmission: null
        });
    },

    goToSubmission(id) {
        // TODO: Get a specific submission, then call onSubmission
    },

    onSubmission(submission) {
        this.setState({
            showList: false,
            currentSubmission: submission
        });
    },

    render() {
        var header, section;
        if (this.state.currentSubmission !== null && !this.state.showList) {
            // Show the current submission (includes header)
            section = <Submission submission={this.state.currentSubmission}
                                  onShowList={this.onShowList} />;
        } else {
            // We don't get an included header, so make one here
            header = <header>
                <HeaderContent showScore={false} />
                <h1>GradeFast</h1>
            </header>;
            // Show the submission list, or a message if we don't have one yet
            if (this.state.submissions.length) {
                section = <SubmissionList submissions={this.state.submissions}
                                          goToSubmission={this.goToSubmission} />;
            } else {
                section = <section><h2>Start a submission, dammit!</h2></section>;
            }
        }
        return (
            <div>
                {header}
                {section}
            </div>
        );
    },

    closeEventStream() {
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

            if (jsonData.submissions) {
                // Update our list of submissions
                this.setState({
                    submissions: jsonData.submissions
                });
            }
            if (typeof jsonData.currentSubmissionID == "number") {
                // Tell the forces at large to start this submission
                this.goToSubmission(jsonData.currentSubmissionID);
            }
        });

        evtSource.addEventListener("done", (event) => {
            // All done! Close the event stream
            this.closeEventStream();

            // Parse the JSON data
            var jsonData;
            try {
                jsonData = JSON.parse(event.data);
            } catch (err) {}

            if (jsonData) {
                this.setState({

                });
            }
        });
    },

    componentWillUnmount() {
        this.closeEventStream();
    }
});

window.addEventListener("load", (event) => {
    ReactDOM.render(
        <GradeBook />,
        document.getElementById("container")
    );
}, false);
