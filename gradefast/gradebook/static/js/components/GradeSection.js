import * as React from "react";

const GradeSection = React.createClass({
    render() {
        return (<div><h3>GradeSection</h3><pre>{JSON.stringify(this.props.grade)}</pre></div>);
    }
});

export default GradeSection;
