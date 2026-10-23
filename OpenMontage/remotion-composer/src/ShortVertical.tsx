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

// 9:16 Shorts layout: one big idea per scene, karaoke captions, top progress bar.
// Built for the YoutubeShortsInc pipeline (pipeline/render.py writes these props).

const { fontFamily } = loadFont("normal", { weights: ["600", "800", "900"], subsets: ["latin"] });

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
  cta?: string; // end-card line shown with a Subscribe button in the last seconds
  question?: string; // one-word-answer question shown on the end card to drive comments
  likeText?: string; // small "like" sticker shown once, just past the middle
  banner?: string; // intro sticker over the first seconds (2-5 word true teaser)
  outro?: string; // short line flashed over the very last frames to push a rewatch
}

const DEFAULT_PALETTE = ["#22D3EE", "#F472B6", "#FACC15", "#34D399", "#A78BFA", "#FB923C"];
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
    // Different camera move per scene: zoom in, zoom out, pan left, pan right.
    const t = frame / fps;
    const move = index % 4;
    const scale = move === 1 ? 1.35 - t * 0.06 : 1.15 + t * 0.06;
    const panX = move === 2 ? -t * 18 : move === 3 ? t * 18 : 0;
    const punch = interpolate(frame, [0, 6], [1.12, 1], { extrapolateRight: "clamp" });
    const flash = interpolate(frame, [0, 4], [0.55, 0], { extrapolateRight: "clamp" });
    return (
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {VIDEO_EXT.test(scene.background) ? (
          <OffthreadVideo
            src={src}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${punch * 1.05})` }}
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
        <AbsoluteFill style={{ backgroundColor: "white", opacity: flash }} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.35) 45%, rgba(0,0,0,0.75) 100%)" }} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${50 + drift}% ${30 - drift}%, ${accent}55 0%, #0B1020 55%), #0B1020`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
          backgroundSize: "90px 90px",
          transform: `translateY(${(frame % 90) * 0.5}px)`,
          opacity: 0.6,
        }}
      />
    </AbsoluteFill>
  );
};

