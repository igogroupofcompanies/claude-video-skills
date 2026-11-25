import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from "remotion";

type Brand = {primary: string; secondary: string; ink: string; paper: string; wordmark: string};
export type Scene =
  | {type: "title"; text: string; sub?: string}
  | {type: "stats"; heading?: string; items: {value: number; suffix?: string; prefix?: string; label: string}[]}
  | {type: "quote"; text: string; by?: string}
  | {type: "outro"; text: string; sub?: string};
export type PromoProps = {width: number; height: number; fps: number; sceneSeconds: number; brand: Brand; scenes: Scene[]};

export const totalFrames = (p: PromoProps) => Math.round(p.scenes.length * p.sceneSeconds * p.fps);
const FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif";

const Bg: React.FC<{brand: Brand}> = ({brand}) => {
  const f = useCurrentFrame();
  const a = 135 + Math.sin(f / 90) * 20;
  return (
    <AbsoluteFill style={{background: `linear-gradient(${a}deg, ${brand.ink} 0%, ${brand.primary} 100%)`}}>
      <AbsoluteFill style={{background: `radial-gradient(circle at ${50 + Math.sin(f / 70) * 20}% 40%, ${brand.secondary}22, transparent 55%)`}} />
    </AbsoluteFill>
  );
};

const useIn = (delay = 0) => {
  const f = useCurrentFrame(); const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping: 18, stiffness: 110}});
};

const Fade: React.FC<{children: React.ReactNode; dur: number}> = ({children, dur}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, dur - 8, dur], [0, 1, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

const Title: React.FC<{s: Extract<Scene, {type: "title" | "outro"}>; brand: Brand}> = ({s, brand}) => {
  const {width, height} = useVideoConfig(); const t = useIn(0), u = useIn(10), line = useIn(4);
  const fs = width * (height > width * 0.9 ? 0.11 : 0.06);
  return (
    <AbsoluteFill style={{justifyContent: "center", padding: width * 0.08, fontFamily: FONT, color: brand.paper}}>
      <div style={{width: width * 0.12 * line, height: 6, background: brand.secondary, marginBottom: fs * 0.4}} />
      <div style={{fontSize: fs, fontWeight: 700, lineHeight: 1.08, transform: `translateY(${(1 - t) * 40}px)`, opacity: t}}>{s.text}</div>
      {s.sub && <div style={{fontSize: fs * 0.42, marginTop: fs * 0.35, color: brand.secondary, opacity: u, transform: `translateY(${(1 - u) * 24}px)`}}>{s.sub}</div>}
    </AbsoluteFill>
  );
};

const Stats: React.FC<{s: Extract<Scene, {type: "stats"}>; brand: Brand}> = ({s, brand}) => {
  const f = useCurrentFrame(); const {width, height, fps} = useVideoConfig();
  const vertical = height > width * 0.9; const fs = Math.min(width, height) * (vertical ? 0.13 : 0.1);
  return (
    <AbsoluteFill style={{justifyContent: "center", padding: width * 0.07, fontFamily: FONT, color: brand.paper}}>
      {s.heading && <div style={{fontSize: fs * 0.4, color: brand.secondary, marginBottom: fs * 0.5, fontWeight: 600}}>{s.heading}</div>}
      <div style={{display: "flex", flexDirection: vertical ? "column" : "row", gap: fs * 0.7}}>
        {s.items.map((it, i) => {
          const p = interpolate(f, [i * 8, i * 8 + fps * 1.2], [0, 1], {easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp"});
          return (
            <div key={i} style={{flex: 1, opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 30}px)`}}>
              <div style={{fontSize: fs, fontWeight: 800, color: brand.secondary, fontVariantNumeric: "tabular-nums"}}>
                {it.prefix}{Math.round(it.value * p).toLocaleString("en-IN")}{it.suffix}
              </div>
              <div style={{fontSize: fs * 0.3, opacity: 0.9}}>{it.label}</div>
              <div style={{height: 4, width: `${p * 100}%`, background: brand.secondary, marginTop: 12, opacity: 0.6}} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Quote: React.FC<{s: Extract<Scene, {type: "quote"}>; brand: Brand}> = ({s, brand}) => {
  const {width, height} = useVideoConfig(); const t = useIn(0), b = useIn(14); const fs = width * (height > width * 0.9 ? 0.07 : 0.042);
  return (
    <AbsoluteFill style={{justifyContent: "center", padding: width * 0.1, fontFamily: "Georgia, serif", color: brand.paper}}>
      <div style={{fontSize: fs * 2.4, color: brand.secondary, lineHeight: 0.5, opacity: t}}>“</div>
      <div style={{fontSize: fs, lineHeight: 1.3, opacity: t, transform: `translateY(${(1 - t) * 30}px)`}}>{s.text}</div>
      {s.by && <div style={{fontFamily: FONT, fontSize: fs * 0.5, marginTop: fs * 0.6, color: brand.secondary, opacity: b}}>{s.by}</div>}
    </AbsoluteFill>
  );
};

export const Promo: React.FC<PromoProps> = (p) => {
  const per = Math.round(p.sceneSeconds * p.fps); const {width, height} = useVideoConfig(); const vert = height > width * 0.9;
  return (
    <AbsoluteFill>
      <Bg brand={p.brand} />
      {p.scenes.map((s, i) => (
        <Sequence key={i} from={i * per} durationInFrames={per}>
          <Fade dur={per}>
            {s.type === "stats" ? <Stats s={s} brand={p.brand} /> : s.type === "quote" ? <Quote s={s} brand={p.brand} /> : <Title s={s} brand={p.brand} />}
          </Fade>
        </Sequence>
      ))}
      <div style={{position: "absolute", left: width * 0.06, bottom: width * (vert ? 0.08 : 0.03), fontFamily: FONT, fontWeight: 700, letterSpacing: 4, color: p.brand.paper, opacity: 0.85, fontSize: width * (vert ? 0.03 : 0.016)}}>
        {p.brand.wordmark}
      </div>
    </AbsoluteFill>
  );
};
