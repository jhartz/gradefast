import * as React from "react";

const GradeItem = React.createClass({
    render() {
        return (<div><h3>GradeItem</h3><pre>{JSON.stringify(this.props.grade)}</pre></div>);
    }
});

export default GradeItem;
