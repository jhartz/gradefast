import * as s from './store'
import HeaderContent from './HeaderContent.jsx'
import GradeSection from './GradeSection.jsx'
import GradeItem from './GradeItem.jsx'

const Submission = React.createClass({
    handleOverallCommentsChange(event) {
        store.dispatch(s.actions.setOverallComments(event.target.value));
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
        store.dispatch(s.actions.setLate(isLate));
    },

    render() {
        return (
            <div>
                <header>
                    <HeaderContent showScore={true}
                                   currentScore={this.props.currentScore}
                                   maxScore={this.props.maxScore}
                                   isLate={this.props.isLate}
                                   setLateHandler={this.setLate} />
                    <h1><a href="#" onClick={(event) => {
                        event.preventDefault();
                        this.props.showListHandler();
                    }}>{this.props.index}: {this.props.name || "GradeFast"}</a></h1>
                </header>
                <section>
                    {this.props.grades.map(function (grade, index) {
                        // We need to have a "key" for each thing here...
                        // https://facebook.github.io/react/docs/lists-and-keys.html#keys
                        return ((grade.has("children") && grade.get("children")) ?
                            (<GradeSection key={index} grade={grade} />) :
                            (<GradeItem key={index} grade={grade} />));
                    })}
                    <table className="bigtable">
                        <tbody>

                        </tbody>
                    </table>
                    <h3>Submission Info</h3>
                    <div>
                        <p>{this.props.name}, is late? {JSON.stringify(this.props.isLate)}, etc.</p>
                        <p>Overall Comments:</p>
                        <pre>{this.props.overallComments}</pre>
                        <p>Grades:</p>
                        <pre>{JSON.stringify(this.props.grades, null, 4)}</pre>
                        <hr />
                        <p>Grade Structure:</p>
                        <pre>{JSON.stringify(this.props.gradeStructure, null, 4)}</pre>
                    </div>
                </section>
                <footer>
                    <textarea ref="overallComments" style={{height: "100%"}}
                              placeholder="Overall Comments (Markdown-parsed)"
                              value={this.props.overallComments}
                              onChange={this.handleOverallCommentsChange} />
                </footer>
            </div>
        );
    },

    componentDidMount() {
        this.resizeOverallComments();
    }
});

function mapStateToProps(state) {
    return {
        index: state.get("submission_index"),
        name: state.get("submission_name"),
        isLate: state.get("submission_is_late"),
        overallComments: state.get("submission_overall_comments"),
        currentScore: state.get("submission_current_score"),
        maxScore: state.get("submission_max_score"),
        grades: state.get("submission_grades"),
        gradeStructure: state.get("grade_structure")
    };
}

export default ReactRedux.connect(mapStateToProps)(Submission);
