import { useEffect, useRef, useState } from "react";

/** Act III — the material. A dependency-free WebGPU layer rendering the
 * desk: procedural fbm grain in steel-green under a slow-breathing lamp;
 * a phosphor field in microfiche dark. The canvas is a fixed aria-hidden
 * background; when it activates, [data-material="gpu"] unsets the CSS desk
 * so the shader shows through. No WebGPU → the CSS scene IS the desk.
 * Reduced-motion renders exactly one static frame. The lamp breath is
 * ambient light physics, not data — the honesty law is untouched. */

const WGSL = /* wgsl */ `
struct U { time: f32, dark: f32, w: f32, h: f32 };
@group(0) @binding(0) var<uniform> u: U;

@vertex
fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  var p = array<vec2f, 6>(
    vec2f(-1.0, -1.0), vec2f(1.0, -1.0), vec2f(-1.0, 1.0),
    vec2f(-1.0, 1.0), vec2f(1.0, -1.0), vec2f(1.0, 1.0));
  return vec4f(p[i], 0.0, 1.0);
}

fn hash(p: vec2f) -> f32 {
  return fract(sin(dot(p, vec2f(127.1, 311.7))) * 43758.5453);
}
fn vnoise(p: vec2f) -> f32 {
  let i = floor(p); let f = fract(p);
  let a = hash(i); let b = hash(i + vec2f(1.0, 0.0));
  let c = hash(i + vec2f(0.0, 1.0)); let d = hash(i + vec2f(1.0, 1.0));
  let s = f * f * (3.0 - 2.0 * f);
  return mix(mix(a, b, s.x), mix(c, d, s.x), s.y);
}
fn fbm(p: vec2f) -> f32 {
  var v = 0.0; var amp = 0.5; var q = p;
  for (var k = 0; k < 4; k++) { v += amp * vnoise(q); q *= 2.07; amp *= 0.5; }
  return v;
}

@fragment
fn fs(@builtin(position) pos: vec4f) -> @location(0) vec4f {
  let res = vec2f(u.w, u.h);
  let uv = pos.xy / res;
  let aspect = vec2f(u.w / u.h, 1.0);
  // the lamp: warm pool upper-center, breathing very slowly
  let lampD = distance(uv * aspect, vec2f(0.5, 0.30) * aspect);
  let lamp = 1.0 - smoothstep(0.0, 1.05, lampD);
  // brushed desk grain: fbm stretched slightly horizontal
  let grain = fbm(pos.xy * vec2f(0.012, 0.05));
  let micro = fbm(pos.xy * 0.35) * 0.5;

  if (u.dark > 0.5) {
    // microfiche: near-black green field, phosphor pool, scan grain
    let base = vec3f(0.040, 0.066, 0.046);
    let breath = 0.85 + 0.15 * sin(u.time * 0.45);
    let glow = base + vec3f(0.018, 0.05, 0.028) * lamp * breath;
    let lum = glow + vec3f(micro * 0.018);
    return vec4f(lum, 1.0);
  }

  // steel-green office desk under the lamp
  let desk = vec3f(0.282, 0.318, 0.276);
  let breath = 0.97 + 0.03 * sin(u.time * 0.35);
  let lit = desk * (0.74 + 0.34 * lamp * breath);
  let tex = lit + vec3f((grain - 0.5) * 0.05 + (micro - 0.25) * 0.025);
  // vignette: the photograph's edge falloff
  let vig = 1.0 - 0.32 * smoothstep(0.45, 1.25, distance(uv, vec2f(0.5, 0.42)));
  return vec4f(tex * vig, 1.0);
}
`;

export function DeskMaterial() {
  const ref = useRef<HTMLCanvasElement>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    let stop = false;
    let raf = 0;
    let device: GPUDevice | undefined;

    (async () => {
      if (!("gpu" in navigator) || !navigator.gpu) return;
      const canvas = ref.current;
      if (!canvas) return;
      try {
        const adapter = await navigator.gpu.requestAdapter();
        if (!adapter || stop) return;
        device = await adapter.requestDevice();
        const ctx = canvas.getContext("webgpu");
        if (!ctx || stop) return;
        const format = navigator.gpu.getPreferredCanvasFormat();

        const resize = () => {
          canvas.width = Math.floor(window.innerWidth * devicePixelRatio);
          canvas.height = Math.floor(window.innerHeight * devicePixelRatio);
          ctx.configure({ device: device!, format, alphaMode: "opaque" });
        };
        resize();
        window.addEventListener("resize", resize);

        const module = device.createShaderModule({ code: WGSL });
        const pipeline = device.createRenderPipeline({
          layout: "auto",
          vertex: { module, entryPoint: "vs" },
          fragment: { module, entryPoint: "fs", targets: [{ format }] },
          primitive: { topology: "triangle-list" },
        });
        const uniform = device.createBuffer({
          size: 16,
          usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
        });
        const bind = device.createBindGroup({
          layout: pipeline.getBindGroupLayout(0),
          entries: [{ binding: 0, resource: { buffer: uniform } }],
        });

        const reduced =
          typeof window.matchMedia === "function" &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const frame = (t: number) => {
          if (stop || !device) return;
          if (!document.hidden) {
            const dark =
              document.documentElement.dataset.theme === "dark" ? 1 : 0;
            device.queue.writeBuffer(
              uniform, 0,
              new Float32Array([t / 1000, dark, canvas.width, canvas.height]),
            );
            const enc = device.createCommandEncoder();
            const pass = enc.beginRenderPass({
              colorAttachments: [{
                view: ctx.getCurrentTexture().createView(),
                loadOp: "clear",
                storeOp: "store",
                clearValue: { r: 0, g: 0, b: 0, a: 1 },
              }],
            });
            pass.setPipeline(pipeline);
            pass.setBindGroup(0, bind);
            pass.draw(6);
            pass.end();
            device.queue.submit([enc.finish()]);
          }
          if (!reduced) raf = requestAnimationFrame(frame);
        };

        document.documentElement.dataset.material = "gpu";
        setActive(true);
        raf = requestAnimationFrame(frame);
      } catch {
        // any failure leaves the CSS desk untouched — the fallback IS the scene
      }
    })();

    return () => {
      stop = true;
      cancelAnimationFrame(raf);
      delete document.documentElement.dataset.material;
      device?.destroy();
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      data-testid="desk-material"
      data-active={active}
      className="desk-canvas"
    />
  );
}
