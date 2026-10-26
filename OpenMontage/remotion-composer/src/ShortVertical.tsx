import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  CalculateMetadataFunction,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { resolveAsset } from "./lib/resolveAsset";

// 9:16 Shorts layout: Single Subtitle Mandate.
// Clean real-world footage, Ken Burns motion, and EXACTLY ONE dynamic animated karaoke subtitle stream on screen.
// Built for YoutubeShortsInc (TerraQuest).

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin"] });

export interface ShortScene {
  start: number; // seconds
  end: number; // seconds
  emoji?: string;
  headline?: string;
  stat?: string;
  sub?: string;
  accent?: string;
  background?: string; // image or video path (public-relative or absolute)
}

export interface ShortWord {
  word: string;
  start: number; // seconds
  end: number; // seconds
  brk?: boolean; // last word of a scene: start a new caption page after it
}

export interface ShortVerticalProps {
  [key: string]: unknown;
  scenes: ShortScene[];
  words: ShortWord[];
  narration?: string;
  music?: string;
  musicVolume?: number;
  palette?: string[];
  handle?: string;
  cta?: string;
  question?: string;
  likeText?: string;
  banner?: string;
  outro?: string;
}

const DEFAULT_PALETTE = ["#38BDF8", "#F472B6", "#FACC15", "#34D399", "#A78BFA", "#FB923C"];
const VIDEO_EXT = /\.(mp4|mov|webm|mkv)$/i;

export const calculateShortMetadata: CalculateMetadataFunction<ShortVerticalProps> = async ({ props }) => {
  const end = Math.max(1, ...props.scenes.map((s) => s.end));
  return { durationInFrames: Math.ceil((end + 0.4) * 30) };
};

const Background: React.FC<{ scene: ShortScene; accent: string; index: number }> = ({ scene, accent, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drift = Math.sin((frame + index * 40) / 45) * 8;

  if (scene.background) {
    const src = resolveAsset(scene.background);
    const t = frame / fps;
    const move = index % 4;

    // Smooth cinematic Ken Burns easing
    const scale = move === 1 ? 1.28 - t * 0.035 : 1.12 + t * 0.035;
    const panX = move === 2 ? -t * 12 : move === 3 ? t * 12 : 0;
    const punch = interpolate(frame, [0, 8], [1.07, 1], { extrapolateRight: "clamp" });
    const flash = interpolate(frame, [0, 4], [0.3, 0], { extrapolateRight: "clamp" });

    return (
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {VIDEO_EXT.test(scene.background) ? (
          <OffthreadVideo
            src={src}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${punch * 1.04})` }}
          />
        ) : (
          <Img
            src={src}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${scale * punch}) translateX(${panX}px)`,
            }}
          />
        )}
        {/* Soft cut transition flash */}
        <AbsoluteFill style={{ backgroundColor: "white", opacity: flash }} />

        {/* Subtle Bottom Gradient Scrim for perfect single-subtitle contrast */}
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(7,11,24,0.35) 0%, transparent 40%, rgba(7,11,24,0.45) 65%, rgba(7,11,24,0.85) 100%)",
          }}
        />

        {/* Subtle Edge Vignette */}
        <AbsoluteFill
          style={{
            background: "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.5) 100%)",
          }}
        />
      </AbsoluteFill>
    );
  }

  // Premium Procedural Motion Fallback if no media exists
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${50 + drift}% ${30 - drift}%, ${accent}44 0%, #070B18 60%), #070B18`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
          transform: `translateY(${(frame % 80) * 0.4}px)`,
          opacity: 0.5,
        }}
      />
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle at 50% 50%, transparent 30%, rgba(0,0,0,0.7) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

// SceneCard: STRICTLY renders the background media only.
// NO static headlines, NO sub-headlines, NO clutter. (Single Subtitle Mandate)
const SceneCard: React.FC<{ scene: ShortScene; accent: string; index: number }> = ({ scene, accent, index }) => {
  return (
    <AbsoluteFill>
      <Background scene={scene} accent={accent} index={index} />
    </AbsoluteFill>
  );
};

