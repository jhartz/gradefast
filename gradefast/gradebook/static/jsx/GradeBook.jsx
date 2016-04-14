import * as s from './store'
import Submission from './Submission.jsx'
import HeaderContent from './HeaderContent.jsx'
import SubmissionList from './SubmissionList.jsx'

const GradeBook = React.createClass({
    showList() {
        store.dispatch(s.actions.setListVisibility(true));
    },

    goToSubmission(index) {
        store.dispatch(s.actions.goToSubmission(index));
    },

    render() {
        var header, section;
        if (this.props.submissionIndex !== null && !this.props.showList) {
            // Show the current submission (includes header)
            section = <Submission showListHandler={this.showList} />;
        } else {
            // We don't get an included header, so make one here
            header = (
                <header>
                    <HeaderContent showScore={false} />
                    <h1>GradeFast</h1>
                </header>
            );
            // Show the submission list, or a message if we don't have one yet
            if (this.props.list.size) {
                section = <SubmissionList submissions={this.props.list}
                                          goToSubmissionHandler={this.goToSubmission} />;
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
    }
});

function mapStateToProps(state) {
    return {
        submissionIndex: state.get("submission_index"),
        showList: state.get("list_visible"),
        list: state.get("list")
    };
}

export default ReactRedux.connect(mapStateToProps)(GradeBook);
