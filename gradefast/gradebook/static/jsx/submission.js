var Submission = React.createClass({
    getInitialState() {
        // Yeah, yeah, we shouldn't do this, but.....
        return {
            overallComments: this.props.submission.overallComments,
            isLate: this.props.submission.isLate
        };
    },

    postUpdate(path, data) {
        // Then, return value should also have latest calculated values (scores)
        // Return value should NOT have big user-entered values (comments)
        var fd = new FormData();
        Object.keys(data).forEach((key) => {
            fd.append(key, data[key]);
        });

        var xhr = new XMLHttpRequest();

        xhr.addEventListener("load", (event) => {
            // Parse the JSON data
            var jsonData;
            try {
                jsonData = JSON.parse(xhr.responseText);
            } catch (err) {
                reportError(true, path, xhr.statusText, xhr.responseText, event);
                return;
            }

            // Check the data's status
            if (jsonData && jsonData.status === "Aight") {
                // Woohoo, all good! Update the things
            } else {
                // Bleh, not good :(
                reportError(true, path, xhr.statusText, JSON.stringify(jsonData, null, 2), event);
            }
        }, false);

        xhr.addEventListener("error", (event) => {
            reportError(false, path, xhr.statusText, xhr.responseText, event);
        }, false);

        xhr.open("GET", base + "_/" + path, true);
        xhr.send(fd);
    },

    handleOverallCommentsChange(event) {
        this.setState({overallComments: event.target.value}, () => {
            post("overall_comments", {
                value: this.state.overallComments
            });
        });
        this.resizeOverallComments();
    },

    resizeOverallComments() {
        var elem = this.refs.overallComments;
        // Reset the height
        elem.style.height = "auto";
        // Calculate new height (min 40px, max 140px)
        var newHeight = Math.max(Math.min(elem.scrollHeight + 3, 140), 40);
        elem.style.height = newHeight + "px";
        //elem.parentNode.style.height = (newHeight + 27) + "px";
    },

    setLate(isLate) {
        this.setState({isLate}, () => {
            post("late", {
                is_late: "" + this.state.isLate
            });
        });
    },

    render() {
        var s = this.props.submission;

        return (
            <div>
                <header>
                    <HeaderContent showScore={true}
                                   currentScore={s.currentScore}
                                   maxScore={s.maxScore}
                                   isLate={this.state.isLate}
                                   setLate={this.setLate} />
                    <h1><a href="#" onClick={(event) => {
                        event.preventDefault();
                        this.props.onShowList();
                    }}>{s.id}: {s.name || "GradeFast"}</a></h1>
                </header>
                <section>
                    <h3>{JSON.stringify(s, null, 4)}</h3>
                    <footer>
                        <textarea ref="overall_comments" style="height: 100%;"
                                  placeholder="Overall Comments (Markdown-parsed)"
                                  value={this.state.overallComments}
                                  onChange={this.handleOverallCommentsChange} />
                    </footer>
                </section>
            </div>
        );
    },

    componentDidMount() {
        this.resizeOverallComments();
    }
});