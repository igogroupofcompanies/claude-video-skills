import {Composition} from "remotion";
import {Promo, PromoProps, totalFrames} from "./Promo";

const defaults: PromoProps = {
  width: 1920, height: 1080, fps: 30, sceneSeconds: 3,
  brand: {primary: "#0B5D3B", secondary: "#E8C77A", ink: "#0E1A14", paper: "#FFFFFF", wordmark: "BRAND"},
  scenes: [{type: "title", text: "Headline", sub: "Subline"}, {type: "outro", text: "Thank you", sub: "example.com"}],
};

export const Root = () => (
  <Composition
    id="Promo" component={Promo} defaultProps={defaults}
    width={defaults.width} height={defaults.height} fps={defaults.fps} durationInFrames={90}
    calculateMetadata={({props}) => ({width: props.width, height: props.height, fps: props.fps, durationInFrames: totalFrames(props)})}
  />
);
