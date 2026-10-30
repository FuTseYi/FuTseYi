/* WebGL atmosphere inspired by DeepSeek Harness.
   Simplex noise: Copyright (C) 2011 Ashima Arts, MIT.
   See webgl-noise-LICENSE.txt. */
(() => {
  const layer = document.createElement('div');
  layer.className = 'atmosphere';
  layer.setAttribute('aria-hidden', 'true');
  const canvas = document.createElement('canvas');
  layer.append(canvas);
  document.body.prepend(layer);
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, powerPreference: 'low-power' });
  if (!gl) { layer.remove(); return; }
  const shaders = [];
  const compile = (type, source) => {
    const shader = gl.createShader(type);
    shaders.push(shader);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
  };
  const vertex = compile(gl.VERTEX_SHADER, `#version 300 es
    in vec2 position;
    void main(){gl_Position=vec4(position,0.,1.);}`);
  const fragment = compile(gl.FRAGMENT_SHADER, `#version 300 es
    precision highp float;
    uniform vec2 resolution;
    uniform float time;
    uniform float dark;
    out vec4 pixel;
    vec3 mod289(vec3 x) {
      return x - floor(x * (1.0 / 289.0)) * 289.0;
    }
    vec4 mod289(vec4 x) {
      return x - floor(x * (1.0 / 289.0)) * 289.0;
    }
    vec4 permute(vec4 x) {
         return mod289(((x*34.0)+1.0)*x);
    }
    vec4 taylorInvSqrt(vec4 r)
    {
      return 1.79284291400159 - 0.85373472095314 * r;
    }
    float noise(vec3 v)
      {
      const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
      const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy) );
      vec3 x0 =   v - i + dot(i, C.xxx) ;
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min( g.xyz, l.zxy );
      vec3 i2 = max( g.xyz, l.zxy );
      vec3 x1 = x0 - i1 + C.xxx;
      vec3 x2 = x0 - i2 + C.yyy;
      vec3 x3 = x0 - D.yyy;
      i = mod289(i);
      vec4 p = permute( permute( permute(
                 i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
               + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
               + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
      float n_ = 0.142857142857;
      vec3  ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_ );
      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4( x.xy, y.xy );
      vec4 b1 = vec4( x.zw, y.zw );
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
      vec3 p0 = vec3(a0.xy,h.x);
      vec3 p1 = vec3(a0.zw,h.y);
      vec3 p2 = vec3(a1.xy,h.z);
      vec3 p3 = vec3(a1.zw,h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x;
      p1 *= norm.y;
      p2 *= norm.z;
      p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1),
                                    dot(p2,x2), dot(p3,x3) ) );
      }
    vec2 drift(float period,float speed){
      float angle=time*6.2831853/period;
      return vec2(sin(angle),1.-cos(angle))*speed*period/6.2831853;
    }
    vec3 travel(float period,float speed,bool sideways){
      vec2 offset=drift(period,speed);
      return sideways?vec3(0.,offset.y,offset.x):vec3(offset.y,0.,offset.x);
    }
    float field(vec2 p){
      vec2 a=vec2(noise(vec3(p*.6,0.)+travel(3000.,.0102,false)),noise(vec3(p*.6+5.2,1.3)+travel(3000.,.0102,true)))*.36;
      vec2 b=vec2(noise(vec3((p+a)*.7+1.7,3.1)+travel(3300.,.0085,false)),noise(vec3((p+a)*.7+9.2,5.7)+travel(3300.,.0085,true)))*.3;
      return noise(vec3((p+a+b)*.5,0.)+travel(3900.,.0068,false))*.6;
    }
    void main(){
      vec2 uv=gl_FragCoord.xy/resolution;
      float aspect=resolution.x/resolution.y;
      vec2 p=vec2(uv.x*aspect,uv.y)*1.19-vec2(1.24,.48);
      float base=noise(vec3(p*.8,0.)+travel(3900.,.0068,true));
      vec2 slope=vec2(noise(vec3((p+vec2(.02,0.))*.8,0.)+travel(3900.,.0068,true))-base,
        noise(vec3((p+vec2(0.,.02))*.8,0.)+travel(3900.,.0068,true))-base)/.02;
      p+=vec2(-slope.y,slope.x)*.036;
      float flow=field(p);
      float cloud=noise(vec3(p*.8+flow*1.5,0.)+travel(4200.,.00595,false))*.5+.5;
      float depth=flow*.5+.5;
      vec3 col=mix(vec3(0.),vec3(26.,56.,112.)/255.,smoothstep(.2,.5,depth));
      col=mix(col,vec3(32.,74.,126.)/255.,smoothstep(.35,.65,depth+cloud*.25));
      col=mix(col,vec3(238.,216.,170.)/255.,smoothstep(.6,.85,cloud)*.55);
      col*=1.-smoothstep(.5,.8,depth*cloud)*.35;
      float brightness=dot(col,vec3(.299,.587,.114));
      col+=(col*.85+vec3(.15,.145,.13))*smoothstep(.43,.79,brightness)*.4;
      float distanceToLight=length((uv-vec2(.89,.46))*vec2(aspect,1.));
      col+=(vec3(1.,.97,.9)*exp(-distanceToLight*distanceToLight*4.5)*.14+
        vec3(.72,.8,1.)*exp(-distanceToLight*1.8)*.2);
      col*=1.-.38*smoothstep(.35,.75,length(uv-.5));
      vec2 grainCell=floor((uv*resolution+(p-(vec2(uv.x*aspect,uv.y)*1.19-vec2(1.24,.48)))*resolution.y)/5.);
      vec3 seed=fract(vec3(grainCell.xyx)*.1031);
      seed+=dot(seed,seed.yzx+33.33);
      float grain=fract((seed.x+seed.y)*seed.z)*2.-1.;
      // Both themes share the same moving field; only the color mapping differs.
      float ribbon=smoothstep(.32,.78,cloud);
      float left=exp(-pow((uv.x-.17)*2.4,2.))*(.25+.75*ribbon);
      float right=exp(-pow((uv.x-.81)*2.1,2.))*(.3+.7*smoothstep(.25,.75,flow*.5+.5));
      float tint=clamp((left*.38+right*.48)*smoothstep(0.,.55,uv.y),0.,.58);
      vec3 paper=mix(vec3(1.),vec3(.65,.83,1.),tint);
      pixel=vec4(mix(paper,col+grain*.005,dark),1.);
    }`);
  const program = gl.createProgram();
  const buffer = gl.createBuffer();
  const release = () => {
    shaders.forEach(shader => gl.deleteShader(shader));
    gl.deleteProgram(program);
    gl.deleteBuffer(buffer);
  };
  if (!vertex || !fragment) { release(); layer.remove(); return; }
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { release(); layer.remove(); return; }
  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, 'position');
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  const uniforms = Object.fromEntries(['resolution','time','dark'].map(name => [name, gl.getUniformLocation(program, name)]));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const system = matchMedia('(prefers-color-scheme: dark)');
  let visible = true, lost = false, frame = 0, last = 0, elapsed = 0;
  const draw = () => {
    const theme = document.documentElement.dataset.theme;
    gl.uniform1f(uniforms.dark, theme === 'dark' || (theme !== 'light' && system.matches) ? 1 : 0);
    gl.uniform1f(uniforms.time, elapsed);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    layer.classList.add('is-ready');
  };
  const tick = now => {
    frame = 0;
    if (lost || !visible || document.hidden) { last = 0; return; }
    if (!last || now - last >= 1000 / 30) {
      if (last && !reduced.matches) elapsed += Math.min(now - last, 100) / 1000 * 1.25;
      last = now;
      draw();
    }
    if (!reduced.matches) frame = requestAnimationFrame(tick);
  };
  const refresh = () => {
    cancelAnimationFrame(frame);
    last = 0;
    if (!lost && visible && !document.hidden) { draw(); if (!reduced.matches) frame = requestAnimationFrame(tick); }
  };
  const resize = new ResizeObserver(() => {
    const bounds = layer.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 1.5);
    const scale = Math.min(dpr, 1400 / bounds.width, Math.sqrt(1000000 / (bounds.width * bounds.height)));
    canvas.width = Math.max(1, Math.floor(bounds.width * scale));
    canvas.height = Math.max(1, Math.floor(bounds.height * scale));
    gl.uniform2f(uniforms.resolution, canvas.width, canvas.height);
    refresh();
  });
  resize.observe(layer);
  new IntersectionObserver(entries => { visible = entries[0].isIntersecting; refresh(); }).observe(layer);
  new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  [reduced, system].forEach(query => query.addEventListener('change', refresh));
  document.addEventListener('visibilitychange', refresh);
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault(); lost = true; cancelAnimationFrame(frame); layer.classList.remove('is-ready');
  });
})();
