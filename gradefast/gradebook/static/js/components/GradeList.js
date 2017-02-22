import * as React from "react";

import GradeSection from "./GradeSection";
import GradeItem from "./GradeItem";

export default ({path, grades}) => (
    <div>
        {(grades || []).map((grade, index) => {
            // We need to have a "key" for each thing here...
            // https://facebook.github.io/react/docs/lists-and-keys.html#keys
            if (grade.has("children") && grade.get("children")) {
                return <GradeSection key={index} grade={grade} path={path.push(index)}/>;
            } else {
                return <GradeItem key={index} grade={grade} path={path.push(index)} />;
            }
        })}
    </div>
);
