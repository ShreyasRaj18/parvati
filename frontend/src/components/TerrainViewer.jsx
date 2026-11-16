
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import "./SamudraTerrainViewer.css";

const SCENE_SCALE = 0.05;

function sampleElevation(metadata, elevations, x, z) {
  const col =
    x / metadata.pixel_size_x_m + (metadata.width - 1) / 2;
  const row =
    z / metadata.pixel_size_y_m + (metadata.height - 1) / 2;

  const x0 = Math.max(0, Math.min(metadata.width - 1, Math.floor(col)));
  const y0 = Math.max(0, Math.min(metadata.height - 1, Math.floor(row)));
  const x1 = Math.min(metadata.width - 1, x0 + 1);
  const y1 = Math.min(metadata.height - 1, y0 + 1);

  const fx = Math.max(0, Math.min(1, col - x0));
  const fy = Math.max(0, Math.min(1, row - y0));

  const a = elevations[y0 * metadata.width + x0];
  const b = elevations[y0 * metadata.width + x1];
  const c = elevations[y1 * metadata.width + x0];
  const d = elevations[y1 * metadata.width + x1];

  return (
    a * (1 - fx) * (1 - fy) +
    b * fx * (1 - fy) +
    c * (1 - fx) * fy +
    d * fx * fy
  );
}

function DrainageNetwork({ segments }) {
  const geometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(segments, 3)
    );
    return geometry;
  }, [segments]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial
        color="#36a9ff"
        transparent
        opacity={0.9}
      />
    </lineSegments>
  );
}


function CorridorNetwork({ segments }) {
  const geometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(segments, 3)
    );

    geometry.computeBoundingSphere();
    return geometry;
  }, [segments]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial
        color="#ff7043"
        transparent
        opacity={0.95}
        depthTest={true}
      />
    </lineSegments>
  );
}

function CorridorSurface({ vertices }) {
  const geometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(vertices, 3)
    );

    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();

    return geometry;
  }, [vertices]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <mesh geometry={geometry}>
  <meshStandardMaterial
  color="#ff7138"
  emissive="#a83208"
  emissiveIntensity={0.4}
  transparent
  opacity={0.72}
  roughness={0.8}
  metalness={0}
  side={THREE.DoubleSide}
  depthWrite={false}
/>
    </mesh>
  );
}


