/* Blue-grey noise atmosphere. Independent WebGL implementation informed by the
   DeepSeek Harness landing page's fluid layering, lighting and fade treatment.
   Simplex noise: Copyright (C) 2011 Ashima Arts, MIT; see webgl-noise-LICENSE.txt.
   Uses the original noise constants; the light palette is a site adaptation. */
(() => {
  const layer = document.createElement('div');
  layer.className = 'atmosphere';
  layer.setAttribute('aria-hidden', 'true');
  const canvas = document.createElement('canvas');
  layer.append(canvas);
  document.body.prepend(layer);
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false, powerPreference: 'low-power' });
  if (!gl) { layer.remove(); return; }
  // One seed per page load; a numeric query parameter allows reproducible previews.
  const seedParam = new URLSearchParams(location.search).get('atmosphere-seed');
  const parsedSeed = seedParam === null ? NaN : Number(seedParam);
  const seedValue = Number.isFinite(parsedSeed) ? parsedSeed >>> 0 : crypto.getRandomValues(new Uint32Array(1))[0];
  const seeded = Math.imul(seedValue ^ (seedValue >>> 16), 0x85ebca6b) >>> 0;
  const offset = [seedValue / 4294967295 * 3.8 - 1.9, seeded / 4294967295 * 3.8 - 1.9];
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
    uniform float touch;
    uniform vec2 seed;
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
    // Soft directional envelopes share one turbulent field rather than three render passes.
    float plume(vec2 p,vec2 origin,vec2 direction,float width,float reach){
      vec2 delta=p-origin;
      float along=dot(delta,direction);
      float across=abs(dot(delta,vec2(-direction.y,direction.x)));
      float spread=width+max(along,0.)*.24;
      float body=1.-smoothstep(spread*.48,spread*1.65,across);
      float head=smoothstep(-.2,.18,along);
      float tail=1.-smoothstep(reach*.55,reach,along);
      return body*head*tail;
    }
    void main(){
      vec2 uv=gl_FragCoord.xy/resolution;
      float aspect=resolution.x/resolution.y;
      vec2 pos=vec2(uv.x*aspect,uv.y);
      vec2 p=pos*1.15+seed*.31;
      float phase=time*.017;
      // Shared, continuous domain warp keeps opposed currents connected.
      vec2 warp=vec2(
        noise(vec3(p*.73,phase)),
        noise(vec3(p*.73+vec2(9.1,3.7),phase*.83))
      );
      vec2 fine=vec2(
        noise(vec3(p*1.55+warp*.35,phase*.67+4.)),
        noise(vec3(p*1.55+warp*.35+vec2(4.7,8.2),phase*.71))
      );
      vec2 swept=pos+(warp*.105+fine*.037);
      vec2 a=normalize(vec2(-.83,-.55));
      vec2 b=normalize(vec2(.85,.53));
      vec2 c=normalize(vec2(.55,-.83));
      float high=plume(swept,vec2(aspect*1.04,.94),a,.20,.98);
      float low=plume(swept,vec2(-aspect*.08,.03),b,.23,1.05);
      float side=plume(swept,vec2(aspect*.18,1.13),c,.12,.73);
      float opposing=max(high,low*.88);
      float sources=max(opposing,side*.52);
      // Compression and shear at the meeting point create depth, not flat additive glow.
      float collision=min(high,low);
      float turbulence=noise(vec3(p*2.05+warp*.64+fine*.18,phase*.59+7.))*.5+.5;
      float broad=noise(vec3(p*.85+warp*.2,phase*.31+2.))*.5+.5;
      float density=clamp(sources*(.48+.53*broad+.39*turbulence)+collision*.22,0.,1.);
      float ridge=smoothstep(.46,.79,turbulence)*sources;
      float core=smoothstep(.48,.9,density);
      float shadow=collision*(1.-turbulence)*.24;
      // Shared density and lighting, with separate dark/light color ramps.
      vec3 darkBase=vec3(.012,.026,.058);
      vec3 darkBody=vec3(.085,.22,.42);
      vec3 darkLight=vec3(.47,.69,.87);
      vec3 night=mix(darkBase,darkBody,smoothstep(.08,.68,density));
      night=mix(night,darkLight,clamp(core*.62+ridge*.24,0.,.75));
      night*=1.-shadow;
      vec3 dayBase=vec3(.995,.998,1.);
      vec3 dayBody=vec3(.69,.82,.96);
      vec3 dayLight=vec3(.32,.56,.79);
      vec3 daylight=mix(dayBase,dayBody,smoothstep(.09,.79,density)*.75);
      daylight=mix(daylight,dayLight,clamp(core*.19+ridge*.07,0.,.22));
      daylight=mix(daylight,dayBase,collision*.18);
      // Preserve negative space and the site's existing soft vertical fade.
      float fade=1.-smoothstep(.64,1.,1.-uv.y);
      night=mix(darkBase,night,fade);
      daylight=mix(dayBase,daylight,fade);
      pixel=vec4(mix(daylight,night,dark),1.);
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
  const uniforms = Object.fromEntries(['resolution','time','dark','touch','seed'].map(name => [name, gl.getUniformLocation(program, name)]));
  gl.uniform2f(uniforms.seed, offset[0], offset[1]);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const system = matchMedia('(prefers-color-scheme: dark)');
  const coarse = matchMedia('(pointer: coarse)');
  let visible = true, lost = false, frame = 0, last = 0, elapsed = 0;
  const draw = () => {
    const theme = document.documentElement.dataset.theme;
    gl.uniform1f(uniforms.dark, theme === 'dark' || (theme !== 'light' && system.matches) ? 1 : 0);
    gl.uniform1f(uniforms.touch, coarse.matches ? 1 : 0);
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
  [reduced, system, coarse].forEach(query => query.addEventListener('change', refresh));
  document.addEventListener('visibilitychange', refresh);
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault(); lost = true; cancelAnimationFrame(frame); layer.classList.remove('is-ready');
  });
})();
