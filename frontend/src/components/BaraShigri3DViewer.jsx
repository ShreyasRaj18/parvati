import {useEffect,useMemo,useRef,useState} from "react";
import {Canvas,useFrame} from "@react-three/fiber";
import {OrbitControls} from "@react-three/drei";
import * as THREE from "three";
import "./BaraShigri3DViewer.css";
const BASE="/data/bara_shigri_3d/";

function GlacierParticles({meta,playing,speed,density,terrainValues}){
 const points=useRef(null);
 const particleIndices=useRef(null);
 const [field,setField]=useState(null);
 const particleCount=Math.max(100,Math.min(2500,Math.round(meta.valid_velocity_pixels*density)));
 useEffect(()=>{
  let live=true;
  Promise.all([
   fetch(BASE+meta.east_velocity_file).then(r=>{if(!r.ok)throw Error("Missing NISAR east velocity binary");return r.arrayBuffer()}),
   fetch(BASE+meta.north_velocity_file).then(r=>{if(!r.ok)throw Error("Missing NISAR north velocity binary");return r.arrayBuffer()}),
   fetch(BASE+meta.motion_mask_file).then(r=>{if(!r.ok)throw Error("Missing NISAR motion mask binary");return r.arrayBuffer()})
  ]).then(([eb,nb,mb])=>{
   if(!live)return;
   const east=new Float32Array(eb),north=new Float32Array(nb),mask=new Uint8Array(mb);
   if(east.length!==meta.width*meta.height||north.length!==east.length||mask.length!==east.length)throw Error("NISAR vector field dimensions do not match terrain.");
   const cells=[];for(let i=0;i<mask.length;i++)if(mask[i]&&Math.hypot(east[i],north[i])>0.001)cells.push(i);
   setField({east,north,cells});
  }).catch(e=>console.error("Bara Shigri particle field:",e));
  return()=>{live=false};
 },[meta]);
 const particleData=useMemo(()=>{
  if(!field||!field.cells.length||!terrainValues)return null;
  const positions=new Float32Array(particleCount*3),indices=new Uint32Array(particleCount);
  for(let p=0;p<particleCount;p++){const cell=field.cells[Math.floor(p*field.cells.length/particleCount)];indices[p]=cell;
   const row=Math.floor(cell/meta.width),col=cell%meta.width;
   positions[p*3]=(col-(meta.width-1)/2)*meta.pixel_size_x_m*.003;
   positions[p*3+1]=(terrainValues[cell]-meta.terrain_min_m)*.012+0.65;
   positions[p*3+2]=(row-(meta.height-1)/2)*meta.pixel_size_y_m*.003;
  }
  return {positions,indices};
 },[field,particleCount,meta,terrainValues]);
 useEffect(()=>{
  if(!particleData||!points.current)return;
  const g=points.current.geometry;
  g.setAttribute("position",new THREE.BufferAttribute(particleData.positions,3));
  g.attributes.position.needsUpdate=true;
  particleIndices.current=new Uint32Array(particleData.indices);
 },[particleData]);
 useFrame((_,delta)=>{
  if(!playing||!field||!field.cells.length||!particleIndices.current||!points.current)return;
  const attr=points.current.geometry.attributes.position;
  const pos=attr.array;
  for(let p=0;p<particleCount;p++){
   const cell=particleIndices.current[p],row=Math.floor(cell/meta.width),col=cell%meta.width;
   const ev=field.east[cell],nv=field.north[cell],mag=Math.hypot(ev,nv)||1;
   // Direction is true NISAR east/north. Time compression is a visual playback control.
   const step=Math.min(delta,.05)*speed*.0035*mag;
   pos[p*3]+=ev/mag*step;
   pos[p*3+2]+=-nv/mag*step;
   const cx=(col-(meta.width-1)/2)*meta.pixel_size_x_m*.003;
   const cz=(row-(meta.height-1)/2)*meta.pixel_size_y_m*.003;
   const dx=pos[p*3]-cx,dz=pos[p*3+2]-cz;
   if(Math.hypot(dx,dz)>meta.pixel_size_x_m*.003*2.2){
    const next=field.cells[Math.floor(Math.random()*field.cells.length)];
    particleIndices.current[p]=next;
    const rr=Math.floor(next/meta.width),cc=next%meta.width;
    pos[p*3]=(cc-(meta.width-1)/2)*meta.pixel_size_x_m*.003;
    pos[p*3+1]=(terrainValues[next]-meta.terrain_min_m)*.012+0.65;
    pos[p*3+2]=(rr-(meta.height-1)/2)*meta.pixel_size_y_m*.003;
   }
  }
  attr.needsUpdate=true;
 });
 if(!particleData)return null;
 return <points ref={points} frustumCulled={false}>
  <bufferGeometry/>
  <pointsMaterial color="#fff2a8" size={2.35} sizeAttenuation transparent opacity={1} depthWrite={false}/>
 </points>;
}