// Captions: The ONLY subtitle on screen. Clean, animated, high-retention karaoke style.
const Captions: React.FC<{ words: ShortWord[]; palette: string[] }> = ({ words, palette }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // Pages of up to 3 words; a page holds until the next page starts.
  const pages: ShortWord[][] = [];
  let cur: ShortWord[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length === 3 || w.brk) {
      pages.push(cur);
      cur = [];
    }
  }
  if (cur.length) pages.push(cur);

  const pageIndex = pages.findIndex((p, i) => t >= p[0].start && (i === pages.length - 1 || t < pages[i + 1][0].start));
  if (pageIndex < 0) return null;
  const page = pages[pageIndex];
  if (t > page[page.length - 1].end + 0.6) return null;

  const color = palette[pageIndex % palette.length];
  const pageFrame = frame - Math.round(page[0].start * fps);
  const bump = spring({ frame: pageFrame, fps, config: { damping: 14, stiffness: 220 } });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 420,
        paddingLeft: 40,
        paddingRight: 40,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 92,
          textAlign: "center",
          lineHeight: 1.15,
          textTransform: "uppercase",
          transform: `scale(${0.92 + 0.08 * bump})`,
          background: "rgba(11, 16, 32, 0.65)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderRadius: 28,
          padding: "16px 36px",
          border: "1.5px solid rgba(255, 255, 255, 0.15)",
          boxShadow: "0 14px 40px rgba(0, 0, 0, 0.7)",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          maxWidth: 960,
        }}
      >
        {page.map((w, i) => {
          const active = t >= w.start && t < w.end + 0.05;
          return (
            <span
              key={i}
              style={{
                color: active ? color : "#FFFFFF",
                transform: active ? "scale(1.12)" : "scale(1.0)",
                transition: "transform 0.08s ease-out",
                WebkitTextStroke: "3.5px rgba(0,0,0,0.9)",
                paintOrder: "stroke fill",
                textShadow: active ? `0 0 24px ${color}aa, 0 6px 14px rgba(0,0,0,0.8)` : "0 6px 12px rgba(0,0,0,0.8)",
                margin: "4px 18px",
                display: "inline-block",
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 12,
          width: `${(frame / durationInFrames) * 100}%`,
          background: `linear-gradient(90deg, ${color}, #60A5FA)`,
          boxShadow: `0 0 16px ${color}cc`,
        }}
      />
    </AbsoluteFill>
  );
};

export const ShortVertical: React.FC<ShortVerticalProps> = (props) => {
  const { fps } = useVideoConfig();
  const palette = props.palette && props.palette.length ? props.palette : DEFAULT_PALETTE;

  return (
    <AbsoluteFill style={{ backgroundColor: "#070B18" }}>
      {/* Visual Scenes - Pure background footage */}
      {props.scenes.map((scene, i) => {
        const from = Math.round(scene.start * fps);
        const next = props.scenes[i + 1];
        const until = Math.round((next ? next.start : scene.end + 0.4) * fps);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, until - from)}>
            <SceneCard scene={scene} accent={scene.accent || palette[i % palette.length]} index={i} />
          </Sequence>
        );
      })}

      {/* SINGLE SUBTITLE ONLY: Dynamic animated karaoke captions */}
      <Captions words={props.words} palette={palette} />

      {/* Neon Progress Bar */}
      <ProgressBar color={palette[0]} />

      {/* Clean Brand Watermark */}
      {props.handle ? (
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 75, pointerEvents: "none" }}>
          <div
            style={{
              fontFamily,
              fontWeight: 700,
              fontSize: 32,
              color: "rgba(255,255,255,0.65)",
              letterSpacing: "1.2px",
              textShadow: "0 2px 10px rgba(0,0,0,0.8)",
            }}
          >
            {props.handle}
          </div>
        </AbsoluteFill>
      ) : null}

      {/* Audio Tracks */}
      {props.narration ? <Audio src={resolveAsset(props.narration)} /> : null}
      {props.music ? <Audio src={resolveAsset(props.music)} volume={props.musicVolume ?? 0.08} loop /> : null}
    </AbsoluteFill>
  );
};