function TerrainMesh({ metadata, elevations }) {
  const geometry = useMemo(() => {
    const { width, height, pixel_size_x_m, pixel_size_y_m } = metadata;
    const geometry = new THREE.BufferGeometry();

    const positions = new Float32Array(width * height * 3);
    const colors = new Float32Array(width * height * 3);
    const indices = [];

    const min = metadata.min_elevation_m;
    const max = metadata.max_elevation_m;
    const range = max - min || 1;

    for (let row = 0; row < height; row++) {
      for (let col = 0; col < width; col++) {
        const index = row * width + col;
        const elevation = elevations[index];

        const x = (col - (width - 1) / 2) * pixel_size_x_m;
        const z = (row - (height - 1) / 2) * pixel_size_y_m;
        const y = elevation - min;

        positions[index * 3] = x;
        positions[index * 3 + 1] = y;
        positions[index * 3 + 2] = z;

        const normalized = THREE.MathUtils.clamp(
          (elevation - min) / range,
          0,
          1
        );

        const color = new THREE.Color().setHSL(
          0.31 - normalized * 0.12,
          0.30,
          0.24 + normalized * 0.29
        );

        colors[index * 3] = color.r;
        colors[index * 3 + 1] = color.g;
        colors[index * 3 + 2] = color.b;

        if (col < width - 1 && row < height - 1) {
          const a = index;
          const b = index + 1;
          const c = index + width;
          const d = index + width + 1;
          indices.push(a, c, b, b, c, d);
        }
      }
    }

    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(positions, 3)
    );
    geometry.setAttribute(
      "color",
      new THREE.BufferAttribute(colors, 3)
    );
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    return geometry;
  }, [metadata, elevations]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        vertexColors
        roughness={1}
        metalness={0}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function DrapedBoundary({ polygons, color, metadata, elevations, offset = 1 }) {
  const geometries = useMemo(() => {
    return polygons.map((ring) => {
      const vertices = ring.map(([x, z]) => {
        const elevation = sampleElevation(metadata, elevations, x, z);
        return new THREE.Vector3(
          x,
          elevation - metadata.min_elevation_m + offset,
          z
        );
      });

      const geometry = new THREE.BufferGeometry().setFromPoints(vertices);
      return geometry;
    });
  }, [polygons, color, metadata, elevations, offset]);

  useEffect(
    () => () => geometries.forEach((geometry) => geometry.dispose()),
    [geometries]
  );

  return (
    <>
      {geometries.map((geometry, index) => (
        <line key={index} geometry={geometry}>
          <lineBasicMaterial color={color} />
        </line>
      ))}
    </>
  );
}


function LakeWater({ metadata }) {
  const waterMesh = useRef(null);

  const geometry = useMemo(() => {
    const positions = [];
    const indices = [];
    const waterY =
      metadata.lake_surface_elevation_m -
      metadata.min_elevation_m +
      1.5;

    for (const ring of metadata.lake_boundary_local) {
      // Convert the lake polygon to Three.js horizontal coordinates.
      const contour = ring.slice(0, -1).map(
        ([x, z]) => new THREE.Vector2(x, z)
      );

      if (contour.length < 3) continue;

      const faces = THREE.ShapeUtils.triangulateShape(contour, []);
      const offset = positions.length / 3;

      contour.forEach((point) => {
        positions.push(point.x, waterY, point.y);
      });

      faces.forEach(([a, b, c]) => {
        indices.push(offset + a, offset + b, offset + c);
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3)
    );
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    geometry.userData.basePositions = new Float32Array(positions);

    return geometry;
  }, [metadata]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame(({ clock }) => {
    const geometry = waterMesh.current?.geometry;
    if (!geometry) return;

    const position = geometry.attributes.position;
    const base = geometry.userData.basePositions;
    const time = clock.getElapsedTime();

    for (let i = 0; i < position.count; i++) {
      const x = base[i * 3];
      const originalY = base[i * 3 + 1];
      const z = base[i * 3 + 2];

      const wave =
        Math.sin(x * 0.002 + time * 1.2) * 0.35 +
        Math.cos(z * 0.0025 - time * 0.9) * 0.25;

      position.setY(i, originalY + wave);
    }

    position.needsUpdate = true;
    geometry.computeVertexNormals();
  });

  return (
    <mesh ref={waterMesh} geometry={geometry}>
      <meshStandardMaterial
        color="#27c8e8"
        roughness={0.19}
        metalness={0.12}
        transparent
        opacity={0.82}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}


function FlowingWaterNetwork({ segments, playing = true, speed = 1 }) {
  const materialRef = useRef(null);

  const geometry = useMemo(() => {
    if (!segments || segments.length < 6) return null;

    const positions = [];
    const uvs = [];
    const indices = [];
    const halfWidth = 9.0; // illustrative channel ribbon width in metres

    for (let i = 0; i + 5 < segments.length; i += 6) {
      const x1 = segments[i];
      const y1 = segments[i + 1] + 1.2;
      const z1 = segments[i + 2];
      const x2 = segments[i + 3];
      const y2 = segments[i + 4] + 1.2;
      const z2 = segments[i + 5];

      const dx = x2 - x1;
      const dz = z2 - z1;
      const length = Math.hypot(dx, dz);
      if (length < 0.01) continue;

      // Perpendicular to the downstream segment in the horizontal plane.
      const px = (-dz / length) * halfWidth;
      const pz = (dx / length) * halfWidth;
      const base = positions.length / 3;

      positions.push(
        x1 + px, y1, z1 + pz,
        x1 - px, y1, z1 - pz,
        x2 + px, y2, z2 + pz,
        x2 - px, y2, z2 - pz
      );

      // U follows the verified D8 downstream direction.
      uvs.push(0, 0, 0, 1, Math.max(1, length / 18), 0, Math.max(1, length / 18), 1);
      indices.push(
        base, base + 1, base + 2,
        base + 2, base + 1, base + 3
      );
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    g.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    g.setIndex(indices);
    g.computeVertexNormals();
    g.computeBoundingSphere();
    return g;
  }, [segments]);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime.value = playing ? clock.getElapsedTime() : materialRef.current.uniforms.uTime.value;
    materialRef.current.uniforms.uSpeed.value = speed;
    materialRef.current.uniforms.uPlaying.value = playing ? 1 : 0;
  });

  useEffect(() => () => geometry?.dispose(), [geometry]);

  if (!geometry) return null;

  return (
    <mesh geometry={geometry} renderOrder={12}>
      <shaderMaterial
        ref={materialRef}
        transparent
        depthWrite={false}
        side={THREE.DoubleSide}
        uniforms={{
          uTime: { value: 0 },
          uSpeed: { value: speed },
          uPlaying: { value: playing ? 1 : 0 }
        }}
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          uniform float uTime;
          uniform float uSpeed;
          uniform float uPlaying;
          varying vec2 vUv;
          void main() {
            float phase = fract(vUv.x * 1.65 - uTime * uSpeed * 0.42 * uPlaying);
            float band = smoothstep(0.02, 0.16, phase) * (1.0 - smoothstep(0.34, 0.50, phase));
            float shimmer = 0.82 + 0.18 * sin(vUv.x * 18.0 - uTime * 2.2);
            vec3 deep = vec3(0.015, 0.25, 0.43);
            vec3 bright = vec3(0.16, 0.83, 0.96);
            vec3 color = mix(deep, bright, band * 0.92) * shimmer;
            float alpha = 0.82 + band * 0.16;
            gl_FragColor = vec4(color, alpha);
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }
        `}
      />
    </mesh>
  );
}

function TerrainScene({
  metadata,
  elevations,
  drainage,
  corridorSegments,
  corridorMesh,
  flowSegments,
  flowPlaying,
  flowSpeed,
  showTerrain,
  showLakeWater,
  showLakeBoundary,
  showCatchment,
  showDrainage,
  showCorridor,
}) {
  const height = metadata.max_elevation_m - metadata.min_elevation_m;
  const width = metadata.width * metadata.pixel_size_x_m;
  const depth = metadata.height * metadata.pixel_size_y_m;
  const maxDimension = Math.max(width, depth, height);

  return (
    <>
      <color attach="background" args={["#08121c"]} />
      <ambientLight intensity={1.1} />
      <directionalLight position={[4000, 7000, 3000]} intensity={2.1} />
      <directionalLight position={[-3000, 2500, -4000]} intensity={0.45} />

      <group scale={SCENE_SCALE}>
      {showTerrain && (
        <TerrainMesh
          metadata={metadata}
          elevations={elevations}
        />
      )}

      {showLakeWater && (
        <LakeWater metadata={metadata} />
      )}

      {showDrainage && drainage && (
        <DrainageNetwork segments={drainage} />
      )}
      {showDrainage && flowSegments && (
        <FlowingWaterNetwork segments={flowSegments} playing={flowPlaying} speed={flowSpeed} />
      )}
{showCorridor && corridorSegments && (
  <CorridorNetwork segments={corridorSegments} />
)}
      {showCorridor && corridorMesh && (
        <CorridorSurface vertices={corridorMesh} />
      )}
      {showCatchment && (
        <DrapedBoundary
          polygons={metadata.catchment_boundary_local}
          color="#f3d36e"
          metadata={metadata}
          elevations={elevations}
          offset={2}
        />
      )}

      {showLakeBoundary && (
        <DrapedBoundary
          polygons={metadata.lake_boundary_local}
          color="#8beeff"
          metadata={metadata}
          elevations={elevations}
          offset={2}
        />
      )}

      </group>

      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        target={[0, height * 0.25 * SCENE_SCALE, 0]}
        minDistance={Math.max(1, maxDimension * 0.03 * SCENE_SCALE)}
        maxDistance={maxDimension * 3 * SCENE_SCALE}
        zoomSpeed={1.2}
        maxPolarAngle={Math.PI / 2.02}
      />
    </>
  );
}

export default function TerrainViewer({
  showTerrain = true,
  showLakeWater = true,
  showLakeBoundary = true,
  showCatchment = true,
  showDrainage = true,
  showCorridor = true,
  corridorThreshold = 1000,
}) {
  const [metadata, setMetadata] = useState(null);
  const [elevations, setElevations] = useState(null);
  const [error, setError] = useState("");
const [drainage, setDrainage] = useState(null);
const [corridorMesh, setCorridorMesh] = useState(null);
const [corridorOutline, setCorridorOutline] = useState(null);
const [flowSegments, setFlowSegments] = useState(null);
const [flowPlaying, setFlowPlaying] = useState(true);
const [flowSpeed, setFlowSpeed] = useState(1);
  useEffect(() => {
    let cancelled = false;

    async function loadTerrain() {
      try {
        const metaResponse = await fetch("/data/samudra_terrain_metadata.json");
        if (!metaResponse.ok) throw new Error("Terrain metadata could not be loaded.");
const drainageResponse = await fetch(
  "/data/samudra_drainage_5000_segments.bin"
);

if (!drainageResponse.ok) {
  throw new Error("Could not load drainage network.");
}

const drainageBuffer = await drainageResponse.arrayBuffer();
const drainageValues = new Float32Array(drainageBuffer);

        const meta = await metaResponse.json();

        const terrainResponse = await fetch("/data/samudra_terrain.bin");
        if (!terrainResponse.ok) throw new Error("Terrain binary could not be loaded.");

        const buffer = await terrainResponse.arrayBuffer();
        const values = new Float32Array(buffer);

        if (values.length !== meta.width * meta.height) {
          throw new Error("Terrain binary dimensions do not match metadata.");
        }

        const maskResponse = await fetch(
          `/data/${meta.catchment_mask_file}`
        );
        if (!maskResponse.ok) {
          throw new Error("Could not load catchment mask for flow particles.");
        }
        const maskBuffer = await maskResponse.arrayBuffer();
        const catchmentMask = new Uint8Array(maskBuffer);
        if (catchmentMask.length !== meta.width * meta.height) {
          throw new Error("Catchment mask dimensions do not match terrain.");
        }

        const flowResponse = await fetch("/data/samudra_d8_flow_particle_segments.bin");
        if (!flowResponse.ok) throw new Error("Could not load verified D8 drainage paths.");
        const flowBuffer = await flowResponse.arrayBuffer();
        if (flowBuffer.byteLength % 24 !== 0) throw new Error("Invalid D8 flow particle binary.");
        const sourceFlowValues = new Float32Array(flowBuffer);
        const visibleFlowValues = new Float32Array(sourceFlowValues.length);
        const halfWidth =
          (meta.width * meta.pixel_size_x_m) / 2;
        const halfDepth =
          (meta.height * meta.pixel_size_y_m) / 2;
        let visibleLength = 0;

        const isInsideCatchment = (x, z) => {
          if (Math.abs(x) > halfWidth || Math.abs(z) > halfDepth) {
            return false;
          }

          const col = Math.floor(
            x / meta.pixel_size_x_m + meta.width / 2
          );
          const row = Math.floor(
            z / meta.pixel_size_y_m + meta.height / 2
          );

          return (
            row >= 0
            && row < meta.height
            && col >= 0
            && col < meta.width
            && catchmentMask[row * meta.width + col] === 1
          );
        };

        for (let i = 0; i < sourceFlowValues.length; i += 6) {
          if (
            !isInsideCatchment(sourceFlowValues[i], sourceFlowValues[i + 2])
            || !isInsideCatchment(sourceFlowValues[i + 3], sourceFlowValues[i + 5])
          ) {
            continue;
          }

          visibleFlowValues.set(
            sourceFlowValues.subarray(i, i + 6),
            visibleLength
          );
          visibleLength += 6;
        }

        const flowValues = visibleFlowValues.slice(0, visibleLength);
        if (flowValues.length === 0) {
          throw new Error("No drainage paths overlap the terrain catchment.");
        }

        if (!cancelled) {
          setMetadata(meta);
          setElevations(values);
          setDrainage(drainageValues);
          setFlowSegments(flowValues);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    loadTerrain();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadCorridorOutline() {
      try {
        setCorridorOutline(null);

        const response = await fetch(
          `/data/samudra_corridor_${corridorThreshold}_segments.bin`
        );
        if (!response.ok) {
          throw new Error("Could not load matching corridor outline.");
        }

        const buffer = await response.arrayBuffer();
        if (buffer.byteLength % 24 !== 0) {
          throw new Error("Invalid corridor outline binary.");
        }

        if (!cancelled) {
          setCorridorOutline(new Float32Array(buffer));
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    loadCorridorOutline();
    return () => {
      cancelled = true;
    };
  }, [corridorThreshold]);

  useEffect(() => {
    let cancelled = false;

    async function loadCorridorMesh() {
      try {
        setCorridorMesh(null);
        setError("");

        const response = await fetch(
          `/data/samudra_corridor_${corridorThreshold}_mesh.bin`
        );

        if (!response.ok) {
          throw new Error(
            `Could not load ${corridorThreshold}-cell corridor mesh.`
          );
        }

        const buffer = await response.arrayBuffer();

        if (buffer.byteLength % 36 !== 0) {
          throw new Error("Invalid corridor mesh binary size.");
        }

        const values = new Float32Array(buffer);

        if (values.length % 9 !== 0) {
          throw new Error("Invalid corridor triangle data.");
        }

        if (!cancelled) {
          setCorridorMesh(values);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    loadCorridorMesh();

    return () => {
      cancelled = true;
    };
  }, [corridorThreshold]);

  if (error) return <div className="terrain-error">{error}</div>;

  if (!metadata || !elevations) {
    return <div className="terrain-loading">Loading expanded Copernicus terrain...</div>;
  }

  const height = metadata.max_elevation_m - metadata.min_elevation_m;
  const width = metadata.width * metadata.pixel_size_x_m;
  const depth = metadata.height * metadata.pixel_size_y_m;
  const maxDimension = Math.max(width, depth, height);

  return (
    <div className="terrain-viewer-shell">
      <div className="terrain-flow-controls">
        <button type="button" onClick={() => setFlowPlaying(v => !v)}>
          {flowPlaying ? "Pause water flow" : "Play water flow"}
        </button>
        <label>Water animation speed
          <input type="range" min="0.25" max="4" step="0.25" value={flowSpeed}
            onChange={e => setFlowSpeed(Number(e.target.value))} />
        </label>
        <span>{flowSegments ? "Continuous water ribbon along DEM-derived drainage · illustrative flow" : "Loading DEM-derived drainage paths…"}</span>
      </div>
      <div className="terrain-canvas">
      <Canvas
        camera={{
          position: [
            maxDimension * 0.75 * SCENE_SCALE,
            maxDimension * 0.65 * SCENE_SCALE,
            maxDimension * 0.9 * SCENE_SCALE,
          ],
          fov: 42,
          near: 0.1,
          far: maxDimension * 10 * SCENE_SCALE,
        }}
        dpr={[1, 1.5]}
        gl={{ antialias: true }}
      >
        <TerrainScene
          metadata={metadata}
          elevations={elevations}
          drainage={drainage}
          corridorMesh={corridorMesh}
          flowSegments={flowSegments}
          flowPlaying={flowPlaying}
          flowSpeed={flowSpeed}
          showTerrain={showTerrain}
          showLakeWater={showLakeWater}
          showLakeBoundary={showLakeBoundary}
          showCatchment={showCatchment}
          showDrainage={showDrainage}
          corridorSegments={corridorOutline}
showCorridor={showCorridor}
        />
      </Canvas>
      </div>
    </div>
  );
}