function Surface({meta,layer,opacity,showParticles,playing,speed,density}){
 const [geometry,setGeometry]=useState(null),[texture,setTexture]=useState(null),[error,setError]=useState("");
 const [terrainValues,setTerrainValues]=useState(null);
 const file=useMemo(()=>layer==="velocity"?meta.velocity_file:layer==="daily"?meta.daily_velocity_file:layer==="uncertainty"?meta.uncertainty_file:meta.candidate_mask_file,[meta,layer]);
 useEffect(()=>{let live=true;
  fetch(BASE+meta.terrain_file).then(r=>{if(!r.ok)throw Error("Terrain binary missing");return r.arrayBuffer()})
   .then(buf=>{if(!live)return;const a=new Float32Array(buf),w=meta.width,h=meta.height;if(a.length!==w*h)throw Error("Terrain dimensions mismatch");setTerrainValues(a);
    const pos=[],col=[],uv=[],idx=[],lo=meta.terrain_min_m,range=Math.max(1,meta.terrain_max_m-lo);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){let i=y*w+x,t=THREE.MathUtils.clamp((a[i]-lo)/range,0,1),s=.28+t*.48;
     pos.push((x-(w-1)/2)*meta.pixel_size_x_m*.003,(a[i]-lo)*.012,(y-(h-1)/2)*meta.pixel_size_y_m*.003);
     col.push(s*.78,s*.92,s);uv.push(x/(w-1),1-y/(h-1));
     if(x<w-1&&y<h-1){let b=i+1,c=i+w,d=i+w+1;idx.push(i,c,b,b,c,d);}
    }
    let g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.Float32BufferAttribute(pos,3));g.setAttribute("color",new THREE.Float32BufferAttribute(col,3));g.setAttribute("uv",new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();setGeometry(g);
   }).catch(e=>setError(e.message));
  return()=>{live=false};
 },[meta]);
 useEffect(()=>{let live=true;new THREE.TextureLoader().load(BASE+file,t=>{if(live){t.colorSpace=THREE.SRGBColorSpace;t.magFilter=THREE.LinearFilter;t.minFilter=THREE.LinearFilter;setTexture(t)}},undefined,()=>setTexture(null));return()=>{live=false}},[file]);
 if(error)return <mesh visible={false}/>;if(!geometry)return null;
 return <group><mesh geometry={geometry}><meshStandardMaterial vertexColors roughness={.92}/></mesh>
  {texture&&<mesh geometry={geometry} renderOrder={2}><meshBasicMaterial map={texture} transparent opacity={opacity} depthWrite={false} side={THREE.DoubleSide} polygonOffset polygonOffsetFactor={-1}/></mesh>}
  {showParticles&&<GlacierParticles meta={meta} playing={playing} speed={speed} density={density} terrainValues={terrainValues}/>}
 </group>;
}

export default function BaraShigri3DViewer(){
 const [meta,setMeta]=useState(null),[error,setError]=useState(""),[layer,setLayer]=useState("velocity"),[opacity,setOpacity]=useState(.92);
 const [playing,setPlaying]=useState(true),[speed,setSpeed]=useState(1),[density,setDensity]=useState(.45),[showParticles,setShowParticles]=useState(true);
 useEffect(()=>{fetch(BASE+"metadata.json").then(r=>{if(!r.ok)throw Error("3D metadata not found. Run the preparation script.");return r.json()}).then(setMeta).catch(e=>setError(e.message))},[]);
 return <main className="bs3d">
  <header><div><small>NISAR · BARA SHIGRI</small><h2>3D Glacier Dynamics</h2><p>Measured horizontal glacier motion animated over Copernicus DEM terrain.</p></div>
  <div className="dates">REFERENCE <b>04 OCT 2026</b><br/>SECONDARY <b>16 OCT 2026</b></div></header>
  <nav><label>DATA LAYER <select value={layer} onChange={e=>setLayer(e.target.value)}>
   <option value="velocity">Horizontal velocity · m/year</option><option value="daily">Horizontal velocity · m/day</option>
   <option value="uncertainty">Velocity uncertainty · m/year</option><option value="mask">Candidate mask</option>
  </select></label><label>OVERLAY OPACITY <input type="range" min=".2" max="1" step=".05" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label></nav>
  <div className="bs3d-playback">
   <button onClick={()=>setPlaying(v=>!v)}>{playing?"Pause movement":"Play movement"}</button>
   <label><input type="checkbox" checked={showParticles} onChange={e=>setShowParticles(e.target.checked)}/> Show glacier particles</label>
   <label>Playback speed <input type="range" min=".25" max="4" step=".25" value={speed} onChange={e=>setSpeed(+e.target.value)}/></label>
   <label>Particle density <input type="range" min=".15" max="1" step=".05" value={density} onChange={e=>setDensity(+e.target.value)}/></label>
  </div>
  <div className="bs3d-canvas">{error?<p>{error}</p>:!meta?<p>Loading terrain…</p>:<Canvas
    camera={{position:[0,58,82],fov:38,near:0.1,far:1200}}
    dpr={[1,1.75]}
    gl={{antialias:true,alpha:false}}
   >
   <color attach="background" args={["#07111c"]}/><ambientLight intensity={1.15}/><directionalLight position={[80,120,50]} intensity={2}/>
   <Surface meta={meta} layer={layer} opacity={opacity} showParticles={showParticles} playing={playing} speed={speed} density={density}/>
   <OrbitControls
     makeDefault enableDamping dampingFactor={0.08}
     target={[0,12,0]} minDistance={28} maxDistance={260}
     maxPolarAngle={Math.PI*.49}
    />
  </Canvas>}</div>
  {meta&&<section className="bs3d-stats">{[
   ["VALID PIXELS",meta.valid_velocity_pixels.toLocaleString()],["MEDIAN VELOCITY",meta.velocity_m_per_year.median.toFixed(2)+" m/yr"],
   ["MEAN VELOCITY",meta.velocity_m_per_year.mean.toFixed(2)+" m/yr"],["MEDIAN UNCERTAINTY",meta.uncertainty_m_per_year_median.toFixed(2)+" m/yr"],
   ["DEM COVERAGE",(meta.dem_coverage_fraction*100).toFixed(1)+"%"]
  ].map(([k,v])=><div key={k}><small>{k}</small><b>{v}</b></div>)}</section>}
  <p className="bs3d-note">Particle direction follows the NISAR east/north horizontal velocity components. Playback is time-compressed for visibility; it is not a forecast. Vertical motion is not included.</p>
 </main>;
}