const SceneCard: React.FC<{ scene: ShortScene; accent: string; index: number }> = ({ scene, accent, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // The very first frame is what people see in the feed: show the opening headline fully, no fade-in.
  const pop = index === 0 ? 1 : spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  const rise = interpolate(pop, [0, 1], [80, 0]);
  const statPop = index === 0 ? 1 : spring({ frame: frame - 4, fps, config: { damping: 9, stiffness: 160 } });
  return (
    <AbsoluteFill>
      <Background scene={scene} accent={accent} index={index} />
      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "center",
          paddingTop: 300,
          paddingLeft: 70,
          paddingRight: 70,
          fontFamily,
          textAlign: "center",
          transform: `translateY(${rise}px)`,
          opacity: pop,
        }}
      >
        {scene.emoji && !scene.background ? (
          <div style={{ fontSize: 190, lineHeight: 1, marginBottom: 30, transform: `scale(${0.6 + 0.4 * pop})` }}>
            {scene.emoji}
          </div>
        ) : null}
        {scene.stat ? (
          <div
            style={{
              fontSize: scene.stat.length > 6 ? 150 : 230,
              fontWeight: 900,
              color: accent,
              lineHeight: 1,
              transform: `scale(${statPop})`,
              textShadow: `0 0 60px ${accent}88`,
            }}
          >
            {scene.stat}
          </div>
        ) : null}
        {scene.headline ? (
          <div
            style={{
              fontSize: scene.stat ? 70 : 92,
              fontWeight: 900,
              color: "white",
              lineHeight: 1.08,
              marginTop: 24,
              textTransform: "uppercase",
              letterSpacing: -1,
              textShadow: "0 6px 30px rgba(0,0,0,0.6)",
            }}
          >
            {scene.headline}
          </div>
        ) : null}
        {scene.sub ? (
          <div style={{ fontSize: 46, fontWeight: 600, color: "#CBD5E1", marginTop: 26, lineHeight: 1.25 }}>{scene.sub}</div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

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
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 470, paddingLeft: 50, paddingRight: 50 }}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 92,
          textAlign: "center",
          lineHeight: 1.1,
          textTransform: "uppercase",
          transform: `scale(${0.85 + 0.15 * bump})`,
        }}
      >
        {page.map((w, i) => {
          const active = t >= w.start && t < w.end + 0.05;
          return (
            <span
              key={i}
              style={{
                color: active ? color : "white",
                WebkitTextStroke: "3px black",
                paintOrder: "stroke fill",
                textShadow: "0 8px 0 rgba(0,0,0,0.55)",
                margin: "0 12px",
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
      <div style={{ position: "absolute", top: 0, left: 0, height: 12, width: `${(frame / durationInFrames) * 100}%`, background: color }} />
    </AbsoluteFill>
  );
};

const IntroBanner: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Visible from frame 0 (it doubles as the feed thumbnail), wobbles for attention, then flies out.
  const wobble = Math.sin(frame / 2.2) * 2.5 * interpolate(frame, [0, fps * 1.2], [1, 0.3], { extrapolateRight: "clamp" });
  const out = interpolate(frame, [fps * 2.3, fps * 2.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 120 }}>
      <div
        style={{
          transform: `rotate(${-3 + wobble}deg) translateY(${-out * 400}px)`,
          background: "#FFE600",
          color: "#0B1020",
          fontFamily,
          fontWeight: 900,
          fontSize: 66,
          lineHeight: 1.05,
          textTransform: "uppercase",
          textAlign: "center",
          padding: "18px 36px",
          borderRadius: 18,
          border: "6px solid #0B1020",
          boxShadow: "0 12px 0 rgba(0,0,0,0.45)",
          maxWidth: 900,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const OutroFlash: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 9, stiffness: 220 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 260 }}>
      <div
        style={{
          transform: `scale(${pop})`,
          background: "#FF2D55",
          color: "white",
          fontFamily,
          fontWeight: 900,
          fontSize: 56,
          textTransform: "uppercase",
          padding: "14px 34px",
          borderRadius: 999,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const LikeSticker: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const slide = spring({ frame, fps, config: { damping: 14, stiffness: 200 } });
  const out = interpolate(frame, [fps * 1.4, fps * 1.7], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const thumb = interpolate(frame, [fps * 0.3, fps * 0.45, fps * 0.6], [1, 1.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "flex-end", justifyContent: "flex-start", paddingTop: 150, paddingRight: 40 }}>
      <div
        style={{
          transform: `translateX(${(1 - slide) * 500}px)`,
          opacity: out,
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "16px 28px",
          borderRadius: 999,
          background: "rgba(255,255,255,0.95)",
          fontFamily,
          fontWeight: 800,
          fontSize: 40,
          color: "#0B1020",
        }}
      >
        <span style={{ fontSize: 52, display: "inline-block", transform: `scale(${thumb})` }}>👍</span>
        {text}
      </div>
    </AbsoluteFill>
  );
};

const SubscribeCard: React.FC<{ text: string; color: string; question?: string }> = ({ text, color, question }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 180 } });
  const press = interpolate(frame, [Math.round(fps * 0.9), Math.round(fps * 1.05), Math.round(fps * 1.2)], [1, 0.9, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subscribed = frame > fps * 1.05;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 200 }}>
      <div
        style={{
          transform: `scale(${pop})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 34,
          padding: "46px 56px",
          borderRadius: 40,
          background: "rgba(11,16,32,0.82)",
          border: `4px solid ${color}`,
          fontFamily,
        }}
      >
        {question ? (
          <div style={{ fontSize: 54, fontWeight: 900, color, textAlign: "center", lineHeight: 1.15, maxWidth: 840 }}>
            💬 {question}
            <div style={{ fontSize: 34, fontWeight: 700, color: "#CBD5E1", marginTop: 10 }}>ANSWER IN THE COMMENTS</div>
          </div>
        ) : null}
        <div style={{ fontSize: question ? 42 : 58, fontWeight: 900, color: "white", textAlign: "center", lineHeight: 1.1, textTransform: "uppercase", maxWidth: 820 }}>
          {text}
        </div>
        <div
          style={{
            transform: `scale(${press})`,
            background: subscribed ? "#3F3F46" : "#FF0000",
            color: "white",
            fontSize: 64,
            fontWeight: 800,
            padding: "22px 64px",
            borderRadius: 999,
          }}
        >
          {subscribed ? "SUBSCRIBED 🔔" : "SUBSCRIBE"}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const ShortVertical: React.FC<ShortVerticalProps> = (props) => {
  const { fps } = useVideoConfig();
  const palette = props.palette && props.palette.length ? props.palette : DEFAULT_PALETTE;
  return (
    <AbsoluteFill style={{ backgroundColor: "#0B1020" }}>
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
      <Captions words={props.words} palette={palette} />
      {props.likeText && props.scenes.length ? (
        <Sequence from={Math.round(props.scenes[props.scenes.length - 1].end * 0.55 * fps)} durationInFrames={Math.round(fps * 1.8)}>
          <LikeSticker text={props.likeText} />
        </Sequence>
      ) : null}
      {props.cta && props.scenes.length ? (
        <Sequence from={Math.max(0, Math.round((props.scenes[props.scenes.length - 1].end - (props.question ? 2.4 : 1.6)) * fps))}>
          <SubscribeCard text={props.cta} color={palette[0]} question={props.question} />
        </Sequence>
      ) : null}
      {props.banner ? (
        <Sequence from={0} durationInFrames={Math.round(fps * 2.8)}>
          <IntroBanner text={props.banner} />
        </Sequence>
      ) : null}
      {props.outro && props.scenes.length ? (
        <Sequence from={Math.max(0, Math.round((props.scenes[props.scenes.length - 1].end - 1.0) * fps))}>
          <OutroFlash text={props.outro} />
        </Sequence>
      ) : null}
      <ProgressBar color={palette[0]} />
      {props.handle ? (
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 90 }}>
          <div style={{ fontFamily, fontWeight: 700, fontSize: 38, color: "rgba(255,255,255,0.7)" }}>{props.handle}</div>
        </AbsoluteFill>
      ) : null}
      {props.narration ? <Audio src={resolveAsset(props.narration)} /> : null}
      {props.music ? <Audio src={resolveAsset(props.music)} volume={props.musicVolume ?? 0.08} loop /> : null}
    </AbsoluteFill>
  );
};
