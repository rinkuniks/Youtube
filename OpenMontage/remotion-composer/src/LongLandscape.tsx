import React from "react";
import { AbsoluteFill } from "remotion";
import { ShortVertical, ShortVerticalProps } from "./ShortVertical";

// 16:9 long-video layout for the YoutubeShortsInc pipeline. Reuses the Shorts look: the Shorts scene
// is laid out on a 3413x1920 canvas (16:9 at the Shorts' 1920px height, so its font sizes stay
// proportional) and scaled down to the 1920x1080 frame.

const CANVAS_W = Math.round((1920 * 16) / 9);
const CANVAS_H = 1920;

export const LongLandscape: React.FC<ShortVerticalProps> = (props) => (
  <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
    <div
      style={{
        position: "absolute",
        width: CANVAS_W,
        height: CANVAS_H,
        transform: `scale(${1080 / CANVAS_H})`,
        transformOrigin: "top left",
      }}
    >
      <ShortVertical {...props} />
    </div>
  </AbsoluteFill>
);
