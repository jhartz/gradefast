import * as React from "react";

import GradeScore from "./GradeScore";
import GradeSection from "./GradeSection";

export default ({path, grades}) => (
    <div>
        {(grades || []).map((grade, index) => {
            // We need to have a "key" for each thing here...
            // https://facebook.github.io/react/docs/lists-and-keys.html#keys
            // Might as well use the index, since it'd better stay constant (it's part of the "path")
            if (grade.has("children") && grade.get("children")) {
                return <GradeSection key={index} grade={grade} path={path.push(index)} />;
            } else {
                return <GradeScore key={index} grade={grade} path={path.push(index)} />;
            }
        })}
    </div>
);
